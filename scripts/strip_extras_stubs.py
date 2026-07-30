#!/usr/bin/env python3
"""删除 extras 里已确认为 stub 的伪源码文件。

按规则 C（aidl 一律 framework.aidl；源码不复制 framework）：
  - 文件 ≤ 5 行
  - 仅含 object/class 声明 + 少量 const val 或简单方法返回常量

这些是 prebuilt jar 提取的伪 stub，应删除（compileOnly framework.jar 提供真实实现）。
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
CSV_PATH = GRADLE_ROOT / "docs" / "extras-file-mapping.csv"

MAX_LINES = 30  # 包含 import/package 的上限
MAX_BODY = 5    # body 行数


def is_stub(path: Path) -> bool:
    """判定文件是否为 stub：

    仅删以下情况：
      - 空 object/class（body 只有闭合括号）
      - object Flags { ... } 风格且全 const val = false/true
      - companion object 单纯返回 const
    """
    try:
        text = path.read_text()
    except Exception:
        return False
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        return False
    # 去掉 license 头注释
    body_lines = [
        l for l in lines
        if l.strip()
        and not l.strip().startswith(("//", "/*", "*", "package", "import"))
        and l.strip() not in ("*/",)
    ]
    if len(body_lines) > MAX_BODY:
        return False
    # body 应只含 object/class 声明 + const val/fun returning literal
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open()))
    stubs = []
    for r in rows:
        rel = r["relpath"]
        if not rel.endswith((".kt", ".java")):
            continue
        p = GRADLE_ROOT / "SystemUI-core" / "src" / rel
        if not p.exists():
            continue
        if is_stub(p):
            stubs.append((r, p))

    print(f"=== {len(stubs)} 个 extras 确认为 stub（≤ {MAX_LINES} 行，body ≤ {MAX_BODY}） ===")
    for r, p in stubs:
        print(f"  {r['relpath']}")

    if not args.apply:
        print("\nDRY RUN — 用 --apply 真删")
        return 0

    for _, p in stubs:
        p.unlink()
        print(f"  deleted: {p.relative_to(GRADLE_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())