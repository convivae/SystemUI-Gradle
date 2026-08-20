#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tools/package_monet_jar.py — clean deterministic monet artifact.

四个聚焦测试（brief 指定，不多不少）：
1. 仅合并两个批准 namespace 下的 .class 条目（过滤 MANIFEST/目录等非 class 条目）
2. 重复打包字节一致（确定性：排序 entry + 固定 timestamp/权限）
3. 拒绝重复 class 条目（跨输入同名类）
4. 拒绝非预期 namespace（含 com/google/errorprone/）
"""

import importlib.util
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "package_monet_jar.py"
_spec = importlib.util.spec_from_file_location("package_monet_jar", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


def _make_jar(path: Path, entries: dict) -> None:
    """构造合成输入 JAR（含目录 entry 与 MANIFEST，模拟 Soong javac 产物）。"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        dirs = set()
        for name in entries:
            parts = name.split("/")[:-1]
            for i in range(len(parts)):
                dirs.add("/".join(parts[: i + 1]) + "/")
        for d in sorted(dirs):
            z.writestr(zipfile.ZipInfo(d), b"")
        z.writestr(zipfile.ZipInfo("META-INF/MANIFEST.MF"), b"Manifest-Version: 1.0\n")
        for name, data in entries.items():
            z.writestr(name, data)


class TestPackageMonetJar(unittest.TestCase):
    def test_merges_only_expected_class_namespaces(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            monet_in = root / "monet.jar"
            libmonet_in = root / "libmonet.jar"
            out = root / "out.jar"
            _make_jar(monet_in, {
                "com/android/systemui/monet/ColorScheme.class": b"CS",
                "com/android/systemui/monet/Shades.class": b"SH",
            })
            _make_jar(libmonet_in, {
                "com/google/ux/material/libmonet/hct/Hct.class": b"HCT",
                "com/google/ux/material/libmonet/utils/MathUtils.class": b"MU",
            })
            n_monet, n_libmonet = module.package_monet_jar(monet_in, libmonet_in, out)
            self.assertEqual((n_monet, n_libmonet), (2, 2))
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
            # 只有四个 .class 条目：MANIFEST 与目录 entry 均不得进入产物
            self.assertEqual(sorted(names), [
                "com/android/systemui/monet/ColorScheme.class",
                "com/android/systemui/monet/Shades.class",
                "com/google/ux/material/libmonet/hct/Hct.class",
                "com/google/ux/material/libmonet/utils/MathUtils.class",
            ])
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.read("com/android/systemui/monet/ColorScheme.class"), b"CS")
                self.assertEqual(z.read("com/google/ux/material/libmonet/hct/Hct.class"), b"HCT")

    def test_output_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            monet_in = root / "monet.jar"
            libmonet_in = root / "libmonet.jar"
            _make_jar(monet_in, {
                "com/android/systemui/monet/Shades.class": b"SH",
                "com/android/systemui/monet/Style.class": b"ST",
            })
            _make_jar(libmonet_in, {
                "com/google/ux/material/libmonet/scheme/Scheme.class": b"SC",
            })
            first = root / "first.jar"
            second = root / "second.jar"
            module.package_monet_jar(monet_in, libmonet_in, first)
            time.sleep(2)
            module.package_monet_jar(monet_in, libmonet_in, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            # entry 字典序 + 固定 timestamp/权限（确定性来源，也是可观测契约）
            with zipfile.ZipFile(first) as z:
                infos = z.infolist()
            self.assertEqual([i.filename for i in infos], sorted(i.filename for i in infos))
            for info in infos:
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual((info.external_attr >> 16) & 0o777, 0o644)

    def test_rejects_duplicate_class_entries(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            monet_in = root / "monet.jar"
            libmonet_in = root / "libmonet.jar"
            out = root / "out.jar"
            _make_jar(monet_in, {
                "com/android/systemui/monet/Shades.class": b"SH",
            })
            # 两个输入都含同名 class → 合并将产生重复定义，必须拒绝
            _make_jar(libmonet_in, {
                "com/google/ux/material/libmonet/utils/MathUtils.class": b"MU",
                "com/android/systemui/monet/Shades.class": b"SH-DUP",
            })
            with self.assertRaises(module.MonetJarError):
                module.package_monet_jar(monet_in, libmonet_in, out)

    def test_rejects_unexpected_class_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            monet_in = root / "monet.jar"
            libmonet_in = root / "libmonet.jar"
            out = root / "out.jar"
            _make_jar(monet_in, {
                "com/android/systemui/monet/Shades.class": b"SH",
            })
            # 模拟被 turbine-combined 污染的输入：混入 errorprone 类，必须拒绝
            _make_jar(libmonet_in, {
                "com/google/ux/material/libmonet/utils/MathUtils.class": b"MU",
                "com/google/errorprone/annotations/CanIgnoreReturnValue.class": b"EP",
            })
            with self.assertRaises(module.MonetJarError):
                module.package_monet_jar(monet_in, libmonet_in, out)


if __name__ == "__main__":
    unittest.main()
