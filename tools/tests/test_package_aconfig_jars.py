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
    "settingslib-selector-flags": (
        "frameworks/base/packages/SettingsLib/SelectorWithWidgetPreference/"
        "settingslib_selectorwithwidgetpreference_flags_lib/android_common/javac/"
        "settingslib_selectorwithwidgetpreference_flags_lib.jar",
        Path("libs/settingslib-selector-flags.jar"),
        "com.android.settingslib.widget.selectorwithwidgetpreference.flags",
    ),
}


BATCH3_CONFIGS = {
    # Task 055 batch: 11 residual same-family hazards. Each maps the base-variant
    # android_common/javac JAR of its java_aconfig_library in
    # frameworks/base/AconfigFlags.bp to libs/ and its runtime package.
    "smartspace-flags": (
        "android.app.smartspace.flags-aconfig-java",
        Path("libs/smartspace-flags.jar"),
        "android.app.smartspace.flags",
    ),
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
    "usb-flags": (
        "android.hardware.usb.flags-aconfig-java",
        Path("libs/usb-flags.jar"),
        "android.hardware.usb.flags",
    ),
    "net-platform-flags": (
        "android.net.platform.flags-aconfig-java",
        Path("libs/net-platform-flags.jar"),
        "android.net.platform.flags",
    ),
    "permission-flags": (
        "android.permission.flags-aconfig-java",
        Path("libs/permission-flags.jar"),
        "android.permission.flags",
    ),
    "provider-flags": (
        "android.provider.flags-aconfig-java",
        Path("libs/provider-flags.jar"),
        "android.provider",
    ),
    "security-flags": (
        "android.security.flags-aconfig-java",
        Path("libs/security-flags.jar"),
        "android.security",
    ),
    "service-controls-flags": (
        "android.service.controls.flags-aconfig-java",
        Path("libs/service-controls-flags.jar"),
        "android.service.controls.flags",
    ),
    "service-notification-flags": (
        "android.service.notification.flags-aconfig-java",
        Path("libs/service-notification-flags.jar"),
        "android.service.notification",
    ),
    "quickaccesswallet-flags": (
        "android.service.quickaccesswallet.flags-aconfig-java",
        Path("libs/quickaccesswallet-flags.jar"),
        "android.service.quickaccesswallet",
    ),
}


def write_runtime_jar(path, package="com.example.flags", classes=RUNTIME_CLASSES):
    """Write a synthetic aconfig runtime JAR with the given class names."""
    prefix = package.replace(".", "/")
    with zipfile.ZipFile(path, "w") as archive:
        for name in classes:
            archive.writestr(f"{prefix}/{name}.class", b"class-bytes")


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

    def test_device_state_feature_flags_config_uses_framework_owned_javac_runtime(self):
        source, destination, package = module.CONFIGS["device-state-feature-flags"]
        self.assertEqual(
            source,
            module.AOSP_INTERMEDIATES
            / "frameworks/base"
            / "android.hardware.devicestate.feature.flags-aconfig-java"
            / "android_common/javac"
            / "android.hardware.devicestate.feature.flags-aconfig-java.jar",
        )
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/device-state-feature-flags.jar"))
        self.assertEqual(package, "android.hardware.devicestate.feature.flags")

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
        # The eleven Batch-3 (task 055) artifacts must map exact owning Soong
        # javac sources to their destinations and runtime packages.
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
        with mock.patch.object(module, "CONFIGS", fake_configs), mock.patch.object(
            module, "copy_jar", side_effect=lambda s, d, p: calls.append((s, d, p))
        ):
            self.assertEqual(self._run_main(["--all"]), 0)
        self.assertEqual(
            calls,
            [fake_configs["a-first"], fake_configs["z-last"]],
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
