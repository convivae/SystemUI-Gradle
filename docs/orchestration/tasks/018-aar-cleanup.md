# Task 018 — AAR/依赖清理（执行 Task 017 审查结论）

## Goal

执行用户已批准的 Task 017 清理决策（2026-08-19）：
1. 删除孤儿 AAR `libs/maven/com/android/systemui/SystemUISharedLib/`；
2. 删除 Maven 侧 flags jar `libs/maven/com/android/systemui/flags/`（Maven 仓只放 AAR；
   顶层 `libs/systemui-flags.jar` 保留不动）；
3. 删除 3 个废弃脚本 `tools/gen_aar_maven.py`、`tools/rebuild_settingslib_aar.py`、
   `tools/clean_aar_maven.py`；
4. 同步 catalog 与文档。

## Non-goals

- 不动任何其他 artifact、POM、源码、资源、依赖版本；
- 不删 `libs/systemui-flags.jar` 顶层 jar；
- 不重构、不"顺手优化"。

## Allowed Paths

- `libs/maven/com/android/systemui/SystemUISharedLib/`（删除）
- `libs/maven/com/android/systemui/flags/`（删除）
- `tools/gen_aar_maven.py`、`tools/rebuild_settingslib_aar.py`、`tools/clean_aar_maven.py`（删除）
- `tools/tests/`（仅当存在引用被删脚本的测试时，删除对应测试文件并说明）
- `gradle/libs.versions.toml`（仅删 `systemui-sharedlib`、`android-systemui-flags` 两行）
- `AGENTS.md`（§3.2 清单与 tools 表的对应条目）、
  `docs/issues/2026-08-19-aar-cleanup.md`、
  `docs/orchestration/tasks/018-aar-cleanup.md`（本文件勾选）

## Forbidden Paths

其它一切（含 `libs/systemui-flags.jar`、`libs/aars/`、其他 maven 坐标、源码、res）。

## Execution Hints

1. 先 worker-contract skill 输出 `CONTRACT:`；
2. 先跑**删除前基线**：`python3 -m unittest discover -s tools/tests -p 'test_*.py'` 与
   `./gradlew :SystemUI-core:compileDebugKotlin :SystemUI-core:compileDebugJavaWithJavac`，
   记录结果（若基线本身有失败，如实记录，删除后对比不得新增失败）；
3. 检查 `tools/tests/` 是否有测试 import 被删脚本；有则删除对应测试文件并在汇报中说明；
4. 执行删除与文档同步；
5. 跑验收命令（见下）；
6. `git diff --check` 干净；英文 commit；**不 push**。

## Acceptance

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（或因删除被测脚本而减少，需说明）
- `./gradlew :SystemUI-core:compileDebugKotlin :SystemUI-core:compileDebugJavaWithJavac`
  结果不劣于删除前基线（目标 0 错误）
- `git grep -n "SystemUISharedLib\|systemui-sharedlib\|android-systemui-flags\|gen_aar_maven\|rebuild_settingslib_aar\|clean_aar_maven" -- ':!docs/' ':!libs/maven/com/android/server'`
  无残留（docs 历史除外）
- issue 文档更新

## Report

完成后汇报：commit、逐条 checklist（真实输出）、issue 更新、新发现、HANDOFF 块。
