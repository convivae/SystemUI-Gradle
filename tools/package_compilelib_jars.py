#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包 AOSP compilelib 的 debug/release Compile.java 为独立 JAR。

compilelib（frameworks/libs/systemui/compilelib）是非 SystemUI 代码（规则 F：不源码复制），
按 tier② 用 JAR 引入。两个变体仅 IS_DEBUG 常量不同（debug=true, release=false），
core 用 debugImplementation / releaseImplementation 分别消费。

产物：
  libs/compilelib-debug.jar   (IS_DEBUG = true)
  libs/compilelib-release.jar (IS_DEBUG = false)
"""

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

AOSP_ROOT = Path("/home/conv/myspace/aosp")
COMPILELIB = AOSP_ROOT / "frameworks/libs/systemui/compilelib"
DEBUG_SRC = COMPILELIB / "src-debug/com/android/systemui/util/Compile.java"
RELEASE_SRC = COMPILELIB / "src-release/com/android/systemui/util/Compile.java"

DEBUG_JAR = Path("libs/compilelib-debug.jar")
RELEASE_JAR = Path("libs/compilelib-release.jar")


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _zip_info(name: str) -> zipfile.ZipInfo:
    """固定 timestamp/metadata 的 ZipInfo，保证重复打包字节一致。"""
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    """用固定 metadata 写入一个 ZIP entry。"""
    archive.writestr(_zip_info(name), data)


def _compile_one(src: Path, output: Path) -> None:
    """用 javac --release 21 编译单个 Compile.java，打包为确定性 JAR。"""
    if not src.exists():
        raise FileNotFoundError(f"缺少 compilelib 源: {src}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        # 编译（--release 21 保证字节码版本一致）
        subprocess.run(
            ["javac", "--release", "21", "-d", str(tdp), str(src)],
            check=True, capture_output=True,
        )
        class_file = tdp / "com/android/systemui/util/Compile.class"
        if not class_file.exists():
            raise RuntimeError(f"编译未产出 Compile.class: {class_file}")
        # 确定性 JAR（entry 排序 + 固定 metadata）
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
            _write_entry(z, "com/android/systemui/util/Compile.class", class_file.read_bytes())
    print(f"{output} ({output.stat().st_size} bytes)")


def main() -> int:
    _compile_one(DEBUG_SRC, DEBUG_JAR)
    _compile_one(RELEASE_SRC, RELEASE_JAR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
