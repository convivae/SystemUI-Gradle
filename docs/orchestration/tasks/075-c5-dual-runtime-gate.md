# Task 075 — Phase C：C5 双 runtime 门（17 镜像模拟器重建 + Debug/Release 运行时验证）

## Task Scope

**Goal**: 在 **AOSP-17 emu64x 镜像**上重建 goldfish 模拟器实例，按 16 时代七门与 release 四
项准入标准，完成 **Debug 与 Release 双 runtime 门**，产出新 APK sha 台账 + 运行时判定
（`DEBUG_RUNTIME_PASS 17` / `RELEASE_RUNTIME_PASS 17`）与 C6 移交材料。
**strictly out of scope**: Gradle 构建修复（构建侧已绿；如发现构建侧 bug，记录+上报）、
代码/资源/src 任何改动、SysUISdk、git push。

## Pre-verified Facts (chief 已核实，直接采信)

1. **构建侧已绿**（chief 2026-08-31 亲手复验）：`:app:assembleDebug` / `:app:assembleRelease`
   均 BUILD SUCCESSFUL；Debug APK 211,710,774 B；Release APK 45,030,130 B。
   pytest 310 passed；对齐 `--strict` exit 0；指纹 24/24 MATCH。
2. **17 镜像就位**：`/home/conv/myspace/aosp/out/target/product/emu64x/`（8-27 13:05 重建产物，
   `system-qemu.img`/`VerifiedBootParams.textproto`）——**不要触发任何 AOSP 构建**。
3. **ACLoud 禁用**：`acloud create` 的 Cuttlefish preflight 缺陷仍在；按 runbook 直接拉起
   prebuilt emulator。实例目录 `/tmp/acloud_gf_temp/local-goldfish-instance-1/`，重启即丢。
4. **runbook 必读**：`docs/issues/2026-08-26-emulator-relaunch-runbook.md`（三环境变量、
   touch 日志文件、**不要**改 textproto、`-ports 5554,5555`、`herdr tab` 前台拉起）。
5. **部署规程必读**：`docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md`（Step 7 +
   Incident 1/2 两个坑：overlay ENOSPC——老 SystemUI 未 force-stop 持 inode；`enable-verity`
   会掀掉 overlay——终态保持 verity **disabled**）。
6. **17 时代差异点（chief 预警）**：
   - Debug APK 211MB（16 时代 164MB）vs 261MB f2fs overlay 剩余空间——**先 df 观测**，
     先 force-stop+kill SystemUI 释放 inode；仍 ENO SPC 则**停工上报**（不自行改分区法）。
   - Release 45MB 无压力。
   - 17 镜像指纹不同（`sdk_phone64_x86_64/emu64x` userdebug，17 于 8 月构建）——预期。
   - task074 移交风险点：displaylib 双 dagger 路径运行时初验（createDisplayLibComponent 在
     DisplayService 组件启动时触发）、parcelize runtime、aconfig R8 adapter 语义。
7. **门定义（16 时代既有标准，17 重跑）**：
   - **Debug 七门**：① pytest ② checkDebugDuplicateClasses ③ 对齐 `--strict`
     ④ manifest-dex 闭包（`tools/check_manifest_dex_closure.py --apk ...`）
     ⑤ clean assembleDebug + APK sha 台账 ⑥ 部署前模拟器健康快照 ⑦ 部署+运行时验证
   - **运行时判定**（Debug/Release 同标准）：部署 survive reboot；`sys.boot_completed=1`；
     SystemUI PID 稳定 ≥5min（≥10 采样）；`logcat -b crash` 0 行；全量 logcat 零
     `FATAL EXCEPTION|NoClassDefFoundError`；`dumpsys window windows` StatusBar 窗口在屏
     （+ NotificationShade/Taskbar/ImageWallpaper）；`dumpsys statusbar` 响应（小写）。
   - **Release 附加**：对照任务 060 的四项准入（0 FATAL / 窗口在屏 / dumpsys 响应 / 稳定 ≥5min）。

## File Map

- 读写：`docs/issues/2026-09-01-c5-dual-runtime-gate.md`（新建，主记录）、
  `docs/orchestration/STATE.md`（单行）、本文件汇报段、`/tmp/acloud_gf_temp/**`；
  app 产物 sha 台账写入 issue 文档
- 只读：`docs/issues/2026-08-26-emulator-relaunch-runbook.md`、
  `2026-08-25-debug-runtime-pass-gate-suite.md`、task060 系列 issue、
  `2026-08-28-c4b-debug-compile-closure.md` §7、`2026-09-01-c4c-release-r8-closure.md` §C5 移交
- **禁改**：工程源码/资源/build 文件/tools（任何修复需求先停工上报）、AOSP 树、
  `VerifiedBootParams.textproto`（runbook 事实 6）、git push
- 模拟器拉起用独立 herdr tab（如 `w2:t-emulator`，label emulator），worker 自己一个 tab；
  `adb -s emulator-5554` 命令直接跑
- **写操作规程**（已有 PITFALLS §14）：staging `/data/local/tmp` → sha256 门禁 → 同目录
  `.tmp-` cp → sync → 原子同 fs mv → chown/chmod/chcon → 清 oat/dalvik-cache →
  重启前 on-device sha256 复验 → reboot

## 风险与兜底

| 情形 | 处置 |
|---|---|
| Debug overlay ENOSPC（211MB） | 按 Incident 1 流程：force-stop+kill SystemUI → df 复核 → 重新 staged；仍失败 → **停工上报** |
| 部署后 boot loop / SystemUI crash | **部署验证不豁免**——如实记录 FATAL 栈到 issue，报 chief；先对比 16 时代对应 FATAL 是否已修（R 系列经验） |
| kernel.log `Run /init` 反复 | runbook 事实 6 处置：`cp .bak-non-mixed` 恢复 textproto |
| emulator 起不来 | 先按 runbook 回退速查表逐项排查；两轮失败 → 上报 |
| scrcpy 截图 | `scrcpy -s emulator-5554` 可选佐证（非门禁） |

## Report Contract

1. **Status**: 八道门逐门 PASS/FAIL + 双 runtime 判定（DEBUG_RUNTIME_PASS 17 /
   RELEASE_RUNTIME_PASS 17 是否可宣告）。
2. **Evidence**: 新 APK sha256 双台账；部署前后 on-device sha256 记录；运行时判据每一项的
   命令输出摘要（boot_completed、PID 采样、crash buffer、dumpsys statusbar、window windows）。
3. **RED LINE REPORT**: 每处需用户/chief 裁决点（若有）：触发条件+已验证步骤+等待裁决。
4. **Next steps**: C6 移交：manifest 快照清单、tag 建议、README 版本声明素材、
   swapfile 撤回注意。

### AUTHORITY

- May: 启停管理模拟器与 adb；构建验证类 gradle 命令（先看 daemon 现状再跑长构建）；
  issue 文档+STATE 单行；commit（英文、明确 add 路径）
- May NOT: 改工程源码/build/tools/AOSP 树/CHARTER/`git add -A`；创建/替换 AOSP 产物；
  修改 textproto；git push；绕过 ENOSPC 用未经文档化的分区法
- 汇报对象：chief（`w2:p1`）

### 五字段

- **Authority**: 见上 May/May NOT
- **Allowed Paths**: `docs/issues/2026-09-01-c5-dual-runtime-gate.md`、`docs/orchestration/STATE.md`、
  本文件汇报段、`/tmp/acloud_gf_temp/**`、`/tmp/t075_*`
- **Forbidden Paths**: 工程源码/res/build.gradle.kts/tools/`docs/orchestration/CHARTER.md`、
  AOSP 树（只读）、`VerifiedBootParams.textproto`、git push、`git add -A`/`.`
- **Acceptance**: 七门+Release 四准入如实记录；双 runtime 判定附完整证据；issue 文档完整；
  无越权改动
- **Reports To**: chief

## 模型

joycode GLM-5.3。

## Worker Report (task075, 2026-08-31)

**Status: HALTED — undocumented blocker (17-image scratch capacity).** Gates 1–6 all PASS
(pytest 310+151; duplicate classes green; alignment strict exit 0; manifest-dex closure
PASS 24 dex / 94,893 classes / missing=0; clean assembleDebug bit-reproducible twice
`a8bab0f6…` 193,890,789 B; emulator relaunch from prebuilt 17 images healthy, pre-deploy
snapshot green). Gate 7 Debug deploy BLOCKED: `/mnt/scratch` (dm-5, backed by super) is
only 87,116 KB total / 40,828 KB avail — `cp: short write: No space left on device`
(truncated to 41,750,528 B, sha gate caught, PITFALLS 14.2 reproduced). force-stop+kill
per Incident 1 procedure did NOT change df (fresh overlay, no held inodes) — this is a
**structural** capacity shortfall: 17 emu64x super.img is nearly fully allocated
(CreateDynamicScratch sizing per fs_mgr source). Release (45,030,130 B) also exceeds
40,807,872 B avail. Device restored to healthy stock state; no partition workarounds
attempted. Full evidence + route options A–D in `docs/issues/2026-09-01-c5-dual-runtime-gate.md`
(actual path: `docs/issues/2026-09-01-c5-dual-runtime-gate.md`). Awaiting chief decision.

## Worker Report — Route B addendum (2026-08-31 17:35)

**Route B outcome (user-approved /data-scratch diagnosis + fix): reported, awaiting chief decision.**

- **Three root causes pinned (source + empirical)**: ① gsid (disabled+oneshot+lazy) never
  auto-starts → runtime disable-verity's CreateScratchOnData fails at binder gsiservice;
  ② emu64x userdata is a bare vdisk (vdc, no PARTNAME → no /dev/block/by-name link, ever)
  → lp_metadata device name unresolvable by PartitionOpener; ③ first-stage init uses
  passthrough libfiemap and /dev tmpfs links vanish on reboot → data scratch unmappable
  at boot; AOSP boot cleanup then DELETES the orphaned image (verified empirically).
- **Runtime fix PROVEN**: start gsid + manual by-name symlinks + disable-verity →
  **1.85GB /data-backed scratch**; full staged Debug deploy (193,890,789 B, sha gates
  PASS, no ENOSPC) + runtime verdict **ALL GREEN** (PID stable 10×30s, crash 0,
  FATAL/NCDFE 0, windows live, dumpsys ok).
- **Release crash-loop discovered (independent build-side defect)**: 85×FATAL, single
  signature NoSuchFieldException educationViewedTimestampMillis_ (wmshell
  WindowingEducationProto, protobuf-lite reflection). Dex forensics: Soong stock keeps
  the field, our Release shrank it (accessors dead-code-eliminated in both). C4c
  handover item #4 precisely predicted. Fix = proguard keep (build side, needs dispatch).
- **Reboot persistence NOT achievable** on this image by device-level reversible
  AOSP-native means (documented three blockers + raw system_ext 100% full).
- **16-era answer (user-named question)**: 16 also used the super fallback path — 261MB
  was 16 super's remaining free space (data-path size would be ~1.9GB); 17 super is full
  → 87MB. Same mechanism, different slack.
- Device restored to stock baseline; no AOSP image bytes written (qemu qcow2 overlays
  only). Full evidence + options B1–B4: docs/issues/2026-09-01-c5-dual-runtime-gate.md.
