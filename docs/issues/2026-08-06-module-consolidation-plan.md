# 13-module 架构实施计划

**日期**：2026-08-06

## 背景

`docs/architecture/2026-08-06-module-structure-audit.md` 已重新审定：当前 22 个 Gradle module 应按真实资源 namespace、复用 seam、依赖方向和构建工具链收敛为 13 个目标 module。实施前需要把该架构拆为可独立审查、可验证、可增量提交的任务，避免再次使用 BP target 数量机械搭脚手架。

## 操作步骤

1. 核对当前 settings、各 module build script、sourceSets、源码目录和依赖图。
2. 同步 ADR 0003、AGENTS/HANDOFF 等政策文档中的模块边界表述。
3. 将实施拆分为政策/对齐工具、源码 module 收敛、外部 JAR/AAR 清理与最终构建恢复三个阶段。
4. 为每个阶段列出精确文件、命令、预期证据和提交点。
5. 保存到 `docs/superpowers/plans/`，实施前由用户选择执行方式。

## 错误数演变

- 计划开始前：构建仍阻塞于 SettingsLib/iconloader/WindowManager-Shell AAR transform 重复 R 类，没有可信 Kotlin 错误数。
- 本阶段只编写计划，不修改 Gradle module、源码或资源，不运行源码编译。

## 待解决问题

1. 按实施计划执行政策同步、owner-aware 对齐工具和 13-module source topology。
2. `SystemUI-plugin-processor` 的 KAPT 接入是 fail-fast 检查点；失败时禁止恢复 `PluginProtectorStub.kt`，需询问用户选择工具链方向。
3. 13-module checkpoint 后另写 artifact recovery 计划，处理 SettingsLib/iconloader/WM Shell/WifiTrackerLib 直接 AAR 和重复 R transform。
4. 最终阶段再验证 manifest merge、core Kotlin 基线和 `:app:assembleDebug`。

## 计划产物

已保存可执行计划：

- `docs/superpowers/plans/2026-08-06-13-module-source-topology.md`

计划包含 10 个任务、58 个以上可追踪步骤和逐任务提交点。本计划只负责政策、源码/resource owner、animationlib AAR、compilelib JAR和 13-module 内部依赖图；既有四个大型 AAR 的恢复被明确拆为下一份独立计划。

## 计划阶段验证

- 未运行源码编译；本阶段只编写实施计划。
- 已核对当前 22 个 include module、目标 13 个 module、AOSP source roots、参考项目模块数及 animationlib/compilelib 中间产物。
- 计划占位符扫描和 Markdown code fence 检查通过。
- `git diff --check`：通过。

## 政策同步验证

- 未运行源码编译；本任务仅同步架构政策。
- `git diff --check`：通过。
- 当前构建阻塞仍为既有 AAR transform 重复 R 类。
- 目标 13-module 清单已写入 ADR 0003 决策 1、AGENTS.md §3.1、HANDOFF §2。
- animationlib 确认为非 SystemUI 代码，"源码化"方案废止，改为直接 AAR。
- kairos 确认为 test-only，不进本 APK 生产图。

## Task 2: 对齐脚本内容感知 + 目标 owner 感知

- 新增 `tools/tests/test_check_source_alignment.py`（8 个单测，全过）。
- 重写 `tools/check_source_alignment.py`：
  - 每条映射对应一个 AOSP source root → 目标 13-module 物理 source root
  - 新增 `diff_pair` 字节级内容比较（[MODIFIED] / [RES-MODIFIED]）
  - root-aware misplaced 判定（同 module 不同 source root 也算放错）
  - `--strict` 在任一 missing/misplaced/extra/modified/app/res 问题时退出 1
  - 移除 SURFACEEFFECTS_PREFIX / check_shader_lib（surfaceeffects 现归入 animation 映射）
- 红色基线（迁移未发生，`--strict` 退出 1）：
  - [MISSING] 212 / [MISPLACED] 162 / [EXTRA] 107 / [MODIFIED] 1046 / [RES-MISS] 2196
  - MODIFIED 1046 反映历史对 core/src 的 R import 规范化等改动，Task 8 重新同步 AOSP 后将归零

## Task 3: 合并 Common + Log + shared-utils

- 同步 AOSP `common/src`、`log/src`、`utils/src` → `SystemUI-common/{common,log,utils}/src`
  - common 3 文件、log 10 文件、utils 2 文件
- `SystemUI-common/build.gradle.kts` 改为 `java-library` + `kotlin.jvm`（JVM 21），
  三个 source root 合入 main sourceSet
- 依赖块按计划：`compileOnly(framework.jar)` + `tracinglib` + `api(kotlinx-coroutines-core)`
  + `implementation(kotlin.stdlib)` + `compileOnly(androidx.annotation)` + `implementation(errorprone)`
- 消费者重连：plugin `:SystemUI-log` → `api(:SystemUI-common)`；core 删除 `:SystemUI-log`；
  customization `:SystemUI-log` → `:SystemUI-common`（Task 5 再精简）
- `settings.gradle.kts` 移除 `include(":SystemUI-log")`，删除 `SystemUI-log/` 目录
- **验证结果（用户裁决：保留错误，继续）**：
  - `:SystemUI-common:compileKotlin` FAILED
  - `e: LogMessage.kt:19 Unresolved reference 'icu'`
  - `e: LogMessage.kt:101 Unresolved reference 'SimpleDateFormat'`
  - 根因：JVM 模块无 AGP android.jar；`android.icu.text.SimpleDateFormat` 只在 SysUISdk
    android.jar，不在 framework.jar。计划依赖块未列 android.jar。
  - 用户明确：严格按计划执行，此错误先保留，不修复，继续后续任务。

## Task 4: animationlib 直接 AAR + Shader 源码合并

- 新增 `tools/package_aosp_aar.py`（严格直接-AAR 打包器）+ `tools/tests/test_package_aosp_aar.py`（8 单测全过）
  - 合并 Soong javac + kotlin JAR；拒绝 R.class；重复非 MANIFEST entry 报 DuplicateEntryError
  - res 字节级复制；不生成 POM；不触碰 libs/maven/
- 生成 `libs/aars/animationlib.aar`（19677 bytes，含 Animations/Interpolators，无 R.class）
- 同步 AOSP `animation/src`（54 文件，含 22 surfaceeffects）+ `animation/res`（4 文件）→ SystemUI-animation
- 消费者重连：animation/customization `api(files(aars/animationlib.aar))`；compose-core `implementation(files(...))`
- 删除 `:SystemUI-animationlib` 模块、`libs/animationlib.jar`；settings 移除 include
- 清理 AGENTS.md §3.2、README.md、scripts/scaffold 中的旧引用
- **验证**：`:SystemUI-animation:compileDebugKotlin` BUILD SUCCESSFUL（仅警告）
- 对齐：MISSING 175（↓37）、MISPLACED 162、EXTRA 107、MODIFIED 1046

## Task 5: 合并 Shared + Keyguard，保留 Biometrics 独立 R

- 同步 AOSP shared/src(81)+res(4)、keyguard/src(2)、biometrics/src(11)+res(1)、
  customization/src(36)+res(100)、unfold/src(38)
- shared: sourceSets 加 keyguard/src；内部边改为 api(biometrics/animation/plugin-core/plugin/unfold)
- biometrics: 独立 R namespace，空 manifest，src+res sourceSets
- customization: 加 aidl srcDirs + buildFeatures.aidl；边改为 api(animation/plugin-core/plugin/unfold)，
  移除旧 :SystemUI-common/:SystemUI-shared 边
- 删除 :SystemUI-shared-keyguard 模块 + libs/shared-uncaught-handler.jar
- core 移除对 biometrics/keyguard/unfold 的直接依赖（经 shared/customization 透传）
- **验证**：:SystemUI-shared-biometrics:compileDebugKotlin BUILD SUCCESSFUL
- 对齐：MISSING 161（↓14）、EXTRA 96（↓11）、RES-MISS 2195（↓1）
- 已知保留：shared 全量编译可能暴露 Thread.setUncaughtExceptionPreHandler 隐藏 API 与
  Dagger 依赖问题（计划明确：记录不恢复 stub）

## Task 6: 合并 Compose Core + Scene

- 创建 `:SystemUI-compose`：core/src(27) + scene/src(50)，namespace `com.android.compose`
- 合并 core+scene 的 Maven 依赖（去重），单一 Compose 编译器配置
- 内部边：`api(:SystemUI-animation)` + animationlib AAR + tracinglib
- core 改为单一 `implementation(:SystemUI-compose)`；删除 compose-core/compose-scene 模块
- **验证**：`:SystemUI-compose:compileDebugKotlin` FAILED
  - `e: Easings.kt:21 Unresolved reference 'Interpolator'`（import androidx.core.animation.Interpolator）
  - 根因：compose 依赖块只有 `androidx.core:core-ktx:1.13.1`，计划未列 `androidx.core:core`；
    旧 compose-core 依赖相同，属预存问题非本次回归
  - 用户既定方针：严格按计划执行，错误先保留，继续后续任务
- 对齐：MISSING 84（↓77，compose 源码归位）、EXTRA 96、MODIFIED 1046

## Task 7: 创建 SystemUI-res 资源 namespace 模块

- 从 AOSP 复制 res(1897)/res-keyguard(212)/res-product(86) → SystemUI-res（字节一致）
- 删除 SystemUI-core/{res,res-keyguard,res-product} 与 app/AndroidManifest-res.xml
- 创建 :SystemUI-res（namespace com.android.systemui.res，无源码，仅资源）
  - 依赖 api(shared/customization/settingslib/leanback/slice-core/slice-view)
- core 移除 res.srcDirs，加 implementation(:SystemUI-res)
- **验证**：res/res-keyguard/res-product 字节级与 AOSP 一致
- 对齐：RES-MISS 2195 → 0，RES-EXTRA 0，RES-MODIFIED 0

## Task 8: pods 合入 core + 删除非生产模块

- 重新同步 core 全部源码根：src(4231)/src-debug(4)/src-release(4)/compose/features/src(153)/
  compose/facade/enabled/src(9)/pods(18, rsync 仅 java/kt/aidl)
  - 自动移除非 SystemUI 的 Compile.java（AOSP src 无此文件）
- 新增 tools/package_compilelib_jars.py：javac --release 21 编译 compilelib debug/release
  - libs/compilelib-debug.jar (IS_DEBUG=1)、libs/compilelib-release.jar (IS_DEBUG=0)
- core sourceSets：java.srcDirs(src, compose/features/src, compose/facade/enabled/src, pods)
- core 变体依赖：debugImplementation/releaseImplementation compilelib jar
- core 项目依赖精简为 7 个：res/animation/common/customization/plugin/shared/compose
- 保留单一 SystemUI-proto.jar（移除 project(:SystemUI-proto)）
- 删除 9 个废弃模块：utils-kairos/proto/pods-{dagger,retail,data,domain,settings,retail-data-impl,retail-domain-impl}
- 移除 root build 的 Kairos ExperimentalFrpApi opt-in flag
- **验证**：./gradlew projects BUILD SUCCESSFUL（12 模块）
- 对齐：MISPLACED 162→0、MODIFIED 1046→0、MISSING 84→66（plugin 源码待 Task 9 同步）

## Task 9: 恢复 Plugin 注解处理器边界（KAPT 失败，待用户裁决）

### 已完成的结构改动
- 同步 AOSP plugin_core/src(13)、plugin/src(49，删 PluginProtectorStub.kt)、
  bcsmartspace/src(2)、plugin_core/processor/src(2)
- plugin-core 转 JVM 源码库（java-library + kotlin.jvm，无 Android 资源/manifest）
- 创建 :SystemUI-plugin-processor（JVM，含 src + resources/META-INF/services 描述符）
- 创建 :SystemUI-plugin/AndroidManifest.xml（空 manifest）
- 重写 :SystemUI-plugin/build.gradle.kts（KAPT + api(plugin-core/animation/common)）
- libs.versions.toml 加 kotlin-kapt 别名
- settings 加 :SystemUI-plugin-processor（13 个 include，目标达成）
- app 移除 id("kotlin-kapt")

### KAPT 失败（计划 Step 5 停止条件触发）

命令：`./gradlew :SystemUI-plugin:compileDebugKotlin --stacktrace`

错误：
```
Error resolving plugin [id: 'org.jetbrains.kotlin.kapt', version: '2.1.0']
> The request for this plugin could not be satisfied because the plugin is
  already on the classpath with an unknown version, so compatibility cannot
  be checked.
```

根因：root build.gradle.kts 已注释"KAPT 1.9+ 与 Gradle 9.5 不兼容，改用 KSP"。
当前 Gradle 9.5.0 + Kotlin 2.1.0，KAPT 插件（org.jetbrains.kotlin.kapt）无法解析。
项目此前已因 KAPT/Gradle 9 不兼容改用 KSP（见 unfold 模块）。

完整 stack trace（196 行）见 /tmp/kapt-stack.txt，首行：
```
org.gradle.api.GradleException: Error resolving plugin [id: 'org.jetbrains.kotlin.kapt', version: '2.1.0']
    at org.gradle.plugin.use.internal.DefaultPluginRequestApplicator.resolvePluginRequest(...)
```

### 待用户裁决
计划 Step 5 明确：KAPT 失败时停止、记录、询问用户后再选编译器/工具链；
不得恢复 PluginProtectorStub.kt。

可选方向：
1. 改用 KSP 跑 ProtectedPluginProcessor（需确认该处理器是否 KSP 兼容）
2. 升级/调整 Kotlin 版本以恢复 KAPT 兼容性
3. 用 javac annotation processor（-processor）直接调用，绕过 KAPT/KSP Gradle 插件
4. 其他用户指定方向

当前未恢复 stub，等待裁决。

### 用户裁决（方向 A → 待办）

用户选择"完全转向 KSP，不使用 KAPT"。但实证发现：
- `ProtectedPluginProcessor` 是 `javax.annotation.processing.AbstractProcessor`（javac API），
  KSP 用 `SymbolProcessor` API，**不兼容**，不能直接换插件。
- 全部 8 个 `@ProtectedInterface` 标注在 `.kt` 文件（ClockController 等 clocks + TestPlugin）。
- javac 原生注解处理器（`JavaCompile.options.annotationProcessorPath`）**只看 Java 源码**，
  看不到 Kotlin 源码 → `PluginProtector` 不会生成。

用户裁决：**先留待办，继续往下执行**（方向 3）。

当前实现：
- 移除 KAPT 插件依赖与 `kotlin-kapt` catalog 别名
- `:SystemUI-plugin` 用 `JavaCompile` + `annotationProcessorPath(project(":SystemUI-plugin-processor"))`
  原生调用处理器（processor 源码原样不动，规则 C 满足）
- `:SystemUI-plugin:compileDebugKotlin` 配置解析成功（annotationProcessorPath 生效）
- **待办**：`PluginProtector` 不生成，下游 `Unresolved reference 'PluginProtector'` 作为保留错误

后续需在 Kotlin 标注处理方向上决策（KAPT 兼容性实证 / KSP 重写 / 其他），不在本计划内。
