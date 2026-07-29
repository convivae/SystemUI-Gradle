# 2026-07-29 会话记录：AIDL 编译原理、animationlib 源码化、app 模块调研

> **日期**: 2026-07-29
> **状态**: 进行中（animationlib 源码已复制但未提交，app 模块调研完成待实施）

---

## 一、AIDL 编译原理与 framework.jar 的关系

### 1.1 用户问题

"为什么不能直接使用 framework.jar？这个 aidl 为什么没有打进 jar 包里面？"

### 1.2 结论

**framework.jar 和 framework.aidl 服务于两个不同的编译阶段，二者互补不可替代。**

```
.aidl 源文件 ──[aidl 工具]──> 生成 .java 桩代码 ──[javac/kotlinc]──> .class ──> jar
     ↑                                                    ↑
  需要 framework.aidl                              需要 framework.jar
  (类型声明表)                                     (真实字节码)
```

| 阶段 | 工具 | 输入 | 输出 |
|------|------|------|------|
| aidl 编译 | `aidl` 工具 | `.aidl` 文件 + `framework.aidl` | `.java` 桩代码 |
| Java/Kotlin 编译 | `javac` / `kotlinc` | `.java`/`.kt` + `framework.jar` | `.class` 字节码 |

**为什么 aidl 不读 jar？**

1. **jar 格式只装 `.class`**，没有 `.aidl` 的概念。AIDL 声明是编译输入源，不是运行时类，不进 jar。
2. **aidl 工具设计上只认 `.aidl` 声明**，不会去翻 jar 里的字节码推断类型。
3. **即使让 aidl 从字节码推断也不行**——AIDL 语义里 `parcelable` 声明可以携带字节码里不存在的信息（稳定性 stable AIDL、可空性、C++ 头文件路径等），所以 aidl 坚持要显式的 `parcelable X;` 声明。

**AOSP 的处理方式**：AOSP 构建时用 `aidl --preprocess` 把 framework 所有 `.aidl` 声明拼接成一个大文件，就是 SDK 平台目录里的 `framework.aidl`。这个文件就是为「下游 aidl 编译能解析 framework 类型」而存在的。

### 1.3 落到我们项目

- `framework.jar` 提供了 `ScreenshotRequest` 的**类**（Kotlin/Java 编译够用）
- 但 aidl 编译 `ISystemUiProxy.aidl` 时缺 `ScreenshotRequest` 的**声明**，而 public SDK 的 `framework.aidl` 没收录这个 `@hide` 类型
- 所以我们往 framework.aidl 补了一行 `parcelable com.android.internal.util.ScreenshotRequest;`

---

## 二、ISystemUiProxy.aidl 归属与调用链

### 2.1 用户问题

"哪个模块调用的这个 aidl？这个模块的代码位于哪？"

### 2.2 结论

| 项目 | 详情 |
|------|------|
| aidl 文件位置 | `SystemUI-shared/src/com/android/systemui/shared/recents/ISystemUiProxy.aidl` |
| 编译模块 | `:SystemUI-shared`（`buildFeatures.aidl = true`，`aidl.srcDirs("src")`） |
| 编译 task | `:SystemUI-shared:compileDebugAidl` |
| 缺失声明触发点 | 第 26 行 `import com.android.internal.util.ScreenshotRequest;`，被第 136 行 `takeScreenshot(in ScreenshotRequest request)` 使用 |
| 同模块引用 | `IOverviewProxy.aidl`（同在 `SystemUI-shared/.../recents/`） |
| 运行时使用 | `:SystemUI-core` 的 `OverviewProxyService.java`（通过 `implementation(project(":SystemUI-shared"))` 获取） |

**数据流**：`:SystemUI-shared` 编译出 aidl 生成的 `ISystemUiProxy.java` 桩 → `:SystemUI-core` 的 `OverviewProxyService` 依赖 `project(":SystemUI-shared")` 拿到它来用。

**一句话**：是 `:SystemUI-shared` 模块在编译 `ISystemUiProxy.aidl` 时缺 `ScreenshotRequest` 声明；这个 aidl 是 SystemUI 与 Launcher 共享的 recents 代理接口，自身在 shared 模块，运行时由 core 的 `OverviewProxyService` 使用。

---

## 三、animationlib 源码化（进行中，未提交）

### 3.1 背景

根据规则 S（Source-first for SystemUI），`animationlib` 属于 ① SystemUI 自有代码（soong 模块定义在 `frameworks/libs/systemui/animationlib/Android.bp`），应该源码复制做源码依赖，而不是用 jar。

### 3.2 当前状态

- `libs/animationlib.jar`：12 个类，`com.android.app.animation.*` 包（4 个 interpolator + 8 个 animation util）
- `libs/WindowManager-Shell.jar`：也含 6 个 `com.android.app.animation.*` 类（有重叠）
- `:SystemUI-animation` 和 `:SystemUI-customization` 均以 `compileOnly(files(".../animationlib.jar"))` 引入
- `:SystemUI-core` 通过 `implementation(project(":SystemUI-animation"))` 间接获取 `com.android.app.animation.*`

### 3.3 已完成的操作

1. **复制 AOSP 源码**：`aosp/frameworks/libs/systemui/animationlib/src/` → `SystemUI-animationlib/src/main/java/`
   - 4 个 Java 文件：`Interpolators.java`、`PhysicsInterpolator.java`、`SpringInterpolator.java`、`WaveInterpolator.java`
2. **复制 AOSP res**：`aosp/frameworks/libs/systemui/animationlib/res/` → `SystemUI-animationlib/src/main/res/`
   - 4 个资源文件：`res/values/interpolators.xml`、`res/anim/...` 等
3. **创建模块骨架**：
   - `SystemUI-animationlib/build.gradle.kts`（library 模块，namespace = `com.android.app.animation`）
   - `SystemUI-animationlib/src/main/AndroidManifest.xml`（空 manifest）
4. **settings.gradle.kts**：添加 `include(":SystemUI-animationlib")`

### 3.4 待完成

- **修改 `:SystemUI-animation` 的 `build.gradle.kts`**：将 `compileOnly(files(".../animationlib.jar"))` 改为 `api(project(":SystemUI-animationlib"))`
  - 用 `api` 而非 `implementation`，因为 `:SystemUI-core` 通过 animation 模块间接引用 `com.android.app.animation.*` 类型
- **修改 `:SystemUI-customization` 的 `build.gradle.kts`**：将 `compileOnly(files(".../animationlib.jar"))` 改为 `api(project(":SystemUI-animationlib"))`
- **移除 `libs/animationlib.jar`**（避免重复类冲突）
- **验证编译**：`./gradlew :SystemUI-animationlib:compileDebugKotlin` 和 `:SystemUI-core:compileDebugKotlin`
- **检查 WindowManager-Shell.jar 的 6 个重叠类**：WMShell.jar 也含 `com.android.app.animation.*`，需要确认是否有类冲突，以及是否需要从 WMShell.jar 中排除这些类

### 3.5 注意事项

- animationlib.jar 和 WindowManager-Shell.jar 有 6 个重叠类。如果 `:SystemUI-core` 同时依赖 `project(":SystemUI-animationlib")` 和 WMShell.jar，可能出现重复类问题。
- AOSP 的 `PlatformAnimationLib` Android.bp 显式依赖 `animationlib`（`static_libs: ["animationlib"]`），说明它们是分开编译的——animationlib 是独立模块，animation 模块依赖它。

---

## 四、app 模块调研：为什么是空的

### 4.1 用户问题

"我们的 app 目录里面为什么什么都没有呢？我们应该有一些代码可以放进去吧，这应该是整个 systemui app 的入口，是用来打 apk 的，理论上可以直接通过 ./gradlew :app:assemble 来做编译的"

### 4.2 当前 :app 状态

```
app/
├── build.gradle.kts     # 已有，但依赖不完整
└── src/main/AndroidManifest.xml   # 空壳
```

`app/build.gradle.kts` 当前内容：
- `plugins`: `com.android.application` + `kotlin.android` + `kotlin-kapt`
- `namespace = "com.android.systemui"`
- `applicationId = "com.android.systemui"`
- `signingConfigs`: platform keystore
- `dependencies`: `implementation(project(":SystemUI-core"))` + 其他几个模块 + `compileOnly` framework.jar / WMShell.jar

### 4.3 AOSP SystemUI 的 APK 打包方式

AOSP 的 `SystemUI` APK 由 `frameworks/base/packages/SystemUI/Android.bp` 第 772 行的 `android_app` 模块定义。关键信息：

#### 4.3.1 APK 入口源码

AOSP 的 SystemUI APK 入口类只有 3 个文件：

| 文件 | 作用 |
|------|------|
| `src/com/android/systemui/SystemUIApplication.java` | Application 子类，初始化 Dagger 组件 |
| `src/com/android/systemui/SystemUIService.java | 核心服务，启动各种 SystemUI 功能 |
| `src/com/android/systemui/SystemUISecondaryUserService.java` | 辅助用户服务 |

这些文件**已经在 `SystemUI-core/src/` 里**（因为 core 的 src 整体复制自 AOSP），所以 `:app` 模块**不需要再复制源码**。

#### 4.3.2 AOSP 的依赖结构

AOSP 的 `android_app` 模块通过 `static_libs` 把所有代码链接进来：

```
android_app "SystemUI" {
    static_libs: [
        "SystemUI-core",           // 主模块（含 src/ 下所有业务代码）
        "SystemUI-res",            // 资源（res/ + res-keyguard/ + res-product/）
        "//frameworks/libs/systemui:compilelib",  // 所有 SystemUI 自有子模块
        "dagger2",
        "jsr330",
        // ... 其他第三方库
    ],
    libs: ["android.car-stubs"],   // compileOnly
    certificate: "platform",
    privileged: true,
    system_ext_specific: true,
    kotlincflags: ["-Xjvm-default=all"],
    optimize: { shrink_resources: false },
    plugins: ["dagger2-compiler"],
}
```

#### 4.3.3 关键发现：AOSP 的 `SystemUI-core` 是 `android_library`，不是 `android_app`

AOSP 的构建层级是：

```
SystemUI-core (android_library)  ← 只编译，不打包 APK
    ↑ static_libs
SystemUI (android_app)           ← 最终打包 APK，把 core + 其他模块链接进来
```

**对应到我们的 Gradle 结构**：
- `:SystemUI-core` = `com.android.library`（只编译，不打包 APK）✅ 已正确
- `:app` = `com.android.application`（最终打包 APK）✅ 已正确
- `:app` 通过 `implementation(project(":SystemUI-core"))` 把 core 的代码拉进来 ✅ 已正确

### 4.4 :app 模块需要补什么

#### 4.4.1 AndroidManifest.xml（必须）

AOSP 的 `AndroidManifest.xml` 非常大（数百行），包含：
- 大量 `<uses-permission>` 声明（INJECT_EVENTS、DUMP、STATUS_BAR 等）
- `<application>` 配置（sharedUserId、coreApp）
- `SystemUIService` 和 `SystemUIApplication` 的 `<service>` / `<activity>` 声明
- 各种 `<receiver>` / `<provider>` 声明

**方案**：直接从 AOSP 复制 `AndroidManifest.xml`，做必要的 Gradle 适配（去掉 soong 特有属性）。

#### 4.4.2 依赖补全（必须）

当前 `:app` 的依赖列表不完整，缺少：
- `:SystemUI-common`
- `:SystemUI-log`
- `:SystemUI-plugin-core`
- `:SystemUI-animationlib`（新增）
- tier② AOSP jar（monet.jar、systemui-flags.jar 等）
- tier③ 标准 Maven 依赖（dagger、compose 等）

**方案**：对齐 AOSP `android_app` 的 `static_libs`，补全 `:app` 的 `dependencies`。

#### 4.4.3 资源合并（必须）

AOSP 的 `SystemUI-res` 是独立的 `android_library`，只含资源。在 Gradle 中，资源通过 `:SystemUI-core` 的 `res/` / `res-keyguard/` / `res-product/` 已经包含。但 `:app` 作为 `application` 模块，需要确保所有资源被正确合并。

**方案**：`implementation(project(":SystemUI-core"))` 已经传递了资源，但需要在 `:app` 的 `android` 块中配置正确的资源合并策略。

#### 4.4.4 ProGuard / R8 配置（可选，后期）

AOSP 有 `proguard.flags` 文件，配置了 keep 规则。前期可以跳过（debug 构建不需要 shrink）。

### 4.5 :app 模块的完整实施计划

```
Phase 1: 基础可编译
  1. 从 AOSP 复制 AndroidManifest.xml 到 app/src/main/
  2. 补全 :app 的 dependencies
  3. 验证 ./gradlew :app:assembleDebug 可以运行

Phase 2: APK 内容验证
  1. 检查生成的 APK 是否包含所有类
  2. 检查资源是否正确合并
  3. 检查 AndroidManifest 是否正确合并

Phase 3: 可安装验证
  1. 用 platform keystore 签名
  2. adb install 到设备
  3. 验证 SystemUIService 启动
```

### 4.6 为什么当前 :app 是空的

**历史原因**：在 v2 骨架重建时（问题二、三），`app/` 目录被整体删除，后来只重建了 `build.gradle.kts` 和空壳 `AndroidManifest.xml`。当时的工作重心放在 `:SystemUI-core` 的编译错误消除上，`:app` 作为最终打包层，在 core 编译通过之前没有意义去填充。

**现在可以开始做了**：因为 core 的错误数已从 5296 降到 509，`SystemUIApplication` 和 `SystemUIService` 的源码已经在 core 里，`:app` 只需要正确的 manifest + 依赖 + 资源合并配置就能打 APK。

---

## 五、本次会话代码改动（未提交）

### 5.1 已修改的文件

| 文件 | 改动 |
|------|------|
| `SystemUI-animationlib/build.gradle.kts` | 重写为 library 模块配置 |
| `SystemUI-animationlib/src/main/AndroidManifest.xml` | 新建空 manifest |
| `settings.gradle.kts` | 添加 `include(":SystemUI-animationlib")` |

### 5.2 新增的文件（untracked）

| 文件/目录 | 说明 |
|-----------|------|
| `SystemUI-animationlib/src/main/java/com/android/app/animation/` | 4 个 Java 源文件（从 AOSP 复制） |
| `SystemUI-animationlib/src/main/res/` | 4 个资源文件（从 AOSP 复制） |

### 5.3 待修改的文件

| 文件 | 改动 |
|------|------|
| `SystemUI-animation/build.gradle.kts` | `compileOnly(animationlib.jar)` → `api(project(":SystemUI-animationlib"))` |
| `SystemUI-customization/build.gradle.kts` | `compileOnly(animationlib.jar)` → `api(project(":SystemUI-animationlib"))` |
| `libs/animationlib.jar` | 移除（避免重复类） |

---

## 六、待解决问题

1. **animationlib 与 WMShell.jar 的类重叠**：两者都含 `com.android.app.animation.*`，需要确认是否冲突
2. **app 模块 AndroidManifest.xml**：需要从 AOSP 复制并适配
3. **app 模块依赖补全**：需要对齐 AOSP 的 static_libs
4. **app 模块资源合并**：需要确保 res-keyguard/res-product 正确合并到 APK
