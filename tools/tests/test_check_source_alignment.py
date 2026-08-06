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


if __name__ == "__main__":
    unittest.main()
