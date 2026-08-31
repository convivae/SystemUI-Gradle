# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-08-31（**Phase C：C1/C2/C3/C4 全部完成**——AOSP 升级 `android-17.0.0_r1` + 全量构建、libs/ 脚本再生、源码重对齐、C4a 接线 + C4b Debug 编译闭合 + C4c Release/R8 编译闭合：`:app:assembleDebug` 与 `:app:assembleRelease` 均 BUILD SUCCESSFUL（minifyReleaseWithR8 含，missing refs 31→0 按 6 根因组闭合）。**剩 C5 双 runtime 门 + C6 收口**。16 时代的 DEBUG/RELEASE_RUNTIME_PASS 为历史基线，APK sha 台账见下。）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| AOSP 基线 | **`android-17.0.0_r1`**（manifest `5bc9a7ce`，frameworks/base `94b4c163b`，1084 projects）；C1 全量构建 `m -j16` 成功（2h35m；GOMEMLIMIT=24GiB + 32G swap） |
| Debug APK | ✅ **C4b 闭合（task073，2026-08-31）**：`:app:assembleDebug` BUILD SUCCESSFUL，APK 199,845,582 B（16 时代 `e8aad131…`/163,896,493 B 为历史台账；APK sha 台账随 C5/C6 重算） |
| Release APK | ✅ **C4c 编译闭合（task074，2026-08-31）**：`:app:assembleRelease` BUILD SUCCESSFUL，APK 45,030,130 B（runtime 门 = C5；16 时代 `d3968fb2…` 为历史台账；APK 内容确定性成立、容器 zip 字节不承诺确定——见 task074 issue chief 补注） |
| Gradle 配置解析 | ✅ `./gradlew help` + `projects` BUILD SUCCESSFUL（C4a 验收；16 模块全部识别，C4b 起追加 `:SystemUI-utils-kairos`） |
| 源码/资源对齐 | ✅ `check_source_alignment.py --strict` exit 0（17 基线：MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1 src CONV_MOD + 86 res-product CONV_DEL 均为白名单） |
| Python 工具测试 | ✅ **310 passed**（+151 subtests，C4c task074 chief 复验，2026-08-31） |
| `libs/` 产物 | ✅ 107 文件全部由 `tools/` 脚本从 AOSP-17 再生（C2 102 + C4a 新增 5），本地 Maven 23 族全部 2.0.0 |
| 设备/模拟器 | 未跑（归 C5）；当前无 QEMU/emulator 进程在跑；C5 按 runbook 重拉 17 镜像模拟器 |
| 当前唯一工程优先级 | **Phase C 收尾**：C5 17 镜像模拟器双 runtime 门 → C6 manifest 快照 + tag + README 版本声明（ADR 0007） |

16 时代 R8 missing refs 轨迹（140 → 126 → … → 1 → 0，Task 044 收口）与 16 时代双 runtime 闭环均为历史证据，保留于本文件历史段落；17 重对齐后的 Release 闭环归 task074 重做。

## Verified milestones（已完成里程碑，最新在后）

| 时间 | 里程碑 | 证据 |
|------|--------|------|
| 2026-08-11 | KSP + Dagger 首次通过（0 KSP 错误） | commit `05ea2064` |
| 2026-08-12 | 全依赖升级 + AGP builtInKotlin；KSP/Kotlin/core javac 全部 0 错误 | `docs/issues/2026-08-12-current-progress-standards-review.md` |
| 2026-08-13 | core javac 0 错误（8 组根因清零）；SysUISdk 可复现 + framework-res + `androidprv` 修复 | `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md` |
| 2026-08-19 | **首个 debug APK**（Task 015，158,775,460 B）；SettingsLib per-target res closure（ADR 0005） | `docs/issues/2026-08-19-settingslib-per-target-aars.md` |
| 2026-08-19 | 无混淆 release 基线（Task 029，126,642,058 B，V2 签名）；AOSP release 配置对齐 | `docs/issues/2026-08-20-release-r8-alignment-decisions.md` |
| 2026-08-20 | 官方 Maven 依赖审计落地（zxing 3.5.4 等，4 个本地 jar 退役） | `docs/issues/2026-08-20-official-maven-audit.md` |
| 2026-08-20 | R8 Batch 1–4C：clean monet/aconfig/view-capture/iconloader/WM-Shell proto/Traceur 产物；140→81 | `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` |
| 2026-08-20 | Traceur 双 AAR（Task 038）：640 类 + 105 res；R8 88→81 精确；179/179 | `docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md` |
| 2026-08-21 | SettingsLib program/resource 闭包（Task 040）：主 AAR 1153 类、Theme 15 类、17 个 per-target 资源 AAR；R8 81→7 精确；195/195 | `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md` |
| 2026-08-21 | SysUISdk R8 library bridge（Task 041）：两个 SDK target 各注入 35 个真实 library classes；APK 0 打包；R8 7→1 精确；233/233 | `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md` |
| 2026-08-21 | **完整 Release closure（Task 044，main fresh）**：单 FQN release-only adapter；R8 1→0；`assembleRelease` + optimized resource shrink + V2 签名成功；APK 28,600,808 B；239/239 | `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md` |
| 2026-08-21 | **SysUISdk 单入口 composition（Task 045，main fresh）**：`build_sysuisdk.py` 重写为事务性单命令生成器；两次 11,382-file 真实 AOSP 生成逐字节相等；main 上 Debug/R8/Release/ZIP/V2/DEX 全绿；220/220 | `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md` |
| 2026-08-22 | 单入口文档同步与 legacy live SysUISdk 清理（Tasks 046–047） | `docs/architecture/2026-08-21-legacy-sysuisdk-backup-inventory.md` |
| 2026-08-22 | 首个真实专用模拟器替换实验（Task 048）— `RUNTIME_FAIL`（namespace/R8 双重缺陷根因入库） | `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md` |
| 2026-08-23 | Task 051 根因审计闭环：app→core→DEX assembly 正确；`usesNonSdkApi`/平台签名 runtime contract divergence 锁定；用户选 same-tree Family B | `docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md` |
| 2026-08-23 | Task 052/052A/B/C：same-tree ARM64 构建与产品矩阵研究；host-native `sdk_phone64_x86_64` 选为主候选 | `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md` |
| 2026-08-25 | **16 时代 DEBUG_RUNTIME_PASS（Task 058 gate suite）**：same-tree emulator-5554 运行 Debug APK `e8aad131…`，PID 稳定零 crash | `docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md` |
| 2026-08-25 | Task 059 直接 AAR 迁移：四族单 consumer AAR 改 `files("libs/aars/…")`，字节中性已证 | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` |
| 2026-08-26 | **16 时代 RELEASE_RUNTIME_PASS（task 060→061）**：AssumeFalseForR8 精确 dontwarn → `-dontobfuscate` → 3 行 `-keep`；Release APK `d3968fb2…` 门级通过 | `docs/issues/2026-08-26-release-runtime-closure.md` |
| 2026-08-27 | **C1（Phase C）**：AOSP 树原地切换 `android-17.0.0_r1` 并全量构建成功（`m -j16`，2h35m；soong_build 分析 OOM 根因 = 26G 单进程） | `docs/orchestration/log.md` 2026-08-27 条目；ADR 0007 |
| 2026-08-27 | **C3 源码 17 重对齐（task070，review-PASS）**：删 EXTRA 847 → 移 MISPLACED 34 → 拷 MISSING 2566（含 3 个新模块目录 + 3 manifest）→ 覆 MODIFIED 3067（逐文件字节校验）→ CONV 重标 5806 处；`--strict` exit 0 | `docs/issues/2026-08-27-c3-source-realignment-execution.md` |
| 2026-08-28 | **C2 libs/ 全删 + AOSP-17 脚本再生（task071，review-PASS）**：104 文件全删 → 仅凭 7 个 tools 脚本再生 102 文件（无手工产物）；maven 全族 2.0.0；漂移 9/47/48/46；`motion_tool_lib.jar`、`settingslib-selector-flags.jar` 退役；aconfig family 14→12（6 族改 framework-minus-apex 聚合分片抽取） | `docs/issues/2026-08-27-c2-libs-regen-17.md` |
| 2026-08-28 | **C4a Gradle 接线（task072，review-PASS）**：16-module 拓扑注册 + catalog 23 族 2.0.0 + 依赖增删 + surfaceeffects×3/uilatencystats-flags jar + dynamiccolors AAR 新产物 + `:app` 最小 manifest 壳 + core namespace→`com.android.systemui.core`；`./gradlew help`/`projects` 绿、`--strict` exit 0、pytest 293 passed | `docs/issues/2026-08-28-c4-gradle-wiring.md` |

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| AOSP 全量构建（17） | ✅ `m -j16` 成功（2h35m；GOMEMLIMIT=24GiB + 32G swapfile） | C1，2026-08-27（log.md） |
| 源码/资源对齐 | ✅ `check_source_alignment.py --strict` exit 0（MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1 src + 86 res = 白名单 CONV） | task072 chief 复验（2026-08-28） |
| Gradle 配置解析 | ✅ `./gradlew help` + `projects` BUILD SUCCESSFUL（16 模块识别） | task072（2026-08-28，先 `pkill -f GradleDaemon`） |
| Python 工具测试 | ✅ 305 passed（+141 subtests） | task073 chief 复验（2026-08-31） |
| 产物确定性 | ✅ 冻结指纹 `package_misc_jars.py --verify-only` 22/22 MATCH（含 mechanics×2 等 5 个新冻结 jar；两个 AAR 内容修正后租户 17→22 族） | task073 chief 复验（2026-08-31） |
| `:app:assembleDebug` | ✅ BUILD SUCCESSFUL（chief 2026-08-31 重跑证实；K 错误 R1 182 → R4 5 → R50 0；四层修复：aapt2 双阶段 feature-flags、SysUISdk 重建 D12 选项 ①、17 依赖图接线 R9-R31（compose 首次真编译 188→0）、Dagger api 化 R24-R50） | task073（5 commits `a65e2d9c..517ca6d6`） |
| `:app:assembleRelease` / R8 | 未跑（归 task074；16 时代 Release closure 流程与规则基线保留为历史参考） | — |
| 设备/模拟器 runtime | 未跑（归 C5）；当前无 QEMU/emulator 进程；C5 按 runbook `docs/issues/2026-08-26-emulator-relaunch-runbook.md` 重拉 17 镜像模拟器并跑双 runtime 门 | — |

## Toolchain and module topology

版本矩阵（升级须先与用户沟通；Compose **不得升 1.12**，`ExperimentalAnimatableApi` 已移除而 AOSP 在用）：

| 组件 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.3.1 | settings.gradle.kts 硬编码 |
| Kotlin | 2.2.10 | AGP `builtInKotlin=true` 内置，无显式 kotlin-android 插件 |
| KSP | 2.2.10-2.0.2 | 对齐 AGP 内置 Kotlin |
| Dagger | 2.59.2 | useBindingGraphFix 默认启用（≥2.58） |
| Compose | 1.11.4 | **上限**（1.12.0 移除 `ExperimentalAnimatableApi`） |
| material3 | 1.5.0-alpha18 | 对齐 compose 1.11.x |
| JDK | 21 | 工具链 |
| compileSdk | `SysUISdk`（自定义 preview） | 生成器 `python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp`（Task 045 单入口；默认 base `android-37.0`）。**当前 live SysUISdk 仍为 16 时代产物（android.jar 2026-08-21 生成）；AOSP-17 八输入已验存，从 17 `out/` 重建排在 C5 前** |
| kotlinx-coroutines | 1.10.2 | **上限**：1.11.0 新 `SharedFlow.collectLatest` overload 破坏 AOSP 源码（Task 035 REDLINE 裁定） |
| protobuf-javalite | 4.35.1 | latest-stable 政策（Task 035） |
| zxing | 3.5.4 | 官方 Maven 最新（Task 026/027） |

builtInKotlin 三件套（PITFALLS §1.5）：`android.builtInKotlin=true`、`android.disallowKotlinSourceSets=false`（Task 023 实验证实 REQUIRED）、每个 Android 模块 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`。

16-module 拓扑（C4a，语义对齐 AOSP 17 `Android.bp`，ADR 0003；AGENTS.md §3.1 为 owner）：

```
:app :SystemUI-core :SystemUI-application :SystemUI-res :SystemUI-common
:SystemUI-animation :SystemUI-plugin-core :SystemUI-plugin-processor
:SystemUI-plugin :SystemUI-unfold :SystemUI-customization :SystemUI-clocks-common
:SystemUI-shared :SystemUI-shared-biometrics :SystemUI-compose
:SystemUI-accessibility-floatingmenu-res
```

C4b（task073）按 17 bp 追加 tier① 源码模块 `:SystemUI-utils-kairos`（kairos，`packages/SystemUI/utils/kairos/`，63 kt；16 时代 test-only 判定为误判，17 已是 SystemUI-core 生产依赖），当前 settings include **17 个模块**。SysUISdk 于 2026-08-31 起已按 AOSP-17 重建（生成器按 D12 选项 ①：桥接切片 39→37 条、冻结映射 8→7 输入），不用再等 C5 前重建这段话；releases 面与 runtime 门不变。另 2026-08-29 起 `:SystemUI-plugin` namespace 对齐 AOSP 为 `com.android.systemui.plugins`（用户批准）。

## Dependency and artifact state

- `libs/`（jar + aars + maven）全部提交入 git；**Phase C 后 107 文件全部由 `tools/` 脚本从 AOSP-17 `out/` 确定性再生**（C2 删 104 → 脚本再生 102；C4a 新增 5：surfaceeffects×3 jar、uilatencystats-flags jar、dynamiccolors AAR）。ADR 0007 验收命题「每一字节都来自脚本产出，无一手工文件」在 17 基线成立。
- 本地 Maven 仓 `libs/maven/`：**23 族全部 2.0.0**（major = AOSP vintage 16→17）；23 AAR + 23 POM。SettingsLib POM 携 17 条 per-target 依赖边（ADR 0005）。
- **退役产物（17 上游不再存在）**：`libs/motion_tool_lib.jar`（motiontoollib 上游删除）、`libs/settingslib-selector-flags.jar`（上游删除）；aconfig family `security-flags`、`quickaccesswallet-flags`（包改名上游删除）——对应 Gradle 依赖行已随 C4a 移除。
- aconfig：`libs/systemui-aconfig-flags.jar` 为 **12 族合并**（60 类；16 时代 14 族 70 类）；其中 6 族在 17 无独立 javac 输出，由 `extract_aggregate_subset()` 从 framework-minus-apex 聚合分片内容扫描抽取（真实 Soong 字节）。另 10 个单族 flags jar（systemui/notification/launcher3/settingslib-widget/settingslib-media/device-state/wifi/wm-shell/systemui-shared/settingslib-flags）由 `package_aconfig_jars.py` 产出。
- **直接 AAR 消费集（Task 059 例外，AGENTS.md §3.2）**：WifiTrackerLib、iconloader、LowLightDreamLib、setupcompat（16 时代四族）+ **dynamiccolors（C4a 新增，单 consumer `:SystemUI-res`）**，经 `files("libs/aars/*.aar")` 直接消费。
- C4a 新产物：`SurfaceEffectsCoreLib/ComposeLib/ViewLib.jar`（frameworks/libs/systemui/surfaceeffects，tier② jar，接入 `:SystemUI-core`）、`uilatencystats-flags.jar`（接入 core）、`dynamiccolors.aar`（res-only，接入 `:SystemUI-res`）。
- `libs/aars/` 30 个 AAR；`libs/` 根 30 个 jar（含 compilelib debug/release、framework.jar 等）；`libs/prebuilts/tracinglib-platform.jar`（溯源仍挂起，推迟 Release 阶段处理）。
- 官方 Maven 坐标优先（Task 026 审计后）：zxing、protobuf-javalite、coroutines 1.10.2、errorprone、jsr330（C4a 新增，javax.inject:javax.inject:1）等走公网；AOSP prebuilts 版本多数不在公网，逐个查 `maven-metadata.xml`。
- 产物再生入口：`uv run python tools/package_aosp_aar.py --all` + `install_aar_to_maven.py` 等 7 脚本（完整序列见 README Quickstart 第 4 步；C2 后全部适配 17 树）。
- keystore：`keystore/platform.keystore`（Phase C 未随 libs/ 重建；ADR 0007 删除范围包含 keystore，其脚本化再生状态以 task067/ADR 0007 后续执行为准）。

## Release closure：16 时代已关闭；17 基线归 task074 重做

16 时代（AOSP main 快照）Release closure 已于 Task 044 + task 060/060b/061 关闭：
`app/proguard_gradle.flags` 累计精确规则 = AssumeFalseForR8 `-dontwarn`（Task 044 同族 option A）+
`-dontobfuscate`（对齐 Soong dex.go:545）+ 3 行 CoreStartable 三件套 `-keep`（抗 R8 水平合并）。
该规则集与 `tools/tests/test_gradle_r8_adapter_rules.py` contract 测试钉住的历史边界对 17 重放
仍是起点，但 **17 基线的 Release/R8 闭环归 task074**（含 view_capture proto keep 规则等
task073 移交项）。16 时代 Release runtime 门（`d3968fb2…`，emulator-5554）为历史台账。

## Next ordered work

1. **task074（C4b 后，下一号工单）**：Release/R8 闭环恢复绿（`minifyReleaseWithR8` + `assembleRelease`）。
   移交清单见 task073 issue §7（assume true-for-R8 adapter、pods 测试源不入生产图、view_capture proto 零引用已核实等）。
2. **C5**：17 镜像模拟器重拉（runbook `docs/issues/2026-08-26-emulator-relaunch-runbook.md`）+
   Debug/Release 双 runtime 门（部署、零 FATAL、窗口在屏）；SysUISdk 已按 AOSP-17 重建（2026-08-31，不需重建）。
   尾账：SDK 目录老备份 `android-SysUISdk.bak-legacy-pre-aosp17` 与 `-staging/` 待用户确认后清理。
4. **C6**：manifest 快照 + release tag + README 版本声明（ADR 0007 收口；`git diff` 即产物漂移审计报告）。
5. 尾账（Release 阶段处理）：tracinglib-platform.jar 溯源；维护性观察（Kotlin 2.3/AGP 9.5 解锁、
   AOSP 树漂移回查、官方 Maven 等价物回查、pytest 偶发间歇失败观察）。

## Verification commands and evidence

```bash
# SysUISdk 单入口重建（C5 前需对 AOSP-17 out/ 重跑；需已构建的 AOSP out/）
python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp

# 单元测试（Python 工具测试；C4a 验收基线 293 passed +111 subtests）
uv run pytest tools/tests -q

# 源码对齐（17 基线；strict exit 0，MODIFIED 仅白名单）
uv run python tools/check_source_alignment.py --strict

# Gradle 配置解析（C4a 验收门；编译闭环归 C4b）
./gradlew help
./gradlew projects

# Debug APK（C4b 目标门，进行中）
./gradlew :app:assembleDebug --console=plain

# Release R8 / 完整 Release（归 task074，未跑）
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain
./gradlew :app:assembleRelease --console=plain
```

**当前（17 基线，2026-08-28）证据**：C4a task072 chief 独立复验——`./gradlew help`
BUILD SUCCESSFUL（41s）；16 模块全部识别；`--strict` exit 0（MODIFIED 1+86 均白名单）；
pytest 293 passed +111 subtests；catalog 23 族 2.0.0、`libs/maven/` 仅存 2.0.0 目录；
四个新产物删除重跑字节一致；禁改面零 diff。C2 task071 chief 复验——pytest 290 passed、
maven 全 2.0.0/零 1.x、byte-identical 文件对 git 历史复核、framework.jar 29,066 类、
聚合分片抽取字节 == 真实 Soong shard、退役族零 import。C3 task070 chief 复验——5806 处
非 default product 变体全标记、90 个 xml 解析合法、禁改面零 diff。**C4b 编译闭环与 17 基线
构建/runtime 验证尚未完成（如实记录：未运行 assembleDebug 成功、未跑 Release、未跑模拟器）。**

**16 时代历史证据（AOSP main 快照，2026-08-21→26，保留供追溯）**：
Task 045 main fresh（SysUISdk 单事务生成器两次 11,382 文件逐字节相等；Debug exit 0；fresh
R8 exit 0 零 refs；`assembleRelease` + 两个 optimized-resource tasks + V2；APK 28,600,808 B
`cd4b885e…`；220/220）。Task 058 gate suite（DEBUG_RUNTIME_PASS 2026-08-25：pytest 243+、
duplicate-classes 绿、对齐 0/0/0、manifest-dex 闭包、clean build `e8aad131`（163,896,493 B）、
emulator-5554 原子部署后 PID 稳定 10×30s 零 crash）。task 060/060b/061（RELEASE_RUNTIME_PASS
2026-08-26：AssumeFalseForR8 → `-dontobfuscate` → 3 行 `-keep`；Release 基线 `d3968fb2…`
（34,688,965 B）门级通过；三轮根因全记录）。task 065（DIFF jar 替换后 Debug 字节不变、
Release 新基线）。详细报告见 `docs/issues/` 对应日期文件。

构建纪律：全系统同一时刻**只允许一个 Gradle build**（CHARTER Part 4）；`:app:assembleDebug`
恢复绿后仍是每批硬门禁；长时间不用时 `pkill -f GradleDaemon`（30G RAM）。

## Historical pointers

- Phase C 执行与验收：`docs/issues/2026-08-27-c3-source-realignment-execution.md`（C3）、
  `docs/issues/2026-08-27-c2-libs-regen-17.md`（C2）、`docs/issues/2026-08-28-c4-gradle-wiring.md`
  （C4a）、`docs/adr/0007-phase-c-clean-regen-release-tag.md`（Phase C 决策）
- 错误数/迁移历史：`docs/GRADLE_MIGRATION_LOG.md`（append-only）
- 深度调研与 audit：`docs/architecture/`
- 每日问题记录：`docs/issues/`
- 踩坑经验：`docs/PITFALLS.md`
- 未完成路线：`docs/PLAN.md`
