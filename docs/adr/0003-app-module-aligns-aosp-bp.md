# ADR 0003: 项目结构对齐 AOSP `frameworks/base/packages/SystemUI/Android.bp`

**状态**：已接受；2026-07-31 修正入口类归属，2026-08-06 修正 manifest 归属和 APK 打包解释，2026-08-06 修正决策 1 为“语义对齐而非 target 1:1”

## 上下文

AOSP 用 soong (`Android.bp`) 定义 SystemUI 的模块图：

- `android_app "SystemUI"` (Android.bp:958) 是 APK 入口，只 `static_libs: ["SystemUI-core"]`
- `android_library "SystemUI-core"` (Android.bp:421) 是核心库，`srcs: [src/**, compose/**]`，`static_libs` 含 **所有子模块**（shared/animation/customization/unfold/log/common/plugin 等）
- 其它子模块（shared/animation/customization/unfold/log/common/plugin/plugin-core）是独立 `android_library`

**历史问题与更正**：

1. `app/build.gradle.kts` 曾多余地直接依赖 `:SystemUI-shared` 等；目标是由 `SystemUI-core` 的依赖链传递
2. 早期误以为 `SystemUIApplication.java` / `SystemUIService.java` 应迁到 app；2026-07-31 已确认它们被 core 的 `src/**/*.java` 包含，必须留在 core
3. `app/src/main/AndroidManifest.xml` 曾只有 4 行；现已复制完整 AOSP manifest
4. AOSP app 还涉及 platform signing、ProGuard、privileged/system_ext 等打包属性，需要在 Gradle 中翻译或明确记录无直接等价项
5. AOSP `SystemUI-res`、`SystemUI-core` 和 `SystemUI` app 的 manifest/资源传播关系曾被误读；2026-08-06 根据 bp 和 Soong 源码重新说明
6. 模块命名/边界和源码、jar、AAR 的判定标准必须由 bp 和来源规则共同决定

## 决策

### 决策 1：源码 owner 和依赖语义对齐 BP，Gradle module 不与 target 1:1

- `Android.bp` 是生产 source roots、资源 owner、static/libs/plugins 语义的唯一依据。
- Soong target 是编译图节点；多个内部 target 可合入一个 Gradle module。
- 独立 Gradle module 只由 R namespace、多消费者、外部 API、处理器/AIDL 工具链或防止依赖环证明。
- 目标模块图以 `docs/architecture/2026-08-06-module-structure-audit.md` 的 13-module 清单为准：
  `:app`、`:SystemUI-core`、`:SystemUI-res`、`:SystemUI-common`、`:SystemUI-animation`、
  `:SystemUI-plugin-core`、`:SystemUI-plugin-processor`、`:SystemUI-plugin`、`:SystemUI-unfold`、
  `:SystemUI-customization`、`:SystemUI-shared`、`:SystemUI-shared-biometrics`、`:SystemUI-compose`。

**不再要求每个 Soong `android_library` 对应一个 Gradle module**。具体合并：

- `SystemUILogLib` + `SystemUICommon` + `SystemUI-shared-utils` → `:SystemUI-common`
- `PlatformAnimationLib` + `SystemUIShaderLib`（surfaceeffects）→ `:SystemUI-animation`
- `SystemUISharedLib` + shared/keyguard child → `:SystemUI-shared`（biometrics 因独立 R namespace 和 Settings 消费者保留为 `:SystemUI-shared-biometrics`）
- Compose Core + Scene → `:SystemUI-compose`
- 全部 pods 生产源码 → `:SystemUI-core`
- `PluginCoreLib` + `PluginAnnotationLib` runtime API → `:SystemUI-plugin-core`；
  `PluginAnnotationProcessor` 独立为 `:SystemUI-plugin-processor`（build-time 工具，不进 APK implementation）
- `SystemUI-res` 独立持有 `res`/`res-keyguard`/`res-product`，生成 `com.android.systemui.res.R`

参考项目 `CarSystemUIGradle` 仅 7 个 module 即产出完整车载 SystemUI APK，证明无需 BP 1:1。

### 决策 2：依赖关系严格按 bp 的 static_libs / libs 顺序

`:app` 只依赖 `:SystemUI-core`，不再写 `:SystemUI-shared/-animation/...` 这些 —— 全部由 `:SystemUI-core` 的 `static_libs` 串起来。

`:SystemUI-core` 的依赖按 AOSP bp 顺序：

```
tier① 源码子模块（按 bp static_libs 语义，合并为 13-module 图后 core 直接依赖）：
  :SystemUI-res, :SystemUI-animation, :SystemUI-common,
  :SystemUI-customization, :SystemUI-plugin, :SystemUI-shared,
  :SystemUI-compose
  （plugin-core/unfold/biometrics/keyguard 经 shared/customization/plugin 传递，不由 core 直接依赖）
tier② AOSP 特有 jar/AAR：
  framework.jar, framework-statsd.jar,
  android.car.jar, WindowManager-Shell, WifiTrackerLib,
  SettingsLib、iconloader（含资源时先直接 AAR，确认冲突后才用本地 Maven AAR），
  systemui-flags, settingslib-flags, notification-flags,
  SystemUI-{proto,statsd,tags}（生成物 jar）
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

### 决策 3：manifest 与 app 打包文件按 bp 职责映射到 Gradle

AOSP 的文件归属必须按对应 module 理解，而不是看到文件名后全部归入 `android_app`：

| AOSP 文件/属性 | AOSP 归属 | Gradle 映射 | 状态 |
|------|------|------|------|
| `AndroidManifest.xml` | `SystemUI-core` 显式使用；`SystemUI` app 在同一 package 中完成最终应用链接 | `:app/src/main/AndroidManifest.xml` 保留完整最终 manifest；`:SystemUI-core/AndroidManifest.xml` 保留 permission/protected-broadcast 部分，避免 AGP 重复合并 application 组件 | ✅ Gradle 适配 |
| `AndroidManifest-res.xml` | **`SystemUI-res`** 的 manifest，不是 `android_app` 的专属输入 | 当前副本位于 `:app/src/main/` 但未被 app Gradle 配置消费；后续建立独立 `:SystemUI-res` module 时归位 | ⚠️ 待校准 |
| `proguard.flags` / `proguard_common.flags` / `proguard_kotlin.flags` | `SystemUI` app 优化配置 | `:app/` 对应文件 | ✅ 已复制 |
| `privapp_whitelist_com.android.systemui` | `required` 的系统镜像权限白名单 | 不属于普通 APK 编译输入；由目标系统镜像/设备配置提供 | 不复制 |

> Gradle 与 Soong 的 manifest 传播机制不同，不能机械要求 app/core 两个 Gradle module 都持有同一份完整 application 组件声明。最终标准是 APK merged manifest 与 AOSP 语义一致，同时保留入口类在 core。
>
> **入口类更正（2026-07-31）**：原决策 3 将 `SystemUIApplication.java` / `SystemUIService.java`
> 列为 "android_app 入口，需迁到 `:app`"——这是对 bp 的误读。实际 AOSP bp 中：
> - `SystemUI-core` (Android.bp:425) `srcs: ["src/**/*.java", ...]` **包含**这两个入口类
>   （它们位于 `src/com/android/systemui/`）
> - `android_app "SystemUI"` (Android.bp:958) **无独立 `srcs`**，仅 `static_libs: ["SystemUI-core"]`
>
> 故按规则 B（bp 对齐），入口类**本来就属于 `:SystemUI-core`**，不应迁到 `:app`。
> `:app` 无源码（与 bp 的 android_app 无 srcs 一致）。

### 决策 4：入口类保留在 `:SystemUI-core`（方案 A，2026-07-31 更正）

- `SystemUIApplication.java` / `SystemUIService.java` **保留在** `:SystemUI-core/src/com/android/systemui/`
  （匹配 bp `src/**/*.java` glob）
- `:app/src/main/java/` **无源码**（匹配 bp android_app 无 srcs），仅 `static_libs: ["SystemUI-core"]`
- 曾在 `:app/src/main/java/` 创建的入口类副本已删除（避免与 core 重复）
- core 的 6 个文件（KeyguardService 等）直接 import `SystemUIApplication`/`SystemUIService`，
  入口类留在 core 保证这些引用可解析（library 无法依赖 app）
- R import 更正：AOSP 原版用 `import com.android.systemui.res.R;`，但项目 core 的 namespace 为
  `com.android.systemui`，R 类生成在 `com.android.systemui.R`。入口类 `package com.android.systemui`
  与 R 同包，用 bare `R.` 即可解析（与 core 其他 119 个同包文件一致），无需 import

### 决策 5：资源传播的当前适配与待校准目标

- 当前 `:SystemUI-core/res{,-keyguard,-product}/` 持有 AOSP SystemUI 资源，`:app` 无 res；APK 打包时由 AAPT2 从 core 依赖链收集资源
- AOSP bp 实际由独立 `SystemUI-res` module 持有这些资源，再由 `SystemUI-core` static link；项目尚未建立等价 module，这是待解决的结构缺口
- 在完成该模块校准前，现有资源文件仍必须与 AOSP 1:1，不得为了当前 Gradle 布局修改、去重或补造资源

### 决策 6：build.gradle.kts 配置项按 bp 转换

| AOSP bp 属性 | Gradle 翻译 | `:app/build.gradle.kts` 写法 |
|------|------|------|
| `static_libs: ["SystemUI-core"]` | `implementation(project(":SystemUI-core"))` | project module 仅直接依赖 core；当前额外外部依赖待审计是否应由 core 传递 |
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

### 决策 7：namespace 冲突处理

**问题**：AGP 要求每个 module 有独立 namespace，否则 manifest merger 报错：
```
Manifest merger failed : Attribute application@name value=(com.android.systemui.app.SystemUIApplication)
is also present at [:SystemUI-core] AndroidManifest.xml value=(com.android.systemui.SystemUIApplication)
```

**AOSP 无此问题**——soong 用 `package=` 区分，namespace 是 AGP 强加概念。

**决策**：
- `:app` namespace 为 `com.android.systemui.app`（独立 namespace，区别于 core）
- `:app` 的 `applicationId` 仍为 `com.android.systemui`（AOSP 真实 APK id）
- app/core manifest 删除 `package=` 属性，由 AGP namespace/applicationId 管理
- AOSP `SystemUI-core` **确实显式设置** `manifest: "AndroidManifest.xml"`；旧文档称其“不含 manifest 字段”是错误的
- Gradle 当前让 app 持有完整 manifest，让 core 保留 permission/protected-broadcast 部分而不重复 `<application>` 组件。这是为适配 AGP manifest merger 的明确差异，不是把入口类迁到 app
- reference: `CarSystemUIGradle/app/build.gradle.kts:22` 使用独立 namespace + `applicationId = "com.android.systemui"` 的等价处理

### 决策 8：AGP 8+ `buildToolsVersion` 与 `compileSdkPreview` 用法

- `buildToolsVersion` 已被 AGP 隐式管理，**不再写**——保留会触发 deprecation
- `compileSdkPreview = "SysUISdk"` 是项目约定的字符串（与 rootProject 内的 SDK 标识一致）；不要写成 `compileSdk = rootProject.extra["compileSdkPreview"] as Int`（root extra 没有这个 key，会在 configure 阶段抛 `Cannot get property 'compileSdkPreview' on extra properties extension as it does not exist`）

## 副作用 / 约束

- 入口类保留在 `:SystemUI-core`，无需调整 `sourceSets`（与 bp `src/**/*.java` 一致）
- `:app/src/main/AndroidManifest.xml` 已从 AOSP 完整复制（1158 行，service/receiver/activity 声明齐全）
- `:app/build.gradle.kts` 的 project module 依赖仅 `:SystemUI-core`，但仍有 framework/WMShell compileOnly 和少量上游 implementation；后续按 bp 检查是否应全部由 core 传递
- `proguard.flags` 引用 `proguard_common.flags`（`include`），后者引用 `proguard_kotlin.flags`，路径相对：需按相对 `:app/` 根
- 本 ADR 解决模块边界和打包职责，不以单次编译错误数衡量；结构更接近 AOSP 即属于有效推进
- 是否运行编译按当前问题需要决定；未运行或失败时必须如实记录，不得声称 APK 已成功产出

## 决策状态

- **结构对齐**：入口类归属和 app/core 边界已确定
- **依赖/资源校准**：继续审查 app 直接依赖、`SystemUI-res` 映射和 manifest merge 结果
- **APK 里程碑验证**：依赖校准完成后运行 `:app:assembleDebug`；在命令退出 0 前只说明打包链路已配置，不宣称 APK 构建成功

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
- `docs/architecture/2026-08-06-soong-android-app-vs-gradle-app.md` — Soong APK 生成流程与 Gradle 对应关系