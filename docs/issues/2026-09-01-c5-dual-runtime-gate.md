# 2026-09-01 — Task 075 / Phase C5: 双 runtime 门（17 镜像模拟器重建 + Debug/Release 运行时验证）

> Worker: task075 (herdr pane, GLM-5.3)。Brief: `docs/orchestration/tasks/075-c5-dual-runtime-gate.md`。
> 前置采信（chief 已核实）：构建侧全绿（Debug 211,710,774 B / Release 45,030,130 B）、pytest 310
> passed、对齐 strict exit 0、指纹 24/24 MATCH；17 镜像位于
> `aosp/out/target/product/emu64x/`（8-27 13:05 产物），本任务**不触发任何 AOSP 构建**。

## 背景与目标

Phase C5 收官门：在 **AOSP-17 emu64x 镜像**上从既有 prebuilt 拉起 goldfish 模拟器，重跑 16 时代
七门（pytest / duplicate classes / 对齐 strict / manifest-dex 闭包 / clean build+sha 台账 /
部署前健康快照 / 部署+运行时验证）与 Release 四项准入（0 FATAL / 窗口在屏 / dumpsys 响应 /
稳定 ≥5min），产出 `DEBUG_RUNTIME_PASS 17` / `RELEASE_RUNTIME_PASS 17` 判定与 C6 移交材料。

## 环境初始状态（worker 自查，2026-08-31 15:31）

- git tree clean @ `7384a100`（task075 dispatch brief）。
- `adb devices`：空（无模拟器实例；`/tmp/acloud_gf_temp` 不存在 → 按 runbook 重建）。
- 17 镜像在位：`system-qemu.img` 1.9G、`super.img`、`userdata` 等；`VerifiedBootParams.textproto`
  为干净原版（仅 vbmeta 参数，无 `verifiedbootstate=orange` 追加 → 无 runbook 事实 6 boot-loop 风险）。
- 既有 APK（chief 8-31 构建）：debug 211,710,774 B / release 45,030,130 B（C4c 初值 sha
  `c74d13fb…`）。
- 内存纪律（C4c 环境教训）：空闲 Gradle daemon 18.9G + Kotlin daemon 6G 常驻（30G RAM 仅 ~2G 可用）
  → 长构建前双杀 daemon + `--max-workers=4`。
- kvm 组 OK（991）；/tmp 15G 可用。

## 证据台账

（所有输出为真实命令结果）

### Gate 1 — pytest

`uv run pytest tools/tests/ -q` → **PASS**：`310 passed, 4 warnings, 151 subtests passed in 72.72s`。

### Gate 2 — checkDebugDuplicateClasses

`./gradlew :app:checkDebugDuplicateClasses --console=plain --max-workers=4` → BUILD SUCCESSFUL
（UP-TO-DATE）；再 `--rerun-tasks` 强制执行 → `> Task :app:checkDebugDuplicateClasses` /
BUILD SUCCESSFUL（scratch 执行零重复类；gate 5 clean 构建内亦再执行一遍）。

### Gate 3 — 对齐 --strict

`uv run python tools/check_source_alignment.py --strict` → exit 0：MISSING=0 / MISPLACED=0 /
EXTRA=0 / RES-EXTRA=0；MODIFIED=1（CONV 标记已知项）、RES-MODIFIED=87（已知存量，strict
不卡 MODIFIED）。

### Gate 4 — manifest-dex 闭包

对部署产物（clean 重建 APK）跑 `uv run python tools/check_manifest_dex_closure.py --apk
app/build/outputs/apk/debug/app-debug.apk` → **PASS**：`DEX_FILES=24`、
`DEFINED_CLASSES=94893`、`MANIFEST_ENTRY_CLASSES=113 (present=111 alias=2 missing=0)`、
`RESULT=PASS`（alias：DemoMode、WifiDebugdingActivityAlias 均按 targetActivity 校验）。
（对 chief 8-31 增量 APK 先跑过一次，同为 24 dex / 94,893 classes / missing=0。）

### Gate 5 — clean assembleDebug + APK sha 台账

**clean 前存量 APK**（chief 8-31 14:36 增量构建）：211,710,774 B，sha256
`ec342e2d0df4d914bd44ab4f1a1f32fd1b8734b1eed000d46e3237f7d3d91e0f`。

**clean 重建 #1**：`./gradlew clean :app:assembleDebug --console=plain --max-workers=4` →
BUILD SUCCESSFUL in 3m 58s（290 tasks: 289 executed）→ APK **193,890,789 B**，sha256
`a8bab0f6761d7c721c6b0c0624c2776c50111150c0480f07e4869cdad97234b7`。

**clean 重建 #2**（确定性复核）：再跑一次同命令 → BUILD SUCCESSFUL in 3m 13s → 字节
完全一致（193,890,789 B / `a8bab0f6…`）。**Debug clean 构建可复现。**

**观察（如实记录，供 chief 裁决）**：Debug APK 尺寸在三次记录间漂移——199,845,582 B
（task073/C4b 时代 chief 增量复验）→ 211,710,774 B（C4c R6 时代 chief 增量构建）→
193,890,789 B（本任务 clean 重建，两次可复现）。增量 vs clean 差 ~17.8MB。CURRENT_STATE
既已声明"APK sha 台账随 C5/C6 重算"，本任务以 clean 产物 `a8bab0f6…`（193,890,789 B）
为 17 基线 Debug 台账值部署验证。gate 4 闭包在 clean 产物上重跑 PASS。

### Release 构建（clean 台账 + 确定性）

- `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew :app:assembleRelease
  --console=plain --max-workers=4` → **BUILD SUCCESSFUL in 4m 34s**；APK
  **45,030,130 B**，sha256 `7fadce6dedf5b426626bb628e7a3ffe0da6454e08ac40e98275bd69181b36478`。
- 确定性：`:app:minifyReleaseWithR8 --rerun-tasks`（263/263 executed，4m 28s）→ 重新
  assemble → 字节一致（`7fadce6d…`）。**Release clean 构建可复现。**
- 观察与 Debug 同类：C4c 记录的 release 初值 `c74d13fb…`（同为 45,030,130 B）系 8-31
  14:58 增量态构建，与本 clean 值 `7fadce6d…` 同尺寸不同字节；增量态与 clean 态产物
  不等价（C4c 自身的 rerun-tasks 复验在其增量目录内自洽）。17 基线以 clean 值为准。

### 静态健全性（两 APK）

- `unzip -t`：debug/release 均 CLEAN（No errors detected）。
- `apksigner verify -v`：两者均 `Verifies`，v2 scheme **true**（v1/v3 false），
  signer cert SHA-256 `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`
  （Android platform，debug/release 同一签名配置）。

### 构建环境事件（如实记录）

1. **daemon 内存纪律**（C4c 教训执行）：空闲 Gradle daemon 18.9G + Kotlin daemon 6G
   常驻，双杀后 26G 可用；重构建全程无 OOM。
2. **JdkImageTransform jlink 故障**：杀 daemon 后新 daemon 起在我 shell 的
   JAVA_HOME（mise java 25）下，`jvmToolchain(21)` 的 toolchain 自动探测选中
   `~/.vscode-server/extensions/redhat.java-1.55.0/…/jre/21.0.11`（JRE，jlink 缺失）
   → `:SystemUI-animation:compileReleaseJavaWithJavac` 失败。修复：用
   `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64` 重启 daemon（与 chief 历次构建同
   JVM；纯环境参数，未改任何工程文件）后 release 全绿。**后续 Gradle 调用一律带此
   JAVA_HOME。**

### Gate 6 — 部署前模拟器健康快照

模拟器按 runbook 从 17 prebuilt 拉起（herdr tab `w2:t2M`/pane `w2:p2S`，label emulator，
`-ports 5554,5555`，三环境变量 + 预 touch 日志文件，textproto 未动）：

- `adb wait-for-device` 后 `sys.boot_completed=1`；`ro.kernel.qemu=1`；
  `ro.build.fingerprint=Android/sdk_phone64_x86_64/emu64x:Baklava/CP2A.260605.016/eng.conv:userdebug/test-keys`
  （17 镜像指纹与 16 时代 MAIN 不同，brief 预期）；`ro.boot.verifiedbootstate=orange`（镜像自带）。
- stock SystemUI PID 1018（elapsed 01:21）；`logcat -b crash -d` 0 行。
- SystemUI 自有窗口在屏（`ScreenDecorOverlay`/`ScreenDecorOverlayBottom`，
  package=com.android.systemui，uid 10123）。
- stock APK：`/system_ext/priv-app/SystemUI/SystemUI.apk`，45,481,797 B，sha256
  `d0e36b33a5170c44b092da00efbf3e0aced2b8dbc5862b2fc3d088d3b77a5e25`（与 16 时代 stock
  `dd1ff45a…` 不同，17 镜像预期）。
- verity 链按规程执行：`adb root` → `adb disable-verity`（"enabling overlayfs"）→ reboot
  → boot_completed=1 → root → `su 0 mount -o remount,rw /system_ext`。

**Gate 6：PASS。**

### Gate 7 — Debug 部署 + 运行时验证：**BLOCKED（ENOSPC，结构性容量不足）**

按 brief 风险表流程执行到停工点：

1. **df 观测（部署前）**：`/mnt/scratch`（f2fs，dm-5，backing=vda2=super）
   **87,116 KB 总 / 46,288 KB used / 40,828 KB avail**。overlay 上层目录实际内容仅 14K/棵
   （du 实测）——46MB "used" 是 f2fs 保留/元数据，非文件占用。
2. **force-stop + kill SystemUI（Incident 1 规定步骤）**：执行后 df **不变**（40,828 KB
   avail）——确认非 inode 占用问题（fresh overlay，无已部署 APK）。
3. **staged 部署尝试（完整规程，含 sha 门禁）**：
   - push `/data/local/tmp/SystemUI.apk`：sha 门禁 MATCH（`a8bab0f6…`，193,890,789 B）。
   - `su 0 cp /data/local/tmp/SystemUI.apk /system_ext/priv-app/SystemUI/.tmp-SystemUI.apk`
     → **`cp: short write: No space left on device`**（cp_rc=1），残留截断文件
     **41,750,528 B**（PITFALLS 14.2 复现：toybox cp 截断留残）；scratch 变 100%。
4. **清理恢复（Incident 1 流程）**：rm 截断文件 + staging + sync → scratch 回
   54%（40,820 KB avail）；reboot → boot_completed=1，stock SystemUI PID 869，
   crash buffer 0 行，`/system_ext/priv-app/SystemUI/SystemUI.apk` 原样（d0e36b33，
   45,481,797 B）。设备停在健康 stock 态，等 chief 裁决。

**结论：Debug 部署被 17 镜像 scratch 容量硬阻断**：193,890,789 B > 总容量 89.2 MB ——
即使清空 f2fs 保留也绝无可能放下。Release 同被阻断：45,030,130 B > 40,807,872 B avail
（差 ~3.2MB；总容量 89.2MB 可容纳，但 f2fs 保留不可释放）。

### 根因分析（只读调研，AOSP 源码证据）

- scratch 设备：dm-5（f2fs，`/mnt/scratch`），`/sys/block/dm-5/slaves` = **vda2**
  （= super.img，1,895,825,408 B）。即 adb-remount overlay 的上层落在 **super 分区剩余空间**。
- kernel.log：`init: [libfs_mgr] Created logical partition scratch on device /dev/block/dm-5`
  （boot 时自动创建）。
- AOSP 源码 `system/fs/fs_mgr/fs_mgr_overlayfs_control.cpp`：
  - `fs_mgr_overlayfs_create_scratch` 先试 **/data 背书 scratch**（ImageManager，默认
    2 GiB，可用 `fs_mgr.overlayfs.data_scratch_size_mb` 调）——本设备未走通（需 /data
    fiemap 可靠 pinning），回退 super；
  - `CreateDynamicScratch`："Take half of free space, minimum 512MB or maximum free -
    margin"——即 scratch 尺寸 = super 剩余空间。
- **16 vs 17 差异**：16 时代 emu64x super 有 ~261MB 剩余 → scratch 261MB（16 部署 164MB
  Debug 可行）；17 镜像（8-27 重建）system 各分区占满 super（dm-0..dm-4 总和 ≈ vda2
  容量，仅剩 ~1MB slack + 已划入 scratch 的 87MB）→ scratch 只有 87MB。**这是镜像
  结构属性，非运行态可修复项。**

### Release 部署 + 四项准入：**BLOCKED（同根因）**

未尝试（45,030,130 B > 40,807,872 B avail，df 已排除可能性；且任务序为 Debug 先行）。
构建侧 Release 产物与确定性证据已在上方台账（gate 5 节后）。

## 判定

- Gate 1–6：**PASS**（见台账）。
- Gate 7（Debug 部署+运行时）：**BLOCKED — 17 镜像 scratch 容量结构性不足**
  （ENOSPC 实证已归档；非 Incident 1 类 inode 占用，force-stop+kill 无效）。
- Release 四项准入：**BLOCKED（同根因）**。
- **`DEBUG_RUNTIME_PASS 17` / `RELEASE_RUNTIME_PASS 17` 均不可宣告。**

## RED LINE REPORT（需 chief/用户裁决点）

触发条件：Debug APK overlay ENOSPC（brief 风险表预设停工点，且与 Incident 1 不同类：
容量结构性不足而非 inode 占用）。已验证步骤：df 观测 → force-stop+kill（无效）→
完整 staged 部署尝试（sha 门禁抓到 ENOSPC 截断）→ 清理 → 设备恢复健康 stock 态。
**等待裁决，未自行尝试任何分区法。**

可选路线（均需授权，worker 未执行）：

| 路线 | 说明 | 障碍 |
|---|---|---|
| A. 接受阻断 | C5 runtime 门挂起，C6 延后 | 项目目标受阻 |
| B. 排查 /data 背书 scratch | AOSP 原生支持（默认 2GiB，`fs_mgr.overlayfs.data_scratch_size_mb`）；需查本机 /data f2fs pinning 为何未走通 | 涉及设备属性/挂载操作，需授权与调研 |
| C. 重建 17 镜像留 super 余量 | AOSP 侧构建参数调整 | **本任务明令不建 AOSP**；需另派任务 |
| D. 设备上改 super 元数据扩 scratch | 能解决但属于 brief 明令禁止的“自行改分区法” | 禁止 |

（注：fastboot 重刷 system_ext 或镜像拼接均属“创建/替换 AOSP 产物”，亦在 May NOT 清单内。）

## Next steps（C6 移交预备，受阻断影响）

- 构建侧台账已齐：Debug clean 产物 `a8bab0f6…`（193,890,789 B，两次可复现）、
  Release clean 产物 `7fadce6d…`（45,030,130 B，rerun-tasks 可复现）、v2 签名/证书一致、
  闭包 PASS、对齐 strict PASS、pytest 310+151。C6 的 manifest 快照/tag/README 素材
  可从本台账超源。
- 增量 vs clean APK 字节不等价现象（199.8M/211.7M/193.9M 漂移；release 同尺寸不同
  sha）建议 chief 知悉并裁定台账口径（本任务按 CURRENT_STATE 预告采用 clean 值）。
- swapfile/内存纪律：本轮无 daemon OOM（预双杀 + `--max-workers=4`；另记录 JdkImageTransform
  jlink 事故与修复：Gradle 必须在 `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64` 下起
  daemon，否则 jvmToolchain(21) 探测会选中 vscode 破 JRE）。
- 模拟器现态：herdr tab `w2:t2M` 运行中，设备健康（stock SystemUI，verity disabled，
  overlay 54%），可留作 chief 现场复验；实例随宿主机重启蒸发（runbook 事实 1）。

## 待解决问题

1. **C5 runtime 双门被 17 镜像 scratch 容量阻断（主阻断，等 chief 裁决路线 A–D）**。
2. 增量 vs clean APK 字节不等价（观察项，供台账口径裁决）。
3. task074 移交的三个 runtime 初验点（displaylib 双 dagger 路径、parcelize、aconfig
   R8 语义）均因部署被阻未能在设备上验证，随阻断解除后一并补。

---

## Route B（用户批准，2026-08-31 chief 下达）：/data scratch 诊断修复 + 16 时代溯源

**授权边界**：设备级诊断与修复、全部操作可逆、走 AOSP 原生机制（gsid ImageManager
/data-backed scratch）、不重建镜像、**不对 AOSP 镜像写任何字节**。每步操作前先存原始
状态；每步发现立即写入本节；超 90 分钟未解决则停工写证据汇总上报。

chief 已核实的证据基础（采信）：
- fs_mgr 路径：`fs_mgr_overlayfs_create_scratch` 先 `CreateScratchOnData`（ImageManager，
  `FilesystemHasReliablePinning` 对 ext4 一律支持；libfiemap utility.cpp L151-160 只对 F2FS
  做额外检查），失败才回退 super `CreateDynamicScratch`。我们落到回退路径 →
  **CreateScratchOnData 失败了**。
- 理想 /data scratch 尺寸 = min(super 物理大小, /data 空闲×0.85)（GetIdealDataScratchSize），
  本机可达 GB 级。
- 本机 gsid 存在且 run-startup-tasks 成功（dmesg 证据）、/metadata 存在（ext4, vdd1）。

### B-Step 1：CreateScratchOnData 失败原因定位

（诊断中）

### B-Step 1 结论：CreateScratchOnData 失败根因 = **gsid 从未运行（gsiservice 不可达）**

证据链（全部实测/源码实证）：

1. **运行期证据**：kernel.log boot-1 期 119.864s（= 我 16:04 `adb disable-verity` 的
   overlayfs setup，caller pid 2607 uid=0 sid=u:r:su:s0 = adb-root adbd）：
   `servicemanager: ... Since 'gsiservice' could not be found trying to start it as a
   lazy AIDL service`。
2. **gsid 定义**（设备 `/system/etc/init/gsid.rc` + AOSP 源码）：`service gsid` 是
   **`oneshot` + `disabled`**——boot 只跑 `exec_background gsid run-startup-tasks`
   （无 DSU 时立即退出），主 daemon（无参数 → `GsiService::Register("gsiservice")`
   + joinThreadPool 驻留，daemon.cpp L49-74）**没有任何 boot trigger 自启**。
   当前 `ps -A | grep gsid` 空、`getprop init.svc.gsid` 空——从未启动。
3. **运行期调用链**（源码）：`adb disable-verity` → remount 工具 main（fs_mgr_remount.cpp
   L440-452）→ `SetupOrTeardownOverlayfs(true)` → `fs_mgr_overlayfs_setup` →
   `fs_mgr_overlayfs_setup_scratch` → `fs_mgr_overlayfs_create_scratch` →
   **`CreateScratchOnData`**：
   - `FilesystemHasReliablePinning("/data")`：/data 是 **ext4** → 无条件 `supported=true`
     （utility.cpp FilesystemHasReliablePinning：非 F2FS 直接 true）——**不是失败点**。
   - `IImageManager::Open("remount", 10s)`：remount 工具链接的是 **binder 版
     libfiemap**（Android.bp：libfiemap_binder_defaults 默认；passthrough 仅限无 binder
     环境）→ `GetGsiService()` → `waitForService("gsiservice")`（libgsid.cpp）→
     **gsid 未运行 → 等待失败 → Open 返回 null → CreateScratchOnData false** →
     `LOG(WARNING) "Failed to allocate scratch on /data, fallback to use free space on
     super"` → `CreateDynamicScratch` → 87MB super scratch。
4. **boot 期必然失败**：first-stage init（selinux.cpp SetupOverlays → exec
   overlay_remounter；scratch 在 kernel 1.34s 创建，早于 gsid.rc 解析 36.8s）连
   servicemanager 都没有 → /data 路径无解 → super。
5. **/metadata/gsi 残留**：`/metadata/gsi/remount/` 存在但**空**（无 lp_metadata）——
   无历史残留干扰（可排除 chief 假设之一）。
6. `fs_mgr.overlayfs.data_scratch_size_mb`（kDataScratchSizeMbProp）语义：
   **CreateScratchOnData 里自定义尺寸**（GetUintProperty×1MiB；未设则
   `GetIdealDataScratchSize()` = min(super 物理大小 1.9GB, /data 空闲×0.85)，再退 2GiB）。
   它只是尺寸旋钮，**不解决 gsid 可达性问题**。
7. **本机 gsid 健康**：gsid 二进制在位，`run-startup-tasks` 成功（boot 日志 42.1s
   "no DSU" 正常退出）——手动 `start gsid` 应可拉起。

### B-Step 2：16 时代溯源（用户点名）——16 也是 super 路径，261MB 来自 16 super 剩余空间

- 16 时代文档证据：task 058（2026-08-25）"261 MB f2fs scratch overlay"；
  task 055 "system_ext overlay 261M 总量，替换前仅剩 6.4M"。
- **路径判定（硬推理）**：/data 路径 scratch 尺寸 = min(super 物理大小, /data 空闲×0.85)
  ≈ min(1.9GB, ~9.4GB×0.85) ≈ **1.9GB**，不可能是 261MB。261MB 只能来自
  `CreateDynamicScratch` 的 super 分配（"half of free space, minimum 512MB"：
  free<512MB 且初始 size=0 时 = 全部 free ≤512MB）。**16 时代同样走 super 回退路径**，
  16 的 emu64x super.img 当时剩 ~261MB 未分配。
- **为什么 16 放得下、17 放不下**：16 super 剩 261MB ≥ 16 Debug APK 164MB（余量 97MB，
  但满态时有 Incident 1 的 inode-ENOSPC 坑）；17 镜像 8-27 重建后 system 系分区涨满
  super（dm-0..4 合计 ≈ vda2 总量）→ 动态 scratch 只分到 87MB（f2fs 保留后 avail 40MB）
  < 17 Debug APK 193.9MB / Release 45MB。**同一机制、同一路径，差在 super 剩余空间。**
- 16 时代未留 mount/dm 记录（issue 文档无 /mnt/scratch mount 行），上述判定基于尺寸
  数学 + 当前 17 源码同构行为（16/17 fs_mgr 逻辑一致）。

### B-Step 3：最小可逆修复计划（AOSP 原生机制，不写 AOSP 镜像字节）

宿主镜像安全前提（已核实）：emulator `-read-only` 为所有磁盘建了 **qcow2 写前覆盖层**
（`out/.../emu64x/*.img.qcow2`，8-31 16:01 生成，~196KB 薄层）——设备侧 super 元数据/
userdata 的全部写入落在 qcow2，**AOSP 8-27 原始镜像零字节改动**（system-qemu.img mtime
仍 Aug 27 13:05）。设备侧 super 元数据编辑（增删 scratch 逻辑分区、overlays-active
flag）与已被授权的 disable-verity 属同一机制类。

执行序列（每步前存档状态）：

1. `adb enable-verity`（AOSP 原生 teardown 入口：fs_mgr_overlayfs_teardown → 卸
   overlay + DestroyLogicalPartition("scratch") + SetOverlaysActiveFlag(false) +
   SetVerityState(true)）→ reboot → 验证：verity enabled、无 overlay、super scratch
   消失。当前设备处于 stock 态，此步无损。
2. boot 后 `adb root` + `su 0 start gsid`（手动拉起被 disabled 的 oneshot 服务）→
   验证 `service list` 含 gsiservice。
3. `adb disable-verity`（此时 gsid 活着）：SetVerityState(false) →
   SetupOrTeardownOverlayfs(true) → CreateScratchOnData 走 binder→gsid →
   **在 /data 上建 ~1.9GB scratch image**（`/data/gsi/remount/scratch.img` +
   `/metadata/gsi/remount/lp_metadata`）→ reboot。
4. boot 后验证 first-stage 映射：`MapScratchPartitionIfNeeded` → `ScratchIsOnData()`
   （lp_metadata 在）→ passthrough ImageManager `MapAllImages`（block-level dm-linear，
   无需 /data 挂载）→ /mnt/scratch ≈ 1.9GB、overlay 在屏。
   - **已知风险点**：fiemap extents 记录的是 /data fs 的块设备 dm-6（vdc 的 dm 包装，
     latemount 后才存在）；若 first-stage 映射失败 → overlay 不在 boot 挂载 → 退路为
     运行期 `start gsid` + `adb remount`（运行期映射），reboot 持久性如实记录并上报。
5. overlay 容量 ≥ APK 尺寸后 → 回到 Gate 7 标准部署规程（staging + sha 门禁）。

### B-Step 3 执行记录（含两个新根因）

**根因 #2（gsid 可达后暴露）：emu64x userdata 裸盘无 by-name 符号链接。**

16:47 实验（gsid 已拉起）：disable-verity 仍回退 super，gsid 日志给出确切失败点：
```
E gsid: [libfs_mgr] realpath: /dev/block/by-name/vdc: No such file or directory
E gsid: Unable to complete device-mapper table, unknown block device
E gsid: Error creating device-mapper node for image scratch
```
源码链：`GetBlockDeviceForFile`（fiemap_writer.cpp L171）把文件 st_dev 穿透 dm 栈
（DeviceMapperStackPop：dm-6"userdata"→slave **vdc**）→ `GetDevicePathForFile`
（utility.cpp L79）的 kUserdataDevice 特判（`/dev/block/by-name/userdata`）在本机
stat 失败（链接不存在）→ lp_metadata 记 basename **"vdc"** → 映射时
`PartitionOpener::GetPartitionAbsolutePath`（partition_opener.cpp L44）只认
`/dev/block/by-name/<name>`，**仅 mmcblk\* 有 /dev/block 回退** → ENOENT。
emu64x 的 userdata 是 qemu 裸 virtio 盘（vdc，无 GPT → 无 PARTNAME → ueventd 不建
by-name 链接；fstab 直接硬编码 /dev/block/vdc）。现有 by-name 链接仅
metadata/super/vbmeta/vda/vdd（全部来自 GPT 命名分区）。**16 时代同样没有此链接，
但从未走到 /data 路径（根因 #1 挡在前面），故从未暴露。**

**根因 #3（gsid 生命周期）**：gsid 用 LazyServiceRegistrar 注册（无客户端数秒后
自退 "Unregistering gsiservice"），且 `service gsid` 为 disabled+oneshot、无 boot
自启 trigger——**每次 reboot 后 gsid 必然不在**，只能运行期手动 `start gsid`。

**运行期修复实证（2026-08-31 16:57，全链走通）**：干净 boot（enable-verity 拆净
overlay）→ `adb root` → `su 0 start gsid`（等注册）→ `su 0 ln -s /dev/block/vdc
/dev/block/by-name/userdata`（+vdc，/dev tmpfs 可逆，重启即失）→ `adb
disable-verity`：
```
/data/gsi/remount/scratch.img + scratch.img.0000（1,895,825,408 B fiemap image）
/metadata/gsi/remount/lp_metadata（4,772 B）+ scratch.status（dm:scratch）
/mnt/scratch = dm-7（slave=vdc），1,849,344 KB 总 / 1,748,884 KB 可用  ← 1.85GB！
```
lp_metadata 记录设备名 "userdata"/"vdc"（依赖运行期手工链接）。

**持久性缺口（代码链已证实，reboot 实验见下）——/data scratch 无法跨 boot 存活：**

1. first-stage init 链接的是 **libfs_mgr（passthrough libfiemap）**（fs_mgr
   Android.bp L192-208 明注：libfs_mgr 用于 recovery/first-stage-init，
   libfs_mgr_binder 用于运行期）；`MapScratchPartitionIfNeeded` →
   `MapAllImages` → `MapWithDmLinear` → PartitionOpener("userdata") →
   `/dev/block/by-name/userdata` —— **/dev 是 tmpfs，重启后手工链接消失，且
   emu64x 无任何持久机制生成它**（无 PARTNAME、无 ueventd symlink 规则、
   ueventd.rc/system 全 RO）。
2. 失败后 boot 回退到 super scratch（87MB，super 元数据里的旧分区仍在）→
   overlay 挂在 87MB 上 → 部署在 /data scratch 的 APK 不可见。
3. 就算运行期重启后再 `start gsid`+建链接+remount：`CreateScratchOnData` 对
   "已存在但未映射"的 image 走 `MapImageDevice`（partition_exists=false）→
   `fs_mgr_overlayfs_setup_scratch` 调 **`MakeScratchFilesystem` 重新格式化** →
   **部署产物被抹掉**（fs_mgr_overlayfs_control.cpp L527-580 + L615-655 实证）。
4. raw 直写 system_ext 不可行：**原始 system_ext ext4 分区 100% 满**
   （235,804 KB 总 / 728 KB 可用，AOSP right-sized）；扩分区=改 super 元数据
   分区大小=禁区。
5. 运行期 `adb remount`（全分区）在 verity-on boot 会被 /system 的 dm-verity +
   stale `ro.boot.veritymode` 短路（early return，不挂 overlay）；带分区参数
   `remount system_ext` 可绕过（/system_ext 本 boot 无 verity wrapper）——见下节
   运行期部署实验。

### B-Step 4：运行期部署实验（/data scratch 上，含 Debug 与 Release）

**运行期 overlay 挂载**：remount 工具在本 boot 被两个模拟器 quirk 卡死
（①stale `ro.boot.veritymode` 使 SetVerityState 恒 want_reboot → 全分区 remount
early-return；②fstab 双条目 erofs/ext4 使 `remount system_ext` 的
IsRemountable 类型不匹配 → "Invalid partition"）。改用与 fs_mgr boot 日志**完全
相同的 overlay 挂载参数**手动挂 `/system_ext`（lowerdir=/system_ext，
upperdir=/mnt/scratch/overlay/system_ext/upper —— upper/work 目录由 disable-verity
的 AOSP 流程创建，挂载后 `overlay on /system_ext (rw,...)` 与 boot 期形态一致，
umount 即可逆）。

**Debug APK（`a8bab0f6…`，193,890,789 B）运行期部署 + 验证 —— 全绿**：

- 标准规程：push（sha MATCH）→ staged cp（**无 ENOSPC**，scratch 用量 6%→16%）
  → sha 门禁 MATCH → 原子 mv → root:root 0644 u:object_r:system_file:s0 →
  清 oat → force-stop 重启 SystemUI。
- `am force-stop` 后 SystemUI 以新 APK 重启（PID 857）；**PID 857 稳定
  10×30s**（17:08:27–17:12:57，>5min）。
- `logcat -b crash -d`：**0 行**；全 logcat FATAL/NCDFE：**0**（grep 命中仅为
  自身命令回显）。
- `dumpsys window windows`：**StatusBar、NotificationShade、Taskbar、
  ImageWallpaper、ScreenDecorOverlay** 全在屏。
- `dumpsys statusbar`（小写）响应。
- **结论：C4b 闭合产出的 17 Debug APK 在 17 镜像上运行时完全健康（runtime-only
  部署形态）。**

**Release APK（`7fadce6d…`，45,030,130 B）运行期部署 —— crash-loop，FAIL**：

- 同规程部署（sha 门禁全过，on-device `7fadce6d…`，权限正确）。
- kill 重启后 SystemUI **crash-loop 后死亡**（10×30s `pidof` 全空）。
- `logcat -b crash -d`：**85 个 FATAL，全部同一签名**（17:21:55 起，wmshell.main
  线程）：
  ```
  java.lang.RuntimeException: Field educationViewedTimestampMillis_ for
    com.android.wm.shell.desktopmode.education.data.WindowingEducationProto not found.
    Known fields are [DEFAULT_INSTANCE, PARSER, bitField0_, educationDataCase_, educationData_]
  Caused by: java.lang.NoSuchFieldException: No field educationViewedTimestampMillis_
    in class Lcom/android/wm/shell/desktopmode/education/data/WindowingEducationProto;
    (declaration ... appears in .../SystemUI.apk!classes2.dex)
    at com.google.protobuf.MessageSchema.reflectField → newSchema → Protobuf.schemaFor
    at com.google.protobuf.GeneratedMessageLite.hashCode
    at androidx.datastore.core.DataStoreImpl$readDataOrHandleCorruption$2$1...
  ```
- **dex 对照取证（决定性）**：
  | 产物 | proto 字段声明 | accessor 方法（get/set/has/clear） |
  |---|---|---|
  | Soong stock 17（minified、设备上健康）classes3.dex | **有**（field table：`name : 'educationViewedTimestampMillis_'`） | 无（同样被删） |
  | 我方 Debug（unminified）classes21.dex | 有 | 有（全套） |
  | 我方 Release（minified）classes2.dex | **无**（仅剩 const-string 字面量） | 无 |
- **机制**：protobuf-lite 生成代码以 `buildMessageInfo`/字符串常量把字段名交给
  运行时 `MessageSchema.reflectField` 反射；accessor 方法被 R8 死代码消除后，
  字段失去唯一 Java 引用 → 我方 R8（AGP 9.3.1 / R8 9.3.16）把字段本体 shrink 掉
  → 运行时 `NoSuchFieldException`。Soong 的 R8 同样删了 accessor 却保留字段
  （版本/行为差异），故 stock 健康。**与 C4c 移交风险点 #4 的预测精确吻合**
  （"若 C5 出现反射类缺失，优先核对 proguard flags 与 AOSP 17 差异"）。
- **修复方向（build 侧，超出 task075 权限，留 chief 派发）**：为
  GeneratedMessageLite 子类加字段 keep，例如
  `-keepclassmembers class * extends com.google.protobuf.GeneratedMessageLite { <fields>; }`
  （protobuf-lite + R8 的业界标准规则；需核对 AOSP 17 侧是否有等价配置以对齐
  语义，避免过度 keep）。
- 注：观测栈里 SnackbarHostKt/ResultKt 等错位帧是 R8 横向合并的栈映射假象
  （16 时代 Round 3 同类），非因果。

### B-Step 5：reboot 持久性实证（两轮）

1. **Debug 部署后 reboot**：`sys.boot_completed=1`，但
   `/system_ext/.../SystemUI.apk` sha 回 **stock `d0e36b33…`**（部署不可见），
   SystemUI 跑 stock；**/mnt/scratch 未挂**；且 **AOSP boot 清理把孤儿 data
   scratch 整个删除**（`/data/gsi/remount/`、`/metadata/gsi/remount/` 全空
   ——clean_scratch_files/overlayfs teardown 路径的预期行为）。
2. Release 实验 reboot 同前（设备已复原 stock 基线：sha d0e36b33、PID 850、
   crash 0、无 overlay、无 scratch、目录清空）。

### Route B 总结论

- **运行期 /data scratch 修复成功且完整实证**（1.85GB；Debug 全绿；Release 暴露
  真实 R8 crash——这本身是 C5 的核心产出之一）。
- **reboot 持久部署在 17 镜像上经设备级可逆手段不可达**（三层卡点：by-name 无
  持久来源 / first-stage passthrough 需 by-name / 运行期重建会 MakeScratchFilesystem
  抹数据；外加 AOSP boot 清理删孤儿 image）。
- **raw 直写不可行**（system_ext 100% 满）；**扩 super scratch = 禁区**。
- **Release 反射 crash 是独立于部署机制的构建侧缺陷**，需 proguard keep 修复
  （chief 派发，参照 C4c 移交 #4）。

### 供 chief 裁决的后续选项

| 选项 | 内容 | 代价/性质 |
|---|---|---|
| B1（build 修复优先） | 派发 proguard keep 修复（GeneratedMessageLite 字段）→ 重跑 C5 runtime 检验 | 小；不解决部署持久性 |
| B2（镜像侧修复） | emu64x 产品侧给 userdata 持久 by-name（ueventd symlink 规则或 GPT userdata），使 AOSP 原生 /data remount 路径跨 boot 生效 | 需改 AOSP 镜像构建；一劳永逸 |
| B3（super 余量） | AOSP 构建参数留 ≥260MB super 余量（复刻 16 时代形态） | 需改 AOSP 构建；容量仍紧 |
| B4（gate 语义） | 与用户讨论 runtime-only 部署（stop/start 语义）是否可作 17 时代 runtime 门 | 偏离 16 时代门定义 |
