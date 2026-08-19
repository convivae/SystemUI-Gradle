# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

| Pane | Agent | Task brief | Worktree | Stage | Since |
|------|-------|------------|----------|-------|-------|
| — | — | — | — | — | — |

## Queue

1. Task 015: implement SettingsLib resource closure. Task 016 recommends B2: 7 new per-target AARs (link-closed reachability set: SelectorWithWidgetPreference, RestrictedLockUtils, ActionButtonsPreference, ProgressBar, TwoTargetPreference, LayoutPreference, AdaptiveIcon) via ADR 0005 POM transitive deps. Awaiting user decision.

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

2026-08-19 — task 016 research merged: minimum conflict-free merge is 12 AARs (12-clique proven) with 39 dormant runtime bombs; reachability-closed B2 needs only 7 new AARs with compile-time fail-fast; R-only AARs unsafe (Q4). Awaiting user granularity decision.
