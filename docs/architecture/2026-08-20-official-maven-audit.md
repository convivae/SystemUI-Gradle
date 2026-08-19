# 官方 Maven 可用性全量审计报告（Task 026）

日期：2026-08-20 · worktree：`SystemUI-Gradle-wt-026` · 性质：**report-only，试验改动全部已 revert**

## 1. 背景与目标

执行用户 2026-08-19 明确的依赖优先级原则：**官方 Maven 坐标 > 本地 jar > 本地 Maven AAR**。
对 `libs/` 全部产物逐一核查公网官方坐标（Google Maven `dl.google.com/dl/android/maven2` /
Maven Central `repo1.maven.org/maven2`），对候选者在 worktree 内试替换并构建验证，产出决策矩阵。
本报告为唯一交付物；落地替换需用户批准后另行实施。

## 2. 盘点口径修正

- Brief 写 48 个产物（32 jar + 16 AAR）；实测 `libs/*.jar` 31 个 + `libs/prebuilts/*.jar` 1 个 = **32 jar**，
  `libs/maven/` 下 AAR **17 个 artifact**（SettingsLibSettingsTheme、color、LowLightDreamLib、
  WifiTrackerLib、WM-Shell×2、animationlib、iconloader、setupcompat、SettingsLib 主件 + 7 个
  per-target 件），合计 **49 个产物**，全部纳入审计（brief 少计 1 个 AAR，无遗漏）。
- 网络证据统一以 `curl -sS -o /dev/null -w '%{http_code}'` 探测 `maven-metadata.xml`（或具体版本文件），
  HTTP 200 = 官方坐标存在；404 = 不存在。所有 URL 于 2026-08-20 亲测。

## 3. 逐产物判定表（32 jar）

| # | 产物 | 包名/内容 | 消费点 | 官方坐标探测 | 判定 |
|---|------|-----------|--------|--------------|------|
| 1 | `framework.jar` | android.*（框架隐藏 API） | 全模块 compileOnly | 概念上无公网物（平台私有） | AOSP-only，保留 |
| 2 | `framework-statsd.jar` | android.app/os, com.android.internal.statsd | core compileOnly | 同上 | AOSP-only，保留 |
| 3 | `android.car.jar` | android.car.* | core compileOnly | `androidx.car.app:car-app` gm 404（且非同类库） | AOSP-only，保留 |
| 4 | `android-merged.jar` | 合并 SDK 原料 | `tools/build_sysuisdk.py` | 平台构建原料，非依赖 | 保留（工具链输入） |
| 5 | `android_module_lib_stubs_current.jar` | android.* module stubs | core compileOnly | 平台私有 | AOSP-only，保留 |
| 6 | `monet.jar` | com.android.systemui.monet + com.google.ux.material.libmonet | core/customization compileOnly | `com.android.systemui:monet` gm/mc 404；`com.google.android.material:libmonet` gm/mc 404 | AOSP-only，保留 |
| 7 | `systemui-flags.jar` | com.android.systemui.Flags（aconfig） | core/animation/root | aconfig 生成物，无公网物 | AOSP-only，保留 |
| 8 | `systemui-shared-flags.jar` | com.android.systemui.shared.Flags | core/animation/shared | 同上 | AOSP-only，保留 |
| 9 | `settingslib-flags.jar` | com.android.settingslib.flags.Flags | core compileOnly | 同上 | AOSP-only，保留 |
| 10 | `settingslib-media-flags.jar` | com.android.settingslib.media.flags.Flags | core | 同上 | AOSP-only，保留 |
| 11 | `device-state-flags.jar` | com.android.server.policy.feature.flags.Flags | core | 同上 | AOSP-only，保留 |
| 12 | `wifi-flags.jar` | com.android.wifi.flags.Flags | core compileOnly | 同上 | AOSP-only，保留 |
| 13 | `wm-shell-flags.jar` | com.android.wm.shell.Flags? | core compileOnly | 同上 | AOSP-only，保留 |
| 14 | `SystemUI-proto.jar` | com.android.systemui.*.nano（nano proto 生成码） | core implementation | 生成物 | AOSP-only，保留 |
| 15 | `SystemUI-statsd.jar` | com.android.systemui.shared.system | core | 生成物 | AOSP-only，保留 |
| 16 | `SystemUI-tags.jar` | com.android.systemui（event-logtags 生成码） | core | 生成物 | AOSP-only，保留 |
| 17 | `SettingsLib-full.jar` | com.android.settingslib.*（闭包 jar） | core compileOnly | `com.android.settingslib:settingslib` gm 404 | AOSP-only，保留 |
| 18 | `SettingsLib-javac.jar` | com.android.settingslib.* | **无消费点（ORPHAN）** | 同上 | 建议单独 git rm（§6 Batch 2） |
| 19 | `zxing-core.jar` | com.google.zxing.* | core implementation | **MC 200**：`com.google.zxing:core`，AOSP METADATA 版本 `zxing-3.5.2`，latest 3.5.4 | **官方可替换（已试替换 PASS）** |
| 20 | `libprotobuf-java-nano.jar` | com.google.protobuf.nano(+.android 3 类) | core implementation | **MC 200**：`com.google.protobuf.nano:protobuf-javanano`，最新 3.1.0（另有 3.2.0rc2） | **官方可替换（已试替换 PASS）** |
| 21 | `keepanno-annotations.jar` | com.android.tools.r8.keepanno.annotations | core compileOnly | gm/mc `com.android.tools.r8:keepanno-annotations` 404；r8-releases bucket 404；`com.android.tools:keep(-annotations)` 404（共 5 URL） | **无官方坐标**，保留本地 |
| 22 | `dynamicanimation-1.1.0-alpha04.jar` | androidx.dynamicanimation.animation | unfold compileOnly | **GM 200**：`androidx.dynamicanimation:dynamicanimation:1.1.0`（公网无 alpha04；stable 1.1.0 类集合与本地 alpha04 **完全一致**，diff 为空） | **官方可替换（已试替换 PASS）** |
| 23 | `msdl.jar` | com.google.android.msdl.* | core compileOnly | `com.google.android.msdl` gm/mc 404 | AOSP-only，保留 |
| 24 | `view_capture.jar` | ViewCapture 闭包（android.support/androidx 混合 fat jar） | core/shared | `com.android.systemui:view-capture` gm/mc 404；无任何公网物 | AOSP-only，保留 |
| 25 | `prebuilts/tracinglib-platform.jar` | com.android.app.tracing(.coroutines) | core/compose/common/shared | `com.android.app.tracing` gm 404（androidx.tracing 是另一库，已在 catalog） | AOSP-only，保留 |
| 26 | `motion_tool_lib.jar` | com.android.app.motiontool | core compileOnly | 平台私有 | AOSP-only，保留 |
| 27 | `contextualeducationlib.jar` | com.android.systemui.contextualeducation | core implementation | `com.google.android:contextualeducation` gm 404 | AOSP-only，保留 |
| 28 | `PlatformMotionTestingComposeValues.jar` | platform.test.motion.compose.values | core implementation | `platform:test:motion` gm 404 | AOSP-only，保留 |
| 29 | `TraceurCommon.jar` | com.android.traceur | core compileOnly | `com.android.systemui:traceur` gm 404 | AOSP-only，保留 |
| 30 | `traceur-res-R.jar` | com.android.traceur.res.R | core compileOnly | 生成物 | AOSP-only，保留 |
| 31/32 | `compilelib-debug.jar` / `compilelib-release.jar` | com.android.systemui.util | core debug/release implementation | `com.android.systemui:compilelib` gm 404 | AOSP-only，保留 |

## 4. 逐产物判定表（17 个 `libs/maven/` AAR）

全部为 AOSP 源库打包（`tools/package_aosp_aar.py` → `install_aar_to_maven.py`），公网均无官方物：

| # | Artifact（catalog alias） | AOSP 源 | 官方坐标探测（均 404） | 判定 |
|---|--------------------------|---------|------------------------|------|
| 1 | `com.android.systemui:SettingsLib` | frameworks/base/packages/SettingsLib | `com.android.settingslib:SettingsLib`、`com.android.systemui:SettingsLib` gm 404 | AOSP-only，保留 |
| 2–8 | SettingsLib{ActionButtonsPreference, AdaptiveIcon, LayoutPreference, ProgressBar, RestrictedLockUtils, SelectorWithWidgetPreference, TwoTargetPreference} | SettingsLib 子模块 | gm `com.android.settingslib:*` 404 | AOSP-only，保留 |
| 9 | `SettingsLibSettingsTheme` | SettingsLib/SettingsTheme | gm 404 | AOSP-only，保留 |
| 10 | `com.android.settingslib:color` | SettingsLib/Color | gm 404 | AOSP-only，保留 |
| 11 | `com.android.systemui:setupcompat` | external/setupcompat | `com.google.android.setupcompat:setupcompat` gm/mc 404（确认 brief 猜测：**不在公网**） | AOSP-only，保留 |
| 12 | `WifiTrackerLib` | frameworks/opt/net/wifi/libs/WifiTrackerLib | gm/mc 多路径 404 | AOSP-only，保留 |
| 13/14 | `WindowManager-Shell`(+`-shared`) | frameworks/base/libs/WindowManager/Shell | gm `com.android.wm.shell`、mc `com.android.systemui:WindowManager-Shell` 404 | AOSP-only，保留 |
| 15 | `animationlib` | frameworks/libs/systemui:animationlib | gm/mc 404 | AOSP-only，保留 |
| 16 | `iconloader` | frameworks/libs/systemui:iconloaderlib | gm/mc 404 | AOSP-only，保留 |
| 17 | `LowLightDreamLib` | frameworks/base/libs/dream/lowlight | gm/mc 多路径 404 | AOSP-only，保留 |

> SettingsLib 家族、WM-Shell、WifiTrackerLib 等在 AOSP `Android.bp` 中均被 AOSP fork 或平台 API
> 耦合（`android.internal`、`@*android:` 资源、隐藏 API），即便存在同名公库也不可替换（tier② 判定成立）。

## 5. 试替换矩阵（协议：改 → 构建 → revert）

基线（本 worktree，试验前）：`:app:assembleDebug` → **BUILD SUCCESSFUL in 3m 5s**（216 tasks）。

| 候选 | 替换 | 改动点 | 验证 | 结果 |
|------|------|--------|------|------|
| zxing-core | `files(zxing-core.jar)` → `libs.zxing.core` = `com.google.zxing:core:3.5.2` | `libs.versions.toml`（+version/+alias）、`SystemUI-core/build.gradle.kts:217` | `:app:assembleDebug` → BUILD SUCCESSFUL in 1m 12s；`dependencies --configuration debugRuntimeClasspath` → `+--- com.google.zxing:core:3.5.2` | **PASS** |
| protobuf-javanano | `files(libprotobuf-java-nano.jar)` → `libs.protobuf.javanano` = `com.google.protobuf.nano:protobuf-javanano:3.1.0` | `libs.versions.toml`、`SystemUI-core/build.gradle.kts:225` | `:app:assembleDebug` → BUILD SUCCESSFUL in 1m 8s；classpath → `+--- com.google.protobuf.nano:protobuf-javanano:3.1.0` | **PASS** |
| dynamicanimation（unfold） | `compileOnly(files(dynamicanimation-1.1.0-alpha04.jar))` → `compileOnly(libs.androidx.dynamicanimation)`（1.1.0，已在 catalog） | `SystemUI-unfold/build.gradle.kts:57` | `:SystemUI-unfold:compileDebugKotlin` + `:app:assembleDebug` → BUILD SUCCESSFUL in 1m；compileClasspath → `+--- androidx.dynamicanimation:dynamicanimation:1.1.0` | **PASS** |
| keepanno-annotations | 无官方坐标（5 URL 全 404） | — | — | 不适用，保留本地 |
| setupcompat | 无官方坐标（gm/mc 404） | — | — | 不适用，保留本地 |

试替换通过率：**3/3（100%）**；每次试验后 `git checkout` 还原，最终 `git status` 干净（见 §7）。

### 5.1 差异与风险记录

- **zxing**：本地 jar 类集合是官方 3.5.2 的**真子集**（官方多出 10 个 javac 合成 `$1` 匿名类，无 API 缺失）。
  版本选择：AOSP `external/zxing/METADATA` 钉在 `zxing-3.5.2`（推荐，对齐 AOSP）；公网 latest 3.5.4 亦可用（用户偏好最新，二选一由用户定）。
- **protobuf-javanano**：本地 jar 比官方 3.1.0 多 3 个 AOSP 私有类 `com.google.protobuf.nano.android.{ParcelableExtendableMessageNano, ParcelableMessageNano, ParcelableMessageNanoCreator}`。
  全仓源码与 `SystemUI-proto.jar` 生成码**均不引用**（proto 类全部直接继承 `MessageNano`）；这 3 个类由
  `framework.jar`（compileOnly）与设备 platform framework 在编译/运行时兜底提供。官方 3.1.0 落地无适配成本。
  注意官方线已死（最后版本 3.1.0/3.2.0rc2），与 AOSP fork 永久分叉，属可接受的钉版。
- **dynamicanimation**：官方 stable 1.1.0 与 AOSP alpha04 prebuilt 的 `.class` 文件清单**逐字节集完全一致**（diff 为空），
  unfold 所需 `SpringAnimation.scheduler`/`FrameCallbackScheduler` API 均在；且运行时其余模块本就以官方 1.1.0 打包，
  替换后消除"编译看 alpha04、运行用 1.1.0"的版本混挂。
- **附带发现**：`libs/SettingsLib-javac.jar` 为 ORPHAN（无任何 build 消费点），属死产物。
- **附带发现**：`tools/package_aconfig_jars.py` 内嵌 zxing/protobuf 打包映射；落地替换时应同步退役对应条目（属 tools 脚本小改，随落地 commit 一并处理）。

## 6. 落地建议（分批，待用户批准）

- **Batch 1（零风险，3 处替换 + 3 个 jar 退役）**：
  1. catalog 增 `com.google.zxing:core:3.5.2` + `com.google.protobuf.nano:protobuf-javanano:3.1.0`；
  2. core 两行 `files(...)` 换 alias；unfold `compileOnly` 换 `libs.androidx.dynamicanimation`；
  3. `git rm libs/zxing-core.jar libs/libprotobuf-java-nano.jar libs/dynamicanimation-1.1.0-alpha04.jar`；
  4. `tools/package_aconfig_jars.py` 退役 zxing 条目（如有 protobuf 条目同理）；
  5. 验证 `:app:assembleDebug`。
- **Batch 2（清理）**：`git rm libs/SettingsLib-javac.jar`（ORPHAN）。
- **不動（44 个）**：其余产物均无官方坐标或为 AOSP fork，维持本地 jar / 本地 Maven AAR 形态；
  `keepanno-annotations` 保留 AOSP prebuilt（`prebuilts/r8`）。

## 7. 验证记录

- 基线构建：`:app:assembleDebug` → BUILD SUCCESSFUL in 3m 5s（2026-08-20，本 worktree）。
- 三次试替换各自 `:app:assembleDebug`（及 unfold compile）均 BUILD SUCCESSFUL，classpath 亲验解析到官方坐标。
- 试验后 `git checkout` 还原：`git status --short` 输出为空（干净）。
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → **Ran 148 tests ... OK**。
- 最终 commit 仅含：本报告、brief 勾选、`docs/issues/2026-08-20-official-maven-audit.md`。未 push。

## 8. 结论

49 个产物中仅 3 个（zxing-core、libprotobuf-java-nano、dynamicanimation-alpha04）存在官方等价物且全部
试替换通过；`keepanno-annotations` 与 `setupcompat` 确认无公网物；其余 42 个 + 1 个 orphan 均为 AOSP
特有产物，官方优先级原则下已无更多可迁移项。用户批准后按 §6 Batch 1/2 落地。
