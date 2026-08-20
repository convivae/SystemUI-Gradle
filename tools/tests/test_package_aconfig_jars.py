import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "package_aconfig_jars.py"
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

    def test_batch2_config_matrix(self):
        # The five Batch-2 artifacts must map exact owning Soong javac sources
        # to their destinations and runtime packages.
        for name, (suffix, destination, package) in BATCH2_CONFIGS.items():
            with self.subTest(config=name):
                self.assertIn(name, module.CONFIGS)
                source = module.CONFIGS[name][0]
                self.assertEqual(
                    str(source),
                    "/home/conv/myspace/aosp/out/soong/.intermediates/" + suffix,
                )
                self.assertIn("/javac/", str(source))
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

if __name__ == "__main__":
    unittest.main()
