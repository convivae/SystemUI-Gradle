import importlib.util
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

# The script under test imports aosp_paths; make tools/ importable no matter
# where the test runner is invoked from.
_TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TOOLS_DIR))

import aosp_paths

_SCRIPT = _TOOLS_DIR / "package_aconfig_jars.py"
_spec = importlib.util.spec_from_file_location("package_aconfig_jars", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

RUNTIME_CLASSES = (
    "CustomFeatureFlags",
    "FakeFeatureFlagsImpl",
    "FeatureFlags",
    "FeatureFlagsImpl",
    "Flags",
)

BATCH2_CONFIGS = {
    "systemui-flags": (
        "frameworks/base/packages/SystemUI/aconfig/"
        "com_android_systemui_flags_lib/android_common/javac/"
        "com_android_systemui_flags_lib.jar",
        Path("libs/systemui-flags.jar"),
        "com.android.systemui",
    ),
    "notification-flags": (
        "frameworks/base/services/core/java/com/android/server/notification/"
        "notification_flags_lib/android_common/javac/notification_flags_lib.jar",
        Path("libs/notification-flags.jar"),
        "com.android.server.notification",
    ),
    "launcher3-flags": (
        "packages/apps/Launcher3/aconfig/"
        "com_android_launcher3_flags_lib/android_common/javac/"
        "com_android_launcher3_flags_lib.jar",
        Path("libs/launcher3-flags.jar"),
        "com.android.launcher3",
    ),
    "settingslib-widget-flags": (
        "frameworks/base/packages/SettingsLib/IllustrationPreference/"
        "settingslib_illustrationpreference_flags_lib/android_common/javac/"
        "settingslib_illustrationpreference_flags_lib.jar",
        Path("libs/settingslib-widget-flags.jar"),
        "com.android.settingslib.widget.flags",
    ),
    # AOSP-17 (Task 071): settingslib-selector-flags removed upstream —
    # SelectorWithWidgetPreference no longer declares an aconfig flags lib.
}


#: AOSP-17 (Task 071): six family members whose standalone javac outputs no
#: longer exist — their CONFIGS source points at the framework-minus-apex
#: javac shard directory (AGGREGATE_JAVAC_DIR) and the five-class subsets are
#: extracted via extract_aggregate_subset().
AGGREGATE_MEMBERS = {
    "smartspace-flags": (
        Path("libs/smartspace-flags.jar"),
        "android.app.smartspace.flags",
    ),
    "usb-flags": (
        Path("libs/usb-flags.jar"),
        "android.hardware.usb.flags",
    ),
    "net-platform-flags": (
        Path("libs/net-platform-flags.jar"),
        "android.net.platform.flags",
    ),
    "permission-flags": (
        Path("libs/permission-flags.jar"),
        "android.permission.flags",
    ),
    "service-controls-flags": (
        Path("libs/service-controls-flags.jar"),
        "android.service.controls.flags",
    ),
    "device-state-feature-flags": (
        Path("libs/device-state-feature-flags.jar"),
        "android.hardware.devicestate.feature.flags",
    ),
}

#: Module-owning javac configs that survived AOSP-17 unchanged.
BATCH3_CONFIGS = {
    # Task 055 batch: framework hidden-twin family members with surviving
    # standalone android_common/javac outputs.
    "content-pm-flags": (
        "android.content.pm.flags-aconfig-java",
        Path("libs/content-pm-flags.jar"),
        "android.content.pm",
    ),
    "biometrics-flags": (
        "android.hardware.biometrics.flags-aconfig-java",
        Path("libs/biometrics-flags.jar"),
        "android.hardware.biometrics",
    ),
    "provider-flags": (
        "android.provider.flags-aconfig-java",
        Path("libs/provider-flags.jar"),
        "android.provider",
    ),
    "service-notification-flags": (
        "android.service.notification.flags-aconfig-java",
        Path("libs/service-notification-flags.jar"),
        "android.service.notification",
    ),
    # AOSP-17 (Task 071): security-flags and quickaccesswallet-flags removed
    # upstream — the .aconfig packages were renamed (android.security /
    # android.service.quickaccesswallet); the old runtime packages exist
    # nowhere in the 17 tree and SystemUI-17 has zero imports of them.
}


def write_runtime_jar(path, package="com.example.flags", classes=RUNTIME_CLASSES):
    """Write a synthetic aconfig runtime JAR with the given class names."""
    prefix = package.replace(".", "/")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0\r\n\r\n")
        for name in classes:
            archive.writestr(f"{prefix}/{name}.class", b"class-bytes")
            if name != "FakeFeatureFlagsImpl":
                archive.writestr(f"{prefix}/{name}.uau", b"uau-bytes")


class TestAconfigJarPackaging(unittest.TestCase):
    def test_runtime_config_uses_javac_not_turbine(self):
        source, destination, package = module.CONFIGS["systemui-shared-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/systemui-shared-flags.jar"))
        self.assertEqual(package, "com.android.systemui.shared")

    def test_wifi_flags_config(self):
        source, destination, package = module.CONFIGS["wifi-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/wifi-flags.jar"))
        self.assertEqual(package, "com.android.wifi.flags")

    def test_wm_shell_flags_config(self):
        source, destination, package = module.CONFIGS["wm-shell-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/wm-shell-flags.jar"))
        self.assertEqual(package, "com.android.wm.shell")

    def test_window_flags_config_uses_framework_owned_javac_runtime(self):
        source, destination, package = module.CONFIGS["window-flags"]
        self.assertEqual(
            source,
            module.AOSP_INTERMEDIATES
            / "frameworks/base"
            / "com.android.window.flags.window-aconfig-java"
            / "android_common/javac"
            / "com.android.window.flags.window-aconfig-java.jar",
        )
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/window-flags.jar"))
        self.assertEqual(package, "com.android.window.flags")

    def test_device_state_feature_flags_config_uses_aggregate_shards(self):
        """AOSP-17 (Task 071)：六族 aggregate 成员 source 指向 shard 目录。"""
        source, destination, package = module.CONFIGS["device-state-feature-flags"]
        self.assertEqual(source, module.AGGREGATE_JAVAC_DIR)
        self.assertIn("framework-minus-apex", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/device-state-feature-flags.jar"))
        self.assertEqual(package, "android.hardware.devicestate.feature.flags")
        self.assertIn("device-state-feature-flags", module.AGGREGATE_FAMILY)
        self.assertIn("device-state-feature-flags", module.FRAMEWORK_FAMILY)

    def test_android_os_flags_config_uses_framework_owned_javac_runtime(self):
        source, destination, package = module.CONFIGS["android-os-flags"]
        self.assertEqual(
            source,
            module.AOSP_INTERMEDIATES
            / "frameworks/base"
            / "android.os.flags-aconfig-java"
            / "android_common/javac"
            / "android.os.flags-aconfig-java.jar",
        )
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/android-os-flags.jar"))
        self.assertEqual(package, "android.os")

    def test_batch2_config_matrix(self):
        # The five Batch-2 artifacts must map exact owning Soong javac sources
        # to their destinations and runtime packages.
        for name, (suffix, destination, package) in BATCH2_CONFIGS.items():
            with self.subTest(config=name):
                self.assertIn(name, module.CONFIGS)
                source = module.CONFIGS[name][0]
                self.assertEqual(source, module.AOSP_INTERMEDIATES / suffix)
                self.assertIn("/javac/", str(source))
                self.assertNotIn("turbine", str(source))
                self.assertEqual(module.CONFIGS[name][1], destination)
                self.assertEqual(module.CONFIGS[name][2], package)

    def test_batch3_config_matrix(self):
        # The module-owning Batch-3 survivors must map exact owning Soong javac
        # sources to their destinations and runtime packages.
        for name, (soong_module, destination, package) in BATCH3_CONFIGS.items():
            with self.subTest(config=name):
                self.assertIn(name, module.CONFIGS)
                source = module.CONFIGS[name][0]
                self.assertEqual(
                    source,
                    module.AOSP_INTERMEDIATES
                    / "frameworks/base"
                    / soong_module
                    / "android_common/javac"
                    / f"{soong_module}.jar",
                )
                self.assertNotIn("turbine", str(source))
                self.assertEqual(module.CONFIGS[name][1], destination)
                self.assertEqual(module.CONFIGS[name][2], package)

    def test_aggregate_members_point_at_shard_directory(self):
        # AOSP-17 (Task 071): aggregate members' sources are the shard dir.
        for name, (destination, package) in AGGREGATE_MEMBERS.items():
            with self.subTest(config=name):
                self.assertIn(name, module.CONFIGS)
                source = module.CONFIGS[name][0]
                self.assertEqual(source, module.AGGREGATE_JAVAC_DIR)
                self.assertIn(name, module.AGGREGATE_FAMILY)
                self.assertEqual(module.CONFIGS[name][1], destination)
                self.assertEqual(module.CONFIGS[name][2], package)

    def test_upstream_deleted_entries_are_gone(self):
        # AOSP-17 (Task 071): upstream-deleted aconfig packages must not
        # resurrect anywhere in the config surface.
        for name in ("security-flags", "quickaccesswallet-flags",
                     "settingslib-selector-flags"):
            self.assertNotIn(name, module.CONFIGS)
            self.assertNotIn(name, module.FRAMEWORK_FAMILY)
            self.assertNotIn(name, module.AGGREGATE_FAMILY)
            self.assertNotIn(name, module.TURBINE_BASELINE_CONFIGS)

    def test_framework_family_membership_and_shape(self):
        # AOSP-17 (Task 071): the 12 framework hidden-twin family configs
        # (3 from tasks 053/054 plus the 11 from task 055, minus the two
        # upstream-renamed members security-flags/quickaccesswallet-flags)
        # are exactly FRAMEWORK_FAMILY, split between module-owning javac
        # outputs and the framework-minus-apex aggregate shard directory.
        self.assertEqual(len(module.FRAMEWORK_FAMILY), 12)
        self.assertEqual(
            module.FRAMEWORK_FAMILY,
            frozenset(BATCH3_CONFIGS) | set(AGGREGATE_MEMBERS) | {
                "window-flags",
                "android-os-flags",
            },
        )
        self.assertEqual(
            module.MERGED_FRAMEWORK_JAR, Path("libs/systemui-aconfig-flags.jar")
        )
        for name in module.FRAMEWORK_FAMILY:
            with self.subTest(config=name):
                source = module.CONFIGS[name][0]
                self.assertIn("frameworks/base/", str(source))
                self.assertNotIn("turbine", str(source))
                if name in module.AGGREGATE_FAMILY:
                    self.assertEqual(source, module.AGGREGATE_JAVAC_DIR)
                else:
                    self.assertIn("/javac/", str(source))

    def test_copy_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "javac" / "flags.jar"
            source.parent.mkdir()
            write_runtime_jar(source)
            destination = root / "out.jar"
            module.copy_jar(source, destination, "com.example.flags")
            self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_copy_preserves_bytes_for_each_config(self):
        # Reuse the byte-identical copy assertion for every CONFIGS entry so a
        # future addition cannot silently skip the turbine/runtime check.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, (_source, _destination, package) in module.CONFIGS.items():
                with self.subTest(config=name):
                    fake_source = root / name / "javac" / "flags.jar"
                    fake_source.parent.mkdir(parents=True)
                    write_runtime_jar(fake_source, package=package)
                    destination = root / f"{name}.out.jar"
                    module.copy_jar(fake_source, destination, package)
                    self.assertEqual(
                        destination.read_bytes(), fake_source.read_bytes()
                    )

    def test_rejects_incomplete_runtime_class_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "javac" / "flags.jar"
            source.parent.mkdir()
            incomplete = tuple(RUNTIME_CLASSES[:4])
            write_runtime_jar(source, classes=incomplete)
            with self.assertRaises(ValueError):
                module.copy_jar(source, root / "out.jar", "com.example.flags")

    def test_rejects_extra_class(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "javac" / "flags.jar"
            source.parent.mkdir()
            write_runtime_jar(
                source, classes=RUNTIME_CLASSES + ("UnexpectedExtra",)
            )
            with self.assertRaises(ValueError):
                module.copy_jar(source, root / "out.jar", "com.example.flags")

class TestExtractAggregateSubset(unittest.TestCase):
    """AOSP-17 (Task 071): validated five-class subset extraction from the
    framework-minus-apex javac shards."""

    def _shard_dir(self, root):
        shard_dir = root / "javac"
        shard_dir.mkdir()
        return shard_dir

    def _write_shard(self, shard_dir, index, package, classes=RUNTIME_CLASSES,
                     extra_entries=None, include_uau=False):
        path = shard_dir / f"framework.jar{index}"
        prefix = package.replace(".", "/")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("android/other/Unrelated.class", b"noise")
            archive.writestr(f"{prefix}/", b"")
            for name in classes:
                archive.writestr(f"{prefix}/{name}.class", f"{name}-bytes".encode())
                if include_uau and name != "FakeFeatureFlagsImpl":
                    archive.writestr(f"{prefix}/{name}.uau", b"uau")
            for entry, data in (extra_entries or {}).items():
                archive.writestr(entry, data)
        return path

    def test_extracts_validated_subset_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard_dir = self._shard_dir(root)
            self._write_shard(shard_dir, 0, "unrelated.one")
            self._write_shard(
                shard_dir, 7, "com.example.flags", include_uau=True
            )
            self._write_shard(shard_dir, 12, "another.two")
            with mock.patch.object(module, "AGGREGATE_JAVAC_DIR", shard_dir):
                out1 = root / "a.jar"
                out2 = root / "b.jar"
                module.extract_aggregate_subset("com.example.flags", out1)
                module.extract_aggregate_subset("com.example.flags", out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            with zipfile.ZipFile(out1) as archive:
                names = archive.namelist()
            self.assertEqual(
                names,
                ["com/example/flags/"]
                + sorted(
                    [f"com/example/flags/{name}.class" for name in RUNTIME_CLASSES]
                    + [
                        f"com/example/flags/{name}.uau"
                        for name in RUNTIME_CLASSES
                        if name != "FakeFeatureFlagsImpl"
                    ]
                ),
            )

    def test_package_split_across_shards_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard_dir = self._shard_dir(root)
            prefix = "com/example/flags"
            with zipfile.ZipFile(shard_dir / "framework.jar0", "w") as archive:
                archive.writestr(f"{prefix}/Flags.class", b"x")
            with zipfile.ZipFile(shard_dir / "framework.jar1", "w") as archive:
                archive.writestr(f"{prefix}/FeatureFlags.class", b"y")
            with mock.patch.object(module, "AGGREGATE_JAVAC_DIR", shard_dir):
                with self.assertRaises(ValueError):
                    module.extract_aggregate_subset(
                        "com.example.flags", root / "out.jar"
                    )

    def test_missing_package_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard_dir = self._shard_dir(root)
            self._write_shard(shard_dir, 3, "unrelated.one")
            with mock.patch.object(module, "AGGREGATE_JAVAC_DIR", shard_dir):
                with self.assertRaises(FileNotFoundError):
                    module.extract_aggregate_subset(
                        "com.example.flags", root / "out.jar"
                    )

    def test_extra_class_under_prefix_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard_dir = self._shard_dir(root)
            self._write_shard(
                shard_dir,
                5,
                "com.example.flags",
                classes=RUNTIME_CLASSES + ("Unexpected",),
            )
            with mock.patch.object(module, "AGGREGATE_JAVAC_DIR", shard_dir):
                with self.assertRaises(ValueError):
                    module.extract_aggregate_subset(
                        "com.example.flags", root / "out.jar"
                    )

    def test_empty_shard_directory_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard_dir = self._shard_dir(root)
            with mock.patch.object(module, "AGGREGATE_JAVAC_DIR", shard_dir):
                with self.assertRaises(FileNotFoundError):
                    module.extract_aggregate_subset(
                        "com.example.flags", root / "out.jar"
                    )


class TestMergeSources(unittest.TestCase):
    """Deterministic union merge used by --merge-framework (task 057)."""

    def _sources(self, root, specs):
        items = []
        for name, package, extras in specs:
            src = root / name / "javac" / f"{name}.jar"
            src.parent.mkdir(parents=True)
            write_runtime_jar(src, package=package)
            if extras:
                with zipfile.ZipFile(src, "a") as archive:
                    for path, data in extras.items():
                        archive.writestr(path, data)
            items.append((name, src, package))
        return items

    def test_merged_jar_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = self._sources(
                root,
                [("a", "a.one.flags", None), ("b", "b.two.flags", None)],
            )
            out1 = root / "m1.jar"
            out2 = root / "m2.jar"
            module.merge_sources(items, out1)
            module.merge_sources(items, out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())

    def test_class_set_is_union_and_entries_byte_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = self._sources(
                root,
                [
                    ("a", "a.one.flags", None),
                    ("b", "b.two.flags", {"b/two/flags/Extra.uau": b"extra"}),
                ],
            )
            out = root / "merged.jar"
            module.merge_sources(items, out)
            with zipfile.ZipFile(out) as merged:
                merged_entries = set(merged.namelist())
                for _name, src, _pkg in items:
                    with zipfile.ZipFile(src) as source:
                        for entry in source.namelist():
                            if entry.endswith("/"):
                                continue
                            self.assertIn(entry, merged_entries)
                            self.assertEqual(
                                merged.read(entry), source.read(entry), entry
                            )
            self.assertIn("b/two/flags/Extra.uau", merged_entries)

    def test_collision_fails_even_when_bytes_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = self._sources(
                root,
                [("a", "same.flags", None), ("b", "same.flags", None)],
            )
            with self.assertRaises(ValueError):
                module.merge_sources(items, root / "merged.jar")

    def test_diverging_manifest_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = self._sources(
                root,
                [
                    ("a", "a.flags", None),
                    (
                        "b",
                        "b.flags",
                        {"META-INF/MANIFEST.MF": b"Manifest-Version: 2.0\r\n\r\n"},
                    ),
                ],
            )
            with self.assertRaises(ValueError):
                module.merge_sources(items, root / "merged.jar")

    def test_manifest_deduped_when_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = self._sources(
                root, [("a", "a.flags", None), ("b", "b.flags", None)]
            )
            out = root / "merged.jar"
            module.merge_sources(items, out)
            with zipfile.ZipFile(out) as merged:
                self.assertEqual(
                    merged.namelist().count("META-INF/MANIFEST.MF"), 1
                )


class TestTask064Configs(unittest.TestCase):
    """Regeneration gap closure (task 064): the three 2026-07 hand copies."""

    def test_settingslib_media_flags_config(self):
        source, destination, package = module.CONFIGS["settingslib-media-flags"]
        self.assertEqual(
            source,
            module.AOSP_INTERMEDIATES
            / "frameworks/base/packages/SettingsLib/settingslib_media_flags_lib"
            / "android_common/javac/settingslib_media_flags_lib.jar",
        )
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/settingslib-media-flags.jar"))
        self.assertEqual(package, "com.android.settingslib.media.flags")

    def test_device_state_flags_config(self):
        # device-state-flags (com.android.server.policy.feature.flags) is a
        # different family from device-state-feature-flags; both must exist.
        source, destination, package = module.CONFIGS["device-state-flags"]
        self.assertEqual(
            source,
            module.AOSP_INTERMEDIATES
            / "frameworks/base/services/foldables/devicestateprovider/src/com/"
            / "android/server/policy/feature/device_state_flags_lib"
            / "android_common/javac/device_state_flags_lib.jar",
        )
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/device-state-flags.jar"))
        self.assertEqual(package, "com.android.server.policy.feature.flags")
        self.assertIn("device-state-feature-flags", module.CONFIGS)
        self.assertNotIn("device-state-flags", module.FRAMEWORK_FAMILY)

    def test_turbine_baseline_config_shape(self):
        # aconfig_settingslib_flags_java_lib has no javac output in the build;
        # the baseline jar wraps its turbine-combined classes.
        source, destination, package = module.TURBINE_BASELINE_CONFIGS[
            "settingslib-flags"
        ]
        self.assertIn("turbine-combined", str(source))
        self.assertEqual(destination, Path("libs/settingslib-flags.jar"))
        self.assertEqual(package, "com.android.settingslib.flags")
        self.assertNotIn("settingslib-flags", module.CONFIGS)


class TestRepackBaselineStubJar(unittest.TestCase):
    """Baseline-preserving jar-tool repack of a turbine stub source."""

    def _turbine_source(self, root, package="com.android.settingslib.flags"):
        source = root / "turbine-combined" / "flags.jar"
        source.parent.mkdir(parents=True)
        prefix = package.replace(".", "/")
        with zipfile.ZipFile(source, "w", zipfile.ZIP_STORED) as archive:
            for name in RUNTIME_CLASSES:
                info = zipfile.ZipInfo(f"{prefix}/{name}.class", (2008, 1, 1, 0, 0, 0))
                archive.writestr(info, f"stub-{name}".encode())
        return source

    def test_repack_is_deterministic_and_carries_baseline_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._turbine_source(root)
            out1 = root / "a.jar"
            out2 = root / "b.jar"
            module.repack_baseline_stub_jar(source, out1, "com.android.settingslib.flags")
            module.repack_baseline_stub_jar(source, out2, "com.android.settingslib.flags")
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            with zipfile.ZipFile(out1) as archive:
                self.assertIn("META-INF/MANIFEST.MF", archive.namelist())
                self.assertEqual(
                    archive.read("META-INF/MANIFEST.MF"), module._BASELINE_MANIFEST
                )
                for name in RUNTIME_CLASSES:
                    self.assertEqual(
                        archive.read(
                            "com/android/settingslib/flags/" + name + ".class"
                        ),
                        ("stub-" + name).encode(),
                    )
                manifest_info = archive.getinfo("META-INF/MANIFEST.MF")
                self.assertEqual(
                    manifest_info.date_time, module._BASELINE_WRAPPER_DATETIME
                )

    def test_repack_rejects_incomplete_class_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "turbine-combined" / "flags.jar"
            source.parent.mkdir(parents=True)
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("com/android/settingslib/flags/Flags.class", b"x")
            with self.assertRaises(ValueError):
                module.repack_baseline_stub_jar(
                    source, root / "out.jar", "com.android.settingslib.flags"
                )

    def test_repack_rejects_source_with_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._turbine_source(root)
            with zipfile.ZipFile(source, "a") as archive:
                archive.writestr("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0\r\n\r\n")
            with self.assertRaises(ValueError):
                module.repack_baseline_stub_jar(
                    source, root / "out.jar", "com.android.settingslib.flags"
                )


class TestBatchAllFlag(unittest.TestCase):
    """The optional --all batch mode keeps the single-artifact path intact."""

    def _run_main(self, argv):
        with mock.patch.object(sys, "argv", ["package_aconfig_jars.py"] + argv):
            return module.main()

    def test_all_packages_every_config_in_sorted_order(self):
        fake_configs = {
            "z-last": (Path("/a.jar"), Path("libs/z.jar"), "a.z"),
            "a-first": (Path("/b.jar"), Path("libs/a.jar"), "a.b"),
        }
        calls = []
        merges = []
        with mock.patch.object(module, "CONFIGS", fake_configs), mock.patch.object(
            module, "FRAMEWORK_FAMILY", frozenset()
        ), mock.patch.object(
            module, "TURBINE_BASELINE_CONFIGS", {}
        ), mock.patch.object(
            module, "copy_jar", side_effect=lambda s, d, p: calls.append((s, d, p))
        ), mock.patch.object(
            module,
            "merge_framework_family",
            side_effect=lambda: merges.append("merged"),
        ):
            self.assertEqual(self._run_main(["--all"]), 0)
        self.assertEqual(merges, ["merged"])
        self.assertEqual(
            calls,
            [fake_configs["a-first"], fake_configs["z-last"]],
        )

    def test_all_excludes_family_members_from_individual_copies(self):
        fake_configs = {
            "solo": (Path("/a.jar"), Path("libs/a.jar"), "a.b"),
            "fam": (Path("/f.jar"), Path("libs/f.jar"), "f.g"),
        }
        calls = []
        with mock.patch.object(module, "CONFIGS", fake_configs), mock.patch.object(
            module, "FRAMEWORK_FAMILY", frozenset({"fam"})
        ), mock.patch.object(
            module, "TURBINE_BASELINE_CONFIGS", {}
        ), mock.patch.object(
            module, "copy_jar", side_effect=lambda s, d, p: calls.append((s, d, p))
        ), mock.patch.object(module, "merge_framework_family", return_value=None):
            self.assertEqual(self._run_main(["--all"]), 0)
        self.assertEqual(calls, [fake_configs["solo"]])

    def test_merge_framework_mode_merges_without_copying_individuals(self):
        calls = []
        merges = []
        with mock.patch.object(
            module, "copy_jar", side_effect=lambda s, d, p: calls.append((s, d, p))
        ), mock.patch.object(
            module,
            "merge_framework_family",
            side_effect=lambda: merges.append("merged"),
        ):
            self.assertEqual(self._run_main(["--merge-framework"]), 0)
        self.assertEqual(merges, ["merged"])
        self.assertEqual(calls, [])

    def test_all_repacks_turbine_baseline_entries(self):
        # --all must also process TURBINE_BASELINE_CONFIGS through the repack
        # path (settingslib-flags), never through the plain javac copy.
        fake_configs = {"solo": (Path("/a.jar"), Path("libs/a.jar"), "a.b")}
        copies = []
        repacks = []
        with mock.patch.object(module, "CONFIGS", fake_configs), mock.patch.object(
            module, "FRAMEWORK_FAMILY", frozenset()
        ), mock.patch.object(
            module, "TURBINE_BASELINE_CONFIGS",
            {"stub": (Path("/t.jar"), Path("libs/stub.jar"), "a.stub")},
        ), mock.patch.object(
            module, "copy_jar", side_effect=lambda s, d, p: copies.append((s, d, p))
        ), mock.patch.object(
            module, "repack_baseline_stub_jar",
            side_effect=lambda s, d, p: repacks.append((s, d, p)),
        ), mock.patch.object(
            module, "merge_framework_family", return_value=None
        ):
            self.assertEqual(self._run_main(["--all"]), 0)
        self.assertEqual(copies, [fake_configs["solo"]])
        self.assertEqual(
            repacks, [(Path("/t.jar"), Path("libs/stub.jar"), "a.stub")]
        )

    def test_single_artifact_still_works(self):
        fake_configs = {"only": (Path("/a.jar"), Path("libs/a.jar"), "a.b")}
        calls = []
        with mock.patch.object(module, "CONFIGS", fake_configs), mock.patch.object(
            module, "copy_jar", side_effect=lambda s, d, p: calls.append((s, d, p))
        ):
            self.assertEqual(self._run_main(["only"]), 0)
        self.assertEqual(calls, [fake_configs["only"]])

    def test_missing_selection_is_an_error(self):
        with self.assertRaises(SystemExit):
            self._run_main([])

    def test_artifact_and_all_is_an_error(self):
        with self.assertRaises(SystemExit):
            self._run_main(["systemui-flags", "--all"])

    def test_artifact_and_merge_framework_is_an_error(self):
        with self.assertRaises(SystemExit):
            self._run_main(["systemui-flags", "--merge-framework"])

    def test_all_and_merge_framework_is_an_error(self):
        with self.assertRaises(SystemExit):
            self._run_main(["--all", "--merge-framework"])


class TestAospPaths(unittest.TestCase):
    """The unified AOSP root source: one default, env and explicit overrides."""

    def test_default_root_is_the_build_machine_checkout(self):
        # Pinning the default is intentional: it is the single place to change.
        self.assertEqual(
            aosp_paths.DEFAULT_AOSP_ROOT, Path("/home/conv/myspace/aosp")
        )

    def test_env_override_wins_over_default(self):
        with mock.patch.dict(os.environ, {"AOSP_ROOT": "/opt/custom-aosp"}):
            self.assertEqual(aosp_paths.aosp_root(), Path("/opt/custom-aosp"))

    def test_explicit_override_wins_over_env(self):
        with mock.patch.dict(os.environ, {"AOSP_ROOT": "/opt/custom-aosp"}):
            self.assertEqual(aosp_paths.aosp_root("/cli/aosp"), Path("/cli/aosp"))

    def test_soong_intermediates_joins_under_root(self):
        self.assertEqual(
            aosp_paths.soong_intermediates("/any/root"),
            Path("/any/root/out/soong/.intermediates"),
        )

    def test_module_constant_matches_shared_source(self):
        # package_aconfig_jars must not keep its own hardcoded root.
        self.assertEqual(module.AOSP_INTERMEDIATES, aosp_paths.soong_intermediates())


if __name__ == "__main__":
    unittest.main()
