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


# --- Task 041 (S3b) approved entry fixtures ---------------------------------

_S3B_IO_UTILS = (
    "libcore/io/IoUtils.class",
    "libcore/io/IoUtils$FileReader.class",
)
_S3B_NATIVE_ALLOCATION = (
    "libcore/util/NativeAllocationRegistry.class",
    "libcore/util/NativeAllocationRegistry$CleanerRunner.class",
    "libcore/util/NativeAllocationRegistry$CleanerThunk.class",
    "libcore/util/NativeAllocationRegistry$Metrics.class",
)
_S3B_DDMC = (
    "org/apache/harmony/dalvik/ddmc/Chunk.class",
    "org/apache/harmony/dalvik/ddmc/ChunkHandler.class",
    "org/apache/harmony/dalvik/ddmc/DdmServer.class",
    "org/apache/harmony/dalvik/ddmc/DdmVmInternal.class",
)
_S3B_UNSUPPORTED = (
    "android/compat/annotation/UnsupportedAppUsage.class",
    "android/compat/annotation/UnsupportedAppUsage$Container.class",
)
_S3B_ACONFIG = ("com/android/aconfig/annotations/AconfigFlagAccessor.class",)
_S3B_KEEPANNO_ENTRIES = tuple(
    f"com/android/tools/r8/keepanno/annotations/{n}.class" for n in (
        "AnnotationPattern", "CheckOptimizedOut", "CheckRemoved",
        "ClassAccessFlags", "ClassNamePattern", "FieldAccessFlags",
        "InstanceOfPattern", "KeepBinding", "KeepCondition", "KeepConstraint",
        "KeepEdge", "KeepForApi", "KeepItemKind", "KeepOption", "KeepTarget",
        "MemberAccessFlags", "MethodAccessFlags", "StringPattern",
        "TypePattern", "UsedByNative", "UsedByReflection", "UsesReflection"))

S3B_APPROVED_35 = sorted(_S3B_IO_UTILS + _S3B_NATIVE_ALLOCATION + _S3B_DDMC
                          + _S3B_UNSUPPORTED + _S3B_ACONFIG + _S3B_KEEPANNO_ENTRIES)
assert len(S3B_APPROVED_35) == 35


def _s3b_payload(entry: str) -> bytes:
    """Deterministic distinct fake class bytes for an S3b fixture entry."""
    return b"\xCA\xFE\xBA\xBE" + entry.encode("utf-8")


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


def _make_merged_jar(path: Path) -> Path:
    """android-merged.jar fixture: B.class (master, different bytes) + C.class
    (new) + a STALE resources.arsc + res/ (the May-27 snapshot S4 will replace).

    Stands in for the real android-merged.jar (2026-07-22 merge product): a
    self-contained jar S1 copies wholesale as android.jar. B.class has master
    bytes distinct from base's B; C.class is a new entry absent from base. The
    stale res/ + resources.arsc mirror the real merged jar carrying an outdated
    resource snapshot that S4 overlays with the current framework-res.apk.
    """
    _make_jar(path, {
        "android/B.class": b"\xCA\xFE\xBA\xBEfwB-master",
        "android/C.class": b"\xCA\xFE\xBA\xBEfwC",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong_zip\n\n",
        "resources.arsc": b"\x02\x00\x00\x00stale-arsc-bytes",
        "res/values/values.xml": b"<resources>stale-values</resources>",
        "res/drawable/old.png": b"\x89PNGstale-old",
    })
    return path


def _make_framework_res_apk(path: Path) -> Path:
    """framework-res.apk fixture: FRESH resources.arsc + res/ entries, plus
    non-resource entries (AndroidManifest.xml, META-INF/*, assets/) that S4
    must NOT carry over into android.jar — only resources.arsc + res/** are
    overlaid.
    """
    _make_jar(path, {
        "resources.arsc": b"\x02\x00\x00\x00fresh-arsc-bytes",
        "res/values/values.xml": b"<resources>fresh-values</resources>",
        "res/drawable/icon.png": b"\x89PNGfresh-icon",
        "res/color/surface.xml": b"<color>fresh-surface</color>",
        # non-resource entries S4 must NOT add to android.jar:
        "AndroidManifest.xml": b"<manifest fresh/>",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong_zip\n\n",
        "META-INF/CERT.SF": b"cert",
        "assets/geoid_map/x.pb": b"\x00\x01fresh-asset",
    })
    return path


def _make_core_libart_jar(path: Path) -> Path:
    """core-libart fixture with the dalvik/annotation/optimization classes
    plus the Task 041 libcore slices (IoUtils, NativeAllocationRegistry, ddmc)."""
    _make_jar(path, {
        "dalvik/annotation/optimization/NeverCompile.class": b"\xCA\xFE\xBA\xBEnc",
        "dalvik/annotation/optimization/NeverInline.class": b"\xCA\xFE\xBA\xBEni",
        "dalvik/annotation/optimization/DeadReferenceSafe.class": b"\xCA\xFE\xBA\xBEdrs",
        "dalvik/annotation/optimization/ReachabilitySensitive.class": b"\xCA\xFE\xBA\xBErs",
        "java/lang/X.class": b"\xCA\xFE\xBA\xBEcoreX-libart",
        # --- Task 041 approved libcore slices (fake fixture bytes) ---
        "libcore/io/IoUtils.class": _s3b_payload("libcore/io/IoUtils.class"),
        "libcore/io/IoUtils$FileReader.class": _s3b_payload(
            "libcore/io/IoUtils$FileReader.class"),
        "libcore/util/NativeAllocationRegistry.class": _s3b_payload(
            "libcore/util/NativeAllocationRegistry.class"),
        "libcore/util/NativeAllocationRegistry$CleanerRunner.class": _s3b_payload(
            "libcore/util/NativeAllocationRegistry$CleanerRunner.class"),
        "libcore/util/NativeAllocationRegistry$CleanerThunk.class": _s3b_payload(
            "libcore/util/NativeAllocationRegistry$CleanerThunk.class"),
        "libcore/util/NativeAllocationRegistry$Metrics.class": _s3b_payload(
            "libcore/util/NativeAllocationRegistry$Metrics.class"),
        "org/apache/harmony/dalvik/ddmc/Chunk.class": _s3b_payload(
            "org/apache/harmony/dalvik/ddmc/Chunk.class"),
        "org/apache/harmony/dalvik/ddmc/ChunkHandler.class": _s3b_payload(
            "org/apache/harmony/dalvik/ddmc/ChunkHandler.class"),
        "org/apache/harmony/dalvik/ddmc/DdmServer.class": _s3b_payload(
            "org/apache/harmony/dalvik/ddmc/DdmServer.class"),
        "org/apache/harmony/dalvik/ddmc/DdmVmInternal.class": _s3b_payload(
            "org/apache/harmony/dalvik/ddmc/DdmVmInternal.class"),
    })
    return path


def _make_unsupportedappusage_jar(path: Path) -> Path:
    """unsupportedappusage fixture: the 2 approved classes + 1 unrelated."""
    _make_jar(path, {
        "android/compat/annotation/UnsupportedAppUsage.class": _s3b_payload(
            "android/compat/annotation/UnsupportedAppUsage.class"),
        "android/compat/annotation/UnsupportedAppUsage$Container.class": _s3b_payload(
            "android/compat/annotation/UnsupportedAppUsage$Container.class"),
        "java/lang/Y.class": b"\xCA\xFE\xBA\xBEunrelated-unsupported",
    })
    return path


def _make_aconfig_annotations_jar(path: Path) -> Path:
    """aconfig-annotations-lib fixture: AconfigFlagAccessor (approved) plus
    the deliberately-unapproved siblings (Assume*ForR8, VisibleForTesting)."""
    _make_jar(path, {
        "com/android/aconfig/annotations/AconfigFlagAccessor.class": _s3b_payload(
            "com/android/aconfig/annotations/AconfigFlagAccessor.class"),
        "com/android/aconfig/annotations/AssumeTrueForR8.class": _s3b_payload(
            "com/android/aconfig/annotations/AssumeTrueForR8.class"),
        "com/android/aconfig/annotations/AssumeFalseForR8.class": _s3b_payload(
            "com/android/aconfig/annotations/AssumeFalseForR8.class"),
        "com/android/aconfig/annotations/VisibleForTesting.class": _s3b_payload(
            "com/android/aconfig/annotations/VisibleForTesting.class"),
        "com/android/aconfig/annotations/VisibleForTesting$Visibility.class": _s3b_payload(
            "com/android/aconfig/annotations/VisibleForTesting$Visibility.class"),
    })
    return path


def _make_keepanno_annotations_jar(path: Path) -> Path:
    """keepanno fixture: the 22 approved annotation classes + out-of-package
    siblings and jar-level metadata that must never be injected."""
    entries = {
        e: _s3b_payload(e) for e in _S3B_KEEPANNO_ENTRIES
    }
    entries["com/android/tools/r8/other/Foo.class"] = b"\xCA\xFE\xBA\xBEout-of-pkg"
    entries["META-INF/MANIFEST.MF"] = b"Manifest-Version: 1.0\n"
    entries["r8-version.properties"] = b"version=fixture\n"
    _make_jar(path, entries)
    return path


class _FixtureCase(unittest.TestCase):
    """Base class that provisions base/framework/core-libart fixtures."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.base = _make_base_platform(root / "android-37.0")
        self.merged = _make_merged_jar(root / "android-merged.jar")
        self.corelib = _make_core_libart_jar(root / "core-libart.jar")
        self.fwres = _make_framework_res_apk(root / "framework-res.apk")
        self.unsupported = _make_unsupportedappusage_jar(
            root / "unsupportedappusage.jar")
        self.aconfig = _make_aconfig_annotations_jar(
            root / "aconfig-annotations-lib.jar")
        self.keepanno = _make_keepanno_annotations_jar(
            root / "keepanno-annotations.jar")
        self.staging = root / "android-SysUISdk-staging"

    def _build_live_like(self) -> Path:
        """Build a 'live' fixture = base + S1 + S2 + S3 (the audited semantics),
        so verify(staging, live) should PASS when staging was built the same way.
        """
        live = Path(self.tmp.name) / "android-SysUISdk-live"
        b.stage_s0(self.base, live, clean=True)
        b.stage_s1(live, self.merged)
        b.stage_s2(live)
        b.stage_s3(live, self.corelib)
        return live

    def _build_staging(self, clean: bool = True) -> None:
        b.stage_s0(self.base, self.staging, clean=clean)
        b.stage_s1(self.staging, self.merged)
        b.stage_s2(self.staging)
        b.stage_s3(self.staging, self.corelib)

    def _build_staging_with_s4(self) -> None:
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)
        b.stage_s2(self.staging)
        b.stage_s3(self.staging, self.corelib)
        b.stage_s4(self.staging, self.fwres)

    def _run_s3b(self, target: Path | None = None) -> None:
        b.stage_s3b(target or self.staging, self.corelib, self.unsupported,
                    self.aconfig, self.keepanno)

    def _build_to_s3(self, target: Path) -> None:
        b.stage_s0(self.base, target, clean=True)
        b.stage_s1(target, self.merged)
        b.stage_s2(target)
        b.stage_s3(target, self.corelib)


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

class S1ConfigTest(unittest.TestCase):
    """Regression guard: the S1 source must be libs/android-merged.jar.

    Task 010b re-tracked the recovered 2026-07-22 merge product as the declared
    S1 source (replacing libs/framework.jar). This test pins the default so a
    future change cannot silently revert S1 to the incomplete framework.jar
    (which reproduced only 25869 of 27139 merge deltas — see architecture doc).
    """

    def test_default_merged_jar_points_at_android_merged(self):
        self.assertEqual(b.DEFAULT_MERGED_JAR.name, "android-merged.jar")
        self.assertEqual(b.DEFAULT_MERGED_JAR.parent.name, "libs")


class StageS1Test(_FixtureCase):
    def test_copies_merged_wholesale(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)
        entries = _jar_entries(self.staging / "android.jar")
        merged_entries = _jar_entries(self.merged)
        # S1 = wholesale copy: every non-manifest entry (name + CRC) matches the
        # merged jar. MANIFEST.MF is intentionally pinned to the audited live
        # bytes (checked separately below).
        non_manifest = {k: v for k, v in entries.items()
                        if k != "META-INF/MANIFEST.MF"}
        non_manifest_merged = {k: v for k, v in merged_entries.items()
                               if k != "META-INF/MANIFEST.MF"}
        self.assertEqual(non_manifest, non_manifest_merged)
        # MANIFEST.MF pinned to audited live bytes (not the merged jar's).
        self.assertEqual(entries["META-INF/MANIFEST.MF"],
                         zipfile.crc32(b.ANDROID_MANIFEST_BYTES) & 0xFFFFFFFF)
        self.assertNotEqual(entries["META-INF/MANIFEST.MF"],
                            merged_entries["META-INF/MANIFEST.MF"])
        # C.class present (new entry from merged).
        self.assertIn("android/C.class", entries)
        # B.class bytes are merged's master bytes (not base's).
        base_entries = _jar_entries(self.base / "android.jar")
        self.assertEqual(entries["android/B.class"], merged_entries["android/B.class"])
        self.assertNotEqual(entries["android/B.class"], base_entries["android/B.class"])

    def test_creates_orig_backup(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)
        orig = self.staging / "android.jar.orig"
        self.assertTrue(orig.exists())
        # backup == base (pre-S1)
        self.assertEqual(_jar_entries(orig), _jar_entries(self.base / "android.jar"))

    def test_manifest_pinned_to_live_bytes(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)
        with zipfile.ZipFile(self.staging / "android.jar") as zf:
            mf = zf.read("META-INF/MANIFEST.MF")
        self.assertEqual(mf, b.ANDROID_MANIFEST_BYTES)

    def test_idempotent_recopy_same_result(self):
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)
        first = _jar_entries(self.staging / "android.jar")
        b.stage_s1(self.staging, self.merged)  # re-run; .orig already exists
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
        b.stage_s1(self.staging, self.merged)
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
        b.stage_s1(self.staging, self.merged)
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


# --- S4 config -----------------------------------------------------------

class S4ConfigTest(unittest.TestCase):
    """Pin the S4 source to libs/framework-res.apk (regression guard)."""

    def test_default_framework_res_apk_points_at_libs(self):
        self.assertEqual(b.DEFAULT_FRAMEWORK_RES_APK.name, "framework-res.apk")
        self.assertEqual(b.DEFAULT_FRAMEWORK_RES_APK.parent.name, "libs")


# --- S4 tests --------------------------------------------------------------

class StageS4Test(_FixtureCase):
    def _staging_with_s1(self) -> None:
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)

    def test_overlays_fresh_resources(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        entries = _jar_entries(self.staging / "android.jar")
        fwres_entries = _jar_entries(self.fwres)
        # fresh resources.arsc + res/ present, CRC-matching framework-res.apk
        self.assertEqual(entries["resources.arsc"], fwres_entries["resources.arsc"])
        for n in ("res/values/values.xml", "res/drawable/icon.png",
                  "res/color/surface.xml"):
            self.assertIn(n, entries)
            self.assertEqual(entries[n], fwres_entries[n])

    def test_strips_stale_resources(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        entries = _jar_entries(self.staging / "android.jar")
        merged_entries = _jar_entries(self.merged)
        # stale merged res/ entry removed
        self.assertNotIn("res/drawable/old.png", entries)
        # resources.arsc + values.xml are the FRESH bytes, not the stale ones
        self.assertNotEqual(entries["resources.arsc"],
                            merged_entries["resources.arsc"])
        self.assertNotEqual(entries["res/values/values.xml"],
                            merged_entries["res/values/values.xml"])

    def test_keeps_non_resource_entries(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        entries = _jar_entries(self.staging / "android.jar")
        merged_entries = _jar_entries(self.merged)
        # B.class, C.class preserved with the original (merged) CRC
        self.assertEqual(entries["android/B.class"],
                         merged_entries["android/B.class"])
        self.assertEqual(entries["android/C.class"],
                         merged_entries["android/C.class"])

    def test_does_not_add_non_resource_from_apk(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        entries = _jar_entries(self.staging / "android.jar")
        for n in ("AndroidManifest.xml", "META-INF/CERT.SF",
                  "assets/geoid_map/x.pb"):
            self.assertNotIn(n, entries)
        # android.jar's own MANIFEST.MF is preserved (pinned live bytes), NOT
        # the apk's manifest.
        self.assertEqual(entries["META-INF/MANIFEST.MF"],
                         zipfile.crc32(b.ANDROID_MANIFEST_BYTES) & 0xFFFFFFFF)

    def test_creates_bak_preres_backup(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        bak = self.staging / "android.jar.bak-preres"
        self.assertTrue(bak.exists())
        bak_entries = _jar_entries(bak)
        merged_entries = _jar_entries(self.merged)
        # backup == pre-S4 android.jar (post-S1): merged wholesale (incl the
        # stale res/) but with MANIFEST.MF pinned to the audited live bytes
        # (NOT merged's soong_zip manifest — S1 rewrites it).
        non_manifest_bak = {k: v for k, v in bak_entries.items()
                           if k != "META-INF/MANIFEST.MF"}
        non_manifest_merged = {k: v for k, v in merged_entries.items()
                              if k != "META-INF/MANIFEST.MF"}
        self.assertEqual(non_manifest_bak, non_manifest_merged)
        self.assertEqual(bak_entries["META-INF/MANIFEST.MF"],
                         zipfile.crc32(b.ANDROID_MANIFEST_BYTES) & 0xFFFFFFFF)
        # the stale res/ is still present in the pre-overlay backup
        self.assertIn("res/drawable/old.png", bak_entries)

    def test_idempotent(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        first = _jar_entries(self.staging / "android.jar")
        b.stage_s4(self.staging, self.fwres)  # re-run; .bak-preres already exists
        second = _jar_entries(self.staging / "android.jar")
        self.assertEqual(first, second)

    def test_manifest_preserved(self):
        self._staging_with_s1()
        b.stage_s4(self.staging, self.fwres)
        with zipfile.ZipFile(self.staging / "android.jar") as zf:
            mf = zf.read("META-INF/MANIFEST.MF")
        self.assertEqual(mf, b.ANDROID_MANIFEST_BYTES)

    def test_deterministic_two_builds_identical(self):
        # Two independent staging dirs built S0+S1+S4 must yield byte-identical
        # android.jar inventories (deterministic entry order + CRCs).
        with tempfile.TemporaryDirectory() as td2:
            root2 = Path(td2)
            base2 = _make_base_platform(root2 / "android-37.0")
            merged2 = _make_merged_jar(root2 / "android-merged.jar")
            fwres2 = _make_framework_res_apk(root2 / "framework-res.apk")
            staging2 = root2 / "android-SysUISdk-staging"
            b.stage_s0(base2, staging2, clean=True)
            b.stage_s1(staging2, merged2)
            b.stage_s4(staging2, fwres2)
            # this staging
            self._staging_with_s1()
            b.stage_s4(self.staging, self.fwres)
            self.assertEqual(_jar_entries(self.staging / "android.jar"),
                             _jar_entries(staging2 / "android.jar"))


# --- S3b tests (Task 041: R8 library-class bridge) ------------------------

class StageS3bTest(_FixtureCase):
    def _build_to_s3_staging(self) -> None:
        self._build_to_s3(self.staging)

    def test_injects_exactly_35_entries_into_both_targets(self):
        self._build_to_s3_staging()
        self._run_s3b()
        for name in ("android.jar", "core-for-system-modules.jar"):
            entries = _jar_entries(self.staging / name)
            approved_present = [e for e in S3B_APPROVED_35 if e in entries]
            self.assertEqual(approved_present, S3B_APPROVED_35,
                             f"{name}: missing approved entries")

    def test_injected_bytes_equal_assigned_source_fixture(self):
        self._build_to_s3_staging()
        self._run_s3b()
        for name in ("android.jar", "core-for-system-modules.jar"):
            with zipfile.ZipFile(self.staging / name) as zf:
                for entry in S3B_APPROVED_35:
                    self.assertEqual(zf.read(entry), _s3b_payload(entry),
                                     f"{name}: {entry}")

    def test_no_unrelated_source_entry_injected(self):
        self._build_to_s3_staging()
        self._run_s3b()
        for name in ("android.jar", "core-for-system-modules.jar"):
            with zipfile.ZipFile(self.staging / name) as zf:
                names = set(zf.namelist())
            for unrelated in (
                "java/lang/Y.class",                      # unsupported jar
                "com/android/aconfig/annotations/AssumeTrueForR8.class",
                "com/android/aconfig/annotations/AssumeFalseForR8.class",
                "com/android/aconfig/annotations/VisibleForTesting.class",
                "com/android/aconfig/annotations/VisibleForTesting$Visibility.class",
                "com/android/tools/r8/other/Foo.class",    # keepanno jar
                "r8-version.properties",                   # keepanno jar
            ):
                self.assertNotIn(unrelated, names,
                                 f"{name}: unrelated entry injected")

    def test_backups_use_bak_prer8lib_and_preserve_pre_s3b_bytes(self):
        self._build_to_s3_staging()
        pre = {
            name: (self.staging / name).read_bytes()
            for name in ("android.jar", "core-for-system-modules.jar")
        }
        self._run_s3b()
        for name, pre_bytes in pre.items():
            bak = self.staging / f"{name}.bak-prer8lib"
            self.assertTrue(bak.exists(), f"{name}: missing backup")
            self.assertEqual(bak.read_bytes(), pre_bytes,
                             f"{name}: backup does not preserve pre-S3b bytes")

    def test_rerun_is_byte_for_byte_noop(self):
        self._build_to_s3_staging()
        self._run_s3b()
        after_first = {
            name: (self.staging / name).read_bytes()
            for name in ("android.jar", "core-for-system-modules.jar")
        }
        self._run_s3b()
        for name, data in after_first.items():
            self.assertEqual((self.staging / name).read_bytes(), data,
                             f"{name}: rerun mutated the jar")

    def test_collision_raises_before_either_target_is_changed(self):
        self._build_to_s3_staging()
        # tamper one approved entry in core-for-system-modules.jar
        core = self.staging / "core-for-system-modules.jar"
        with zipfile.ZipFile(core, "a") as zf:
            zf.writestr(_S3B_ACONFIG[0], b"\xCA\xFE\xBA\xBETAMPERED")
        pre_core = core.read_bytes()
        pre_android = (self.staging / "android.jar").read_bytes()
        with self.assertRaises(RuntimeError) as ctx:
            self._run_s3b()
        self.assertIn("collision", str(ctx.exception))
        # neither target was mutated
        self.assertEqual(core.read_bytes(), pre_core)
        self.assertEqual((self.staging / "android.jar").read_bytes(),
                         pre_android)
        self.assertFalse(
            (self.staging / "android.jar.bak-prer8lib").exists())

    def test_android_manifest_remains_audited_bytes(self):
        self._build_to_s3_staging()
        self._run_s3b()
        with zipfile.ZipFile(self.staging / "android.jar") as zf:
            mf = zf.read("META-INF/MANIFEST.MF")
        self.assertEqual(mf, b.ANDROID_MANIFEST_BYTES)

    def test_all_stages_order_places_s3b_between_s3_and_s4(self):
        self.assertEqual(b.ALL_STAGES,
                         ("s0", "s1", "s2", "s3", "s3b", "s4"))

    def test_run_stages_invokes_s3b_between_s3_and_s4(self):
        from unittest import mock
        order = []
        stamps = {
            "stage_s0": lambda *a, **k: order.append("s0"),
            "stage_s1": lambda *a, **k: order.append("s1"),
            "stage_s2": lambda *a, **k: order.append("s2"),
            "stage_s3": lambda *a, **k: order.append("s3"),
            "stage_s3b": lambda *a, **k: order.append("s3b"),
            "stage_s4": lambda *a, **k: order.append("s4"),
        }
        with mock.patch.multiple(b, **stamps):
            b._run_stages(list(b.ALL_STAGES), self.base, self.staging,
                          self.merged, self.corelib, self.fwres,
                          unsupported_jar=self.unsupported,
                          aconfig_jar=self.aconfig,
                          keepanno_jar=self.keepanno, clean=True)
        self.assertEqual(order, ["s0", "s1", "s2", "s3", "s3b", "s4"])

    def test_default_stages_include_s3b_but_not_s4(self):
        self.assertIn("s3b", b.DEFAULT_STAGES.split(","))
        self.assertNotIn("s4", b.DEFAULT_STAGES.split(","))

    def test_default_source_jars_pinned(self):
        # core-libart default is shared with S3
        self.assertEqual(b.DEFAULT_UNSUPPORTEDAPPUSAGE_JAR.name,
                         "unsupportedappusage.jar")
        self.assertEqual(b.DEFAULT_ACONFIG_ANNOTATIONS_JAR.name,
                         "aconfig-annotations-lib.jar")
        self.assertEqual(b.DEFAULT_KEEPANNO_ANNOTATIONS_JAR.name,
                         "keepanno-annotations.jar")
        self.assertEqual(b.DEFAULT_KEEPANNO_ANNOTATIONS_JAR.parent.name,
                         "libs")


class FullPipelineWithS3bTest(_FixtureCase):
    """s0,s1,s2,s3,s3b,s4 full-pipeline determinism and S5 interaction."""

    def _build_full(self, target: Path) -> None:
        b.stage_s0(self.base, target, clean=True)
        b.stage_s1(target, self.merged)
        b.stage_s2(target)
        b.stage_s3(target, self.corelib)
        b.stage_s3b(target, self.corelib, self.unsupported, self.aconfig,
                    self.keepanno)
        b.stage_s4(target, self.fwres)

    def test_two_independent_builds_have_equal_inventories(self):
        self._build_full(self.staging)
        with tempfile.TemporaryDirectory() as td2:
            staging2 = Path(td2) / "android-SysUISdk-staging"
            # independent fixtures -> independent inputs
            base2 = _make_base_platform(Path(td2) / "android-37.0")
            merged2 = _make_merged_jar(Path(td2) / "android-merged.jar")
            corelib2 = _make_core_libart_jar(Path(td2) / "core-libart.jar")
            fwres2 = _make_framework_res_apk(Path(td2) / "framework-res.apk")
            unsup2 = _make_unsupportedappusage_jar(
                Path(td2) / "unsupportedappusage.jar")
            aconfig2 = _make_aconfig_annotations_jar(
                Path(td2) / "aconfig-annotations-lib.jar")
            keepanno2 = _make_keepanno_annotations_jar(
                Path(td2) / "keepanno-annotations.jar")
            b.stage_s0(base2, staging2, clean=True)
            b.stage_s1(staging2, merged2)
            b.stage_s2(staging2)
            b.stage_s3(staging2, corelib2)
            b.stage_s3b(staging2, corelib2, unsup2, aconfig2, keepanno2)
            b.stage_s4(staging2, fwres2)
            for name in ("android.jar", "core-for-system-modules.jar"):
                self.assertEqual(_jar_entries(self.staging / name),
                                 _jar_entries(staging2 / name),
                                 f"{name}: inventories differ between builds")

    def test_strict_s5_passes_when_live_built_through_same_stages(self):
        live = Path(self.tmp.name) / "android-SysUISdk-live"
        self._build_full(live)
        self._build_full(self.staging)
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 0)

    def test_s3_only_live_reports_exactly_35_extras_per_jar(self):
        live = Path(self.tmp.name) / "android-SysUISdk-live"
        self._build_to_s3(live)  # live fixture without S3b
        # staging: same stages + s3b (no s4, so the only delta is the 35)
        b.stage_s0(self.base, self.staging, clean=True)
        b.stage_s1(self.staging, self.merged)
        b.stage_s2(self.staging)
        b.stage_s3(self.staging, self.corelib)
        b.stage_s3b(self.staging, self.corelib, self.unsupported,
                    self.aconfig, self.keepanno)
        for name in ("android.jar", "core-for-system-modules.jar"):
            s = _jar_entries(self.staging / name)
            l = _jar_entries(live / name)
            extras = sorted(set(s) - set(l))
            missing = sorted(set(l) - set(s))
            self.assertEqual(extras, S3B_APPROVED_35,
                             f"{name}: staging-only entries are not exactly "
                             f"the 35 approved")
            self.assertEqual(missing, [], f"{name}: unexpected missing")
        # strict S5 reports DIFF before the apply-equivalent sync
        rc = b.stage_verify(self.staging, live)
        self.assertEqual(rc, 1)


# --- S5 verify with --expect-s4-delta --------------------------------------

class VerifyS4DeltaTest(_FixtureCase):
    def test_expect_s4_delta_passes_after_s4(self):
        # live = pre-S4 (stale res/); staging = post-S4 (fresh res/).
        live = self._build_live_like()      # s0-s3, stale res/
        self._build_staging_with_s4()       # s0-s4, fresh res/
        rc = b.stage_verify(self.staging, live, expect_s4_delta=True)
        self.assertEqual(rc, 0)

    def test_strict_verify_diffs_after_s4(self):
        # Without --expect-s4-delta the strict 7/7 check flags the resource
        # delta (staging no longer inventory-matches live after S4).
        live = self._build_live_like()
        self._build_staging_with_s4()
        rc = b.stage_verify(self.staging, live)  # no expect_s4_delta
        self.assertEqual(rc, 1)

    def test_expect_s4_delta_catches_non_resource_regression(self):
        # A non-resource entry mutation must still fail verify even with the
        # S4 delta allowed — only resource entries are exempted.
        live = self._build_live_like()
        self._build_staging_with_s4()
        with zipfile.ZipFile(self.staging / "android.jar", "r") as zf:
            entries = {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}
        entries["android/B.class"] = b"\xCA\xFE\xBA\xBEmutated"
        _make_jar(self.staging / "android.jar", entries)
        rc = b.stage_verify(self.staging, live, expect_s4_delta=True)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
