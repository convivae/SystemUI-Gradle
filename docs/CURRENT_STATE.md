# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-09-02（Phase C 的 C1–C4 全部完成；C5 编译、部署基础设施与 Debug 热运行已闭合。task076 修复 Release protobuf-lite 反射字段；task077 完成 durable emulator 基础设施；task078/080 将 AOSP-17 aconfig 改名缺口固定为四条 exact mappings、166 个 program reference classes。Task 081 的 buildSrc reference-only plugin 已通过 9 个 focused tests 与双轴 review；**Task 082 首次真实 Debug pipeline 在 `:app:desugarDebugFileDependencies` FAIL：AGP `AsmClassesTransform` 无法隔离参数，因为 `AconfigReferenceRewriteFactory` 无法序列化。当前唯一 blocker 是修复该 transform-isolation contract，再重跑独立 Debug build/static gate。**）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| AOSP 基线 | **`android-17.0.0_r1`**（manifest `5bc9a7ce`，frameworks/base `94b4c163b`，1084 projects）；C1 全量构建 `m -j16` 成功（2h35m；GOMEMLIMIT=24GiB + 32G swap） |
| Debug APK | ⚠️ C4b/Task 075 的旧 Debug APK 曾编译并热运行通过；Task 081 新增 reference-only build logic 后，Task 082 首次真实 `assembleDebug --rerun-tasks` 在 `:app:desugarDebugFileDependencies` 因 `AconfigReferenceRewriteFactory` transform-isolation serialization failure 停止，未产出或验收新的候选 APK |
| Release APK | ⚠️ `:app:assembleRelease` 编译/R8 闭合；task076 已修复 protobuf-lite 反射字段并证明三轮内容 SHA 一致。task077 运行时暴露 AOSP 17 platform aconfig jarjar 改名缺口：DEX 引用原名 `Flags`、设备仅有 `hidden_from_bootclasspath` 改名类，当前冷启动 **FAIL** |
| Gradle 配置解析 | ✅ `./gradlew help` + `projects` BUILD SUCCESSFUL（C4a 验收；16 模块全部识别，C4b 起追加 `:SystemUI-utils-kairos`） |
| 源码/资源对齐 | ✅ `check_source_alignment.py --strict` exit 0（17 基线：MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1 src CONV_MOD + 86 res-product CONV_DEL 均为白名单） |
| Python 工具测试 | ✅ **310 passed**（+151 subtests，C4c task074 chief 复验，2026-08-31） |
| `libs/` 产物 | ✅ 107 文件全部由 `tools/` 脚本从 AOSP-17 再生（C2 102 + C4a 新增 5）；17-vintage 坐标以 2.0.0 为基线，C4b/C4c 修正的 WM-Shell/SettingsLib 产物已升 2.0.1 |
| 设备/模拟器 | ⏸️ 主机重启后当前无连接设备、无 emulator/QEMU 进程。17 emu64x durable runtime 基础设施已验收：`super.img` 3,028,287,488 B（SHA `50496c9b…`），scratch 582MiB、五 overlay、orange verified boot、64MiB probe 跨重启 PASS；当前 build-logic/Debug build blocker 不需要设备，后续双 runtime gate 前再按 runbook 启动并核验专用模拟器 |
| 当前唯一工程优先级 | **C5 blocker**：Task 081 的四-rule/166-class reference-only plugin 已通过 focused tests 与 review，但 Task 082 证明真实 AGP dependency transform 无法序列化 `AconfigReferenceRewriteFactory`。下一步先取得最深层 cause、建立 focused regression gate并只修 build logic，再以新任务重跑 Debug build/static gate；之后才允许 Release build/static gate与双 runtime gate。Task 079 broad replay保持暂停；禁止打包平台类、stub、`dontwarn`、源码 import 批量改写或 post-R8 DEX patch |

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
| 2026-08-31 | **C4b Debug 编译闭环（task073）**：追加 kairos 形成 17-module 拓扑；AOSP-17 SysUISdk 重建；`:app:assembleDebug` BUILD SUCCESSFUL；对齐、pytest 305、冻结指纹 22/22 PASS | `docs/issues/2026-08-28-c4b-debug-compile-closure.md` |
| 2026-08-31 | **C4c Release/R8 编译闭环（task074）**：missing refs 31→0；`:app:assembleRelease` BUILD SUCCESSFUL；SettingsLib/WM-Shell 修正产物升 2.0.1；pytest 310、冻结指纹 24/24 PASS | `docs/issues/2026-09-01-c4c-release-r8-closure.md` |
| 2026-09-01 | **C5 部分闭环（tasks075–077）**：Debug 热运行 PASS；Release protobuf 反射修复 PASS；goldfish 2880MiB super、582MiB scratch、五 overlay、64MiB probe 跨重启 PASS。剩余 blocker：Release platform aconfig JarJar 引用未改名 | `docs/issues/2026-09-01-c5-emulator-super-slack.md` |
| 2026-09-01 | **C5 task078 研究/gate 闭环（review-PASS）**：纯 stdlib DEX checker + 26 个 focused tests；Release exit 1（30 source/0 target）、stock exit 0（1 source/36 target）；725 条 exact 规则主源传播/执行时序已还原 | `docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md` |
| 2026-09-02 | **C5 task080 来源闭环（review-PASS）**：按 `CONSTANT_Class`/`this_class` 扫描并以引用类身份去重；四个 critical 旧名对应 50/7/5/104，共 166 个 program reference classes，`ORIGINS_PROVEN=4/4`、`UNKNOWN=0`；compileOnly `framework.jar` 明确隔离 | `docs/issues/2026-09-01-c5-focused-reference-origins.md` |
| 2026-09-02 | **C5 task081 build-logic proof（review-PASS）**：app-only `InstrumentationScope.ALL` reference-only plugin；四规则/166-class inputs；9 focused tests；`ALL`/`COPY_FRAMES` registration与十项 mandatory contract通过双轴 review。只证明 build logic，不证明 Android pipeline | `docs/issues/2026-09-02-c5-pre-dex-reference-rewrite.md` |
| 2026-09-02 | **C5 task082 Debug pipeline FAIL**：唯一 `assembleDebug --rerun-tasks` exit 1；`:app:desugarDebugFileDependencies` 无法隔离 `AsmClassesTransform.Parameters`，最深已知消息为 `Could not serialize value of type AconfigReferenceRewriteFactory`；未验收 APK | `docs/issues/2026-09-02-c5-debug-build-after-reference-rewrite.md` |

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| AOSP 全量构建（17） | ✅ `m -j16` 成功（2h35m；GOMEMLIMIT=24GiB + 32G swapfile） | C1，2026-08-27（log.md） |
| 源码/资源对齐 | ✅ `check_source_alignment.py --strict` exit 0（MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1 src + 86 res = 白名单 CONV） | task072 chief 复验（2026-08-28） |
| Gradle 配置解析 | ✅ `./gradlew help` + `projects` BUILD SUCCESSFUL（16 模块识别） | task072（2026-08-28，先 `pkill -f GradleDaemon`） |
| Python 工具测试 | ✅ 310 passed（+151 subtests） | task074 chief 复验（2026-08-31） |
| 产物确定性 | ✅ 冻结指纹 `package_misc_jars.py --verify-only` 24/24 MATCH；task076 三轮 clean Release 的 ZIP 条目内容 SHA 一致（整 APK 仅 SDKP signing block 随机） | task074 + task076（2026-08-31/09-01） |
| `:app:assembleDebug` | ⚠️ C4b/task073 历史基线 BUILD SUCCESSFUL；Task 081 plugin 后的 Task 082 fresh pipeline FAIL at `:app:desugarDebugFileDependencies`：`AsmClassesTransform.Parameters` isolation → `Could not serialize value of type AconfigReferenceRewriteFactory`。新 Debug APK 未验收 | task082，`/tmp/task082-c5-debug-build/assemble-debug.log`（2026-09-02） |
| `:app:assembleRelease` / R8 | ✅ BUILD SUCCESSFUL、missing refs=0；task076 的 GeneratedMessageLite 字段 keep 修复后，三轮 clean build 的 ZIP 条目内容 SHA 均为 `2a5e372f…`（整 APK 仅 SDKP signing block 随机） | task074 + task076（2026-08-31/09-01） |
| 设备/模拟器 runtime | ⚠️ task075 Debug 热运行门 PASS；task077 durable super/overlay/64MiB probe 跨重启 PASS。修复后 Release 在冷启动时因 `android.view.accessibility.Flags` 等原名引用触发 `NoClassDefFoundError`；stock APK 已恢复且健康 | `docs/issues/2026-09-01-c5-emulator-super-slack.md` |
| Aconfig JarJar 静态/build-logic gate | ⚠️ task078 checker/focused tests与 task081 9 个 buildSrc tests通过；Task 082 证明真实 AGP `ALL` dependency transform 在 factory serialization/isolation 阶段失败，尚无新 APK 可运行四 hidden-reference/零 hidden-definition gate | `tools/check_aconfig_jarjar_references.py`；Task 081/082 issues |

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
| compileSdk | `SysUISdk`（自定义 preview） | 生成器 `uv run python tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp`（Task 045 单入口；默认 base `android-37.0`）。live SysUISdk 已于 2026-08-31 从 AOSP-17 的 7 个冻结输入重建 |
| kotlinx-coroutines | 1.10.2 | **上限**：1.11.0 新 `SharedFlow.collectLatest` overload 破坏 AOSP 源码（Task 035 REDLINE 裁定） |
| protobuf-javalite | 4.35.1 | latest-stable 政策（Task 035） |
| zxing | 3.5.4 | 官方 Maven 最新（Task 026/027） |

builtInKotlin 三件套（PITFALLS §1.5）：`android.builtInKotlin=true`、`android.disallowKotlinSourceSets=false`（Task 023 实验证实 REQUIRED）、每个 Android 模块 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`。

17-module 拓扑（C4a 先注册 16 模块，C4b 追加 `:SystemUI-utils-kairos`；语义对齐 AOSP 17 `Android.bp`，ADR 0003；AGENTS.md §3.1 为 owner）：

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
- 本地 Maven 仓 `libs/maven/`：AOSP-17 坐标以 2.0.0 为基线；C4b/C4c 经内容变化升版的 WM-Shell/SettingsLib 族使用 2.0.1，旧坐标退役。SettingsLib POM 携 17 条 per-target 依赖边（ADR 0005）。
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

1. **Transform-isolation diagnosis/fix**：Task 082 已以真实 pipeline 稳定触发 `:app:desugarDebugFileDependencies` failure。下一任务先在 cached dependency-transform 路径取得完整 stacktrace/最深 cause，建立最小正确 regression gate，再只修改 `buildSrc` factory/parameters 生命周期；不得扩大四规则、166-class allowlist或 rewrite seam。
2. **独立 Debug build/static gate**：fix review-PASS 后重新立 no-fix build task，运行 fresh `:app:assembleDebug`，验证 APK ZIP/SHA、四 hidden references、零 hidden target definitions和无非法 old-name caller。
3. **Release build/static gate**：Debug 成功后独立停止 Gradle/Kotlin daemons并运行 Release/R8；Release checker 必须消除四个 critical old references、出现 hidden references且 hidden target definitions=0。
4. **C5 runtime 收口**：分别部署 Debug 与 Release 到 task077 durable overlay，核对 host/device SHA、PID/fatal/UI 门并完成整机重启前后验证。
5. **C6**：manifest 快照 + release tag + README/version/HANDOFF 收口（ADR 0007）。
6. **尾账**：SDK 老备份清理（待用户确认）、`tracinglib-platform.jar` 溯源、依赖/pytest 维护性观察。

## Verification commands and evidence

```bash
# SysUISdk 单入口重建（live SDK 已按 AOSP-17 重建；仅需再生时运行）
uv run python tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp

# 单元测试（Python 工具测试；C4a 验收基线 293 passed +111 subtests）
uv run pytest tools/tests -q

# 源码对齐（17 基线；strict exit 0，MODIFIED 仅白名单）
uv run python tools/check_source_alignment.py --strict

# Gradle 配置解析（C4a 验收门；编译闭环归 C4b）
./gradlew help
./gradlew projects

# Debug APK（C4b 已闭合；C5 修复后重跑冷启动门）
./gradlew :app:assembleDebug --console=plain

# Release R8 / 完整 Release（编译门已闭合；task078 后重跑）
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain
./gradlew :app:assembleRelease --console=plain
```

**当前（17 基线，2026-09-02）证据**：pytest 310 passed；源码对齐 strict exit 0；
manifest-dex closure 24/24、missing=0；Debug 热运行 PID/crash/UI 门通过；Release protobuf-lite
反射字段已修复且三轮内容级构建一致。AOSP goldfish 单行容量变更经正式 `m -j16` 构建成功，
`super.img` SHA `50496c9b…`，设备 scratch 582MiB、五分区 overlay、64MiB 探针跨整机重启
持久。task078/080 �� blocker 固定为四条 critical mappings和 166 个 program reference classes；Task 081
的 reference-only plugin 已通过 9 个 focused tests与双轴 review。Task 082 首次真实 Debug pipeline
运行唯一 `assembleDebug --rerun-tasks` 后 exit 1：`:app:desugarDebugFileDependencies` 无法隔离
`AsmClassesTransform.Parameters`，因为 `AconfigReferenceRewriteFactory` 无法序列化。完整日志为
`/tmp/task082-c5-debug-build/assemble-debug.log`；新 Debug APK/static gate 未执行。Task 079 broad replay
保持暂停；主机当前无连接设备或 emulator/QEMU，后续 runtime gate 前再启动。详见
`docs/issues/2026-09-01-c5-focused-reference-origins.md`、
`docs/issues/2026-09-02-c5-pre-dex-reference-rewrite.md` 与
`docs/issues/2026-09-02-c5-debug-build-after-reference-rewrite.md`。

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
