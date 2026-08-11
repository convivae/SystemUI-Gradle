#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install_aar_to_maven.py 单测"""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import install_aar_to_maven as iam


def _make_test_aar(path: Path, marker: bytes = b"test") -> None:
    """生成一个最小合法 AAR(AndroidManifest.xml + classes.jar)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("AndroidManifest.xml", b"<manifest package='x'/>")
        z.writestr("classes.jar", marker)


class ArtifactDirTest(unittest.TestCase):
    def test_group_dots_to_path(self):
        d = iam.artifact_dir(Path("/tmp/maven"), "com.android.systemui", "SettingsLib", "1.0.0")
        self.assertEqual(d, Path("/tmp/maven/com/android/systemui/SettingsLib/1.0.0"))

    def test_single_letter_group(self):
        d = iam.artifact_dir(Path("/tmp/maven"), "x", "A", "1.0.0")
        self.assertEqual(d, Path("/tmp/maven/x/A/1.0.0"))


class InstallAarTest(unittest.TestCase):
    def test_install_writes_aar_and_pom(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            repo = tmp / "repo"
            aar = src / "Test.aar"
            _make_test_aar(aar, marker=b"unique-bytes")
            aar_dst, pom_dst = iam.install_aar(
                aar, "com.test", "Test", "1.0.0", repo)
            self.assertEqual(aar_dst, repo / "com/test/Test/1.0.0/Test-1.0.0.aar")
            self.assertEqual(pom_dst, repo / "com/test/Test/1.0.0/Test-1.0.0.pom")
            self.assertTrue(aar_dst.exists())
            self.assertTrue(pom_dst.exists())
            # 字节不变
            self.assertEqual(aar_dst.read_bytes(), aar.read_bytes())

    def test_pom_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            repo = tmp / "repo"
            aar = src / "Foo.aar"
            _make_test_aar(aar)
            _, pom_dst = iam.install_aar(aar, "com.foo", "Foo", "2.0.0", repo)
            text = pom_dst.read_text()
            self.assertIn("<groupId>com.foo</groupId>", text)
            self.assertIn("<artifactId>Foo</artifactId>", text)
            self.assertIn("<version>2.0.0</version>", text)
            self.assertIn("<packaging>aar</packaging>", text)

    def test_install_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            repo = tmp / "repo"
            aar = src / "X.aar"
            _make_test_aar(aar, marker=b"old")
            iam.install_aar(aar, "g", "X", "1.0.0", repo)
            _make_test_aar(aar, marker=b"new")
            aar_dst, _ = iam.install_aar(aar, "g", "X", "1.0.0", repo)
            with zipfile.ZipFile(aar_dst) as z:
                self.assertEqual(z.read("classes.jar"), b"new")


class InstallAllTest(unittest.TestCase):
    def test_install_all_default_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            repo = tmp / "repo"
            for name in iam.ARTIFACTS:
                _make_test_aar(src / f"{name}.aar")
            installed = iam.install_all(src, repo)
            self.assertEqual(len(installed), len(iam.ARTIFACTS))
            # 每个 artifact 都有 aar + pom
            for aar_dst, pom_dst in installed:
                self.assertTrue(aar_dst.exists())
                self.assertTrue(pom_dst.exists())

    def test_install_selected_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            repo = tmp / "repo"
            _make_test_aar(src / "A.aar")
            _make_test_aar(src / "B.aar")
            artifacts = {"A": {"group": "g", "name": "A", "version": "1.0.0"}}
            installed = iam.install_all(src, repo, artifacts)
            self.assertEqual(len(installed), 1)
            self.assertEqual(installed[0][0].name, "A-1.0.0.aar")

    def test_missing_aar_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                iam.install_all(tmp / "src", tmp / "repo",
                                {"Missing": {"group": "g", "name": "Missing", "version": "1.0.0"}})


if __name__ == "__main__":
    unittest.main()
