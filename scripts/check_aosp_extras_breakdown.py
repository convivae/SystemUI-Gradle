#!/usr/bin/env python3
"""细化多出文件，按顶层包名 + 路径模式分类。

用法：python3 scripts/check_aosp_extras_breakdown.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_aosp_src_parity import collect, SOURCE_SUBDIRS, CORE_DIR, DEFAULT_AOSP_ROOT  # type: ignore

aosp = collect(DEFAULT_AOSP_ROOT, "src")
ours = collect(CORE_DIR, "src")
extras = sorted(ours - aosp)

print(f"src/ 多出 {len(extras)} 个文件")
print()

# 按顶层包 + 路径前缀分组
top_pkg = Counter()
sub_dirs = Counter()
for f in extras:
    parts = f.split("/")
    # 顶层包
    if len(parts) >= 2:
        top_pkg[parts[0]] += 1
    # 深层路径（>3 段）
    if len(parts) >= 4:
        sub_dirs["/".join(parts[:3])] += 1

print("--- 多出文件按顶层包统计 ---")
for pkg, n in top_pkg.most_common():
    print(f"  {pkg:20s} {n}")

print()
print("--- 多出文件按前 3 段路径统计（>5 的显示） ---")
for k, v in sorted(sub_dirs.items(), key=lambda x: -x[1]):
    if v >= 2:
        print(f"  {k:60s} {v}")

# 多出里 com/android/compose/ 是不是就一个独立模块？
com_comp = [f for f in extras if f.startswith("com/android/compose/")]
print()
print(f"--- com/android/compose/ 多出 {len(com_comp)} 个文件 ---")
if com_comp:
    # 进一步按子目录
    sub = Counter()
    for f in com_comp:
        parts = f.split("/")
        if len(parts) >= 4:
            sub["/".join(parts[:3])] += 1
        else:
            sub["/".join(parts[:2])] += 1
    for k, v in sub.most_common():
        print(f"  {k:60s} {v}")
