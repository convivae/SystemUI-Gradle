# 2026-08-20 — R8 Runtime Closure Batch 2: aconfig Runtime JARs (Task 034)

## 背景

Task 033 已将 release R8 missing-class 集合从 140 推进到 126：精确移除 A6/A10/A12 的
15 类，同时新浮出 B3 家族的 `com.android.aconfig.annotations.AssumeTrueForR8`。
Task 031 的 Batch 2 审计确认仍有 7 个 A 类缺失项来自 5 个不完整或缺失的 aconfig runtime
JAR：

- `com.android.systemui.FeatureFlags` / `FeatureFlagsImpl`；
- `com.android.server.notification.FeatureFlags` / `FeatureFlagsImpl`；
- `com.android.launcher3.Flags`；
- `com.android.settingslib.widget.flags.Flags`；
- `com.android.settingslib.widget.selectorwithwidgetpreference.flags.Flags`。

当前 `libs/systemui-flags.jar` 与本地 Maven 中的 notification flags JAR 都只有
`Flags.class`。JAR 被放进 `libs/maven/` 也违反本项目“本地 Maven 只交付 AAR”的约束。
用户已批准 Task 034：从 owning Soong `javac` 输出重产完整 JAR，将 notification flags 迁移为
直接 `libs/notification-flags.jar`，并把 5 个真实 AOSP `static_libs` 产物纳入 APK
program/runtime closure。

## 依赖判定

五个模块均为 SystemUI 之外的 AOSP aconfig 生成产物，无资源，也不存在等价的官方 Maven
坐标，因此属于 tier② **JAR**：

| Gradle artifact | owning Soong module | 运行时 package |
|---|---|---|
| `systemui-flags.jar` | `com_android_systemui_flags_lib` | `com.android.systemui` |
| `notification-flags.jar` | `notification_flags_lib` | `com.android.server.notification` |
| `launcher3-flags.jar` | `com_android_launcher3_flags_lib` | `com.android.launcher3` |
| `settingslib-widget-flags.jar` | `settingslib_illustrationpreference_flags_lib` | `com.android.settingslib.widget.flags` |
| `settingslib-selector-flags.jar` | `settingslib_selectorwithwidgetpreference_flags_lib` | `com.android.settingslib.widget.selectorwithwidgetpreference.flags` |

每个 owning `javac` JAR 当前实测均恰含标准 5 类：`CustomFeatureFlags`、
`FakeFeatureFlagsImpl`、`FeatureFlags`、`FeatureFlagsImpl`、`Flags`。

## 操作步骤

1. 在任何修改前 fresh 运行 `:app:minifyReleaseWithR8`，保存 126 类基线集合及完整日志。
2. TDD 扩展 `tools/package_aconfig_jars.py`：先写并运行失败测试，再加入 5 个 config；每个
   config 固定 owning Soong `javac` 路径、目标路径和 package，并拒绝缺失、非 ZIP、turbine、
   不完整或额外 `.class` 集合。
3. 重产并提交 5 个 byte-identical JAR。
4. 将 notification flags 从 `libs/maven/com/android/server/notification-flags/` 迁移到
   `libs/notification-flags.jar`；删除旧 JAR/POM 与 catalog alias；根 `build.gradle.kts`
   classpath 优先级改指向新直接 JAR。
5. `SystemUI-core` 以 `implementation(files(...))` 消费五个 runtime JAR；不得把它们合入
   AAR，也不得调用 `install_aar_to_maven.py`。
6. 运行完整测试、duplicate check、debug APK 和代表类 dex 检查，再 fresh 运行 release R8，
   与步骤 1 做精确集合差分。

## 预期错误数演变

- 修改前：**126** unique missing refs（Task 033 实测；Task 034 需 fresh 复验）。
- 本批应移除：上述 **7** 个 A 类 refs。
- 修改后预测：**119**，即 `126 - 7`。
- `AssumeTrueForR8` 必须继续存在并记录为 B3；本批不通过 runtime implementation、keep 或
  dontwarn 处理它。
- 若出现任何新的 missing ref、duplicate class 或非 missing-class R8 错误，worker 必须停止并
  `REDLINE`，不能扩展依赖范围掩盖问题。

## 明确禁止

- 不修改源码、AIDL、res、SysUISdk、模块边界、依赖版本或 AAR。
- 不添加 keep/dontwarn/ProGuard、stub、source exclusion、suppression 或关闭检查。
- 不处理 `AssumeTrueForR8` / `AconfigFlagAccessor`；它们留给 A 类闭包完成后的 B3 方案。
- 不修改 `AGENTS.md` 或历史问题文档；当前依赖清单的机械同步需架构师另行取得 red-line 授权。

## 验证记录

待 worker 填写。所有带管道的 Gradle 命令必须 `set -o pipefail`，并记录真实 Gradle exit code；
所有等待/轮询不超过 90 秒。

## 待解决问题

- Batch 3：protobuf-javalite + clean view_capture + motion_tool runtime closure。
- Batch 4：Traceur / SettingsLib / SettingsTheme / WM-Shell / iconloader AAR 闭包。
- A 类完成后处理 B1/B2/B3/B4，其中 B3 包含 `AssumeTrueForR8`。
