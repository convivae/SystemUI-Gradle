#!/usr/bin/env python3
"""从 AOSP 1:1 复制所有 extras-file-mapping.csv 里 AOSP_bp_dir 对应的源文件。

逻辑：
  - 读 CSV
  - 对每行（非 SystemUI-core），找到 AOSP 物理路径
  - 复制到对应 gradle 子模块
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")
CSV_PATH = GRADLE_ROOT / "docs" / "extras-file-mapping.csv"


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open()))
    copied = 0
    skipped = 0
    for r in rows:
        target = r["gradle_target"]
        if target == "SystemUI-SystemUI-core":
            target = "SystemUI-core"
        # 跳过 SystemUI-core（应留原位的，不动）
        if target == "SystemUI-core":
            continue
        # 修正目标名
        if target.startswith("SystemUI-SystemUI-"):
            target = "SystemUI-" + target[len("SystemUI-SystemUI-"):]

        aosp_full = r["aosp_full_path"]
        bp_dir = r["aosp_bp_dir"]

        # 计算源文件 AOSP 物理路径
        # bp_dir 是 AOSP ROOT 相对子目录；aosp_full 是 AOSP ROOT 相对文件路径
        aosp_src = AOSP_ROOT / aosp_full
        if not aosp_src.exists():
            print(f"  missing AOSP src: {aosp_src}", file=sys.stderr)
            skipped += 1
            continue

        # 目标 gradle 子模块路径：直接用 relpath 作为包路径
        # （relpath 已经是 extras 文件的路径，反映了真实包结构）
        gradle_target = GRADLE_ROOT / target / "src" / "main" / "java" / r["relpath"]
        if gradle_target.exists():
            skipped += 1
            continue
        gradle_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(aosp_src, gradle_target)
        copied += 1

    print(f"复制 {copied} 个文件，跳过 {skipped} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())