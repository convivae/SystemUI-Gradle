# Debug / Release 最终可见模拟器验证（2026-09-03）

## 背景与目标

用户要求在 SysUISdk Release 发布后做最后一轮端到端验证：串行构建 Debug 与 Release；启动用户可见的 same-tree AOSP 17 模拟器；先部署 Debug 并整机重启，停下等待用户目视确认；确认后再部署 Release，重复运行验证。

最终结论必须区分构建、APK 静态门、部署、重启后运行和用户目视确认，任何局部门禁不得冒充最终运行结果。

## 执行计划

1. 串行运行 `:app:assembleDebug` 和 `:app:assembleRelease`，每个构建后记录 APK 大小、SHA-256，并运行 `tools/check_aconfig_jarjar_references.py`；两次构建之间停止 Gradle/Kotlin daemon。
2. 启动 `sdk_phone64_x86_64` same-tree 模拟器。主机 `DISPLAY=:0` 可用，优先启动 emulator 原生窗口；若窗口不可见，则运行 `scrcpy -s emulator-5554` 供用户观看。
3. fresh userdata 执行 root / disable-verity / reboot / remount。按 staged copy → device SHA → atomic mv → 权限/SELinux → 清 oat/dalvik cache 的规程部署 Debug，整机重启。
   **（2026-09-04 修订，Task 102/103）**：本步骤不再包含任何手动 `pm grant`。sharedUserId 修复（`app/src/main/AndroidManifest.xml` 显式声明 `android:sharedUserId="android.uid.systemui"`，Task 101 根因）后，fresh userdata 上 `DefaultPermissionGrantPolicy` 首靴即自动授予全部运行时权限（persistent ✓ priv-app ✓ platform-signed ✓）——
验收标准改为：部署后重启，`BLUETOOTH_CONNECT` 与 `READ_CONTACTS` 必须 **未经任何手动授予即为 granted=true**，sharedUser 为 `android.uid.systemui`/appId 10123。若不满足即 FAIL。此前的研究用模拟器（emulator-5554，QEMU PID 36896）因 Task 101 的无 sharedUserId 启动污染了 appId-10123 授权状态，已按污染实例废弃，改用全新实例验证。
4. 冻结 Debug host/device SHA、boot ID、PID、crash/FATAL 与 UI 窗口状态后停止操作，等待用户目视确认。
5. 用户确认后，以同一规程部署 Release 并重复验证。

## 初始状态

- git HEAD：`928353a0`；开始时工作区 clean。
- 主机：30 GiB RAM（约 22 GiB available）+ 8 GiB swap；根分区剩余约 17 GiB；`/tmp` 为 16 GiB tmpfs。
- `DISPLAY=:0`、Wayland 会话和 X11 socket 可用；`scrcpy` 已安装。
- 开始时无在线 adb 设备、无 emulator 进程、无 Gradle/Kotlin daemon。

## 执行记录

**最终判定：DUAL_VARIANT_RUNTIME_PASS（2026-09-06）**。sharedUserId 修复（commit `9723a96e`）后，
Debug 与 Release 两个变体在同一全新实例上先后部署，均通过整机重启后全项验收，全程
**零手动 `pm grant`**。完整报告：`docs/architecture/2026-09-06-fresh-instance-dual-variant-validation.md`。

实际执行与计划的差异（背景：执行中途宿主机重启，`/tmp` 被清空，原污染实例随之销毁——
正好满足“旧实例完全停止”的要求；但图形会话仅剩 GDM 登录界面，无可用 X 会话，
`DISPLAY=:0` 不可达）：

1. 变体串行构建改为分属 Task 103（Release 重建 + Debug 部署）与 Task 104（Release 部署），
   两个任务在同一实例上先后完成。
2. 模拟器按 runbook 原始命令以 **headless**（`-no-window`）方式运行于独立 herdr tab
   （`task103-emulator`，端口 5554/5555，实例目录
   `/tmp/acloud_gf_temp/local-goldfish-instance-2/`）——这是验证文档自身许可的回退方式；
   用户通过 `scrcpy -s emulator-5554` 观看。
3. 部署采用 staged copy → 设备 SHA 门禁 → 原子 mv → 权限/SELinux → 清 oat/dalvik cache
   的标准规程，两个变体各经历一次 disable-verity 后的整机重启。

验收数据（均为文本证据，无截图）：

- **Debug `e61d5485…`（Task 103）**：fresh userdata 首靴 stock 基线即含 DPGP 授予
  （sharedUser `android.uid.systemui/10123`）；部署后重启 boot_id `a0f06e2e-…`，
  identity 保持 10123，BLUETOOTH_CONNECT / READ_CONTACTS 均为
  `granted=true [SYSTEM_FIXED|GRANTED_BY_DEFAULT]`，PID 854 稳定 180s，0 FATAL，
  6 个窗口（uid 10123），KeyguardService 运行。**用户已视觉确认 Debug UI 正常**。
- **Release `6d1d4254…`（Task 104）**：同实例 Debug→Release 同 identity 替换，重启后
  boot_id `03244666-…`，identity 10123，两项权限仍为 granted=true，PID 855 稳定 180s，
  0 FATAL，6 个窗口，KeyguardService 运行（RELEASE_DEPLOY_PASS）。
- 静态门禁：Release aconfig reference 完整性门禁 RESULT=PASS（0 violations）；
  `aapt2` 确认 Release 清单含 `sharedUserId="android.uid.systemui"`。

结论：Task 101 发现的权限回归（AGP manifest merger 不从 library 清单继承 sharedUserId
→ appId 10160 → 授权不适用）已由 app 模块主清单显式声明修复，对两个变体均闭环
（Tasks 100–104 证据链完整）。运行时验证至此全部完成，剩余收尾仅 C6（项目 release tag、
版本声明、manifest 快照）及暂停中的 Task 079 / 方案B。

原始证据：`/tmp/task103-fresh-instance-validation/`、`/tmp/task104-release-validation/`。
