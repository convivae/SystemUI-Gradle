# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-08-21（Task 044 merged；架构师在 main fresh 验证 239/239、Debug、Release R8 0 refs、完整 optimized-resource Release、APK 内容与 V2 签名；设备验证未运行）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| Debug APK | **`:app:assembleDebug` SUCCESS**（每批硬门禁；Task 044 main fresh 8s） |
| Python 工具测试 | **239/239 通过**（Task 044 main fresh，含 6 个 adapter contract 测试） |
| Release R8 | **SUCCESS（Task 044 main fresh，exit 0，missing refs 1→0）**：option A 单 FQN release-only adapter（`app/proguard_gradle.flags`） |
| `:app:assembleRelease` | **SUCCESS（main fresh）**：minify + AGP 9.3.1 optimized resource shrink + V2 签名；APK 28,600,808 B，SHA-256 `1f7a7f8f...` |
| 设备/模拟器运行验证 | **未运行**（构建完成 ≠ 装机验证；另行排期） |
| 当前唯一工程优先级 | 设计并审批单入口、AOSP `out/` 驱动的 SysUISdk composition；先冻结 artifact 映射和 exact Worker brief，再实施与删除已证明被替代的仓库文件 |

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
| 2026-08-21 | **完整 Release closure（Task 044，main fresh）**：单 FQN release-only adapter；R8 1→0；`assembleRelease` + optimized resource shrink + V2 签名成功；APK 28,600,808 B；239/239 | `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md` |

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| KSP（debug/release） | ✅ 0 错误（2933 文件生成） | Task 041 main fresh |
| core Kotlin | ✅ 0 错误 | Task 041 main fresh |
| core javac | ✅ 0 错误 | Task 041 main fresh |
| `:app:assembleDebug` | ✅ BUILD SUCCESSFUL（硬门禁，每批必过） | Task 044 main fresh，exit 0 in 8s（含 checkDebugDuplicateClasses） |
| Python 工具测试 | ✅ 239/239（含 Task 044 新增 6 个 adapter contract 测试） | Task 044 main fresh |
| APK 类定义检查 | ✅ SysUISdk bridge 35/35 present；APK 0/35 packaged | Task 041 main fresh |
| `:app:minifyReleaseWithR8` | ✅ exit 0，missing refs 0；effective config 对 FQN 仅一条 exact `-dontwarn`，无 keep/assume | Task 044 main fresh（`--rerun-tasks`，3m09s） |
| `:app:assembleRelease` | ✅ BUILD SUCCESSFUL：resource shrinking **技术性已验证**（`optimizeReleaseResources` + `convertShrunkResourcesToBinaryRelease` 实际执行）；brief 原字面 `shrinkReleaseRes` 判据不可满足及 Worker 未先 REDLINE 的流程偏差均保留在审查裁定中 | Task 044 main fresh，exit 0（3m47s；首次尝试因 host OOM 被 kernel kill，清理孤立 Kotlin daemon 后无代码变更重试成功） |
| Release APK 检查 | ✅ 非空 28,600,808 B，SHA-256 `1f7a7f8fdb1fb7948754356f3ef6679e654127078dd7f831c92cce87ca1805ef`；`unzip -t` 无错；dex 无 `AssumeTrueForR8`；V2 scheme true | Task 044 main fresh |
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
| compileSdk | `SysUISdk`（自定义 preview） | 可由 tracked inputs 从零重建（`tools/build_sysuisdk.py --apply`） |
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

1. **SysUISdk 单入口 composition 设计与实施**：先冻结从传入 AOSP `out/` 到 `android.jar`、`core-for-system-modules.jar`、framework resources、AIDL 与 39 个 bridge classes 的确定性 artifact 映射；向用户展示并批准 exact Worker brief 后，再以 TDD 实施 `python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp`
2. 新 SysUISdk 完成 Debug/Release 等价验证后，退役并删除已证明被替代的仓库脚本/文件；外部 9 个历史 SDK 备份只做独立 inventory，未经不可逆删除批准不动
3. 兼容模拟器/设备安装与运行验证：platform-signed Release APK install → SystemUI restart → 无启动崩溃/logcat 检查
4. Gradle-native 架构 Phase 2：逐项讨论 Task 043 ledger 的其余 7 个 `NOT APPROVED` packet

## Verification commands and evidence

```bash
# 单元测试（Python 工具测试）
python3 -m unittest discover -s tools/tests -p 'test_*.py'   # 当前 239/239

# Debug APK（每批硬门禁）
./gradlew :app:assembleDebug --console=plain

# Release R8（Task 044 后 exit 0，missing refs 0）
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain

# 完整 Release（minify + optimized resource shrink + V2 签名）
./gradlew :app:assembleRelease --console=plain
```

最新证据：Task 044 main fresh（2026-08-21）— 239/239 tests；`:app:checkDebugDuplicateClasses :app:assembleDebug` exit 0（8s）；`:app:minifyReleaseWithR8 --rerun-tasks` exit 0（3m09s）、missing refs 0、effective config 对 FQN 仅一条 exact `-dontwarn`；完整 `assembleRelease --no-daemon` exit 0（3m47s），AGP-native optimized resource tasks 均执行；APK 28,600,808 B，SHA-256 `1f7a7f8fdb1fb7948754356f3ef6679e654127078dd7f831c92cce87ca1805ef`，ZIP/dex/V2 gates 全过。首次 main Release 尝试被 Linux OOM killer 终止（Gradle daemon anon RSS 15,227,120 KiB，另有孤立 Kotlin daemon RSS 8,840,516 KiB）；终止孤立 daemon 后未改代码重试成功。**设备/模拟器验证未运行。** 详细证据：`docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`。

构建纪律：全系统同一时刻**只允许一个 Gradle build**（CHARTER Part 4）；每批必须保持 `:app:assembleDebug` 成功（硬门禁）。

## Historical pointers

- 错误数/迁移历史：`docs/GRADLE_MIGRATION_LOG.md`（append-only）
- 深度调研与 audit：`docs/architecture/`（含 active operational audit `2026-08-20-r8-runtime-closure-audit.md`）
- 每日问题记录：`docs/issues/`
- 踩坑经验：`docs/PITFALLS.md`
- 未完成路线：`docs/PLAN.md`
