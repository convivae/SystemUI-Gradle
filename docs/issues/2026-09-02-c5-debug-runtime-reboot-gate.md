# C5 Task 098：fresh Debug APK runtime reboot gate

**日期**：2026-09-02
**状态**：PLANNED — 尚未启动模拟器、尚未部署
**前置**：Task 096 fresh Debug build/static gate `PASS`；Task 097 fresh Release build/R8/static gate `PASS`；Task 077 已验收 17 emu64x durable super/overlay 通道。

## 背景

Task 096 已冻结 Debug APK 的构建与静态身份，但没有在设备上执行该 APK。既有 Task 075 Debug 热运行使用的是更早 APK，Task 077 的 durable 64MiB probe 也只证明 overlay 通道，均不能替代本轮 fresh artifact runtime 证据。

本任务只消费现有 Debug APK，不运行 Gradle、不修复代码，并在 task077 的 AOSP-17 emu64x 镜像上证明：host/device APK 身份一致、priv-app replacement 生效、SystemUI 在部署后的冷启动阶段稳定、UI/窗口服务正常，并在第二次整机 reboot 后继续保持同一 APK 与稳定运行。

## 冻结输入

- 项目基线：规划时 `HEAD == origin/main == a47ed877d28f9e7a04817d4b0ede7203a2542fe0`；实际 dispatch commit 由 worker preflight 记录。
- Debug APK：`app/build/outputs/apk/debug/app-debug.apk`
  - size：`190547804` bytes
  - SHA-256：`f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`
- 17 emu64x `super.img`：`/home/conv/myspace/aosp/out/target/product/emu64x/super.img`
  - size：`3028287488` bytes
  - SHA-256：`50496c9b542aa49939840b4f1befb4ca11767b707148a7b77b395844740d040e`
- 设备 serial：`emulator-5554`；目标 APK：`/system_ext/priv-app/SystemUI/SystemUI.apk`。
- Scratch evidence：`/tmp/task098-c5-debug-runtime-reboot/`。

任一冻结身份不匹配即 `BLOCKED_PREFLIGHT`；不得在本任务中重建 APK、AOSP 镜像或修复输入。

## 执行计划

1. 严格 startup/CONTRACT 后做只读 preflight：clean pushed base、APK/super identity、无冲突 build/emulator/ADB 状态、磁盘/内存和 launcher inputs。
2. 从基础镜像启动独立 task077 emulator service tab；fresh userdata 首启后补持久 runtime grants，重启并证明 stock baseline 健康。
3. `adb root` + `disable-verity` + reboot，验证 582MiB 级 super-backed scratch、五个 overlay 和 `/system_ext` 可写。
4. 按 staged + SHA + same-filesystem atomic `mv` 规程部署冻结 Debug APK；严格检查空间、权限、SELinux label、pre-reboot device SHA，并在 reboot 前清理 oat/dalvik cache与logcat。
5. **Checkpoint A（部署冷启动）**：reboot 后核对 boot identity、device SHA、package path、PID 11×30s稳定、crash/FATAL/NCDFE为0、StatusBar/NotificationShade/Taskbar/ImageWallpaper、`dumpsys statusbar`、`android layout`和视觉截图。
6. 清空logcat并执行第二次 whole-device reboot；以不同 boot ID/uptime证明真实重启。
7. **Checkpoint B（整机重启后）**：重复 device SHA、package、PID 11×30s、crash/FATAL/NCDFE、窗口/statusbar、layout及视觉截图门。
8. 仅删除 staging/temp 文件；PASS 时保持 Debug APK、verity disabled、overlay和 emulator service运行，供 Chief验收及后续独立 Release runtime gate。worker 不改 tracked files、不commit/push。

## 验收标准

`DEBUG_RUNTIME_REBOOT_PASS` 仅在以下全部成立时宣告：

- host APK 初/终 SHA 均为冻结值；目标 device SHA 在 atomic replacement 后、Checkpoint A、Checkpoint B 均相同。
- `sys.boot_completed=1`；第二次 reboot 的 boot ID 与 Checkpoint A 不同。
- 两个 checkpoint 各自 SystemUI PID 单一且 11×30s不变，最终进程 elapsed ≥300s。
- 两个 checkpoint 的 fresh log window 中：`logcat -b crash -d` 为0行；全量logcat无 `FATAL EXCEPTION`、`NoClassDefFoundError`、SystemUI crash loop或 ANR 对话框。
- 两个 checkpoint 均有 StatusBar、NotificationShade、Taskbar、ImageWallpaper窗口；小写 `dumpsys statusbar` 成功响应。
- 两个 checkpoint 的 `android layout` 与截图均显示可用系统 UI，无 crash/ANR/黑屏；截图必须由 worker实际视觉读取，不能只凭命令exit判定。
- APK survive both reboots，scratch/overlay仍挂载，SELinux enforcing，worktree保持clean；无 Gradle/Soong/Ninja、代码修复或 Task 079 action。

任何 frozen input、启动、部署 SHA、boot、PID、fatal或UI门失败都保存首个证据并停止；不得在同一任务修代码、换 APK、启用 verity、重建镜像或改 gate。

## 成功边界

本任务 PASS 只关闭 Debug runtime reboot gate，不证明 Release runtime。Release 必须在 Debug durable closure 后由独立任务部署 Task 097 APK并重复同等级证据。Task 079 broad replay继续暂停。

## 构建记录

规划阶段未运行构建、Gradle、Soong、ADB部署或模拟器；只读取文档/状态并创建本计划。
