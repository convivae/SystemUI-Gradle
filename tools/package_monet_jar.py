#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包干净的 monet runtime JAR（Task 033，用户批准的 REDLINE 方案 A）。

背景：旧 libs/monet.jar 为 turbine-combined FAT 产物（83 类 = monet 9 + libmonet 47
+ errorprone 27）。翻转为 implementation 后，其内嵌的 27 个
com.google.errorprone.annotations.** 类与官方 Maven error_prone_annotations:2.50.0
（guava/material/SystemUI-common 传递）产生 27 条 D8 duplicate class 硬错误。

方案（用户 2026-08-20 批准）：仅合并两个 owning Soong javac 产物——
  monet    9 类  out/soong/.intermediates/frameworks/libs/systemui/monet/monet/
                 android_common/javac/monet.jar
  libmonet 47 类 out/soong/.intermediates/external/libmonet/libmonet/
                 android_common/javac/libmonet.jar
errorprone 继续由官方 Maven 供给（不 exclusion）。产物为 56 类确定性 tier② JAR。

防污染纪律：任何输入中出现批准 namespace 之外的 .class（含 errorprone）即拒绝，
确保 turbine-combined 污染永远进不了产物。
"""

import argparse
import sys
import zipfile
from pathlib import Path

from aosp_paths import aosp_root

# Single AOSP root source (user rule 2026-08-25): tools/aosp_paths.py resolves
# the default, the AOSP_ROOT env override, and any explicit --aosp-root value.
AOSP_ROOT = aosp_root()
MONET_INPUT = (
    "out/soong/.intermediates/frameworks/libs/systemui/monet/monet/"
    "android_common/javac/monet.jar"
)
LIBMONET_INPUT = (
    "out/soong/.intermediates/external/libmonet/libmonet/"
    "android_common/javac/libmonet.jar"
)
OUTPUT_JAR = Path("libs/monet.jar")

APPROVED_PREFIXES = (
    "com/android/systemui/monet/",
    "com/google/ux/material/libmonet/",
)

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class MonetJarError(Exception):
    """输入不合规（缺失/为空/重复类/非预期 namespace）时抛出。"""


def _zip_info(name: str) -> zipfile.ZipInfo:
    """固定 timestamp/metadata 的 ZipInfo，保证重复打包字节一致。"""
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _read_classes(jar: Path, label: str) -> dict:
    """读取输入 JAR 中批准 namespace 下的全部 .class 条目；拒绝污染。"""
    if not jar.is_file():
        raise MonetJarError(f"{label} input missing: {jar}")
    classes: dict = {}
    with zipfile.ZipFile(jar) as z:
        for info in z.infolist():
            name = info.filename
            if not name.endswith(".class"):
                continue  # 跳过 MANIFEST、目录 entry 等
            if not name.startswith(APPROVED_PREFIXES):
                raise MonetJarError(
                    f"{label} input {jar.name} contains unexpected class "
                    f"outside approved namespaces: {name}"
                )
            if name in classes:
                raise MonetJarError(
                    f"{label} input {jar.name} contains duplicate class entry: {name}"
                )
            classes[name] = z.read(name)
    if not classes:
        raise MonetJarError(f"{label} input has no approved classes: {jar}")
    return classes


def package_monet_jar(monet_input: Path, libmonet_input: Path, output: Path):
    """合并两个 Soong javac 产物为确定性干净 JAR。

    Returns: (monet_emitted, libmonet_emitted) 各输入贡献的 class 数。
    """
    merged: dict = {}
    counts = []
    for jar, label in ((monet_input, "monet"), (libmonet_input, "libmonet")):
        classes = _read_classes(Path(jar), label)
        for name in classes:
            if name in merged:
                raise MonetJarError(f"duplicate class across inputs: {name}")
        merged.update(classes)
        counts.append(len(classes))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(merged):
            z.writestr(_zip_info(name), merged[name])
    return counts[0], counts[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp-root", type=Path, default=AOSP_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT_JAR)
    args = parser.parse_args()

    monet_input = args.aosp_root / MONET_INPUT
    libmonet_input = args.aosp_root / LIBMONET_INPUT
    try:
        n_monet, n_libmonet = package_monet_jar(monet_input, libmonet_input, args.output)
    except MonetJarError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(
        f"{args.output} ({args.output.stat().st_size} bytes): "
        f"monet={n_monet} libmonet={n_libmonet} total={n_monet + n_libmonet}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
