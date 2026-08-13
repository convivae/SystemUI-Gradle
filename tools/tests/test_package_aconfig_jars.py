import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "package_aconfig_jars.py"
_spec = importlib.util.spec_from_file_location("package_aconfig_jars", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class TestAconfigJarPackaging(unittest.TestCase):
    def test_runtime_config_uses_javac_not_turbine(self):
        source, destination = module.CONFIGS["systemui-shared-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/systemui-shared-flags.jar"))

    def test_zxing_core_config(self):
        source, destination = module.CONFIGS["zxing-core"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/zxing-core.jar"))

    def test_wifi_flags_config(self):
        source, destination = module.CONFIGS["wifi-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/wifi-flags.jar"))

    def test_wm_shell_flags_config(self):
        source, destination = module.CONFIGS["wm-shell-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/wm-shell-flags.jar"))

    def test_copy_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "javac" / "flags.jar"
            source.parent.mkdir()
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("com/example/Flags.class", b"class-bytes")
            destination = root / "out.jar"
            module.copy_jar(source, destination)
            self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_copy_preserves_bytes_for_each_config(self):
        # Reuse the byte-identical copy assertion for every CONFIGS entry so a
        # future addition cannot silently skip the turbine/runtime check.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, (source, _destination) in module.CONFIGS.items():
                with self.subTest(config=name):
                    fake_source = root / name / "javac" / "flags.jar"
                    fake_source.parent.mkdir(parents=True)
                    with zipfile.ZipFile(fake_source, "w") as archive:
                        archive.writestr(
                            f"com/example/{name}/Flags.class", b"class-bytes"
                        )
                    destination = root / f"{name}.out.jar"
                    module.copy_jar(fake_source, destination)
                    self.assertEqual(
                        destination.read_bytes(), fake_source.read_bytes()
                    )


if __name__ == "__main__":
    unittest.main()
