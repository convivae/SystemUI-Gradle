# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

- Task 035 implementation: `wV:p1`, worktree `/home/conv/myspace/SystemUI-Gradle-wt-035`, branch `task-035`, model `joycode/GLM-5.3`. ModelId and CONTRACT verified. User approved the REDLINE resolution: preserve AOSP source and pin official coroutines to the highest compatible stable release, 1.10.2; worker is authorized to resume and finish full acceptance.

## Queue

1. Tasks 019/020/021 merged: small cleanups done (docstring, .sh removed, libs tree synced); Room schema export live (repo-root schemas/, 5 AOSP JSONs byte-exact); Kotlin 2.3 still blocked upstream (AGP 9.5.0-alpha01 still embeds 2.2.10; recheck triggers documented).
2. Manifest duplicate-permission item closed (AOSP-inherent, merger dedupes, no fix allowed by rule C).
3. Task 022 (merged): Room official Gradle plugin migration done; room.internal.* removed; 5 schemas byte-exact; APK builds.
4. Task 023 (merged): experiment concluded — disallowKotlinSourceSets=false is REQUIRED (KSP config error without it); flag stays, documented.
5. Task 024 (merged): heap now 16G; default-config assembleDebug SUCCESS (2m54s), no OOM; historical javac OOM point re-verified clean.
6. Tasks 026+027 (merged): official-Maven audit (49 artifacts) landed — zxing 3.5.4 (latest, full build passed), protobuf-javanano 3.1.0, dynamicanimation 1.1.0; 4 jars retired (3 replaced + SettingsLib-javac orphan); tooling entry retired; test baseline now 147 (zxing packaging test retired with it).
7. Task 028 (merged): AOSP release config deep analysis complete; user approved G1/R1/R2/R3 and diagnostic boundaries. Task 029 merged: core zero-ProGuard + plugin export flags + unobfuscated release baseline SUCCESS (126,642,058 B, V2 signed, 147/147). Task 030 partial merged after user approval: release R8+shrinkResources remain enabled; 140-class closure blocker fully documented. Tasks 031/032 merged after Standards+Spec review: A=135 runtime/program-closure classes, B=5 R8-library/build classes. Task 033 merged after dual-axis PASS: deterministic 56-class clean monet JAR plus msdl/monet/wifi-flags/wm-shell-flags runtime scopes; debug APK succeeds, tests 151/151, fresh R8 missing set is 126 (15 removed, `AssumeTrueForR8` newly surfaced). Task 034 merged after dual-axis PASS: five byte-identical complete aconfig runtime JARs, notification flags migrated out of local Maven, tests 154/154, debug APK succeeds, fresh R8 missing set is 119 (exact seven removals, zero additions, `AssumeTrueForR8` retained). Task 035 dispatched: latest-stable protobuf-javalite 4.35.1 + deterministic clean view_capture/motion_tool JARs; target exact R8 delta 119→108.
8. After debug+release compile milestones: emulator/device validation plan recorded at docs/issues/2026-08-20-device-emulator-validation-plan.md; first audit AVD signature/root/framework compatibility before replacing preinstalled SystemUI.
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

优化 Release 主分支仍被 119 个 R8 missing class 阻塞（Task 034 从 126 精确移除 7，`AssumeTrueForR8` 仍保留并延期到 B3）。Task 035 正在实施 protobuf-javalite + clean view_capture + motion_tool runtime closure；clean JAR 暴露的 coroutines 1.11.0/AOSP source 编译不兼容已获用户批准按最高兼容官方 1.10.2 解决。APK 装机/运行验证未做。

## Last Updated

2026-08-20 — Task 035 REDLINE approved. Removing the polluted FAT view-capture JAR exposed coroutines 1.11.0's new `SharedFlow.collectLatest` overload, which makes unchanged AOSP `OriginalUnseenKeyguardCoordinator.kt` fail in both debug and release compilation. A coroutines-only AOSP 1.9.0 probe and a temporary official 1.10.2 probe proved the boundary; 1.10.2 succeeds and is the immediately preceding stable release. The user chose to preserve AOSP source and authorized only `kotlinxCoroutines` 1.11.0→1.10.2. Task 035 resumes with full debug/APK/R8 acceptance; all waits remain capped at 90 seconds.
