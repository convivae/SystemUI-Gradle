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

## 验证记录（worker 实测，2026-08-20）

所有带管道的 Gradle 命令均 `set -o pipefail`，exit code 由独立 status 文件记录（前台 90s 超时后改用 nohup 后台 launcher + 短轮询，无一次等待超过 90 秒）。

### Task 1 — pre-change R8 基线

- `./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` → `GRADLE_EXIT=1`，
  `BUILD FAILED in 1m 53s`（R8 missing classes，与预期同型）；完整日志 `/tmp/task034-r8-before.log`，
  基线集合存档 `/tmp/task034-missing-before.txt`。
- **126 条 `-dontwarn` 规则 / 126 个唯一 class 引用**，与 Task 033 终态一致。
- 7 个目标 ref（systemui FeatureFlags{,Impl}、server.notification FeatureFlags{,Impl}、
  launcher3 Flags、settingslib widget/selector flags）全部在位；`AssumeTrueForR8` 在位。

### Task 2 — TDD（规格纠正后）

- **RED**：先改 `tools/tests/test_package_aconfig_jars.py` 再跑，
  `Ran 9 tests / FAILED (failures=5, errors=8)`——全部因缺失 Batch-2 config/包元数据/校验行为
  （初始版本含越界的第 4 个测试 `test_rejects_wrong_namespace`，经架构师纠正后删除；
  wrong-namespace 拒绝由 exact-set 的 incomplete+extra 组合覆盖，production 校验保留在
  `validate_runtime_jar` 的 `actual != expected` 比较中）。
- **GREEN ×2**：最小实现后连跑两次，`Ran 8 tests / OK`。
- 新增 3 个 focused behaviors：Batch-2 config matrix（5 组 source/destination/package 精确断言）、
  incomplete runtime-set 拒绝、extra class 拒绝；存量 copy 测试改为完整五类合成集 + package 元数据。

### Task 3 — 五个真实 JAR

`python3 tools/package_aconfig_jars.py <name>` 逐一重产，机械校验全部通过：

| JAR | cmp 源 JAR | 类数 | FeatureFlagsImpl/FakeFeatureFlagsImpl | SHA-256 |
|---|---|---|---|---|
| `libs/systemui-flags.jar` | IDENTICAL | 5 | ✓ | `c0b7d482…f9f6` |
| `libs/notification-flags.jar` | IDENTICAL | 5 | ✓ | `0f3bfc66…a423` |
| `libs/launcher3-flags.jar` | IDENTICAL | 5 | ✓ | `5b0f57ee…6eb` |
| `libs/settingslib-widget-flags.jar` | IDENTICAL | 5 | ✓ | `e08f2587…57e` |
| `libs/settingslib-selector-flags.jar` | IDENTICAL | 5 | ✓ | `7c54c1fb…145` |

五个 SHA-256 与实施前对 AOSP owning javac 源的独立实测完全一致（byte-identical 拷贝，
无任何合并/合成）。

### Task 4 — 迁移与机械断言

- 根 `build.gradle.kts`：`serverNotificationFlagsJar` 指向 `libs/notification-flags.jar`，
  保持在 framework.jar 之前注入的顺序逻辑未动；无其他 classpath 改动。
- `SystemUI-core/build.gradle.kts`：`implementation(libs.android.server.notification.flags)` →
  直引 `libs/notification-flags.jar`；新增 launcher3/widget/selector 三个直引 `implementation`；
  `systemui-flags.jar` 维持既有 implementation。
- `gradle/libs.versions.toml`：仅删除 `android-server-notification-flags` alias 及其分组注释行，
  无版本变更。
- `git rm` 旧 `libs/maven/com/android/server/notification-flags/1.0.0/` JAR+POM；
  `libs/maven` 已无 notification/server 条目；空目录自然消失。
- 机械断言全部 PASS：五 JAR 均为 core `implementation`；tracked build/catalog 文件
  `git grep` 旧 alias/旧路径 0 命中；`settings.gradle.kts` 未改动；Batch 3/4/B-class 缓办项
  （view_capture/motion_tool_lib/TraceurCommon/traceur-res-R/keepanno-annotations，含 shared 模块）
  scope 全部维持 `compileOnly`。

### Task 5 — 闭包与精确推进验证

- `git diff --check`：干净（DIFF_CHECK_OK）。
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`：**Ran 154 tests / OK**
  （151 存量 + 3 新增，符合验收 #3）。
- `./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4` →
  `GRADLE_EXIT=0`，**BUILD SUCCESSFUL in 2m 41s**，无重复类。
- `apkanalyzer dex packages --defined-only` 五个代表类全部 DEFINED：
  `com.android.systemui.FeatureFlagsImpl`、`com.android.server.notification.FeatureFlagsImpl`、
  `com.android.launcher3.Flags`、`com.android.settingslib.widget.flags.Flags`、
  `com.android.settingslib.widget.selectorwithwidgetpreference.flags.Flags`。
- Fresh `:app:minifyReleaseWithR8` → `GRADLE_EXIT=1`（后续 missing classes，预期中间态），
  `BUILD FAILED in 1m 3s`，日志 `/tmp/task034-r8-after.log`，集合存档 `/tmp/task034-missing-after.txt`。
- **精确差分（LC_ALL=C）**：BEFORE=126 → AFTER=119；REMOVED = 恰好 7 个批准目标
  （A1×2 + A2×2 + launcher3 Flags + widget flags + selector flags）；ADDED = 0；
  `AssumeTrueForR8` 保留。与预测 119 完全一致，无 REDLINE。

### 边界检查

`git status --short` 与 Allowed Paths 逐一比对：改动仅为 `tools/package_aconfig_jars.py`、
`tools/tests/test_package_aconfig_jars.py`、`libs/systemui-flags.jar`（M）、4 个新 JAR、
旧本地 Maven JAR/POM（D）、`gradle/libs.versions.toml`、`build.gradle.kts`、
`SystemUI-core/build.gradle.kts`、本 issue 文档。无越界文件。

## 待解决问题

- Batch 3：protobuf-javalite + clean view_capture + motion_tool runtime closure。
- Batch 4：Traceur / SettingsLib / SettingsTheme / WM-Shell / iconloader AAR 闭包。
- A 类完成后处理 B1/B2/B3/B4，其中 B3 包含 `AssumeTrueForR8`。
