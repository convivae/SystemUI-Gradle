# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-08-21（Task 041 合并后 main fresh 验证，commits `f51caf76` + `3379600d` + `5d4d62ea` + `344aa344`）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| Debug APK | **`:app:assembleDebug` SUCCESS**（每批硬门禁；Task 041 main fresh 1m18s） |
| Python 工具测试 | **233/233 通过** |
| Release R8 | **仍失败**：1 个真实 missing ref（`AssumeTrueForR8`；Task 042 边界，非成功状态） |
| `shrinkResources` | 未完成有效验收 |
| 设备/模拟器运行验证 | 未开始 |
| 当前唯一工程优先级 | **Task 042：`AssumeTrueForR8` build-time annotation 1 ref** |

R8 missing refs 轨迹：140 → 126 → 119 → 109 → 106 → 88 → 81 → 7 → **1**（每批精确差分，零新增未解释引用）。

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

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| KSP（debug/release） | ✅ 0 错误（2933 文件生成） | Task 041 main fresh |
| core Kotlin | ✅ 0 错误 | Task 041 main fresh |
| core javac | ✅ 0 错误 | Task 041 main fresh |
| `:app:assembleDebug` | ✅ BUILD SUCCESSFUL（硬门禁，每批必过） | Task 041 main fresh，exit 0 in 1m18s |
| Python 工具测试 | ✅ 233/233 | Task 041 main fresh |
| APK 类定义检查 | ✅ SysUISdk bridge 35/35 present；APK 0/35 packaged | Task 041 main fresh |
| `:app:minifyReleaseWithR8` | ❌ 预期失败：1 个 missing ref（Task 042 边界） | Task 041 main fresh，exit 1，精确 7→1 |
| `shrinkResources` 有效验收 | ❌ 未完成 | — |
| 设备/模拟器 install + runtime | ❌ 未开始 | `docs/issues/2026-08-20-device-emulator-validation-plan.md` |

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
- 本地 Maven AAR（`libs/maven/`）均为确定性产物：SettingsLib 1.0.1（1153 类；POM 携 17 条 per-target 依赖边，ADR 0005）、SettingsLibSettingsTheme 1.0.1（15 类）、17 个 SettingsLib per-target res-only AAR、WindowManager-Shell 1.0.1（含 proto 闭包 1888 类）、iconloader 1.0.1（75 类）、animationlib、WifiTrackerLib、LowLightDreamLib、setupcompat、SettingsLibColor。
- Traceur：双直接 AAR（TraceurCommon 640 类 + Traceur-res 105 res，Task 038）；占位 jar 已退役。
- 官方 Maven 坐标优先（Task 026 审计后）：zxing、protobuf-javalite、coroutines 1.10.2、errorprone 等走公网；AOSP prebuilts 版本多数不在公网，逐个查 `maven-metadata.xml`。
- aconfig flags：五个完整 Soong `javac` 产物 JAR（Task 034，位于 `libs/` 根目录）；notification flags 已从本地 Maven 迁出，现为 `libs/notification-flags.jar`。
- `libs/prebuilts/` 仅剩 `tracinglib-platform.jar`（历史遗留，逐步清理）。

## Release closure blocker（1 个）

Release R8 在 `:app:minifyReleaseWithR8` 阶段因唯一真实 missing ref 失败（exit 1，这是**预期失败**，不是成功状态）：

| 组 | 数量 | 内容 | 处置路径 |
|----|------|------|---------|
| Task 042 | 1 | `com.android.aconfig.annotations.AssumeTrueForR8` | build-time annotation classpath；保留 R8 flag-assumption 语义，禁止 runtime `implementation` 或 `-dontwarn` |

Task 041 已通过声明式 SysUISdk S3b bridge 清零 B1–B4 的 6 个 platform/build refs；两个 SDK target 各有 35 个真实 library classes，且 APK 中 0 个被打包。

## Next ordered work

1. **Task 042：`AssumeTrueForR8` 1 ref**（当前唯一工程优先级）
2. release R8 达到 0 missing refs
3. `shrinkResources` + 签名/打包验证
4. 兼容模拟器/设备安装与运行验证（见 `docs/issues/2026-08-20-device-emulator-validation-plan.md`）

## Verification commands and evidence

```bash
# 单元测试（Python 工具测试）
python3 -m unittest discover -s tools/tests -p 'test_*.py'   # 当前 233/233

# Debug APK（每批硬门禁）
./gradlew :app:assembleDebug --console=plain

# Release R8（当前预期 exit 1，唯一 missing ref 为 AssumeTrueForR8）
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain
```

最新证据：Task 041 main fresh（2026-08-21）— 233/233 tests；两个独立 staging SDK 构建成功，`android.jar` 与 `core-for-system-modules.jar` 各有 35 个 source-identical entries 且 A/B `name→CRC` inventory 一致；guarded `--apply` 后 S5 `ALL PASS`；`:app:checkDebugDuplicateClasses :app:assembleDebug` exit 0（1m18s）；APK `BRIDGED=35 PACKAGED=0`；fresh R8 exit 1（2m09s），精确 7→1（6 removed、0 added），唯一 remaining 为 `com.android.aconfig.annotations.AssumeTrueForR8`。详细证据：`docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`、`docs/orchestration/STATE.md`、`docs/orchestration/log.md`。

构建纪律：全系统同一时刻**只允许一个 Gradle build**（CHARTER Part 4）；每批必须保持 `:app:assembleDebug` 成功（硬门禁）。

## Historical pointers

- 错误数/迁移历史：`docs/GRADLE_MIGRATION_LOG.md`（append-only）
- 深度调研与 audit：`docs/architecture/`（含 active operational audit `2026-08-20-r8-runtime-closure-audit.md`）
- 每日问题记录：`docs/issues/`
- 踩坑经验：`docs/PITFALLS.md`
- 未完成路线：`docs/PLAN.md`
