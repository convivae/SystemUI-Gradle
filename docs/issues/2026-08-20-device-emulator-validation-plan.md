# 2026-08-20 — Debug/Release APK 模拟器与真机验证计划

## 用户目标

Debug 与 Release 编译完成后，在 Android Studio / SDK Manager 创建的模拟器及后续真机上
安装 SystemUI APK，验证是否可启动、是否 crash、关键 SystemUI 功能是否生效。

## 执行时机

Task 029（未混淆 release）与 Task 030（R8 + resource shrink release）全部完成后实施。
Debug APK 同时作为对照组。

## 必须先核对的前置条件

SystemUI 不是普通应用，标准 AVD 已预装 `com.android.systemui`：

1. **签名**：预装 SystemUI 的证书是否与本项目 `keystore/platform.keystore` 一致；不一致时
   `adb install -r` 通常会因签名冲突失败。
2. **镜像能力**：优先 AOSP userdebug/可 root、可 `adb remount` 的 system image；
   Google Play image 通常不可替换 `/system_ext/priv-app/SystemUI`。
3. **API/资源匹配**：AVD framework/framework-res 必须尽量匹配本项目 AOSP 分支与 SysUISdk；
   “最新 API”不自动等价于“匹配”，私有资源 ID/API 不一致可能在启动时 crash。
4. **替换与回滚**：记录原 APK 路径、证书、SELinux/context，准备快照/恢复方案；不得直接
   覆盖唯一可用镜像而无回滚。
5. **日志**：保存 `adb logcat`、`dumpsys activity/service/package`、native tombstone/ANR，
   分清安装失败、签名失败、进程启动失败和运行时 crash。

## 预期阶段

1. 环境审计（AVD image/API/build type/root/signature/framework-res）；
2. Debug APK 替换/启动/日志基线；
3. Release APK 同流程，对比 R8/shrink 后行为；
4. 真机在具备匹配 platform key 与系统分区权限后复验；
5. 输出安装命令、日志证据、功能/崩溃矩阵与回滚步骤。

具体实现需另写 task brief，并优先使用 `android` CLI / adb 的官方流程。
