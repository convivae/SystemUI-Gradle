#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instruction-level aconfig jarjar reference gate (Task 099).

Scans every ``classes*.dex`` of a final APK, walks the real executable
instructions of every defined class (Dalvik opcode decoding with a table
derived from AOSP ``art/libdexfile/dex/dex_instruction_list.h``), resolves
every method/field/type/proto/method-handle/call-site index those
instructions carry, and applies the complete authoritative jarjar rule set
(725 exact renames; see ``gradle/aosp17-aconfig-repackaging-rules.txt``).

Gate verdict (fail-closed; exit 1 = FAIL, exit 2 = usage/parse error):

1. FAIL on ANY executable old-owner (rule source) reference whose caller
   class differs from the referenced old class. The ONLY allowed residuals
   are self-references (a rule-source class referencing its own old name),
   which resolve to the APK's own dead-shell definitions: every old-name
   class in the APK is a self-contained shell whose outward references
   (including ``BootstrapMethods`` method handles, so D8-synthesized
   lambdas) are rewritten to the on-device hidden twins. "Executable"
   includes instruction operands, exception catch types, and static-value
   encoded arrays (class-initializer constants), because those resolve at
   class init like instructions.
2. FAIL on ANY hidden-target definition in the APK (targets are device
   framework classes; packaging them is never legitimate).

Only executable references count (Task 095/099 ruling); bare type-table or
string-pool mentions do not. Strings are never rewritten by the production
seam, so string constants are reported only informationally under --full.

Usage (project rule: run via ``uv run python``)::

    uv run python tools/check_aconfig_jarjar_references.py \
        --apk app/build/outputs/apk/debug/app-debug.apk \
        [--rules gradle/aosp17-aconfig-repackaging-rules.txt] \
        [--full]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

DEFAULT_RULES = "gradle/aosp17-aconfig-repackaging-rules.txt"
RULES_SHA256 = "411ad0e60c4647b3cc4c0160573e12f1a8ae5eadf9fc3f5492b76071b78d5191"
RULE_COUNT = 725
FULL_AOSP_RULES_SHA256 = "f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97"
CRITICAL_SOURCES = (
    "android.app.Flags",
    "android.os.Flags",
    "android.view.accessibility.Flags",
    "com.android.window.flags.Flags",
)
_RULE_RE = re.compile(r"^rule ([A-Za-z_$][A-Za-z0-9_$.]*) ([A-Za-z_$][A-Za-z0-9_$.]*)$")


class GateError(Exception):
    """Fatal usage/parse error (exit 2)."""


def fqcn_to_descriptor(fqcn: str) -> str:
    return "L" + fqcn.replace(".", "/") + ";"


def parse_rules(text: str) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        m = _RULE_RE.match(line)
        if not m:
            raise ValueError(f"line {lineno}: unsupported rule syntax (only exact renames): {line!r}")
        source, target = m.group(1), m.group(2)
        if source == target:
            raise ValueError(f"line {lineno}: identity rule: {line!r}")
        if source in seen:
            if seen[source] != target:
                raise ValueError(f"line {lineno}: conflicting duplicate rule for {source!r}")
            continue  # exact duplicate tolerated
        seen[source] = target
        rules.append((source, target))
    return rules


def load_rules(rules_path: Path) -> list[tuple[str, str]]:
    text = rules_path.read_text(encoding="utf-8")
    rules = parse_rules(text)
    if rules_path.name == DEFAULT_RULES.split("/")[-1]:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != RULES_SHA256 or len(rules) != RULE_COUNT:
            raise GateError(
                f"{rules_path}: frozen rules drift (sha256={digest}, count={len(rules)})"
            )
    return rules


# ---------------------------------------------------------------------------
# DEX structural parsing
# ---------------------------------------------------------------------------

class Dex:
    """Read-only parser for one DEX file (ids tables, class defs, map list)."""

    def __init__(self, blob: bytes, origin: str):
        self.blob = blob
        self.origin = origin
        if len(blob) < 112 or blob[0:4] != b"dex\n":
            raise GateError(f"{origin}: not a DEX file")
        (self.endian_tag,) = struct.unpack_from("<I", blob, 40)
        if self.endian_tag != 0x12345678:
            raise GateError(f"{origin}: bad endian tag")
        (
            _map_off,
            string_ids_size, string_ids_off,
            type_ids_size, type_ids_off,
            proto_ids_size, proto_ids_off,
            field_ids_size, field_ids_off,
            method_ids_size, method_ids_off,
            class_defs_size, class_defs_off,
        ) = struct.unpack_from("<13I", blob, 52)

        self._strings: list[str] = []
        for i in range(string_ids_size):
            (data_off,) = struct.unpack_from("<I", blob, string_ids_off + 4 * i)
            length, off = self._read_uleb(data_off)
            end = blob.index(b"\x00", off)
            self._strings.append(blob[off:end].decode("utf-8", errors="replace"))

        self._types: list[str] = []
        for i in range(type_ids_size):
            (idx,) = struct.unpack_from("<I", blob, type_ids_off + 4 * i)
            self._types.append(self._strings[idx])

        self._protos: list[list[str]] = []  # param types + return type
        for i in range(proto_ids_size):
            _shorty_idx, return_idx, params_off = struct.unpack_from("<III", blob, proto_ids_off + 12 * i)
            types = []
            if params_off:
                (size,) = struct.unpack_from("<I", blob, params_off)
                types = [self._types[t] for t in struct.unpack_from(f"<{size}H", blob, params_off + 4)]
            self._protos.append(types + [self._types[return_idx]])

        self._fields: list[tuple[str, str]] = []  # (owner, type)
        for i in range(field_ids_size):
            class_idx, type_idx, _name_idx = struct.unpack_from("<HHI", blob, field_ids_off + 8 * i)
            self._fields.append((self._types[class_idx], self._types[type_idx]))

        self._methods: list[tuple[str, int]] = []  # (owner, proto_idx)
        for i in range(method_ids_size):
            class_idx, proto_idx, _name_idx = struct.unpack_from("<HHI", blob, method_ids_off + 8 * i)
            self._methods.append((self._types[class_idx], proto_idx))

        # map_list -> method_handles (type 0x0008) and call_sites (0x0007)
        self.method_handles: list[tuple[int, int]] = []  # (handle type, field/method target idx)
        self.call_sites: list[int] = []  # offsets of encoded_array args
        if _map_off:
            (n,) = struct.unpack_from("<I", blob, _map_off)
            for i in range(n):
                type_, _unused, size, offset = struct.unpack_from("<HHII", blob, _map_off + 4 + 12 * i)
                if type_ == 0x0008:
                    for j in range(size):
                        mh_type, _r, target = struct.unpack_from("<HHI", blob, offset + 8 * j)
                        self.method_handles.append((mh_type, target))
                elif type_ == 0x0007:
                    for j in range(size):
                        _mh_idx, arr_off = struct.unpack_from("<II", blob, offset + 8 * j)
                        self.call_sites.append(arr_off)

        # class_defs: (descriptor, class_data_off, static_values_off)
        self.class_defs: list[tuple[str, int, int]] = []
        for i in range(class_defs_size):
            type_idx = struct.unpack_from("<I", blob, class_defs_off + 32 * i)[0]
            (class_data_off, static_values_off) = struct.unpack_from("<II", blob, class_defs_off + 32 * i + 24)
            self.class_defs.append((self._types[type_idx], class_data_off, static_values_off))
        self.defined = {d for d, _, _ in self.class_defs}

    # -- table accessors ---------------------------------------------------

    def type(self, idx: int) -> str:
        return self._types[idx]

    def field_refs(self, idx: int) -> list[str]:
        owner, ftype = self._fields[idx]
        return [owner, ftype]

    def method_refs(self, idx: int) -> list[str]:
        owner, proto_idx = self._methods[idx]
        return [owner] + self._protos[proto_idx]

    def proto_refs(self, idx: int) -> list[str]:
        return self._protos[idx]

    def method_handle_refs(self, mh_idx: int) -> list[str]:
        mh_type, target = self.method_handles[mh_idx]
        if mh_type <= 0x03:  # field accessors
            return self.field_refs(target)
        return self.method_refs(target)  # 0x04..0x08 invokes

    # -- uleb/sleb ----------------------------------------------------------

    def _read_uleb(self, off: int) -> tuple[int, int]:
        result = 0
        shift = 0
        while True:
            b = self.blob[off]
            off += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result, off
            shift += 7

    def read_uleb(self, off: int) -> tuple[int, int]:
        return self._read_uleb(off)

    def read_sleb(self, off: int) -> tuple[int, int]:
        result = 0
        shift = 0
        while True:
            b = self.blob[off]
            off += 1
            result |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                if b & 0x40:
                    result -= 1 << shift
                return result, off

    # -- encoded values -------------------------------------------------------

    def call_site_refs(self, cs_idx: int) -> list[str]:
        """Descriptors referenced via a call site (bootstrap method handle + static args)."""
        mh_idx, arr_off = self.call_sites[cs_idx]
        refs = list(self.method_handle_refs(mh_idx))
        size, off = self._read_uleb(arr_off)
        for _ in range(size):
            part, off = self._encoded_value_refs(off)
            refs.extend(part)
        return refs

    def encoded_array_refs(self, off: int) -> list[str]:
        """Class-init-executable descriptors inside an encoded_array."""
        size, off = self._read_uleb(off)
        refs: list[str] = []
        for _ in range(size):
            refs_part, off = self._encoded_value_refs(off)
            refs.extend(refs_part)
        return refs

    def _encoded_value_refs(self, off: int) -> tuple[list[str], int]:
        # encoded_value header is a SINGLE byte: (value_arg << 5) | value_type
        header = self.blob[off]
        off += 1
        tag = header & 0x1F
        nbytes = (header >> 5) + 1
        if tag in (0x1C,):  # array
            size, off = self._read_uleb(off)
            refs: list[str] = []
            for _ in range(size):
                part, off = self._encoded_value_refs(off)
                refs.extend(part)
            return refs, off
        if tag == 0x1D:  # annotation (recursed for strictness)
            type_idx, off = self._read_uleb(off)
            refs = [self._types[type_idx]]
            size, off = self._read_uleb(off)
            for _ in range(size):
                _name_idx, off = self._read_uleb(off)
                part, off = self._encoded_value_refs(off)
                refs.extend(part)
            return refs, off
        if tag in (0x1E, 0x1F):  # null / boolean: no payload
            return [], off
        idx = int.from_bytes(self.blob[off:off + nbytes], "little")
        off += nbytes
        if tag == 0x15:  # method_type -> proto
            return self._protos[idx], off
        if tag == 0x16:  # method_handle
            return self.method_handle_refs(idx), off
        if tag == 0x18:  # type
            return [self._types[idx]], off
        if tag in (0x19, 0x1B):  # field / enum
            return self.field_refs(idx), off
        if tag == 0x1A:  # method
            return self.method_refs(idx), off
        return [], off  # string and primitives carry no class refs


# ---------------------------------------------------------------------------
# Dalvik instruction decoding
# ---------------------------------------------------------------------------

# Instruction size in 16-bit code units for every opcode 0x00..0xFF.
# GENERATED from AOSP art/libdexfile/dex/dex_instruction_list.h (format
# strings, aosp17 frozen tree); do not hand-edit. Verified: 256 entries,
# k10x/k12x/k11n/k11x/k10t=1, k2*=2, k30t/k32x/k31t/k31i/k31c/k35c/k3rc/
# k45cc/k4rcc=3, k51l=5.
_INSN_SIZES = (
    1, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 1, 1, 1, 1, 1,  # 0x00-0x0F
    1, 1, 1, 2, 3, 2, 2, 3, 5, 2, 2, 3, 2, 1, 1, 2,  # 0x10-0x1F
    2, 1, 2, 2, 3, 3, 3, 1, 1, 2, 3, 3, 3, 2, 2, 2,  # 0x20-0x2F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1,  # 0x30-0x3F
    1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,  # 0x40-0x4F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,  # 0x50-0x5F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3,  # 0x60-0x6F
    3, 3, 3, 1, 3, 3, 3, 3, 3, 1, 1, 1, 1, 1, 1, 1,  # 0x70-0x7F
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  # 0x80-0x8F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,  # 0x90-0x9F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,  # 0xA0-0xAF
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  # 0xB0-0xBF
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  # 0xC0-0xCF
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,  # 0xD0-0xDF
    2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  # 0xE0-0xEF
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 2, 2,  # 0xF0-0xFF
)

# Opcode -> operand index kind. Index is always the 16-bit unit right after
# the opcode unit (formats k21c/k22c/k35c/k3rc/k45cc/k4rcc); invoke-
# polymorphic additionally carries a proto index as the 4th unit.
_KIND_TYPE = frozenset((0x1C, 0x1F, 0x20, 0x22, 0x23, 0x24, 0x25))
_KIND_FIELD = frozenset(range(0x52, 0x6E))  # iget..sput (0x52-0x6D)
_KIND_METHOD = frozenset((0x6E, 0x6F, 0x70, 0x71, 0x72, 0x74, 0x75, 0x76, 0x77, 0x78))
_KIND_CALLSITE = frozenset((0xFC, 0xFD))
_KIND_METHODHANDLE = frozenset((0xFE,))
_KIND_PROTO = frozenset((0xFF,))
_KIND_STRING = frozenset((0x1A, 0x1B))  # reported informationally only


def _payload_units(dex: Dex, op_off: int, ident: int) -> int:
    blob = dex.blob
    if ident == 0x01:  # packed-switch-payload: ident, size u2, first_key i4, size*(i4)
        (size,) = struct.unpack_from("<H", blob, op_off + 2)
        return 4 + size * 2
    if ident == 0x02:  # sparse-switch-payload: ident, size u2, size*(u4), size*(i4)
        (size,) = struct.unpack_from("<H", blob, op_off + 2)
        return 2 + size * 4
    # fill-array-data-payload: ident, elem_width(u2), size(u4), data
    (elem_width,) = struct.unpack_from("<H", blob, op_off + 2)
    (size,) = struct.unpack_from("<I", blob, op_off + 4)
    return 4 + (size * elem_width + 1) // 2


def walk_code_item(dex: Dex, code_off: int) -> list[str]:
    """Descriptors referenced by executable instructions + catch types."""
    if code_off == 0:
        return []
    blob = dex.blob
    tries_size, = struct.unpack_from("<H", blob, code_off + 6)
    insns_size, = struct.unpack_from("<I", blob, code_off + 12)
    insns_off = code_off + 16
    refs: list[str] = []
    pc = 0
    while pc < insns_size:
        op_off = insns_off + 2 * pc
        (unit,) = struct.unpack_from("<H", blob, op_off)
        opcode = unit & 0xFF
        if opcode == 0x00 and (unit >> 8) in (0x01, 0x02, 0x03):
            pc += _payload_units(dex, op_off, unit >> 8)
            continue
        size = _INSN_SIZES[opcode]
        if size == 0:
            raise GateError(f"{dex.origin}: zero-size opcode 0x{opcode:02x} at pc {pc}")
        if opcode in _KIND_TYPE:
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            refs.append(dex.type(idx))
        elif opcode in _KIND_FIELD:
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            refs.extend(dex.field_refs(idx))
        elif opcode in _KIND_METHOD:
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            refs.extend(dex.method_refs(idx))
        elif opcode in (0xFA, 0xFB):  # invoke-polymorphic: method + proto idx
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            (pidx,) = struct.unpack_from("<H", blob, op_off + 6)
            refs.extend(dex.method_refs(idx))
            refs.extend(dex.proto_refs(pidx))
        elif opcode in _KIND_CALLSITE:
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            refs.extend(dex.call_site_refs(idx))
        elif opcode in _KIND_METHODHANDLE:
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            refs.extend(dex.method_handle_refs(idx))
        elif opcode in _KIND_PROTO:
            (idx,) = struct.unpack_from("<H", blob, op_off + 2)
            refs.extend(dex.proto_refs(idx))
        pc += size
    if tries_size:
        handlers_off = insns_off + 2 * insns_size + (2 if insns_size % 2 else 0) + 8 * tries_size
        (list_size, off) = dex.read_uleb(handlers_off)
        for _ in range(list_size):
            size_s, off = dex.read_sleb(off)
            for _ in range(abs(size_s)):
                type_idx, off = dex.read_uleb(off)
                _addr, off = dex.read_uleb(off)
                refs.append(dex.type(type_idx))
            if size_s <= 0:
                _catch_all, off = dex.read_uleb(off)
    return refs


def walk_class_data(dex: Dex, class_data_off: int) -> list[int]:
    """Code item offsets of all methods of one class."""
    if class_data_off == 0:
        return []
    off = class_data_off
    static_fields, off = dex.read_uleb(off)
    instance_fields, off = dex.read_uleb(off)
    direct_methods, off = dex.read_uleb(off)
    virtual_methods, off = dex.read_uleb(off)
    for _ in range(static_fields + instance_fields):
        _fidx, off = dex.read_uleb(off)
        _flags, off = dex.read_uleb(off)
    code_offsets: list[int] = []
    for _ in range(direct_methods + virtual_methods):
        _midx, off = dex.read_uleb(off)
        _flags, off = dex.read_uleb(off)
        code_off, off = dex.read_uleb(off)
        code_offsets.append(code_off)
    return code_offsets


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


def scan_apk(apk_path: Path, rules: list[tuple[str, str]], full: bool = False) -> dict:
    sources = {fqcn_to_descriptor(s) for s, _ in rules}
    targets = {fqcn_to_descriptor(t) for _, t in rules}
    violations: list[str] = []
    old_owner_violations: list[str] = []
    self_refs: set[tuple[str, str]] = set()
    hidden_target_refs: set[tuple[str, str]] = set()
    old_ref_total = 0
    hidden_definitions: list[str] = []
    old_definitions: set[str] = set()
    string_mentions: set[tuple[str, str]] = set()
    dex_count = 0
    class_count = 0
    insn_ref_total = 0

    with zipfile.ZipFile(apk_path) as zf:
        dex_names = sorted(n for n in zf.namelist() if re.fullmatch(r"classes\d*\.dex", n))
        if not dex_names:
            raise GateError(f"{apk_path}: no classes dex found")
        for name in dex_names:
            dex = Dex(zf.read(name), name)
            dex_count += 1
            class_count += len(dex.class_defs)
            for descriptor, class_data_off, static_values_off in dex.class_defs:
                if descriptor in targets:
                    hidden_definitions.append(f"{name}: {descriptor}")
                if descriptor in sources:
                    old_definitions.add(descriptor)
                refs = []
                for code_off in walk_class_data(dex, class_data_off):
                    refs.extend(walk_code_item(dex, code_off))
                if static_values_off:
                    refs.extend(dex.encoded_array_refs(static_values_off))
                insn_ref_total += len(refs)
                for ref in refs:
                    if ref in targets:
                        hidden_target_refs.add((descriptor, ref))
                    elif ref in sources:
                        old_ref_total += 1
                        if descriptor == ref:
                            # Self-reference: resolves to this APK's own
                            # dead-shell definition. The only allowed shape.
                            self_refs.add((descriptor, ref))
                        else:
                            old_owner_violations.append(
                                f"{name}: {descriptor} -> {ref} "
                                "(old-owner reference; only self-references are allowed)"
                            )
            if full:
                for s in dex._strings:
                    if s in sources or s in targets:
                        string_mentions.add((name, s))

    if hidden_definitions:
        violations.extend(f"HIDDEN DEFINITION {d}" for d in hidden_definitions)
    violations.extend(old_owner_violations)
    return {
        "dex_count": dex_count,
        "class_count": class_count,
        "insn_ref_total": insn_ref_total,
        "old_ref_total": old_ref_total,
        "self_ref_count": len(self_refs),
        "violations": violations,
        "old_owner_violations": old_owner_violations,
        "self_refs": sorted(self_refs),
        "hidden_target_refs": sorted(hidden_target_refs),
        "hidden_definitions": hidden_definitions,
        "old_definitions": sorted(old_definitions),
        "string_mentions": sorted(string_mentions) if full else None,
    }


def print_report(result: dict) -> None:
    print(f"dex files scanned:      {result['dex_count']}")
    print(f"classes defined:        {result['class_count']}")
    print(f"instruction refs total: {result['insn_ref_total']}")
    print(f"old-owner instruction refs: {result['old_ref_total']}")
    print(f"  self-reference residuals (allowed dead shells): {result['self_ref_count']}")
    print(f"  VIOLATIONS:           {len(result['violations'])}")
    for v in result["violations"][:60]:
        print(f"    {v}")
    if len(result["violations"]) > 60:
        print(f"    ... and {len(result['violations']) - 60} more")
    print(f"hidden-target instruction refs (expected after rewrite): {len(result['hidden_target_refs'])}")
    print(f"hidden-target definitions in APK: {len(result['hidden_definitions'])}")
    print(f"old-name classes defined in APK (dead shells): {len(result['old_definitions'])}")
    if result["string_mentions"] is not None:
        print(f"string constants mentioning old/hidden names (informational): {len(result['string_mentions'])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--rules", type=Path, default=None)
    parser.add_argument("--full", action="store_true", help="also report string-pool mentions")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    rules_path = args.rules if args.rules else repo_root / DEFAULT_RULES
    try:
        rules = load_rules(rules_path)
    except (OSError, ValueError, GateError) as e:
        print(f"GATE ERROR: {e}", file=sys.stderr)
        return 2
    if not args.apk.is_file():
        print(f"GATE ERROR: APK not found: {args.apk}", file=sys.stderr)
        return 2

    try:
        result = scan_apk(args.apk, rules, full=args.full)
    except (GateError, zipfile.BadZipFile, struct.error) as e:
        print(f"GATE ERROR: {e}", file=sys.stderr)
        return 2

    print(f"APK: {args.apk}")
    print(f"rules: {len(rules)} exact renames from {rules_path}")
    print_report(result)
    if result["violations"]:
        print("RESULT=FAIL")
        return 1
    print("RESULT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
