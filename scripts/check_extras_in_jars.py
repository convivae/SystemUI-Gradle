#!/usr/bin/env python3
"""检查 extras-file-mapping.csv 里哪些文件其实在 libs/*.jar 已存在（应删除伪源码）。"""
from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
LIBS = GRADLE_ROOT / "libs"
CSV_PATH = GRADLE_ROOT / "docs" / "extras-file-mapping.csv"


def jar_index() -> dict[str, list[str]]:
    """Build full class path → jar mapping for all jars in libs/."""
    idx: dict[str, list[str]] = {}
    for jar in sorted(LIBS.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar) as zf:
                for name in zf.namelist():
                    if name.endswith("/"):
                        continue
                    # name is like "com/android/server/display/feature/flags/Flags.class"
                    # 把 .class 视为 .kt 同名同包
                    if name.endswith(".class"):
                        # 仅记 class path
                        idx[name] = idx.get(name, []) + [str(jar.name)]
                        # 也记去掉 .class 后缀（对应 .java/.kt 同名）
                        no_ext = name[:-6]  # remove ".class"
                        idx[no_ext] = idx.get(no_ext, []) + [str(jar.name)]
        except Exception:
            pass
    return idx


def main() -> int:
    idx = jar_index()
    print(f"libs/ jar 中文件名索引: {sum(len(v) for v in idx.values())} 条\n")

    rows = list(csv.DictReader(CSV_PATH.open()))
    prebuilt = []
    for r in rows:
        rel = r["relpath"]
        # relpath 是 "com/android/.../X.kt" 形式
        # jar 索引 key 是 "com/android/.../X"（不带 .class）或 "X.class"
        matches = idx.get(rel[:-3], []) + idx.get(rel, [])
        if matches:
            prebuilt.append((r, matches))

    print(f"=== extras 中 {len(prebuilt)} 个文件 libs/*.jar 已有同名 class ===")
    for r, matches in prebuilt:
        print(f"  {r['relpath']}")
        for m in matches[:2]:
            print(f"    in: {m}")

    return 0


if __name__ == "__main__":
    sys.exit(main())