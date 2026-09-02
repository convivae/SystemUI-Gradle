# C5 Task 098：fresh Debug APK runtime reboot gate

**日期**：2026-09-02
**状态**：REPLACEMENT REQUIRED — 三次 worker 均因流程违规退休；第二次已完成部署到 Checkpoint A 早期采样但在技术验收前定性为 `RETIRED_PROTOCOL`，第三次仅在 startup 读取阶段运行了禁止的 `wc -l` 后即退休，因此仍无 Debug runtime PASS/FAIL 结论
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

## 执行记录

- planning 已提交并 push 为 `36394ca51dba4af74ce9bee8807104620110b7b9`。
- 首个 worker `task098-debug-runtime` 曾位于 `w2:t46` / `w2:p4B`，session 为 `/home/conv/.pi/agent/sessions/--home-conv-myspace-SystemUI-Gradle--/2026-09-02T12-58-24-762Z_01a06233-007a-73ed-9c19-f2a32911a610.jsonl`。session 独立确认 `provider=joycode`、`modelId=GLM-5.3`、`thinkingLevel=high`，但该 worker 在 mandated `AGENTS.md → HANDOFF.md → CHARTER.md → STATE.md → log tail → task brief` 序列前先打开了 task brief，随后没有在冻结位置重新读取 task brief。其 startup 顺序因此不合格，CONTRACT 未被 Chief 接受，tab 已退休。
- 该尝试只读取文档；未创建 evidence scratch，未执行 preflight、Gradle/Soong/Ninja、ADB、emulator/QEMU 或 process mutation，未修改 tracked files。
- 第二个 worker `task098-debug-runtime-r2` 位于 `w2:t47` / `w2:p4C`，session 为 `/home/conv/.pi/agent/sessions/--home-conv-myspace-SystemUI-Gradle--/2026-09-02T13-04-01-408Z_01a06238-2380-7832-9891-774d2b54b9cb.jsonl`。session 独立确认 `provider=joycode`、`modelId=GLM-5.3`、`thinkingLevel=high`；startup reads 与 Chief 接受的 CONTRACT 合规。但是 worker 在首次 Herdr control action（创建 emulator service tab）前，仅读取了 `herdr --skill`，没有查询将使用命令的精确 help，也没有记录 caller workspace/tab/pane，违反 mandatory Herdr control protocol。本次尝试因此在任何技术验收前定性为 **`RETIRED_PROTOCOL`**；不得从其不完整 runtime 证据推导 Debug PASS 或 FAIL。
- 第二次尝试确实发生了 runtime mutation：在证明无 owner 后删除五个旧 generated `.qcow2`；创建 instance/log 路径；在 owned tab `w2:t48` 启动 fresh `emulator-5554`；`adb root` 后授予 `BLUETOOTH_CONNECT` 与 `READ_CONTACTS`；完成 permission-baseline reboot 1/4；执行 `adb disable-verity` 并完成 reboot 2/4；建立五个 durable overlay 与约 581 MiB scratch；以 staged SHA gate、同文件系统临时文件和 atomic `mv` 将冻结 Debug APK 部署到 `/system_ext/priv-app/SystemUI/SystemUI.apk`，恢复 owner/mode/SELinux label并清理 oat/dalvik cache；完成 deployment reboot 3/4。stock baseline 为 boot ID `ba5cfe0d-1610-402f-8ba5-d2dda59635fb`、APK SHA `d0e36b33…`、PID `1027`、crash buffer 0；deployment boot ID 为 `a3d80326-a5ff-4cc5-8620-03c7ace0bd8b`，device APK SHA 为 `f3af35d9…`，最初 PID 为 `3425`。
- Checkpoint A 仅采集 3/11 个样本即收到 stop order：sample 1 PID 为 `4276`，已不同于初始 `3425`；samples 2–3 的 `pidof` 为空，并伴随由空 PID 触发的 `grep: no REGEX`。stop order 前没有完成 fresh crash/full log、窗口、statusbar、layout或截图门；因此该序列只是待新合规尝试验证的异常线索，不是正式 `DEBUG_RUNTIME_REBOOT_FAIL`。
- worker 停止了进一步 ADB/reboot，未执行 reboot 4/4 或 Checkpoint B；保留 `/tmp/task098-c5-debug-runtime-reboot/` 和 regenerated `.qcow2`，只关闭自己拥有的 emulator tab `w2:t48`。独立 census 显示 emulator/QEMU 已停止、ADB 无设备。worker 未改 tracked files，未运行 Gradle/Soong/Ninja，未 commit/push；完整退休记录见 `/tmp/task098-c5-debug-runtime-reboot/RETIREMENT.txt`。
- 下一 replacement 必须从新的 clean pushed dispatch base 启动，并在 frozen startup 读取期间只使用串行 `read`，不得插入 `wc` 或任何 bash 命令；在任何 Herdr control action 前还必须完成 `herdr --skill`、精确 command help 查询和 caller workspace/tab/pane 记录。它必须先证明无 emulator/QEMU owner，再按 frozen brief 删除第二次尝试生成的顶层 `.qcow2` 与精确 instance directory，从基础镜像重做完整四次 reboot 和两个 checkpoint；若复现 PID 变化、进程消失或 crash/UI failure，立即保存正式证据并 fail closed，不得修复或继续。
- 第三个 worker `task098-debug-runtime-r3` 位于 `w2:t49` / `w2:p4E`，session 为 `/home/conv/.pi/agent/sessions/--home-conv-myspace-SystemUI-Gradle--/2026-09-02T13-29-25-255Z_01a0624f-6407-7474-b470-cd45d7b102a5.jsonl`；session 独立确认 `provider=joycode`、`modelId=GLM-5.3`、`thinkingLevel=high`。它按序完成 AGENTS、HANDOFF、CHARTER 和完整 STATE 读取后，在读取冻结 log tail 前执行了 dispatch 明确禁止的 `wc -l docs/orchestration/log.md`，中断了“只串行读取”的 startup 序列。Chief 拒绝 CONTRACT 并在 preflight 前退休该尝试。除该只读 line-count 命令和文档读取外，没有 scratch、git、Herdr、emulator/QEMU、ADB、build 或 tracked/untracked file mutation；tab 已关闭，独立 census 仍为无 emulator/QEMU、无 ADB device。

## 构建记录

规划及三次退休尝试均未运行 Gradle、Soong、Ninja、测试或任何构建命令。第一次与第三次尝试仅做文档读取（第三次另有一次无写副作用但违反 startup 协议的 `wc -l`）；第二次只消费已有冻结 Debug APK并执行 emulator/ADB runtime mutation。当前仍无可接受的 Debug runtime 技术结论。
