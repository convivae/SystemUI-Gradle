#!/usr/bin/env python3
"""细化 src/ 多出 com/android/systemui/ 子目录分类。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_aosp_src_parity import collect, CORE_DIR, DEFAULT_AOSP_ROOT  # type: ignore

aosp = collect(DEFAULT_AOSP_ROOT, "src")
ours = collect(CORE_DIR, "src")
extras = sorted(ours - aosp)

# 仅看 com/android/systemui/...
sysui_extras = [f for f in extras if f.startswith("com/android/systemui/")]
print(f"src/ 多出 com/android/systemui/... 共 {len(sysui_extras)} 个")
print()

# 按前 4 段（包名到 4 层）
prefix_4 = Counter()
for f in sysui_extras:
    parts = f.split("/")
    key = "/".join(parts[:4])
    prefix_4[key] += 1

print("--- 按 4 段路径（包到 4 层）---")
for k, v in sorted(prefix_4.items(), key=lambda x: -x[1]):
    if v >= 1:
        print(f"  {k:80s} {v}")

# 列出每组下的具体文件
print()
print("--- 各组下文件列表（每组最多 3 个 sample）---")
groups = {}
for f in sysui_extras:
    parts = f.split("/")
    key = "/".join(parts[:4])
    groups.setdefault(key, []).append(f)
for k in sorted(groups.keys()):
    print(f"\n  {k} ({len(groups[k])} files):")
    for f in groups[k][:3]:
        print(f"    {f}")
    if len(groups[k]) > 3:
        print(f"    ... and {len(groups[k]) - 3} more")
