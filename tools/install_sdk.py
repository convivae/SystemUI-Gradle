#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 android-SysUISdk 平台并补齐 SystemUI aidl 编译所需的框架隐藏接口声明。

背景：SystemUI 的 .aidl（tier① 自有代码，源码编译）import 了少量 framework @hide 接口
      （如 android.os.IRemoteCallback）。标准 SysUISdk/framework.aidl 只含 public API
      的 parcelable 声明，缺这些隐藏接口 → aidl 编译报 "couldn't find import"。
规则：framework 代码属 tier②，不允许源码复制进 SystemUI；正确做法是在 SysUISdk 层面补齐
      （framework.aidl 支持 `interface X;` 声明），等价于"重新生成 SysUISdk"。
幂等：重复执行只会补一次。
"""
import os
import sys

# SystemUI aidl 需要、但 public framework.aidl 缺失的 framework @hide 接口。
# 若将来有新增，追加到此列表即可。
HIDDEN_IFACES = [
    "android.os.IRemoteCallback",
]

# SystemUI aidl import 了、但 public framework.aidl 缺失的 framework @hide parcelable。
# 类本身在 framework.jar；这里只补 aidl 预处理声明，避免把 framework 代码源码复制进 SystemUI。
# 例：ISystemUiProxy.aidl `import com.android.internal.util.ScreenshotRequest;`
HIDDEN_PARCELABLES = [
    "com.android.internal.util.ScreenshotRequest",
]


def main() -> int:
    sdk_root = (
        os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
        or "/home/conv/Android/Sdk"
    )
    target = os.path.join(sdk_root, "platforms", "android-SysUISdk")
    if not os.path.isdir(target):
        print(f"ERROR: {target} does not exist.", file=sys.stderr)
        return 1
    print(f"SysUISdk OK: {target}")

    fw = os.path.join(target, "framework.aidl")
    if not os.path.isfile(fw):
        print(f"ERROR: {fw} not found.", file=sys.stderr)
        return 1

    with open(fw, "r", encoding="utf-8") as f:
        content = f.read()

    to_append = []
    for iface in HIDDEN_IFACES:
        decl = f"interface {iface};"
        if decl in content:
            print(f"  已存在: {decl}")
        else:
            to_append.append(decl)
            print(f"  待补齐: {decl}")
    for parcel in HIDDEN_PARCELABLES:
        decl = f"parcelable {parcel};"
        if decl in content:
            print(f"  已存在: {decl}")
        else:
            to_append.append(decl)
            print(f"  待补齐: {decl}")

    if to_append:
        with open(fw, "a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            for decl in to_append:
                f.write(decl + "\n")

    print(f"framework.aidl patched: {fw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
