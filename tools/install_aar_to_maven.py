#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 libs/aars/*.aar 安装到 libs/maven/ 本地 Maven 仓，生成简单 POM 骨架。

模式参考 CarSystemUIGradle 项目：
  libs/maven/<group>/<name>/<version>/<name>-<version>.aar
  libs/maven/<group>/<name>/<version>/<name>-<version>.pom

POM 骨架只声明 groupId/artifactId/version/packaging=aar，无 transitive deps
（由消费方显式声明所需依赖，避免依赖地狱）。

与 gen_aar_maven.py 的区别：
  - gen_aar_maven.py 把 R.jar 错误合并进 classes.jar（已废弃的失败实验）
  - 本工具只做文件复制 + POM 生成，不修改 AAR 字节内容
"""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "libs/aars"
DEFAULT_REPO_DIR = PROJECT_ROOT / "libs/maven"

# AAR 名 → Maven 坐标
ARTIFACTS = {
    "SettingsLib": {"group": "com.android.systemui", "name": "SettingsLib", "version": "1.0.0"},
    "WifiTrackerLib": {"group": "com.android.systemui", "name": "WifiTrackerLib", "version": "1.0.0"},
    "WindowManager-Shell": {"group": "com.android.systemui", "name": "WindowManager-Shell", "version": "1.0.0"},
    "WindowManager-Shell-shared": {"group": "com.android.systemui", "name": "WindowManager-Shell-shared", "version": "1.0.0"},
    "animationlib": {"group": "com.android.systemui", "name": "animationlib", "version": "1.0.0"},
    "iconloader": {"group": "com.android.systemui", "name": "iconloader", "version": "1.0.0"},
    "LowLightDreamLib": {"group": "com.android.systemui", "name": "LowLightDreamLib", "version": "1.0.0"},
    "SettingsLibColor": {"group": "com.android.settingslib", "name": "color", "version": "1.0.0"},
    "setupcompat": {"group": "com.android.systemui", "name": "setupcompat", "version": "1.0.0"},
}

POM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<project xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"
    xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{group}</groupId>
  <artifactId>{name}</artifactId>
  <version>{version}</version>
  <packaging>aar</packaging>
</project>
"""


def artifact_dir(repo: Path, group: str, name: str, version: str) -> Path:
    """Maven 仓中 artifact 的目录路径。"""
    return repo / Path(group.replace(".", "/")) / name / version


def install_aar(aar_path: Path, group: str, name: str, version: str,
                repo: Path) -> tuple:
    """安装一个 AAR 到本地 Maven 仓，返回 (aar_dst, pom_dst) 路径。"""
    dst_dir = artifact_dir(repo, group, name, version)
    dst_dir.mkdir(parents=True, exist_ok=True)
    aar_dst = dst_dir / f"{name}-{version}.aar"
    pom_dst = dst_dir / f"{name}-{version}.pom"
    shutil.copyfile(aar_path, aar_dst)
    pom_dst.write_text(POM_TEMPLATE.format(group=group, name=name, version=version))
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
        dst = install_aar(aar_path, coord["group"], coord["name"], coord["version"], repo_dir)
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
