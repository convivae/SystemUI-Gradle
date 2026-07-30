#!/usr/bin/env python3
"""
rebuild_settingslib_aar.py — 用 AOSP 源码的 strings.xml 替换 SettingsLib AAR 中不完整的 res
"""

import zipfile
import shutil
from pathlib import Path

PROJECT_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
AOSP_ROOT = Path("/home/conv/myspace/aosp")
AAR_PATH = PROJECT_ROOT / "libs" / "maven" / "com" / "android" / "systemui" / "SettingsLib" / "1.0.0" / "SettingsLib-1.0.0.aar"
BACKUP_PATH = AAR_PATH.with_suffix(".aar.bak")
TEMP_PATH = AAR_PATH.with_suffix(".aar.tmp")

# AOSP SettingsLib res 目录（含所有 strings.xml）
AOSP_SETTINGSLIB_RES = AOSP_ROOT / "frameworks" / "base" / "packages" / "SettingsLib" / "res"

def main():
    # 备份原始 AAR
    if not BACKUP_PATH.exists():
        shutil.copy(AAR_PATH, BACKUP_PATH)
        print(f"Backup: {BACKUP_PATH}")

    # 收集 AOSP 中所有 res 文件
    aosp_res_files = {}
    for f in AOSP_SETTINGSLIB_RES.rglob("*"):
        if f.is_file():
            rel = f.relative_to(AOSP_SETTINGSLIB_RES)
            aosp_res_files[str(rel)] = f

    print(f"Found {len(aosp_res_files)} res files in AOSP SettingsLib")

    # 重建 AAR
    with zipfile.ZipFile(AAR_PATH, "r") as src, zipfile.ZipFile(TEMP_PATH, "w", zipfile.ZIP_DEFLATED) as dst:
        # 复制原 AAR 中所有文件，除非在 aosp_res_files 中有对应
        for name in src.namelist():
            # 跳过 res 目录（重新添加完整版）
            if name.startswith("res/"):
                continue
            # 复制
            data = src.read(name)
            dst.writestr(name, data)

        # 添加 AOSP 完整 res
        for rel, src_path in aosp_res_files.items():
            arcname = "res/" + str(rel).replace("\\", "/")
            with open(src_path, "rb") as f:
                data = f.read()
            dst.writestr(arcname, data)

    # 删除 AAR 中旧的 R.txt — 让 AGP 在 build 时基于 AOSP 完整 strings.xml 重新生成
    import os
    tmp_no_r = AAR_PATH.with_suffix(".aar.noR")
    with zipfile.ZipFile(AAR_PATH, "r") as src, zipfile.ZipFile(tmp_no_r, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in src.namelist():
            if name == "R.txt":
                continue
            data = src.read(name)
            dst.writestr(name, data)
    shutil.move(tmp_no_r, AAR_PATH)
    print(f"Rebuilt: {AAR_PATH}")
    print(f"Size: {AAR_PATH.stat().st_size} bytes")

if __name__ == "__main__":
    main()