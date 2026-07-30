#!/usr/bin/env python3
"""Phase B: 按 extras-file-mapping.csv 移动文件到目标子模块。

读 docs/extras-file-mapping.csv，对每行：
  relpath          src/main/ 内当前相对路径
  aosp_full_path   AOSP 完整路径（含 bp_path/）
  aosp_bp_dir      AOSP bp 路径
  aosp_module      AOSP bp module 名
  gradle_target    目标 Gradle 子模块名

逻辑：
  - 源文件：SystemUI-Gradle/SystemUI-core/src/<relpath>
  - 目标文件：SystemUI-Gradle/<gradle_target>/src/main/<aosp_full_path>
    其中 aosp_full_path 是 AOSP ROOT 相对路径（如 "compose/features/src/com/..."）
    应去掉 src/ 前缀（因为 gradle 子模块默认 src/main/java 已是源码根）

按 AOSP 1:1：目标子模块的源码目录结构应与 AOSP 完全一致（去除 src/main/ 前缀差异）

输出：dry-run 默认开启，确认后用 --apply 真做移动。
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
CSV_PATH = GRADLE_ROOT / "docs" / "extras-file-mapping.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="真的执行移动（默认 dry-run）")
    parser.add_argument("--only", help="仅处理指定 gradle_target 模块名")
    args = parser.parse_args()

    if not CSV_PATH.exists():
        print(f"fatal: CSV not found: {CSV_PATH}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(CSV_PATH.open()))
    print(f"读取 {len(rows)} 条映射", file=sys.stderr)

    # 把 gradle_target 标准化：去掉重复 SystemUI- 前缀
    for r in rows:
        gt = r["gradle_target"]
        if gt.startswith("SystemUI-SystemUI-"):
            r["gradle_target"] = "SystemUI-" + gt[len("SystemUI-SystemUI-"):]

    # 按 gradle_target 分组
    by_target: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_target[r["gradle_target"]].append(r)

    moves: list[tuple[Path, Path]] = []
    for target, items in by_target.items():
        if args.only and target != args.only:
            continue
        # 自身应留 SystemUI-core 的不动
        if target == "SystemUI-core":
            continue
        for r in items:
            src = GRADLE_ROOT / "SystemUI-core" / "src" / r["relpath"]
            # 直接用 relpath 作为目标子路径（保留 extras 原包路径）
            # extras relpath = "com/android/hardware/devicestate/feature/flags/Flags.kt"
            # → gradle 子模块里: src/main/java/<relpath>
            target_path = GRADLE_ROOT / target / "src" / "main" / "java" / r["relpath"]
            moves.append((src, target_path))

    # 排除 gradle_target = "SystemUI-SystemUI-core" 的 162 个文件
    # 这些文件 aosp_full_path 是 compose/features/src/ 或 compose/facade/enabled/src/
    # AOSP SystemUI-core 模块的 srcs glob 已包含这些路径（5 个 glob）
    # 它们本就是 SystemUI-core 自己的代码，物理位置无需改
    print(f"\n{'=' * 60}")
    print(f"共 {len(moves)} 个文件移动")
    actual_moves = [(s, t) for s, t in moves if "SystemUI-SystemUI-core" not in str(t)]
    skipped = len(moves) - len(actual_moves)
    print(f"  真要搬：{len(actual_moves)}")
    print(f"  跳过（AOSP SystemUI-core 自身代码，留原位）：{skipped}")

    by_target_count: dict[str, int] = defaultdict(int)
    for src, tgt in actual_moves:
        for p in tgt.parts:
            if p.startswith("SystemUI-"):
                by_target_count[p] += 1
                break

    print()
    for k in sorted(by_target_count, key=lambda x: -by_target_count[x]):
        print(f"  {k:50s} {by_target_count[k]}")

    # 检查源文件存在
    missing = [src for src, _ in actual_moves if not src.exists()]
    if missing:
        print(f"\n警告：{len(missing)} 个源文件不存在（已从 CSV 跳过）", file=sys.stderr)
        for m in missing[:5]:
            print(f"  missing: {m.relative_to(GRADLE_ROOT)}", file=sys.stderr)
        # 跳过这些
        actual_moves = [(s, t) for s, t in actual_moves if s.exists()]
        print(f"  实际可搬：{len(actual_moves)}", file=sys.stderr)

    # 检查目标是否已存在
    existing = [tgt for _, tgt in actual_moves if tgt.exists()]
    if existing:
        print(f"\n警告：{len(existing)} 个目标已存在（将被覆盖）", file=sys.stderr)

    if not args.apply:
        print("\nDRY RUN — 用 --apply 真做")
        print("\n前 10 个移动示例：")
        for src, tgt in actual_moves[:10]:
            print(f"  {src.relative_to(GRADLE_ROOT)}")
            print(f"    → {tgt.relative_to(GRADLE_ROOT)}")
        return 0

    moved = 0
    for src, tgt in actual_moves:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        if tgt.exists():
            tgt.unlink()
        shutil.move(str(src), str(tgt))
        moved += 1

    print(f"\n已移动 {moved} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())