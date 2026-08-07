# CONV_MOD 首例：UncaughtExceptionPreHandlerManager 反射化

**日期**：2026-08-07
**ADR**：0004（CONV 标记规范）
**规则**：F（framework @hide API 不源码复制，但此处无可用 jar，反射为合理退路）

## 背景

`:SystemUI-shared:compileDebugKotlin` 报 4 个错误，全部在 `UncaughtExceptionPreHandlerManager.kt`：

```text
:31:37 Unresolved reference 'getUncaughtExceptionPreHandler'.
:36:29 Cannot infer type for this parameter. Specify it explicitly.
:36:33 Cannot infer type for this parameter. Specify it explicitly.
:37:20 Unresolved reference 'setUncaughtExceptionPreHandler'.
```

## 根因

`Thread.getUncaughtExceptionPreHandler()` / `Thread.setUncaughtExceptionPreHandler()` 是 Android 平台隐藏 API，定义在 `libcore/ojluni/src/main/java/java/lang/Thread.java:2370/2384`，标注 `@UnsupportedAppUsage`。

- AOSP SystemUI 用 Soong 编译时，`SystemUISharedLib` 的 `min_sdk_version: "current"` 配合完整 core-oj turbine，可直接访问。
- Gradle 编译用标准 SDK / framework.jar，**没有任何可用 jar 含这两个方法**：
  - `SysUISdk/android.jar`：无
  - `libs/framework.jar`：不含 `java.lang.Thread`（framework 层不含 core-lib）
  - `core-oj/classes.jar`：含 `Thread.class` 但 hiddenapi 政策已移除这两个方法
  - `android_module_lib_stubs_current.jar`：无（hiddenapi stub 移除）
- 全 AOSP `out/` 产物扫描，无任何 jar 的 `java.lang.Thread` 含此方法。

## 决策（规则 H → 用户授权）

用户授权方案 A：反射调用 + CONV_MOD 标记。

理由：
1. 参考项目 `CarSystemUIGradle/docs/GRADLE_MIGRATION.md:429-470` 已验证反射方案（改 `GlobalConcurrencyModule.java` 和 `PluginManagerImpl.java`）。
2. `@UnsupportedAppUsage` 本就表示"运行时可用、编译期不暴露"——反射是 Android 官方推荐的此类 API 调用方式。
3. 规则 F 的"补 SysUISdk"前提是"有可用 jar"——此处客观上没有含此方法的 jar，反射是合理退路。
4. 改动小（1 文件 2 处）、可追溯（CONV_MOD 标记）、不引入 stub（不违反规则 P）。

## 改动清单

**文件**：`SystemUI-shared/src/com/android/systemui/shared/system/UncaughtExceptionPreHandlerManager.kt`

| 行 | 原码 | 新码 |
|----|------|------|
| 31 | `val currentHandler = Thread.getUncaughtExceptionPreHandler()` | 反射调用 |
| 37 | `Thread.setUncaughtExceptionPreHandler(globalUncaughtExceptionPreHandler)` | 反射调用 |

## 对账

- [x] 改动后跑对齐：SRC-MODIFIED = 1（仅此文件）
- [x] 跑 `:SystemUI-shared:compileDebugKotlin` 验证 4 个错误消除（BUILD SUCCESSFUL）
- [x] 跑 core 看新 first boundary

## 结果

shared Kotlin 编译通过。新 boundary 推进到 `:SystemUI-shared:compileDebugJavaWithJavac`——`PluginProtector` 类不存在（Blocker B3）。

## B3 解决（同轮）

根因：AOSP `plugin/Android.bp:33` 用 `exclude_srcs` 排除 `PluginProtectorStub.kt`（生产构建有 processor 生成真品）。本项目 javac processor 看不到 .kt 标注，不生成 `PluginProtector`。

解决：恢复 AOSP 自带的 `PluginProtectorStub.kt`（AOSP 官方 fallback，非我们发明的 stub，不违反规则 P）。从对齐工具 exclude 列表移除。

用户澄清（2026-08-07）：规则 P 禁止的是"我们自己新生成的 stub"；AOSP 自带的源码文件（含 stub）属源码复制范畴，可以原样复制恢复。

排查其他 AOSP 自带 stub：`TestStubDrawable.kt`/`AndroidStubs.kt` 在 tests/checks（test-only 不进生产图，不复制是对的）；`StubQSTileViewModel.kt`/`NotificationsControllerStub.kt` 本项目已有（名字含 Stub 但是正常源码）。仅 `PluginProtectorStub.kt` 是被错误删除的 fallback。

## 新 first boundary（B3 解决后）

core Kotlin 编译终于启动！卡在 AAR transform 阶段：

```text
Failed to transform SettingsLib-1.0.0.aar
  Zip file '...SettingsLib-1.0.0-api.jar' already contains entry 'com/android/settingslib/R.class'
Failed to transform iconloader-1.0.0.aar
  ... 'com/android/launcher3/icons/R.class'
Failed to transform WindowManager-Shell-1.0.0.aar
```

这正是 artifact-recovery 计划（Phase B）要解决的 AAR 重复 R.class 问题——`gen_aar_maven.py` 把 R.jar 错误合入 classes.jar 的失败实验遗留。
