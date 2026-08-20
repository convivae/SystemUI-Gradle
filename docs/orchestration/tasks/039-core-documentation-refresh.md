# Task 039 — Refresh Core Project Documentation

## Goal

基于 Task 038 合并后的主分支 fresh 事实，刷新六个核心文档，使访问者和下一个 Agent 获得一致、可执行、不夸大的当前状态。

## Required Reading / Startup

1. `AGENTS.md`（全文）
2. `docs/orchestration/CHARTER.md`（全文）
3. 本 brief
4. `docs/issues/2026-08-20-core-documentation-refresh.md`
5. `docs/superpowers/plans/2026-08-20-core-documentation-refresh.md`
6. `docs/orchestration/STATE.md` 与 `docs/orchestration/log.md` 尾部
7. `docs/architecture/2026-08-20-r8-runtime-closure-audit.md`
8. Tasks 033–038 的 issue 文档

启动后先输出 CHARTER Part 7 规定的 `CONTRACT:`。执行计划时使用 `superpowers:executing-plans`。

## Fixed Facts After Architect Verification

- `:app:assembleDebug`: SUCCESS
- Python tools tests: **179/179**
- R8 missing refs: **140→126→119→109→106→88→81**
- Remaining 81: SettingsLib 74 + platform/build classpath 6 + `AssumeTrueForR8` 1
- Release R8: still blocked (expected non-zero until closure complete)
- `shrinkResources`: not completed
- Device/emulator install/runtime validation: not started
- Next order: SettingsLib → B1–B4 → `AssumeTrueForR8` → release/shrink/sign/device

若 worktree 中的已合并 STATE/log 与这些数字不一致，停止并报告 `REDLINE: baseline mismatch`；不要自行选择数字。

## Allowed Paths

- `docs/CURRENT_STATE.md`
- `docs/HANDOFF.md`
- `docs/PLAN.md`
- `docs/README.md`
- `docs/PITFALLS.md`
- `docs/GRADLE_MIGRATION_LOG.md`
- `docs/issues/2026-08-20-core-documentation-refresh.md`

## Forbidden Paths

- `AGENTS.md`
- `docs/orchestration/CHARTER.md`
- `docs/adr/**`
- `docs/orchestration/STATE.md`
- `docs/orchestration/log.md`
- all source/resource/Gradle/tool/library/build-output paths

发现 `AGENTS.md` 或 `CHARTER.md` 陈旧时只在 HANDOFF 列出 exact file:line；由架构师处理，worker 不得编辑。

## Tasks

严格执行计划 Tasks 1–5：

- [ ] 建立并提交统一事实表；
- [ ] 重写 CURRENT_STATE + PLAN；
- [ ] 重写 HANDOFF + docs/README；
- [ ] 增量更新 PITFALLS + GRADLE_MIGRATION_LOG；
- [ ] 做链接、数字、陈旧短语、范围、diff-check 验收并更新 issue。

## Acceptance

1. 六个核心文档当前状态一致包含 179 tests 与 R8 81；
2. 不再把 APK 描述为未生成，不再把 SettingsLib switch drawable 或 42 javac 当当前 blocker；
3. 明确 debug 成功但 release R8/shrink/device 未完成；
4. 当前路线顺序与 fixed facts 完全一致；
5. Markdown 本地链接检查 exit 0；
6. `git diff --check` exit 0；
7. diff 只包含 allowed paths；
8. 未运行 Gradle，未生成产物；
9. English commits，worker 不 push；
10. 终端输出完整 `HANDOFF:`。

## Authority

`self-commit` for allowed paths only. Any need to touch forbidden/red-line paths must halt and request architect/user approval.
