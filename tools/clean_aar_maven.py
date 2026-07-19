#!/usr/bin/env python3
"""
clean_aar_maven.py - 清理本地 Maven AAR 中的重复类

从 gen_aar_maven.py 生成的 AAR 文件包含 material、kotlinx、androidx 等类，
与 Gradle Maven 依赖冲突。此脚本清理这些类。

用法:
    python3 tools/clean_aar_maven.py
"""

import os
import shutil
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
MAVEN_DIR = PROJECT_ROOT / "libs" / "maven"

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
    "com/google/android/material/",  # material 库冲突
    "com/airbnb/",
    "okio/",
    "okhttp3/",
    "dagger/",
    "javax/inject/",
    "javax/annotation/",
    "jakarta/",
    "com/intellij/",
    "META-INF/versions/",
    "META-INF/DEPENDENCIES",
    "META-INF/LICENSE*",
    "META-INF/NOTICE*",
    "META-INF/*.kotlin_module",
]


def should_remove(file_path: str) -> bool:
    """判断文件是否应该被删除"""
    for pkg in PACKAGES_TO_REMOVE:
        if "*" in pkg:
            import fnmatch
            if fnmatch.fnmatch(file_path, pkg):
                return True
        elif file_path.startswith(pkg):
            return True
    return False


def clean_jar_in_aar(aar_path: Path) -> int:
    """清理 AAR 中的 classes.jar，返回清理的文件数"""
    print(f"  Cleaning classes.jar in {aar_path.name}...")

    temp_aar = aar_path.with_suffix(".aar.tmp")
    removed = 0
    kept = 0

    with zipfile.ZipFile(aar_path, "r") as src:
        with zipfile.ZipFile(temp_aar, "w", zipfile.ZIP_DEFLATED) as dst:
            for item in src.namelist():
                if item == "classes.jar":
                    # 清理 classes.jar 中的冲突类
                    jar_data = src.read(item)
                    import io
                    src_jar = zipfile.ZipFile(io.BytesIO(jar_data), "r")
                    out_buffer = io.BytesIO()
                    dst_jar = zipfile.ZipFile(out_buffer, "w", zipfile.ZIP_DEFLATED)

                    for jar_item in src_jar.namelist():
                        if jar_item.endswith("/"):
                            continue
                        if should_remove(jar_item):
                            removed += 1
                        else:
                            dst_jar.writestr(jar_item, src_jar.read(jar_item))
                            kept += 1

                    src_jar.close()
                    dst_jar.close()
                    dst.writestr(item, out_buffer.getvalue())
                else:
                    dst.writestr(item, src.read(item))

    shutil.move(temp_aar, aar_path)
    print(f"    Removed {removed} classes, kept {kept}")
    return removed


def main():
    if not MAVEN_DIR.exists():
        print(f"ERROR: {MAVEN_DIR} does not exist")
        return

    total_removed = 0
    for aar_path in sorted(MAVEN_DIR.rglob("*.aar")):
        total_removed += clean_jar_in_aar(aar_path)

    print(f"\nTotal removed: {total_removed} classes")
    print(f"Cleaned AARs are now compatible with Gradle Maven dependencies")


if __name__ == "__main__":
    main()
