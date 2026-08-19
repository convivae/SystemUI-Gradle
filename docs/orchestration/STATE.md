# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

| Pane | Agent | Task brief | Worktree | Stage | Since |
|------|-------|------------|----------|-------|-------|
| w2:pV | w015g53 | `tasks/015-settingslib-per-target-aars.md` | wt-015 | implementing (GLM 5.3) | 2026-08-19 |

## Queue

1. Task 015 (dispatched): implement B2 — 7 new per-target AARs + SettingsLib POM transitive deps; user approved 2026-08-19.
2. Task 017 (merged): audit done — all 10 consumed AARs have usage evidence; 0 direct files() AAR refs; delete candidates: SystemUISharedLib orphan AAR, duplicate flags maven jar, deprecated tools (gen_aar_maven/rebuild_settingslib_aar/clean_aar_maven). 4 items pending user decision.

## Done

- 001–014 merged and pushed.
- Task 014: reference-project research done — CarSystemUIGradle uses a monolithic merged SettingsLib AAR via content-rewriting res concatenation + v31 deletion (rule-R non-compliant); Soong has no reusable merged artifact; closure = 33 res targets / 1512 files / 101 duplicate-path groups; latent child-R-class runtime defect found in merged classes.jar; recommended Option C.
- Task 013: `SettingsLibSettingsTheme` res-only AAR is byte-identical to all 174 AOSP resources; switch drawable errors are 0; 137/137 tests pass.
- Task 008: core javac milestone, 0 errors.
- Tasks 010/010b: reproducible SysUISdk S0–S3+S5, strict verify 7/7 PASS.
- Task 011: S4 framework-res overlay implemented and applied; Factor 1 fixed.
- Task 012: AGP `androidprv` namespace loss fixed at build-intermediate layer; architect verified 131/131 tests, helper `419/8/8 unresolved=0`, and `androidprv` 20→0.

## Blocked

- `:app:processDebugResources`: blocked by SettingsLib static-lib resource gaps. Task 014 research delivered the architecture options; awaiting user decision between monolithic merge (rejected: rule R) and per-target res-only AARs (recommended Option C).

## Last Updated

2026-08-19 — task 017 audit merged (4 user-decision items pending); task 015 B2 implementation in progress (7 AARs already generated+installed).
