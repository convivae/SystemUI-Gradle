# 13-module 拓扑实施后审查结论与后续路线

**日期**：2026-08-07
**审查范围**：`40ffb2b9e132bc1b0c57397744d2e74bc1e5c00b...1e457cad`
**当前 HEAD**：`1e457cad refactor: establish 13-module SystemUI topology`

## 背景

另一个 AI 已执行 `docs/superpowers/plans/2026-08-06-13-module-source-topology.md`。本次审查按两条轴进行：

1. **Standards**：是否符合 `AGENTS.md` 的 P/S/C/F/R/B/D/I 规则；
2. **Spec**：是否满足 13-module 计划各 Task 的接口和验收条件。

本文件记录审查结论、证据、遗留问题及下一个 AI 的执行顺序。详细可执行步骤见：

- `docs/superpowers/plans/2026-08-07-post-topology-correctness.md`

## 总结结论

### 可以验收的部分

13-module 的**架构与 owner 里程碑基本符合预期**：

- settings 已精确收敛为目标 13 module；
- `:app` 无源码，只直接 `implementation(project(":SystemUI-core"))`；
- 入口类仍属于 `:SystemUI-core`；
- SystemUI src/AIDL/res 当前文件集已经归位；
- animationlib 改为直接 AAR；compilelib 改为 debug/release JAR；
- kairos 未进入生产依赖图；
- `PluginProtectorStub.kt` 未恢复，也未新增其他源码 stub；
- `./gradlew projects` 可配置成功；
- `:SystemUI-animation` 和 `:SystemUI-shared-biometrics` 已有编译成功证据。

### 不能宣称完成的部分

13-module 计划的**完整编译与工具链验收尚未完成**：

- Task 6：`:SystemUI-compose:compileDebugKotlin` 未通过；
- Task 9：processor module/JAR/service descriptor 已建立，但 `PluginProtector` 没有生成；
- Task 10：隔离模块编译仅部分通过；
- `:SystemUI-core` 自身 Kotlin 编译尚未开始；
- `:app:assembleDebug` 尚未成功运行；
- SettingsLib/iconloader/WindowManager-Shell/WifiTrackerLib artifact recovery 尚未开始。

准确状态应写为：

> 13-module 拓扑迁移步骤已完成；源码/resource owner checkpoint 已建立；Task 6/9/10 的功能和编译验收仍为部分完成。

不能笼统写成“Task 1–10 全部验收完成”或“APK 已可构建”。

## 审查证据

审查时确认：

- 工作树在审查前后均干净；
- `git diff --check 40ffb2b9...HEAD`：通过；
- `python3 -m unittest discover -s tools/tests -v`：16 tests PASS；
- `python3 -m py_compile tools/*.py tools/tests/*.py`：通过；
- `python3 tools/check_source_alignment.py --strict`：exit 0；
- `./gradlew projects --console=plain`：BUILD SUCCESSFUL；
- `./gradlew :SystemUI-plugin-processor:jar --console=plain`：BUILD SUCCESSFUL；
- processor JAR 的 `META-INF/services/javax.annotation.processing.Processor` 内容正确；
- animationlib AAR 与 compilelib JAR 均通过 `unzip -t`。

这些证据只证明当前拓扑、当前文件集和部分独立产物，不证明 core/APK 已构建。

## Standards 发现

### S1：Plugin 遗漏真实 Compose runtime 依赖

`SystemUI-plugin/src/com/android/systemui/plugins/qs/TileDetailsViewModel.kt` 直接使用：

```kotlin
import androidx.compose.runtime.Composable
```

但 `SystemUI-plugin/build.gradle.kts` 当前没有 Compose runtime，且 `debugCompileClasspath` 中没有 `androidx.compose.runtime`。旧构建文件和 AOSP `plugin/Android.bp` 都声明过 Compose runtime。

这是被 `:SystemUI-common` 更早失败遮住的下一个真实 blocker。

**处理方向**：恢复与当前 Compose 模块一致的官方 Maven runtime 依赖，不复制源码、不打本地 JAR。

### S2：WindowManager-Shell prebuilt 与源码 module 有重复类

当前以下模块仍引用 `libs/WindowManager-Shell.jar`：

- `:app`
- `:SystemUI-core`
- `:SystemUI-animation`
- `:SystemUI-shared`

扫描发现该 JAR 至少含 48 个与 `:SystemUI-animation` 源码重复的 `com.android.systemui.animation.*` 顶层类，例如 `ActivityTransitionAnimator`、`DialogTransitionAnimator`。

这违反规则 S 的“源码与 prebuilt 不得重复提供同名类”。虽然当前依赖多为 `compileOnly`，仍可能造成编译期遮蔽。

**处理方向**：纳入后续 artifact-recovery 计划；不能假定从 JAR 换成 AAR 会自动消除 fat artifact 中的重复类。

### S3：当前交接文档存在过期和错误描述

已发现：

- HANDOFF 正文仍写 animationlib.jar 待改 AAR；
- HANDOFF 正文仍写 core 资源待迁出；
- Compose blocker 被写成缺 `androidx.core:core`。

正确 artifact 是：

```text
androidx.core:core-animation:1.0.0
```

AOSP `animation/Android.bp` 对应依赖名为 `androidx.core_core-animation`。

## Spec 发现

### P1：Plugin processor 边界完成，但功能输出未恢复

已完成：

- `:SystemUI-plugin-processor` 独立 JVM module；
- AOSP processor 源码归位；
- service descriptor 正确；
- processor JAR 可构建。

未完成：

- 8 个 `@ProtectedInterface` 都位于 Kotlin 源码；
- javac `AbstractProcessor` 看不到 Kotlin 声明；
- `PluginProtector.java` 不生成；
- `SystemUI-shared` 仍引用 `PluginProtector`。

用户已经裁决：不使用 KAPT，暂不授权 KSP processor 重写，不恢复 stub。因此该问题继续保留为显式 blocker，不能由后续 AI 擅自选择新方案。

### P2：Common 与 Compose 的隔离编译验收未通过

`:SystemUI-common`：

```text
android.icu.text.SimpleDateFormat unresolved
```

根因是纯 JVM module 不自动获得 AGP 的 SysUISdk android.jar；现有 `framework.jar` 不含 `android.icu`。

`:SystemUI-compose`：

```text
androidx.core.animation.Interpolator unresolved
```

根因是缺 `androidx.core:core-animation:1.0.0`，不是缺普通 `androidx.core:core`。

### P3：两个“确定性”打包器当前并不确定

以下脚本使用 `ZipFile.writestr(name, data)`，没有固定 ZIP entry 时间、权限等 metadata：

- `tools/package_aosp_aar.py`
- `tools/package_compilelib_jars.py`

重复生成会得到不同 SHA-256，与计划要求的 deterministic ZIP/JAR 不符。

### P4：source alignment 对重复 tail 的多合法 root 会漏报

`run_source_check()` 遇到目标 root 缺文件、但同 tail 存在于其他 root 时直接跳过 missing。对于同时合法存在于 `src-debug` 和 `src-release` 的四个文件，删除其中一个变体副本仍可能得到全 0。

最小复现实证结果：

```text
missing=0, misplaced=0, extra=0, modified=0
```

当前项目的四组文件实际仍在，所以当前 checkpoint 文件集没有因此缺失；但检查器无法保证未来仍“不漏”。

## 后续路线与边界

### Phase A：先完成确定性、无产品决策的修复

执行：

- `docs/superpowers/plans/2026-08-07-post-topology-correctness.md`

内容包括：

1. 修复 source alignment 多 root 漏报并加回归测试；
2. 修复 AAR/JAR 确定性并加双次生成字节一致测试；
3. 给 JVM `:SystemUI-common` 补 SysUISdk android.jar compile classpath；
4. 给 `:SystemUI-compose` 补 `androidx.core:core-animation`；
5. 给 `:SystemUI-plugin` 恢复 Compose runtime；
6. 重新取得隔离模块和 core 的第一真实 blocker；
7. 更新状态与交接文档。

### Phase A 执行进度

#### Task 1：修复多合法 root 的 MISSING 漏报 ✅

- 新增回归测试 `TestDuplicateTailAcrossExpectedRoots.test_missing_one_of_two_valid_roots_is_reported`。
- 先确认红：`missing=[]`，合法的 `src-release` 掩盖了 `src-debug` 缺失。
- 修复 `run_source_check()`：用 `aosp_idx` 算出该 tail 的全部合法 owner 集合 `expected_locs`，只有出现在不在该集合的位置才算 MISPLACED；合法的另一个 root 不再掩盖 MISSING。
- 验证：
  - `python3 -m unittest tools.tests.test_check_source_alignment -v` → 9 tests PASS。
  - `python3 tools/check_source_alignment.py --strict` → exit 0，全 0。

#### Task 2：AAR/JAR 打包字节确定性 ✅

- 新增 failing 测试：
  - `test_package_aosp_aar.TestAssembleAar.test_repeated_builds_are_byte_identical`
  - `tools/tests/test_package_compilelib_jars.py::TestCompilelibJarDeterminism`（新文件）
- 先确认红：两次生成的 ZIP entry timestamp 不同导致 bytes 不同。
- 修复：两个脚本均引入 `FIXED_ZIP_TIME=(1980,1,1,0,0,0)` 和 `_write_entry()`，用固定 `ZipInfo`（timestamp/compress_type/create_system/external_attr）写入所有 entry，不依赖输入 JAR 原始 metadata。
- 验证：
  - `python3 -m unittest tools.tests.test_package_aosp_aar tools.tests.test_package_compilelib_jars -v` → 10 tests PASS。
  - 两次重生成 animationlib.aar / compilelib-debug.jar / compilelib-release.jar 的 SHA-256 完全一致。
  - `unzip -t` 三个 archive integrity check 通过。
  - 重生成后的 SHA-256：
    - animationlib.aar: `91f85a93f174c1907a4af1d7afab66253314a45b09b750a4a84d7215eeb610ab`
    - compilelib-debug.jar: `9d12cbddf01e352485197646dcb794676738ee3ed1faf5d9490175cf920afbd3`
    - compilelib-release.jar: `ad605e3fc7bb80f563497983392fc193368d88c1042bdda22e28004df73ca022`

#### Task 3：给 JVM Common 模块补 SysUISdk compile API ✅

- 验证：`android.icu.text.SimpleDateFormat` 只在 SysUISdk `android.jar`，不在 `libs/framework.jar`。
- 先确认红：`compileKotlin` 报 `Unresolved reference 'icu'` / `'SimpleDateFormat'`（`LogMessage.kt:19,101`）。
- 修复：JVM 模块不自动获得 AGP 的 `compileSdkPreview`，添加 module-local
  `compileOnly(files(sysUiAndroidJar))`（lazy `Provider`，默认 `/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar`）。
  保留现有 `framework.jar`，未修改 root `KotlinCompile` classpath，未改成 Android library。
- 验证：
  - `./gradlew :SystemUI-common:compileKotlin --rerun-tasks` → BUILD SUCCESSFUL（exit 0）。
  - 仅余一条 Kotlin annotation-target warning（`LogLevel.kt:22`），非 error。

#### Task 4：恢复 Compose 的 core-animation 依赖 ✅

- 先确认红：`compileDebugKotlin` 报 `Unresolved reference 'Interpolator'`（`Easings.kt:21`）。
- 确认 `:SystemUI-animation` 已有 `androidx.core:core-animation:1.0.0`，证明官方 artifact/version 可用。
- 修复：
  - `gradle/libs.versions.toml` 加 `androidx-core-animation = { module = "androidx.core:core-animation", version = "1.0.0" }`。
  - `SystemUI-compose/build.gradle.kts` 加 `implementation(libs.androidx.core.animation)`。
- 验证：
  - `./gradlew :SystemUI-compose:dependencies --configuration debugCompileClasspath` 包含 `core-animation:1.0.0`。
  - `./gradlew :SystemUI-compose:compileDebugKotlin --rerun-tasks` → BUILD SUCCESSFUL（exit 0）。
- 文档同步：修正 `module-consolidation-plan.md` 两处旧描述；更新 `CURRENT_STATE.md`/`HANDOFF.md` 保留错误列表（common/compose 已解决）。

#### Task 5：恢复 Plugin Compose runtime 依赖 ✅

- 先确认红：plugin `debugCompileClasspath` 无 `androidx.compose.runtime:runtime`。
- `TileDetailsViewModel.kt` 用 `@Composable abstract fun GetContentView()`（abstract，无 body）。
- 修复：`SystemUI-plugin/build.gradle.kts` 加 `implementation("androidx.compose.runtime:runtime:1.8.3")`（对齐 AOSP `plugin/Android.bp`）。
- 验证：
  - classpath 含 `androidx.compose.runtime:runtime:1.8.3`。
  - `./gradlew :SystemUI-plugin:compileDebugKotlin --rerun-tasks` → BUILD SUCCESSFUL（exit 0）。
  - 未加 compose compiler plugin：`@Composable abstract fun` 无 body，不需要 IR 转换，Kotlin 编译通过。
- 确认：
  - `PluginProtectorStub.kt` 不存在。
  - `SystemUI-plugin/build/generated` 下无 `PluginProtector.java`（processor 仍看不到 .kt 标注）。

#### Task 6：建立 post-topology build boundary ✅

**Step 1–2：Python 验证 + 13-module graph**
- `python3 -m py_compile tools/*.py tools/tests/*.py` → OK。
- `python3 -m unittest discover -s tools/tests -v` → 19 tests PASS（新增 Task 1/2 共 3 个测试）。
- `python3 tools/check_source_alignment.py --strict` → exit 0，全 0。
- `./gradlew projects` → BUILD SUCCESSFUL；`settings.gradle.kts` 精确匹配 13 module。

**Step 3：隔离编译证据**
- `:SystemUI-common:compileKotlin` → BUILD SUCCESSFUL。
- `:SystemUI-compose:compileDebugKotlin` → BUILD SUCCESSFUL。
- `:SystemUI-plugin:compileDebugKotlin` → BUILD SUCCESSFUL。
- `:SystemUI-shared:compileDebugKotlin` → BUILD FAILED（首个失败 task 为 `:SystemUI-plugin:compileDebugJavaWithJavac`，见 blocker B2）。

**Step 4：core 新的 first boundary**

`./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks` 失败，首个失败 task 为：

```text
> Task :SystemUI-res:packageDebugResources FAILED
```

不是 Kotlin 编译错误，也不是 AAR transform duplicate-R，而是资源打包阶段。

**Step 5：重复类审计**
- `libs/WindowManager-Shell.jar`（turbine-combined fat jar）含 20155 classes，其中 179 个 `com/android/systemui/**`：
  - animation: 109（与 `:SystemUI-animation` 源码重复）
  - surfaceeffects: 48（与 `:SystemUI-animation` Shader 源码重复）
  - util: 12、(root): 5、shared: 5
- 消费位置（`compileOnly`）：`:app`、`:SystemUI-core`、`:SystemUI-animation`、`:SystemUI-shared`。
- `:SystemUI-core` 还用 catalog aliases 消费 `libs/maven/` 的 settingslib/iconloader/wmshell/wifitrackerlib。

### Phase A 完成后的 blocker 分析

Phase A 清除了 common/compose/plugin 三个上游 classpath blocker，但暴露了两个新的、更深层的 blocker，均需规则 H。

#### Blocker B1（core first boundary）：AOSP `product="..."` 资源变体不被 AAPT2 支持

`./gradlew :SystemUI-core:compileDebugKotlin` 首个失败为 `:SystemUI-res:packageDebugResources`。

根因：AOSP `res-product/values/strings.xml`（与项目字节一致，`check_source_alignment` MODIFIED=0）定义了：

```xml
<string name="inattentive_sleep_warning_message" product="tv">The Android TV device will soon turn off...</string>
<string name="inattentive_sleep_warning_message" product="default">The device will soon turn off...</string>
```

这是 AOSP 的资源 product variant 机制（`product="tv"` / `product="default"`）。Soong 的资源处理器理解该属性，按构建变体选择；但 Gradle/AAPT2 **不支持** `product="..."` 资源属性，把两者都当 default configuration 重复，报 `Found item ... more than one time`，涉及 res-product 下所有 locale 目录（~40 个）。

AOSP `Android.bp` 有独立 `android_library { name: "SystemUI-res", resource_dirs: ["res-product", "res-keyguard", "res"] }`，与项目 `:SystemUI-res` 配置一致——是 Soong vs AAPT2 行为差异，不是配置错误。

涉及规则 R（不得修改 res 文件）和规则 C（res 必须与 AOSP 字节一致），需规则 H 询问用户。

#### Blocker B2：Plugin annotation processor 运行时缺 kotlin stdlib

`:SystemUI-shared:compileDebugKotlin` 首个失败 task 为 `:SystemUI-plugin:compileDebugJavaWithJavac`：

```text
java.lang.NoClassDefFoundError: kotlin/jvm/internal/Intrinsics
```

根因：`SystemUI-plugin/build.gradle.kts` 配置 `options.annotationProcessorPath = files(jarTask.archiveFile)`，只含 `:SystemUI-plugin-processor` 的 jar，不含 kotlin stdlib。processor 是 Kotlin 编译的 JVM `java-library`，运行时引用 `kotlin.jvm.internal.Intrinsics`，但 processor classpath 缺 stdlib 导致 `NoClassDefFoundError`。

这不是 PluginProtector 不生成的问题（那是 B3），而是 processor 运行时 crash。在 B1 解决前会阻断 shared/core 的 Java 编译。

修复方向（不需产品决策，属 build 配置）：把 kotlin stdlib 加入 `annotationProcessorPath`，或用 processor module 的 runtime classpath。

#### Blocker B3（保留）：PluginProtector 不生成

javac 原生 processor 仍看不到 .kt 标注。需用户裁决是否授权 KSP 等价实现。

### Phase A.5：CONV 标记规范与 B1/B2 解决（2026-08-07）

在 Phase A 之后，与用户经 grilling 对齐确定了 AOSP 源码改动标记规范（ADR 0004），并以此解决了 B1、B2：

**阶段一：规范落地**（commit `17fb5c14`）
- ADR 0004：CONV_ADD/DEL/MOD + BEGIN/END 标记；XML 用 `<!-- -->`；顺序铁律（先对齐干净再打标）；`check_source_alignment.py --strict` 不再卡 MODIFIED，靠人工对账
- 27 tests PASS，对齐仍 0/0/0/0，strict exit 0

**阶段二：B1 解决——product variant CONV_DEL**（本次提交）
- 写 `tools/markup_product_variants.py`（+8 单测）批量给非 default product 变体加 CONV_DEL 块
- 86 个 res-product 文件、2237 处非 default 变体被注释（不删除字节，可追溯可撤回）
- `:SystemUI-res:packageDebugResources` BUILD SUCCESSFUL（重复资源错误消除）
- RES-MODIFIED=86 与 issue 清单逐条对账一致；86 个 XML 仍合法

**B2 解决——processor kotlin stdlib**（本次提交）
- 根因：`SystemUI-plugin/build.gradle.kts` 手动设 `annotationProcessorPath = files(jarTask.archiveFile)` 只含 processor jar，缺 kotlin stdlib → `NoClassDefFoundError: kotlin/jvm/internal/Intrinsics`
- 修复：移除手动 `doFirst`，只用 `annotationProcessor(project(...))` 声明——Gradle 9 会自动解析 processor 的传递依赖（含 kotlin-stdlib）。手动设反而破坏了传递依赖解析
- `:SystemUI-plugin:compileDebugJavaWithJavac` BUILD SUCCESSFUL

### 新的 first boundary

B1、B2 解决后，core 编译链推进到 `:SystemUI-shared:compileDebugKotlin`，错误为 4 个真实 Kotlin unresolved reference：

```text
SystemUI-shared/src/com/android/systemui/shared/system/UncaughtExceptionPreHandlerManager.kt:31:37 Unresolved reference 'getUncaughtExceptionPreHandler'.
SystemUI-shared/src/com/android/systemui/shared/system/UncaughtExceptionPreHandlerManager.kt:36:29 Cannot infer type for this parameter. Specify it explicitly.
SystemUI-shared/src/com/android/systemui/shared/system/UncaughtExceptionPreHandlerManager.kt:36:33 Cannot infer type for this parameter. Specify it explicitly.
SystemUI-shared/src/com/android/systemui/shared/system/UncaughtExceptionPreHandlerManager.kt:37:20 Unresolved reference 'setUncaughtExceptionPreHandler'.
```

全部是 `Thread.getUncaughtExceptionPreHandler()`/`setUncaughtExceptionPreHandler()` framework @hide API 未解析（参考项目 GRADLE_MIGRATION.md:439/458 记录同类问题）。core 自身 Kotlin 编译尚未开始。

### Phase B：独立 artifact-recovery 计划

Phase A 完成并取得新的 first-failure 证据后，下一 AI 应执行（开始前按新证据校准首个 blocker）：

```text
docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md
```

该计划已按以下要求编写：

- SettingsLib、iconloader、WindowManager-Shell、WifiTrackerLib 逐个恢复；
- 每个库先直接 AAR；只有实证直接 AAR 冲突后才使用本地 Maven；
- 禁止把 R.jar 合入含资源 AAR 的 classes.jar；
- 检查 AAR/JAR 与 13 个源码 module 的重复类；
- 特别处理 WindowManager-Shell 中嵌入的 `com.android.systemui.animation.*`；
- 每次只接入一个 artifact，记录首个 transform/resource/class 冲突；
- 不修改任何 AOSP SystemUI res 文件来适配 AAPT2。

该计划先以 Phase A 后的真实 first-failure 和 Soong 产物结构重新确认基线，再逐个执行；不能预设所有库都需要本地 Maven 或同一种重打包方式。

### Phase C：Plugin processor 产品决策

遇到 `PluginProtector` 后停止并询问用户。允许讨论但不得擅自执行：

1. 授权实现 KSP `SymbolProcessor` 等价处理器；
2. 找到并验证其他 Kotlin→javac bridge；
3. 用户指定的新工具链方案。

仍然禁止：

- 恢复 `PluginProtectorStub.kt`；
- 提交手写的生成结果冒充 processor 输出；
- 未经授权恢复 KAPT。

### Phase D：最终 APK 验收

依次验证：

1. `:SystemUI-core:compileDebugKotlin`；
2. `:app:processDebugMainManifest`；
3. merged manifest 的入口、权限、shared UID 和组件；
4. `:app:assembleDebug`；
5. 实际 APK 文件、类和资源内容；
6. 最终 runtime/compile classpath 重复类检查。

在 `:app:assembleDebug` exit 0 且 APK 实际存在前，禁止宣称项目构建成功。

## 错误数演变

- 审查开始前：无可信 Kotlin 总错误数；core 在上游 common/compose 失败前未开始。
- 本次只做审查和文档计划：未修改生产代码，错误数不变。
- 错误数始终只作为诊断信息，不是提交、回滚或审批条件。

## 待解决问题

1. 执行 Phase A 计划并取得新的 core first-failure。
2. 基于新证据编写并执行 artifact-recovery 计划。
3. PluginProtector 触发时请求用户裁决。
4. 恢复 manifest merge 和 `:app:assembleDebug` 验收。
