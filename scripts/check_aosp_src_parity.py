#!/usr/bin/env python3
"""AOSP src 1:1 对齐扫描。

用法：python3 scripts/check_aosp_src_parity.py [--aosp-root <path>]

按规则 S：SystemUI-Gradle 的 src/ src-debug/ src-release/ 必须与 AOSP
frameworks/base/packages/SystemUI/ 严格 1:1。

报告：
  - 每个 source set 缺/多/重名
  - 跨 source set 误放（同文件既在 src 也在 src-debug）
  - res/ 资源目录文件数对比

"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

GRADLE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")
CORE_DIR = GRADLE_ROOT / "SystemUI-core"

SOURCE_EXTS = {".kt", ".java", ".aidl", ".proto"}
SOURCE_SUBDIRS = ("src", "src-debug", "src-release")
RESOURCE_SUBDIRS = ("res", "res-keyguard", "res-product")


@dataclass
class SubsetReport:
    name: str
    aosp: set[str]
    ours: set[str]

    def extras(self) -> set[str]:
        return self.ours - self.aosp

    def missing(self) -> set[str]:
        return self.aosp - self.ours


def collect(root: Path, sub: str) -> set[str]:
    """Collect relative paths of source files under root/<sub>/."""
    base = root / sub
    if not base.exists():
        return set()
    out: set[str] = set()
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in SOURCE_EXTS:
            rel = p.relative_to(base).as_posix()
            out.add(rel)
    return out


def collect_res(root: Path, sub: str) -> int:
    base = root / sub
    if not base.exists():
        return 0
    return sum(1 for _ in base.rglob("*") if _.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aosp-root",
        type=Path,
        default=DEFAULT_AOSP_ROOT,
        help="AOSP SystemUI 根目录路径",
    )
    args = parser.parse_args()

    aosp_root: Path = args.aosp_root
    if not aosp_root.is_dir():
        print(f"fatal: AOSP root not found: {aosp_root}", file=sys.stderr)
        return 1

    print("=" * 80)
    print("AOSP src 1:1 alignment check")
    print(f"  GRADLE: {GRADLE_ROOT}")
    print(f"  AOSP:   {aosp_root}")
    print(f"  CORE:   {CORE_DIR}")
    print("=" * 80)

    reports: dict[str, SubsetReport] = {}
    for sub in SOURCE_SUBDIRS:
        reports[sub] = SubsetReport(
            name=sub,
            aosp=collect(aosp_root, sub),
            ours=collect(CORE_DIR, sub),
        )

    # 报告每个 source set
    for sub, r in reports.items():
        print()
        print(f"### {sub}/ ###")
        print(f"  AOSP files: {len(r.aosp)}")
        print(f"  OURS files: {len(r.ours)}")

        missing = r.missing()
        extras = r.extras()
        print(f"  缺少 (AOSP has, we don't): {len(missing)}")
        for f in sorted(missing)[:50]:
            print(f"    - {f}")
        if len(missing) > 50:
            print(f"    ... and {len(missing) - 50} more")

        print(f"  多出 (ours has, AOSP doesn't): {len(extras)}")
        for f in sorted(extras)[:50]:
            print(f"    + {f}")
        if len(extras) > 50:
            print(f"    ... and {len(extras) - 50} more")

    # 跨 source set 误放
    print()
    print("=" * 80)
    print("Cross source-set overlap (same file in multiple source sets)")
    print("=" * 80)
    overlaps_found = False
    for i, sub1 in enumerate(SOURCE_SUBDIRS):
        for sub2 in SOURCE_SUBDIRS[i + 1 :]:
            inter = reports[sub1].ours & reports[sub2].ours
            if inter:
                overlaps_found = True
                print(
                    f"\n  *** Overlap: {sub1}/ <-> {sub2}/ ({len(inter)} files) ***"
                )
                for f in sorted(inter):
                    print(f"    {f}")
    if not overlaps_found:
        print("  (none)")

    # 资源目录
    print()
    print("=" * 80)
    print("Resource layout parity (res/ vs AOSP res/)")
    print("=" * 80)
    for sub in RESOURCE_SUBDIRS:
        a_n = collect_res(aosp_root, sub)
        o_n = collect_res(CORE_DIR, sub)
        print(f"  {sub:14s} AOSP {a_n:5d} files / ours {o_n:5d} files")

    # 汇总
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    total_missing = sum(len(r.missing()) for r in reports.values())
    total_extras = sum(len(r.extras()) for r in reports.values())
    print(f"  total missing: {total_missing}")
    print(f"  total extras:  {total_extras}")
    print(f"  overlaps:      {'yes' if overlaps_found else 'no'}")

    # 仅缺文件无退出码要求；返回 0 以便 CI 跑
    return 0


if __name__ == "__main__":
    sys.exit(main())
