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

    def test_excluded_prefix_is_omitted_but_other_classes_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code.jar"
            _make_jar(
                code,
                {
                    "com/android/wm/shell/shared/IHomeTransitionListener.class": b"aidl",
                    "com/android/wm/shell/ShellTaskOrganizer.class": b"main",
                },
            )
            resources = root / "res"
            resources.mkdir()
            manifest = root / "AndroidManifest.xml"
            manifest.write_bytes(b"<manifest/>")
            rtxt = root / "R.txt"
            rtxt.write_bytes(b"")
            output = root / "library.aar"

            paar.assemble_aar(
                [code],
                resources,
                manifest,
                rtxt,
                output,
                exclude_prefixes=[
                    "com/android/wm/shell/shared/IHomeTransitionListener"
                ],
            )

            with zipfile.ZipFile(output) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as classes:
                    names = set(classes.namelist())
            self.assertNotIn(
                "com/android/wm/shell/shared/IHomeTransitionListener.class", names
            )
            self.assertIn("com/android/wm/shell/ShellTaskOrganizer.class", names)

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
        # Task 036：code 必须是 owning Soong 的 javac + kotlin implementation 输出（有序两项）
        self.assertEqual(
            cfg["code"],
            [
                paar.SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/javac/iconloader.jar",
                paar.SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/kotlin/iconloader.jar",
            ],
        )
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
        for name in ["WifiTrackerLib", "iconloader", "SettingsLib", "animationlib", "SettingsLibColor"]:
            self.assertFalse(paar.CONFIGS[name].get("reject_sysui", False),
                             f"{name} 不应 reject_sysui")


    def test_settingslib_color_config_paths(self):
        cfg = paar.CONFIGS["SettingsLibColor"]
        self.assertEqual(cfg["code"], [])  # res-only 模块，无代码 JAR
        self.assertIn("SettingsLib/Color/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("Color/AndroidManifest.xml"))
        self.assertIn("SettingsLibColor/android_common/R.txt", str(cfg["rtxt"]))

    def test_setupcompat_config_paths(self):
        cfg = paar.CONFIGS["setupcompat"]
        code = str(cfg["code"])
        self.assertIn("setupcompat/android_common/javac/setupcompat.jar", code)
        self.assertNotIn("turbine", code)  # 必须是 javac 产物，非 turbine header
        self.assertIn("setupcompat/main/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("setupcompat/AndroidManifest.xml"))
        self.assertIn("setupcompat/android_common/R.txt", str(cfg["rtxt"]))
        self.assertEqual(cfg["output"], "libs/aars/setupcompat.aar")
        # setupcompat 是 com.google.android.setupcompat，无 com/android/systemui 类，无需 reject_sysui
        self.assertFalse(cfg.get("reject_sysui", False))

    def test_settingslib_program_code_inputs(self):
        """Task 040：main code = javac discovery + 主 Kotlin + DeviceStateRotationLock Kotlin；
        Theme code = 其 owning Kotlin JAR（不得并入 main）。"""
        cfg = paar.CONFIGS["SettingsLib"]
        discovered = paar._discover_settingslib_code_jars()
        main_kotlin = (
            paar.SOONG_DIR
            / "frameworks/base/packages/SettingsLib/SettingsLib/android_common/kotlin/SettingsLib.jar"
        )
        device_kotlin = (
            paar.SOONG_DIR
            / "frameworks/base/packages/SettingsLib/DeviceStateRotationLock/"
              "SettingsLibDeviceStateRotationLock/android_common/kotlin/"
              "SettingsLibDeviceStateRotationLock.jar"
        )
        self.assertEqual(cfg["code"], discovered + [main_kotlin, device_kotlin])

        theme_kotlin = (
            paar.SOONG_DIR
            / "frameworks/base/packages/SettingsLib/SettingsTheme/"
              "SettingsLibSettingsTheme/android_common/kotlin/SettingsLibSettingsTheme.jar"
        )
        self.assertEqual(paar.CONFIGS["SettingsLibSettingsTheme"]["code"], [theme_kotlin])

    def test_settingslib_settings_theme_config_paths(self):
        """SettingsLibSettingsTheme 是独立 Soong target：res + owning Kotlin 代码（Task 040）。

        Task 040 起其代码类由自身 Kotlin JAR 交付（15 类），不再依赖 SettingsLib.aar
        的 static_libs javac 合并；main AAR 不得包含 Theme 目标类。
        """
        cfg = paar.CONFIGS["SettingsLibSettingsTheme"]
        self.assertEqual(
            cfg["code"],
            [paar.SOONG_DIR
             / "frameworks/base/packages/SettingsLib/SettingsTheme/"
               "SettingsLibSettingsTheme/android_common/kotlin/SettingsLibSettingsTheme.jar"],
        )
        self.assertIn("SettingsLib/SettingsTheme/res", str(cfg["res"]))
        self.assertTrue(str(cfg["manifest"]).endswith("SettingsTheme/AndroidManifest.xml"))
        self.assertIn("SettingsLibSettingsTheme/android_common/R.txt", str(cfg["rtxt"]))
        self.assertEqual(cfg["output"], "libs/aars/SettingsLibSettingsTheme.aar")
        self.assertFalse(cfg.get("reject_sysui", False))

    def test_settingslib_closure_seven_target_configs(self):
        """Task 015（B2）：7 个 per-target res-only 配置（code=[]，res/manifest/R.txt 源自各自 AOSP 目录）。"""
        expected = {
            "SettingsLibSelectorWithWidgetPreference": "SelectorWithWidgetPreference",
            "SettingsLibRestrictedLockUtils": "RestrictedLockUtils",
            "SettingsLibActionButtonsPreference": "ActionButtonsPreference",
            "SettingsLibProgressBar": "ProgressBar",
            "SettingsLibTwoTargetPreference": "TwoTargetPreference",
            "SettingsLibLayoutPreference": "LayoutPreference",
            "SettingsLibAdaptiveIcon": "AdaptiveIcon",
        }
        for target, subdir in expected.items():
            cfg = paar.CONFIGS[target]
            self.assertEqual(cfg["code"], [], f"{target} 应为 res-only")
            self.assertEqual(cfg["res"],
                             [paar.AOSP_ROOT / "frameworks/base/packages/SettingsLib" / subdir / "res"])
            self.assertTrue(str(cfg["manifest"]).endswith(f"{subdir}/AndroidManifest.xml"))
            self.assertIn(f"{target}/android_common/R.txt", str(cfg["rtxt"]))
            self.assertEqual(cfg["output"], f"libs/aars/{target}.aar")
            self.assertFalse(cfg.get("reject_sysui", False))

    def test_settingslib_ten_new_resource_configs(self):
        """Task 040（Batch 4D）：10 个新增 per-target res-only 配置
        （code=[]，res/manifest/R.txt 源自各自 AOSP 目录，独立 namespace）。"""
        expected = {
            "SettingsLibMainSwitchPreference": "MainSwitchPreference",
            "SettingsLibAppPreference": "AppPreference",
            "SettingsLibBannerMessagePreference": "BannerMessagePreference",
            "SettingsLibBarChartPreference": "BarChartPreference",
            "SettingsLibButtonPreference": "ButtonPreference",
            "SettingsLibFooterPreference": "FooterPreference",
            "SettingsLibIllustrationPreference": "IllustrationPreference",
            "SettingsLibSliderPreference": "SliderPreference",
            "SettingsLibUsageProgressBarPreference": "UsageProgressBarPreference",
            "SettingsLibSettingsSpinner": "SettingsSpinner",
        }
        for target, subdir in expected.items():
            cfg = paar.CONFIGS[target]
            self.assertEqual(cfg["code"], [], f"{target} 应为 res-only")
            self.assertEqual(
                cfg["res"],
                [paar.AOSP_ROOT / "frameworks/base/packages/SettingsLib" / subdir / "res"],
            )
            self.assertTrue(str(cfg["manifest"]).endswith(f"{subdir}/AndroidManifest.xml"))
            self.assertEqual(
                cfg["rtxt"],
                paar.SOONG_DIR / "frameworks/base/packages/SettingsLib" / subdir / target
                / "android_common/R.txt",
            )
            self.assertEqual(cfg["output"], f"libs/aars/{target}.aar")
            self.assertFalse(cfg.get("reject_sysui", False))


class TestSettingsLibProgramClosure(unittest.TestCase):
    """Task 040：SettingsLib 程序类闭包——780 javac + 372 主 Kotlin + 1 RotationLock
    Kotlin = 1153 类精确不相交并集；Theme 15 类独立交付，零重叠。"""

    MAIN_KOTLIN = (
        paar.SOONG_DIR
        / "frameworks/base/packages/SettingsLib/SettingsLib/android_common/kotlin/SettingsLib.jar"
    )
    DEVICE_KOTLIN = (
        paar.SOONG_DIR
        / "frameworks/base/packages/SettingsLib/DeviceStateRotationLock/"
          "SettingsLibDeviceStateRotationLock/android_common/kotlin/"
          "SettingsLibDeviceStateRotationLock.jar"
    )
    THEME_KOTLIN = (
        paar.SOONG_DIR
        / "frameworks/base/packages/SettingsLib/SettingsTheme/"
          "SettingsLibSettingsTheme/android_common/kotlin/SettingsLibSettingsTheme.jar"
    )

    def _classes_of(self, jar):
        with zipfile.ZipFile(jar) as z:
            return {n: z.read(n) for n in z.namelist() if n.endswith(".class")}

    def _input_union(self):
        """按 packager 语义（R 类排除）机械读取全部配置 code JAR 的 class bytes。"""
        contributions = []
        for jar in paar.CONFIGS["SettingsLib"]["code"]:
            classes = {n: b for n, b in self._classes_of(jar).items()
                       if not paar._is_r_class(n)}
            contributions.append(classes)
        return contributions

    def test_input_class_sets_pairwise_disjoint_union_1153(self):
        contributions = self._input_union()
        self.assertEqual(len(contributions), 34)  # 32 javac + 2 Kotlin
        union = {}
        for c in contributions:
            self.assertEqual(set(c) & set(union), set(),
                             "输入 class 集存在重叠")
            union.update(c)
        self.assertEqual(len(union), 1153, len(union))

    def test_main_classes_jar_exact_union(self):
        contributions = self._input_union()
        expected = {}
        for c in contributions:
            expected.update(c)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLib.aar"
            paar.build_artifact("SettingsLib", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    actual = {n: cj.read(n) for n in cj.namelist() if n.endswith(".class")}
        self.assertEqual(set(actual), set(expected),
                         "输出 class 集不是配置输入的精确并集")
        for name, data in expected.items():
            self.assertEqual(actual[name], data, f"{name} 字节与 Soong 输入不一致")
        self.assertEqual(len(actual), 1153)

    def test_main_owner_classes_present(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLib.aar"
            paar.build_artifact("SettingsLib", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    names = set(cj.namelist())
        self.assertIn("com/android/settingslib/RestrictedPreferenceHelperProvider.class", names)
        self.assertIn("com/android/settingslib/devicestate/PosturesHelper.class", names)

    def test_main_excludes_theme_target_classes(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLib.aar"
            paar.build_artifact("SettingsLib", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    names = set(cj.namelist())
        self.assertNotIn("com/android/settingslib/widget/GroupSectionDividerMixin.class", names)
        self.assertNotIn("com/android/settingslib/widget/SettingsThemeHelper.class", names)

    def test_theme_classes_jar_exact_fifteen(self):
        expected = self._classes_of(self.THEME_KOTLIN)
        self.assertEqual(len(expected), 15)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLibSettingsTheme.aar"
            paar.build_artifact("SettingsLibSettingsTheme", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    actual = {n: cj.read(n) for n in cj.namelist() if n.endswith(".class")}
        self.assertEqual(set(actual), set(expected),
                         "Theme 输出 class 集与其 Kotlin 源 JAR 不一致")
        for name, data in expected.items():
            self.assertEqual(actual[name], data, f"{name} 字节与 Soong 输入不一致")
        self.assertIn("com/android/settingslib/widget/GroupSectionDividerMixin.class", actual)
        self.assertIn("com/android/settingslib/widget/SettingsThemeHelper.class", actual)

    def test_main_and_theme_class_sets_disjoint(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            main_out = d / "SettingsLib.aar"
            theme_out = d / "SettingsLibSettingsTheme.aar"
            paar.build_artifact("SettingsLib", main_out)
            paar.build_artifact("SettingsLibSettingsTheme", theme_out)
            sets = []
            for path in (main_out, theme_out):
                with zipfile.ZipFile(path) as aar:
                    with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                        sets.append({n for n in cj.namelist() if n.endswith(".class")})
        self.assertEqual(sets[0] & sets[1], set(), "main 与 Theme class 集不得重叠")

    def test_rebuild_byte_identical(self):
        import time
        for name in ["SettingsLib", "SettingsLibSettingsTheme"]:
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                first = d / "first.aar"
                second = d / "second.aar"
                paar.build_artifact(name, first)
                time.sleep(2)
                paar.build_artifact(name, second)
                self.assertEqual(first.read_bytes(), second.read_bytes(),
                                 f"{name} 重复打包字节不一致")


class TestSettingsLibSettingsThemeProvenance(unittest.TestCase):
    """Task 013：完整 res 树逐字节溯源——不漏、不多、不改；
    Task 040：加入 owning Kotlin 代码（15 类）。"""

    AOSP_THEME_RES = Path("/home/conv/myspace/aosp/frameworks/base/packages/SettingsLib/SettingsTheme/res")

    def _source_files(self) -> dict:
        return {
            f"res/{p.relative_to(self.AOSP_THEME_RES)}": p.read_bytes()
            for p in sorted(self.AOSP_THEME_RES.rglob("*")) if p.is_file()
        }

    def test_res_entries_match_aosp_tree_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLibSettingsTheme.aar"
            paar.build_artifact("SettingsLibSettingsTheme", out)
            with zipfile.ZipFile(out) as z:
                aar_res = {n: z.read(n) for n in z.namelist() if n.startswith("res/")}
        source = self._source_files()
        self.assertEqual(set(aar_res), set(source),
                         "AAR res entry 集与 AOSP SettingsTheme res 树不一致")
        for name, data in source.items():
            self.assertEqual(aar_res[name], data, f"{name} 字节与 AOSP 源不一致")

    def test_switch_drawable_entries_present(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLibSettingsTheme.aar"
            paar.build_artifact("SettingsLibSettingsTheme", out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
        self.assertIn("res/drawable-v31/settingslib_switch_track.xml", names)
        self.assertIn("res/drawable-v31/settingslib_switch_thumb.xml", names)
        self.assertIn("res/drawable-v34/settingslib_switch_track.xml", names)

    def test_classes_jar_contains_only_theme_kotlin_classes(self):
        """Task 040：classes.jar 恰为其 owning Kotlin JAR 的 15 个类。"""
        from io import BytesIO
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SettingsLibSettingsTheme.aar"
            paar.build_artifact("SettingsLibSettingsTheme", out)
            with zipfile.ZipFile(out) as z:
                self.assertIn("classes.jar", z.namelist())
                with zipfile.ZipFile(BytesIO(z.read("classes.jar"))) as cj:
                    classes = [n for n in cj.namelist()
                               if n.endswith(".class")]
        self.assertEqual(len(classes), 15, classes)
        for n in classes:
            self.assertTrue(n.startswith("com/android/settingslib/widget/"),
                            f"越界类名: {n}")

    def test_rebuild_is_byte_identical(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            first = d / "first.aar"
            second = d / "second.aar"
            paar.build_artifact("SettingsLibSettingsTheme", first)
            time.sleep(2)
            paar.build_artifact("SettingsLibSettingsTheme", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

class TestSettingsLibPerTargetProvenance(unittest.TestCase):
    """Task 015（B2）：7 个 per-target AAR 的 res 树逐字节溯源——不漏、不多、不改。"""

    TARGETS = [
        "SettingsLibSelectorWithWidgetPreference",
        "SettingsLibRestrictedLockUtils",
        "SettingsLibActionButtonsPreference",
        "SettingsLibProgressBar",
        "SettingsLibTwoTargetPreference",
        "SettingsLibLayoutPreference",
        "SettingsLibAdaptiveIcon",
    ]

    def _build(self, target: str, tmpdir: Path) -> Path:
        out = tmpdir / f"{target}.aar"
        paar.build_artifact(target, out)
        return out

    def test_res_entries_match_aosp_tree_exactly(self):
        for target in self.TARGETS:
            subdir = target[len("SettingsLib"):]
            src_root = paar.AOSP_ROOT / "frameworks/base/packages/SettingsLib" / subdir / "res"
            source = {
                f"res/{p.relative_to(src_root)}": p.read_bytes()
                for p in sorted(src_root.rglob("*")) if p.is_file()
            }
            with tempfile.TemporaryDirectory() as d:
                out = self._build(target, Path(d))
                with zipfile.ZipFile(out) as z:
                    aar_res = {n: z.read(n) for n in z.namelist() if n.startswith("res/")}
            self.assertEqual(set(aar_res), set(source),
                             f"{target} res entry 集与 AOSP 源树不一致")
            for name, data in source.items():
                self.assertEqual(aar_res[name], data,
                                 f"{target}/{name} 字节与 AOSP 源不一致")

    def test_closure_keystone_resources_present(self):
        """Task 013 浮出的 3 类缺失资源 + AdaptiveIcon 主资源必须在各自 AAR 中。"""
        keystone = {
            "SettingsLibProgressBar": [
                "res/interpolator/progress_indeterminate_horizontal_rect2_translatex_copy.xml",
            ],
            "SettingsLibActionButtonsPreference": [
                "res/values/styles.xml",
            ],
            "SettingsLibTwoTargetPreference": [
                "res/layout/preference_two_target_divider.xml",
            ],
        }
        for target, names in keystone.items():
            with tempfile.TemporaryDirectory() as d:
                out = self._build(target, Path(d))
                with zipfile.ZipFile(out) as z:
                    have = set(z.namelist())
            for n in names:
                self.assertIn(n, have, f"{target} 缺 {n}")

    def test_no_code_entries(self):
        from io import BytesIO
        for target in self.TARGETS:
            with tempfile.TemporaryDirectory() as d:
                out = self._build(target, Path(d))
                with zipfile.ZipFile(out) as z:
                    self.assertIn("classes.jar", z.namelist())
                    with zipfile.ZipFile(BytesIO(z.read("classes.jar"))) as cj:
                        self.assertEqual(
                            [n for n in cj.namelist()
                             if not n.endswith("/") and n != "META-INF/MANIFEST.MF"],
                            [], f"{target} 应为 res-only")

    def test_rebuild_is_byte_identical(self):
        import time
        for target in self.TARGETS:
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                first = self._build(target, d / "first.aar")
                time.sleep(2)
                second = self._build(target, d / "second.aar")
                self.assertEqual(first.read_bytes(), second.read_bytes(),
                                 f"{target} 重复打包字节不一致")


class TestSettingsLibNewResourceProvenance(unittest.TestCase):
    """Task 040（Batch 4D）：10 个新 res-only AAR——res 树逐字节溯源不漏不多不改、
    空 classes.jar、manifest/R.txt 原样、确定性。"""

    NEW_RESOURCE_TARGETS = {
        "SettingsLibMainSwitchPreference": "MainSwitchPreference",
        "SettingsLibAppPreference": "AppPreference",
        "SettingsLibBannerMessagePreference": "BannerMessagePreference",
        "SettingsLibBarChartPreference": "BarChartPreference",
        "SettingsLibButtonPreference": "ButtonPreference",
        "SettingsLibFooterPreference": "FooterPreference",
        "SettingsLibIllustrationPreference": "IllustrationPreference",
        "SettingsLibSliderPreference": "SliderPreference",
        "SettingsLibUsageProgressBarPreference": "UsageProgressBarPreference",
        "SettingsLibSettingsSpinner": "SettingsSpinner",
    }

    EXPECTED_COUNTS = {
        "SettingsLibMainSwitchPreference": 22,
        "SettingsLibAppPreference": 91,
        "SettingsLibBannerMessagePreference": 96,
        "SettingsLibBarChartPreference": 6,
        "SettingsLibButtonPreference": 23,
        "SettingsLibFooterPreference": 91,
        "SettingsLibIllustrationPreference": 6,
        "SettingsLibSliderPreference": 5,
        "SettingsLibUsageProgressBarPreference": 1,
        "SettingsLibSettingsSpinner": 5,
    }

    def _build(self, target: str, tmpdir: Path) -> Path:
        out = tmpdir / f"{target}.aar"
        paar.build_artifact(target, out)
        return out

    def test_source_tree_counts_total_346(self):
        total = 0
        for target, subdir in self.NEW_RESOURCE_TARGETS.items():
            src_root = paar.AOSP_ROOT / "frameworks/base/packages/SettingsLib" / subdir / "res"
            count = sum(1 for p in src_root.rglob("*") if p.is_file())
            self.assertEqual(count, self.EXPECTED_COUNTS[target],
                             f"{target} AOSP 源树文件数变化")
            total += count
        self.assertEqual(total, 346)

    def test_res_entries_match_aosp_tree_exactly(self):
        for target, subdir in self.NEW_RESOURCE_TARGETS.items():
            src_root = paar.AOSP_ROOT / "frameworks/base/packages/SettingsLib" / subdir / "res"
            source = {
                f"res/{p.relative_to(src_root)}": p.read_bytes()
                for p in sorted(src_root.rglob("*")) if p.is_file()
            }
            with tempfile.TemporaryDirectory() as d:
                out = self._build(target, Path(d))
                with zipfile.ZipFile(out) as z:
                    aar_res = {n: z.read(n) for n in z.namelist() if n.startswith("res/")}
                    manifest_bytes = z.read("AndroidManifest.xml")
                    rtxt_bytes = z.read("R.txt")
            self.assertEqual(set(aar_res), set(source),
                             f"{target} res entry 集与 AOSP 源树不一致")
            for name, data in source.items():
                self.assertEqual(aar_res[name], data,
                                 f"{target}/{name} 字节与 AOSP 源不一致")
            cfg = paar.CONFIGS[target]
            self.assertEqual(manifest_bytes, cfg["manifest"].read_bytes(),
                             f"{target} AndroidManifest.xml 字节与 AOSP 源不一致")
            self.assertEqual(rtxt_bytes, cfg["rtxt"].read_bytes(),
                             f"{target} R.txt 字节与 Soong 输出不一致")

    def test_no_code_entries(self):
        from io import BytesIO
        for target in self.NEW_RESOURCE_TARGETS:
            with tempfile.TemporaryDirectory() as d:
                out = self._build(target, Path(d))
                with zipfile.ZipFile(out) as z:
                    self.assertIn("classes.jar", z.namelist())
                    with zipfile.ZipFile(BytesIO(z.read("classes.jar"))) as cj:
                        self.assertEqual(
                            [n for n in cj.namelist()
                             if not n.endswith("/") and n != "META-INF/MANIFEST.MF"],
                            [], f"{target} 应为 res-only")

    def test_rebuild_is_byte_identical(self):
        import time
        for target in self.NEW_RESOURCE_TARGETS:
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                first = self._build(target, d / "first.aar")
                time.sleep(2)
                second = self._build(target, d / "second.aar")
                self.assertEqual(first.read_bytes(), second.read_bytes(),
                                 f"{target} 重复打包字节不一致")


class TestIconloaderProvenance(unittest.TestCase):
    """Task 036：iconloader AAR 完整 Kotlin closure——59+16=75 类精确并集 + 资源溯源 + 确定性。"""

    def _input_classes(self) -> "tuple[dict, dict]":
        """返回 (javac 贡献, kotlin 贡献) 的 {class_name: bytes}。"""
        javac_jar, kotlin_jar = paar.CONFIGS["iconloader"]["code"]
        contributions = []
        for jar in (javac_jar, kotlin_jar):
            with zipfile.ZipFile(jar) as z:
                contributions.append({
                    n: z.read(n) for n in z.namelist()
                    if n.endswith(".class")
                })
        return contributions[0], contributions[1]

    def test_classes_exact_disjoint_union(self):
        from io import BytesIO
        javac, kotlin = self._input_classes()
        # 输入贡献必须是精确的 59 + 16，且不相交
        self.assertEqual(len(javac), 59)
        self.assertEqual(len(kotlin), 16)
        self.assertEqual(set(javac) & set(kotlin), set())
        expected = {**javac, **kotlin}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "iconloader.aar"
            paar.build_artifact("iconloader", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    actual = {n: cj.read(n) for n in cj.namelist() if n.endswith(".class")}
        self.assertEqual(set(actual), set(expected),
                         "输出 class 集不是两输入的精确并集")
        for name, data in expected.items():
            self.assertEqual(actual[name], data, f"{name} 字节与 Soong 输入不一致")
        self.assertEqual(len(actual), 75)
        for name in actual:
            self.assertTrue(name.startswith("com/android/launcher3/"),
                            f"越界类名: {name}")

    def test_resource_manifest_rtxt_provenance(self):
        cfg = paar.CONFIGS["iconloader"]
        res_root = cfg["res"][0]
        source_res = {
            f"res/{p.relative_to(res_root)}": p.read_bytes()
            for p in sorted(res_root.rglob("*")) if p.is_file()
        }
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "iconloader.aar"
            paar.build_artifact("iconloader", out)
            with zipfile.ZipFile(out) as z:
                aar_res = {n: z.read(n) for n in z.namelist() if n.startswith("res/")}
                manifest_bytes = z.read("AndroidManifest.xml")
                rtxt_bytes = z.read("R.txt")
        self.assertEqual(set(aar_res), set(source_res),
                         "AAR res entry 集与 AOSP iconloaderlib res 树不一致")
        for name, data in source_res.items():
            self.assertEqual(aar_res[name], data, f"{name} 字节与 AOSP 源不一致")
        self.assertEqual(manifest_bytes, cfg["manifest"].read_bytes(),
                         "AndroidManifest.xml 字节与 AOSP 源不一致")
        self.assertEqual(rtxt_bytes, cfg["rtxt"].read_bytes(),
                         "R.txt 字节与 Soong 输出不一致")

    def test_rebuild_is_byte_identical(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            first = d / "first.aar"
            second = d / "second.aar"
            paar.build_artifact("iconloader", first)
            time.sleep(2)
            paar.build_artifact("iconloader", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


class TestWMShellProtoProvenance(unittest.TestCase):
    """Task 037：WM-Shell AAR proto closure——(主 javac∪kotlin 去除 exclude)∪40 proto=1888 类精确并集。"""

    SHELL = paar.SOONG_DIR / "frameworks/base/libs/WindowManager/Shell"
    PROTO_JAR = SHELL / "WindowManager-Shell-proto/android_common/javac/WindowManager-Shell-proto.jar"          # noqa: E501  bp L138（nano）
    LITE_PROTO_JAR = SHELL / "WindowManager-Shell-lite-proto/android_common/javac/WindowManager-Shell-lite-proto.jar"  # noqa: E501  bp L148（lite）

    # 审计 docs/architecture/2026-08-20-r8-runtime-closure-audit.md §7 的 A4 18 项目标
    R8_TARGETS = (
        "com/android/wm/shell/desktopmode/education/data/WindowingEducationProto.class",
        "com/android/wm/shell/desktopmode/education/data/WindowingEducationProto$AppHandleEducation.class",      # noqa: E501
        "com/android/wm/shell/desktopmode/education/data/WindowingEducationProto$AppHandleEducation$Builder.class",  # noqa: E501
        "com/android/wm/shell/desktopmode/education/data/WindowingEducationProto$AppToWebEducation.class",       # noqa: E501
        "com/android/wm/shell/desktopmode/education/data/WindowingEducationProto$AppToWebEducation$Builder.class",   # noqa: E501
        "com/android/wm/shell/desktopmode/education/data/WindowingEducationProto$Builder.class",               # noqa: E501
        "com/android/wm/shell/desktopmode/persistence/Desktop.class",
        "com/android/wm/shell/desktopmode/persistence/Desktop$Builder.class",
        "com/android/wm/shell/desktopmode/persistence/DesktopPersistentRepositories.class",
        "com/android/wm/shell/desktopmode/persistence/DesktopPersistentRepositories$Builder.class",            # noqa: E501
        "com/android/wm/shell/desktopmode/persistence/DesktopRepositoryState.class",
        "com/android/wm/shell/desktopmode/persistence/DesktopRepositoryState$Builder.class",
        "com/android/wm/shell/desktopmode/persistence/DesktopTask.class",
        "com/android/wm/shell/desktopmode/persistence/DesktopTask$Builder.class",
        "com/android/wm/shell/desktopmode/persistence/DesktopTaskState.class",
        "com/android/wm/shell/nano/HandlerMapping.class",
        "com/android/wm/shell/nano/Transition.class",
        "com/android/wm/shell/nano/WmShellTransitionTraceProto.class",
    )

    def _config_code(self):
        return list(paar.CONFIGS["WindowManager-Shell"]["code"])

    def _input_classes(self, jar):
        with zipfile.ZipFile(jar) as z:
            return {n: z.read(n) for n in z.namelist() if n.endswith(".class")}

    def test_config_code_ordered_four_jars(self):
        """Task 037：code 必须是主 javac、主 kotlin、proto（nano）、lite-proto 四项有序列表。"""
        self.assertEqual(
            self._config_code(),
            [
                self.SHELL / "WindowManager-Shell/android_common/javac/WindowManager-Shell.jar",
                self.SHELL / "WindowManager-Shell/android_common/kotlin/WindowManager-Shell.jar",
                self.PROTO_JAR,
                self.LITE_PROTO_JAR,
            ],
        )

    def test_classes_exact_disjoint_union(self):
        from io import BytesIO
        javac = self._input_classes(self._config_code()[0])
        kotlin = self._input_classes(self._config_code()[1])
        proto = self._input_classes(self.PROTO_JAR)
        lite = self._input_classes(self.LITE_PROTO_JAR)
        # 输入贡献规模固定：主 1183+677（去 exclude 后 1848）、nano 4、lite 36
        self.assertEqual(len(javac), 1183)
        self.assertEqual(len(kotlin), 677)
        self.assertEqual(len(proto), 4)
        self.assertEqual(len(lite), 36)
        excluded = paar.CONFIGS["WindowManager-Shell"]["exclude_prefixes"]
        main = {**javac, **kotlin}
        main = {n: b for n, b in main.items()
                if not any(n.startswith(p) for p in excluded)}
        self.assertEqual(len(main), 1848)
        # 四个来源两两不相交（主 javac/kotlin 之间由 merge 检查；这里验证 proto 侧）
        self.assertEqual(set(proto) & set(lite), set())
        self.assertEqual((set(proto) | set(lite)) & set(main), set())
        expected = {**main, **proto, **lite}
        self.assertEqual(len(expected), 1888)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "WindowManager-Shell.aar"
            paar.build_artifact("WindowManager-Shell", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    actual = {n: cj.read(n) for n in cj.namelist() if n.endswith(".class")}
        self.assertEqual(set(actual), set(expected),
                         "输出 class 集不是四输入（去 exclude）的精确并集")
        for name, data in expected.items():
            self.assertEqual(actual[name], data, f"{name} 字节与 Soong 输入不一致")
        self.assertEqual(len(actual), 1888)
        # 命名空间约束：40 个 proto 类全部在 com/android/wm/shell/ 下；
        # 主产物带来的 com/android/internal/protolog 2 类是 1.0.0 基线既有
        # （wm_shell protolog cache，owning Soong javac 产物），不得新增其它越界类
        proto_names = set(proto) | set(lite)
        for name in proto_names:
            self.assertTrue(name.startswith("com/android/wm/shell/"),
                            f"proto 越界类名: {name}")
        baseline_ns = {n for n in actual if not n.startswith("com/android/wm/shell/")}
        self.assertEqual(
            baseline_ns,
            {"com/android/internal/protolog/ProtoLogImpl_992223594.class",
             "com/android/internal/protolog/ProtoLogImpl_992223594$Cache.class"},
            "除基线既有的 2 个 protolog 类外出现新增越界类")

    def test_proto_r8_targets_present(self):
        from io import BytesIO
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "WindowManager-Shell.aar"
            paar.build_artifact("WindowManager-Shell", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    names = set(cj.namelist())
        for t in self.R8_TARGETS:
            self.assertIn(t, names, f"R8 目标类缺失: {t}")

    def test_resource_manifest_rtxt_provenance(self):
        cfg = paar.CONFIGS["WindowManager-Shell"]
        res_root = cfg["res"][0]
        source_res = {
            f"res/{p.relative_to(res_root)}": p.read_bytes()
            for p in sorted(res_root.rglob("*")) if p.is_file()
        }
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "WindowManager-Shell.aar"
            paar.build_artifact("WindowManager-Shell", out)
            with zipfile.ZipFile(out) as z:
                aar_res = {n: z.read(n) for n in z.namelist() if n.startswith("res/")}
                manifest_bytes = z.read("AndroidManifest.xml")
                rtxt_bytes = z.read("R.txt")
        self.assertEqual(set(aar_res), set(source_res),
                         "AAR res entry 集与 AOSP Shell res 树不一致")
        for name, data in source_res.items():
            self.assertEqual(aar_res[name], data, f"{name} 字节与 AOSP 源不一致")
        self.assertEqual(manifest_bytes, cfg["manifest"].read_bytes(),
                         "AndroidManifest.xml 字节与 AOSP 源不一致")
        self.assertEqual(rtxt_bytes, cfg["rtxt"].read_bytes(),
                         "R.txt 字节与 Soong 输出不一致")

    def test_rebuild_is_byte_identical(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            first = d / "first.aar"
            second = d / "second.aar"
            paar.build_artifact("WindowManager-Shell", first)
            time.sleep(2)
            paar.build_artifact("WindowManager-Shell", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())


class TestTraceurProvenance(unittest.TestCase):
    """Task 038（Batch 4C）：Traceur 双 AAR——TraceurCommon（15+625=640 类，无 res）
    + Traceur-res（res-only 105 文件，namespace com.android.traceur.res）。

    依据 packages/apps/Traceur/Android.bp：TraceurCommon.static_libs 含
    perfetto_config_java_protos（与 WM-Shell 并入 proto static_libs 同构，先例 Task 037）。
    """

    TRACEUR = paar.AOSP_ROOT / "packages/apps/Traceur"
    TRACEUR_SOONG = paar.SOONG_DIR / "packages/apps/Traceur"
    PERFETTO_PROTO_JAR = (paar.SOONG_DIR /
                          "external/perfetto/perfetto_config_java_protos/android_common/javac/perfetto_config_java_protos.jar")  # noqa: E501

    # 审计 A7：5 个 class 级 R8 目标（另 2 个 traceur.res.R$* 由 AGP 从 R.txt 重新生成）
    R8_CLASS_TARGETS = (
        "com/android/traceur/FileSender.class",
        "com/android/traceur/PresetTraceConfigs.class",
        "com/android/traceur/PresetTraceConfigs$TraceOptions.class",
        "com/android/traceur/TraceConfig.class",
        "com/android/traceur/TraceConfig$Builder.class",
    )

    def _classes_of(self, jar):
        with zipfile.ZipFile(jar) as z:
            return {n: z.read(n) for n in z.namelist() if n.endswith(".class")}

    def test_traceur_common_config(self):
        """code = TraceurCommon javac ∪ perfetto proto javac；无 res；manifest/rtxt 溯源。"""
        cfg = paar.CONFIGS["TraceurCommon"]
        self.assertEqual(cfg["code"], [
            self.TRACEUR_SOONG / "TraceurCommon/android_common/javac/TraceurCommon.jar",
            self.PERFETTO_PROTO_JAR,
        ])
        self.assertEqual(cfg["res"], [])
        self.assertEqual(cfg["manifest"], self.TRACEUR / "AndroidManifest-common.xml")
        self.assertEqual(cfg["rtxt"],
                         self.TRACEUR_SOONG / "TraceurCommon/android_common/R.txt")
        self.assertEqual(cfg["output"], "libs/aars/TraceurCommon.aar")

    def test_traceur_res_config(self):
        """res-only：code=[]；res = Traceur/res；manifest/rtxt 溯源。"""
        cfg = paar.CONFIGS["Traceur-res"]
        self.assertEqual(cfg["code"], [])
        self.assertEqual(cfg["res"], [self.TRACEUR / "res"])
        self.assertEqual(cfg["manifest"], self.TRACEUR / "AndroidManifest-res.xml")
        self.assertEqual(cfg["rtxt"],
                         self.TRACEUR_SOONG / "Traceur-res/android_common/R.txt")
        self.assertEqual(cfg["output"], "libs/aars/Traceur-res.aar")

    def test_traceur_common_classes_exact_disjoint_union(self):
        """640 类 = 15（com/android/traceur/）∪ 625（perfetto/protos/）不相交并集，字节一致。"""
        traceur = self._classes_of(paar.CONFIGS["TraceurCommon"]["code"][0])
        protos = self._classes_of(self.PERFETTO_PROTO_JAR)
        self.assertEqual(len(traceur), 15)
        self.assertEqual(len(protos), 625)
        self.assertEqual(set(traceur) & set(protos), set())
        for n in traceur:
            self.assertTrue(n.startswith("com/android/traceur/"), f"越界类名: {n}")
        for n in protos:
            self.assertTrue(n.startswith("perfetto/protos/"), f"越界类名: {n}")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "TraceurCommon.aar"
            paar.build_artifact("TraceurCommon", out)
            with zipfile.ZipFile(out) as aar:
                names = set(aar.namelist())
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    actual = {n: cj.read(n) for n in cj.namelist()
                              if n.endswith(".class")}
        expected = {**traceur, **protos}
        self.assertEqual(len(actual), 640)
        self.assertEqual(set(actual), set(expected),
                         "输出 class 集不是两输入的精确并集")
        for name, data in expected.items():
            self.assertEqual(actual[name], data, f"{name} 字节与 Soong 输入不一致")
        # 无 res 条目；manifest/R.txt 原样
        self.assertFalse({n for n in names if n.startswith("res/")})
        self.assertEqual(names, {"classes.jar", "AndroidManifest.xml", "R.txt"})

    def test_traceur_common_manifest_and_rtxt(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "TraceurCommon.aar"
            paar.build_artifact("TraceurCommon", out)
            with zipfile.ZipFile(out) as z:
                manifest_bytes = z.read("AndroidManifest.xml")
                rtxt_bytes = z.read("R.txt")
        cfg = paar.CONFIGS["TraceurCommon"]
        self.assertEqual(manifest_bytes, cfg["manifest"].read_bytes())
        self.assertEqual(rtxt_bytes, cfg["rtxt"].read_bytes())
        self.assertIn(b'package="com.android.traceur.common"', manifest_bytes)
        self.assertIn(b"android.permission.CONTROL_UI_TRACING", manifest_bytes)

    def test_traceur_common_r8_targets_present(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "TraceurCommon.aar"
            paar.build_artifact("TraceurCommon", out)
            with zipfile.ZipFile(out) as aar:
                with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as cj:
                    names = set(cj.namelist())
        for t in self.R8_CLASS_TARGETS:
            self.assertIn(t, names, f"R8 目标类缺失: {t}")

    def test_traceur_res_no_code_and_res_matches_aosp(self):
        """0 类；res 恰好 105 文件与 AOSP 树字节一致；R.txt 与 Soong 一致。"""
        res_root = self.TRACEUR / "res"
        source_res = {
            f"res/{p.relative_to(res_root)}": p.read_bytes()
            for p in sorted(res_root.rglob("*")) if p.is_file()
        }
        self.assertEqual(len(source_res), 105)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "Traceur-res.aar"
            paar.build_artifact("Traceur-res", out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
                aar_res = {n: z.read(n) for n in names if n.startswith("res/")}
                with zipfile.ZipFile(BytesIO(z.read("classes.jar"))) as cj:
                    classes = [n for n in cj.namelist() if n.endswith(".class")]
                manifest_bytes = z.read("AndroidManifest.xml")
                rtxt_bytes = z.read("R.txt")
        self.assertEqual(classes, [])
        self.assertEqual(set(aar_res), set(source_res),
                         "AAR res entry 集与 AOSP Traceur res 树不一致")
        for name, data in source_res.items():
            self.assertEqual(aar_res[name], data, f"{name} 字节与 AOSP 源不一致")
        self.assertIn(b'package="com.android.traceur.res"', manifest_bytes)
        self.assertEqual(rtxt_bytes,
                         (self.TRACEUR_SOONG / "Traceur-res/android_common/R.txt").read_bytes(),
                         "R.txt 字节与 Soong 输出不一致")
        self.assertEqual(names, {"classes.jar", "AndroidManifest.xml", "R.txt"}
                         | set(aar_res))

    def test_traceur_res_rtxt_has_r8_symbol_types(self):
        """R$array / R$string（R8 目标 6-7）由 AGP 从 R.txt 重新生成：符号类型必须在表内。"""
        rtxt = (self.TRACEUR_SOONG / "Traceur-res/android_common/R.txt").read_text()
        types = {line.split()[1] for line in rtxt.splitlines() if line.strip()}
        self.assertIn("array", types)
        self.assertIn("string", types)

    def test_rebuild_is_byte_identical(self):
        import time
        for name in ["TraceurCommon", "Traceur-res"]:
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                first = d / "first.aar"
                second = d / "second.aar"
                paar.build_artifact(name, first)
                time.sleep(2)
                paar.build_artifact(name, second)
                self.assertEqual(first.read_bytes(), second.read_bytes(),
                                 f"{name} 重复打包字节不一致")


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
        # 确认 CONFIGS 含 29 个 artifact（Task 015 新增 7 个 SettingsLib per-target
        # res-only target；Task 038 新增 Traceur 双 AAR；Task 040 新增 10 个
        # SettingsLib per-target res-only target）
        self.assertEqual(
            set(paar.CONFIGS),
            {"animationlib", "WifiTrackerLib", "iconloader",
             "SettingsLib", "WindowManager-Shell", "WindowManager-Shell-shared",
             "LowLightDreamLib", "SettingsLibColor", "setupcompat",
             "SettingsLibSettingsTheme",
             "SettingsLibSelectorWithWidgetPreference",
             "SettingsLibRestrictedLockUtils",
             "SettingsLibActionButtonsPreference",
             "SettingsLibProgressBar",
             "SettingsLibTwoTargetPreference",
             "SettingsLibLayoutPreference",
             "SettingsLibAdaptiveIcon",
             "SettingsLibMainSwitchPreference",
             "SettingsLibAppPreference",
             "SettingsLibBannerMessagePreference",
             "SettingsLibBarChartPreference",
             "SettingsLibButtonPreference",
             "SettingsLibFooterPreference",
             "SettingsLibIllustrationPreference",
             "SettingsLibSliderPreference",
             "SettingsLibUsageProgressBarPreference",
             "SettingsLibSettingsSpinner",
             "TraceurCommon", "Traceur-res"})
        self.assertEqual(len(paar.CONFIGS), 29)

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
