# Stage 4 (部分): 引入 SystemUI AIDL 生成接口 jar (2026-07-28)

> 承接 transitive R（1806→1759）。本次处理 AIDL 接口 unresolved，错误数 **1759 → 1658 (−101)**。

## TL;DR

`IGlanceableHubWidgetManagerService` / `IHomeControlsRemoteProxy` / `IScreenshotProxy` 等
AIDL 接口 unresolved，且其 `.Stub`(extends Binder) 缺失级联导致 `clearCallingIdentity` /
`restoreCallingIdentity` 等 unresolved。从 AOSP 已编译的 SystemUI `classes.jar` 提取这 11 个
接口类（含 `$Stub` / `$Stub$Proxy` / `$Default` / 嵌套回调接口）打包为 `libs/systemui-aidl.jar`
并 `compileOnly` 引入。错误数 −101。

## 根因

源码里有 14 个 `.aidl` 文件（与 .kt 同放在 `src/`），但：
1. **AGP 8+ 默认关闭 aidl 编译**（`buildFeatures.aidl` 默认 false）。
2. **开启 aidl 编译会失败**：`IHomeControlsRemoteProxy.aidl` import `android.os.IRemoteCallback`，
   而我们的 `SysUISdk/framework.aidl` 只含 public API，缺 hidden 接口（IRemoteCallback 是 @hide）。
   提供完整 aidl import 依赖会陷入递归依赖泥潭。

## 方法（对齐 AGENTS §1：从 AOSP 编译产物提取 jar）

不走 aidl 编译，改为直接引入 AOSP 已编译好的接口 `.class`：

```bash
JAR=aosp/out/target/common/obj/APPS/SystemUI_intermediates/classes.jar
# 提取 11 个 I*Service 接口 + 嵌套类 ($Stub/$Stub$Proxy/$Default/内部回调)
unzip -o "$JAR" "<pkg>/I*.class" "<pkg>/I*\$*.class"
jar cf libs/systemui-aidl.jar -C tmp .
```

`build.gradle.kts`：
```kotlin
compileOnly(files("${rootProject.projectDir}/libs/systemui-aidl.jar"))
```

引入的 11 个接口（60 个 .class）：
IAssistHandleService, IGlanceableHubWidgetManagerService, IHomeControlsRemoteProxy,
IOnControlsSettingsChangeListener, INoteTaskBubblesService, IAppClipsScreenshotHelperService,
ICrossProfileService, IOnDoneCallback, IScreenshotProxy, IWalletCardsUpdatedListener,
IWalletContextualLocationsService。

## 无回归

LC_ALL=C 对比 unresolved 符号集 vs 1759：**无新增符号类型**。

## 残留（9 个，honest）

`IGlanceableHubWidgetManagerService` 的嵌套回调接口（IConfigureWidgetCallback /
IGlanceableHubWidgetsListener / IAppWidgetHostListener）出现 **Argument type mismatch**
（源码传 `?` nullable，提取的 .class 方法签名要求 non-null）——平台 nullability 注解差异，
非 unresolved，非本次回归。留作后续（可能需 nullable 化调用点或重新提取带注解的类）。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| transitive R 后 | 1759 |
| 引入 systemui-aidl.jar | **1658** |
