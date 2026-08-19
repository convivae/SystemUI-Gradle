# Task 022 — Room 迁移到官方 Gradle Plugin（替换 room.internal.* 内部参数）

## Goal

用 Room 官方 Gradle Plugin 替换 Task 020 中的手写内部参数（用户 2026-08-19 批准）：

1. `gradle/libs.versions.toml`：`[plugins]` 新增
   `androidx-room = { id = "androidx.room", version.ref = "androidxRoom" }`
   （复用现有 `androidxRoom = "2.8.4"`，避免版本漂移）；
2. `SystemUI-core/build.gradle.kts`：
   - plugins 块加 `alias(libs.plugins.androidx.room)`；
   - 用公开 DSL `room { schemaDirectory(rootProject.file("schemas").absolutePath) }`；
   - **删除** Task 020 手写的 `ksp { arg("room.schemaLocation", ...); arg("room.internal.schemaInput", ...) }`
     块及其注释（替换为指向本 issue 的简短注释）；
3. **不改 `settings.gradle.kts`**（pluginManagement 已含 google()；plugin marker
   `androidx.room:androidx.room.gradle.plugin:2.8.4` 已确认存在于 Google Maven）。

## Non-goals

- 不动 Room 版本（仍 2.8.4）、不动 DB 实体/迁移代码；
- 不动 schemas/ 下 5 个 JSON 的内容（构建后必须保持 byte-exact）；
- 不动 settings.gradle.kts、其他模块、其他依赖。

## Allowed Paths

- `gradle/libs.versions.toml`（仅 [plugins] 新增 1 行）
- `SystemUI-core/build.gradle.kts`（仅 plugin alias + room 块替换）
- `docs/issues/2026-08-19-room-schema-export.md`（追加迁移记录）
- `docs/orchestration/tasks/022-room-official-plugin.md`（本文件勾选）

## Forbidden Paths

其它一切（含 settings.gradle.kts、schemas/*.json、tools/、libs/、其他模块）。

## Execution Hints

1. 先 worker-contract skill 输出 `CONTRACT:`；
2. 记录迁移前 5 个 JSON 的 SHA-256；
3. 改完后跑验收命令；
4. 若 plugin DSL 名称/签名不符，查阅官方文档或
   `~/.gradle/caches/modules-2/files-2.1/androidx.room/room-gradle-plugin/` 中的实现；
   如官方机制无法满足（如必须改 settings），停下输出 REDLINE；
5. `git diff --check` 干净；英文 commit；**不 push**。

## Acceptance

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（148 基线）
- `./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:kspReleaseKotlin` BUILD SUCCESSFUL
- `./gradlew :app:assembleDebug` BUILD SUCCESSFUL
- 迁移前后 `schemas/**/*.json` SHA-256 全部一致（5 个文件，表格入 issue）
- `git grep -n "room.internal" -- '*.gradle.kts'` 无匹配
- 任务图出现官方 Room schema 相关任务（如 `room` 前缀任务），记录真实输出
- issue 文档更新

## Report

完成后汇报：commit、逐条 checklist（真实输出）、官方插件实际设置的任务/参数、
issue 更新、新发现、HANDOFF 块。
