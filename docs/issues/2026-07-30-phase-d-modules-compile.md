# Phase A-D: 13 子模块脚手架完成 + 关键基础设施修复

**日期**: 2026-07-30
**提交**: `828923f`
**编译错误**: 4675 → 66 (98.6% 减少)

## 完成内容

### A. 脚手架（13 个新子模块）

| Gradle 模块 | AOSP bp 模块 | 类型 | 描述 |
|------|------------|------|------|
| `:SystemUI-utils-kairos` | `utils/kairos` | android_library | Functional reactive programming utilities |
| `:SystemUI-compose-core` | `PlatformComposeCore` | android_library | Compose core (Animation, theme, gesture) |
| `:SystemUI-compose-scene` | `PlatformComposeSceneTransitionLayout` | android_library | Compose scene framework (45+ 文件) |
| `:SystemUI-shared-biometrics` | `BiometricsSharedLib` | android_library | Biometrics shared lib (Udfps, PromptKind) |
| `:SystemUI-shared-keyguard` | `SystemUISharedLib-Keyguard` | android_library | Keyguard shared (PinShapeInput) |
| `:SystemUI-proto` | `SystemUI-proto` | java_library | protobuf.nano classes (NO-SOURCE) |
| `:SystemUI-pods-dagger` | `pods/com/android/systemui/dagger` | android_library | Dagger qualifiers |
| `:SystemUI-pods-retail` | `pods/com/android/systemui/retail` | android_library | Retail mode impl |
| `:SystemUI-pods-data` | `pods/com/android/systemui/retail/data` | android_library | Retail data (api+impl) |
| `:SystemUI-pods-domain` | `pods/com/android/systemui/retail/domain` | android_library | Retail domain (api+impl) |
| `:SystemUI-pods-settings` | `pods/com/android/systemui/util/settings` | android_library | Settings pod API |

### B. 文件迁移

152 个 AOSP src 文件从 `SystemUI-core/src/` 物理迁移到对应子模块，按 AOSP `Android.bp` 1:1 对齐。

### C. 依赖图

每个子模块通过 `implementation(project(":xxx"))` 引用其他子模块 + 必需的 prebuilt JARs。

## 关键基础设施修复

### 1. Kotlin 2.x Compose Compiler Plugin (REQUIRED)

**症状**: 所有 Compose 模块（compose-core, compose-scene）报：
```
Couldn't inline method call: CompositionLocal.getCurrent()
Caused by: java.lang.IllegalStateException: couldn't find inline method
  Landroidx/compose/runtime/CompositionLocal;.getCurrent()Ljava/lang/Object;
```

**根因**: Kotlin 2.0+ 把 Compose Compiler 从 KGP 拆出为独立插件 `org.jetbrains.kotlin.plugin.compose`。没有它，Kotlin 编译器不会生成 Compose inline metadata，导致 IR lowering 阶段失败。

**修复**: `gradle/libs.versions.toml` 新增 plugin alias：
```toml
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
```
所有含 Compose 代码的模块添加 `alias(libs.plugins.kotlin.compose)` 到 plugins 块。

**参考**: [Kotlin Compose Compiler 迁移指南](https://kotlinlang.org/docs/compose-compiler-migration-guide.html)

### 2. framework.jar 不应加到 KotlinCompile.libraries

**症状**: 添加 framework.jar 到 Kotlin 编译 classpath 后，所有 Compose 模块仍报 "Couldn't inline method call"。

**根因**: framework.jar 污染了 Kotlin 编译器解析 Compose inline metadata 的路径。framework.jar 中含 `androidx.compose.*` 之类的隐藏 stub 类（如果有），或者 `classpath.from()` 顺序打断了 AGP 内部对 Compose AAR 的优先级管理。

**修复**: `build.gradle.kts` 中：
```kotlin
// 之前（错）
tasks.withType<KotlinCompile>().configureEach {
    libraries.from(frameworkJar)  // ← 移除这行
}

// 之后（对）
tasks.withType<KotlinCompile>().configureEach {
    compilerOptions { jvmTarget.set(...) }
}
```

framework.jar 只加到 `JavaCompile.classpath`（供 Kotlin 调 javac 时使用），不加到 `KotlinCompile.libraries`。

### 3. Compose 1.7.5 → 1.8.3

**症状**: compose-scene 模块 9 个错误：
```
Class 'BaseContentOverscrollEffect' is not abstract and does not implement abstract member:
val effectModifier: Modifier
Class 'OffsetOverscrollEffect' is not abstract and does not implement abstract member:
val effectModifier: Modifier
'node' overrides nothing.
Cannot access 'constructor(packedValue: Long): IntSize': it is internal in 'androidx/compose/ui/unit/IntSize'
```

**根因**: AOSP SystemUI 是按 Compose 1.8.x 写的：
- 1.7.x: `OverscrollEffect.effectModifier` 是具体属性（可空），node 不存在
- 1.8.x: `OverscrollEffect.effectModifier` 是抽象属性（必须实现），`node: DelegatableNode` 引入
- `IntSize(Long)` 1.8.x 才开放为 internal 构造函数

**修复**: 所有 Compose 依赖 1.7.5 → 1.8.3。`material-icons-core/extended` 保留 1.7.8（1.7 后停止发布）。

## 模块命名空间修正

### BiometricsSharedLib: `com.android.systemui.biometrics` → `com.android.systemui.shared.biometrics`

AOSP AndroidManifest.xml `package="com.android.systemui.shared.biometrics"`。脚手架初次生成时 namespace 错误，导致 import `com.android.systemui.shared.biometrics.R` 找不到 R 类。

## SystemUI-proto 模块清空

AOSP `SystemUI-proto` 是 `java_library`，**只含 .proto 文件**（生成 protobuf.nano 类）。`map_extras_to_modules.py` 错把 `com/android/systemui/flags/Flags.kt` 等 2 个文件配到 proto 模块（bp_path 用了 `.`）。这些应属 systemui.flags 范畴，已删除：
```bash
rm -rf SystemUI-proto/src/main/java
```

修改 `docs/extras-file-mapping.csv` 移除 2 条 proto 错误映射。

> **注记（2026-08-26，Task 063）**：本文件引用的 `map_extras_to_modules.py` 与
> `docs/extras-file-mapping.csv` 已于 2026-08-26 经用户批准删除。历史内容保留原样。

## SystemUI-shared-biometrics 补 res 目录

AOSP `BiometricsSharedLib.Android.bp`：
```bp
resource_dirs: ["res"],
```

但共享库有 1 个 strings.xml（`udfps_accessibility_touch_hints_up` 等）。脚手架未复制 res，导致 R 类不生成。手动复制：
```bash
cp -r /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/shared/biometrics/res \
   SystemUI-shared-biometrics/src/main/
```

## pods-* 依赖链路

| 模块 | 缺什么依赖 | 来自 |
|------|----------|------|
| pods-settings | `javax.inject.*` (Inject, Qualifier) | `libs.dagger` |
| pods-settings | `@AnyThread`/`@WorkerThread` | `:SystemUI-pods-dagger` |
| pods-settings | `conflatedCallbackFlow` | `:SystemUI-common` |
| pods-settings | `traceSection` | `tracinglib-platform.jar` |
| pods-settings | `Flags.something()` | `systemui-flags.jar` |
| pods-data | `GlobalSettings` / `SecureSettings` | `:SystemUI-pods-settings` |
| pods-data | `conflatedCallbackFlow` | `:SystemUI-common` |
| pods-domain | `SysUISingleton` / `Inject` | `:SystemUI-pods-dagger` + `libs.dagger` |
| pods-retail | (uses data+domain) | `:SystemUI-pods-data` + `:SystemUI-pods-domain` |
| pods-dagger | `javax.inject.*` | `libs.dagger` |

## 错误统计

| 阶段 | 错误数 | 备注 |
|------|--------|------|
| 起始 | 4675 | Phase A 脚手架后 |
| compose-scene fix | 4620 | + 9 → 0 (compose-scene 全错) |
| 1.7.5 → 1.8.3 | 4000+ | 大幅减少 |
| scaffold + settings.gradle | 3567 | 13 子模块 |
| 修复 namespace | 4620 | biometrics namespace 修正 |
| **Phase D 末** | **66** | compose plugin + 依赖全修 |

## 剩余 66 错误的分类

| 类型 | 计数 | 来源 |
|------|------|------|
| 缺失 R.string/R.drawable 资源 | ~30 | AOSP res-keyguard/res-product 中提取，尚未合并 |
| 缺失 Flags.* | ~10 | 设置库 flags (settingslib-flags.jar) 等 |
| 缺失 LottieColorUtils | 2 | Lottie 内部工具 |
| SystemUIR / SystemUIAppComponentFactoryBase | 5 | Dagger generated code (KAPT 禁用后未生成) |
| 其它 | ~19 | Domain 内部 (communal, dreams) 等 |

下一步：在 Phase E 处理 R 资源合并 + Flags 增量 + Dagger 重新启用。