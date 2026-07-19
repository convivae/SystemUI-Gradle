# 2026-07-18: 使用真实 framework.jar 编译问题

## 问题一：Kotlin 编译器错误 - QSTile 符号找不到

### 错误信息

```
e: java.lang.IllegalStateException: Value class underlying type is not a simple type: @R|kotlin/jvm/JvmInline|() public final value class Tile : R|com/android/systemui/qs/pipeline/domain/interactor/CurrentTilesInteractorImpl.TileOrNotInstalled|
    public constructor(tile: <ERROR TYPE REF: Symbol not found for QSTile>)

at org.jetbrains.kotlin.fir.backend.utils.IrElementsCreationUtilsKt.computeValueClassRepresentation$lambda$7
```

### 发生位置

`SystemUI-core` 模块编译时，`kaptGenerateStubsDebugKotlin` 任务失败。

### 根本原因

`QSTile` 类来自 `com.android.systemui.qs` 包，但 Kotlin 编译器无法找到该符号。这可能是因为：

1. **模块依赖顺序问题**：`SystemUI-core` 依赖于自身包内的 `QSTile` 类
2. **R 类生成顺序问题**：资源编译尚未完成，R 类不存在
3. **源码结构问题**：源码可能在错误的目录下

### 当前项目源码结构

```
SystemUI-core/src/
├── com/
│   ├── android/
│   │   ├── keyguard/    # 只包含 keyguard 模块
│   │   └── systemui/     # 只包含根级别类
```

### AOSP SystemUI 源码结构

```
frameworks/base/packages/SystemUI/src/
├── com/android/systemui/
│   ├── qs/               # 包含 QSTile 类
│   ├── statusbar/
│   ├── notifications/
│   └── ... (100+ 模块)
```

### 解决方案探索

#### 方案 A：完整复制 AOSP SystemUI 源码

参考 CarSystemUIGradle 项目，需要：

1. 从 AOSP `frameworks/base/packages/SystemUI/src` 完整复制所有源码到 `SystemUI-core/src`
2. 确保所有模块（qs, statusbar, notifications 等）都在同一源码树中

#### 方案 B：使用 AAR 模块依赖

将 SystemUI 拆分为多个 Gradle 模块：
- `:SystemUI-qs`
- `:SystemUI-statusbar`
- `:SystemUI-notifications`
- 等等

但这需要大量重构。

#### 方案 C：检查并修复 R 类生成顺序

确保资源编译任务在 Kotlin 编译之前完成。

### 当前状态

❌ **阻塞中** - 需要完整复制 AOSP SystemUI 源码

---

## 问题二：资源重复 - res-product 不兼容 Gradle

### 错误信息

```
ERROR: Found item String/inattentive_sleep_warning_message more than one time.
```

### 根本原因

AOSP 使用 `res-product` 目录存储产品特定资源，使用 `product="tv"` / `product="default"` 属性。

Gradle/Android Gradle Plugin 不支持这种资源分区方式。

### 解决方案

暂时从 `sourceSets` 中移除 `res-product`。

长期方案：
1. 使用 Android Product Flavors
2. 或将 product-specific 资源合并到主 `res` 目录

### 当前状态

✅ **已绕过** - 移除 res-product 引用

---

## 问题三：编译 SDK 版本警告

### 警告信息

```
WARNING: compile SDK preview version "SysUISdk" has not been tested with this version of the Android Gradle plugin.
This Android Gradle plugin (9.2.0) was tested up to compile SDK version 37.0.
```

### 解决方案

在 `gradle.properties` 中添加：

```properties
android.suppressUnsupportedCompileSdk=SysUISdk
```

### 当前状态

⚠️ **待处理** - 添加 suppress 配置

---

## 问题四：AGP 新 DSL 弃用警告

### 警告信息

```
WARNING: The option setting 'android.newDsl=false' is deprecated.
w: 'fun Project.android(configure: Action<LibraryExtension>): Unit' is deprecated.
```

### 解决方案

1. 迁移到 AGP 新 DSL（`androidComponents` 扩展）
2. 或保持 `android.newDsl=false` 并忽略警告

### 当前状态

⚠️ **待处理** - AGP 升级时迁移

---

## 依赖体系参考

### CarSystemUIGradle 项目依赖

```
CarSystemUIGradle/
├── libs/
│   ├── framework.jar              # 设备编译的 framework.jar
│   ├── framework-statsd.jar
│   ├── android.car.jar           # Car API
│   ├── WindowManager-Shell.jar    # WM Shell
│   ├── android_module_lib_stubs_current.jar  # Stub（最终应移除）
│   ├── SystemUI-proto.jar
│   ├── SystemUI-statsd.jar
│   ├── SystemUI-tags.jar
│   └── maven/                     # 本地 Maven 仓库
│       ├── com/android/systemui/SettingsLib/
│       ├── com/android/systemui/WifiTrackerLib/
│       ├── com/android/systemui/iconloader/
│       ├── com/android/systemui/WindowManager-Shell/
│       └── ... (car-ui-lib, car-uxr-client-lib 等)
├── tools/
│   └── gen_aar_maven.py           # 从 AOSP 编译产物生成 AAR
```

### gen_aar_maven.py 功能

1. 从 AOSP `out/soong/.intermediates/` 提取 JAR
2. 提取资源文件
3. 清理冲突的类（AndroidX、Guava、Kotlin 等）
4. 打包为 AAR
5. 安装到本地 Maven 仓库

### Maven 仓库 AAR 列表

| AAR 名称 | 源码路径 | 用途 |
|---------|---------|------|
| SettingsLib | frameworks/base/packages/SettingsLib | 设置相关 UI |
| iconloader | frameworks/libs/systemui/iconloaderlib | 图标加载 |
| WindowManager-Shell | frameworks/base/libs/WindowManager/Shell | WM Shell |
| WifiTrackerLib | frameworks/opt/net/wifi/libs/WifiTrackerLib | WiFi 状态 |
| car-ui-lib | packages/apps/Car/libs/car-ui-lib | Car UI 组件 |
| CarNotificationLib | packages/apps/Car/Notification | Car 通知 |
| car-qc-lib | packages/apps/Car/systemlibs/car-qc-lib | Car QC |
| car-uxr-client-lib | packages/apps/Car/libs/car-uxr-client-lib | Car UXR |
| car-assist-client-lib | packages/apps/Car/systemlibs/car-assist-client-lib | Car Assist |

---

## 问题五：Kotlin 插件版本冲突

### 错误信息

```
Error resolving plugin [id: 'org.jetbrains.kotlin.android', version: '2.3.21']
> The request for this plugin could not be satisfied because the plugin is already on the classpath with an unknown version, so compatibility cannot be checked.
```

### 根本原因

在 `libs.versions.toml` 中声明了 Kotlin 版本 `2.3.21`，但该版本与 Gradle 9.5 不兼容或已在 classpath 中存在。

### 解决方案

1. 在 `settings.gradle.kts` 中显式声明 Kotlin 插件版本
2. 降低 Kotlin 版本至 `1.9.22`（与 AGP 9.2.0 兼容）

```kotlin
// settings.gradle.kts
plugins {
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
}
```

```toml
# libs.versions.toml
[versions]
kotlin = "1.9.22"
```

### 当前状态

✅ **已修复** - 使用 Kotlin 1.9.22

---

## 问题六：AGP 9.2.0 新 DSL 语法不兼容

### 错误信息

```
e: Unresolved reference 'kotlinOptions'
e: Unresolved reference 'jvmTarget'
e: Unresolved reference 'kapt'
```

### 根本原因

AGP 9.0+ 使用新 DSL，旧语法 `kotlinOptions { jvmTarget = "11" }` 已弃用。

### 解决方案

1. 确保 `kotlin-android` 插件正确应用
2. 使用新版 Kotlin DSL：

```kotlin
// 新语法
kotlin {
    jvmToolchain(11)
}

// kapt 配置保持不变
kapt {
    correctErrorTypes = true
}
```

3. 更新 `sourceSets` 使用 `listOf()` 替代可变参数

### 当前状态

✅ **已修复** - 更新 build.gradle.kts 使用新 DSL

---

## 问题七：Platform SDK 找不到

### 错误信息

```
Could not determine the dependencies of task ':SystemUI-core:extractDebugAnnotations'.
> Failed to find Platform SDK with path: platforms;android-JdJkcSdk
```

### 根本原因

`compileSdkPreview = "JdJkcSdk"` 指定的 SDK 平台在本地 Android SDK 中不存在。

### 解决方案

1. 检查本地 Android SDK 中可用的平台版本：

```bash
ls /home/conv/Android/Sdk/platforms/
```

2. 方案 A：使用可用的 SDK 版本（如 `android-34`）

```kotlin
android {
    compileSdk = 34  // 或 35、36 等
    // compileSdkPreview = "JdJkcSdk"  // 注释掉
}
```

3. 方案 B：创建符号链接或复制 SDK 平台目录

4. 方案 C：从 AOSP out 目录复制编译好的 platform

### 当前状态

⏳ **待处理** - 需要配置正确的 SDK 平台

---

## 问题八：stub.jar 依赖需要移除

### 要求

用户明确要求：**不允许使用 stub**

### 根本原因

当前 `SystemUI-core/build.gradle.kts` 中包含：

```kotlin
compileOnly(files("${rootProject.projectDir}/libs/android_module_lib_stubs_current.jar"))
```

这是 AOSP 编译的 stub JAR，包含占位符类和接口，不应该用于最终编译。

### 解决方案

1. 保留 `framework.jar`（真实运行时）
2. 移除 `android_module_lib_stubs_current.jar`
3. 依赖的类需要通过其他方式提供：
   - 从 AOSP `out/soong/.intermediates/` 提取真实编译产物
   - 使用 Maven AAR 方式引入
   - 或将相关模块复制为子项目

### 当前状态

✅ **要求确认** - 按用户要求不使用 stub

---

## 问题九：源码不完整导致编译失败

### 错误信息

```
e: java.lang.IllegalStateException: Value class underlying type is not a simple type:
   @R|kotlin/jvm/JvmInline|() public final value class Tile :
   R|com/android/systemui/qs/pipeline/domain/interactor/CurrentTilesInteractorImpl.TileOrNotInstalled|
    public constructor(tile: <ERROR TYPE REF: Symbol not found for QSTile>)
```

### 根本原因

当前项目的 `SystemUI-core/src` 只有部分源码，缺少关键模块如 `qs/`、`statusbar/` 等。

### 解决方案

#### 已完成：复制 plugin 模块源码

```bash
# SystemUI-plugin 需要 plugin_core 和 animation 模块
cp -r /path/to/aosp/.../plugin/src/* SystemUI-plugin/src/main/
cp -r /path/to/aosp/.../plugin_core/src/* SystemUI-plugin-core/src/main/
cp -r /path/to/aosp/.../animation/src/* SystemUI-animation/src/
```

#### 进行中：解决循环依赖问题

需要确保依赖关系正确：
- SystemUI-plugin-core: 基础插件框架
- SystemUI-animation: 动画相关
- SystemUI-shared: 共享代码
- SystemUI-plugin: 插件接口
- SystemUI-core: 核心代码

### 当前状态

⏳ **进行中** - 正在解决子模块依赖问题

---

## 问题十：模块依赖缺失

### 错误信息

```
error: package com.android.systemui.plugins.annotations does not exist
error: package com.android.systemui.animation does not exist
```

### 解决方案

在 `SystemUI-plugin/build.gradle.kts` 添加依赖：

```kotlin
dependencies {
    implementation(project(":SystemUI-plugin-core"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-shared"))
    // ...
}
```

在 `SystemUI-animation/build.gradle.kts` 添加依赖：

```kotlin
dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
}
```

### 当前状态

⏳ **进行中** - 需要持续修复依赖

---

## 下一步计划

### 优先级 1：完成子模块编译

1. SystemUI-plugin-core ✅ 已复制源码
2. SystemUI-animation ⏳ 需要添加更多依赖
3. SystemUI-shared ✅ 配置完成
4. SystemUI-plugin ⏳ 依赖循环问题
5. SystemUI-core ⏳ 依赖上游模块

### 优先级 2：运行 gen_aar_maven.py

1. 配置 AOSP_ROOT 指向实际 AOSP 目录
2. 运行脚本生成所有 AAR
3. 验证 AAR 正确性

### 优先级 3：移除 Stub 依赖

1. 确认 `android_module_lib_stubs_current.jar` 不再需要
2. 从依赖中移除

---

## 验证命令

```bash
# 检查当前源码结构
find /home/conv/myspace/SystemUI-Gradle/SystemUI-core/src -name "*.kt" -o -name "*.java" | wc -l

# 尝试编译
cd /home/conv/myspace/SystemUI-Gradle
./gradlew assembleDebug

# 检查 AOSP 源码
find /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src -name "QSTile*" -o -name "CurrentTilesInteractorImpl*"
```
