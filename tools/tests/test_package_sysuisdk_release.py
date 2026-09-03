#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tools/package_sysuisdk_release.py."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import package_sysuisdk_release as pkg  # noqa: E402


def _make_platform(root: Path, with_marker: bool = True) -> Path:
    platform = root / pkg.PLATFORM_DIR_NAME
    (platform / "data" / "res").mkdir(parents=True)
    (platform / "android.jar").write_bytes(b"fake-android-jar")
    (platform / "data" / "res" / "values.xml").write_bytes(b"<res/>")
    if with_marker:
        (platform / pkg.MARKER_NAME).write_text(json.dumps({
            "schema_version": pkg.MARKER_SCHEMA_VERSION,
            "tool_version": "045.2",
            "generated": {"inventory": {}},
        }), encoding="utf-8")
    return platform


def _make_release_dir(root: Path) -> Path:
    release = root / "release"
    release.mkdir()
    for name in pkg.TOP_LEVEL_DOCS:
        (release / name).write_text(f"{name} body\n", encoding="utf-8")
    return release


class MarkerGateTest(unittest.TestCase):
    def test_missing_marker_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td), with_marker=False)
            with self.assertRaises(pkg.PackageError):
                pkg.check_generator_owned(platform)

    def test_wrong_schema_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td))
            (platform / pkg.MARKER_NAME).write_text(
                json.dumps({"schema_version": 999}), encoding="utf-8")
            with self.assertRaises(pkg.PackageError):
                pkg.check_generator_owned(platform)

    def test_valid_marker_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td))
            marker = pkg.check_generator_owned(platform)
            self.assertEqual(marker["tool_version"], "045.2")


class CollectEntriesTest(unittest.TestCase):
    def test_entries_are_prefixed_and_complete(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td))
            entries = pkg.collect_platform_entries(platform)
            self.assertEqual(
                set(entries),
                {f"{pkg.PLATFORM_DIR_NAME}/android.jar",
                 f"{pkg.PLATFORM_DIR_NAME}/data/res/values.xml",
                 f"{pkg.PLATFORM_DIR_NAME}/{pkg.MARKER_NAME}"})

    def test_symlink_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td))
            os.symlink(platform / "android.jar", platform / "link.jar")
            with self.assertRaises(pkg.PackageError):
                pkg.collect_platform_entries(platform)

    def test_missing_doc_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            release = _make_release_dir(Path(td))
            (release / "NOTICE").unlink()
            with self.assertRaises(pkg.PackageError):
                pkg.collect_doc_entries(release)


class DeterminismTest(unittest.TestCase):
    def test_two_runs_produce_identical_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td))
            release = _make_release_dir(Path(td))
            out1 = Path(td) / "a.zip"
            out2 = Path(td) / "b.zip"
            for out in (out1, out2):
                rc = pkg.run(["--platform", str(platform),
                              "--release-dir", str(release),
                              "--output", str(out)])
                self.assertEqual(rc, 0)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())

    def test_zip_layout_and_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            platform = _make_platform(Path(td))
            release = _make_release_dir(Path(td))
            out = Path(td) / "o.zip"
            self.assertEqual(
                pkg.run(["--platform", str(platform),
                         "--release-dir", str(release),
                         "--output", str(out)]), 0)
            with zipfile.ZipFile(out) as zf:
                names = zf.namelist()
                # sorted, top-level docs first (uppercase sorts first)
                self.assertEqual(names, sorted(names))
                self.assertEqual(names[:3], ["LICENSE", "NOTICE",
                                             "README.txt"])
                for info in zf.infolist():
                    self.assertEqual(info.date_time, pkg.FIXED_TIMESTAMP)
                self.assertIn(f"{pkg.PLATFORM_DIR_NAME}/android.jar", names)
            sidecar = out.with_suffix(".zip.sha256")
            self.assertTrue(sidecar.is_file())
            digest, _, fname = sidecar.read_text().strip().partition("  ")
            import hashlib
            self.assertEqual(
                digest, hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertEqual(fname, out.name)


if __name__ == "__main__":
    unittest.main()
