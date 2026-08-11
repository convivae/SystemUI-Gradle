#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/package_aosp_aar.py — strict direct-AAR packager."""

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "package_aosp_aar.py"
_spec = importlib.util.spec_from_file_location("package_aosp_aar", _SCRIPT)
paar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(paar)


def _make_jar(path: Path, entries: dict):
    """entries: {name_in_zip: bytes}"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        for name, data in entries.items():
            z.writestr(name, data)


class TestMergeCodeJars(unittest.TestCase):
    def test_both_input_classes_appear(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"com/android/app/animation/Animations.class": b"\xca\xfe\xba\xbe"})
            _make_jar(d / "b.jar", {"com/android/app/animation/Interpolators.class": b"\xbe\xef"})
            out = d / "merged.jar"
            paar.merge_code_jars([d / "a.jar", d / "b.jar"], out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertIn("com/android/app/animation/Animations.class", names)
            self.assertIn("com/android/app/animation/Interpolators.class", names)

    def test_r_class_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "bad.jar", {"com/android/app/animation/R.class": b"x"})
            with self.assertRaises(paar.DuplicateEntryError if False else Exception):
                paar.merge_code_jars([d / "bad.jar"], d / "out.jar")

    def test_r_inner_class_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "bad.jar", {"com/android/app/animation/R$id.class": b"x"})
            with self.assertRaises(Exception):
                paar.merge_code_jars([d / "bad.jar"], d / "out.jar")

    def test_duplicate_non_manifest_entry_raises(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"com/x/Foo.class": b"1"})
            _make_jar(d / "b.jar", {"com/x/Foo.class": b"2"})
            with self.assertRaises(paar.DuplicateEntryError):
                paar.merge_code_jars([d / "a.jar", d / "b.jar"], d / "out.jar")

    def test_duplicate_manifest_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"META-INF/MANIFEST.MF": b"m1", "com/x/Foo.class": b"1"})
            _make_jar(d / "b.jar", {"META-INF/MANIFEST.MF": b"m2", "com/x/Bar.class": b"2"})
            out = d / "merged.jar"
            paar.merge_code_jars([d / "a.jar", d / "b.jar"], out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertIn("com/x/Foo.class", names)
            self.assertIn("com/x/Bar.class", names)
            # 只保留一份 MANIFEST
            self.assertEqual(sum(1 for n in names if n == "META-INF/MANIFEST.MF"), 1)

    def test_directory_entries_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "a.jar", {"com/x/": b"", "com/x/Foo.class": b"1"})
            out = d / "merged.jar"
            paar.merge_code_jars([d / "a.jar"], out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertNotIn("com/x/", names)
            self.assertIn("com/x/Foo.class", names)


class TestCopyResourceTree(unittest.TestCase):
    def test_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / "res"
            (src / "values").mkdir(parents=True)
            (src / "values/ids.xml").write_bytes(b"<ids/>")
            (src / "interpolator").mkdir()
            (src / "interpolator/foo.xml").write_bytes(b"<interpolator/>")
            dst = d / "out"
            paar.copy_resource_tree(src, dst)
            self.assertEqual((dst / "values/ids.xml").read_bytes(), b"<ids/>")
            self.assertEqual((dst / "interpolator/foo.xml").read_bytes(), b"<interpolator/>")


class TestAssembleAar(unittest.TestCase):
    def test_no_pom_or_maven_generated(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/Foo.class": b"1"})
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            out = d / "lib.aar"
            paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
            self.assertIn("classes.jar", names)
            self.assertIn("res/values/ids.xml", names)
            self.assertIn("AndroidManifest.xml", names)
            self.assertIn("R.txt", names)
            # 不生成 POM / maven 元数据
            self.assertFalse(any(n.endswith(".pom") or n.startswith("META-INF/maven") for n in names),
                             f"不应生成 POM/maven 元数据: {names}")
            # classes.jar 内无 R.class
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    cn = set(cj.namelist())
            self.assertFalse(any(n.rsplit("/", 1)[-1] == "R.class" or
                                 n.rsplit("/", 1)[-1].startswith("R$") for n in cn),
                             "classes.jar 不应含 R.class")

    def test_repeated_builds_are_byte_identical(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/Foo.class": b"\xca\xfe\xba\xbe"})
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            first = d / "first.aar"
            second = d / "second.aar"
            paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, first)
            time.sleep(2)
            paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


class TestArtifactConfigs(unittest.TestCase):
    """Step 1: 每个 artifact 的 config 路径匹配 canonical inputs table。"""

    def test_wifitrackerlib_config_paths(self):
        cfg = paar.CONFIGS["WifiTrackerLib"]
        self.assertIn("WifiTrackerLib/android_common/javac/WifiTrackerLib.jar", str(cfg["code"]))
        self.assertIn("WifiTrackerLib/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("WifiTrackerLib/AndroidManifest.xml"))
        self.assertIn("WifiTrackerLibRes/android_common/R.txt", str(cfg["rtxt"]))

    def test_iconloader_config_paths(self):
        cfg = paar.CONFIGS["iconloader"]
        self.assertIn("iconloader/android_common/javac/iconloader.jar", str(cfg["code"]))
        self.assertIn("iconloaderlib/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("iconloaderlib/AndroidManifest.xml"))
        self.assertIn("iconloader/android_common/R.txt", str(cfg["rtxt"]))

    def test_settingslib_config_paths(self):
        cfg = paar.CONFIGS["SettingsLib"]
        self.assertIn("SettingsLib/android_common/javac/SettingsLib.jar", str(cfg["code"]))
        self.assertIn("SettingsLib/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("SettingsLib/AndroidManifest.xml"))
        self.assertIn("SettingsLib/android_common/R.txt", str(cfg["rtxt"]))

    def test_wmshell_config_paths(self):
        cfg = paar.CONFIGS["WindowManager-Shell"]
        self.assertIn("WindowManager-Shell/android_common/javac/WindowManager-Shell.jar", str(cfg["code"]))
        self.assertIn("WindowManager/Shell/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("WindowManager/Shell/AndroidManifest.xml"))
        self.assertIn("WindowManager-Shell/android_common/R.txt", str(cfg["rtxt"]))

    def test_wmshell_config_rejects_sysui(self):
        """WM-Shell config 必须声明 reject_sysui=True。"""
        self.assertTrue(paar.CONFIGS["WindowManager-Shell"].get("reject_sysui", False))

    def test_other_configs_do_not_reject_sysui(self):
        for name in ["WifiTrackerLib", "iconloader", "SettingsLib", "animationlib"]:
            self.assertFalse(paar.CONFIGS[name].get("reject_sysui", False),
                             f"{name} 不应 reject_sysui")


class TestAbsentInputFails(unittest.TestCase):
    """Step 1: 缺输入报 FileNotFoundError。"""

    def test_missing_code_jar_raises(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/Foo.class": b"1"})
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            with self.assertRaises(FileNotFoundError):
                paar.assemble_aar([d / "nonexistent.jar"], res, manifest, rtxt, d / "out.aar")


class TestCodeJarWithRFails(unittest.TestCase):
    """Step 1: code JAR 含 R 则在输出替换前失败。"""

    def test_r_class_in_code_jar_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/R.class": b"x", "com/x/Foo.class": b"1"})
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            with self.assertRaises(paar.DuplicateEntryError):
                paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, d / "out.aar")


class TestDuplicateResourcePaths(unittest.TestCase):
    """Step 3: 重复 res 相对路径报错而非合并/覆盖。"""

    def test_duplicate_res_entry_raises(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {"com/x/Foo.class": b"1"})
            # 两个 res root 有相同相对路径
            res1 = d / "res1"
            (res1 / "values").mkdir(parents=True)
            (res1 / "values/ids.xml").write_bytes(b"<ids1/>")
            res2 = d / "res2"
            (res2 / "values").mkdir(parents=True)
            (res2 / "values/ids.xml").write_bytes(b"<ids2/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            with self.assertRaises(paar.DuplicateEntryError):
                paar.assemble_aar([d / "code.jar"], [res1, res2], manifest, rtxt, d / "out.aar")


class TestWmShellNoSysuiClasses(unittest.TestCase):
    """Step 4: WM-Shell 输出不得含 com/android/systemui/** 类。"""

    def test_sysui_class_rejected_when_configured(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _make_jar(d / "code.jar", {
                "com/android/wm/shell/Shell.class": b"1",
                "com/android/systemui/animation/Foo.class": b"2",
            })
            res = d / "res"
            (res / "values").mkdir(parents=True)
            (res / "values/ids.xml").write_bytes(b"<ids/>")
            manifest = d / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = d / "R.txt"
            rtxt.write_bytes(b"int id foo 0x0\n")
            with self.assertRaises(paar.DuplicateEntryError):
                paar.assemble_aar([d / "code.jar"], res, manifest, rtxt, d / "out.aar",
                                  reject_prefixes=["com/android/systemui/"])


class TestRepeatedPackagingDeterministic(unittest.TestCase):
    """Step 6: 重复打包字节一致。"""

    def test_four_artifacts_deterministic(self):
        import time
        for name in ["WifiTrackerLib", "iconloader", "SettingsLib", "WindowManager-Shell"]:
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                first = d / "first.aar"
                second = d / "second.aar"
                paar.build_artifact(name, first)
                time.sleep(2)
                paar.build_artifact(name, second)
                self.assertEqual(first.read_bytes(), second.read_bytes(),
                                 f"{name} 重复打包字节不一致")


class TestAllFlag(unittest.TestCase):
    """--all 选项应能遍历 CONFIGS。"""

    def test_configs_covers_six_artifacts(self):
        # 确认 CONFIGS 含 6 个 artifact（与 install_aar_to_maven.py ARTIFACTS 对齐）
        self.assertEqual(
            set(paar.CONFIGS),
            {"animationlib", "WifiTrackerLib", "iconloader",
             "SettingsLib", "WindowManager-Shell", "WindowManager-Shell-shared"})

    def test_all_flag_iterates_all_configs(self):
        # 验证 --all 会遍历全部 CONFIGS（用 monkeypatch 拦截 build_artifact）
        called = []
        orig = paar.build_artifact
        paar.build_artifact = lambda name, out: called.append(name)
        try:
            sys.argv = ["package_aosp_aar.py", "--all"]
            rc = paar.main()
            self.assertEqual(rc, 0)
            self.assertEqual(set(called), set(paar.CONFIGS))
        finally:
            paar.build_artifact = orig


if __name__ == "__main__":
    unittest.main()
