# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

- Task 037 (WM-Shell proto closure): worker `b80869c9` on branch task-037 in wt-037 (`w15:p1`, GLM-5.3, CONTRACT+model verified). Worker reports done; architect Stage-3 verification PASSED; dispatching dual-axis review.

## Queue

1. Tasks 019/020/021 merged: small cleanups done (docstring, .sh removed, libs tree synced); Room schema export live (repo-root schemas/, 5 AOSP JSONs byte-exact); Kotlin 2.3 still blocked upstream (AGP 9.5.0-alpha01 still embeds 2.2.10; recheck triggers documented).
2. Manifest duplicate-permission item closed (AOSP-inherent, merger dedupes, no fix allowed by rule C).
3. Task 022 (merged): Room official Gradle plugin migration done; room.internal.* removed; 5 schemas byte-exact; APK builds.
4. Task 023 (merged): experiment concluded — disallowKotlinSourceSets=false is REQUIRED (KSP config error without it); flag stays, documented.
5. Task 024 (merged): heap now 16G; default-config assembleDebug SUCCESS (2m54s), no OOM; historical javac OOM point re-verified clean.
6. Tasks 026+027 (merged): official-Maven audit (49 artifacts) landed — zxing 3.5.4 (latest, full build passed), protobuf-javanano 3.1.0, dynamicanimation 1.1.0; 4 jars retired (3 replaced + SettingsLib-javac orphan); tooling entry retired; test baseline now 147 (zxing packaging test retired with it).
7. Task 028 (merged): AOSP release config deep analysis complete; user approved G1/R1/R2/R3 and diagnostic boundaries. Task 029 merged: core zero-ProGuard + plugin export flags + unobfuscated release baseline SUCCESS (126,642,058 B, V2 signed, 147/147). Task 030 partial merged after user approval: release R8+shrinkResources remain enabled; 140-class closure blocker fully documented. Tasks 031/032 merged after Standards+Spec review: A=135 runtime/program-closure classes, B=5 R8-library/build classes. Task 033 merged after dual-axis PASS: deterministic 56-class clean monet JAR plus msdl/monet/wifi-flags/wm-shell-flags runtime scopes; debug APK succeeds, tests 151/151, fresh R8 missing set is 126 (15 removed, `AssumeTrueForR8` newly surfaced). Task 034 merged after dual-axis PASS: five byte-identical complete aconfig runtime JARs, notification flags migrated out of local Maven, tests 154/154, debug APK succeeds, fresh R8 missing set is 119 (exact seven removals, zero additions, `AssumeTrueForR8` retained). Task 035 merged as `bf6ff75f` after Standards+Spec PASS: latest-stable protobuf-javalite 4.35.1 + clean 56/65-class view-capture/motion-tool JARs + coroutines 1.10.2; main fresh tests 160/160, debug succeeds, five representative classes are defined, and R8 truthfully moves 119→109 by removing exactly 11 planned refs and surfacing only deferred B2 `ChunkHandler`. Task 036 merged as `d0bbbda3` after Standards+Spec PASS: iconloader AAR rebuilt as deterministic 75-class javac+kotlin union at local coordinate 1.0.1 (1.0.0 retired); main fresh tests 164/164, debug succeeds, three target classes defined, R8 109→106 exact (3 removed, 0 added, `AssumeTrueForR8` retained). Task 037 merged as `5377bfd9` after Standards+Spec PASS: WM-Shell AAR merged both proto static_libs Soong jars (nano 4 + lite 36 = 40 classes), 1848→1888 exact disjoint union at local coordinate 1.0.1 (1.0.0 retired); main fresh tests 171/171, debug succeeds, 18 targets defined, R8 106→88 exact (18 wm.shell removed, 0 added, `AssumeTrueForR8` retained).
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

优化 Release 主分支当前是 **106 个 R8 missing refs**。Task 036 已完成双轴 PASS、合并和主分支 fresh 复验：iconloader AAR 补齐 Kotlin 闭包（59+16=75 精确并集），坐标升至 1.0.1，R8 精确 109→106（移除 3、新增 0）。后续继续 A 类 Batch 4 剩余闭包（Traceur 7、WM-Shell proto 18、SettingsLib 74），再处理 B1–B4 library/classpath closure；APK 装机/运行验证未做。

## Last Updated

2026-08-20 — Task 037 dispatched and worker-reported done (architect Stage-3 verified): WM-Shell AAR merged both proto static_libs Soong jars (nano 4 + lite 36), 1848→1888 exact disjoint union (2 pre-existing com/android/internal/protolog classes unchanged), local-Maven WindowManager-Shell 1.0.0→1.0.1 (user-approved; 1.0.0 retired, byte-identical AAR, skeleton POM), catalog one-line; 171/171 tests, assembleDebug exit 0 (2m33s, hard gate), 18 targets defined, R8 106→88 exact (18 wm.shell removed, 0 added, AssumeTrueForR8 retained). Awaiting dual-axis review + merge. All waits remain capped at 90 seconds.
