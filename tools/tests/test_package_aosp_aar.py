#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/package_aosp_aar.py — strict direct-AAR packager."""

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "package_aosp_aar.py"
_spec = importlib.util.spec_from_file_location("package_aosp_aar", _SCRIPT)
paar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(paar)


def _make_jar(path: Path, entries: dict):
    """entries: {name_in_zip: bytes}"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        for name, data in entries.items():
            z.writestr(name, data)


class TestMergeCodeJars(unittest.TestCase):
    def test_both_input_classes_appear(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"com/android/app/animation/Animations.class": b"\xca\xfe\xba\xbe"})
            _make_jar(d / "b.jar", {"com/android/app/animation/Interpolators.class": b"\xbe\xef"})
            out = d / "merged.jar"
            paar.merge_code_jars([d / "a.jar", d / "b.jar"], out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertIn("com/android/app/animation/Animations.class", names)
            self.assertIn("com/android/app/animation/Interpolators.class", names)

    def test_r_class_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "bad.jar", {"com/android/app/animation/R.class": b"x"})
            with self.assertRaises(paar.DuplicateEntryError if False else Exception):
                paar.merge_code_jars([d / "bad.jar"], d / "out.jar")

    def test_r_inner_class_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "bad.jar", {"com/android/app/animation/R$id.class": b"x"})
            with self.assertRaises(Exception):
                paar.merge_code_jars([d / "bad.jar"], d / "out.jar")

    def test_duplicate_non_manifest_entry_raises(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"com/x/Foo.class": b"1"})
            _make_jar(d / "b.jar", {"com/x/Foo.class": b"2"})
            with self.assertRaises(paar.DuplicateEntryError):
                paar.merge_code_jars([d / "a.jar", d / "b.jar"], d / "out.jar")

    def test_duplicate_manifest_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"META-INF/MANIFEST.MF": b"m1", "com/x/Foo.class": b"1"})
            _make_jar(d / "b.jar", {"META-INF/MANIFEST.MF": b"m2", "com/x/Bar.class": b"2"})
            out = d / "merged.jar"
            paar.merge_code_jars([d / "a.jar", d / "b.jar"], out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertIn("com/x/Foo.class", names)
            self.assertIn("com/x/Bar.class", names)
            # 只保留一份 MANIFEST
            self.assertEqual(sum(1 for n in names if n == "META-INF/MANIFEST.MF"), 1)

    def test_directory_entries_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"com/x/": b"", "com/x/Foo.class": b"1"})
            out = d / "merged.jar"
            paar.merge_code_jars([d / "a.jar"], out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertNotIn("com/x/", names)
            self.assertIn("com/x/Foo.class", names)


class TestCopyResourceTree(unittest.TestCase):
    def test_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / "res"
            (src / "values").mkdir(parents=True)
            (src / "values/ids.xml").write_bytes(b"<ids/>")
            (src / "interpolator").mkdir()
            (src / "interpolator/foo.xml").write_bytes(b"<interpolator/>")
            dst = d / "out"
            paar.copy_resource_tree(src, dst)
            self.assertEqual((dst / "values/ids.xml").read_bytes(), b"<ids/>")
            self.assertEqual((dst / "interpolator/foo.xml").read_bytes(), b"<interpolator/>")


class TestAssembleAar(unittest.TestCase):
    def test_no_pom_or_maven_generated(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/Foo.class": b"1"})
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            out = d / "lib.aar"
            paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertIn("classes.jar", names)
            self.assertIn("res/values/ids.xml", names)
            self.assertIn("AndroidManifest.xml", names)
            self.assertIn("R.txt", names)
            # 不生成 POM / maven 元数据
            self.assertFalse(any(n.endswith(".pom") or n.startswith("META-INF/maven") for n in names),
                             f"不应生成 POM/maven 元数据: {names}")
            # classes.jar 内无 R.class
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    cn = set(cj.namelist())
            self.assertFalse(any(n.rsplit("/", 1)[-1] == "R.class" or
                                 n.rsplit("/", 1)[-1].startswith("R$") for n in cn),
                             "classes.jar 不应含 R.class")

    def test_repeated_builds_are_byte_identical(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/Foo.class": b"\xca\xfe\xba\xbe"})
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            first = d / "first.aar"
            second = d / "second.aar"
            paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, first)
            time.sleep(2)
            paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
