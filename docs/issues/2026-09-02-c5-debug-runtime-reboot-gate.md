# C5 Task 098：fresh Debug APK runtime reboot gate

**日期**：2026-09-02
**状态**：`DEBUG_RUNTIME_REBOOT_FAIL` — 第四个 replacement 完成合规 startup、Herdr protocol、fresh deployment 与 Checkpoint A；部署后的 Debug SystemUI 因 `android.service.dreams.Flags` old-owner reference 未重写而持续 crash-loop，Checkpoint A fail closed，reboot 4/4 与 Checkpoint B 未运行
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

### 第四个 replacement：正式技术结论

- 第四个 worker `task098-debug-runtime-r4` 位于 `w2:t4A` / `w2:p4F`，session 为 `/home/conv/.pi/agent/sessions/--home-conv-myspace-SystemUI-Gradle--/2026-09-02T13-39-20-036Z_01a06258-7764-72bf-bf2e-a286aa918b57.jsonl`；session 独立确认 `provider=joycode`、`modelId=GLM-5.3`、`thinkingLevel=high`、`HERDR_ENV=1`。它严格串行完成 frozen startup，CONTRACT 获 Chief 接受，并在首次 operational Herdr action 前完整读取 `herdr --skill`、查询实际使用命令的 exact help、记录 caller workspace `w2` / tab `w2:t4A` / pane `w2:p4F`。因此本次结果是 Task 098 的首个合规技术 authority。
- Preflight 在 `HEAD == origin/main == 09d2314a585d0f561ccc4cedb9df05ed196a7619`、clean worktree 上通过；Task 096/097 closure 均为 ancestor。冻结 APK 和 `super.img` 的 size/SHA 均精确匹配，初始 emulator/QEMU/build census 为零，ADB 无设备。证明无 owner 后，仅删除授权的五个 generated 顶层 `.qcow2` 与精确 instance directory，并在 dedicated service tab `w2:t4B` / pane `w2:p4G` 启动 fresh emulator。
- 本次完成 reboot `3/4`：permission-baseline reboot、disable-verity reboot、deployment cold boot。只授予 `BLUETOOTH_CONNECT` 与 `READ_CONTACTS`；stock SHA 为 `d0e36b33a5170c44b092da00efbf3e0aced2b8dbc5862b2fc3d088d3b77a5e25`，当前运行单独证据记录 stock PID `842` 且 crash buffer 为空。随后建立五个 durable overlay（部署前 scratch total `595496` KiB、available `526204` KiB），按 staged SHA、同文件系统 temp 与 atomic `mv` 部署冻结 Debug APK，恢复 `root:root` / `0644` / `u:object_r:system_file:s0` 并清理 oat/dalvik cache。部署后 target SHA 与 host SHA 均为 `f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`，`pm path` 指向 `/system_ext/priv-app/SystemUI/SystemUI.apk`。
- Checkpoint A 的完整 11×30 秒窗口正式失败：PID 依次为 `6533, 8217, 9871, empty, 13199, 14854, 16539, 18176, empty, 21495, 23143`；所有非空样本 elapsed 均为 `00:00:00`，从未形成单一稳定 PID，也未达到 ≥300 秒。deployment reboot 前已清空的 fresh crash buffer 保存为 `checkpointA-crash.txt`：13,716 行、1,812,966 bytes、622 个 `FATAL EXCEPTION`、622 个 `NoClassDefFoundError`。首个 fatal 为 21:49:50.182、PID 849、thread `wmshell.main`，在 `com.android.wm.shell.keyguard.KeyguardTransitionHandler.onInit(KeyguardTransitionHandler.java:155)` 命中 `Landroid/service/dreams/Flags;`。
- 结论严格限定为：一个未重写的 `android.service.dreams.Flags` old-owner runtime reference 到达设备。authoritative AOSP `repackaging.txt:350` 为 `rule android.service.dreams.Flags com.android.internal.hidden_from_bootclasspath.android.service.dreams.Flags`。本任务没有执行修复或额外根因诊断，也不泛化为“设备缺少该类”。
- 按 fail-closed 边界，reboot 4/4、Checkpoint B、两组 layout 与两组视觉截图均为 `NOT_RUN_DUE_CHECKPOINT_A_FAIL`。失败后的 `service call statusbar 1` 仅为 fail-probe，即使返回 Parcel 也不是 statusbar gate PASS。最终状态为 **`DEBUG_RUNTIME_REBOOT_FAIL`**；Release runtime 仍阻塞，必须先由独立任务完成 bounded 诊断与后续获批修复。
- 证据偏差如实保留：evidence root 混有先前退休尝试的 stale 文件（包括 `RETIREMENT.txt`、旧 `preflight.txt`、旧 `checkpointA-pid.log`，以及内容时间戳为 21:14 的旧 `stock-baseline.txt`）；本次 preflight authority 位于 `preflight/`，运行证据以 21:45–21:56 的当前 phase files 与单独 `stock-pid.txt` / `stock-sha.txt` / `stock-crash.txt` 为准。`reboot3.txt` 错读不存在的 `ro.boot.boot_id`，因此 PRE/POST 字段为空；仅捕获 post-reboot `/proc/sys/kernel/random/boot_id` `0491a5ec-6fc8-496e-b9af-565107660e79`，uptime reset、完整 PID window 和 622 条 fresh fatal/NCDFE 是正式失败 authority。
- worker 未运行 Gradle/Soong/Ninja、未 rebuild、未修复、未修改 tracked files。按 frozen FAIL stop state，`emulator-5554`、verity-disabled overlays 与部署后的 Debug APK 保持运行供 Chief 验收；不能据此继续 ADB、reboot 或试修。

## 构建记录

本任务第四次合规执行仍未运行 Gradle、Soong、Ninja、测试或任何构建命令；它只消费冻结的 Task 096 Debug APK并完成 runtime deployment。最终技术结论为 `DEBUG_RUNTIME_REBOOT_FAIL`，而不是 build failure。前三次退休尝试的流程事实保持不变。
