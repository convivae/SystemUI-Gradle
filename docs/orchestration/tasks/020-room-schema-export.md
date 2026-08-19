# Task 020 — Room schema 导出（对齐 AOSP schemaLocation）

## Goal

补齐 Room schema 导出（用户 2026-08-19 批准）：
1. `SystemUI-core` 的 KSP 配置加 `arg("room.schemaLocation", ...)`，
   导出到**仓库根 `schemas/`**（镜像 AOSP `packages/SystemUI/schemas`）；
2. 从 AOSP 原样复制 5 个历史 schema JSON
   `schemas/com.android.systemui.communal.data.db.CommunalDatabase/{1..5}.json`（byte-exact，规则 R/C）；
3. 构建后 Room 会重新导出 `5.json`——与 AOSP 版做**结构对比**（jq 比 entities/indices），
   格式差异（Room 版本不同导致）如实记录，不强行 byte 对齐 5.json。

## Non-goals

- 不接 `asset_dirs` 语义（AOSP 里 schemas 只进 `SystemUI-tests-base` 测试模块 assets，
  本项目未构建测试模块，记录即可）；
- 不改 Room/DB 版本、不改实体、不加迁移代码；
- 不动其他模块。

## Allowed Paths

- `SystemUI-core/build.gradle.kts`（仅 KSP arg + 必要注释）
- `schemas/`（新目录，5 个 AOSP JSON）
- `docs/issues/2026-08-19-room-schema-export.md`、
  `docs/orchestration/tasks/020-room-schema-export.md`（本文件勾选）

## Forbidden Paths

其它一切（含 AGENTS.md、tools/、libs/、其他 build 文件）。

## Execution Hints

1. 先 worker-contract skill 输出 `CONTRACT:`；
2. 复制 JSON：`cp` 自 `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/schemas/...`，
   逐文件 SHA-256 对照记录；
3. KSP arg 写法参考项目现有 `ksp { arg(...) }`（如 dagger 参数）；路径用
   `rootProject.file("schemas").absolutePath` 或等价；
4. 跑 `./gradlew :SystemUI-core:kspDebugKotlin`，确认导出发生；
5. 验收（见下）后 `git diff --check`；英文 commit；**不 push**。

## Acceptance

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（148 基线）
- `./gradlew :SystemUI-core:kspDebugKotlin` BUILD SUCCESSFUL
- 5 个历史 JSON 与 AOSP byte-exact（SHA-256 对照表入 issue）
- 构建后 `schemas/.../5.json` 存在且与 AOSP `5.json` 结构一致（jq 对比结果入 issue）
- `git status` 中构建重导出的 5.json 若与 AOSP 版有 diff，保留 Room 生成的版本并记录原因
- issue 文档更新

## Report

完成后汇报：commit、逐条 checklist（真实输出）、5.json 对比结论、issue 更新、新发现、HANDOFF 块。
