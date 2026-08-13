#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tools/build_sysuisdk.py.

All tests operate on throwaway fixture trees under tempfile.TemporaryDirectory.
The real live SDK at ~/Android/Sdk/platforms/android-SysUISdk is NEVER touched.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

# Make tools/ importable.
_TOOLS = Path(__file__).resolve().parent.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
import build_sysuisdk as b  # noqa: E402
import install_sdk  # noqa: E402


# --- fixture helpers -------------------------------------------------------

def _make_jar(path: Path, entries: dict) -> None:
    """Create a jar at path with {entry_name: bytes}."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def _jar_entries(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as zf:
        return {i.filename: i.CRC for i in zf.infolist() if not i.is_dir()}


_BASE_PKG_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<repo>
    <localPackage path="platforms;android-37.0" obsolete="false">
        <type-details>
            <api-level>37.0</api-level>
            <codename></codename>
        </type-details>
        <display-name>Android SDK Platform 37.0</display-name>
    </localPackage>
</repo>
"""


def _make_base_platform(root: Path) -> Path:
    """A minimal but realistic base platform fixture (android-37.0-like)."""
    root.mkdir(parents=True, exist_ok=True)
    # android.jar: A.class, B.class, manifest(soong_zip)
    _make_jar(root / "android.jar", {
        "android/A.class": b"\xCA\xFE\xBA\xBEbaseA",
        "android/B.class": b"\xCA\xFE\xBA\xBEbaseB",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong_zip\n\n",
    })
    # core-for-system-modules.jar: X.class + manifest (no dalvik yet)
    _make_jar(root / "core-for-system-modules.jar", {
        "java/lang/X.class": b"\xCA\xFE\xBA\xBEcoreX",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong_zip\n\n",
    })
    # framework.aidl (no hidden decls yet)
    (root / "framework.aidl").write_text("// stub aidl\n", encoding="utf-8")
    (root / "package.xml").write_text(_BASE_PKG_XML, encoding="utf-8")
    (root / "build.prop").write_text("ro.build.version.sdk=37\n", encoding="utf-8")
    (root / "source.properties").write_text("Pkg.Desc=Android SDK Platform 37.0\n",
                                            encoding="utf-8")
    (root / "sdk.properties").write_text("sdk.dir=stub\n", encoding="utf-8")
    # data/ and optional/ subtrees
    d = root / "data"; d.mkdir()
    (d / "features.txt").write_text("f1\n", encoding="utf-8")
    (d / "res").mkdir(); (d / "res" / "v.txt").write_text("r", encoding="utf-8")
    o = root / "optional"; o.mkdir()
    _make_jar(o / "android.test.base.jar", {"t/B.class": b"tb"})
    # Pristine backups that S0 must SKIP (not copy), so each stage makes its own.
    shutil.copy2(root / "android.jar", root / "android.jar.orig")
    shutil.copy2(root / "framework.aidl", root / "framework.aidl.bak-preaidl")
    return root


def _make_framework_jar(path: Path) -> Path:
    """framework.jar fixture: B.class (master, different bytes), C.class, manifest."""
    _make_jar(path, {
        "android/B.class": b"\xCA\xFE\xBA\xBEfwB-master",
        "android/C.class": b"\xCA\xFE\xBA\xBEfwC",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong_zip\n\n",
    })
    return path


def _make_core_libart_jar(path: Path) -> Path:
    """core-libart fixture with the dalvik/annotation/optimization classes."""
    _make_jar(path, {
        "dalvik/annotation/optimization/NeverCompile.class": b"\xCA\xFE\xBA\xBEnc",
        "dalvik/annotation/optimization/NeverInline.class": b"\xCA\xFE\xBA\xBEni",
        "dalvik/annotation/optimization/DeadReferenceSafe.class": b"\xCA\xFE\xBA\xBEdrs",
        "dalvik/annotation/optimization/ReachabilitySensitive.class": b"\xCA\xFE\xBA\xBErs",
        "java/lang/X.class": b"\xCA\xFE\xBA\xBEcoreX-libart",
    })
    return path


class _FixtureCase(unittest.TestCase):
    """Base class that provisions base/framework/core-libart fixtures."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.base = _make_base_platform(root / "android-37.0")
        self.fw = _make_framework_jar(root / "framework.jar")
        self.corelib = _make_core_libart_jar(root / "core-libart.jar")
        self.staging = root / "android-SysUISdk-staging"

    def _build_live_like(self) -> Path:
        """Build a 'live' fixture = base + S1 + S2 + S3 (the audited semantics),
        so verify(staging, live) should PASS when staging was built the same way.
        """
        live = Path(self.tmp.name) / "android-SysUISdk-live"
        b.stage_s0(self.base, live, clean=True)
        b.stage_s1(live, self.fw)
        b.stage_s2(live)
        b.stage_s3(live, self.corelib)
        return live

    def _build_staging(self, clean: bool = True) -> None:
        b.stage_s0(self.base, self.staging, clean=clean)
        b.stage_s1(self.staging, self.fw)
        b.stage_s2(self.staging)
        b.stage_s3(self.staging, self.corelib)


# --- live-guard tests ------------------------------------------------------

class LiveGuardTest(unittest.TestCase):
    def test_rejects_live_sdk_path(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "android-SysUISdk"
            live.mkdir()
            orig = b.LIVE_SDK_DIR
            b.LIVE_SDK_DIR = live
            try:
                with self.assertRaises(SystemExit):
                    b._live_guard(live)
            finally:
                b.LIVE_SDK_DIR = orig

    def test_rejects_path_inside_live_sdk(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "android-SysUISdk"
            live.mkdir()
            inside = live / "sub"
            orig = b.LIVE_SDK_DIR
            b.LIVE_SDK_DIR = live
            try:
                with self.assertRaises(SystemExit):
                    b._live_guard(inside)
            finally:
                b.LIVE_SDK_DIR = orig

    def test_allows_unrelated_staging_path(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "android-SysUISdk-staging"
            live = Path(td) / "android-SysUISdk"
            live.mkdir()
            orig = b.LIVE_SDK_DIR
            b.LIVE_SDK_DIR = live
            try:
                b._live_guard(staging)  # must not raise
            finally:
                b.LIVE_SDK_DIR = orig


# --- S0 tests --------------------------------------------------------------

class StageS0Test(_FixtureCase):
    def test_copies_base_and_rewrites_package_xml(self):
        b.stage_s0(self.base, self.staging, clean=True)
        self.assertTrue((self.staging / "android.jar").is_file())
        self.assertTrue((self.staging / "core-for-system-modules.jar").is_file())
        self.assertTrue((self.staging / "framework.aidl").is_file())
        self.assertTrue((self.staging / "build.prop").is_file())
        self.assertTrue((self.staging / "data" / "features.txt").is_file())
        self.assertTrue((self.staging / "optional" / "android.test.base.jar").is_file())
        pkg = (self.staging / "package.xml").read_text(encoding="utf-8")
        self.assertIn(b.STAGING_PKG_PATH, pkg)
        self.assertIn(f"<api-level>{b.STAGING_API_LEVEL}</api-level>", pkg)
        self.assertIn(f"<codename>{b.STAGING_CODENAME}</codename>", pkg)
        self.assertIn(b.STAGING_DISPLAY_NAME, pkg)
        # build.prop copied verbatim
        self.assertEqual((self.staging / "build.prop").read_text(),
                         (self.base / "build.prop").read_text())

    def test_skips_orig_and_bak_backups(self):
        b.stage_s0(self.base, self.staging, clean=True)
        self.assertFalse((self.staging / "android.jar.orig").exists())
        self.assertFalse((self.staging / "framework.aidl.bak-preaidl").exists())

    def test_clean_removes_existing(self):
        b.stage_s0(self.base, self.staging, clean=True)
        (self.staging / "leftover.txt").write_text("x")
        b.stage_s0(self.base, self.staging, clean=True)
        self.assertFalse((self.staging / "leftover.txt").exists())

    def test_idempotent_without_clean_keeps_existing(self):
        b.stage_s0(self.base, self.staging, clean=True)
        (self.staging / "leftover.txt").write_text("x")
        b.stage_s0(self.base, self.staging, clean=False)  # no-op copy
        self.assertTrue((self.staging / "leftover.txt").exists())


# --- S1 tests --------------------------------------------------------------

class StageS1Test(_FixtureCase):
    def test_merges_framework_master(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.fw)
        entries = _jar_entries(self.staging / "android.jar")
        # A.class kept from base (not in framework)
        self.assertIn("android/A.class", entries)
        # C.class added from framework
        self.assertIn("android/C.class", entries)
        # B.class present; its CRC must equal framework's B (master wins)
        fw_entries = _jar_entries(self.fw)
        self.assertEqual(entries["android/B.class"], fw_entries["android/B.class"])
        # base B bytes overwritten: staging B CRC != base B CRC
        base_entries = _jar_entries(self.base / "android.jar")
        self.assertNotEqual(entries["android/B.class"], base_entries["android/B.class"])

    def test_creates_orig_backup(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.fw)
        orig = self.staging / "android.jar.orig"
        self.assertTrue(orig.exists())
        # backup == base (pre-merge)
        self.assertEqual(_jar_entries(orig), _jar_entries(self.base / "android.jar"))

    def test_manifest_pinned_to_live_bytes(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.fw)
        with zipfile.ZipFile(self.staging / "android.jar") as zf:
            mf = zf.read("META-INF/MANIFEST.MF")
        self.assertEqual(mf, b.ANDROID_MANIFEST_BYTES)

    def test_idempotent_remerge_same_result(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.fw)
        first = _jar_entries(self.staging / "android.jar")
        b.stage_s1(self.staging, self.fw)  # re-run; .orig already exists
        second = _jar_entries(self.staging / "android.jar")
        self.assertEqual(first, second)


# --- S2 tests --------------------------------------------------------------

class StageS2Test(_FixtureCase):
    def test_patches_aidl_with_hidden_decls(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s2(self.staging)
        text = (self.staging / "framework.aidl").read_text(encoding="utf-8")
        for decl_iface in install_sdk.HIDDEN_IFACES:
            self.assertIn(f"interface {decl_iface};", text)
        for decl_parcel in install_sdk.HIDDEN_PARCELABLES:
            self.assertIn(f"parcelable {decl_parcel};", text)

    def test_creates_bak_preaidl_backup(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s2(self.staging)
        bak = self.staging / "framework.aidl.bak-preaidl"
        self.assertTrue(bak.exists())
        self.assertEqual(bak.read_text(), (self.base / "framework.aidl").read_text())

    def test_idempotent_appends_once(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s2(self.staging)
        before = (self.staging / "framework.aidl").read_text()
        b.stage_s2(self.staging)
        after = (self.staging / "framework.aidl").read_text()
        self.assertEqual(before, after)


# --- S3 tests --------------------------------------------------------------

class StageS3Test(_FixtureCase):
    def test_injects_dalvik_classes(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.fw)
        b.stage_s3(self.staging, self.corelib)
        entries = _jar_entries(self.staging / "core-for-system-modules.jar")
        for cls in ("NeverCompile", "NeverInline", "DeadReferenceSafe",
                    "ReachabilitySensitive"):
            self.assertIn(f"dalvik/annotation/optimization/{cls}.class", entries)

    def test_creates_core_orig_backup(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s3(self.staging, self.corelib)
        orig = self.staging / "core-for-system-modules.jar.orig"
        self.assertTrue(orig.exists())
        self.assertEqual(_jar_entries(orig),
                         _jar_entries(self.base / "core-for-system-modules.jar"))

    def test_normalizes_android_manifest(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.fw)
        b.stage_s3(self.staging, self.corelib)
        with zipfile.ZipFile(self.staging / "android.jar") as zf:
            mf = zf.read("META-INF/MANIFEST.MF")
        self.assertEqual(mf, b.ANDROID_MANIFEST_BYTES)

    def test_idempotent_no_reinject(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s3(self.staging, self.corelib)
        before = _jar_entries(self.staging / "core-for-system-modules.jar")
        b.stage_s3(self.staging, self.corelib)
        after = _jar_entries(self.staging / "core-for-system-modules.jar")
        self.assertEqual(before, after)


# --- S5 verify tests -------------------------------------------------------

class VerifyTest(_FixtureCase):
    def test_pass_when_staging_equals_live(self):
        live = self._build_live_like()
        self._build_staging()
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 0)

    def test_diff_missing_entries_in_android_jar(self):
        live = self._build_live_like()
        self._build_staging()
        # remove an entry from staging android.jar by rebuilding it smaller
        with zipfile.ZipFile(self.staging / "android.jar", "r") as zf:
            kept = {n: zf.read(n) for n in zf.namelist()
                    if n != "android/C.class" and not n.endswith("/")}
        _make_jar(self.staging / "android.jar", kept)
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 1)

    def test_diff_extra_entries_in_android_jar(self):
        live = self._build_live_like()
        self._build_staging()
        with zipfile.ZipFile(self.staging / "android.jar", "r") as zf:
            entries = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
        entries["android/EXTRA.class"] = b"\xCA\xFE\xBA\xBEextra"
        _make_jar(self.staging / "android.jar", entries)
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 1)

    def test_diff_crc_mismatch(self):
        live = self._build_live_like()
        self._build_staging()
        with zipfile.ZipFile(self.staging / "android.jar", "r") as zf:
            entries = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
        entries["android/A.class"] = b"\xCA\xFE\xBA\xBEmutated"
        _make_jar(self.staging / "android.jar", entries)
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 1)

    def test_diff_framework_aidl_bytes(self):
        live = self._build_live_like()
        self._build_staging()
        (self.staging / "framework.aidl").write_text("// tampered\n",
                                                       encoding="utf-8")
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 1)

    def test_package_xml_shape_passes_with_staging_name(self):
        live = self._build_live_like()
        self._build_staging()
        # staging package.xml uses the staging name; verify checks shape, not
        # byte-equality, so it should still PASS.
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 0)

    def test_diff_data_tree(self):
        live = self._build_live_like()
        self._build_staging()
        (self.staging / "data" / "extra.txt").write_text("x")
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 1)


# --- integration -----------------------------------------------------------

class FullPipelineTest(_FixtureCase):
    def test_staging_inventory_equals_live_after_full_pipeline(self):
        live = self._build_live_like()
        self._build_staging()
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 0)
        # android.jar inventory identical entry-for-entry
        self.assertEqual(_jar_entries(self.staging / "android.jar"),
                         _jar_entries(live / "android.jar"))
        self.assertEqual(_jar_entries(self.staging / "core-for-system-modules.jar"),
                         _jar_entries(live / "core-for-system-modules.jar"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
