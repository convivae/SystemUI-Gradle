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

    def test_pom_content_without_deps_has_no_dependencies_element(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            aar = tmp / "src" / "Baz.aar"
            _make_test_aar(aar)
            _, pom_dst = iam.install_aar(aar, "com.foo", "Baz", "1.0.0", tmp / "repo")
            text = pom_dst.read_text()
            self.assertNotIn("<dependencies>", text)
            self.assertNotIn("<dependency>", text)

    def test_pom_with_renders_dependencies(self):
        """Task 015（ADR 0005）：deps 字段按声明顺序渲染 <dependencies>。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            aar = tmp / "src" / "With.aar"
            _make_test_aar(aar)
            _, pom_dst = iam.install_aar(
                aar, "com.foo", "With", "1.0.0", tmp / "repo",
                deps=[
                    {"group": "g1", "name": "A", "version": "1.0.0"},
                    {"group": "g2", "name": "B", "version": "2.0.0"},
                ])
            text = pom_dst.read_text()
            self.assertIn("<packaging>aar</packaging>", text)
            self.assertIn(
                """  <dependencies>
    <dependency>
      <groupId>g1</groupId>
      <artifactId>A</artifactId>
      <version>1.0.0</version>
    </dependency>
    <dependency>
      <groupId>g2</groupId>
      <artifactId>B</artifactId>
      <version>2.0.0</version>
    </dependency>
  </dependencies>""",
                text,
            )

    def test_install_all_passes_deps_through(self):
        """install_all 从 ARTIFACTS 读取 deps 并写入 POM。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            _make_test_aar(src / "Parent.aar")
            _make_test_aar(src / "Child.aar")
            artifacts = {
                "Parent": {"group": "g", "name": "Parent", "version": "1.0.0",
                           "deps": [{"group": "g", "name": "Child", "version": "1.0.0"}]},
                "Child": {"group": "g", "name": "Child", "version": "1.0.0"},
            }
            iam.install_all(src, tmp / "repo", artifacts)
            parent_pom = (tmp / "repo" / "g" / "Parent" / "1.0.0" / "Parent-1.0.0.pom").read_text()
            child_pom = (tmp / "repo" / "g" / "Child" / "1.0.0" / "Child-1.0.0.pom").read_text()
            self.assertIn("<artifactId>Child</artifactId>", parent_pom)
            self.assertNotIn("<dependencies>", child_pom)

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


class ArtifactRegistryTest(unittest.TestCase):
    def test_settingslib_settings_theme_coordinate(self):
        """Task 013：SettingsLibSettingsTheme 固定本地坐标。"""
        self.assertEqual(
            iam.ARTIFACTS["SettingsLibSettingsTheme"],
            {"group": "com.android.systemui", "name": "SettingsLibSettingsTheme", "version": "1.0.0"},
        )

    def test_settingslib_closure_seven_targets_coordinates(self):
        """Task 015（B2）：7 个 per-target res-only AAR 固定坐标 com.android.systemui:<Target>:1.0.0。"""
        expected = {
            "SettingsLibSelectorWithWidgetPreference",
            "SettingsLibRestrictedLockUtils",
            "SettingsLibActionButtonsPreference",
            "SettingsLibProgressBar",
            "SettingsLibTwoTargetPreference",
            "SettingsLibLayoutPreference",
            "SettingsLibAdaptiveIcon",
        }
        for name in expected:
            self.assertEqual(
                iam.ARTIFACTS[name],
                {"group": "com.android.systemui", "name": name, "version": "1.0.0"},
            )

    def test_settingslib_pom_carries_seven_closure_deps(self):
        """Task 015（ADR 0005）：SettingsLib POM 依赖边机械镜像主 bp 的 7 个新增直接 static_libs。"""
        deps = iam.ARTIFACTS["SettingsLib"].get("deps")
        self.assertEqual(
            deps,
            [
                {"group": "com.android.systemui", "name": "SettingsLibSelectorWithWidgetPreference", "version": "1.0.0"},
                {"group": "com.android.systemui", "name": "SettingsLibRestrictedLockUtils", "version": "1.0.0"},
                {"group": "com.android.systemui", "name": "SettingsLibActionButtonsPreference", "version": "1.0.0"},
                {"group": "com.android.systemui", "name": "SettingsLibProgressBar", "version": "1.0.0"},
                {"group": "com.android.systemui", "name": "SettingsLibTwoTargetPreference", "version": "1.0.0"},
                {"group": "com.android.systemui", "name": "SettingsLibLayoutPreference", "version": "1.0.0"},
                {"group": "com.android.systemui", "name": "SettingsLibAdaptiveIcon", "version": "1.0.0"},
            ],
        )

    def test_closure_targets_have_no_deps(self):
        """7 个新 target 自身 POM 保持骨架（无 deps 边）。"""
        for name in [
            "SettingsLibSelectorWithWidgetPreference", "SettingsLibRestrictedLockUtils",
            "SettingsLibActionButtonsPreference", "SettingsLibProgressBar",
            "SettingsLibTwoTargetPreference", "SettingsLibLayoutPreference",
            "SettingsLibAdaptiveIcon", "SettingsLibSettingsTheme", "SettingsLibColor",
        ]:
            self.assertNotIn("deps", iam.ARTIFACTS[name], f"{name} 不应携带 deps")


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
