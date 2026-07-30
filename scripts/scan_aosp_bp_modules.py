#!/usr/bin/env python3
"""扫描 AOSP frameworks/base/packages/SystemUI 所有 java_library 模块。

输出：name, srcs, plugins(AIDL), proto, libs
按 bp name 排序，便于人工映射 Gradle 子模块名。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")


def main() -> int:
    if not AOSP_ROOT.exists():
        print(f"fatal: AOSP root not found: {AOSP_ROOT}")
        return 1

    # 找所有 .bp 文件
    bp_files = sorted(AOSP_ROOT.rglob("Android.bp"))
    print(f"Scanning {len(bp_files)} Android.bp files under {AOSP_ROOT}")
    print()

    # 每个 java_library 的属性
    module_re = re.compile(
        r"^\s*(?P<type>java_library|java_library_static|android_library)\s*\{",
        re.MULTILINE,
    )
    name_re = re.compile(r'^\s*name:\s*"([^"]+)"', re.MULTILINE)
    srcs_re = re.compile(r"srcs:\s*\[([^\]]*)\]", re.DOTALL)
    srcs_item_re = re.compile(r'"([^"]+)"')

    results = []
    for bp in bp_files:
        text = bp.read_text()
        # 抓所有 java_library / android_library 块
        # 简单状态机：找到 { 后扫描到匹配 }
        idx = 0
        while True:
            m = module_re.search(text, idx)
            if not m:
                break
            # 找匹配的 }
            start = m.end()
            depth = 1
            i = start
            while i < len(text) and depth > 0:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            body = text[start : i - 1]
            idx = i

            nm = name_re.search(body)
            if not nm:
                continue
            name = nm.group(1)

            srcs_match = srcs_re.search(body)
            srcs: list[str] = []
            if srcs_match:
                srcs = srcs_item_re.findall(srcs_match.group(1))

            results.append(
                {
                    "bp": str(bp.relative_to(AOSP_ROOT)),
                    "type": m.group("type"),
                    "name": name,
                    "srcs": srcs,
                }
            )

    # 按 name 排序
    results.sort(key=lambda r: r["name"])

    # 筛 java_library
    java_libs = [r for r in results if r["type"] in ("java_library", "java_library_static")]

    print(f"=== java_library / java_library_static ({len(java_libs)} 个) ===")
    for r in java_libs:
        print(f"\n{r['name']}  ({r['bp']})")
        for s in r["srcs"][:5]:
            print(f"    srcs: {s}")
        if len(r["srcs"]) > 5:
            print(f"    ... +{len(r['srcs']) - 5} more")

    print()
    print("=== Summary ===")
    print(f"  java_library total: {len(java_libs)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
