# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

| Pane | Agent | Task brief | Worktree | Stage | Since |
|------|-------|------------|----------|-------|-------|
| wF:p1 | w012g53 | `tasks/012-preserve-androidprv-namespace.md` | wt-012 | dispatched (GLM 5.3) | 2026-08-19 |

## Queue

1. (empty)

## Done

- 001–011 merged and pushed.
- Task 008: core javac milestone, 0 errors.
- Tasks 010/010b: reproducible SysUISdk S0–S3+S5, strict verify 7/7 PASS.
- Task 011: S4 framework-res overlay implemented and applied; 116 tests; Factor 1 fixed.

## Blocked

- `:app:processDebugResources`: Factor 2 — AGP MergeResources drops `xmlns:androidprv`; task 012 approved to repair at build-logic layer without source/res edits.

## Last Updated

2026-08-19 — initial w012 dispatch aborted before edits (disallowed GPT-5.6 and herdr created a LingerLane worktree); incorrect worktree removed, correct SystemUI worktree recreated manually at `33a2e6ff`, and task redispatched as w012g53 using GLM 5.3.
