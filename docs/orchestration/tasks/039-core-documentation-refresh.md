# Task 039 — Documentation Information Architecture and Deduplication

## Goal

按用户批准的保守治理方案，将项目文档整理为“`docs/CURRENT_STATE.md` 单一完整实时状态源 + 明确生命周期 + 历史原地冻结”，并移除规则/编排文档中的动态技术快照。

## Required Reading / Startup

1. `AGENTS.md`（全文）
2. `docs/orchestration/CHARTER.md`（全文）
3. 本 brief
4. `docs/issues/2026-08-20-core-documentation-refresh.md`（完整治理 spec）
5. `docs/superpowers/plans/2026-08-20-core-documentation-refresh.md`（Tasks 1–5）
6. `docs/orchestration/STATE.md`
7. `docs/orchestration/log.md` 尾部
8. `docs/CURRENT_STATE.md`、`docs/HANDOFF.md`、`docs/PLAN.md`、`docs/README.md`

启动后先按 worker-contract 输出 `CONTRACT:`，明确 allowed paths、frozen-history 边界、no-Gradle、no-delete、self-commit/no-push。执行使用 `superpowers:executing-plans`。

## Fixed Facts

- Task 038 已合并并在 main fresh 验证；当前 main 包含 commit `2545bdc9`。
- `:app:assembleDebug`: SUCCESS。
- Python tools tests: **179/179**。
- R8 missing refs: **140→126→119→109→106→88→81**。
- Remaining 81: SettingsLib 74 + B1–B4 platform/build classpath 6 + `AssumeTrueForR8` 1。
- Release R8 仍 blocked；`shrinkResources` 未完成；device/emulator runtime validation 未开始。
- Next order: SettingsLib → B1–B4 → `AssumeTrueForR8` → release R8/shrink/sign → device。

若 `git merge-base --is-ancestor 2545bdc9 HEAD`、STATE 或当前 main 与上述事实冲突，输出 `REDLINE: Task 039 baseline mismatch` 并停止，不自行选数字。

## Information Ownership Contract

- `docs/CURRENT_STATE.md`: 唯一完整实时技术状态。
- `docs/HANDOFF.md`: 5 分钟接手，不复制完整状态。
- `docs/PLAN.md`: 仅未完成路线和完成条件。
- `docs/README.md`: 生命周期、owner、维护触发和导航。
- `AGENTS.md`: 强制规则，不保存动态进度。
- `docs/orchestration/CHARTER.md`: 编排协议，不保存动态项目快照。
- `docs/orchestration/STATE.md`: 仅 active workers / queue / orchestration transitions。
- `docs/PITFALLS.md`: 可复用经验，不维护当前错误数。
- `docs/GRADLE_MIGRATION_LOG.md`: append-only；旧历史不改写。
- 已完成 issue/audit/spec/plan/task: frozen historical snapshot，本次不修改。

## Allowed Paths

- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- `docs/HANDOFF.md`
- `docs/PLAN.md`
- `docs/README.md`
- `docs/PITFALLS.md`
- `docs/GRADLE_MIGRATION_LOG.md`
- `docs/issues/2026-08-20-core-documentation-refresh.md`
- `docs/orchestration/CHARTER.md`
- `docs/orchestration/STATE.md`

对 `AGENTS.md`、`CHARTER.md`、`STATE.md` 的授权仅限 plan 明确描述的动态状态去重；不得改变规则含义、红线或 worker contract。

## Forbidden Paths

- `README.md`、`README.en.md`（架构师已同步 179/81，只读验收）
- `docs/orchestration/log.md`（只读；架构师追加）
- `docs/adr/**`
- 除本 Task 039 issue 外的 `docs/issues/**`
- `docs/architecture/**`
- `docs/superpowers/specs/**` 与其他 `docs/superpowers/plans/**`
- `docs/orchestration/tasks/**`（包括本 brief，worker 不改）
- 所有源码、资源、Gradle、工具、library 和 build-output 路径

## Mandatory Boundaries

1. 不移动历史文件，不批量加 lifecycle header。
2. 不删除任何文档；发现候选只写入 Task 039 issue。
3. frozen 历史中的旧数字是合法快照，不为“全仓数字一致”而回写。
4. 当前事实只从 fixed facts / merged STATE-log / Task 038 证据读取。
5. 不把 R8 expected failure 写成 release success。
6. 不运行任何 Gradle task，不生成 AAR/JAR/APK。
7. commits 使用英文；worker 只 commit、不 push。

## Tasks

严格执行 plan Tasks 1–5：

- [ ] 审计陈旧状态并在 issue 固定执行表；
- [ ] 重写 CURRENT_STATE / HANDOFF / PLAN；
- [ ] 重写 docs index，移除 AGENTS/CHARTER 动态快照，收窄 STATE；
- [ ] 校准 PITFALLS，追加 GRADLE_MIGRATION_LOG；
- [ ] 做链接、陈旧状态、职责、无删除、范围和 diff-check 验收并记录证据。

## Acceptance

1. `CURRENT_STATE` 是唯一完整实时技术状态 owner，包含真实 179/81 和未完成项。
2. HANDOFF 是简短接手入口；PLAN 只含未完成路线。
3. docs/README 明确四类生命周期、audit 边界、五项删除准则、索引和维护触发。
4. AGENTS 的规则 P/S/C/F/R/B/H/D/I、依赖策略、SysUISdk 规则、诊断和用户偏好保留；动态 Section 4 被移除并链接 CURRENT_STATE。
5. CHARTER 的串行构建、red-line、contract 和 review/merge 纪律保持；Part 6 改为 owner 声明。
6. STATE 只保留 Task 039 active orchestration、next queue、recent transitions 和 CURRENT_STATE 链接。
7. PITFALLS 不维护当前错误数；migration log 只追加 2026-08-19/20 摘要。
8. frozen historical files 无移动、无修改、无删除。
9. Markdown local-link check、stale-current scan、scope check、`git diff --check` 全部 exit 0。
10. `Gradle: NOT RUN (task boundary)`；最终输出完整 `HANDOFF:`。

## Authority

`self-commit` for allowed paths only. 任何需要改 forbidden path、删除/移动历史文档或改变规则含义的情况必须 HALT 并报告架构师。

## Model and Resources

- Required model: `joycode/GLM-5.3`
- Static documentation task: no Gradle ownership; do not start a build.
