# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-09-03（**Phase C 的 C1–C5 全部完成**。Task 099 完成 aconfig reference rewrite 生产修复：完整 725 条 AOSP jarjar 规则 + instrument-everything seam + 指令级静态门禁。fresh Debug APK SHA `33e07319…` 与 fresh Release APK SHA `17358f4d…` 均通过静态门、部署、冷启动与**整机重启门**（PID 稳定、0 FATAL、StatusBar/Shade/Wallpaper 在屏）。commits `ed40e4b4`/`ea9b2f52`/`c79044b4` 已 push。Task 079 broad replay 继续暂停。下一步 C6 收口。）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| AOSP 基线 | **`android-17.0.0_r1`**（manifest `5bc9a7ce`，frameworks/base `94b4c163b`，1084 projects）；C1 全量构建 `m -j16` 成功（2h35m；GOMEMLIMIT=24GiB + 32G swap） |
| Debug APK | ✅ **Task 099 fresh Debug 全门 PASS**：`assembleDebug --rerun-tasks` exit 0（`BUILD SUCCESSFUL in 22m 03s`）；APK 200,506,573 B、SHA `33e07319…`；指令级静态门 0 违规（3,571 条 old-owner refs 全为 52 个 dead-shell 自引用，0 hidden 定义）；**部署 + 冷启动 + 整机重启门 PASS**（PID 848 稳定 90s、0 FATAL、UI 三件套在屏） |
| Release APK | ✅ **Task 099 fresh Release 全门 PASS**：APK 45,030,130 B、SHA `17358f4d…`、2 DEX；静态门 0 old-owner refs、449 hidden refs、0 hidden 定义；**部署 + 冷启动 + 整机重启门 PASS**（PID 850/852 稳定、0 FATAL） |
| Gradle 配置解析 | ✅ `./gradlew help --refresh-dependencies` BUILD SUCCESSFUL；`buildSrc` 的 dependency/plugin 两层仓库均已镜像优先，fresh sync 不再因直连 Maven Central/Plugin Portal TLS 失败 |
| 源码/资源对齐 | ✅ `check_source_alignment.py --strict` exit 0（17 基线：MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1 src CONV_MOD + 86 res-product CONV_DEL 均为白名单） |
| Python 工具测试 | ✅ **361 passed**（+151 subtests，chief 复验，2026-09-03） |
| `libs/` 产物 | ✅ 107 文件全部由 `tools/` 脚本从 AOSP-17 再生（C2 102 + C4a 新增 5）；17-vintage 坐标以 2.0.0 为基线，C4b/C4c 修正的 WM-Shell/SettingsLib 产物已升 2.0.1 |
| 设备/模拟器 | ✅ emulator-5554 运行 Release `17358f4d…`（PID 852 稳定，0 FATAL）。17 emu64x durable runtime 基础设施：`super.img` SHA `50496c9b…`，scratch 582MiB、五 overlay、orange verified boot、64MiB probe 跨重启 PASS；双 variant runtime 门均在其上通过 |
| 当前唯一工程优先级 | **C6 收口**：manifest 快照 + release tag + README/version/HANDOFF 声明（ADR 0007） |

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
| 2026-09-02 | **C5 task083 isolation diagnosis PASS**：唯一 direct task在 5 秒内精确重现；deepest cause 为 `java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty`。Factory自有 cache已证为 transient；具体 runtime decorator field path交由 Task 084 | `docs/issues/2026-09-02-c5-asm-factory-isolation.md` |
| 2026-09-02 | **C5 task084 serialization field-path PASS**：唯一 extended-info direct task在 5 秒内精确重现；46 个 cause chain均显示 `InstrumentationContext_Decorated.__apiVersion__` → factory decorator `__instrumentationContext__` literal path。首个失败对象属于 AGP注入状态；custom parameters后续可否序列化仍未确定 | `docs/issues/2026-09-02-c5-serialization-field-path.md` |
| 2026-09-02 | **C5 task086 corrected control PASS**：临时 `InstrumentationParameters.None`、field-free no-op、`ALL` registration显式传空lambda；唯一direct task `:app:desugarDebugFileDependencies` BUILD SUCCESSFUL in 21s，日志98行 SHA `938d2248…`；随后byte-for-byte恢复且worktree clean。该结果排除所有None/no-op ALL factory必然失败，但未单独隔离parameters与factory行为 | `docs/issues/2026-09-02-c5-none-all-control-corrected.md` |
| 2026-09-02 | **C5 task087 control INCONCLUSIVE**：field-free no-op + production `AconfigReferenceRewriteParameters` command exit 0，但`:app:desugarDebugFileDependencies UP-TO-DATE`；无artifact-transform/factory实际执行证据，不能判定custom file parameters通过 | `docs/issues/2026-09-02-c5-custom-file-params-control.md` |
| 2026-09-02 | **C5 tasks088/089 official research review-PASS**：未发现AGP/Gradle升级是当前literal failure的targeted fix证据；当前ASM seam的pre-D8/pre-R8与compileOnly排除由AGP 9.3.1 source证明，serialization触发边界仍unknown；`ScopedArtifacts`仅bounded candidate。四个独立Standards/Spec review均PASS | `docs/architecture/2026-09-02-agp-gradle-upgrade-feasibility.md`；`docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md` |
| 2026-09-02 | **C5 task090 observable control PASS**：production `AconfigReferenceRewriteParameters` 两个file-property槽位 + field-free no-op `ALL` factory在唯一input fingerprint下实际执行；sentinel 1、`AsmClassesTransform`记录45、exit 0、无serialization path。只排除parameter shape作为充分trigger，不证明production implementation或APK | `docs/issues/2026-09-02-c5-observable-file-params-control.md` |
| 2026-09-02 | **C5 task091 frozen-input load control PASS**：唯一command exit 0；entered/loaded sentinels各1，`FrozenAconfigInputs.load(...)`完成4 mappings/166 allowlist校验，ASM记录45且无serialization path。恢复完整；cleanup重复一次GradleDaemon pkill且三exit codes未保存的过程偏差已记录 | `docs/issues/2026-09-02-c5-frozen-input-load-control.md` |
| 2026-09-02 | **C5 task092 positive-admission control PASS**：唯一command exit 0；entered/accepted/no-op-visitor sentinels各1，ASM记录45且无serialization path，证明positive admission与class-byte no-op visitor不是充分trigger。恢复完整；cleanup shell self-match、首个exit code缺失及短暂out-of-root scratch偏差已记录 | `docs/issues/2026-09-02-c5-positive-allowlist-control.md` |
| 2026-09-02 | **C5 task093 cache activation control FAIL（已闭合）**：唯一command exit 1；三个sentinel与ASM records均0，Task 084 literal path markers各46。完整production-shaped transient cache layer是当前最小已知activation boundary；未单独归因任一子元素 | `docs/issues/2026-09-02-c5-transient-cache-control.md` |
| 2026-09-02 | **C5 task094 immutable snapshot control PASS**：configuration-time validated 4/166 managed values + field-free no-op factory的唯一direct command exit 0；45 ASM records、known serialization markers为0，证明isolation-safe seam，不证明visitor/APK | `docs/issues/2026-09-02-c5-immutable-input-snapshot-control.md` |
| 2026-09-02 | **C5 task095 production seam review-PASS**：production迁移完成；focused tests 9/9；direct transform exit 0、45 ASM records、serialization markers 0。真实`android.os.Flags` instruction rewrite已落DEX，hidden defs 0/2、old defs 2/2；原2/2 gate实际1/2因`window.flags`无可达caller。用户批准corrected bounded gate；Standards/Spec及两处文档修正的focused re-review均PASS，不声明APK四映射/runtime成功 | `docs/issues/2026-09-02-c5-production-immutable-input-seam.md` |
| 2026-09-02 | **C5 task096 fresh Debug build/static PASS**：唯一fresh build exit 0、278/278 tasks；APK 190,547,804 B、SHA `f3af35d9…`、ZIP/13 DEX通过；critical hidden refs `4/4`、725-rule hidden defs `0`；两个old definitions仅same-class context，另两个old descriptors为0。未声明runtime | `docs/issues/2026-09-02-c5-debug-build-static-gate.md` |
| 2026-09-02 | **C5 task097 fresh Release build/R8/static PASS**：唯一fresh build exit 0、493/493 tasks、R8/package实际执行；APK 45,030,130 B、SHA `641c6533…`、ZIP/2 DEX通过；checker exit 0 / `RESULT=PASS`，critical old refs/defs `0/4`、hidden refs `4/4`、hidden defs `0/4`、全725-rule hidden defs `0`。cleanup首条self-match导致exit丢失的过程偏差已披露；未声明runtime | `docs/issues/2026-09-02-c5-release-build-static-gate.md` |
| 2026-09-03 | **C5 闭环（Task 099，chief 验收并 push）**：aconfig reference rewrite 生产修复——根因为覆盖双重缺口（4 条手写 mapping + 166 caller allowlist vs 权威 725 规则；旧"健康"APK 经 A/B 实验证伪）；D8 从 BootstrapMethods 合成 lambda 使"跳过 source 类"方案不可行，Chief 裁定 instrument 一切类（reference-only visitor 保持 this_class/self-ref，hidden 定义 fail-closed）。Debug `33e07319…` 与 Release `17358f4d…` 双 APK 指令级静态门 PASS（0 违规 / 0 hidden 定义）+ 部署 + 冷启动 + **整机重启门 PASS**。commits `ed40e4b4`（seam+725 规则+buildSrc tests）、`ea9b2f52`（指令级 checker+33 tests）、`c79044b4`（docs）已 push | `docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md` |
| 2026-09-03 | **buildSrc fresh-sync TLS 修复**：补齐独立 build 的 dependency mirrors 与 pluginManagement mirrors；原失败的 Kotlin compiler plugin 及 Kotlin DSL plugin 均从腾讯镜像解析，`./gradlew help --refresh-dependencies` 成功 | `docs/issues/2026-09-03-buildsrc-maven-central-tls-resolution.md` |

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| AOSP 全量构建（17） | ✅ `m -j16` 成功（2h35m；GOMEMLIMIT=24GiB + 32G swapfile） | C1，2026-08-27（log.md） |
| 源码/资源对齐 | ✅ `check_source_alignment.py --strict` exit 0（MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1 src + 86 res = 白名单 CONV） | task072 chief 复验（2026-08-28） |
| Gradle 配置解析 | ✅ `./gradlew help --refresh-dependencies --console=plain --info` BUILD SUCCESSFUL in 48s；buildSrc dependency/plugin resolution 均命中腾讯镜像，0 direct Central/Plugin Portal、0 TLS failure | buildSrc mirror 修复（2026-09-03） |
| Python 工具测试 | ✅ 361 passed（+151 subtests） | chief 复验（2026-09-03） |
| 产物确定性 | ✅ 冻结指纹 `package_misc_jars.py --verify-only` 24/24 MATCH；task076 三轮 clean Release 的 ZIP 条目内容 SHA 一致（整 APK 仅 SDKP signing block 随机） | task074 + task076（2026-08-31/09-01） |
| `:app:assembleDebug` | ✅ Task 099 fresh `--rerun-tasks` BUILD SUCCESSFUL in 22m03s；APK 200,506,573 B、SHA `33e07319…` | Task 099（2026-09-03） |
| `:app:assembleRelease` / R8 | ✅ BUILD SUCCESSFUL、missing refs=0；task076 的 GeneratedMessageLite 字段 keep 修复后，三轮 clean build 的 ZIP 条目内容 SHA 均为 `2a5e372f…`（整 APK 仅 SDKP signing block 随机） | task074 + task076（2026-08-31/09-01） |
| 设备/模拟器 runtime | ✅ **双 variant 全门 PASS**：Debug `33e07319…`（PID 848，重启后 90s 稳定、0 FATAL）与 Release `17358f4d…`（PID 850/852，0 FATAL）均通过部署 + 冷启动 + 整机重启门；BLUETOOTH_CONNECT/READ_CONTACTS 两个 frozen grant 跨重启保持（APK 替换后可能需重授） | Task 099（2026-09-03），issue 099 |
| Aconfig JarJar 静态 gate | ✅ **双 APK 指令级门禁 PASS**：checker 重写为自包含 DEX 指令级 walker；规则=任何非 self-reference 的 old-owner executable ref 或任何 hidden target 定义即 FAIL。Debug：3,571 条 old refs 全为 52 个 dead-shell 自引用、0 违规、965 hidden refs、0 hidden 定义；Release：0 old refs（R8 strip dead shell）、449 hidden refs、0 hidden 定义 | `tools/check_aconfig_jarjar_references.py`；Task 099 |

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
| Gradle runtime JDK | 25 | daemon/runtime JVM；与编译toolchain分离 |
| Java toolchain | 21 | `jvmTarget JVM_21`；不是AGP runtime最低JDK声明 |
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

## Release closure：16/17 两时代均已关闭（17 最终由 Task 099 闭环）

16 时代（AOSP main 快照）Release closure 已于 Task 044 + task 060/060b/061 关闭：
`app/proguard_gradle.flags` 累计精确规则 = AssumeFalseForR8 `-dontwarn`（Task 044 同族 option A）+
`-dontobfuscate`（对齐 Soong dex.go:545）+ 3 行 CoreStartable 三件套 `-keep`（抗 R8 水平合并）。
该规则集与 `tools/tests/test_gradle_r8_adapter_rules.py` contract 测试钉住的历史边界对 17 重放
仍是起点；**17 基线的 Release/R8 闭环由 task074（编译/R8）+ Task 099（aconfig rewrite 后的
fresh Release 静态门 + runtime 门）接力完成**。16 时代 Release runtime 门（`d3968fb2…`，
emulator-5554）为历史台账。

## Next ordered work

1. **C6**：manifest 快照 + release tag + README/version/HANDOFF 收口（ADR 0007）。README 双语已于 2026-09-03 重写为对外文档；剩余为 manifest 快照与 release tag。
2. **尾账**：SDK 老备份清理（待用户确认）、`tracinglib-platform.jar` 溯源、依赖/pytest 维护性观察。
3. **Task 079 broad replay**：继续暂停，除非用户明确重新授权。

## Verification commands and evidence

```bash
# SysUISdk 单入口重建（live SDK 已按 AOSP-17 重建；仅需再生时运行）
uv run python tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp

# 单元测试（Python 工具测试；当前 361 passed +151 subtests）
uv run pytest tools/tests -q

# 源码对齐（17 基线；strict exit 0，MODIFIED 仅白名单）
uv run python tools/check_source_alignment.py --strict

# Gradle 配置解析
./gradlew help
./gradlew projects

# Debug APK（静态门 + runtime 均已 PASS，SHA `33e07319…`）
./gradlew :app:assembleDebug --console=plain

# Release R8 / 完整 Release（静态门 + runtime 均已 PASS，SHA `17358f4d…`）
./gradlew :app:assembleRelease --console=plain

# APK 引用完整性指令级门禁（Task 099；任何非 self-ref old-owner ref 或 hidden 定义即 FAIL）
uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/debug/app-debug.apk
uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/release/app-release.apk
```

**当前（17 基线，2026-09-03）证据**：双 variant 全门 PASS——Debug `33e07319…`（200,506,573 B）
与 Release `17358f4d…`（45,030,130 B，2 DEX）均通过：fresh 构建、指令级静态门禁（0 违规、
0 hidden 定义）、部署（staged-SHA + 原子 mv）、冷启动与整机重启门（PID 稳定、0 FATAL、
StatusBar/NotificationShade/Wallpaper 在屏）。pytest 361 passed（+151 subtests）；源码对齐
strict exit 0；buildSrc 11/11。aconfig 生产 seam：完整 725 条 AOSP repackaging 规则
（`gradle/aosp17-aconfig-repackaging-rules.txt`，SHA-pin、漂移 fail-closed）+ instrument-everything
reference-only visitor + 指令级 checker（FAIL = 非 self-ref old-owner ref 或 hidden target 定义）。
旧"健康"APK 前提已被 A/B 实验证伪（byte-identical 旧 APK 在当前 emulator 同样 crash-loop）。
Task 098 的 `dreams.Flags` 崩溃与其后发现的 460/446 条 old-owner refs 均由同一覆盖缺口
解释，Task 099 修复后归零。证据根：`/tmp/task099-c5-dreams-flags-diagnosis/`；完整记录见
`docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md`。

**Task 081–097 历史摘要（build-logic 攻关，细节见各 issue）**：task081 证明 app-only
`InstrumentationScope.ALL` reference-only plugin 的 build logic；task082–084 将真实 Debug pipeline
失败的最深 literal path 固定为 `InstrumentationContext_Decorated.__apiVersion__` → factory
`__instrumentationContext__`；task085–094 通过一系列 control 实验（含 CACHE_ACTIVATED_ISOLATION_FAILURE）
定位到 immutable managed-value seam；task095 完成 production 迁移；task096/097 分别取得 fresh
Debug/Release build/static PASS（SHA `f3af35d9…` / `641c6533…`，四-rule seam）。上述 APK 已被
Task 099 的 725-rule instrument-everything APK 取代，不再作为当前证据。

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
