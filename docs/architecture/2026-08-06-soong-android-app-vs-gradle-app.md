# Soong `android_app` 与 Gradle `:app` 如何生成 SystemUI APK

**日期**：2026-08-06
**问题**：入口类留在 `:SystemUI-core`，`:app` 没有 Java/Kotlin 源码，是否仍能生成 APK？
**结论**：**能。** AOSP 的 `android_app "SystemUI"` 本来就没有独立 `srcs`；它通过 `static_libs: ["SystemUI-core"]` 将 core 的代码和传递资源打入最终 APK。Gradle 的 `com.android.application` + `implementation(project(":SystemUI-core"))` 是对应实现。`:app` 是 APK 打包边界，不是入口类源码目录。

---

## 1. AOSP 的实际模块图

来源：`/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/Android.bp`。

```text
SystemUI-res (android_library)
  - res-product / res-keyguard / res
  - AndroidManifest-res.xml
             ↓ static_libs
SystemUI-core (android_library)
  - src/**/*.kt / src/**/*.java / AIDL / compose
  - AndroidManifest.xml
  - SystemUIApplication.java / SystemUIService.java
  - SystemUI-res + 所有 SystemUI 子模块和外部依赖
             ↓ static_libs
SystemUI (android_app)
  - 无独立 srcs
  - resource_dirs: []
  - platform certificate / privileged / system_ext
  - 生成、签名并安装 SystemUI.apk
```

关键 bp：

```bp
android_app {
    name: "SystemUI",
    static_libs: [
        "SystemUI-core",
    ],
    resource_dirs: [],
    platform_apis: true,
    system_ext_specific: true,
    certificate: "platform",
    privileged: true,
}
```

`resource_dirs: []` 只表示 app module 没有自己的资源目录，不表示最终 APK 没有资源。资源通过 `SystemUI-core → SystemUI-res` 的 `static_libs` 链进入最终资源链接。

## 2. Soong 为什么能在 app 无源码时生成 APK

### 2.1 `AndroidApp` 本身拥有 Library 编译能力

来源：`build/soong/java/app.go` 的 `type AndroidApp struct`：

```go
type AndroidApp struct {
    Library
    aapt
    // ...
}
```

所以 `android_app` 不只是一个源码目录；它是建立在 Java/Android library 编译能力之上的最终应用打包器。

### 2.2 `static_libs` 本身就让 app 被视为“有代码”

来源：`build/soong/java/base.go` 的 `hasCode()`：

```go
return len(srcFiles) > 0 || len(ctx.GetDirectDepsProxyWithTag(staticLibTag)) > 0
```

即使 app 自己没有 `srcs`，只要有 `SystemUI-core` 这个 `static_libs`，manifest 就不会被标记为 `hasCode=false`。

### 2.3 core 实现类被静态并入

来源：`build/soong/java/base.go` 的 `collectDeps()`。对 `staticLibTag`：

```go
deps.classpath = append(deps.classpath, dep.HeaderJars...)
deps.staticJars = append(deps.staticJars, dep.ImplementationJars...)
deps.staticResourceJars = append(deps.staticResourceJars, dep.ResourceJars...)
```

因此 `SystemUI-core` 的 implementation jar 不是只用于编译，它会进入 app 的静态代码集合；core 的传递 static libs 也继续传播。

### 2.4 AAPT 链接传递资源并生成 R

来源：`build/soong/java/app.go` 的 `aaptBuildActions()` / `dexBuildActions()`。Soong 注释明确说明，AAPT 会为 app 及所有传递 `static android_library` 依赖处理 R 类和资源。

SystemUI app 自身 `resource_dirs: []`，但 `SystemUI-core` 静态依赖 `SystemUI-res`，因此最终 APK 仍包含 SystemUI 的资源。

### 2.5 最后 dex、打包、签名和安装

来源：`build/soong/java/app.go` 的 `generateAndroidBuildActions()`：

1. `aaptBuildActions()`：处理/合并 manifest 和资源
2. `dexBuildActions()`：编译静态代码并生成 dex jar
3. `CreateAndSignAppPackage()`：把资源、DEX、JNI 等装入 APK 并签名
4. `installPath()` / `InstallFile()`：按 privileged/system_ext 属性安装

AOSP 的输出是 platform-signed `SystemUI.apk`；`privileged: true` 使安装目录使用 `priv-app/SystemUI/`，`system_ext_specific: true` 决定其分区根。

## 3. Gradle 中的等价结构

当前 `app/build.gradle.kts`：

```kotlin
plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.android.systemui.app"
    defaultConfig {
        applicationId = "com.android.systemui"
    }
}

dependencies {
    implementation(project(":SystemUI-core"))
}
```

对应关系：

| Soong | Gradle/AGP | 含义 |
|---|---|---|
| `android_app` | `com.android.application` | 创建 APK variant 和最终打包任务 |
| `android_library` | `com.android.library` | 提供类、资源、manifest 的库模块 |
| `static_libs` | `implementation(...)` | 类和资源进入运行时/最终 APK |
| `libs` | `compileOnly(...)`（近似） | 编译可见，但不由当前 APK 打包 |
| AAPT link | AGP/AAPT2 resource + manifest processing | 合并资源、生成 R、处理 manifest |
| dex | D8/R8 | 把 app runtime classes 转为 classes.dex |
| `certificate: "platform"` | platform `signingConfig` | 使用平台证书签名 |
| `system_ext_specific` / `privileged` | 无完整 AGP 等价 | APK 构建后由系统镜像/部署流程决定安装位置和权限 |

`:app` 没有源码不影响 D8/R8：`implementation(project(":SystemUI-core"))` 把 core 放到 app runtime classpath，core 的类会进入最终 DEX。manifest 中的 `.SystemUIApplication` 和 `SystemUIService` 在运行时按最终 APK 的 DEX 查找，不要求源码物理位于 app module。

## 4. 当前项目已有的结构证据

2026-08-06 运行（只做 Gradle 配置/依赖解析，不编译源码）：

```bash
./gradlew :app:dependencies --configuration debugRuntimeClasspath --console=plain
```

结果：退出码 0，`debugRuntimeClasspath` 包含：

```text
+--- project :SystemUI-core
```

运行：

```bash
./gradlew :app:tasks --all --console=plain
```

结果：退出码 0，存在：

```text
assembleDebug
assembleRelease
bundleDebug
packageDebug
```

这证明 APK 任务和 core → app runtime 依赖链已经建立。

但这**不等于 APK 已成功构建**。当前工作区仍有 AAR transform 的重复 R 类阻塞；只有以下命令退出 0，才能声称 APK 已产出：

```bash
./gradlew :app:assembleDebug --console=plain
```

## 5. Manifest：AOSP 原貌与 Gradle 适配

### 5.1 AOSP

- `SystemUI-res` 显式使用 `AndroidManifest-res.xml`（空 `<application/>`）
- `SystemUI-core` 显式使用完整 `AndroidManifest.xml`
- `android_app "SystemUI"` 位于同一 bp/package 目录，最终由 Soong/AAPT 处理应用 manifest

因此旧 ADR 中“SystemUI-core 不含 manifest 字段”“AndroidManifest-res.xml 属于 android_app”的说法不正确。

### 5.2 当前 Gradle 适配

- `:app/src/main/AndroidManifest.xml`：完整 AOSP manifest（删除 AGP 不允许继续放在 manifest 的 `package=`，由 `namespace/applicationId` 管理）
- `:SystemUI-core/AndroidManifest.xml`：保留完整 manifest 的 permission/protected-broadcast 部分，不重复声明 `<application>` 组件
- `:app/src/main/AndroidManifest-res.xml`：当前文件存在，但 `app/build.gradle.kts` 没把它配置为主 manifest；它是历史复制项，后续建立独立 `SystemUI-res` module 时应按 bp 归位

这是 Gradle manifest merger 的适配：最终 APK 必须拥有完整 application/service/activity/receiver 声明，同时避免 library 和 app 重复声明同一整套组件。它不改变入口类属于 `SystemUI-core` 的事实。

## 6. `:app` 应该负责什么

`:app` 即使无源码，仍必须负责：

1. 应用插件和 APK variants
2. 最终 `applicationId = "com.android.systemui"`
3. 完整 APK manifest
4. `implementation(project(":SystemUI-core"))`
5. platform signing
6. R8/ProGuard 配置
7. APK/AAB/package tasks

不应负责：

- 保存 `SystemUIApplication.java` / `SystemUIService.java` 副本
- 直接重复依赖所有 SystemUI 子模块
- 保存 SystemUI-core 的业务源码

## 7. 后续结构审查项

1. 检查 `:app` 当前除 `:SystemUI-core` 外的直接 implementation 依赖是否真有必要；目标是尽量对应 bp 的单一 static_lib。
2. 建立独立 `:SystemUI-res` Gradle module，映射 AOSP bp 的资源边界；实施前先用对齐脚本确认现有资源文件集和 manifest 来源，不修改资源内容。
3. 检查 app/core manifest 的最终 merge 输出，而不是机械要求两个 Gradle module 都复制同一个完整 manifest。
4. 依赖清理完成后，以 `:app:assembleDebug` 和 APK 内容检查作为阶段性里程碑验证，不要求每次修改都编译。

## 8. 结论

- 入口类留在 `:SystemUI-core` 完全符合 AOSP bp。
- `:app` 无源码完全正常；它是最终 APK 生产和签名边界。
- `implementation(project(":SystemUI-core"))` 是 Gradle 对 `static_libs: ["SystemUI-core"]` 的对应表达。
- 当前 Gradle 打包链路已经配置出来，但尚未通过实际 `assembleDebug`，不能提前宣称 APK 已构建成功。
