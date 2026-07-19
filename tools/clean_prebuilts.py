#!/usr/bin/env python3
"""
clean_prebuilts.py - 清理 prebuilt JAR 中的重复类

从 AOSP 编译的 prebuilt JAR 包含 kotlinx、androidx 等类，与 Gradle Maven 依赖冲突。
此脚本清理这些类，保留 SystemUI 自己的类。

用法:
    python3 tools/clean_prebuilts.py
"""

import os
import re
import shutil
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
PREBUILTS_DIR = PROJECT_ROOT / "libs" / "prebuilts"

# 需要从 JAR 中删除的包前缀（与 Gradle Maven 依赖冲突）
PACKAGES_TO_REMOVE = [
    "kotlinx/",
    "kotlin/",
    "androidx/",
    "com/google/common/",
    "com/google/errorprone/",
    "com/google/j2objc/",
    "com/google/protobuf/",
    "com/google/thirdparty/",
    "org/checkerframework/",
    "org/intellij/",
    "org/jetbrains/",
    "org/jspecify/",
    "com/airbnb/",
    "okio/",
    "okhttp3/",
    "dagger/",
    "javax/inject/",
    "javax/annotation/",
    "jakarta/",
    "com/intellij/",
    "META-INF/versions/",  # 多版本 jar
    "META-INF/DEPENDENCIES",
    "META-INF/LICENSE*",
    "META-INF/NOTICE*",
    "META-INF/*.kotlin_module",
]


def should_remove(file_path: str) -> bool:
    """判断文件是否应该被删除"""
    for pkg in PACKAGES_TO_REMOVE:
        if "*" in pkg:
            # 通配符匹配
            import fnmatch
            if fnmatch.fnmatch(file_path, pkg):
                return True
        elif file_path.startswith(pkg):
            return True
    return False


def clean_jar(jar_path: Path) -> int:
    """清理 JAR 中的冲突类，返回清理的文件数"""
    print(f"Cleaning {jar_path.name}...")

    temp_jar = jar_path.with_suffix(".jar.tmp")
    removed = 0
    kept = 0

    with zipfile.ZipFile(jar_path, "r") as src:
        with zipfile.ZipFile(temp_jar, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.namelist():
                if item.endswith("/"):
                    continue
                if should_remove(item):
                    removed += 1
                else:
                    dst.writestr(item, src.read(item))
                    kept += 1

    shutil.move(temp_jar, jar_path)
    print(f"  Removed {removed} classes, kept {kept}")
    return removed


def main():
    if not PREBUILTS_DIR.exists():
        print(f"ERROR: {PREBUILTS_DIR} does not exist")
        return

    total_removed = 0
    for jar_path in sorted(PREBUILTS_DIR.glob("*.jar")):
        total_removed += clean_jar(jar_path)

    print(f"\nTotal removed: {total_removed} classes")
    print(f"Cleaned JARs are now compatible with Gradle Maven dependencies")


if __name__ == "__main__":
    main()
