# Phase C: :SystemUI-shared 源码化迁移

日期：2026-07-29
关联：`docs/architecture/2026-07-29-dependency-audit.md`（Phase C）

## 背景

依赖审查（规则 S，三层策略）判定 `:SystemUI-shared` 属于**① SystemUI 自有代码**
（soong 模块 `SystemUISharedLib` 定义在 `packages/SystemUI/shared/Android.bp`），
应**源码复制、源码依赖**，而非此前的 `prebuilts/SystemUISharedLib.jar`（AAR）。

## 操作步骤

1. 复制 AOSP `packages/SystemUI/shared/src` → `SystemUI-shared/src`（81 文件：34 kt + 41 java + 6 aidl）。
2. 复制 AOSP `shared/res` → `SystemUI-shared/res`（4 xml，含 `DoubleShadowTextView` styleable）。
3. 重写 `SystemUI-shared/build.gradle.kts`（android.library + kotlin.android，
   `src` 同时作 java/kotlin/aidl/res srcDir，`buildFeatures.aidl=true`，
   `-Xjvm-default=all`，对齐 AOSP kotlincflags）。
4. 依赖分层接入：
   - tier①源码模块：`project(:SystemUI-plugin)`、`project(:SystemUI-plugin-core)`
   - tier② jar：framework.jar、WindowManager-Shell.jar、SystemUI-unfold.jar、
     tracinglib-platform.jar、view_capture.jar
   - tier③ maven：androidx.*、dagger、guava、kotlinx.coroutines、kotlin.stdlib
5. 删除 core/src 中 8 个「杂散拷贝」文件（这些文件 AOSP 归属 shared，早期批量复制误入 core，
   若保留会与源码模块**重复类**）：`dagger/qualifiers/{Main,DisplaySpecific,Tracing}`、
   `flags/{Flag,FlagListenable,FlagManager,FlagSerializer,FlagSettingsHelper}`（已逐一 diff 确认与 shared 版本一致）。
6. core `compileOnly(libs.systemui.sharedlib)` → `implementation(project(":SystemUI-shared"))`。
7. 补 `:SystemUI-plugin` 缺失的 `plugins/log/TableLogBufferBase.kt`（shared 的 Monitor.java 依赖）。
8. core 直接补 `msdl.jar` + `view_capture.jar`（见下「透传依赖」）。

## 遇到的两处技术困难

### 1. `Thread.setUncaughtExceptionPreHandler` 隐藏 API（无法源码编译）

`shared/src/.../system/UncaughtExceptionPreHandlerManager.kt` 调用 libcore 隐藏静态方法
`Thread.get/setUncaughtExceptionPreHandler`（`@hide @UnsupportedAppUsage`）。

- AOSP 平台编译走 `core-for-system-modules` 作 bootclasspath/system-modules，可见该隐藏方法。
- 我们的 Kotlin/JDK21 工具链：`java.lang.Thread` 恒从 JDK `java.base` 模块解析，
  **任何 classpath jar 都无法覆盖 java.base**。已实测：
  - 加 `core-for-system-modules.jar` 作 compileOnly library → 无效（java.* 仍走 JDK）。
  - 加 `-no-jdk` 编译参数 → 无效。
- 结论：这是 Kotlin/JVM 工具链的硬限制，非 stub 规避问题。
- **处理（§1.3 允许「从 AOSP 编译产物提取 .class 打包 jar」）**：
  排除该 1 个 .kt 源文件，从 AOSP 编译产物 `SystemUISharedLib.jar` 提取其真实编译类
  → `libs/shared-uncaught-handler.jar`（4 个 class），compileOnly 接入 shared 与 core。
  该类仅被 Java 文件引用（shared 的 PluginManagerImpl.java、core 的 SystemUIService/PluginsModule.java），
  无 Kotlin 引用，故排除 .kt 不影响 Kotlin 编译。
  - ⚠️ 这是**真实 AOSP 编译产物**，非人造 stub，符合规则 P。
  - TODO：若未来切换到 Android system-modules 编译方式，可恢复该 .kt 源码。

### 2. AIDL 外部 parcelable `ScreenshotRequest`

`shared` 的 aidl 引用 `com.android.internal.util.ScreenshotRequest`（framework parcelable）。
AAPT/aidl 需在 include path 找到其声明。已复制 AOSP 真实 aidl
`frameworks/base/core/java/com/android/internal/util/ScreenshotRequest.aidl`
→ `SystemUI-shared/src/com/android/internal/util/`（真实 AOSP 源码，非 stub）。

## 透传依赖修正（msdl / view_capture）

旧 `SystemUISharedLib.jar` 是 turbine-combined **fat jar**，透传了 25 个 msdl 类、
37 个 viewcapture 类给 core。源码化后 shared 为精简模块不再透传，
故 core 直接补 `libs/msdl.jar`、`libs/view_capture.jar`（tier② `frameworks/libs/systemui`）。
→ 这是更正确的显式依赖，而非回归。

## 错误数演变（`:SystemUI-core:compileDebugKotlin`）

| 阶段 | 错误数 | 说明 |
|------|--------|------|
| 基线（Phase B `4102b41`） | 116 | shared 为 prebuilt jar |
| 迁 shared 源码 + 删 8 杂散 + 换 project 依赖 | 239 | fat jar 透传的 msdl/viewcapture 断裂暴露 |
| 补 core 的 msdl.jar + view_capture.jar | **102** | 透传断裂修复，且源码解析修好若干 jar metadata 问题 |

净结果 **116 → 102（−14）**，无新回归；剩余 102 均为既有类别
（communal/widgets 29、guest_exit_* 文案、ic_* 图标、infinitegrid 实验 API 等）。

`:SystemUI-shared` 独立编译：Kotlin 0 错、Java 0 错。

## 待办

- SystemUI-unfold.jar 仍为 jar（tier① 应源码化，Phase C 后续项 id7）。
- UncaughtExceptionPreHandlerManager.kt 源码化依赖 system-modules 编译方案（长期）。
