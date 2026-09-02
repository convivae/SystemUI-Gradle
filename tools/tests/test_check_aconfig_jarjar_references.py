#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/check_aconfig_jarjar_references.py (Task 099 C5).

Instruction-level gate semantics (725-rule full repackaging authority):
the synthetic DEX builder emits real class_data/code_items so the walker's
opcode-level extraction is exercised, while no real APK or external package
is needed. Real-APK validation is recorded separately in the Task 099 issue
doc (frozen Debug/Release RED gates cross-checked against dexdump scans).
"""

import hashlib
import importlib.util
import io
import struct
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "check_aconfig_jarjar_references.py"
_spec = importlib.util.spec_from_file_location("check_aconfig_jarjar_references", _SCRIPT)
cj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cj)


def _uleb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _sleb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        done = (value == 0 and not (byte & 0x40)) or (value == -1 and (byte & 0x40))
        if not done:
            byte |= 0x80
        out.append(byte)
        if done:
            return bytes(out)


def make_code(insns, tries=(), handlers=b"", registers=4, outs=0):
    """Serialize one code_item (k layout the walker expects)."""
    insns = list(insns)
    body = bytearray()
    body += struct.pack("<HHHH", registers, 1, outs, len(tries))
    body += struct.pack("<I", 0)  # debug_info_off
    body += struct.pack("<I", len(insns))
    for unit in insns:
        body += struct.pack("<H", unit)
    if len(insns) % 2:
        body += b"\x00\x00"  # 4-byte alignment padding
    for start_addr, insn_count, handler_off in tries:
        body += struct.pack("<IHH", start_addr, insn_count, handler_off)
    body += handlers
    return bytes(body)


def const_string(string_idx, reg=0):
    return [0x1A | (reg << 8), string_idx]


def check_cast(type_idx, reg=0):
    return [0x1F | (reg << 8), type_idx]


def sget_boolean(field_idx, reg=0):
    return [0x53 | (reg << 8), field_idx]


def invoke_static(method_idx):
    return [0x71, method_idx, 0]


RETURN_VOID = [0x0E]


class DexBuilder:
    """Minimal structural DEX builder: ids tables + class_defs + real code."""

    def __init__(self):
        self._strings = []
        self._smap = {}
        self._types = []
        self._tmap = {}
        self._protos = []  # (return_desc, tuple(param_descs))
        self._pmap = {}
        self._fields = []  # (owner_desc, type_desc, name)
        self._fmap = {}
        self._methods = []  # (owner_desc, proto_idx, name)
        self._mmap = {}
        self._classes = []  # (desc, [(method_idx, code_bytes)], [static value type descs])

    def string(self, s: str) -> int:
        if s not in self._smap:
            self._smap[s] = len(self._strings)
            self._strings.append(s)
        return self._smap[s]

    def type(self, descriptor: str) -> int:
        if descriptor not in self._tmap:
            self._tmap[descriptor] = len(self._types)
            self._types.append(descriptor)
            self.string(descriptor)
        return self._tmap[descriptor]

    def proto(self, ret="V", params=()) -> int:
        key = (ret, tuple(params))
        if key not in self._pmap:
            self._pmap[key] = len(self._protos)
            self._protos.append(key)
            self.type(ret)
            for p in params:
                self.type(p)
            self.string(ret[0] + "".join(p[0] for p in params))  # shorty
        return self._pmap[key]

    def field(self, owner, ftype, name) -> int:
        self.type(owner)
        self.type(ftype)
        self.string(name)
        key = (owner, ftype, name)
        if key not in self._fmap:
            self._fmap[key] = len(self._fields)
            self._fields.append(key)
        return self._fmap[key]

    def method(self, owner, name, ret="V", params=()) -> int:
        proto_idx = self.proto(ret, params)
        self.type(owner)
        self.string(name)
        key = (owner, proto_idx, name)
        if key not in self._mmap:
            self._mmap[key] = len(self._methods)
            self._methods.append(key)
        return self._mmap[key]

    def define_class(self, descriptor, codes=(), static_value_types=()):
        """codes: [(method_idx, code_item_bytes)]; static_value_types: descs."""
        self.type(descriptor)
        for t in static_value_types:
            self.type(t)
        self._classes.append((descriptor, list(codes), list(static_value_types)))

    def build(self) -> bytes:
        header_size = 112
        string_ids_off = header_size
        type_ids_off = string_ids_off + 4 * len(self._strings)
        proto_ids_off = type_ids_off + 4 * len(self._types)
        field_ids_off = proto_ids_off + 12 * len(self._protos)
        method_ids_off = field_ids_off + 8 * len(self._fields)
        class_defs_off = method_ids_off + 8 * len(self._methods)
        data_off = class_defs_off + 32 * len(self._classes)

        data = bytearray()
        string_data_offs = []
        for s in self._strings:
            string_data_offs.append(data_off + len(data))
            data += _uleb128(len(s.encode("utf-8"))) + s.encode("utf-8") + b"\x00"

        proto_params_offs = []
        for _ret, params in self._protos:
            if params:
                proto_params_offs.append(data_off + len(data))
                data += struct.pack("<I", len(params))
                data += struct.pack("<" + "H" * len(params), *(self._tmap[p] for p in params))
            else:
                proto_params_offs.append(0)

        class_records = []  # (type_idx, class_data_off, static_values_off)
        for descriptor, codes, static_types in self._classes:
            code_offs = []
            for _midx, payload in codes:
                code_offs.append(data_off + len(data))
                data += payload
            class_data_off = data_off + len(data)
            cd = bytearray()
            cd += _uleb128(0) + _uleb128(0)  # static/instance fields
            cd += _uleb128(len(codes)) + _uleb128(0)  # direct/virtual methods
            prev = 0
            for (midx, _payload), coff in zip(codes, code_offs):
                cd += _uleb128(midx - prev) + _uleb128(1) + _uleb128(coff)
                prev = midx
            data += cd
            static_values_off = 0
            if static_types:
                static_values_off = data_off + len(data)
                data += _uleb128(len(static_types))
                for t in static_types:
                    # encoded_value: type tag 0x18, value_arg 0 -> one-byte idx
                    data += bytes([0x18]) + struct.pack("<B", self._tmap[t])
            class_records.append((self._tmap[descriptor], class_data_off, static_values_off))

        out = bytearray()
        out += b"dex\n035\x00"
        out += b"\x00" * 24  # checksum + signature (walker ignores)
        out += struct.pack("<II", 0, header_size)  # file_size patched below
        out += struct.pack("<I", 0x12345678)  # endian tag
        out += struct.pack("<III", 0, 0, 0)  # link_size, link_off, map_off
        out += struct.pack("<II", len(self._strings), string_ids_off)
        out += struct.pack("<II", len(self._types), type_ids_off)
        out += struct.pack("<II", len(self._protos), proto_ids_off)
        out += struct.pack("<II", len(self._fields), field_ids_off)
        out += struct.pack("<II", len(self._methods), method_ids_off)
        out += struct.pack("<II", len(self._classes), class_defs_off)
        out += struct.pack("<II", len(data), data_off)
        assert len(out) == header_size
        for off in string_data_offs:
            out += struct.pack("<I", off)
        for t in self._types:
            out += struct.pack("<I", self._smap[t])
        for ret, params in self._protos:
            shorty = ret[0] + "".join(p[0] for p in params)
            out += struct.pack(
                "<III", self._smap[shorty], self._tmap[ret],
                proto_params_offs[self._pmap[(ret, tuple(params))]],
            )
        for owner, ftype, name in self._fields:
            out += struct.pack("<HHI", self._tmap[owner], self._tmap[ftype], self._smap[name])
        for owner, proto_idx, name in self._methods:
            out += struct.pack("<HHI", self._tmap[owner], proto_idx, self._smap[name])
        for type_idx, class_data_off, static_values_off in class_records:
            out += struct.pack("<IIIIIIII", type_idx, 1, 0, 0, 0, 0, class_data_off, static_values_off)
        out += data
        struct.pack_into("<I", out, 32, len(out))
        return bytes(out)


OLD_APP_FLAGS = "android.app.Flags"
OLD_OS_FLAGS = "android.os.Flags"
HIDDEN_APP = "com.android.internal.hidden_from_bootclasspath.android.app.Flags"
HIDDEN_OS = "com.android.internal.hidden_from_bootclasspath.android.os.Flags"

RULES_TEXT = (
    f"rule {OLD_APP_FLAGS} {HIDDEN_APP}\n"
    f"rule {OLD_OS_FLAGS} {HIDDEN_OS}\n"
)


def desc(fqcn: str) -> str:
    return cj.fqcn_to_descriptor(fqcn)


class TestRuleParsing(unittest.TestCase):
    def test_exact_rules_parse(self):
        rules = cj.parse_rules("rule a.b.C x.y.C\n\nrule a.b.D x.y.D\n")
        self.assertEqual(rules, [("a.b.C", "x.y.C"), ("a.b.D", "x.y.D")])

    def test_exact_duplicate_is_tolerated(self):
        rules = cj.parse_rules("rule a.b.C x.y.C\nrule a.b.C x.y.C\n")
        self.assertEqual(rules, [("a.b.C", "x.y.C")])

    def test_conflicting_duplicate_is_error(self):
        with self.assertRaises(ValueError):
            cj.parse_rules("rule a.b.C x.y.C\nrule a.b.C x.y.Z\n")

    def test_wildcard_is_rejected(self):
        with self.assertRaises(ValueError):
            cj.parse_rules("rule android.app.* com.foo.*\n")

    def test_zap_and_keep_are_rejected(self):
        for line in ("zap android.app.Flags", "keep android.app.Flags"):
            with self.assertRaises(ValueError):
                cj.parse_rules(line + "\n")

    def test_identity_rule_is_rejected(self):
        with self.assertRaises(ValueError):
            cj.parse_rules("rule a.b.C a.b.C\n")

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            cj.parse_rules("\n# only a comment\n")


class TestRulesFileHandling(unittest.TestCase):
    def test_frozen_rules_file_drift_is_error(self):
        # A file with the canonical frozen NAME but drifted content must be
        # rejected (sha256/count pin), even before the gate scans any dex.
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / cj.DEFAULT_RULES.split("/")[-1]
            rules.write_text("rule a.b.C x.y.C\n")
            with self.assertRaises(cj.GateError):
                cj.load_rules(rules)

    def test_frozen_rules_file_exact_bytes_pass(self):
        repo_rules = Path(__file__).resolve().parents[2] / cj.DEFAULT_RULES
        rules = cj.load_rules(repo_rules)
        self.assertEqual(len(rules), cj.RULE_COUNT)
        digest = hashlib.sha256(repo_rules.read_bytes()).hexdigest()
        self.assertEqual(digest, cj.RULES_SHA256)

    def test_custom_named_rules_file_is_free_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "rules.txt"
            rules.write_text("rule a.b.C x.y.C\n")
            self.assertEqual(cj.load_rules(rules), [("a.b.C", "x.y.C")])

    def test_invalid_utf8_rules_file_is_clean_exit_2(self):
        dex = DexBuilder().build()
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "test.apk"
            rules = Path(tmp) / "rules.txt"
            with zipfile.ZipFile(apk, "w") as zf:
                zf.writestr("classes.dex", dex)
            rules.write_bytes(b"rule a.b.C x.y.C\nrule \xff\xfe broken\n")
            buf, errbuf = io.StringIO(), io.StringIO()
            with redirect_stdout(buf), redirect_stderr(errbuf):
                rc = cj.main(["--apk", str(apk), "--rules", str(rules)])
        self.assertEqual(rc, 2)
        self.assertIn("GATE ERROR", errbuf.getvalue())


class TestDexParsing(unittest.TestCase):
    def test_valid_dex_roundtrip(self):
        b = DexBuilder()
        b.define_class("La/b/C;")
        dex = b.build()
        parsed = cj.Dex(dex, "classes.dex")
        self.assertEqual([d for d, _, _ in parsed.class_defs], ["La/b/C;"])
        self.assertEqual(parsed.defined, {"La/b/C;"})

    def test_bad_magic_raises(self):
        with self.assertRaises(cj.GateError):
            cj.Dex(b"\x00" * 200, "classes.dex")

    def test_compact_dex_magic_raises(self):
        with self.assertRaises(cj.GateError):
            cj.Dex(b"cdex001\x00" + b"\x00" * 200, "classes.dex")

    def test_truncated_header_raises(self):
        with self.assertRaises(cj.GateError):
            cj.Dex(b"dex\n035\x00" + b"\x00" * 40, "classes.dex")

    def test_bad_endian_tag_raises(self):
        b = DexBuilder()
        dex = bytearray(b.build())
        struct.pack_into("<I", dex, 40, 0xDEADBEEF)
        with self.assertRaises(cj.GateError):
            cj.Dex(bytes(dex), "classes.dex")

    def test_uleb128_maximal_five_bytes(self):
        d = object.__new__(cj.Dex)
        d.blob = b"\xff\xff\xff\xff\x0f"
        value, off = d.read_uleb(0)
        self.assertEqual(value, 0xFFFFFFFF)
        self.assertEqual(off, 5)

    def test_sleb128_negative_roundtrip(self):
        d = object.__new__(cj.Dex)
        for value in (-1, -64, -8192, -1234567):
            d.blob = _sleb128(value)
            parsed, off = d.read_sleb(0)
            self.assertEqual(parsed, value)
            self.assertEqual(off, len(d.blob))

    def test_non_dex_zip_member_only_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "a.apk"
            with zipfile.ZipFile(apk, "w") as zf:
                zf.writestr("AndroidManifest.xml", b"junk-not-a-dex")
            with self.assertRaises(cj.GateError):
                cj.scan_apk(apk, [])


class GateHarness(unittest.TestCase):
    def run_gate(self, dexes, rules_text=RULES_TEXT, full=False):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "test.apk"
            rules = Path(tmp) / "rules.txt"
            with zipfile.ZipFile(apk, "w") as zf:
                for name, data in dexes:
                    zf.writestr(name, data)
            rules.write_text(rules_text)
            result = cj.scan_apk(apk, cj.parse_rules(rules_text), full=full)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cj.main(["--apk", str(apk), "--rules", str(rules)] + (["--full"] if full else []))
        return rc, buf.getvalue(), result


class TestGateSemantics(GateHarness):
    def test_clean_apk_passes(self):
        b = DexBuilder()
        m = b.method("Lcom/example/Caller;", "call")
        b.define_class("Lcom/example/Caller;", codes=[(m, make_code(invoke_static(m) + RETURN_VOID))])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 0)
        self.assertIn("RESULT=PASS", out)
        self.assertEqual(result["violations"], [])

    def test_old_owner_reference_from_any_other_class_fails(self):
        # Chief decision (Task 099): only self-references are allowed. A
        # caller that differs from the referenced old class FAILs, regardless
        # of whether the old class is defined in the APK (dead shell) or not
        # (unresolvable) -- sibling and external callers must be rewritten.
        b = DexBuilder()
        f = b.field(desc(OLD_APP_FLAGS), "Z", "FLAG")
        m = b.method("Lcom/example/Lambda0;", "test")
        b.define_class(desc(OLD_APP_FLAGS))  # APK-defined old name (dead shell)
        b.define_class("Lcom/example/Lambda0;", codes=[
            (m, make_code(sget_boolean(f) + [0x0A] + RETURN_VOID))  # 0x0A move-result
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertIn("RESULT=FAIL", out)
        self.assertEqual(result["old_ref_total"], 1)
        self.assertEqual(len(result["old_owner_violations"]), 1)
        self.assertIn("only self-references are allowed", out)

    def test_source_class_referencing_itself_is_allowed(self):
        # A rule-source class referencing its own old name: resolves to the
        # APK's own dead-shell definition. The only allowed residual.
        b = DexBuilder()
        f = b.field(desc(OLD_APP_FLAGS), "Z", "FLAG")
        m = b.method(desc(OLD_APP_FLAGS), "enabled")
        b.define_class(desc(OLD_APP_FLAGS), codes=[
            (m, make_code(sget_boolean(f) + [0x0A] + RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 0)
        self.assertIn("RESULT=PASS", out)
        self.assertEqual(result["old_ref_total"], 1)
        self.assertEqual(result["self_refs"], [(desc(OLD_APP_FLAGS), desc(OLD_APP_FLAGS))])
        self.assertEqual(result["violations"], [])

    def test_sibling_old_owner_reference_from_source_class_fails(self):
        # A rule-source caller referencing a DIFFERENT old name FAILs: under
        # the instrument-everything design, sibling refs must be rewritten to
        # the hidden twins (this is the fix for the D8-synthesized lambda
        # residuals observed in the 2026-09-03 Debug build).
        b = DexBuilder()
        f = b.field(desc(OLD_APP_FLAGS), "Z", "FLAG")
        m = b.method(desc(OLD_OS_FLAGS), "enabled")
        b.define_class(desc(OLD_APP_FLAGS))
        b.define_class(desc(OLD_OS_FLAGS), codes=[
            (m, make_code(sget_boolean(f) + [0x0A] + RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertIn("RESULT=FAIL", out)
        self.assertEqual(result["old_ref_total"], 1)
        self.assertEqual(len(result["old_owner_violations"]), 1)

    def test_hidden_target_definition_in_apk_fails(self):
        b = DexBuilder()
        m = b.method(desc(HIDDEN_APP), "enabled")
        b.define_class(desc(HIDDEN_APP), codes=[
            (m, make_code(RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertIn("RESULT=FAIL", out)
        self.assertTrue(any("HIDDEN DEFINITION" in v for v in result["violations"]))

    def test_post_rewrite_shape_passes(self):
        # The GREEN shape: callers reference the hidden targets (defined on
        # the device framework, not in the APK) and the only old-owner
        # residuals are self-references.
        b = DexBuilder()
        f = b.field(desc(HIDDEN_APP), "Z", "FLAG")
        m = b.method("Lcom/example/Caller;", "call")
        self_sf = b.field(desc(OLD_APP_FLAGS), "Z", "SELF")
        self_m = b.method(desc(OLD_APP_FLAGS), "self")
        b.define_class("Lcom/example/Caller;", codes=[
            (m, make_code(sget_boolean(f) + [0x0A] + RETURN_VOID))
        ])
        b.define_class(desc(OLD_APP_FLAGS), codes=[
            (self_m, make_code(sget_boolean(self_sf) + [0x0A] + RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 0)
        self.assertIn("RESULT=PASS", out)
        self.assertEqual(result["hidden_target_refs"], [("Lcom/example/Caller;", desc(HIDDEN_APP))])
        self.assertEqual(result["old_ref_total"], 1)
        self.assertEqual(result["self_ref_count"], 1)

    def test_string_constant_is_not_a_violation(self):
        # const-string with the exact old-name text is informational only:
        # strings never rewrite and must not FAIL the gate.
        b = DexBuilder()
        s = b.string("plain text mentioning android.app.Flags")
        m = b.method("Lcom/example/Caller;", "call")
        b.define_class("Lcom/example/Caller;", codes=[
            (m, make_code(const_string(s) + [0x0A] + RETURN_VOID))  # 0x0A move-result
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())], full=True)
        self.assertEqual(rc, 0)
        self.assertIn("RESULT=PASS", out)
        self.assertIn("string constants mentioning old/hidden names (informational)", out)

    def test_multidex_sibling_ref_from_later_dex_fails(self):
        b1 = DexBuilder()
        b1.define_class(desc(OLD_APP_FLAGS))
        b2 = DexBuilder()
        f = b2.field(desc(OLD_APP_FLAGS), "Z", "FLAG")
        m = b2.method("Lcom/example/LateCaller;", "call")
        b2.define_class("Lcom/example/LateCaller;", codes=[
            (m, make_code(sget_boolean(f) + [0x0A] + RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b1.build()), ("classes2.dex", b2.build())])
        self.assertEqual(rc, 1)
        self.assertEqual(len(result["old_owner_violations"]), 1)


class TestWalkerCoverage(GateHarness):
    def test_invoke_static_counts_owner_and_proto_types(self):
        # invoke-static refs = [owner] + [param types...] + [return type].
        b = DexBuilder()
        m = b.method(desc(OLD_APP_FLAGS), "enabled", ret="V", params=(desc(OLD_OS_FLAGS),))
        caller = b.method("Lcom/example/Caller;", "call")
        b.define_class("Lcom/example/Caller;", codes=[
            (caller, make_code(invoke_static(m) + RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertEqual(result["old_ref_total"], 2)  # owner + param type

    def test_catch_handler_type_is_counted(self):
        b = DexBuilder()
        exc = b.type(desc(OLD_APP_FLAGS))
        m = b.method("Lcom/example/Caller;", "call")
        handlers = _uleb128(1) + _sleb128(1) + _uleb128(exc) + _uleb128(0)
        b.define_class("Lcom/example/Caller;", codes=[
            (m, make_code(
                RETURN_VOID,
                tries=[(0, 1, 0)],
                handlers=handlers,
            ))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertEqual(result["old_ref_total"], 1)
        self.assertEqual(len(result["old_owner_violations"]), 1)

    def test_static_values_encoded_array_is_counted(self):
        # Class-init constants: static_values type refs are executable state.
        b = DexBuilder()
        m = b.method("Lcom/example/Holder;", "x")
        b.define_class("Lcom/example/Holder;", codes=[(m, make_code(RETURN_VOID))],
                       static_value_types=[desc(OLD_APP_FLAGS)])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertEqual(result["old_ref_total"], 1)

    def test_check_cast_counts_type_ref(self):
        b = DexBuilder()
        t = b.type(desc(OLD_APP_FLAGS))
        m = b.method("Lcom/example/Caller;", "call")
        b.define_class("Lcom/example/Caller;", codes=[
            (m, make_code(check_cast(t) + RETURN_VOID))
        ])
        rc, out, result = self.run_gate([("classes.dex", b.build())])
        self.assertEqual(rc, 1)
        self.assertEqual(result["old_ref_total"], 1)


class TestMainEntrypoint(unittest.TestCase):
    def test_missing_apk_is_clean_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "rules.txt"
            rules.write_text("rule a.b.C x.y.C\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cj.main(["--apk", str(Path(tmp) / "nope.apk"), "--rules", str(rules)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
