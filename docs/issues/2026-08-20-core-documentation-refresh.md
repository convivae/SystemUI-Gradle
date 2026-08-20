# 核心文档状态刷新（Task 039）

> 日期：2026-08-20
> 状态：计划完成，等待 Task 038 合并后派发

## 背景

项目核心入口文档仍停留在 2026-08-12/19 的资源链接阶段，包含“APK 尚未生成”、
“SettingsLib switch drawable 阻塞”、131 tests、8 个 AAR 等已失效陈述。实际上项目已经：

- 完成 13-module Gradle 拓扑和可复现 SysUISdk；
- 产出并验证 debug APK；
- Python 工具测试在 Task 038 后为 179/179；
- release R8 missing refs 从 140 逐批收敛到 81；
- 当前下一批是 SettingsLib 74 refs，之后处理 B1–B4 6 refs 与
  `AssumeTrueForR8` 1 ref，再验证 release shrink/sign/device。

陈旧文档会误导新 Agent 重做已完成工作，必须集中刷新。

## 目标

将以下核心文档统一到 Task 038 合并后的同一事实基线：

1. `docs/CURRENT_STATE.md`：当前构建、依赖、R8、验证和 blocker 的权威快照；
2. `docs/HANDOFF.md`：5 分钟上手、强规则、当前任务和正确命令；
3. `docs/PLAN.md`：以当前 release/runtime closure 路线替换失效阶段计划；
4. `docs/README.md`：文档导航、近期关键文档和工具索引；
5. `docs/PITFALLS.md`：只补充/修正近期仍会误导执行者的 SysUISdk、AAR、R8、构建串行经验；
6. `docs/GRADLE_MIGRATION_LOG.md`：在顶部追加 2026-08-19/20 里程碑摘要，保留历史记录。

## 事实源

- `docs/orchestration/STATE.md` 与 `docs/orchestration/log.md`；
- `docs/issues/2026-08-20-release-r8-alignment-decisions.md`；
- `docs/architecture/2026-08-20-r8-runtime-closure-audit.md`；
- Batch 1–4C issue 文档（Tasks 033–038）；
- `docs/issues/2026-08-20-device-emulator-validation-plan.md`；
- `gradle/libs.versions.toml`、`settings.gradle.kts`、实际 `libs/` 文件树；
- Task 038 合并后的主分支 fresh verification 结果。

历史文档只能作为历史背景，不得覆盖以上当前事实源。

## 操作步骤

1. 审计六个目标文档中的陈旧数字、已关闭 blocker、失效命令与失效路径。
2. 先重写 `CURRENT_STATE.md` 和 `PLAN.md`，明确 debug 成功、release R8 未完成。
3. 由同一事实表同步 `HANDOFF.md` 和 `docs/README.md`，避免数字分叉。
4. 对 `PITFALLS.md` 做最小增量更新，不删除有价值的历史失败记录。
5. 在 `GRADLE_MIGRATION_LOG.md` 顶部追加近期里程碑，不重排历史条目。
6. 静态验证 Markdown 链接、关键数字一致性、陈旧短语清零和 `git diff --check`。

## 边界

- 文档 worker 不得修改 `AGENTS.md`、`docs/orchestration/CHARTER.md`、ADR、源码、资源、Gradle 配置或产物。
- `AGENTS.md` / `CHARTER.md` 中的陈旧状态由架构师在 Task 039 review 后做事实性同步。
- 不运行任何 Gradle task；不生成或替换 AAR/JAR/APK。
- 不把 release R8 失败描述成 release 构建成功；`shrinkResources` 尚未真正完成。
- 不把设备安装计划描述成已执行。

## 错误数与状态演变

- 旧文档：APK 未生成；Python tests 131；release 路线未记录。
- Task 037：debug 成功；171 tests；R8 missing refs 88。
- Task 038 目标基线：debug 成功；179 tests；R8 missing refs 81。
- 错误数仅作诊断；文档刷新不运行构建。

## 待解决问题

1. Task 038 必须先通过双轴审查并合并、由架构师 fresh 复验，文档 worker 才能使用 179/81 作为当前事实。
2. `AGENTS.md` 和 `CHARTER.md` 的事实性现状段不在 worker 权限内，需架构师后续同步。
3. SettingsLib 74 refs 的具体落地方案仍需下一任务设计，本文档只记录顺序，不预先宣称方案已定。
