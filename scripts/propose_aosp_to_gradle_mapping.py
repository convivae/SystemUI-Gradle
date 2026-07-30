#!/usr/bin/env python3
"""生成 AOSP bp 模块 → Gradle 子模块映射方案。

每个 AOSP bp 模块：
  - 列出其 srcs 的实际目录
  - 与我们 SystemUI-core/src/ 实际路径对齐
  - 推断目标 Gradle 子模块名（按 AOSP 路径 1:1）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")
CORE_DIR = Path("/home/conv/myspace/SystemUI-Gradle/SystemUI-core")


def parse_bp(path: Path) -> list[dict]:
    text = path.read_text()
    out = []
    for m in re.finditer(
        r'(java_library|java_library_static|android_library)\s*\{([^}]*)\}',
        text, re.DOTALL,
    ):
        body = m.group(2)
        n = re.search(r'name:\s*"([^"]+)"', body)
        if not n:
            continue
        name = n.group(1)
        srcs_match = re.search(r'srcs:\s*\[([^\]]*)\]', body, re.DOTALL)
        srcs = []
        if srcs_match:
            srcs = re.findall(r'"([^"]+)"', srcs_match.group(1))
        out.append({
            "type": m.group(1),
            "name": name,
            "srcs": srcs,
            "bp": str(path.relative_to(AOSP_ROOT)),
        })
    return out


def srcs_dirs(srcs: list[str]) -> list[str]:
    """从 srcs glob 提取实际目录前缀（去除 **/* 通配）"""
    dirs = set()
    for s in srcs:
        # 跳过模块引用 (:xxx) 和非目录 glob
        if s.startswith(":") or "*" not in s:
            continue
        # 提取到第一个 */
        d = s.split("**")[0].rstrip("/")
        if d:
            dirs.add(d)
    return sorted(dirs)


def main() -> int:
    all_modules: list[dict] = []
    for bp in sorted(AOSP_ROOT.rglob("Android.bp")):
        all_modules.extend(parse_bp(bp))
    all_modules.sort(key=lambda m: m["name"])

    # AOSP path → 推断 Gradle module 名
    # AOSP 路径: frameworks/base/packages/SystemUI/<subpath>
    # 例: animation/lib → SystemUI-animation-lib
    # 例: compose/scene → SystemUI-compose-scene

    # 输出 Markdown 报告
    print("# AOSP bp 模块 → Gradle 子模块映射")
    print()
    print(f"总模块数: {len(all_modules)}")
    print()
    print("| # | bp 模块名 | 类型 | bp 路径 | srcs 目录（推断） | Gradle 子模块候选 |")
    print("|---|---------|------|--------|-----------------|------------------|")

    for i, m in enumerate(all_modules, 1):
        bp_path = m["bp"].rsplit("/", 1)[0]  # e.g. "animation/lib"
        dirs = srcs_dirs(m["srcs"])
        # 推断 gradle name
        # 顶层 . (Android.bp) → SystemUI-<name>
        # animation/lib → SystemUI-animation-lib
        # pods/com/android/systemui/dagger → SystemUI-dagger 之类
        gradle_name: str
        if bp_path in (".", ""):
            gradle_name = f"SystemUI-{m['name']}"
        else:
            suffix = bp_path.replace("/", "-")
            gradle_name = f"SystemUI-{suffix}"
        # 个别修正：带横线的名字加 - 收尾
        gradle_name = gradle_name.replace("--", "-")
        # 处理特殊: PlatformCompose* 等
        if m["name"].startswith("Platform"):
            # 例如 PlatformComposeSceneTransitionLayout → 来自 compose/scene
            # 已经按路径推断
            pass

        print(f"| {i} | `{m['name']}` | {m['type']} | `{m['bp']}` | {', '.join(dirs[:3])}{'...' if len(dirs) > 3 else ''} | `{gradle_name}` |")

    return 0


if __name__ == "__main__":
    sys.exit(main())
