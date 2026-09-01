#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/check_aconfig_jarjar_references.py (Task 078 P1).

Uses synthetic minimal DEX files built in-memory by a small builder (header +
string_ids + type_ids + class_defs + MUTF-8 blobs) so that no real APK or
external package is needed. The builder shares the layout assumptions of the
parser under test, so real-APK validation is done separately by the frozen
acceptance runs recorded in docs/issues/2026-09-01-c5-aconfig-jarjar-closure.md.
"""

import importlib.util
import io
import struct
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
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


def build_dex(type_descriptors, defined_descriptors=()) -> bytes:
    """Build a minimal but structurally valid DEX (version 035).

    ``type_descriptors`` populate the type_ids table (i.e. "referenced");
    ``defined_descriptors`` (must be a subset) additionally get class_defs.
    """
    types = list(dict.fromkeys(type_descriptors))
    defined = list(dict.fromkeys(defined_descriptors))
    for d in defined:
        if d not in types:
            raise ValueError(f"defined descriptor {d!r} missing from type table")
    strings = list(dict.fromkeys(types))

    header_size = 112
    string_ids_off = header_size
    string_ids_size = len(strings)
    type_ids_off = string_ids_off + 4 * string_ids_size
    type_ids_size = len(types)
    class_defs_off = type_ids_off + 4 * type_ids_size
    class_defs_size = len(defined)
    data_off = class_defs_off + 32 * class_defs_size

    blobs = []
    offsets = []
    cursor = data_off
    for s in strings:
        blob = _uleb128(len(s)) + s.encode("utf-8") + b"\x00"
        offsets.append(cursor)
        blobs.append(blob)
        cursor += len(blob)
    total = cursor

    out = bytearray(header_size)
    out[0:8] = b"dex\n035\x00"
    struct.pack_into(
        "<20I",
        out,
        32,
        total,  # file_size
        header_size,
        0x12345678,  # endian_tag
        0, 0, 0,  # link_size, link_off, map_off
        string_ids_size,
        string_ids_off,
        type_ids_size,
        type_ids_off,
        0, 0, 0, 0, 0, 0,  # proto/field/method ids
        class_defs_size,
        class_defs_off,
        total - data_off,  # data_size
        data_off,
    )
    for off in offsets:
        out += struct.pack("<I", off)
    for t in types:
        out += struct.pack("<I", strings.index(t))
    for d in defined:
        out += struct.pack("<I", types.index(d)) + b"\x00" * 28
    for blob in blobs:
        out += blob
    assert len(out) == total
    return bytes(out)


def target_desc(source: str) -> str:
    return cj.fqcn_to_descriptor("com.android.internal.hidden_from_bootclasspath." + source)


CRITICAL_TARGET_DESCS = [target_desc(s) for s in cj.CRITICAL_SOURCES]


def critical_rules_text() -> str:
    lines = [f"rule {s} com.android.internal.hidden_from_bootclasspath.{s}" for s in cj.CRITICAL_SOURCES]
    return "\n".join(lines) + "\n"


class TestRuleParsing(unittest.TestCase):
    def test_exact_rules_parse(self):
        rules = cj.parse_rules("rule a.b.C x.y.C\n\nrule a.b.D x.y.D\n")
        self.assertEqual(rules, [("a.b.C", "x.y.C"), ("a.b.D", "x.y.D")])

    def test_exact_duplicate_is_tolerated(self):
        rules = cj.parse_rules("rule a.b.C x.y.C\nrule a.b.C x.y.C\n")
        self.assertEqual(rules, [("a.b.C", "x.y.C")])

    def test_conflicting_duplicate_is_error(self):
        with self.assertRaises(cj.RulesError):
            cj.parse_rules("rule a.b.C x.y.C\nrule a.b.C x.y.Z\n")

    def test_wildcard_is_rejected(self):
        with self.assertRaises(cj.RulesError):
            cj.parse_rules("rule android.app.* com.foo.*\n")

    def test_zap_and_keep_are_rejected(self):
        for line in ("zap android.app.Flags", "keep android.app.Flags"):
            with self.assertRaises(cj.RulesError):
                cj.parse_rules(line + "\n")

    def test_bad_arity_is_rejected(self):
        with self.assertRaises(cj.RulesError):
            cj.parse_rules("rule a.b.C\n")

    def test_empty_is_rejected(self):
        with self.assertRaises(cj.RulesError):
            cj.parse_rules("\n# only a comment\n")


class TestDexParsing(unittest.TestCase):
    def test_valid_dex_roundtrip(self):
        dex = build_dex(["La/b/C;", "Lx/y/D;"], defined_descriptors=["La/b/C;"])
        info = cj.parse_dex(dex, "classes.dex")
        self.assertEqual(info.referenced, {"La/b/C;", "Lx/y/D;"})
        self.assertEqual(info.defined, {"La/b/C;"})

    def test_bad_magic_raises(self):
        with self.assertRaises(cj.DexError):
            cj.parse_dex(b"\x00" * 200, "classes.dex")

    def test_compact_dex_magic_raises(self):
        with self.assertRaises(cj.DexError):
            cj.parse_dex(b"cdex001\x00" + b"\x00" * 200, "classes.dex")

    def test_truncated_header_raises(self):
        with self.assertRaises(cj.DexError):
            cj.parse_dex(b"dex\n035\x00" + b"\x00" * 40, "classes.dex")

    def test_wrong_file_size_raises(self):
        dex = bytearray(build_dex(["La/b/C;"]))
        # Corrupt the file_size field (offset 32).
        struct.pack_into("<I", dex, 32, 4)
        with self.assertRaises(cj.DexError):
            cj.parse_dex(bytes(dex), "classes.dex")

    def test_non_dex_zip_member_is_skipped_and_empty_zip_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "a.apk"
            with zipfile.ZipFile(apk, "w") as zf:
                zf.writestr("AndroidManifest.xml", b"junk-not-a-dex")
            with self.assertRaises(cj.DexError):
                cj.scan_apk(apk)


class TestGate(unittest.TestCase):
    def _run(self, dexes: list[tuple[str, bytes]], rules_text: str | None = None) -> tuple[int, str]:
        """Run the gate over an in-memory APK; return (exit_code, stdout)."""
        rules_text = critical_rules_text() if rules_text is None else rules_text
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "test.apk"
            rules = Path(tmp) / "rules.txt"
            with zipfile.ZipFile(apk, "w") as zf:
                for name, data in dexes:
                    zf.writestr(name, data)
            rules.write_text(rules_text)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cj.run_gate(apk, rules, out=buf)
        return rc, buf.getvalue()

    def test_source_present_fails_with_target_ambiguity(self):
        # Pair 1: source referenced (and defined) while its target is also
        # referenced -- the ambiguous state that must FAIL on the source side.
        src = cj.fqcn_to_descriptor(cj.CRITICAL_SOURCES[0])
        dex = build_dex([src] + CRITICAL_TARGET_DESCS, defined_descriptors=[src])
        rc, out = self._run([("classes.dex", dex)])
        self.assertEqual(rc, 1)
        self.assertIn("RESULT=FAIL", out)
        self.assertIn(f"FAIL: critical source is still referenced in the APK: {cj.CRITICAL_SOURCES[0]}", out)
        self.assertIn("source: referenced=yes (defined=yes)", out)
        self.assertIn("target: referenced=yes", out)

    def test_all_targets_present_passes(self):
        dex = build_dex(CRITICAL_TARGET_DESCS)
        rc, out = self._run([("classes.dex", dex)])
        self.assertEqual(rc, 0)
        self.assertIn("RESULT=PASS", out)
        self.assertEqual(out.count("source: referenced=no"), 4)
        self.assertEqual(out.count("target: referenced=yes"), 4)

    def test_missing_target_fails(self):
        # Only three of the four relocated targets are referenced.
        dex = build_dex(CRITICAL_TARGET_DESCS[:3])
        rc, out = self._run([("classes.dex", dex)])
        self.assertEqual(rc, 1)
        self.assertIn("RESULT=FAIL", out)
        self.assertIn("FAIL: relocated target is not referenced in the APK:", out)

    def test_multidex_duplicate_descriptor_counted_once(self):
        src = cj.fqcn_to_descriptor(cj.CRITICAL_SOURCES[1])  # android.os.Flags
        # The same source descriptor appears in two dex files; totals must be
        # a stable union, not a per-entry count.
        dex1 = build_dex([src] + CRITICAL_TARGET_DESCS)
        dex2 = build_dex([src, "Lother/Type;"])
        rc, out = self._run([("classes.dex", dex1), ("classes2.dex", dex2)])
        self.assertEqual(rc, 1)
        self.assertIn("RESULT=FAIL", out)
        self.assertIn("source descriptors referenced: 1 (defined: 0)", out)
        self.assertIn(f"dex=['classes.dex', 'classes2.dex']", out)

    def test_missing_critical_rule_is_an_error(self):
        rules_text = "rule " + cj.CRITICAL_SOURCES[0] + " com.example.SomeTarget\n"
        dex = build_dex(CRITICAL_TARGET_DESCS)
        rc, out = self._run([("classes.dex", dex)], rules_text=rules_text)
        self.assertEqual(rc, 2)
        self.assertIn("ERROR", out)

    def test_main_entrypoint(self):
        dex = build_dex(CRITICAL_TARGET_DESCS)
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "test.apk"
            rules = Path(tmp) / "rules.txt"
            with zipfile.ZipFile(apk, "w") as zf:
                zf.writestr("classes.dex", dex)
            rules.write_text(critical_rules_text())
            argv = ["--apk", str(apk), "--rules", str(rules)]
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cj.main(argv)
        self.assertEqual(rc, 0)
        self.assertIn("RESULT=PASS", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
