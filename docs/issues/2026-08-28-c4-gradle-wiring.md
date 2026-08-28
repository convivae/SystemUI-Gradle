# Task 072 — C4a：Gradle 接线（新模块注册 + catalog 2.0.0 + 依赖增删 + 新 jar/AAR 打包）

**日期**：2026-08-28
**任务**：docs/orchestration/tasks/072-c4-gradle-wiring.md
**前置**：C2（task071，libs/ 全量 AOSP-17 再生，maven 2.0.0）、C3（task070，源码 17 重对齐）
**范围**：仅接线/打包/配置。验收门 = `./gradlew help` 配置解析通过；编译闭环归 task073。

## 1. 计划

| 步骤 | 内容 |
|------|------|
| P0 | tools 三脚本扩展：surfaceeffects 三 jar（package_misc_jars.py，冻结指纹）、uilatencystats flags jar（package_aconfig_jars.py）、dynamiccolors AAR（package_aosp_aar.py，17 bp SystemUI-res static_libs 漂移修正）；pytest 全绿 |
| P1 | settings 注册三模块；三个新 build.gradle.kts |
| P2 | catalog 23 族 1.x→2.0.0 + jsr330 官方坐标；SystemUI-res 加 floatingmenu-res/wmshell/dynamiccolors；SystemUI-customization 加 clocks-common；SystemUI-core 删两退役 jar、加四个新 jar；SystemUI-plugin 补 :SystemUI-compose（17 bp 漂移） |
| P3 | :app 依赖换 :SystemUI-application；app manifest 最小合并壳；SystemUI-application manifest 剥 package 属性 + CONV_DEL |
| P4 | 验证：gradle help / 对齐工具 --strict / pytest |
| P5 | AGENTS.md §1.9、§3.1 两处预批准编辑；本文档收尾 + STATE.md |

## 2. bp 依据摘录（17 树，逐条）

### SystemUI-application（frameworks/base/packages/SystemUI/Android.bp L599-620）

```
android_library {
    name: "SystemUI-application",
    srcs: ["application/src/**/*.java", "application/src/**/*.kt"],
    defaults: ["SystemUI-srcs-defaults"],      // resource_dirs: [], kotlincflags -Xjvm-default=all
    static_libs: ["SystemUI-core", "com.android.systemui.bundle.phone_dagger", "dagger2"],
    enable_ksp: true,
    annotation_processor_flags: [
        "dagger.fastInit=enabled",
        "dagger.explicitBindingConflictsWithInject=ERROR",
        "dagger.strictMultibindingValidation=enabled",
        "dagger.useBindingGraphFix=ENABLED",
    ],
    manifest: "AndroidManifest.xml",           // = 顶层 1338 行完整 manifest
}
```

android_app "SystemUI"（L1084-1110）：`static_libs: ["SystemUI-application"]`，`resource_dirs: []`，无独立源码。

### SystemUIClocks-CommonLib（customization/clocks/common/Android.bp）

```
static_libs: [PlatformAnimationLib, androidx.compose.runtime_runtime,
              androidx.compose.ui_ui, dagger2, jsr330, kotlinx_coroutines, monet]
libs: ["SystemUIPluginLib"]
plugins: ["dagger2-compiler"]
resource_dirs: ["res"]；kotlincflags: ["-Xjvm-default=all"]；manifest 在模块根
```

SystemUICustomizationLib static_libs 含 `SystemUIClocks-CommonLib`（customization/Android.bp L36）。

### AccessibilityFloatingMenu-res（主 bp L415-427，SystemUI-res static_libs）

```
static_libs: [SystemUISharedLib, SystemUICustomizationLib, SettingsLib,
              WindowManager-Shell, androidx.leanback_leanback, slice-core, slice-view,
              dynamiccolors, AccessibilityFloatingMenu-res]
```

纯 res（accessibility/accessibilitymenu/res），manifest = AndroidManifest-floatingmenu.xml（C3 已按 AGP 惯例改名放模块根）。

### SystemUI-core static_libs 新增（主 bp L460-575 内）

- `SurfaceEffectsComposeLib`（L571）；SystemUI-17 src 大量 import `com.android.systemui.surfaceeffects.{compose,view,core}.*`
- `uilatencystats_flags_core_java_lib`（L572；frameworks/base/AconfigFlags.bp L218 的 java_aconfig_library，运行时包 `com.android.server.ui_latency_stats`）
- `motion_tool_lib` / `settingslib-selector-flags` 不在 17 bp（C2 已退役产物，本任务删 Gradle 依赖行）

### SurfaceEffects 三库（frameworks/libs/systemui/surfaceeffects/*/Android.bp）

bp 无 resource_dirs、源树无 res → 规则 F tier② jar；Kotlin 产物位于
`out/soong/.intermediates/frameworks/libs/systemui/surfaceeffects/{core,compose,view}/<Target>/android_common/kotlin/*.jar`
（三 jar 各自只含 `com.android.systemui.surfaceeffects.*` 自有类，互不相交，已 unzip 验证）。
PlatformAnimationLib bp static_libs 含 SurfaceEffectsViewLib（animation L36）——animation 模块源码零 import
surfaceeffects（已 grep），运行时闭包由 core 的 implementation jar 承担，故不在 :SystemUI-animation 单独接线（记录于此）。

### dynamiccolors（frameworks/libs/systemui/dynamiccolors/Android.bp）

res-only android_library（无 srcs），namespace `com.android.systemui.dynamiccolors`，
提供 `materialColor*` 色板（SystemUI-res 17 的 styles.xml/colors.xml/drawable-night 直接引用，已 grep 确认）。
tier② AAR（Soong R.txt + 原始 res + manifest），单 consumer（:SystemUI-res）→ 直接 AAR（Task 059 例外，libs/aars/）。

### SystemUIPluginLib（plugin/Android.bp L51-63）

static_libs 含 `PlatformComposeSceneTransitionLayout` —— 17 plugin src 新增
`keyguard/ui/composable/elements/*`（import scene），而本项目 :SystemUI-plugin 未依赖 :SystemUI-compose（16 遗留漂移）→ 补 `api(project(":SystemUI-compose"))`。

## 3. 关键设计决策

### 3.1 SystemUI-application 的 namespace = `com.android.systemui`（core 改名 `com.android.systemui.core`）

17 manifest 全部组件名是**相对名**（`.application.impl.SystemUIApplicationImpl`、`.SystemUIService`…）。
ManifestMerger2 对 package-dependent 属性把相对名展开为 `<document namespace>.X`（XmlAttribute.checkAndExpandPlaceHolder，
manifest-merger 32.3.1 源码 XmlAttribute.java L87-113 已核实）。要得到正确的 `com.android.systemui.*` FQCN，
SystemUI-application 的 namespace **必须**等于 AOSP manifest package `com.android.systemui`。

同时 merger 的 unique-namespace 检查（ENFORCE_UNIQUE_PACKAGE_NAMES，AGP 9 默认开启且 10 起强制；
`android.uniquePackageNames`）会在 app 合并闭包内对重复 namespace 直接 ERROR——16 时代 Task 050 已实证
（app 尝试 namespace com.android.systemui 与 core 冲突）。因此：

- `:SystemUI-application` namespace = `com.android.systemui`（承接 AOSP manifest package）
- `:SystemUI-core` namespace 改为 `com.android.systemui.core`（Gradle-only 标签：core 无 res、无 BuildConfig 引用、
  无 R 引用、manifest 无组件相对名——全仓 grep `import com.android.systemui.R` 为 0；17 bp 的 SystemUI-core 本就无
  manifest/package 声明，该 namespace 不承载任何 AOSP 语义）

这样相对名按构造正确展开，无需 16 时代 Task 050 的 79 处 FQCN 手工改写（那是 forbidden path）。

### 3.2 app 最小合并壳

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

- 16 时代 1158 行完整 manifest 的角色由 :SystemUI-application 的 1338 行 AOSP 原版 manifest（library manifest）接管；
  library manifest 的 permissions/application 等全部经合并器并入 app 最终 manifest（16 时代 core manifest 的
  sharedUserId/coreApp 根属性同理合并，实证可行）。
- `sharedUserId`/`coreApp` 保留在 SystemUI-application 的 AOSP 原 manifest 中（不动字节）；壳不重复声明。
- applicationId `com.android.systemui`、namespace `com.android.systemui.app` 维持 Task 050 结论不变。

### 3.3 SystemUI-application manifest 剥 package 属性（CONV_DEL）

AGP 9 CHECK_IF_PACKAGE_IN_MAIN_MANIFEST：library 源 manifest 的 package 属性若 ≠ namespace → RuntimeException；
= namespace → 仅警告。按 brief §3 指示剥除并 CONV_DEL 标记（注释块保全被删字节，可整体撤回；ADR 0004）。
XML 注释不能出现在标签内部（XML 规范），故标记块置于根元素之前的 prolog 区。
clocks-common / floatingmenu-res 的 manifest 保留 package 属性（namespace 与之相等 → 仅警告，零字节改动，
避免越出 brief 授权的唯一例外）。

### 3.4 依赖漂移修正（SystemUI-res）

17 bp SystemUI-res static_libs vs 现 build.gradle.kts：
- 新增 floatingmenu-res 模块依赖（brief 指示）
- 新增 WindowManager-Shell（bp L421，16 遗留缺失）→ `api(libs.systemui.wmshell)`
- 新增 dynamiccolors（bp L425）→ 直接 AAR（§2）
- 保留 settingslib.theme：不在 17 bp 顶层列表，但 17 AOSP 里 SettingsLibSettingsTheme 经
  MainSwitchPreference/ActionButtonsPreference 等 per-target static_libs 传递（SettingsLib/MainSwitchPreference/Android.bp），
  其 `settingslib_switch_{track,thumb}` 等 res 被 SystemUI-res 17 直接引用；本地 POM per-target 骨架无传递边，
  显式 api() 维持 16 时代资源合并（记录于此）。

### 3.5 catalog

23 个本地 maven 族 1.x → 2.0.0（与 libs/maven/ 现存目录逐一核对：全部仅存 2.0.0 版本目录）。
新增 `jsr330`（javax.inject:javax.inject:1，tier③ 官方坐标，AOSP clocks-common bp jsr330 的公网等价物）。
dynamiccolors 走直接 AAR（Task 059 例外），不进 catalog。

## 4. 错误数演变

不适用（本任务不编译；唯一构建验证 = `./gradlew help` 配置解析）。

## 5. 验证记录（P4 实测后回填）

（待回填）

## 6. 移交 task073 清单

（P5 回填：新 flags、core bp 17 static_libs 缺口、view_capture proto keep 规则、编译错误预期面）
