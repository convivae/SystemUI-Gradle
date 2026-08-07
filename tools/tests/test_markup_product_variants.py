#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/markup_product_variants.py."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "markup_product_variants.py"
_spec = importlib.util.spec_from_file_location("markup_product_variants", _SCRIPT)
mpv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mpv)


class TestTransformContent(unittest.TestCase):
    def test_tv_variant_is_marked(self):
        content = (
            '<resources>\n'
            '    <string name="x" product="tv">TV text</string>\n'
            '    <string name="x" product="default">Default text</string>\n'
            '</resources>\n'
        )
        out, n = mpv.transform_content(content)
        self.assertEqual(n, 1)
        self.assertIn('<!-- CONV_DEL BEGIN:', out)
        self.assertIn('<!-- <string name="x" product="tv">TV text</string> -->', out)
        self.assertIn('<!-- CONV_DEL END -->', out)
        # default 变体必须保留为有效标签
        self.assertIn('<string name="x" product="default">Default text</string>', out)

    def test_tablet_and_device_marked(self):
        content = (
            '<resources>\n'
            '    <string name="x" product="default">D</string>\n'
            '    <string name="x" product="tablet">T</string>\n'
            '    <string name="x" product="device">V</string>\n'
            '</resources>\n'
        )
        out, n = mpv.transform_content(content)
        self.assertEqual(n, 2)
        self.assertNotIn('<string name="x" product="tablet">T</string>\n', out)
        self.assertNotIn('<string name="x" product="device">V</string>\n', out)
        self.assertIn('<string name="x" product="default">D</string>', out)

    def test_default_not_marked(self):
        content = '<resources>\n    <string name="x" product="default">D</string>\n</resources>\n'
        out, n = mpv.transform_content(content)
        self.assertEqual(n, 0)
        self.assertEqual(out, content)

    def test_idempotent(self):
        """已标记的文件再跑一次不应再改。"""
        content = (
            '<resources>\n'
            '    <string name="x" product="tv">TV</string>\n'
            '</resources>\n'
        )
        once, n1 = mpv.transform_content(content)
        twice, n2 = mpv.transform_content(once)
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 0)
        self.assertEqual(once, twice)

    def test_preserves_surrounding_comments(self):
        """AOSP 的描述性注释（非 product 变体）应保留。"""
        content = (
            '<resources>\n'
            '    <!-- Message for TV -->\n'
            '    <string name="x" product="tv">TV</string>\n'
            '    <!-- Message for default -->\n'
            '    <string name="x" product="default">D</string>\n'
            '</resources>\n'
        )
        out, n = mpv.transform_content(content)
        self.assertEqual(n, 1)
        self.assertIn('<!-- Message for TV -->', out)
        self.assertIn('<!-- Message for default -->', out)

    def test_multiline_string_with_xliff_is_marked(self):
        """多行 string（含 <xliff:g> 子元素）应整块注释。"""
        content = (
            '<resources>\n'
            '    <string name="x" product="tablet">\n'
            '       You have <xliff:g id="number">%1$d</xliff:g> times.\n'
            '       This tablet will be reset.\n'
            '    </string>\n'
            '    <string name="x" product="default">D</string>\n'
            '</resources>\n'
        )
        out, n = mpv.transform_content(content)
        self.assertEqual(n, 1)
        self.assertIn('<!-- CONV_DEL BEGIN:', out)
        self.assertIn('<!-- CONV_DEL END -->', out)
        # default 变体保留
        self.assertIn('<string name="x" product="default">D</string>', out)
        # 多行内容被整块注释：原 <string 开始行被 <!-- 包裹
        # （原行以 "<!-- <string name=..." 形式保留，是注释）
        self.assertIn('<!-- <string name="x" product="tablet">', out)
        # 不应存在未注释的有效 <string product="tablet"> 标签
        import re
        # 有效标签 = 行首是 <string（不是 <!-- <string）
        effective_tablet = re.compile(r'^[ \t]*<string[^>]*product="tablet"', re.MULTILINE)
        self.assertEqual(effective_tablet.findall(out), [])


class TestProcessRoot(unittest.TestCase):
    def test_process_multiple_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "values").mkdir()
            (root / "values" / "strings.xml").write_text(
                '<resources>\n    <string name="x" product="tv">TV</string>\n'
                '    <string name="x" product="default">D</string>\n</resources>\n',
                encoding="utf-8")
            (root / "values-zh-rCN").mkdir()
            (root / "values-zh-rCN" / "strings.xml").write_text(
                '<resources>\n    <string name="x" product="tablet">平板</string>\n'
                '    <string name="x" product="default">默认</string>\n</resources>\n',
                encoding="utf-8")
            # 文件无 product 变体
            (root / "values" / "colors.xml").write_text(
                '<resources>\n    <color name="c">#FF0000</color>\n</resources>\n',
                encoding="utf-8")

            total_files, total_changed, details = mpv.process_root(root)

            self.assertEqual(total_files, 2)
            self.assertEqual(total_changed, 2)
            rels = {r for r, _ in details}
            self.assertIn("values/strings.xml", rels)
            self.assertIn("values-zh-rCN/strings.xml", rels)

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "values").mkdir(parents=True)
            f = root / "values" / "strings.xml"
            original = '<resources>\n    <string name="x" product="tv">TV</string>\n</resources>\n'
            f.write_text(original, encoding="utf-8")

            mpv.process_root(root, dry_run=True)

            self.assertEqual(f.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
