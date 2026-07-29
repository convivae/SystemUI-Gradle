# ADR 0003: 项目结构对齐 AOSP `frameworks/base/packages/SystemUI/Android.bp`

## 上下文

AOSP 用 soong (`Android.bp`) 定义 SystemUI 的模块图：

- `android_app "SystemUI"` (Android.bp:958) 是 APK 入口，只 `static_libs: ["SystemUI-core"]`
- `android_library "SystemUI-core"` (Android.bp:421) 是核心库，`srcs: [src/**, compose/**]`，`static_libs` 含 **所有子模块**（shared/animation/customization/unfold/log/common/plugin 等）
- 其它子模块（shared/animation/customization/unfold/log/common/plugin/plugin-core）是独立 `android_library`

**当前项目结构问题**：

1. `app/build.gradle.kts` 多余地 `implementation(project(":SystemUI-shared"))` 等 —— `SystemUI-core` 已通过 static_libs 引入，重复
2. `SystemUI-core/src/com/android/systemui/SystemUIApplication.java` 和 `SystemUIService.java` 是 AOSP `android_app` 的入口，但放在 `android_library` (core) 里 —— 与 AOSP 不对齐
3. `app/src/main/AndroidManifest.xml` 仅 4 行，AOSP 原版 1158 行（service、permission、receiver 大量）
4. AOSP `android_app "SystemUI"` 还引用 `proguard.flags` / `proguard_common.flags` / `proguard_kotlin.flags` / `AndroidManifest-res.xml` / `privapp_whitelist_com.android.systemui` —— 当前 `:app` 都没有
5. 模块命名/边界虽然大体对齐，但**判断标准未明确文档化**：哪些按源码模块、哪些按 jar、哪些按 aar → 用户给的新规则：按 bp 文件定义

## 决策

### 决策 1：模块划分与命名以 AOSP `Android.bp` 为唯一标准

- `android_app "SystemUI"` → 项目 `:app`（Kotlin `com.android.application` plugin）
- `android_library "SystemUI-core"` → 项目 `:SystemUI-core`
- `android_library "SystemUISharedLib"` → 项目 `:SystemUI-shared`
- `android_library "PlatformAnimationLib"` → 项目 `:SystemUI-animation`
- `android_library "SystemUICustomizationLib"` → 项目 `:SystemUI-customization`
- `android_library "SystemUICommon"` → 项目 `:SystemUI-common`
- `android_library "SystemUILogLib"` → 项目 `:SystemUI-log`
- `android_library "SystemUIUnfoldLib"` → 项目 `:SystemUI-unfold`
- `android_library "SystemUIPluginLib"` → 项目 `:SystemUI-plugin`（运行时接口）
- `android_library "PluginCoreLib"` + `PluginAnnotationLib` → 项目 `:SystemUI-plugin-core`（编译时注解）

→ 已基本对齐，唯一例外 `:SystemUI-animationlib`（来自 `animation/lib/`，AOSP 也有独立 soong 模块）

### 决策 2：依赖关系严格按 bp 的 static_libs / libs 顺序

`:app` 只依赖 `:SystemUI-core`，不再写 `:SystemUI-shared/-animation/...` 这些 —— 全部由 `:SystemUI-core` 的 `static_libs` 串起来。

`:SystemUI-core` 的依赖按 AOSP bp 顺序：

```
tier① 源码子模块（按 bp static_libs 顺序）：
  :SystemUI-shared, :SystemUI-animation, :SystemUI-customization,
  :SystemUI-common, :SystemUI-log, :SystemUI-unfold,
  :SystemUI-plugin, :SystemUI-plugin-core
tier② AOSP 特有 jar/aar：
  framework.jar, framework-statsd.jar, monet.jar,
  android.car.jar, WindowManager-Shell.jar, WifiTrackerLib,
  SettingsLib (maven-aar), iconloader (maven-aar),
  systemui-flags, settingslib-flags, notification-flags,
  SystemUI-{proto,statsd,tags} (生成物 jar)
tier③ 公网 maven（按 bp 顺序）：
  androidx.core-ktx, viewpager2, legacy-support-v4,
  recyclerview, preference, appcompat,
  concurrent-futures, concurrent-futures-ktx,
  mediarouter, palette, legacy-preference-v14, leanback,
  slice-{core,view,builders}, arch.core:core-runtime,
  lifecycle-{common-java8,extensions,runtime-ktx},
  dynamicanimation, constraintlayout, exifinterface,
  room-{runtime,ktx}, datastore-preferences,
  media3-{common,session}, material,
  kotlinx-coroutines-{android,core},
  dagger2, jsr305, jsr330, lottie, lottie-compose
```

### 决策 3：`android_app "SystemUI"` 引用文件 → 全部迁到 `:app`

AOSP Android.bp 表明 `android_app "SystemUI"` 涉及以下文件/属性，必须从 AOSP 复制/移动到 `:app/`，**不能漏**：

| AOSP 路径（相对 `frameworks/base/packages/SystemUI/`） | 行数/类型 | 在 `:app` 中的目标位置 | 状态 |
|------|------|------|------|
| `AndroidManifest.xml` | 1158 行（service/permission/receiver/activity 声明） | `:app/src/main/AndroidManifest.xml` | 缺失（当前 4 行） |
| `AndroidManifest-res.xml` | 16 行（空壳 manifest `package="com.android.systemui.res"`，用于 aapt2 资源处理） | `:app/src/main/AndroidManifest-res.xml` | 缺失 |
| `src/com/android/systemui/SystemUIApplication.java` | 入口类 | `:app/src/main/java/com/android/systemui/SystemUIApplication.java` | 在 `:SystemUI-core/src/`，需移 |
| `src/com/android/systemui/SystemUIService.java` | 服务入口 | `:app/src/main/java/com/android/systemui/SystemUIService.java` | 在 `:SystemUI-core/src/`，需移 |
| `proguard.flags` | 7 行（include 公共/kotlin flags + keep 规则） | `:app/proguard.flags` | 缺失 |
| `proguard_common.flags` | 72 行（反射保护、回调字段等） | `:app/proguard_common.flags` | 缺失 |
| `proguard_kotlin.flags` | 37 行（Kotlin 反射/Metadata） | `:app/proguard_kotlin.flags` | 缺失 |
| `privapp_whitelist_com.android.systemui` | 系统权限白名单（OEM 设备配置，**只在真机签名时校验**，本项目编译不必） | **不复制**（注释标记） | 不复制 |

### 决策 4：SystemUIApplication / SystemUIService 迁移动作

- `:SystemUI-core/src/com/android/systemui/SystemUIApplication.java` → `:app/src/main/java/com/android/systemui/SystemUIApplication.java`
- `:SystemUI-core/src/com/android/systemui/SystemUIService.java` → `:app/src/main/java/com/android/systemui/SystemUIService.java`
- `:SystemUI-core/build.gradle.kts` 的 `sourceSets.main.java.srcDirs` 不需要排除（Gradle 编译时按 `java.srcDirs("src")` 包含所有，移走即不参与编译）

### 决策 5：resource_dirs 在 `:app` 与 `:SystemUI-core` 之间的分配

- `:SystemUI-core/res{,-keyguard,-product}/` 持有所有 AOSP 资源（规则 C：1:1 完整复制）
- `:app` 不再持有 res；apk 打包时由 aapt2 收集 `:SystemUI-core` 的所有 res

### 决策 6：build.gradle.kts 配置项按 bp 转换

| AOSP bp 属性 | Gradle 翻译 | `:app/build.gradle.kts` 写法 |
|------|------|------|
| `static_libs: ["SystemUI-core"]` | `implementation(project(":SystemUI-core"))` | 仅这一行 + framework 等 jar |
| `platform_apis: true` | 隐含（compileSdkPreview = "SysUISdk"） | 已有 |
| `system_ext_specific: true` | 注释标记（Gradle 无对应） | 注释 `// AOSP: system_ext_specific: true` |
| `privileged: true` | 注释标记 | 注释 `// AOSP: privileged: true` |
| `certificate: "platform"` | `signingConfig` 引用 platform keystore | 已有（`signingConfigs.release`） |
| `kotlincflags: ["-Xjvm-default=all"]` | `kotlinOptions.freeCompilerArgs += "-Xjvm-default=all"` | 加 |
| `dxflags: ["--multi-dex"]` | minSdk 21+ 自动 multi-dex | 已有 minSdk=35 |
| `use_resource_processor: true` | aapt2 自动 | 无需 |
| `optimize.proguard_flags_files: ["proguard.flags"]` | `proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard.flags")` | 加 |
| `defaults: ["platform_app_defaults", "SystemUI_optimized_defaults", "wmshell_defaults"]` | 不翻译（AOSP 平台层配置，由 soong 注入；Gradle 不存在） | 注释标记 |
| `required: ["privapp_whitelist_com.android.systemui"]` | 不复制（OEM 设备） | 注释标记 |

## 副作用 / 约束

- 移动入口类时需更新 :SystemUI-core/build.gradle.kts 不再 include 这两个文件；`:app/build.gradle.kts` 加 `aidl.srcDirs("src/main/aidl")`（如果有 aidl）
- 当前 4 行 manifest 不够：缺失 `uses-permission`（RECEIVE_BOOT_COMPLETED、READ_EXTERNAL_STORAGE 等 50+）和 `service` / `receiver` / `activity` 声明
- 删除 `app/build.gradle.kts` 中冗余的 `implementation(project(":SystemUI-shared"))` 等
- `proguard.flags` 引用 `proguard_common.flags`（`include`），后者引用 `proguard_kotlin.flags`，路径相对：需按相对 `:app/` 根
- **不解决编译错误**（本 ADR 只解决"结构不对齐"，编译错误是后续 commit 解决，符合规则 I 增量）

## 决策状态

- **结构对齐阶段**（本 ADR）：复制 + 移动文件 + 配置项翻译，**预期可能编译失败**（规则 I 例外适用 — 结构对齐属于"基准对齐"）
- **错误修复阶段**（后续 commit）：在结构对齐基础上，**逐个** 解决编译错误

## 参考

- AOSP `frameworks/base/packages/SystemUI/Android.bp`（420 行 SystemUI-core、772 行 android_app、936 行 optimized_defaults）
- AOSP `frameworks/base/packages/SystemUI/AndroidManifest.xml`（1158 行）
- AOSP `frameworks/base/packages/SystemUI/AndroidManifest-res.xml`（16 行，空壳）
- AOSP `frameworks/base/packages/SystemUI/proguard.flags`（7 行）
- AOSP `frameworks/base/packages/SystemUI/proguard_common.flags`（72 行）
- AOSP `frameworks/base/packages/SystemUI/proguard_kotlin.flags`（37 行）
- AOSP `out/soong/.intermediates/frameworks/base/data/etc/privapp_whitelist_com.android.systemui`（OEM 配置，不复制）
- AGENTS.md §1.5 规则 S（Source-first）+ §1.6 规则 C（不漏不多）+ §1.9 规则 B（bp 对齐）
- `CarSystemUIGradle/app/build.gradle.kts` 参考实现