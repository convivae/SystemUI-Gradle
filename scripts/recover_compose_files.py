#!/usr/bin/env python3
"""从 AOSP 1:1 复制被 rm -rf 误删的文件回 SystemUI-Gradle/。

只针对 git status 显示 D 的文件，按 AOSP bp_path 重新映射：
  SystemUI-compose-core ← AOSP compose/core/src
  SystemUI-compose-scene ← AOSP compose/scene/src
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")

# relpath prefix → (子模块, AOSP 子目录)
MAP = {
    "com/android/compose/": ("SystemUI-compose-core", "compose/core/src"),
    "com/android/compose/animation/scene/": ("SystemUI-compose-scene", "compose/scene/src"),
}


def main() -> int:
    moved = 0
    for prefix, (sub, aosp_sub) in MAP.items():
        src_dir = AOSP_ROOT / aosp_sub
        target_dir = GRADLE_ROOT / sub / "src" / "main" / "java"
        if not src_dir.exists():
            print(f"missing AOSP dir: {src_dir}")
            continue
        # 在 src_dir 下按 prefix 找文件
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            # 相对 src_dir 的 relpath，去掉 src/ 前缀，得到 gradle 子模块里的 java 路径
            rel_to_aosp_sub = p.relative_to(src_dir).as_posix()
            if rel_to_aosp_sub.startswith("src/"):
                rel_to_aosp_sub = rel_to_aosp_sub[len("src/"):]
            # 必须包含 prefix 段（不然不属于该子模块）
            if prefix not in rel_to_aosp_sub and rel_to_aosp_sub not in prefix.rstrip("/"):
                continue
            target = target_dir / rel_to_aosp_sub
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(p, target)
                moved += 1
    print(f"复制 {moved} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())