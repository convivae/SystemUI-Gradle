#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static gate for the AOSP-17 platform aconfig jarjar closure (Task 078).

AOSP 17 rewrites a set of framework aconfig classes (``android.app.Flags``,
``android.os.Flags``, ...) into ``com.android.internal.hidden_from_bootclasspath.*``
via Soong jarjar before they land on the device boot classpath. Stock SystemUI
DEX therefore references the relocated descriptors, while a Gradle-built
Release APK that compiled against the original names still references -- and
possibly defines -- the originals, which breaks at runtime.

This tool reads the DEX type tables of every ``classes*.dex`` entry in an APK
and checks them against the authoritative Soong ``repackaging.txt``:

* "referenced"  == descriptor appears in a DEX ``type_ids`` table
                   (the dex references the type somewhere: field/method/
                   annotation/definition), and
* "defined"     == descriptor appears as a ``class_def`` in some DEX
                   (the class implementation ships inside the APK).

Gate semantics (frozen, Task 078): the four runtime-critical sources must be
absent (not referenced at all) and their relocated targets must be present
(referenced). Additionally, no target descriptor of the full rule set may be
defined inside the APK: a defined relocated target means a platform class
(the device framework's own) is shipped as program code, so the gate cannot
be satisfied by packaging the hidden definitions (critical targets are a
subset of this full-set check). The full rule file is additionally scanned
and reported as stable totals, but the source-side full-rule numbers are
diagnostics only -- the "all 725 rule sources must be absent" assertion is
intentionally NOT encoded: stock AOSP legitimately defines app-owned
originals (e.g. ``android.app.admin.flags.FeatureFlagsImpl``), and such
definitions also appear in type_ids.

Exit codes: 0 = PASS, 1 = RESULT=FAIL, 2 = usage/parse/DEX error.

Usage:
    uv run python tools/check_aconfig_jarjar_references.py \
        --apk <apk> --rules <repackaging.txt>
"""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
import zipfile
from pathlib import Path

# Frozen runtime-critical source classes (Task 078 brief). Do not weaken.
CRITICAL_SOURCES = (
    "android.app.Flags",
    "android.os.Flags",
    "android.view.accessibility.Flags",
    "com.android.window.flags.Flags",
)

_DEX_ENTRY_RE = re.compile(r"^classes\d*\.dex$")
_DEX_VERSIONS = (b"035", b"036", b"037", b"038", b"039")
_HEADER_SIZE = 112
_VALID_FQCN_RE = re.compile(r"^[A-Za-z0-9_$]+(?:\.[A-Za-z0-9_$]+)*$")


class RulesError(Exception):
    """The rules file cannot be interpreted exactly."""


class DexError(Exception):
    """A DEX entry is malformed."""


# ---------------------------------------------------------------------------
# Rule parsing
# ---------------------------------------------------------------------------


def parse_rules(text: str) -> list[tuple[str, str]]:
    """Parse ``rule <source> <target>`` entries.

    Only exact (non-wildcard) class rename rules are supported; ``zap``/``keep``
    directives and wildcard syntax are rejected loudly instead of being
    silently misinterpreted. Exact duplicate lines are tolerated; conflicting
    duplicate sources are an error.
    """
    seen: dict[str, str] = {}
    order: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if tokens[0] in ("zap", "keep"):
            raise RulesError(f"line {lineno}: unsupported directive {tokens[0]!r}")
        if tokens[0] != "rule":
            raise RulesError(f"line {lineno}: expected 'rule <source> <target>', got {line!r}")
        if len(tokens) != 3:
            raise RulesError(f"line {lineno}: expected 'rule <source> <target>', got {line!r}")
        source, target = tokens[1], tokens[2]
        for name in (source, target):
            if "*" in name or "?" in name:
                raise RulesError(
                    f"line {lineno}: wildcard syntax not supported (would not "
                    f"match exactly one descriptor): {line!r}"
                )
            if not _VALID_FQCN_RE.match(name):
                raise RulesError(f"line {lineno}: not a plain fully-qualified class name: {name!r}")
        if source in seen:
            if seen[source] != target:
                raise RulesError(f"line {lineno}: conflicting duplicate rule for source {source!r}")
            continue
        seen[source] = target
        order.append(source)
    if not seen:
        raise RulesError("no rule entries found")
    return [(source, seen[source]) for source in order]


def fqcn_to_descriptor(name: str) -> str:
    """``a.b.C`` -> ``La/b/C;`` (plain class only; no arrays/primitives here)."""
    return "L" + name.replace(".", "/") + ";"


# ---------------------------------------------------------------------------
# Minimal DEX reader (stdlib only)
# ---------------------------------------------------------------------------


def _read_uleb128(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise DexError("truncated uleb128")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, offset
        shift += 7
        if shift >= 35:
            # A uleb128 encodes at most 32 bits => at most 5 bytes.
            raise DexError("uleb128 exceeds 5 bytes")


def _decode_mutf8(raw: bytes) -> str:
    """Decode MUTF-8 bytes (without the trailing NUL).

    Descriptors of interest are plain ASCII, so strict UTF-8 succeeds for
    them; anything exotic (CESU-8 surrogate pairs) degrades lossily without
    affecting exact descriptor matching.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


class DexInfo:
    """Type table (referenced) and class definitions of one DEX entry."""

    def __init__(self, entry: str, referenced: set[str], defined: set[str]):
        self.entry = entry
        self.referenced = referenced
        self.defined = defined


def parse_dex(data: bytes, entry: str) -> DexInfo:
    if len(data) < _HEADER_SIZE:
        raise DexError(f"{entry}: shorter than a DEX header ({len(data)} bytes)")
    if data[:4] != b"dex\n":
        raise DexError(f"{entry}: bad magic {data[:8]!r} (compact dex is not supported)")
    if data[4:7] not in _DEX_VERSIONS:
        raise DexError(f"{entry}: unsupported DEX version {data[4:7]!r}")
    (
        file_size,
        header_size,
        endian_tag,
        _link_size,
        _link_off,
        _map_off,
        string_ids_size,
        string_ids_off,
        type_ids_size,
        type_ids_off,
        _proto_ids_size,
        _proto_ids_off,
        _field_ids_size,
        _field_ids_off,
        _method_ids_size,
        _method_ids_off,
        class_defs_size,
        class_defs_off,
        _data_size,
        _data_off,
    ) = struct.unpack_from("<20I", data, 32)
    if endian_tag != 0x12345678:
        raise DexError(f"{entry}: unexpected endian tag 0x{endian_tag:08x}")
    if header_size < _HEADER_SIZE:
        raise DexError(f"{entry}: header_size {header_size} too small")
    if file_size != len(data):
        raise DexError(f"{entry}: file_size {file_size} != entry size {len(data)}")

    def _check(offset: int, count: int, item_size: int, what: str) -> None:
        if offset + count * item_size > len(data):
            raise DexError(f"{entry}: {what} table out of bounds (off={offset}, size={count})")

    # String table.
    _check(string_ids_off, string_ids_size, 4, "string_ids")
    strings: list[str] = []
    for i in range(string_ids_size):
        (str_off,) = struct.unpack_from("<I", data, string_ids_off + 4 * i)
        if str_off >= len(data):
            raise DexError(f"{entry}: string {i} offset out of bounds")
        _utf16_len, pos = _read_uleb128(data, str_off)
        nul = data.find(b"\x00", pos)
        if nul < 0:
            raise DexError(f"{entry}: string {i} not NUL-terminated")
        strings.append(_decode_mutf8(data[pos:nul]))

    # Type table: every type the DEX references anywhere.
    _check(type_ids_off, type_ids_size, 4, "type_ids")
    referenced: set[str] = set()
    for i in range(type_ids_size):
        (str_idx,) = struct.unpack_from("<I", data, type_ids_off + 4 * i)
        if str_idx >= len(strings):
            raise DexError(f"{entry}: type {i} references string {str_idx} out of range")
        referenced.add(strings[str_idx])

    # Class definitions: classes implemented inside this DEX.
    _check(class_defs_off, class_defs_size, 32, "class_defs")
    defined: set[str] = set()
    for i in range(class_defs_size):
        (class_idx,) = struct.unpack_from("<I", data, class_defs_off + 32 * i)
        if class_idx >= type_ids_size:
            raise DexError(f"{entry}: class_def {i} type index out of range")
        (str_idx,) = struct.unpack_from("<I", data, type_ids_off + 4 * class_idx)
        defined.add(strings[str_idx])

    return DexInfo(entry, referenced, defined)


def scan_apk(apk: Path) -> list[DexInfo]:
    """Parse every ``classes*.dex`` entry of an APK, in stable order."""
    if not apk.is_file():
        raise DexError(f"APK not found: {apk}")
    dexes: list[DexInfo] = []
    with zipfile.ZipFile(apk) as zf:
        for info in zf.infolist():
            if not _DEX_ENTRY_RE.match(info.filename):
                continue
            dexes.append(parse_dex(zf.read(info), info.filename))
    if not dexes:
        raise DexError(f"no classes*.dex entries found in {apk}")
    return sorted(dexes, key=lambda d: d.entry)


# ---------------------------------------------------------------------------
# Evaluation and reporting
# ---------------------------------------------------------------------------


def _descriptor_dexes(dexes: list[DexInfo], descriptor: str, table: str) -> list[str]:
    attr = "referenced" if table == "referenced" else "defined"
    return [d.entry for d in dexes if descriptor in getattr(d, attr)]


def evaluate(dexes: list[DexInfo], rules: list[tuple[str, str]]) -> dict:
    """Compute per-rule and critical-pair results against the APK DEX union."""
    referenced_union: set[str] = set()
    defined_union: set[str] = set()
    for d in dexes:
        referenced_union |= d.referenced
        defined_union |= d.defined

    per_rule = []
    for source, target in rules:
        src_desc = fqcn_to_descriptor(source)
        tgt_desc = fqcn_to_descriptor(target)
        per_rule.append(
            {
                "source": source,
                "target": target,
                "src_ref": src_desc in referenced_union,
                "src_def": src_desc in defined_union,
                "tgt_ref": tgt_desc in referenced_union,
                "tgt_def": tgt_desc in defined_union,
            }
        )
    rule_map = dict(rules)
    critical = []
    for source in CRITICAL_SOURCES:
        if source not in rule_map:
            raise RulesError(f"critical source {source!r} has no rule in the rules file")
        target = rule_map[source]
        entry = next(r for r in per_rule if r["source"] == source)
        entry["critical"] = True
        src_desc = fqcn_to_descriptor(source)
        tgt_desc = fqcn_to_descriptor(target)
        critical.append(
            {
                "source": source,
                "target": target,
                "src_ref": entry["src_ref"],
                "src_def": entry["src_def"],
                "src_ref_dexes": _descriptor_dexes(dexes, src_desc, "referenced"),
                "src_def_dexes": _descriptor_dexes(dexes, src_desc, "defined"),
                "tgt_ref": entry["tgt_ref"],
                "tgt_def": entry["tgt_def"],
                "tgt_ref_dexes": _descriptor_dexes(dexes, tgt_desc, "referenced"),
                "tgt_def_dexes": _descriptor_dexes(dexes, tgt_desc, "defined"),
            }
        )
    return {"per_rule": per_rule, "critical": critical}


def _fmt_flag(flag: bool) -> str:
    return "yes" if flag else "no"


def run_gate(apk: Path, rules_path: Path, out=None) -> int:
    """Execute the gate; return the process exit code (0/1/2)."""
    if out is None:
        out = sys.stdout
    try:
        rules_raw = rules_path.read_bytes()
    except OSError as exc:
        print(f"ERROR: cannot read rules file {rules_path}: {exc}", file=out)
        return 2
    try:
        rules_text = rules_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"ERROR: {rules_path}: rules file is not valid UTF-8: {exc}", file=out)
        return 2
    try:
        rules = parse_rules(rules_text)
    except RulesError as exc:
        print(f"ERROR: {rules_path}: {exc}", file=out)
        return 2
    try:
        dexes = scan_apk(apk)
    except (DexError, zipfile.BadZipFile, OSError) as exc:
        print(f"ERROR: {apk}: {exc}", file=out)
        return 2
    try:
        result = evaluate(dexes, rules)
    except RulesError as exc:
        print(f"ERROR: {exc}", file=out)
        return 2

    # Hash the raw file bytes exactly as frozen in the task evidence, not a
    # newline-normalized re-encoding of the parsed text.
    rules_sha = hashlib.sha256(rules_raw).hexdigest()
    print(f"apk: {apk}", file=out)
    print(f"rules: {rules_path} ({len(rules)} rule entries, sha256 {rules_sha})", file=out)
    print(f"dex entries: {', '.join(d.entry for d in dexes)}", file=out)
    print("", file=out)

    print("critical pairs:", file=out)
    for pair in result["critical"]:
        print(f"  {pair['source']} -> {pair['target']}", file=out)
        src_loc = f" dex={pair['src_ref_dexes']}" if pair["src_ref"] else ""
        tgt_loc = f" dex={pair['tgt_ref_dexes']}" if pair["tgt_ref"] else ""
        print(
            f"    source: referenced={_fmt_flag(pair['src_ref'])}"
            f" (defined={_fmt_flag(pair['src_def'])}){src_loc}",
            file=out,
        )
        print(
            f"    target: referenced={_fmt_flag(pair['tgt_ref'])}"
            f" (defined={_fmt_flag(pair['tgt_def'])}){tgt_loc}",
            file=out,
        )
    print("", file=out)

    per_rule = result["per_rule"]
    src_present = [r for r in per_rule if r["src_ref"]]
    tgt_present = [r for r in per_rule if r["tgt_ref"]]
    src_defined = [r for r in per_rule if r["src_def"]]
    tgt_defined = [r for r in per_rule if r["tgt_def"]]
    print("full-rule scan:", file=out)
    print(f"  rules={len(per_rule)}", file=out)
    print(
        f"  source descriptors referenced: {len(src_present)} (defined: {len(src_defined)})",
        file=out,
    )
    print(
        f"  target descriptors referenced: {len(tgt_present)} (defined: {len(tgt_defined)})",
        file=out,
    )
    for r in sorted(src_present, key=lambda r: r["source"]):
        defined = " (defined)" if r["src_def"] else ""
        print(f"    source-present: {r['source']}{defined}", file=out)
    for r in sorted(tgt_defined, key=lambda r: r["target"]):
        print(f"    target-defined: {r['target']}", file=out)
    print("", file=out)

    failed_sources = [p for p in result["critical"] if p["src_ref"]]
    missing_targets = [p for p in result["critical"] if not p["tgt_ref"]]
    # Hardened rule (second review): a relocated target defined inside the
    # APK means a platform class is shipped as program code. Any target of
    # the full rule set (critical targets are a subset) fails the gate, so
    # packaging the hidden definitions can never produce a PASS.
    defined_targets = tgt_defined
    if failed_sources or missing_targets or defined_targets:
        for p in failed_sources:
            print(f"FAIL: critical source is still referenced in the APK: {p['source']}", file=out)
        for p in missing_targets:
            print(f"FAIL: relocated target is not referenced in the APK: {p['target']}", file=out)
        for r in defined_targets:
            print(
                f"FAIL: relocated target is defined inside the APK (platform class shipped): "
                f"{r['target']}",
                file=out,
            )
        print("RESULT=FAIL", file=out)
        return 1
    print("RESULT=PASS", file=out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Static gate: check an APK's DEX type tables against the Soong "
            "framework jarjar repackaging rules (aconfig closure)."
        )
    )
    parser.add_argument("--apk", required=True, type=Path, help="APK to scan")
    parser.add_argument(
        "--rules",
        required=True,
        type=Path,
        help="Soong repackaging.txt (exact 'rule <source> <target>' entries)",
    )
    args = parser.parse_args(argv)
    return run_gate(args.apk, args.rules)


if __name__ == "__main__":
    sys.exit(main())
