#!/usr/bin/env python3
"""回滚 move_extras_to_modules.py --apply 的所有移动。

逻辑：扫描 docs/extras-file-mapping.csv，对每个非 SystemUI-core 行：
  - 如果目标文件存在，把它移回 SystemUI-core/src/<relpath>
  - 如果目标目录是脚手架之外的（错位目录），删除整个目录

完成后状态与 --apply 前一致。
"""
from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
CSV_PATH = GRADLE_ROOT / "docs" / "extras-file-mapping.csv"

# 脚手架目录（合法目标）
SCAFFOLD_DIRS = {
    "SystemUI-utils-kairos",
    "SystemUI-compose-core",
    "SystemUI-compose-scene",
    "SystemUI-shared-biometrics",
    "SystemUI-shared-keyguard",
    "SystemUI-pods-dagger",
    "SystemUI-pods-retail-impl",
    "SystemUI-pods-retail-data-api",
    "SystemUI-pods-retail-data-impl",
    "SystemUI-pods-retail-domain-api",
    "SystemUI-pods-retail-domain-impl",
    "SystemUI-pods-util-settings",
}


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open()))
    rows = [r for r in rows if r["gradle_target"] != "SystemUI-SystemUI-core"]

    # 标准化
    for r in rows:
        gt = r["gradle_target"]
        if gt.startswith("SystemUI-SystemUI-"):
            r["gradle_target"] = "SystemUI-" + gt[len("SystemUI-SystemUI-"):]

    moved_back = 0
    for r in rows:
        target = r["gradle_target"]
        rel = r["relpath"]
        aosp_full = r["aosp_full_path"]
        # 在错位目录里找（-kairos、-PlatformComposeCore 等旧命名）
        # 简化：根据 aosp_full 路径特征找实际位置
        # 当前错位目录有：SystemUI-<x>-<y>/
        # 实际目录可能包含 aosp_full 的所有段

        # 错位目录特征：包含 AOSP 完整路径
        # 例：目标应是 SystemUI-utils-kairos/src/main/<aosp_full>
        # 但脚本旧版写到 SystemUI-utils-kairos-kairos/src/main/<aosp_full>
        # 找到正确的"非脚手架"目录里实际路径

        # 简化：扫所有 SystemUI-* 目录找文件
        candidates = []
        for d in GRADLE_ROOT.glob("SystemUI-*"):
            if not d.is_dir():
                continue
            for p in d.rglob(rel.split("/")[-1]):
                if p.is_file() and p.name == Path(rel).name:
                    candidates.append(p)

        if not candidates:
            continue

        # 取最近的（按文件名匹配 + 路径含 relpath 段数最多）
        def score(p: Path) -> int:
            score = 0
            parts = p.as_posix().split("/")
            rel_parts = rel.split("/")
            for rp in rel_parts:
                if rp in parts:
                    score += 1
            return -score

        candidates.sort(key=score)
        best = candidates[0]

        # 移回 SystemUI-core
        target_path = GRADLE_ROOT / "SystemUI-core" / "src" / rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            target_path.unlink()
        shutil.move(str(best), str(target_path))
        moved_back += 1

    print(f"已移回 {moved_back} 个文件")

    # 删除错位空目录
    removed = 0
    for d in sorted(GRADLE_ROOT.glob("SystemUI-*")):
        if not d.is_dir():
            continue
        name = d.name
        if name in SCAFFOLD_DIRS:
            continue
        # 是错位目录吗？看是否含 src/main/... 文件
        if (d / "src" / "main").exists():
            try:
                shutil.rmtree(d)
                print(f"  removed wrong-position dir: {name}")
                removed += 1
            except Exception as e:
                print(f"  failed to remove {name}: {e}")

    print(f"已删除 {removed} 个错位目录")
    return 0


if __name__ == "__main__":
    sys.exit(main())