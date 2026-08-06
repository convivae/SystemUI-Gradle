# SystemUI Gradle 模块边界调研（重新审定）

**日期**：2026-08-06
**状态**：替代本文此前“约 30 个 Soong target，因此 22 个 Gradle module 数量并不离谱”的结论。该结论把 Soong 编译图节点误当成了 Gradle 工程边界，现已废止。

## 一、结论摘要

### 1.1 不能按 `Android.bp` target 数量创建 Gradle module

AOSP `Android.bp` 中的 `java_library` / `android_library` 可能只是：

- 为 Soong 增量编译或可见性检查创建的切片；
- 为公共 SDK、host tool、annotation processor 使用不同编译参数创建的切片；
- 为生成独立 R namespace 创建的资源边界；
- 为其他 AOSP 产品复用而创建的发布单元；
- 仅供测试使用、并不进入 SystemUI APK 的 target。

Soong 的 `static_libs` 会把依赖实现 JAR和资源继续合并到父 target。`build/soong/java/base.go` 中明确构造 `completeStaticLibsImplementationJars`，随后把这些 JAR 合成父模块 `classes.jar`；资源 JAR也通过 `completeStaticLibsResourceJars` 合并。因此：

> **Soong target 是编译图节点，不天然等于 Gradle project module。**

Gradle module 应只保留有真实 seam 的边界：独立 R namespace、多个兄弟模块共同依赖、外部稳定 API、不同编译工具链、AIDL/annotation processing 隔离，或必须避免依赖环。

### 1.2 建议的最终数量

当前 `settings.gradle.kts` include **22 个 module**。重新审定后建议为：

- **12 个参与 Android/SystemUI 构建的 module**；
- **1 个仅构建期使用的 host annotation processor module**；
- 合计 **13 个 Gradle module**。

目标清单：

1. `:app`
2. `:SystemUI-core`
3. `:SystemUI-res`
4. `:SystemUI-common`
5. `:SystemUI-animation`
6. `:SystemUI-plugin-core`
7. `:SystemUI-plugin-processor`（仅构建期）
8. `:SystemUI-plugin`
9. `:SystemUI-unfold`
10. `:SystemUI-customization`
11. `:SystemUI-shared`
12. `:SystemUI-shared-biometrics`
13. `:SystemUI-compose`

这不是追求最少 module，而是删除没有独立 Gradle 价值的浅模块，同时保留资源、工具链、复用和依赖方向所要求的边界。

## 二、判定方法

### 2.1 应保留独立 Gradle module 的条件

一个 AOSP target 满足以下任一条件时，才优先保留为 Gradle module：

1. **独立资源 namespace**：源码显式引用该库自己的 `R`，不能与另一个 namespace 在同一 Android library 中生成。
2. **多个兄弟模块共同依赖**：合入任一父模块会造成重复源码、过宽依赖或依赖环。
3. **外部稳定接口**：被 SystemUI 以外的产品直接消费，且边界本身具有明确 API 语义。
4. **不同构建工具链**：例如 host annotation processor、AIDL、KSP/Dagger 或 Java 版本要求明显不同。
5. **依赖方向要求**：基础接口必须位于 core 之下，不能让 plugin/shared 反向依赖整个 core。

### 2.2 应合并为同一 Gradle module/source set 的条件

以下情况不应机械拆 module：

- 只有一个生产消费者；
- 与父模块使用相同语言、SDK 和处理器配置；
- 只是 `api` / `impl` 的 Soong namespace 切片；
- 只是同一源码树通过 `exclude_srcs` 切开的实现细节；
- 无独立资源 namespace；
- 合并后不会制造依赖环，也不会破坏外部 API。

### 2.3 BP 属性在 Gradle 中的正确含义

| BP 属性/事实 | Gradle 含义 | 不代表什么 |
|---|---|---|
| `static_libs` | 通常是 `implementation`/`api`、同 module source set，或需打包的 JAR/AAR | 不代表必须创建 Gradle module |
| `libs` | 通常是 `compileOnly` 或平台运行时提供依赖 | 不代表一定是 JAR；仍需看资源和运行时归属 |
| `resource_dirs` | 外部产物必须保留资源，通常用 AAR；项目内可能形成独立 R module | `android_library` 名称本身不强制 AAR |
| `plugins` | annotation processor/compiler plugin；应是构建期依赖 | 不应打包进 APK runtime |
| `sdk_version` / `java_version` | 可能构成独立编译边界 | 仅因值不同也不必无条件拆 module，需结合消费者和工具链 |
| `visibility` | Soong API/实现隔离线索 | 不要求 Gradle 逐 target 复刻 namespace |

## 三、参考项目 `CarSystemUIGradle` 能证明什么

参考项目 `settings.gradle.kts` 只有 7 个 module：

- `:app`
- `:SystemUI-core`
- `:SystemUI-shared`
- `:SystemUI-plugin`
- `:SystemUI-plugin-core`
- `:SystemUI-animation`
- `:SystemUI-monet`

它证明了两点：

1. 正常 Gradle 改造不会把每个 Soong target 都平铺为 project module；
2. AOSP 外部且含资源的依赖（SettingsLib、iconloader、WM Shell、WifiTrackerLib 等）适合以 AAR 交付，而不是复制源码。

但不能直接照抄其 7 模块：

- 参考项目对应的 SystemUI 源码代际较旧，`SystemUI-core` 仅约 1474 个源码文件；当前 AOSP 顶层 `src/` 已约 4203 个源码/AIDL/proto 文件，并新增 Compose、pods、Unfold、Common/Log 等结构。
- 参考项目把部分 unfold、biometrics、log 源码直接放进 core/shared，说明“可合并”，但不能证明当前分支的资源 namespace 和多消费者关系可以忽略。
- 参考项目有 app 对多个子模块的冗余直接依赖、`res-gradle` 补充资源等历史做法；这些不能成为本项目规则 C/R 下的模板。
- 参考项目的 `:SystemUI-monet` 来源是 `frameworks/libs/systemui/monet`，按本项目规则 F 应改用 AOSP 产物 JAR，而不是源码 module。

因此参考项目是“不要 1:1 映射 BP”的证据，不是当前模块清单的权威来源。

## 四、建议的最终模块图

```text
:app
└── :SystemUI-core
    ├── :SystemUI-res
    │   ├── :SystemUI-shared
    │   └── :SystemUI-customization
    ├── :SystemUI-common
    ├── :SystemUI-animation
    ├── :SystemUI-customization
    ├── :SystemUI-plugin
    ├── :SystemUI-shared
    └── :SystemUI-compose

:SystemUI-plugin
├── :SystemUI-plugin-core
├── :SystemUI-common
├── :SystemUI-animation
└── annotationProcessor/kapt(:SystemUI-plugin-processor)

:SystemUI-plugin-processor (host/build-time only)
└── :SystemUI-plugin-core

:SystemUI-customization
├── :SystemUI-plugin-core
├── :SystemUI-plugin
├── :SystemUI-animation
└── :SystemUI-unfold

:SystemUI-shared
├── :SystemUI-shared-biometrics
├── :SystemUI-plugin-core
├── :SystemUI-plugin
├── :SystemUI-animation
└── :SystemUI-unfold

:SystemUI-compose
└── :SystemUI-animation
```

约束：

- `:app` 只直接依赖 `:SystemUI-core`；不得为了“保证打包”重复直接依赖所有子模块。
- `:SystemUI-core` 不直接依赖 biometrics、keyguard、unfold、plugin-core 等传递子边界，除非 AOSP core 源码存在真实直接引用且 BP 也直接声明。
- 外部 AAR/JAR 和官方 Maven 依赖未画入此项目模块图。

## 五、每个目标模块的源码归属

### 5.1 `:app` — APK 壳

- 对应：Soong `android_app "SystemUI"`。
- 自有源码：无。
- 职责：application plugin、完整主 manifest、签名、privileged/system 属性、最终 APK。
- 依赖：只 `implementation(project(":SystemUI-core"))`。
- `SystemUIApplication.java`、`SystemUIService.java` 继续属于 core，不能移入 app。

### 5.2 `:SystemUI-core` — 主实现

应直接消费以下 AOSP source roots：

- `src/`
- `src-debug/` / `src-release/`（按 build type 选择）
- `compose/features/src/`
- `compose/facade/enabled/src/`
- `pods/com/android/systemui/dagger/`
- `pods/com/android/systemui/util/settings/`
- `pods/com/android/systemui/retail/` 下 data/domain/api/impl/顶层全部生产源码

pods 合入 core 的理由：

- 总计仅 18 个左右的生产源码文件；
- visibility 限定在 SystemUI 子包，最终只有 core 消费顶层 retail impl/settings/dagger API；
- `api`/`impl` 是 Soong namespace 内部隔离，不是独立发布单元；
- 无资源、无不同编译器，也不会因合入 core 产生依赖环。

`SystemUI-core` 不应包含：

- `frameworks/libs/systemui/compilelib` 的 `Compile.java`；
- `utils/kairos`；
- shared/keyguard/biometrics、animation shader 等其他 owner 的重复副本；
- proto/tags/statsd/aconfig 的手写替代类。

### 5.3 `:SystemUI-res` — 必须保留的资源 namespace

来源：

- `res/`
- `res-keyguard/`
- `res-product/`
- `AndroidManifest-res.xml`

这个 target **不能仅因“资源可以放 core”而删除**。当前 AOSP 约 **959 个** core/compose 源码文件显式导入：

```java
import com.android.systemui.res.R;
```

因此 Gradle 必须稳定生成 `com.android.systemui.res.R`。独立 Android library 是最直接且不修改 AOSP 源码的做法。它还需按 BP 依赖 shared/customization/SettingsLib/leanback/slice，使非 transitive R 模式关闭时得到与 Soong 接近的资源符号可见性。

此前文档只因“BP 有 SystemUI-res”要求建模块，论证不充分；现在保留它的依据是**真实 R namespace 和源码 import**。

### 5.4 `:SystemUI-common` — 合并 Common + Log + shared-utils

合并以下 Soong targets/source roots：

- `SystemUICommon` → `common/src/`（3 个源码文件）
- `SystemUILogLib` → `log/src/`（10 个源码文件）
- `SystemUI-shared-utils` → `utils/src/`（2 个源码文件）

保留一个基础 module 的原因：

- plugin 和 core 都使用 Common/Log；若把它们并入 core，plugin 将反向依赖 core，形成错误依赖方向；
- Log 本身只依赖 Common，二者编译配置接近；单独保留 10 文件的 `:SystemUI-log` 是浅模块；
- shared-utils 只有 Common/core 消费，无资源、无独立工具链；单独建 module 没有收益。

因此不新增旧文档建议的 `:SystemUI-shared-utils`，并删除现有 `:SystemUI-log`，统一进入 `:SystemUI-common`。

### 5.5 `:SystemUI-animation` — 合并 Animation + Shader

合并：

- `PlatformAnimationLib` 的 `animation/src/` 非 surfaceeffects 部分；
- `SystemUIShaderLib` 的 `animation/src/com/android/systemui/surfaceeffects/**`；
- `animation/res/`。

AOSP 用 `exclude_srcs` 把同一源码树切成两个 target，主要为 Shader 强制 public SDK/minSdk 检查。Shader 只有 `PlatformAnimationLib` 一个生产消费者、无独立资源、使用相同 Kotlin flags。对本 APK Gradle 工程，不值得再增加 `:SystemUI-shader` 浅模块；可用 lint/CI 保留 public-API 约束。

不得纳入：

- `animation/lib/PlatformAnimationLib-core/server`：SystemUI APK 生产图不依赖，只被其测试使用；
- `frameworks/libs/systemui/animationlib` 源码：不属于 packages/SystemUI，且有 `res/`，必须使用 AAR。

### 5.6 `:SystemUI-plugin-core` — 合并运行时 Core + Annotation API

合并：

- `PluginAnnotationLib`：`plugin_core/src/**/annotations/*`
- `PluginCoreLib`：`plugin_core/src/` 其余源码

AOSP 中后者静态依赖前者；二者都是 Java 8/public SDK 运行时接口，放在同一源码 module 可保持 Launcher/plugin 兼容边界。当前项目已经基本采用这一合并方式，方向正确。

### 5.7 `:SystemUI-plugin-processor` — 独立构建期工具

来源：

- `plugin_core/processor/src/`（`ProtectedPluginProcessor.kt`、`TabbedWriter.kt`）

必须独立的原因：

- 它是 host annotation processor，不是 Android runtime 库；
- AOSP `SystemUIPluginLib` 通过 `plugins: ["PluginAnnotationProcessor"]` 生成 `PluginProtector` 和受保护 proxy；
- 把 processor 源码塞入 plugin-core 会把构建工具打进 APK；完全忽略 processor 则会退回 `PluginProtectorStub.kt`，偏离 AOSP 生产行为。

Gradle 中应作为 `java-library`/Kotlin JVM 构建期 module，通过 `kapt`/兼容处理链只挂到 `:SystemUI-plugin`，不得作为 runtime `implementation` 打包。Kotlin 2/Gradle 9 下的具体 processor 接入方式需单独验证，但这不改变其独立 host seam。

### 5.8 `:SystemUI-plugin` — 对外插件 API

来源：

- `plugin/src/`（排除 `PluginProtectorStub.kt`）
- `plugin/bcsmartspace/src/`

保留原因：

- 被 CarSystemUI、QuickAccessWallet、SystemUIGo、TvSystemUI 等外部产品消费；
- plugin classloader/proguard 语义独立；
- 依赖 plugin-core、animation、common，但不能依赖 core。

当前 `SystemUI-plugin/src/main/com/` 下还有约 30 个未被 sourceSets 消费的旧副本（27 个与活动 source root 相同、3 个已发生内容分叉），应在以 AOSP 为准核对后删除；有效源码只保留一个 owner/source root。

### 5.9 `:SystemUI-unfold` — 多消费者 + 独立处理器边界

来源：`unfold/src/`（38 个 Java/Kotlin/AIDL 文件）。

保留原因：

- 同时被 shared 和 customization 消费，不能并入其中一方；
- 使用 AIDL、Dagger processor，当前 Gradle 还需独立 KSP/Dagger 版本隔离；
- AOSP Settings 也直接消费该库。

core 不直接依赖 unfold；通过 shared/customization 得到传递实现。

### 5.10 `:SystemUI-customization` — 独立资源/API 库

来源：

- `customization/src/`
- `customization/res/`

保留原因：

- 有 `com.android.systemui.customization.R` 独立资源 namespace；
- 被 ThemePicker、WallpaperPicker2 外部消费；
- 有 AIDL 和 Dagger processor；
- 与 shared 是兄弟依赖，不应互相依赖。

正确内部依赖：animation、plugin-core、plugin、unfold。现有 Gradle 对 shared/log 的额外依赖没有 BP 依据，应删除或以真实源码引用重新证明。

### 5.11 `:SystemUI-shared` — 合并 Shared + Keyguard child

来源：

- `shared/src/`
- `shared/res/`
- `shared/keyguard/src/`（2 个 Java 文件）

`SystemUISharedLib-Keyguard` 只有 shared 一个生产消费者、没有资源、没有不同处理器；应作为 shared source set，而不是独立 `:SystemUI-shared-keyguard`。

shared 继续独立，因为它有自己的 AIDL、资源 namespace、Dagger 处理，并被 core/其他 SystemUI 产品复用。

### 5.12 `:SystemUI-shared-biometrics` — 必须保留的第二个 R namespace

来源：

- `shared/biometrics/src/`（11 个源码文件）
- `shared/biometrics/res/`（当前 1 个资源文件）

虽然 SystemUI 内部只有 shared 消费它，但 `UdfpsUtils.java` 显式导入：

```java
import com.android.systemui.shared.biometrics.R;
```

一个 Android library 不能同时自然生成 `com.android.systemui.shared.R` 和 `com.android.systemui.shared.biometrics.R`。此外 Settings 也直接消费 `BiometricsSharedLib`。因此它不是应合并的普通 child target，需保留独立 module。

### 5.13 `:SystemUI-compose` — 合并 Compose Core + Scene

合并：

- `compose/core/src/`（27 个 Kotlin 文件）
- `compose/scene/src/`（50 个 Kotlin 文件）

两个 Soong target：

- 都无 Android 资源；
- 使用相同 Compose compiler/Kotlin flags；
- Scene 单向依赖 Core；
- 在本项目中由 SystemUI core 统一消费。

因此合并成一个有内聚性的 Platform Compose toolkit module，比保留两个浅层 Gradle module 更合适。AOSP 外部消费者若未来也迁入本 Gradle workspace，再根据发布需求重新拆分，而不是现在为不存在的 Gradle consumer 预付复杂度。

注意：`compose/features/src/` 和 `compose/facade/enabled/src/` 在 BP 中本来就是 `SystemUI-core.srcs`，不能放入 `:SystemUI-compose`。

## 六、当前 22 个 module 的逐项处置

| 当前 module | 处置 | 最终 owner/形态 | 原因 |
|---|---|---|---|
| `:app` | 保留 | `:app` | APK 壳 |
| `:SystemUI-core` | 保留、校准 source roots | `:SystemUI-core` | 主实现 |
| `:SystemUI-shared` | 保留、吸收 keyguard | `:SystemUI-shared` | AIDL/资源/复用边界 |
| `:SystemUI-animation` | 保留、吸收 shader | `:SystemUI-animation` | 多消费者动画库 |
| `:SystemUI-customization` | 保留、修依赖 | 原 module | 独立 R/AIDL/外部消费者 |
| `:SystemUI-plugin` | 保留、删重复死源码 | 原 module | 对外 plugin API |
| `:SystemUI-plugin-core` | 保留 | 原 module | Java 8/public API 边界 |
| `:SystemUI-common` | 保留并吸收 log/utils | 原 module | 避免 plugin→core 依赖环 |
| `:SystemUI-log` | 删除 module | 合入 common | 只有 10 文件、同工具链、依赖 Common |
| `:SystemUI-unfold` | 保留 | 原 module | shared/customization 共用 + AIDL/KSP |
| `:SystemUI-animationlib` | 删除源码 module | AOSP AAR | 非 packages/SystemUI，且含资源 |
| `:SystemUI-utils-kairos` | 删除 | 不进入生产图 | 仅测试使用，core BP 不依赖 |
| `:SystemUI-compose-core` | 重组/更名 | `:SystemUI-compose` | 与 scene 合并 |
| `:SystemUI-compose-scene` | 删除 module | 合入 compose | 同工具链、无资源、单向依赖 |
| `:SystemUI-shared-biometrics` | 保留 | 原 module | 独立 R + Settings 消费 |
| `:SystemUI-shared-keyguard` | 删除 module | 合入 shared | 单消费者、无资源 |
| `:SystemUI-proto` | 删除空源码 module | `libs/SystemUI-proto.jar` | proto 生成产物；当前 module 无源码且又重复依赖 JAR |
| `:SystemUI-pods-dagger` | 删除 module | 合入 core | 私有内部切片 |
| `:SystemUI-pods-retail` | 删除 module | 合入 core | 私有内部切片 |
| `:SystemUI-pods-data` | 删除 module | 合入 core | 私有 api/impl 切片 |
| `:SystemUI-pods-domain` | 删除 module | 合入 core | 私有 api/impl 切片 |
| `:SystemUI-pods-settings` | 删除 module | 合入 core | 私有内部切片 |
| （新增）`:SystemUI-res` | 新建 | AOSP 资源源码 | `com.android.systemui.res.R` 必需 |
| （新增）`:SystemUI-plugin-processor` | 新建 | host source module | AOSP processor 生产行为 |

另外两个未 include 的目录：

- `SystemUI-pods-retail-data-impl/`
- `SystemUI-pods-retail-domain-impl/`

是脚手架空壳，引用不存在的 module，应直接删除。

## 七、哪些必须是源码，哪些应是 JAR/AAR/Maven

### 7.1 项目内 SystemUI 源码

`frameworks/base/packages/SystemUI/` 下进入生产图的手写 Java/Kotlin/AIDL 源码，按上文 11 个源码 owner module（不含 app/res，包含 build-time processor）消费。多个 Soong target 可以合入同一个 Gradle module，但：

- 每个 AOSP 文件只能有一个 Gradle owner；
- 不允许为了编译复制第二份；
- 对齐脚本必须按“source root → 最终 owner module”映射，而不是按 BP target 名猜目录。

### 7.2 AOSP 生成或代码型产物：JAR

以下不应创建空/伪源码 Gradle module：

| 产物 | 形式 | 说明 |
|---|---|---|
| `SystemUI-proto` | JAR | `.proto` nano 生成类 |
| `SystemUI-tags` | JAR | logtags 生成类 |
| `SystemUI-statsd` | JAR | stats-log-api-gen 生成类 |
| SystemUI/shared/server/device-state 等 aconfig flags | JAR | aconfig 生成类 |
| `compilelib` | debug/release 对应 JAR | 非 packages/SystemUI；必须按 variant 选择，不能复制 `Compile.java` |
| `monet` + `libmonet` | AOSP 合并 JAR | 均无 Android 资源；不能源码化为本项目 module |
| `tracinglib-platform` | JAR | 纯代码 |
| `msdl` | JAR | 当前 BP 无 `resource_dirs` |
| `view_capture` | 含 proto 的 AOSP JAR | 当前 BP 无 Android 资源 |
| `motion_tool_lib` | 含 proto/view_capture 的 AOSP JAR | 当前 BP 无 Android 资源 |
| `contextualeducationlib` | JAR | 当前 BP 无 Android 资源 |
| `PlatformMotionTestingComposeValues` | JAR | 非 SystemUI 源码 |
| `framework.jar` / statsd / car 等平台 API | `compileOnly` JAR/SysUISdk | 设备运行时提供 |

若某个 Soong `android_library` 实际输出包含传递资源，应以实际 AOSP artifact 内容为准改用 AAR，不能只看 module 类型或本表名称。

### 7.3 AOSP 含资源产物：AAR

| 产物 | 形式 | 原因 |
|---|---|---|
| `frameworks/libs/systemui:animationlib` | AAR | 明确有 `res/` |
| SettingsLib | AAR | 代码 + 大量资源/AIDL/传递库 |
| iconloader | AAR | 代码 + 资源 |
| WindowManager-Shell | AAR | 代码/AIDL + `res/`；不要同时再引同类全量 JAR |
| WifiTrackerLib 组合产物 | AAR | 需携带其资源依赖 |
| LowLightDreamLib | AAR | 明确有 `res/` |
| Traceur-res | AAR/资源 AAR | 资源 target；TraceurCommon 代码可单独 JAR |

流程仍遵守 ADR 0001：先直接 `implementation(files("...aar"))`；只有确认直接 AAR 的资源/类/传递依赖冲突后，才放入 `libs/maven/` 作为 AAR + POM 交付。不得把 `R.jar` 合入 AAR `classes.jar`。

### 7.4 官方 Maven

AndroidX、Compose、Kotlin/coroutines、Dagger、Material、Lottie、Guava、JSR 注解等标准上游依赖使用 `google()` / `mavenCentral()` 官方坐标。只有 AOSP fork/API 与官方版本不兼容时，才退回 AOSP JAR/AAR并记录原因。

Maven 是仓库/交付渠道，不是第四种依赖产物。

## 八、几个容易误判的 BP target

### 8.1 `SystemUI-res`

**保留 module，但不是因为 BP 1:1。**真正原因是 `com.android.systemui.res.R` namespace 和约 959 个显式 import。

### 8.2 `SystemUIShaderLib`

**不保留 module。**同源码树、唯一生产消费者、无资源；合入 animation。

### 8.3 `SystemUI-shared-utils` / `SystemUILogLib`

**不保留 module。**合入 common，保持 plugin/core 之下的基础层即可。

### 8.4 pods `api`/`impl`

**不保留 5 个 module。**它们是私有 namespace 编译切片，全部合入 core。

### 8.5 `BiometricsSharedLib`

**保留 module。**虽然文件少，但它有独立 R namespace，并被 Settings 外部消费；这是深边界，不是“文件少就合并”。

### 8.6 `SystemUISharedLib-Keyguard`

**不保留 module。**只有 shared 消费、无资源、无不同工具链，合入 shared。

### 8.7 Compose Core/Scene

**Gradle 合并为一个 `:SystemUI-compose`。**两者都无资源、同 compiler、单向依赖；当前 workspace 没有要求分别发布它们的消费者。

### 8.8 kairos / animation/lib

**均不进入 SystemUI APK 生产图。**不能因为目录位于 packages/SystemUI 就自动 include；规则 S 只要求复制进入目标生产图的 SystemUI 自有源码，不要求把 test-only target 注入 core。

## 九、实施顺序

1. 先更新 ADR 0003、AGENTS/HANDOFF 中“Gradle module 必须逐 BP target 对齐”的过强表述；改为“源码归属和依赖语义对齐，Gradle 边界按本调研”。
2. 新建 `:SystemUI-res`，保持三个 AOSP res 目录和 `AndroidManifest-res.xml` 1:1，不修改资源。
3. 合并 common/log/utils；删除 `:SystemUI-log`。
4. 补 animation shader 源码到 animation；删除违规 `:SystemUI-animationlib`，改直接 AAR。
5. 合并 shared/keyguard，保留并正确挂接 biometrics。
6. 合并 compose core/scene 为一个 module。
7. 把全部 pods source roots 合入 core，删除 5 个 pods module 和 2 个空壳目录。
8. 删除 kairos、空 `SystemUI-proto` module和 core 中非 SystemUI `Compile.java`；改用真实 JAR。
9. 建立 plugin processor host module，删除 plugin 重复死源码并恢复 AOSP processor 行为。
10. 按最终图重写各 module dependencies；尤其移除 core 对 biometrics/keyguard/unfold/plugin-core 的错误平级依赖。
11. 更新 `tools/check_source_alignment.py` 为 source-root owner 映射，再校验 src/AIDL/res 不漏不多且无重复 owner。
12. 最后审计 JAR/AAR：同一 AOSP 库只能有一个 authoritative runtime artifact，避免 AAR + full JAR 重复类。
13. AAR transform 恢复后再运行 Kotlin 编译；随后验证 manifest merge 和 `:app:assembleDebug`。

## 十、验收条件

模块结构完成不以“错误数下降”为门槛，而以下证据必须成立：

- `settings.gradle.kts` 只 include 上述 13 个目标 module；
- 所有生产 SystemUI Java/Kotlin/AIDL 文件有且仅有一个 owner；
- AOSP `src`/AIDL/res 对齐不漏不多；
- `com.android.systemui.res.R`、`com.android.systemui.shared.R`、`com.android.systemui.shared.biometrics.R`、`com.android.systemui.customization.R` 等 namespace 由真实 Android library/AAR 生成，不改源码 import；
- 非 packages/SystemUI 源码未被复制进项目 module；
- test-only kairos、animation/lib 不进入 core runtime graph；
- generated proto/tags/statsd/flags 只使用真实 AOSP JAR，无空 module或手写 stub；
- `:app` 只直接依赖 core；
- Gradle dependency graph 无项目 module 环、无同一库 AAR/JAR重复类；
- 构建状态如实记录，最终 APK 成功只能由 `./gradlew :app:assembleDebug` 证明。

## 十一、证据索引

- Soong static library 实现/资源合并：`build/soong/java/base.go` 中 `completeStaticLibsImplementationJars`、`completeStaticLibsResourceJars` 和 `TransformJarsToJar`。
- SystemUI core/res/app：`frameworks/base/packages/SystemUI/Android.bp` 的 `SystemUI-res`、`SystemUI-core`、`android_app "SystemUI"`。
- Animation/Shader：`frameworks/base/packages/SystemUI/animation/Android.bp`。
- Common/Log/Utils：`common/Android.bp`、`log/Android.bp`、`utils/Android.bp`。
- Shared children：`shared/Android.bp`、`shared/biometrics/Android.bp`、`shared/keyguard/Android.bp`。
- Plugin processor：`plugin/Android.bp`、`plugin_core/Android.bp`、`plugin_core/processor/src/`。
- Compose：`compose/core/Android.bp`、`compose/scene/Android.bp`。
- pods visibility/消费者：`pods/com/android/systemui/**/Android.bp`。
- 非 SystemUI animationlib/compilelib：`frameworks/libs/systemui/{animationlib,compilelib}/Android.bp`。
- 参考项目模块清单：`/home/conv/myspace/CarSystemUIGradle/settings.gradle.kts`。

## 十二、本轮验证记录

本轮只重新调研并修订架构文档，未修改源码、资源或 Gradle module，未运行编译。当前构建仍以既有 AAR transform 重复 R 类阻塞为真实状态；本文不宣称编译或 APK 已成功。
