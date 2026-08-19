# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

| Pane | Agent | Task brief | Worktree | Stage | Since |
|------|-------|------------|----------|-------|-------|
| w2:p15 | w026g53 | `tasks/027-official-deps-landing.md` | wt-026 | extended to landing+cleanup (GLM 5.3) | 2026-08-20 |

## Queue

1. Tasks 019/020/021 merged: small cleanups done (docstring, .sh removed, libs tree synced); Room schema export live (repo-root schemas/, 5 AOSP JSONs byte-exact); Kotlin 2.3 still blocked upstream (AGP 9.5.0-alpha01 still embeds 2.2.10; recheck triggers documented).
2. Manifest duplicate-permission item closed (AOSP-inherent, merger dedupes, no fix allowed by rule C).
3. Task 022 (merged): Room official Gradle plugin migration done; room.internal.* removed; 5 schemas byte-exact; APK builds.
4. Task 023 (merged): experiment concluded — disallowKotlinSourceSets=false is REQUIRED (KSP config error without it); flag stays, documented.
5. Task 024 (merged): heap now 16G; default-config assembleDebug SUCCESS (2m54s), no OOM; historical javac OOM point re-verified clean.
6. Task 025 (merged): release fails on dangling consumer-rules.pro (never existed, inherited from reference project); AOSP has NO library-level proguard config — app-level proguard.flags chain already byte-identical; fix = remove dangling refs at core (AOSP-consistent). Task 026 (merged report): 49 artifacts audited, 3 official replacements trial-passed. Task 027 (dispatched to w026): land 3 replacements (zxing try latest first) + jar retirement + thorough cleanup. Task 028 (release fix) dispatches AFTER 027 merges (both touch core build file).
6. Grill item 9 closed (user approved): :SystemUI-plugin keeps NO compose compiler — AOSP bp has none; see docs/issues/2026-08-19-plugin-no-compose-compiler.md. Item 10 approved (16G heap, task 024). Next: 11 (assembleRelease). Device/runtime verification of APK still open.
2. Task 015 (merged): **FIRST APK** — :app:processDebugResources and :app:assembleDebug BUILD SUCCESSFUL; app-debug.apk 158775460 bytes; main-verified SHA-256 d591ec2dbaf51c70dcb5f3f8e0e836da6a4b6212aa07a7ed91fdc5a2ecc21054 (post-015+018 merge, same size; zip timestamps make hashes build-dependent); 148/148 tests; 7 B2 AARs provenance-verified.
3. Task 017 (merged): audit done; user approved all 4 decision items (2026-08-19).

## Done

- 001–014 merged and pushed.
- Task 014: reference-project research done — CarSystemUIGradle uses a monolithic merged SettingsLib AAR via content-rewriting res concatenation + v31 deletion (rule-R non-compliant); Soong has no reusable merged artifact; closure = 33 res targets / 1512 files / 101 duplicate-path groups; latent child-R-class runtime defect found in merged classes.jar; recommended Option C.
- Task 013: `SettingsLibSettingsTheme` res-only AAR is byte-identical to all 174 AOSP resources; switch drawable errors are 0; 137/137 tests pass.
- Task 008: core javac milestone, 0 errors.
- Tasks 010/010b: reproducible SysUISdk S0–S3+S5, strict verify 7/7 PASS.
- Task 011: S4 framework-res overlay implemented and applied; Factor 1 fixed.
- Task 012: AGP `androidprv` namespace loss fixed at build-intermediate layer; architect verified 131/131 tests, helper `419/8/8 unresolved=0`, and `androidprv` 20→0.

## Blocked

无构建阻塞：`:app:processDebugResources` 与 `:app:assembleDebug` 均已 BUILD SUCCESSFUL（2026-08-19，Task 015）。剩余：APK 装机/运行验证未做。

## Last Updated

2026-08-19 — **APK MILESTONE** (task 015). Tasks 017/018 audit+cleanup merged. 019/020/021 merged: cleanups, Room schema export, Kotlin-2.3-blocked confirmation.
