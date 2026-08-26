"""Tests for tools/package_viewcapture_motiontool_jars.py.

The packager merges fixed owning-Soong implementation outputs (javac/kotlin,
never turbine/header/FAT) into two deterministic class-only JARs:
``libs/view_capture.jar`` (56 classes under com/android/app/viewcapture/) and
``libs/motion_tool_lib.jar`` (65 classes under com/android/app/motiontool/).
"""

import importlib.util
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

# The script under test imports aosp_paths; make tools/ importable no matter
# where the test runner is invoked from.
_TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

_SCRIPT = _TOOLS_DIR / "package_viewcapture_motiontool_jars.py"
_spec = importlib.util.spec_from_file_location("package_viewcapture_motiontool_jars", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

VIEW_PREFIX = "com/android/app/viewcapture/"
MOTION_PREFIX = "com/android/app/motiontool/"


def write_jar(path, entries):
    """Write a synthetic JAR. ``entries`` maps archive names to payloads."""
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)


class TestViewCaptureMotionToolPackaging(unittest.TestCase):
    def _view_inputs(self, root):
        first = root / "view_javac.jar"
        second = root / "view_kotlin.jar"
        third = root / "view_proto.jar"
        write_jar(first, {
            f"{VIEW_PREFIX}A.class": b"a",
            f"{VIEW_PREFIX}B.class": b"b",
            "META-INF/MANIFEST.MF": b"manifest",
        })
        write_jar(second, {f"{VIEW_PREFIX}C.class": b"c"})
        write_jar(third, {
            f"{VIEW_PREFIX}data/D.class": b"d",
            f"{VIEW_PREFIX}data/E.class": b"e",
            "com/android/app/other/F.txt": b"non-class entry",
        })
        return (first, second, third)

    def test_view_target_merges_three_clean_inputs(self):
        # The synthetic view fixture contributes (2, 1, 2) classes; manifests
        # and namespace pollution must never reach the output.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "view_capture.jar"
            counts = module.package_target(
                self._view_inputs(root), output, VIEW_PREFIX
            )
            self.assertEqual(counts, (2, 1, 2))
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            self.assertEqual(
                names,
                sorted([
                    f"{VIEW_PREFIX}A.class",
                    f"{VIEW_PREFIX}B.class",
                    f"{VIEW_PREFIX}C.class",
                    f"{VIEW_PREFIX}data/D.class",
                    f"{VIEW_PREFIX}data/E.class",
                ]),
            )

    def test_motion_target_merges_two_clean_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "motion_kotlin.jar"
            second = root / "motion_proto.jar"
            write_jar(first, {
                f"{MOTION_PREFIX}A.class": b"a",
                f"{MOTION_PREFIX}B.class": b"b",
            })
            write_jar(second, {
                f"{MOTION_PREFIX}C.class": b"c",
                f"{MOTION_PREFIX}D.class": b"d",
                "dir-entry/": b"",
            })
            output = root / "motion_tool_lib.jar"
            counts = module.package_target((first, second), output, MOTION_PREFIX)
            self.assertEqual(counts, (2, 2))
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
            self.assertEqual(len(names), 4)
            self.assertTrue(all(n.endswith(".class") for n in names))
            self.assertEqual(names, sorted(names))

    def test_output_is_deterministic(self):
        # Fixed timestamp, 0644 mode, sorted entries, byte-identical reruns.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.jar"
            module.package_target(self._view_inputs(root), output, VIEW_PREFIX)
            first_run = output.read_bytes()
            module.package_target(self._view_inputs(root), output, VIEW_PREFIX)
            self.assertEqual(output.read_bytes(), first_run)
            with zipfile.ZipFile(output) as archive:
                for info in archive.infolist():
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(info.external_attr >> 16, 0o644)
                    self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)

    def test_rejects_class_outside_approved_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "bad.jar"
            write_jar(bad, {
                f"{VIEW_PREFIX}A.class": b"a",
                "androidx/core/Core.class": b"androidx",
            })
            with self.assertRaises(module.PackagingError):
                module.package_target((bad,), root / "out.jar", VIEW_PREFIX)

    def test_rejects_duplicate_classes(self):
        # Both an intra-input and a cross-input duplicate must be rejected.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicated = root / "dup.jar"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicated, "w") as archive:
                    archive.writestr(f"{VIEW_PREFIX}A.class", b"a")
                    archive.writestr(f"{VIEW_PREFIX}A.class", b"a2")
            with self.assertRaises(module.PackagingError):
                module.package_target((duplicated,), root / "out.jar", VIEW_PREFIX)
            first = root / "first.jar"
            second = root / "second.jar"
            write_jar(first, {f"{VIEW_PREFIX}A.class": b"a"})
            write_jar(second, {f"{VIEW_PREFIX}A.class": b"a-other"})
            with self.assertRaises(module.PackagingError):
                module.package_target((first, second), root / "out.jar", VIEW_PREFIX)

    def test_rejects_missing_invalid_or_empty_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / "missing.jar"
            with self.assertRaises(module.PackagingError):
                module.package_target((missing,), root / "out.jar", VIEW_PREFIX)
            invalid = root / "invalid.jar"
            invalid.write_bytes(b"not a zip file")
            with self.assertRaises(module.PackagingError):
                module.package_target((invalid,), root / "out.jar", VIEW_PREFIX)
            empty = root / "empty.jar"
            write_jar(empty, {"META-INF/MANIFEST.MF": b"manifest"})
            with self.assertRaises(module.PackagingError):
                module.package_target((empty,), root / "out.jar", VIEW_PREFIX)


if __name__ == "__main__":
    unittest.main()
