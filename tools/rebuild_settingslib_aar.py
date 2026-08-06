#!/usr/bin/env python3
"""
rebuild_settingslib_aar.py — 用 AOSP 源码的 res/ 替换 SettingsLib AAR 中不完整的资源

**问题 (2026-07-30)**: SettingsLib AAR 是用 AOSP `out/.../SettingsLib-res` 中间产物生成的，
其中 res/values/strings.xml 只含 608 个 string (缺失 113 个，例如 font_scale_percentage，
guest_exit_dialog_message_non_ephemeral 等)。这是因为 AOSP 构建过程会对 Resources 进行
去重/合并，导致 out 中的资源比源码少。

**修复**: 从 AOSP source tree (`frameworks/base/packages/SettingsLib/res/`) 重新拷贝完整 res
到 AAR，替换不完整的 out 资源。

**注意事项**:
- 删掉 AAR 中的 R.txt 是为了让 AGP 在 build 时基于完整 strings.xml 重新生成 R 类
  (但这会导致更多错误，因为 AGP 必须从 aar-metadata 推断 namespace，可能不准确)
- 我们改用另一种方式：**保留 R.txt**，但 R.txt 是从 out 抽的旧版不完整；
  这意味着 font_scale_percentage 等 R.string.* 仍找不到（短期限制，需要后续优化）

**用法**:
    python3 tools/rebuild_settingslib_aar.py
    # 重建后 R.txt 中仍可能不包含所有 strings.xml 中的 string (AGP 限制)
"""

import os
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")
AOSP_ROOT = Path("/home/conv/myspace/aosp")
AAR_PATH = PROJECT_ROOT / "libs" / "maven" / "com" / "android" / "systemui" / "SettingsLib" / "1.0.0" / "SettingsLib-1.0.0.aar"
BACKUP_PATH = AAR_PATH.with_suffix(".aar.bak")
TEMP_PATH = AAR_PATH.with_suffix(".aar.tmp")

# AOSP SettingsLib res 目录（含所有 strings.xml）
AOSP_SETTINGSLIB_RES = AOSP_ROOT / "frameworks" / "base" / "packages" / "SettingsLib" / "res"

# 是否删除 R.txt 让 AGP 重新生成
DELETE_R_TXT = False  # 默认保留，避免 AGP 生成空 R 类导致更多错误


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
        skip_names = {"res/"}
        if DELETE_R_TXT:
            skip_names.add("R.txt")
        for name in src.namelist():
            if name in skip_names or name.startswith("res/"):
                continue
            data = src.read(name)
            dst.writestr(name, data)

        # 添加 AOSP 完整 res
        for rel, src_path in aosp_res_files.items():
            arcname = "res/" + str(rel).replace("\\", "/")
            with open(src_path, "rb") as f:
                data = f.read()
            dst.writestr(arcname, data)

    shutil.move(TEMP_PATH, AAR_PATH)
    print(f"Rebuilt: {AAR_PATH}")
    print(f"Size: {AAR_PATH.stat().st_size} bytes")
    if DELETE_R_TXT:
        print(f"Removed: R.txt (AGP will regenerate)")


if __name__ == "__main__":
    main()
