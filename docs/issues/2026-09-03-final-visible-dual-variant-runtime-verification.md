# Debug / Release 最终可见模拟器验证（2026-09-03）

## 背景与目标

用户要求在 SysUISdk Release 发布后做最后一轮端到端验证：串行构建 Debug 与 Release；启动用户可见的 same-tree AOSP 17 模拟器；先部署 Debug 并整机重启，停下等待用户目视确认；确认后再部署 Release，重复运行验证。

最终结论必须区分构建、APK 静态门、部署、重启后运行和用户目视确认，任何局部门禁不得冒充最终运行结果。

## 执行计划

1. 串行运行 `:app:assembleDebug` 和 `:app:assembleRelease`，每个构建后记录 APK 大小、SHA-256，并运行 `tools/check_aconfig_jarjar_references.py`；两次构建之间停止 Gradle/Kotlin daemon。
2. 启动 `sdk_phone64_x86_64` same-tree 模拟器。主机 `DISPLAY=:0` 可用，优先启动 emulator 原生窗口；若窗口不可见，则运行 `scrcpy -s emulator-5554` 供用户观看。
3. fresh userdata 执行 root / disable-verity / reboot / remount。按 staged copy → device SHA → atomic mv → 权限/SELinux → 清 oat/dalvik cache 的规程部署 Debug，重新授予 `BLUETOOTH_CONNECT` 与 `READ_CONTACTS`，整机重启。
4. 冻结 Debug host/device SHA、boot ID、PID、crash/FATAL 与 UI 窗口状态后停止操作，等待用户目视确认。
5. 用户确认后，以同一规程部署 Release 并重复验证。

## 初始状态

- git HEAD：`928353a0`；开始时工作区 clean。
- 主机：30 GiB RAM（约 22 GiB available）+ 8 GiB swap；根分区剩余约 17 GiB；`/tmp` 为 16 GiB tmpfs。
- `DISPLAY=:0`、Wayland 会话和 X11 socket 可用；`scrcpy` 已安装。
- 开始时无在线 adb 设备、无 emulator 进程、无 Gradle/Kotlin daemon。

## 执行记录

待填写。
