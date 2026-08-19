# 2026-08-19 — AAR/依赖清理（Task 018，执行 Task 017 审查结论）

## 背景

Task 017 审查（`docs/architecture/2026-08-19-aar-dependency-audit.md`）结论：
所有 AAR 已走本地 Maven，0 条直接 `files()` AAR 引用；10 个在消费 AAR 全部有引用证据。
删除候选经用户 2026-08-19 逐项批准。

## 用户决策（2026-08-19，明确批准）

1. **批准删除** `libs/maven/com/android/systemui/SystemUISharedLib/`（孤儿 AAR）——
   删除前需构建验证（编译类覆盖不受影响）；
2. **删 Maven 侧 flags jar**：删除 `libs/maven/com/android/systemui/flags/` +
   catalog alias `android-systemui-flags`——**Maven 仓只放 AAR**，
   `libs/systemui-flags.jar` 顶层 jar 保留不变；
3. **批准删除** 3 个废弃脚本：`tools/gen_aar_maven.py`、
   `tools/rebuild_settingslib_aar.py`、`tools/clean_aar_maven.py`；
4. 确认 SettingsTheme AAR 是 switch drawable 正确归属（Task 013/015 已覆盖，无动作）。

## 同步更新

- `gradle/libs.versions.toml`：删 `systemui-sharedlib` 与 `android-systemui-flags` 两行 alias；
- `AGENTS.md` §3.2 libs 清单：移除 SystemUISharedLib "[旧] 遗留，待清理" 行与
  maven flags 目录描述；`tools/` 表格移除 3 个废弃脚本条目；
- 本 issue 记录结果。

## 验收

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（如有引用被删脚本的测试需一并清理并说明）；
- `./gradlew :SystemUI-core:compileDebugKotlin :SystemUI-core:compileDebugJavaWithJavac`
  0 错误（验证 SystemUISharedLib 未独占任何编译所需类）；
- `git grep -n "sharedlib\|android-systemui-flags\|systemui.flags:flags\|gen_aar_maven\|rebuild_settingslib_aar\|clean_aar_maven" -- ':!docs/'`
  无残留引用（docs 历史记录除外）。

## 结果

待填。
