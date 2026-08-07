#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/check_source_alignment.py.

验证对齐脚本的：
  1. 目标 owner 清单（EXPECTED_OWNERS / FORBIDDEN_OWNERS）
  2. res 根目录映射到 SystemUI-res
  3. 相对路径相同但字节不同 → MODIFIED
  4. 同一 Gradle module 的不同 source root 中的文件 → MISPLACED（root-aware）
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

# 动态导入 tools/check_source_alignment.py（非 package）
_SCRIPT = Path(__file__).resolve().parents[1] / "check_source_alignment.py"
_spec = importlib.util.spec_from_file_location("check_source_alignment", _SCRIPT)
csa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(csa)


EXPECTED_OWNERS = {
    "SystemUI-core",
    "SystemUI-common",
    "SystemUI-animation",
    "SystemUI-plugin-core",
    "SystemUI-plugin-processor",
    "SystemUI-plugin",
    "SystemUI-unfold",
    "SystemUI-customization",
    "SystemUI-shared",
    "SystemUI-shared-biometrics",
    "SystemUI-compose",
}

FORBIDDEN_OWNERS = {
    "SystemUI-log",
    "SystemUI-animationlib",
    "SystemUI-utils-kairos",
    "SystemUI-compose-core",
    "SystemUI-compose-scene",
    "SystemUI-shared-keyguard",
    "SystemUI-proto",
    "SystemUI-pods-dagger",
    "SystemUI-pods-retail",
    "SystemUI-pods-data",
    "SystemUI-pods-domain",
    "SystemUI-pods-settings",
}


class TestOwners(unittest.TestCase):
    def _owners_in_mappings(self):
        return {m.project_module for m in csa.SOURCE_MAPPINGS}

    def test_expected_owners_present(self):
        actual = self._owners_in_mappings()
        missing = EXPECTED_OWNERS - actual
        self.assertFalse(missing, f"缺少期望 owner: {missing}")

    def test_no_forbidden_owners(self):
        actual = self._owners_in_mappings()
        forbidden = actual & FORBIDDEN_OWNERS
        self.assertFalse(forbidden, f"出现已废止 owner: {forbidden}")

    def test_no_none_src_root(self):
        for m in csa.SOURCE_MAPPINGS:
            self.assertIsNotNone(m.project_src_root, f"{m.project_module} src_root 为 None")


class TestResMappings(unittest.TestCase):
    def test_res_roots_map_to_systemui_res(self):
        d = dict(csa.RES_MAPPINGS)
        for root in ("res", "res-keyguard", "res-product"):
            self.assertIn(root, d, f"缺少 res 根 {root}")
            self.assertTrue(d[root].startswith("SystemUI-res/"),
                            f"{root} 应映射到 SystemUI-res，实际 {d[root]}")

    def test_no_animationlib_res(self):
        for _, proj_rel in csa.RES_MAPPINGS:
            self.assertNotIn("animationlib", proj_rel, f"animationlib res 不应再出现: {proj_rel}")


class TestContentModified(unittest.TestCase):
    def test_same_bytes_not_modified(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a").mkdir()
            (root / "a" / "Foo.kt").write_bytes(b"hello\n")
            (root / "b").mkdir()
            (root / "b" / "Foo.kt").write_bytes(b"hello\n")
            aosp = csa.walk_source(root / "a", csa.SOURCE_SUFFIXES)
            proj = csa.walk_source(root / "b", csa.SOURCE_SUFFIXES)
            _, _, modified = csa.diff_pair(aosp, proj)
            self.assertEqual(modified, [])

    def test_different_bytes_reported_modified(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a").mkdir()
            (root / "a" / "Foo.kt").write_bytes(b"hello\n")
            (root / "b").mkdir()
            (root / "b" / "Foo.kt").write_bytes(b"world\n")
            aosp = csa.walk_source(root / "a", csa.SOURCE_SUFFIXES)
            proj = csa.walk_source(root / "b", csa.SOURCE_SUFFIXES)
            _, _, modified = csa.diff_pair(aosp, proj)
            self.assertEqual(modified, ["Foo.kt"])


class TestRootAwareMisplaced(unittest.TestCase):
    """同一 module 的不同 source root 中的文件应被判为 MISPLACED。"""

    def _mapping(self, aosp_sub, src_root):
        return csa.M([aosp_sub], "Mod", src_root, recursive=True)

    def test_file_in_wrong_src_root_same_module_is_misplaced(self):
        mappings = [self._mapping("common/src", "common/src"),
                    self._mapping("log/src", "log/src")]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            aosp = root / "aosp"
            proj = root / "proj"
            # AOSP: common/src 有 Foo.kt, log/src 有 Bar.kt
            (aosp / "common/src").mkdir(parents=True)
            (aosp / "common/src/Foo.kt").write_bytes(b"1")
            (aosp / "log/src").mkdir(parents=True)
            (aosp / "log/src/Bar.kt").write_bytes(b"2")
            # 项目: Foo.kt 放到了 log/src（错误 root，同 module）
            (proj / "Mod/log/src").mkdir(parents=True)
            (proj / "Mod/log/src/Foo.kt").write_bytes(b"1")
            # 项目: Bar.kt 放到了 common/src（错误 root，同 module）
            (proj / "Mod/common/src").mkdir(parents=True)
            (proj / "Mod/common/src/Bar.kt").write_bytes(b"2")

            result = csa.run_source_check(mappings, aosp, proj)
            misplaced_tails = {mp[2] for mp in result["misplaced"]}
            self.assertIn("Foo.kt", misplaced_tails, "Foo.kt 放错 root 应判 MISPLACED")
            self.assertIn("Bar.kt", misplaced_tails, "Bar.kt 放错 root 应判 MISPLACED")
            # 不应报 MISSING（放错不算漏）
            missing_tails = {ms[3] for ms in result["missing"]}
            self.assertNotIn("Foo.kt", missing_tails)
            self.assertNotIn("Bar.kt", missing_tails)


class TestDuplicateTailAcrossExpectedRoots(unittest.TestCase):
    """同一 tail 在 AOSP 有多个合法 root（如 src-debug + src-release）时，
    项目只放了一份，另一份的缺失必须被报告为 MISSING，
    不能被合法的另一份掩盖成“别处有”。"""

    def test_missing_one_of_two_valid_roots_is_reported(self):
        mappings = [
            csa.M(["src-debug"], "Core", "src-debug"),
            csa.M(["src-release"], "Core", "src-release"),
        ]
        tail = Path("com/android/systemui/flags/FlagsFactory.kt")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            aosp = root / "aosp"
            project = root / "project"
            # AOSP: src-debug 和 src-release 各有一份（内容不同）
            for variant, body in (("src-debug", b"debug"), ("src-release", b"release")):
                path = aosp / variant / tail
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
            # 项目：只放了 src-release（合法 root），缺 src-debug
            release = project / "Core/src-release" / tail
            release.parent.mkdir(parents=True, exist_ok=True)
            release.write_bytes(b"release")

            result = csa.run_source_check(mappings, aosp, project)

            # src-debug 的缺失必须被报告
            missing_tails = [item[3] for item in result["missing"]]
            self.assertEqual(missing_tails, [str(tail)])
            # src-release 是合法 root，不应误报 MISPLACED
            self.assertEqual(result["misplaced"], [])
            self.assertEqual(result["extra"], [])


class TestStrictShouldFail(unittest.TestCase):
    """strict 模式只卡 MISSING/MISPLACED/EXTRA，不卡 MODIFIED（见 ADR 0004）。"""

    def _src(self, **kw):
        base = {"missing": [], "misplaced": [], "extra": [], "modified": []}
        base.update(kw)
        return base

    def _res(self, **kw):
        base = {"missing": [], "extra": [], "modified": []}
        base.update(kw)
        return base

    def test_all_clean_passes(self):
        self.assertFalse(csa.strict_should_fail(self._src(), [], self._res()))

    def test_modified_does_not_fail_strict(self):
        # MODIFIED>0 不应触发 strict 失败（CONV 标记的授权改动也会改字节）
        src = self._src(modified=[("m", "sr", "t.kt", None, None)])
        res = self._res(modified=[("res", "p", "t.xml")])
        self.assertFalse(csa.strict_should_fail(src, [], res))

    def test_missing_fails_strict(self):
        self.assertTrue(csa.strict_should_fail(
            self._src(missing=[("sub", "m", "sr", "t.kt", "n")]), [], self._res()))

    def test_misplaced_fails_strict(self):
        self.assertTrue(csa.strict_should_fail(
            self._src(misplaced=[("m", "sr", "t.kt", None, "em", "esr", "as")]), [], self._res()))

    def test_extra_fails_strict(self):
        self.assertTrue(csa.strict_should_fail(
            self._src(extra=[("m", "sr", "t.kt", None)]), [], self._res()))

    def test_res_missing_fails_strict(self):
        self.assertTrue(csa.strict_should_fail(
            self._src(), [], self._res(missing=[("res", "p", "t.xml")])))

    def test_res_extra_fails_strict(self):
        self.assertTrue(csa.strict_should_fail(
            self._src(), [], self._res(extra=[("res", "p", "t.xml")])))

    def test_app_issues_fail_strict(self):
        self.assertTrue(csa.strict_should_fail(
            self._src(), [("APP-MISSING", "f", "p", "msg")], self._res()))


if __name__ == "__main__":
    unittest.main()
