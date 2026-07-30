#!/usr/bin/env python3
"""删除 extras 里 libs/*.jar 已含同包同名 class 的伪源码（按规则 C：源码不复制 framework）。

策略：检查每个 extras 文件，libs/*.jar 内是否有同包路径的 .class：
  - extras relpath = "com/android/X/Y.kt"  →  jar 里找 "com/android/X/Y.class"
  - extras relpath = "com/android/X/Y.java"  →  同上

输出将被删除的文件列表。
"""
from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
LIBS = GRADLE_ROOT / "libs"
CSV_PATH = GRADLE_ROOT / "docs" / "extras-file-mapping.csv"


def build_jar_index() -> dict[str, list[str]]:
    """class path (no .class ext) → jar names."""
    idx: dict[str, list[str]] = {}
    for jar in sorted(LIBS.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar) as zf:
                for name in zf.namelist():
                    if name.endswith(".class"):
                        no_ext = name[:-6]
                        idx.setdefault(no_ext, []).append(jar.name)
        except Exception:
            pass
    return idx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="真删除（默认 dry-run）")
    args = parser.parse_args()

    idx = build_jar_index()
    print(f"libs/ jar class 索引: {len(idx)} 条", file=sys.stderr)

    rows = list(csv.DictReader(CSV_PATH.open()))
    to_delete = []
    for r in rows:
        rel = r["relpath"]
        # 处理 .java 和 .kt
        if rel.endswith(".java"):
            no_ext = rel[:-5]
        elif rel.endswith(".kt"):
            no_ext = rel[:-3]
        else:
            continue
        if no_ext in idx:
            to_delete.append((r, idx[no_ext]))

    print(f"=== {len(to_delete)} 个伪源码（libs/ 已有同包 class） ===")
    for r, jars in to_delete:
        print(f"  {r['relpath']}  ←  {', '.join(sorted(set(jars)))}")

    if not args.apply:
        print("\nDRY RUN — 用 --apply 真删")
        return 0

    for r, _ in to_delete:
        p = GRADLE_ROOT / "SystemUI-core" / "src" / r["relpath"]
        if p.exists():
            p.unlink()
            print(f"  deleted: {p.relative_to(GRADLE_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())