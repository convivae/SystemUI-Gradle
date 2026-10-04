# Task 023 — 实验：移除 `android.disallowKotlinSourceSets=false`

## Goal

评估能否移除 `gradle.properties` 中的实验性开关 `android.disallowKotlinSourceSets=false`
（builtInKotlin 迁移时为让 KSP 操作 kotlin.sourceSets 而加；现 AGP 每次构建都打印
experimental 警告）。用户 2026-08-19 授权做移除实验。

## 实验协议

1. 先跑**基线**：`./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin`
   应 BUILD SUCCESSFUL，记录输出；
2. 删除 `gradle.properties` 中的 `android.disallowKotlinSourceSets=false` 行
   （连同其上方注释行一并删除）；
3. 跑**全量验证**：
   - `./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:kspReleaseKotlin --rerun-tasks`
   - `./gradlew :SystemUI-core:compileDebugKotlin :SystemUI-core:compileDebugJavaWithJavac`
   - `./gradlew :app:assembleDebug`
   - `python3 -m unittest discover -s tools/tests -p 'test_*.py'`
4. 判定：
   - **全部成功** → 保留删除，commit；issue 记录"该开关在当前 AGP 9.3.1 + KSP 2.2.10-2.0.2
     下已非必需"；
   - **任一失败且明确与该开关相关**（如 KSP 无法注册生成源码目录、kotlinSourceSets 报错）→
     `git checkout -- gradle.properties` 恢复，issue 记录失败证据与"仍需保留"的结论，
     commit 仅含文档（实验记录）。

## Non-goals

- 不升级/降级任何依赖；
- 不改 KSP/Dagger 配置、sourceSets；
- 不动其他 gradle.properties 条目。

## Allowed Paths

- `gradle.properties`（仅删 1 行 + 其注释行，或实验失败时不改）
- `docs/issues/2026-08-19-disallow-kotlin-sourcesets-experiment.md`（新建）
- `docs/orchestration/tasks/023-disallow-kotlin-sourcesets.md`（本文件勾选）

## Forbidden Paths

其它一切。

## Acceptance

- 无论实验结果如何：148 个工具测试 OK + issue 记录基线与实验输出（真实粘贴）
- 成功路径：APK 构建成功且 experimental 警告消失（grep 构建输出确认）
- 失败路径：gradle.properties 恢复原状，issue 含失败任务名与首条错误

## Report

完成后汇报：commit、结论（可移除/需保留）、关键输出、issue 更新、HANDOFF 块。

## Outcome (2026-08-20)

- [x] 实验完成。结论：**开关不可移除**（AGP 9.3.1 + KSP 2.2.10-2.0.2 + Gradle 9.5.0 下仍为必需）。
- [x] 基线 `:SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin` → BUILD SUCCESSFUL in 3m 34s；experimental 警告确认存在（`> Configure project :app` 阶段）。
- [x] 移除后 `:SystemUI-core:kspDebugKotlin :SystemUI-core:kspReleaseKotlin --rerun-tasks` → BUILD FAILED in 1s（配置阶段）；首条错误：`Using kotlin.sourceSets DSL to add Kotlin sources is not allowed with built-in Kotlin.`，AGP 自身给出的 solution 即重新设置 `android.disallowKotlinSourceSets=false`。
- [x] `git checkout -- gradle.properties` 恢复，`git diff` 为空（与基线字节一致）。
- [x] `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 148 tests in 34.116s / OK`（exit 0）。
- [x] 详细记录：`docs/issues/2026-08-19-disallow-kotlin-sourcesets-experiment.md`。
- 失败路径：仅文档 commit（gradle.properties 已恢复，无代码改动）。
