#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tools/build_sysuisdk.py (Task 045 single-entry composition).

All tests operate on throwaway fixture trees under tempfile.TemporaryDirectory.
The official SDK platforms (android-37.0, android-SysUISdk) and the AOSP tree
are NEVER touched.
"""
import os
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


# --- fixture helpers -------------------------------------------------------

def _make_zip(path: Path, entries: dict) -> None:
    """Create a zip/jar at path with {entry_name: bytes} (deterministic order)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(entries):
            zf.writestr(name, entries[name])


def _fake_class(tag: str) -> bytes:
    """Deterministic fake class bytes for a fixture entry."""
    return b"\xCA\xFE\xBA\xBE" + tag.encode("utf-8")


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

# --- Task 041 + dalvik frozen bridge (37 entries; D12 2026-08-29) ------------
# The two UnsupportedAppUsage classes are NOT bridged (D12 option 1): the
# 17 framework aggregate turbine JAR embeds them, and the framework aggregate
# is master over duplicates. Fake trees therefore place them in framework.jar.

_DALVIK_OPT = (
    "dalvik/annotation/optimization/DeadReferenceSafe.class",
    "dalvik/annotation/optimization/NeverCompile.class",
    "dalvik/annotation/optimization/NeverInline.class",
    "dalvik/annotation/optimization/ReachabilitySensitive.class",
)
_IO_UTILS = (
    "libcore/io/IoUtils.class",
    "libcore/io/IoUtils$FileReader.class",
)
_NATIVE_ALLOC = (
    "libcore/util/NativeAllocationRegistry.class",
    "libcore/util/NativeAllocationRegistry$CleanerRunner.class",
    "libcore/util/NativeAllocationRegistry$CleanerThunk.class",
    "libcore/util/NativeAllocationRegistry$Metrics.class",
)
_DDMC = (
    "org/apache/harmony/dalvik/ddmc/Chunk.class",
    "org/apache/harmony/dalvik/ddmc/ChunkHandler.class",
    "org/apache/harmony/dalvik/ddmc/DdmServer.class",
    "org/apache/harmony/dalvik/ddmc/DdmVmInternal.class",
)
_ACONFIG = ("com/android/aconfig/annotations/AconfigFlagAccessor.class",)
_KEEPANNO = tuple(
    f"com/android/tools/r8/keepanno/annotations/{n}.class" for n in (
        "AnnotationPattern", "CheckOptimizedOut", "CheckRemoved",
        "ClassAccessFlags", "ClassNamePattern", "FieldAccessFlags",
        "InstanceOfPattern", "KeepBinding", "KeepCondition", "KeepConstraint",
        "KeepEdge", "KeepForApi", "KeepItemKind", "KeepOption", "KeepTarget",
        "MemberAccessFlags", "MethodAccessFlags", "StringPattern",
        "TypePattern", "UsedByNative", "UsedByReflection", "UsesReflection"))

BRIDGE_37 = sorted(_DALVIK_OPT + _IO_UTILS + _NATIVE_ALLOC + _DDMC
                   + _ACONFIG + _KEEPANNO)
assert len(BRIDGE_37) == 37

# D12 regression set: the two classes that used to be bridged from
# unsupportedappusage.jar; they must now arrive via framework.jar.
FRAMEWORK_UNSUPPORTED = (
    "android/compat/annotation/UnsupportedAppUsage.class",
    "android/compat/annotation/UnsupportedAppUsage$Container.class",
)


def _fw_unsupported_payload(entry: str) -> bytes:
    return _fake_class("fw-turbine:" + entry)

IREMOTE_CALLBACK_AIDL = """\
// copyright header
package android.os;

import android.os.Bundle;

/** @hide */
oneway interface IRemoteCallback {
    void sendResult(in Bundle data);
}
"""
SCREENSHOT_REQUEST_AIDL = """\
// copyright header
package com.android.internal.util;

parcelable ScreenshotRequest;
"""


def _bridge_payload(entry: str) -> bytes:
    return _fake_class("bridge:" + entry)


def _make_fake_aosp(root: Path) -> Path:
    """A fake AOSP tree with all seven frozen inputs at their exact paths."""
    soong = root / "out/soong/.intermediates"
    # framework aggregate turbine jar: duplicate-of-stock entry with DIFFERENT
    # bytes (framework must win), a framework-only entry, res/ entries, and
    # (D12) the two UnsupportedAppUsage classes as turbine-embedded copies.
    fw_entries = {
        "android/app/Activity.class": _fake_class("fw-Activity"),
        "android/telephony/HiddenApi.class": _fake_class("fw-only"),
        "res/android.mime.types": b"fw-mime",
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong\n\n",
    }
    for entry in FRAMEWORK_UNSUPPORTED:
        fw_entries[entry] = _fw_unsupported_payload(entry)
    _make_zip(
        soong / "frameworks/base/framework/android_common/turbine-combined/framework.jar",
        fw_entries)
    # framework-res.apk: resource entries + excluded non-resource entries.
    _make_zip(
        soong / "frameworks/base/core/res/framework-res/android_common/framework-res.apk",
        {
            "resources.arsc": b"ARSCDATA-v2",
            "res/layout/activity_list.xml": b"<layout/>",
            "res/values/strings.xml": b"<strings/>",
            "AndroidManifest.xml": b"<manifest/>",      # must be excluded
            "META-INF/MANIFEST.MF": b"apkmf",           # must be excluded
            "META-INF/CERT.RSA": b"cert",               # must be excluded
            "assets/images/logo.png": b"png",           # must be excluded
        })
    # core-libart: the 14 bridge entries + unrelated entries.
    core_entries = {e: _bridge_payload(e) for e in
                    _DALVIK_OPT + _IO_UTILS + _NATIVE_ALLOC + _DDMC}
    core_entries["java/lang/Unrelated.class"] = _fake_class("core-unrelated")
    core_entries["dalvik/annotation/optimization/CriticalNative.class"] = \
        _fake_class("core-criticalnative")  # already in stock; not injected
    _make_zip(soong / "libcore/core-libart/android_common_apex31/javac/"
              "core-libart.jar", core_entries)
    # (D12) no unsupportedappusage.jar input anymore — the two classes come
    # from framework.jar above.
    _make_zip(
        soong / "frameworks/libs/modules-utils/java/aconfig-annotations-lib/"
        "linux_glibc_common/javac/aconfig-annotations-lib.jar",
        {
            "com/android/aconfig/annotations/AconfigFlagAccessor.class":
                _bridge_payload("com/android/aconfig/annotations/AconfigFlagAccessor.class"),
            "com/android/aconfig/annotations/AssumeTrueForR8.class":
                _fake_class("must-not-be-injected"),
            "com/android/aconfig/annotations/AssumeFalseForR8.class":
                _fake_class("must-not-be-injected-2"),
        })
    _make_zip(
        soong / "prebuilts/r8/keepanno-annotations/android_common/combined/"
        "keepanno-annotations.jar",
        {e: _bridge_payload(e) for e in _KEEPANNO})
    (root / "frameworks/base/core/java/android/os/IRemoteCallback.aidl").parent.mkdir(
        parents=True, exist_ok=True)
    (root / "frameworks/base/core/java/android/os/IRemoteCallback.aidl").write_text(
        IREMOTE_CALLBACK_AIDL, encoding="utf-8")
    (root / "frameworks/base/core/java/com/android/internal/util/"
     "ScreenshotRequest.aidl").parent.mkdir(parents=True, exist_ok=True)
    (root / "frameworks/base/core/java/com/android/internal/util/"
     "ScreenshotRequest.aidl").write_text(SCREENSHOT_REQUEST_AIDL,
                                          encoding="utf-8")
    return root


def _make_base_platform(root: Path) -> Path:
    """A minimal but realistic base platform fixture (android-37.0-like)."""
    root.mkdir(parents=True, exist_ok=True)
    # android.jar: Activity.class (framework will override), B.class
    # (stock-only survivor), stale resources, dalvik CriticalNative/FastNative.
    _make_zip(root / "android.jar", {
        "android/app/Activity.class": _fake_class("stock-Activity"),
        "android/B.class": _fake_class("stock-B"),
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: stub\n\n",
        "resources.arsc": b"STALE-ARSC",
        "res/values/strings.xml": b"<stale/>",
        "dalvik/annotation/optimization/CriticalNative.class":
            _fake_class("stock-criticalnative"),
        "dalvik/annotation/optimization/FastNative.class":
            _fake_class("stock-fastnative"),
    })
    _make_zip(root / "core-for-system-modules.jar", {
        "java/lang/X.class": _fake_class("core-X"),
        "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\nCreated-By: soong\n\n",
        "dalvik/annotation/optimization/CriticalNative.class":
            _fake_class("core-criticalnative"),
        "dalvik/annotation/optimization/FastNative.class":
            _fake_class("core-fastnative"),
    })
    (root / "framework.aidl").write_text("// stub aidl\n", encoding="utf-8")
    (root / "package.xml").write_text(_BASE_PKG_XML, encoding="utf-8")
    (root / "build.prop").write_text("ro.build.version.sdk=37\n", encoding="utf-8")
    (root / "source.properties").write_text(
        "Pkg.Desc=Android SDK Platform 37.0\n", encoding="utf-8")
    (root / "sdk.properties").write_text("component.sdk=stub\n", encoding="utf-8")
    d = root / "data"; d.mkdir(exist_ok=True)
    (d / "features.txt").write_text("f1\n", encoding="utf-8")
    (d / "res").mkdir(exist_ok=True); (d / "res" / "v.txt").write_text("r", encoding="utf-8")
    o = root / "optional"; o.mkdir(exist_ok=True)
    (o / "optional.json").write_text("[]\n", encoding="utf-8")
    # pre-existing backup files in the base — must be skipped, not copied.
    (root / "android.jar.orig").write_bytes(b"pristine-backup")
    return root


# --- Step 2: CLI and SDK-root discovery contract ----------------------------

class CliContractTest(unittest.TestCase):
    """The one public interface: --aosp-root (required) + discovery options."""

    def test_aosp_root_is_required(self):
        with self.assertRaises(SystemExit):
            b.build_arg_parser().parse_args([])

    def test_aosp_root_accepted(self):
        args = b.build_arg_parser().parse_args(["--aosp-root", "/tmp/aosp"])
        self.assertEqual(args.aosp_root, "/tmp/aosp")

    def test_no_stages_option(self):
        with self.assertRaises(SystemExit):
            b.build_arg_parser().parse_args(
                ["--aosp-root", "/a", "--stages", "s0,s1"])

    def test_no_verify_option(self):
        with self.assertRaises(SystemExit):
            b.build_arg_parser().parse_args(["--aosp-root", "/a", "--verify"])

    def test_no_apply_option(self):
        with self.assertRaises(SystemExit):
            b.build_arg_parser().parse_args(["--aosp-root", "/a", "--apply"])

    def test_replace_is_opt_in_flag(self):
        args = b.build_arg_parser().parse_args(["--aosp-root", "/a", "--replace"])
        self.assertTrue(args.replace)
        args = b.build_arg_parser().parse_args(["--aosp-root", "/a"])
        self.assertFalse(args.replace)

    def test_base_platform_defaults_to_android_37_0(self):
        args = b.build_arg_parser().parse_args(["--aosp-root", "/a"])
        self.assertEqual(args.base_platform, "android-37.0")


class SdkRootDiscoveryTest(unittest.TestCase):
    """Precedence: --sdk-root > ANDROID_SDK_ROOT > ANDROID_HOME > OS default."""

    def _discover(self, cli=None, env=None, system="Linux", home="/home/u"):
        return b.resolve_sdk_root(cli, env or {}, system, Path(home))

    def test_cli_value_wins(self):
        p = self._discover(cli="/opt/sdk", env={
            "ANDROID_SDK_ROOT": "/env/root", "ANDROID_HOME": "/env/home"})
        self.assertEqual(p, Path("/opt/sdk"))

    def test_android_sdk_root_beats_android_home(self):
        p = self._discover(env={"ANDROID_SDK_ROOT": "/env/root",
                                "ANDROID_HOME": "/env/home"})
        self.assertEqual(p, Path("/env/root"))

    def test_android_home_used_when_sdk_root_unset(self):
        p = self._discover(env={"ANDROID_HOME": "/env/home"})
        self.assertEqual(p, Path("/env/home"))

    def test_linux_default(self):
        self.assertEqual(self._discover(), Path("/home/u/Android/Sdk"))

    def test_macos_default(self):
        self.assertEqual(self._discover(system="Darwin"),
                         Path("/home/u/Library/Android/sdk"))

    def test_windows_default_uses_localappdata(self):
        p = self._discover(system="Windows", env={"LOCALAPPDATA": "C:\\Users\\u\\AppData\\Local"})
        self.assertEqual(p, Path("C:\\Users\\u\\AppData\\Local") / "Android" / "Sdk")

    def test_windows_default_without_localappdata(self):
        p = self._discover(system="Windows", env={})
        self.assertEqual(p, Path("/home/u/AppData/Local/Android/Sdk"))

    def test_home_expansion(self):
        p = b.resolve_sdk_root(None, {}, "Linux", Path("~/x"))
        self.assertFalse(str(p).startswith("~"))


class OutputResolutionTest(unittest.TestCase):

    def test_default_output_under_sdk_root(self):
        out = b.resolve_output(None, Path("/opt/sdk"))
        self.assertEqual(out, Path("/opt/sdk/platforms/android-SysUISdk"))

    def test_explicit_output_wins(self):
        out = b.resolve_output("/tmp/elsewhere", Path("/opt/sdk"))
        self.assertEqual(out, Path("/tmp/elsewhere"))


class BasePlatformResolutionTest(unittest.TestCase):

    def test_name_resolves_under_sdk_root_platforms(self):
        p = b.resolve_base_platform("android-37.0", Path("/opt/sdk"))
        self.assertEqual(p, Path("/opt/sdk/platforms/android-37.0"))

    def test_existing_path_used_as_is(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "mybase"; d.mkdir()
            p = b.resolve_base_platform(str(d), Path("/opt/sdk"))
            self.assertEqual(p, d)

    def test_explicit_relative_path_not_forced_under_platforms(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "relbase"; d.mkdir()
            cwd = Path.cwd()
            os.chdir(td)
            try:
                p = b.resolve_base_platform("relbase", Path("/opt/sdk"))
            finally:
                os.chdir(cwd)
            self.assertEqual(p, d)


# --- Step 4: exact AOSP input resolution ------------------------------------

class ExactInputResolutionTest(unittest.TestCase):
    """The frozen artifact map: seven exact AOSP-relative paths, no globbing."""

    def test_all_seven_inputs_resolve_under_aosp_root(self):
        with tempfile.TemporaryDirectory() as td:
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            self.assertEqual(len(inputs), 7)
            for key, rel in b.AOSP_INPUT_RELPATHS.items():
                self.assertEqual(inputs[key], aosp / rel,
                                 f"input {key} resolved to a wrong path")

    def test_d12_removed_unsupportedappusage_input(self):
        # D12 (2026-08-29): the former eighth input is gone from the frozen map.
        self.assertNotIn("unsupportedappusage_jar", b.AOSP_INPUT_RELPATHS)

    def test_missing_input_fails_with_exact_path(self):
        with tempfile.TemporaryDirectory() as td:
            aosp = _make_fake_aosp(Path(td) / "aosp")
            victim = aosp / b.AOSP_INPUT_RELPATHS["framework_jar"]
            victim.unlink()
            with self.assertRaises(b.BuildError) as ctx:
                b.resolve_inputs(aosp)
            self.assertIn(str(victim), str(ctx.exception))

    def test_missing_aidl_source_fails_with_exact_path(self):
        with tempfile.TemporaryDirectory() as td:
            aosp = _make_fake_aosp(Path(td) / "aosp")
            victim = (aosp / b.AOSP_INPUT_RELPATHS["screenshot_request_aidl"])
            victim.unlink()
            with self.assertRaises(b.BuildError) as ctx:
                b.resolve_inputs(aosp)
            self.assertIn(str(victim), str(ctx.exception))

    def test_frozen_map_is_exactly_the_spec_paths(self):
        self.assertEqual(b.AOSP_INPUT_RELPATHS, {
            "framework_jar":
                "out/soong/.intermediates/frameworks/base/framework/"
                "android_common/turbine-combined/framework.jar",
            "framework_res_apk":
                "out/soong/.intermediates/frameworks/base/core/res/"
                "framework-res/android_common/framework-res.apk",
            "core_libart_jar":
                "out/soong/.intermediates/libcore/core-libart/"
                "android_common_apex31/javac/core-libart.jar",
            "aconfig_annotations_jar":
                "out/soong/.intermediates/frameworks/libs/modules-utils/"
                "java/aconfig-annotations-lib/linux_glibc_common/javac/"
                "aconfig-annotations-lib.jar",
            "keepanno_jar":
                "out/soong/.intermediates/prebuilts/r8/keepanno-annotations/"
                "android_common/combined/keepanno-annotations.jar",
            "iremote_callback_aidl":
                "frameworks/base/core/java/android/os/IRemoteCallback.aidl",
            "screenshot_request_aidl":
                "frameworks/base/core/java/com/android/internal/util/"
                "ScreenshotRequest.aidl",
        })


class AidlDerivationTest(unittest.TestCase):
    """Hidden AIDL declarations must be derived from primary sources."""

    def test_derives_interface_declaration(self):
        decl = b.derive_aidl_declaration(
            IREMOTE_CALLBACK_AIDL, "android.os.IRemoteCallback", "interface")
        self.assertEqual(decl, "interface android.os.IRemoteCallback;")

    def test_derives_parcelable_declaration(self):
        decl = b.derive_aidl_declaration(
            SCREENSHOT_REQUEST_AIDL,
            "com.android.internal.util.ScreenshotRequest", "parcelable")
        self.assertEqual(decl,
                         "parcelable com.android.internal.util.ScreenshotRequest;")

    def test_wrong_package_rejected(self):
        with self.assertRaises(b.BuildError):
            b.derive_aidl_declaration(
                IREMOTE_CALLBACK_AIDL, "android.os.Other", "interface")

    def test_wrong_name_rejected(self):
        with self.assertRaises(b.BuildError):
            b.derive_aidl_declaration(
                IREMOTE_CALLBACK_AIDL, "android.os.IOtherCallback", "interface")

    def test_wrong_kind_rejected(self):
        with self.assertRaises(b.BuildError):
            b.derive_aidl_declaration(
                SCREENSHOT_REQUEST_AIDL,
                "com.android.internal.util.ScreenshotRequest", "interface")

    def test_missing_package_rejected(self):
        with self.assertRaises(b.BuildError):
            b.derive_aidl_declaration("interface Foo;\n", "a.Foo", "interface")

    def test_missing_declaration_rejected(self):
        with self.assertRaises(b.BuildError):
            b.derive_aidl_declaration("package a.b;\n", "a.b.Foo", "interface")

    def test_derives_both_hidden_declarations_from_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            aosp = _make_fake_aosp(Path(td) / "aosp")
            decls = b.derive_hidden_aidl_declarations(aosp)
            self.assertEqual(decls, [
                "interface android.os.IRemoteCallback;",
                "parcelable com.android.internal.util.ScreenshotRequest;",
            ])


# --- Step 6: deterministic JAR/resource composition --------------------------

def _zip_bytes(data: bytes) -> dict[str, bytes]:
    """Read a zip/jar from bytes into {entry_name: bytes} (non-dir)."""
    import io
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        return {i.filename: zf.read(i.filename) for i in zf.infolist()
                if not i.is_dir()}


class AndroidJarCompositionTest(unittest.TestCase):
    """android.jar: stock base + framework overlay + APK resources + bridge."""

    def _compose(self, td: Path, bridge: dict | None = None) -> dict[str, bytes]:
        base = _make_base_platform(Path(td) / "base")
        aosp = _make_fake_aosp(Path(td) / "aosp")
        data = b.compose_android_jar(
            base / "android.jar",
            aosp / b.AOSP_INPUT_RELPATHS["framework_jar"],
            aosp / b.AOSP_INPUT_RELPATHS["framework_res_apk"],
            bridge or {})
        return _zip_bytes(data)

    def test_framework_aggregate_wins_duplicate_stock_class(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            self.assertEqual(entries["android/app/Activity.class"],
                             _fake_class("fw-Activity"))

    def test_stock_only_entries_survive(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            self.assertEqual(entries["android/B.class"], _fake_class("stock-B"))

    def test_framework_only_entries_survive(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            self.assertEqual(entries["android/telephony/HiddenApi.class"],
                             _fake_class("fw-only"))

    def test_framework_res_resources_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            self.assertEqual(entries["resources.arsc"], b"ARSCDATA-v2")
            self.assertEqual(entries["res/layout/activity_list.xml"],
                             b"<layout/>")
            self.assertEqual(entries["res/values/strings.xml"], b"<strings/>")

    def test_resource_set_is_exactly_the_apk_set(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            res_names = {n for n in entries
                         if n == "resources.arsc" or n.startswith("res/")}
            self.assertEqual(res_names, {
                "resources.arsc", "res/layout/activity_list.xml",
                "res/values/strings.xml"})
            # stale stock resource gone
            self.assertNotIn("res/values/strings.xml:stale", res_names)
            # framework-jar res/ entry not carried (APK is the resource master)

    def test_framework_res_non_resource_entries_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            self.assertNotIn("AndroidManifest.xml", entries)
            self.assertNotIn("assets/images/logo.png", entries)
            # apk signing metadata excluded; jar manifest comes from the
            # framework aggregate (framework wins duplicates)
            self.assertEqual(entries["META-INF/MANIFEST.MF"],
                             b"Manifest-Version: 1.0\nCreated-By: soong\n\n")
            self.assertNotIn("META-INF/CERT.RSA", entries)

    def test_stock_stale_resources_removed(self):
        with tempfile.TemporaryDirectory() as td:
            entries = self._compose(Path(td))
            # stock had resources.arsc=STALE-ARSC and res/values/strings.xml=<stale/>
            self.assertNotEqual(entries["resources.arsc"], b"STALE-ARSC")
            self.assertNotIn(b"<stale/>", entries["res/values/strings.xml"])

    def test_duplicate_names_in_framework_jar_fail(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            fw = aosp / b.AOSP_INPUT_RELPATHS["framework_jar"]
            with zipfile.ZipFile(fw, "a") as zf:  # append a duplicate name
                zf.writestr("android/telephony/HiddenApi.class", b"dupe")
            with self.assertRaises(b.BuildError):
                b.compose_android_jar(base / "android.jar", fw,
                                      aosp / b.AOSP_INPUT_RELPATHS[
                                          "framework_res_apk"], {})

    def test_duplicate_names_in_res_apk_fail(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            apk = aosp / b.AOSP_INPUT_RELPATHS["framework_res_apk"]
            with zipfile.ZipFile(apk, "a") as zf:
                zf.writestr("res/values/strings.xml", b"dupe")
            with self.assertRaises(b.BuildError):
                b.compose_android_jar(base / "android.jar",
                                      aosp / b.AOSP_INPUT_RELPATHS[
                                          "framework_jar"], apk, {})

    def test_duplicate_names_in_base_jar_fail(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            with zipfile.ZipFile(base / "android.jar", "a") as zf:
                zf.writestr("android/B.class", b"dupe")
            with self.assertRaises(b.BuildError):
                b.compose_android_jar(base / "android.jar",
                                      aosp / b.AOSP_INPUT_RELPATHS[
                                          "framework_jar"],
                                      aosp / b.AOSP_INPUT_RELPATHS[
                                          "framework_res_apk"], {})

    def test_identical_builds_produce_byte_identical_jars(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            kwargs = dict(
                base_jar=base / "android.jar",
                framework_jar=aosp / b.AOSP_INPUT_RELPATHS["framework_jar"],
                framework_res_apk=aosp / b.AOSP_INPUT_RELPATHS[
                    "framework_res_apk"],
                bridge={})
            first = b.compose_android_jar(**kwargs)
            second = b.compose_android_jar(**kwargs)
            self.assertEqual(first, second)


class CoreModulesJarCompositionTest(unittest.TestCase):

    def test_preserves_stock_entries(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            data = b.compose_core_modules_jar(base / "core-for-system-modules.jar",
                                             {})
            entries = _zip_bytes(data)
            self.assertEqual(entries["java/lang/X.class"], _fake_class("core-X"))
            self.assertEqual(
                entries["dalvik/annotation/optimization/CriticalNative.class"],
                _fake_class("core-criticalnative"))

    def test_deterministic_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            first = b.compose_core_modules_jar(
                base / "core-for-system-modules.jar", {})
            second = b.compose_core_modules_jar(
                base / "core-for-system-modules.jar", {})
            self.assertEqual(first, second)


# --- Step 8: frozen 37-entry bridge (D12) ------------------------------------

class BridgeAllowlistTest(unittest.TestCase):
    """The bridge is exactly Task 041's 35 + the 4 dalvik entries (D12: minus
    the 2 UnsupportedAppUsage classes now provided by the framework JAR)."""

    def test_allowlist_is_exactly_37_frozen_entries(self):
        self.assertEqual(sorted(b.BRIDGE_ENTRIES), BRIDGE_37)
        self.assertEqual(len(b.BRIDGE_ENTRIES), 37)

    def test_unsupported_app_usage_is_not_bridged(self):
        # D12 regression: the two classes must not be bridge entries.
        for entry in FRAMEWORK_UNSUPPORTED:
            self.assertNotIn(entry, b.BRIDGE_ENTRIES)

    def test_assume_true_for_r8_is_excluded(self):
        self.assertNotIn(
            "com/android/aconfig/annotations/AssumeTrueForR8.class",
            b.BRIDGE_ENTRIES)


class BridgeLoadTest(unittest.TestCase):

    def test_load_bridge_returns_source_identical_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            bridge = b.load_bridge(inputs)
            self.assertEqual(sorted(bridge), BRIDGE_37)
            for entry in _DALVIK_OPT + _IO_UTILS + _NATIVE_ALLOC + _DDMC:
                self.assertEqual(bridge[entry], _bridge_payload(entry))
            self.assertEqual(
                bridge["com/android/aconfig/annotations/AconfigFlagAccessor.class"],
                _bridge_payload(
                    "com/android/aconfig/annotations/AconfigFlagAccessor.class"))
            for entry in _KEEPANNO:
                self.assertEqual(bridge[entry], _bridge_payload(entry))

    def test_missing_declared_source_entry_fails(self):
        with tempfile.TemporaryDirectory() as td:
            aosp = _make_fake_aosp(Path(td) / "aosp")
            victim = (aosp / b.AOSP_INPUT_RELPATHS["keepanno_jar"])
            entries = {e: _bridge_payload(e) for e in _KEEPANNO}
            del entries["com/android/tools/r8/keepanno/annotations/KeepEdge.class"]
            _make_zip(victim, entries)
            inputs = b.resolve_inputs(aosp)
            with self.assertRaises(b.BuildError):
                b.load_bridge(inputs)

    def test_both_target_jars_contain_the_complete_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            bridge = b.load_bridge(inputs)
            android = _zip_bytes(b.compose_android_jar(
                base / "android.jar", inputs["framework_jar"],
                inputs["framework_res_apk"], bridge))
            core = _zip_bytes(b.compose_core_modules_jar(
                base / "core-for-system-modules.jar", bridge))
            for jar_name, entries in (("android.jar", android),
                                      ("core-for-system-modules.jar", core)):
                for entry in BRIDGE_37:
                    self.assertEqual(entries[entry], _bridge_payload(entry),
                                     f"{jar_name} missing/wrong bridge entry "
                                     f"{entry}")
            # D12 regression: the two UnsupportedAppUsage classes live in the
            # final android.jar with the framework aggregate (turbine) bytes.
            for entry in FRAMEWORK_UNSUPPORTED:
                self.assertEqual(
                    android[entry], _fw_unsupported_payload(entry),
                    f"android.jar missing framework-borne entry {entry}")
            # and they are NOT injected into core-for-system-modules.jar
            for entry in FRAMEWORK_UNSUPPORTED:
                self.assertNotIn(
                    entry, core,
                    f"core jar must not carry framework-borne entry {entry}")

    def test_unlisted_siblings_are_absent(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            bridge = b.load_bridge(inputs)
            android = _zip_bytes(b.compose_android_jar(
                base / "android.jar", inputs["framework_jar"],
                inputs["framework_res_apk"], bridge))
            core = _zip_bytes(b.compose_core_modules_jar(
                base / "core-for-system-modules.jar", bridge))
            for entries in (android, core):
                self.assertNotIn(
                    "com/android/aconfig/annotations/AssumeTrueForR8.class",
                    entries)
                self.assertNotIn(
                    "com/android/aconfig/annotations/AssumeFalseForR8.class",
                    entries)
                self.assertNotIn("java/lang/Unrelated.class", entries)
            # stock CriticalNative/FastNative stay stock bytes (not re-injected)
            self.assertEqual(
                android["dalvik/annotation/optimization/CriticalNative.class"],
                _fake_class("stock-criticalnative"))

    def test_equal_bytes_bridge_entry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            # pre-inject one bridge entry with EQUAL bytes into the stock jar
            with zipfile.ZipFile(base / "android.jar", "a") as zf:
                zf.writestr(_DALVIK_OPT[0], _bridge_payload(_DALVIK_OPT[0]))
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            bridge = b.load_bridge(inputs)
            android = _zip_bytes(b.compose_android_jar(
                base / "android.jar", inputs["framework_jar"],
                inputs["framework_res_apk"], bridge))
            self.assertEqual(android[_DALVIK_OPT[0]],
                             _bridge_payload(_DALVIK_OPT[0]))

    def test_unequal_bytes_collision_is_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            with zipfile.ZipFile(base / "android.jar", "a") as zf:
                zf.writestr(_DALVIK_OPT[0], b"\xCA\xFE\xBA\xBEdifferent")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            bridge = b.load_bridge(inputs)
            with self.assertRaises(b.BuildError):
                b.compose_android_jar(base / "android.jar",
                                      inputs["framework_jar"],
                                      inputs["framework_res_apk"], bridge)

    def test_unequal_bytes_collision_fatal_for_core_jar(self):
        with tempfile.TemporaryDirectory() as td:
            base = _make_base_platform(Path(td) / "base")
            with zipfile.ZipFile(base / "core-for-system-modules.jar", "a") as zf:
                zf.writestr(_KEEPANNO[0], b"\xCA\xFE\xBA\xBEdifferent")
            aosp = _make_fake_aosp(Path(td) / "aosp")
            inputs = b.resolve_inputs(aosp)
            bridge = b.load_bridge(inputs)
            with self.assertRaises(b.BuildError):
                b.compose_core_modules_jar(
                    base / "core-for-system-modules.jar", bridge)


# --- Step 10: transaction, marker, and replace protection --------------------

def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree_inventory(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): _sha256_file(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


class TransactionTest(unittest.TestCase):

    def _build(self, td: Path, output: Path, replace: bool = False):
        base = _make_base_platform(td / "base")
        aosp = _make_fake_aosp(td / "aosp")
        return b.build_platform(aosp_root=aosp, base_platform=base,
                                output=output, replace=replace)

    def test_success_publishes_output_and_cleans_staging(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            parent = td / "platforms"; parent.mkdir()
            output = parent / "android-SysUISdk"
            captured = {}
            orig_validate = b._validate_platform
            def spy(staging, *a, **kw):
                captured["staging"] = Path(staging)
                return orig_validate(staging, *a, **kw)
            b._validate_platform = spy
            try:
                self._build(td, output)
            finally:
                b._validate_platform = orig_validate
            self.assertTrue(output.is_dir())
            # staging was a sibling of the output, inside the same parent
            self.assertEqual(captured["staging"].parent, output.parent)
            self.assertNotEqual(captured["staging"], output)
            # staging is gone; the parent holds only the published output
            self.assertEqual(list(parent.iterdir()), [output])

    def test_injected_failure_cleans_staging_and_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            parent = td / "platforms"; parent.mkdir()
            output = parent / "android-SysUISdk"
            def boom(staging, *a, **kw):
                raise b.BuildError("injected validation failure")
            orig_validate = b._validate_platform
            b._validate_platform = boom
            try:
                with self.assertRaises(b.BuildError):
                    self._build(td, output)
            finally:
                b._validate_platform = orig_validate
            self.assertFalse(output.exists())
            self.assertEqual(list(parent.iterdir()), [])  # staging cleaned

    def test_default_refusal_for_existing_unmarked_output(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"; output.mkdir()
            (output / "junk").write_text("x", encoding="utf-8")
            with self.assertRaises(b.BuildError):
                self._build(td, output)

    def test_default_refusal_for_existing_marked_output(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"
            self._build(td, output)  # first build succeeds (marker written)
            with self.assertRaises(b.BuildError):
                self._build(td, output, replace=False)

    def test_replace_refused_for_unmarked_output(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"; output.mkdir()
            (output / "junk").write_text("x", encoding="utf-8")
            with self.assertRaises(b.BuildError):
                self._build(td, output, replace=True)

    def test_replace_succeeds_for_marked_output(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            parent = td / "p"; parent.mkdir()
            output = parent / "out"
            self._build(td, output)
            first_marker = (output / b.MARKER_NAME).read_bytes()
            self._build(td, output, replace=True)
            self.assertTrue(output.is_dir())
            self.assertEqual((output / b.MARKER_NAME).read_bytes(),
                             first_marker)
            # no leftover .old-* / staging siblings
            self.assertEqual(list(parent.iterdir()), [output])

    def test_base_output_alias_refused(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            base = _make_base_platform(td / "base")
            aosp = _make_fake_aosp(td / "aosp")
            with self.assertRaises(b.BuildError):
                b.build_platform(aosp_root=aosp, base_platform=base,
                                 output=base)
            with self.assertRaises(b.BuildError):
                b.build_platform(aosp_root=aosp, base_platform=base,
                                 output=base / "nested")

    def test_no_backup_artifacts_in_generated_platform(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"
            self._build(td, output)
            for p in output.rglob("*"):
                self.assertFalse(p.name.endswith(".orig"), p)
                self.assertNotIn(".bak-", p.name, p)
            # base backup files were skipped, not copied
            self.assertFalse((output / "android.jar.orig").exists())

    def test_base_platform_untouched(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            base = _make_base_platform(td / "base")
            aosp = _make_fake_aosp(td / "aosp")
            before = _tree_inventory(base)
            b.build_platform(aosp_root=aosp, base_platform=base,
                             output=td / "out")
            self.assertEqual(_tree_inventory(base), before)

    def test_data_and_optional_copied(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"
            self._build(td, output)
            self.assertEqual((output / "data" / "features.txt").read_text(),
                             "f1\n")
            self.assertEqual((output / "data" / "res" / "v.txt").read_text(),
                             "r")
            self.assertEqual((output / "optional" / "optional.json").read_text(),
                             "[]\n")

    def test_framework_aidl_gets_both_decls_once(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"
            self._build(td, output)
            text = (output / "framework.aidl").read_text(encoding="utf-8")
            self.assertIn("interface android.os.IRemoteCallback;", text)
            self.assertIn(
                "parcelable com.android.internal.util.ScreenshotRequest;", text)
            self.assertEqual(
                text.count("interface android.os.IRemoteCallback;"), 1)
            self.assertEqual(
                text.count(
                    "parcelable com.android.internal.util.ScreenshotRequest;"),
                1)

    def test_package_xml_metadata(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            output = td / "out"
            self._build(td, output)
            text = (output / "package.xml").read_text(encoding="utf-8")
            self.assertIn('path="platforms;android-SysUISdk"', text)
            self.assertIn("<api-level>37</api-level>", text)
            self.assertIn("<codename>SysUISdk</codename>", text)

    def test_marker_records_provenance(self):
        import json
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            aosp = _make_fake_aosp(td / "aosp")
            output = td / "out"
            self._build(td, output)
            marker = json.loads(
                (output / b.MARKER_NAME).read_text(encoding="utf-8"))
            self.assertEqual(marker["schema_version"],
                             b.MARKER_SCHEMA_VERSION)
            self.assertEqual(marker["tool_version"], b.TOOL_VERSION)
            fw = aosp / b.AOSP_INPUT_RELPATHS["framework_jar"]
            self.assertEqual(marker["inputs"]["framework_jar"]["sha256"],
                             _sha256_file(fw))
            self.assertEqual(marker["inputs"]["framework_jar"]["path"],
                             b.AOSP_INPUT_RELPATHS["framework_jar"])
            self.assertIn("android.jar", marker["generated"]["inventory"])
            # base platform identity is normalized (name, not absolute path)
            self.assertEqual(marker["base_platform"]["name"], "base")
            self.assertNotIn(str(td), json.dumps(marker))

    def test_two_independent_builds_are_identical(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            out1 = td / "one"
            out2 = td / "two"
            self._build(td, out1)
            self._build(td, out2)
            self.assertEqual(_tree_inventory(out1), _tree_inventory(out2))


class CliEndToEndTest(unittest.TestCase):

    def test_run_builds_output_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            _make_base_platform(td / "sdk" / "platforms" / "android-37.0")
            aosp = _make_fake_aosp(td / "aosp")
            rc = b.run(["--aosp-root", str(aosp),
                        "--sdk-root", str(td / "sdk")])
            self.assertEqual(rc, 0)
            output = td / "sdk" / "platforms" / "android-SysUISdk"
            self.assertTrue((output / "android.jar").is_file())
            self.assertTrue((output / b.MARKER_NAME).is_file())

    def test_run_reports_build_error_as_exit_one(self):
        with tempfile.TemporaryDirectory() as td_str:
            td = Path(td_str)
            _make_base_platform(td / "sdk" / "platforms" / "android-37.0")
            rc = b.run(["--aosp-root", str(td / "no-such-aosp"),
                        "--sdk-root", str(td / "sdk")])
            self.assertEqual(rc, 1)
            self.assertFalse(
                (td / "sdk" / "platforms" / "android-SysUISdk").exists())


if __name__ == "__main__":
    unittest.main()
