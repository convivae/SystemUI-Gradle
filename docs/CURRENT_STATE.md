# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-08-21（Task 045 Worker worktree：单入口 SysUISdk 生成器实现并通过全部功能门禁 — 220/220 Python、两次确定性真实 AOSP 构建、Debug、fresh R8 0 refs、完整 optimized Release + V2 签名 + 0/39 bridge 打包；七个已替代仓库文件已删；设备验证未运行。待架构师 main fresh 复验）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| Debug APK | **`:app:assembleDebug` SUCCESS**（每批硬门禁；Task 045 Worker worktree 对**生成 SDK** 验证 2m57s） |
| Python 工具测试 | **220/220 通过**（Task 045 Worker worktree；删 36 个 legacy patch 测试 + 新 70 个单入口生成器测试） |
| Release R8 | **SUCCESS（Task 045 Worker worktree，exit 0，missing refs 0）**：对生成 SDK fresh `--rerun-tasks` 3m14s |
| `:app:assembleRelease` | **SUCCESS（Task 045 Worker worktree）**：minify + AGP 9.3.1 optimized resource shrink + V2 签名；APK 28,600,808 B，SHA-256 `d53f815c...`（生成 SDK 构建） |
| SysUISdk 生成器 | **单入口落地（Task 045）**：`python3 tools/build_sysuisdk.py --aosp-root <aosp>`；确定性、事务性、39-entry bridge；两次独立构建逐字节相等 |
| 设备/模拟器运行验证 | **未运行**（构建完成 ≠ 装机验证；另行排期） |
| 当前唯一工程优先级 | 架构师 review/merge Task 045 并在 main fresh 复验；随后兼容模拟器/设备安装与运行验证 |

R8 missing refs 轨迹：140 → 126 → 119 → 109 → 106 → 88 → 81 → 7 → 1 → **0（Task 044）**。该轨迹继续作为诊断证据，但不再驱动 artifact seam 或要求 Soong/Gradle 输出一致。

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
| 2026-08-21 | **完整 Release closure（Task 044，main fresh）**：单 FQN release-only adapter；R8 1→0；`assembleRelease` + optimized resource shrink + V2 签名成功；APK 28,600,808 B；239/233 | `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md` |
| 2026-08-21 | **SysUISdk 单入口 composition（Task 045，Worker worktree）**：`build_sysuisdk.py` 重写为事务性单命令生成器；两次真实 AOSP 构建逐字节相等；生成 SDK 上 Debug/R8/Release 全绿；七个 superseded 仓库文件已删；220/220 | `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md` |

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| KSP（debug/release） | ✅ 0 错误（2933 文件生成） | Task 041 main fresh |
| core Kotlin | ✅ 0 错误 | Task 041 main fresh |
| core javac | ✅ 0 错误 | Task 041 main fresh |
| `:app:assembleDebug` | ✅ BUILD SUCCESSFUL（硬门禁，每批必过） | Task 045 Worker worktree（对生成 SDK，exit 0 in 2m57s，含 checkDebugDuplicateClasses；删除后回归 14s） |
| Python 工具测试 | ✅ 220/220（Task 045：70 个新单入口生成器测试；36 个 legacy patch 测试随被删模块退役） | Task 045 Worker worktree |
| APK 类定义检查 | ✅ SysUISdk bridge 39/39 present in SDK；APK 0/39 packaged；无 `AssumeTrueForR8` | Task 045 Worker worktree（dexdump 15,683 defined classes 全量检查） |
| `:app:minifyReleaseWithR8` | ✅ exit 0，missing refs 0；effective config 对 FQN 仅一条 exact `-dontwarn`，无 keep/assume | Task 045 Worker worktree（对生成 SDK，`--rerun-tasks`，3m14s） |
| `:app:assembleRelease` | ✅ BUILD SUCCESSFUL：resource shrinking（`optimizeReleaseResources` + `convertShrunkResourcesToBinaryRelease` 实际执行） | Task 045 Worker worktree，exit 0（3m55s） |
| Release APK 检查 | ✅ 非空 28,600,808 B，SHA-256 `d53f815ca9a72570f3be55e3f9bd25f1ac64c9c166adca6c2adf886fb7f9a14f`（生成 SDK 构建）；`unzip -t` 无错；V2 scheme true | Task 045 Worker worktree |
| SysUISdk 单入口生成器 | ✅ 两次独立真实 AOSP 构建输出逐字节相等（11382 文件）；refusal/replace 语义实测；marker 纯 provenance | Task 045 Worker worktree（`/tmp/task045-sdk-{a,b}`） |
| 设备/模拟器 install + runtime | ❌ 未运行（构建完成不等于装机验证） | `docs/issues/2026-08-20-device-emulator-validation-plan.md` |

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
| compileSdk | `SysUISdk`（自定义 preview） | 可由 AOSP `out/` 从零重建：`python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp`（Task 045 单入口；默认 base `android-37.0`，输出 `<sdk-root>/platforms/android-SysUISdk`） |
| kotlinx-coroutines | 1.10.2 | **上限**：1.11.0 新 `SharedFlow.collectLatest` overload 破坏 AOSP 源码（Task 035 REDLINE 裁定） |
| protobuf-javalite | 4.35.1 | latest-stable 政策（Task 035） |
| zxing | 3.5.4 | 官方 Maven 最新（Task 026/027） |

builtInKotlin 三件套（PITFALLS §1.5）：`android.builtInKotlin=true`、`android.disallowKotlinSourceSets=false`（Task 023 实验证实 REQUIRED）、每个 Android 模块 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`。

13-module 拓扑（语义对齐 AOSP `Android.bp`，ADR 0003）：

```
:app :SystemUI-core :SystemUI-res :SystemUI-common :SystemUI-animation
:SystemUI-plugin-core :SystemUI-plugin-processor :SystemUI-plugin
:SystemUI-unfold :SystemUI-customization :SystemUI-shared
:SystemUI-shared-biometrics :SystemUI-compose
```

## Dependency and artifact state

- `libs/`（jar + aars + maven）全部提交入 git；新 clone 可直接构建。仅在重新生成 AOSP 产物时运行 `python3 tools/package_aosp_aar.py --all` + `python3 tools/install_aar_to_maven.py`。
- 当前 artifact 数量是新架构只读审查的重点：`libs/maven/` 有 27 个 AAR，其中 20 个属于 SettingsLib family；`libs/aars/` 有 29 个 AAR。它们不是自动回退清单。
- 当前本地 Maven 交付包括 SettingsLib 1.0.1（1153 类；POM 携 17 条 per-target 依赖边，ADR 0005）、SettingsLibSettingsTheme 1.0.1（15 类）、17 个 SettingsLib per-target res-only AAR、WindowManager-Shell 1.0.1（含 proto 闭包 1888 类）、iconloader 1.0.1（75 类）、animationlib、WifiTrackerLib、LowLightDreamLib、setupcompat、SettingsLibColor。
- Traceur：双直接 AAR（TraceurCommon 640 类 + Traceur-res 105 res，Task 038）；占位 jar 已退役。
- 官方 Maven 坐标优先（Task 026 审计后）：zxing、protobuf-javalite、coroutines 1.10.2、errorprone 等走公网；AOSP prebuilts 版本多数不在公网，逐个查 `maven-metadata.xml`。
- aconfig flags：五个完整 Soong `javac` 产物 JAR（Task 034，位于 `libs/` 根目录）；notification flags 已从本地 Maven 迁出，现为 `libs/notification-flags.jar`。
- **Task 045 后**：`libs/android-merged.jar` 与 `libs/framework-res.apk` 已删除（被单入口生成器的 AOSP 输入取代）；`libs/keepanno-annotations.jar` 保留（`:SystemUI-core` 独立 compile-only 依赖）。
- `libs/prebuilts/` 仅剩 `tracinglib-platform.jar`（历史遗留，逐步清理）。

## Release closure：已关闭（Task 044）

最后一个 missing ref `com.android.aconfig.annotations.AssumeTrueForR8` 已按用户批准的 option A
关闭：`app/proguard_gradle.flags` 唯一 active rule 为 exact
`-dontwarn com.android.aconfig.annotations.AssumeTrueForR8`，仅接入 release build type（debug
与 5 个 AOSP-owned 规则文件未动）。不引入 annotation class/JAR/AAR、SysUISdk 变更或任何
assume/folding 规则；aconfig flag runtime 语义不变。Task 044 contract 测试
（`tools/tests/test_gradle_r8_adapter_rules.py`）机械钉住该边界。

**Resource-shrink 验收裁定**：brief 原字面判据（日志含 `:app:shrinkReleaseRes`）在 AGP 9.3.1
下不可满足（该任务已不存在）；Worker 未先提 REDLINE 而直接替换为 AGP-native 证据，属流程
偏差。双轴 review（base `3cc95a49` / head `4a0a8b08`）判 Spec FAIL BLOCKER；架构师向用户
披露后，用户批准继续，**post-review waiver** 接受 `optimizeReleaseResources` +
`convertShrunkResourcesToBinaryRelease` 实际执行的证据作为修正后的语义验收。详见
`docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`。

## Next ordered work

1. **Task 045 review/merge**：架构师双轴 review Worker worktree（commits `991b6302`/`76ad180f`/docs）并在 main fresh 复验（Python 220、Debug、R8、Release、APK/V2、确定性双构建）；外部 9 个历史 SDK 备份只做独立 inventory，未经不可逆删除审批不动
2. 兼容模拟器/设备安装与运行验证：platform-signed Release APK install → SystemUI restart → 无启动崩溃/logcat 检查
3. Gradle-native 架构 Phase 2：逐项讨论 Task 043 ledger 的其余 7 个 `NOT APPROVED` packet
4. 清理历史文档引用：`AGENTS.md` §7 表格仍列已删除的 `tools/install_sdk.py`（归 architect/用户处理）

## Verification commands and evidence

```bash
# SysUISdk 单入口重建（Task 045；需已构建的 AOSP out/）
python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp

# 单元测试（Python 工具测试）
python3 -m unittest discover -s tools/tests -p 'test_*.py'   # 当前 220/220

# Debug APK（每批硬门禁）
./gradlew :app:assembleDebug --console=plain

# Release R8（exit 0，missing refs 0）
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain

# 完整 Release（minify + optimized resource shrink + V2 签名）
./gradlew :app:assembleRelease --console=plain
```

最新证据：Task 045 Worker worktree（2026-08-21，生成 SDK 位于 `/tmp/task045-sdk-a`，私有 root 经 symlink 暴露官方 build-tools 等；`local.properties` 事后已恢复原状）— 220/220 tests；两次真实 AOSP 构建输出逐字节相等（11382 文件，各自 ~7s）；`:app:checkDebugDuplicateClasses :app:assembleDebug` exit 0（2m57s）；`:app:minifyReleaseWithR8 --rerun-tasks` exit 0（3m14s）、missing refs 0；`assembleRelease --no-daemon` exit 0（3m55s），`optimizeReleaseResources` + `convertShrunkResourcesToBinaryRelease` 均执行；APK 28,600,808 B，SHA-256 `d53f815ca9a72570f3be55e3f9bd25f1ac64c9c166adca6c2adf886fb7f9a14f`，`unzip -t` 无错，V2 scheme true，dexdump 全量 15,683 defined classes 中 0/39 bridge、无 `AssumeTrueForR8`。无 OOM/环境事件。**设备/模拟器验证未运行。** 详细证据：`docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`。（前一基线：Task 044 main fresh，APK SHA-256 `1f7a7f8f...`，详见其 issue。）

构建纪律：全系统同一时刻**只允许一个 Gradle build**（CHARTER Part 4）；每批必须保持 `:app:assembleDebug` 成功（硬门禁）。

## Historical pointers

- 错误数/迁移历史：`docs/GRADLE_MIGRATION_LOG.md`（append-only）
- 深度调研与 audit：`docs/architecture/`（含 active operational audit `2026-08-20-r8-runtime-closure-audit.md`）
- 每日问题记录：`docs/issues/`
- 踩坑经验：`docs/PITFALLS.md`
- 未完成路线：`docs/PLAN.md`
