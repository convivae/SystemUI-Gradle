#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 libs/aars/*.aar 安装到 libs/maven/ 本地 Maven 仓，生成简单 POM 骨架。

模式参考 CarSystemUIGradle 项目：
  libs/maven/<group>/<name>/<version>/<name>-<version>.aar
  libs/maven/<group>/<name>/<version>/<name>-<version>.pom

POM 默认为骨架（只声明 groupId/artifactId/version/packaging=aar，无传递依赖，
由消费方显式声明）；例外（ADR 0005）：SettingsLib 闭包的 POM 携带机械镜像
Android.bp static_libs 的 <dependencies>（仅 SettingsLib 主 POM，当前 17 条边）。

本工具只做文件复制 + POM 生成，不修改 AAR 字节内容。
"""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "libs/aars"
DEFAULT_REPO_DIR = PROJECT_ROOT / "libs/maven"

# AAR 名 → Maven 坐标。
# 可选 "deps" 字段（ADR 0005，仅 SettingsLib 闭包）：POM 渲染 <dependencies>，
# 依赖边机械镜像 AOSP Android.bp static_libs；无 deps 的 artifact 保持骨架 POM。
#
# AOSP-17 (Task 071, AGENTS §3.2.4)：vintage 16→17 全族坐标 major 升 2.0.0，
# 旧 1.x 目录随 libs/ 全删消失；catalog 更新归 C4。
_SETTINGS_LIB_CLOSURE_DEPS = [
    "SettingsLibActionButtonsPreference",
    "SettingsLibAdaptiveIcon",
    "SettingsLibAppPreference",
    "SettingsLibBannerMessagePreference",
    "SettingsLibBarChartPreference",
    "SettingsLibButtonPreference",
    "SettingsLibFooterPreference",
    "SettingsLibIllustrationPreference",
    "SettingsLibLayoutPreference",
    "SettingsLibMainSwitchPreference",
    "SettingsLibProgressBar",
    "SettingsLibRestrictedLockUtils",
    "SettingsLibSelectorWithWidgetPreference",
    "SettingsLibSettingsSpinner",
    "SettingsLibSliderPreference",
    "SettingsLibTwoTargetPreference",
    "SettingsLibUsageProgressBarPreference",
]


def _settingslib_closure_dep_entries():
    """SettingsLib POM 的 17 条传递依赖边（Task 040 / ADR 0005）。

    机械镜像 AOSP 主 SettingsLib Android.bp static_libs 中全部 res-owning
    子 target，按 bp 声明顺序过滤后排列（7 条既有 + 10 条 Task 040 新增）。
    AOSP-17：随全族升 2.0.0。
    """
    return [
        {"group": "com.android.systemui", "name": n, "version": "2.0.0"}
        for n in _SETTINGS_LIB_CLOSURE_DEPS
    ]


ARTIFACTS = {
    "SettingsLib": {
        # AOSP-17 (Task 071): vintage 16→17 全族升 2.0.0
        "group": "com.android.systemui", "name": "SettingsLib", "version": "2.0.0",
        "deps": _settingslib_closure_dep_entries(),
    },
    # AOSP-17 (Task 071): WifiTrackerLib / iconloader / setupcompat /
    # LowLightDreamLib 四族已从坐标表移除——Task 059 用户批准的直连 AAR 例外：
    # 单 artifact、单 consumer、骨架 POM、Maven 副本与 libs/aars/ 字节相同，
    # 直接经 files("libs/aars/xxx.aar") 消费，不入本地 Maven 仓（与 16 时代
    # libs/maven/ 的 23 族清单一致，保证脚本再生形状可复现）。
    "WindowManager-Shell": {"group": "com.android.systemui", "name": "WindowManager-Shell", "version": "2.0.0"},
    # Task 073（C4b）：shared 类集 +aidls 闭包（IShellTransitions/AnimatedSurface 等 19 类），
    # 升 2.0.1 并退役 2.0.0（AGENTS §3.2.4 内容变化必须升坐标）
    "WindowManager-Shell-shared": {"group": "com.android.systemui", "name": "WindowManager-Shell-shared", "version": "2.0.1"},
    "animationlib": {"group": "com.android.systemui", "name": "animationlib", "version": "2.0.0"},
    "SettingsLibColor": {"group": "com.android.settingslib", "name": "color", "version": "2.0.0"},
    "SettingsLibSettingsTheme": {"group": "com.android.systemui", "name": "SettingsLibSettingsTheme", "version": "2.0.0"},
    # Task 015（B2）：7 个 SettingsLib per-target res-only AAR（坐标与 Soong target 名一致）
    "SettingsLibSelectorWithWidgetPreference": {"group": "com.android.systemui", "name": "SettingsLibSelectorWithWidgetPreference", "version": "2.0.0"},
    "SettingsLibRestrictedLockUtils": {"group": "com.android.systemui", "name": "SettingsLibRestrictedLockUtils", "version": "2.0.0"},
    "SettingsLibActionButtonsPreference": {"group": "com.android.systemui", "name": "SettingsLibActionButtonsPreference", "version": "2.0.0"},
    "SettingsLibProgressBar": {"group": "com.android.systemui", "name": "SettingsLibProgressBar", "version": "2.0.0"},
    "SettingsLibTwoTargetPreference": {"group": "com.android.systemui", "name": "SettingsLibTwoTargetPreference", "version": "2.0.0"},
    "SettingsLibLayoutPreference": {"group": "com.android.systemui", "name": "SettingsLibLayoutPreference", "version": "2.0.0"},
    "SettingsLibAdaptiveIcon": {"group": "com.android.systemui", "name": "SettingsLibAdaptiveIcon", "version": "2.0.0"},
    # Task 040（Batch 4D）：10 个新增 SettingsLib per-target res-only AAR（坐标与 Soong target 名一致）
    "SettingsLibMainSwitchPreference": {"group": "com.android.systemui", "name": "SettingsLibMainSwitchPreference", "version": "2.0.0"},
    "SettingsLibAppPreference": {"group": "com.android.systemui", "name": "SettingsLibAppPreference", "version": "2.0.0"},
    "SettingsLibBannerMessagePreference": {"group": "com.android.systemui", "name": "SettingsLibBannerMessagePreference", "version": "2.0.0"},
    "SettingsLibBarChartPreference": {"group": "com.android.systemui", "name": "SettingsLibBarChartPreference", "version": "2.0.0"},
    "SettingsLibButtonPreference": {"group": "com.android.systemui", "name": "SettingsLibButtonPreference", "version": "2.0.0"},
    "SettingsLibFooterPreference": {"group": "com.android.systemui", "name": "SettingsLibFooterPreference", "version": "2.0.0"},
    "SettingsLibIllustrationPreference": {"group": "com.android.systemui", "name": "SettingsLibIllustrationPreference", "version": "2.0.0"},
    "SettingsLibSliderPreference": {"group": "com.android.systemui", "name": "SettingsLibSliderPreference", "version": "2.0.0"},
    "SettingsLibUsageProgressBarPreference": {"group": "com.android.systemui", "name": "SettingsLibUsageProgressBarPreference", "version": "2.0.0"},
    "SettingsLibSettingsSpinner": {"group": "com.android.systemui", "name": "SettingsLibSettingsSpinner", "version": "2.0.0"},
}

POM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<project xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"
    xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{group}</groupId>
  <artifactId>{name}</artifactId>
  <version>{version}</version>
  <packaging>aar</packaging>{deps_section}
</project>
"""


def _render_deps_section(deps) -> str:
    """把 deps 列表渲染为 POM <dependencies> 块；None/空列表 → 空字符串（骨架 POM）。"""
    if not deps:
        return ""
    parts = ["\n  <dependencies>"]
    for dep in deps:
        parts.append("\n    <dependency>")
        parts.append(f"\n      <groupId>{dep['group']}</groupId>")
        parts.append(f"\n      <artifactId>{dep['name']}</artifactId>")
        parts.append(f"\n      <version>{dep['version']}</version>")
        parts.append("\n    </dependency>")
    parts.append("\n  </dependencies>")
    return "".join(parts)


def artifact_dir(repo: Path, group: str, name: str, version: str) -> Path:
    """Maven 仓中 artifact 的目录路径。"""
    return repo / Path(group.replace(".", "/")) / name / version


def install_aar(aar_path: Path, group: str, name: str, version: str,
                repo: Path, deps=None) -> tuple:
    """安装一个 AAR 到本地 Maven 仓，返回 (aar_dst, pom_dst) 路径。

    :param deps: 可选传递依赖列表 [{group, name, version}]，渲染进 POM（ADR 0005）。
    """
    dst_dir = artifact_dir(repo, group, name, version)
    dst_dir.mkdir(parents=True, exist_ok=True)
    aar_dst = dst_dir / f"{name}-{version}.aar"
    pom_dst = dst_dir / f"{name}-{version}.pom"
    shutil.copyfile(aar_path, aar_dst)
    pom_dst.write_text(POM_TEMPLATE.format(
        group=group, name=name, version=version,
        deps_section=_render_deps_section(deps)))
    return aar_dst, pom_dst


def install_all(source_dir: Path = DEFAULT_SOURCE_DIR,
                repo_dir: Path = DEFAULT_REPO_DIR,
                artifacts=None) -> list:
    """安装 artifacts 里所有 AAR。返回安装的 (aar_dst, pom_dst) 列表。"""
    artifacts = artifacts or ARTIFACTS
    installed = []
    for aar_name, coord in artifacts.items():
        aar_path = source_dir / f"{aar_name}.aar"
        if not aar_path.exists():
            raise FileNotFoundError(f"缺少 AAR: {aar_path}")
        dst = install_aar(aar_path, coord["group"], coord["name"], coord["version"],
                          repo_dir, deps=coord.get("deps"))
        installed.append(dst)
    return installed


def main():
    ap = argparse.ArgumentParser(description="把 libs/aars/*.aar 安装到 libs/maven/ 本地 Maven 仓")
    ap.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR), help="AAR 源目录")
    ap.add_argument("--repo-dir", default=str(DEFAULT_REPO_DIR), help="Maven 仓目录")
    ap.add_argument("artifacts", nargs="*", default=None,
                    help="要安装的 artifact 名（默认全部）")
    args = ap.parse_args()

    source_dir = Path(args.source_dir)
    repo_dir = Path(args.repo_dir)
    names = args.artifacts or list(ARTIFACTS)

    selected = {n: ARTIFACTS[n] for n in names}
    installed = install_all(source_dir, repo_dir, selected)
    for aar_dst, pom_dst in installed:
        print(f"installed: {aar_dst.relative_to(PROJECT_ROOT)}  ({aar_dst.stat().st_size} bytes)")
        print(f"           {pom_dst.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
