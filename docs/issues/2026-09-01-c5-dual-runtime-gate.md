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
