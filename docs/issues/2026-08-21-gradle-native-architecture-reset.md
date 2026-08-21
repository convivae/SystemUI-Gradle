# 2026-08-21 — Gradle-native SystemUI architecture reset

## Status

Written architecture specification explicitly approved by the user on 2026-08-21.
Task 043's read-only current-state audit is complete and passed final fixed-range Standards and
Spec reviews with zero findings. The audit changed no build code or artifacts, ran no Gradle
command, consulted no Git history, and authorized no rollback. Its eight non-`keep` approval
packets remain `NOT APPROVED` pending item-by-item user decisions.

## Background

The project has reached a real debug APK and reduced release R8 missing references from 140
to one. That progress exposed a design problem: several recent closure tasks optimized for
reconstructing Soong target ownership and R8 input parity rather than for a maintainable,
standalone Gradle migration.

The user clarified the intended product:

- the Gradle build does not need byte-identical outputs or configuration identity with Soong;
- success means debug/release APKs build, install, and run without crashes;
- AOSP SystemUI source/resources still retain their strict provenance and alignment rules;
- external AOSP artifacts should use coarse, maintainable upstream-family granularity;
- unused content within a coherent library family is acceptable when AGP can package and
  optimize it safely;
- no rollback may occur until its original purpose, present cost, alternatives, and validation
  are explained and explicitly discussed.

## Verified current facts

- AGP 9.3.1 uses R8 when `isMinifyEnabled = true`; Gradle itself is the task engine, not the
  Android code optimizer.
- Current release uses `proguard-android-optimize.txt`, `app/proguard.flags`,
  `SystemUI-plugin-core/proguard.flags`, and dependency consumer rules.
- Current task is literally `:app:minifyReleaseWithR8`.
- `isShrinkResources = true` enables AGP 9.x optimized resource shrinking integrated with the
  code optimization graph.
- The repository currently has 27 AARs in `libs/maven/`; 20 belong to the SettingsLib family.
- `libs/aars/` currently contains 29 source AARs.
- Debug APK builds; release R8 still stops on one missing build-time annotation reference.
- Task 042's proposed byte-exact whole-file rule import and S3c stage were never implemented.

## Why the previous direction became expensive

The R8 closure program mapped each missing reference to an exact Soong owner, then delivered
narrow class/resource slices while forbidding warning suppression. This produced strong
provenance, removed duplicate classes, and closed real dependencies. It also made the R8
missing-reference graph drive artifact architecture. SettingsLib's family was consequently
represented by many small AARs and local Maven coordinates.

The individual fixes are not presumed wrong. The governing objective was too strict:
Soong target/configuration parity was treated as a product goal instead of a diagnostic aid.

## New direction

The approved direction is **AGP-native functional parity**:

1. Preserve AOSP SystemUI source/AIDL/resource provenance and semantic module ownership.
2. Let AGP provide its normal release R8 and resource-shrinking pipeline.
3. Treat AOSP build metadata and R8 rules as references, translating only behavior required by
   this standalone build.
4. Package non-SystemUI AOSP dependencies at the coarsest viable upstream-family seam.
5. Prefer a little unused but coherent library content over many fragile per-target artifacts.
6. Keep local Maven only where Gradle metadata/resource merging demonstrably requires it.
7. Validate outcomes: build, package, install, launch, no crash, key SystemUI behavior, and
   repeatable upstream refresh.
8. Audit first; explain and discuss every candidate consolidation or rollback before editing.

## Work sequence

1. Write and review the architecture specification.
2. After explicit spec approval, write a read-only current-state audit plan and worker brief.
3. The worker inspects the present repository, AOSP owners, AGP behavior, and reference project;
   it does not begin with Git history and modifies no build code or artifacts.
4. Produce a keep / simplify / consolidate / candidate rollback / needs experiment ledger.
5. Discuss each candidate with the user, including cause, consequences, lost guarantees, and
   acceptance tests.
6. Only explicitly approved items become separate implementation tasks.
7. Re-establish release packaging and device/runtime milestones under the new architecture.

## Error-count evolution

No build was run for this design step. The truthful current release state remains one R8
missing reference. Error/ref counts are diagnostic only and no longer define artifact seams.

## Pending

- Present the eight `NOT APPROVED` packets from report §10 for item-by-item user decisions.
- Convert only explicitly approved packets into separate implementation or targeted-history tasks.
- Keep the truthful release baseline at one remaining R8 missing reference until the user chooses
  the `AssumeTrueForR8` treatment experiment; no audit recommendation is self-authorizing.

## Audit execution record (Task 043, 2026-08-21)

Executed by the dispatched read-only Worker in worktree `SystemUI-Gradle-wt-043` at dispatch checkout
`67fe3284f3b058c40b963c58eff931d83c0e85d7` (ancestry gate `72970b84` ancestor: pass; clean worktree).
Full report: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`.

- Inventory baseline verified: 29 `libs/aars/*.aar`, 27 `libs/maven/**/*.aar`, 28 root `libs/*.jar`,
  1 `libs/prebuilts/**/*.jar`; 13 modules; 5 project rule files.
- Decision-ledger totals (34 data rows, machine-parsed by a Task 043 revision-time ad-hoc static
  verification command; the plan Task 10 gate was not modified): keep 26 · simplify 0 ·
  consolidate 1 (SettingsLib family delivery) · candidate rollback 4 (WifiTrackerLib / iconloader /
  setupcompat / LowLightDreamLib local-Maven delivery) · needs experiment 2 (animationlib delivery;
  `AssumeTrueForR8` treatment) · needs history/context 1 (`libs/prebuilts/tracinglib-platform.jar`).
- Every non-`keep` item carries a `### … — NOT APPROVED` approval packet in report §10; nothing in this
  audit authorizes implementation. The 13-module topology, all five rule files, the SysUISdk S0–S5 pipeline,
  and the ADR 0001/0005 delivery policy are `keep` on current evidence.
- Top evidence gaps: whether the SettingsLib 17-way res split was forced by a reproduced conflict (needs
  targeted history or the umbrella experiment); direct-AAR vs Maven metadata equivalence for single families;
  `AssumeTrueForR8` runtime reachability under assumption-import treatments; tracinglib-platform.jar origin.
- Build status for this step: `Gradle: NOT RUN (read-only audit boundary)`. No history, implementation,
  rollback, artifact, or SDK mutation occurred; only static gates were run.

## Revision record (Task 043 fixed-range review, 2026-08-21)

The audit report was revised per the architect's fixed-range review; all facts independently re-verified
read-only before fixing. Corrections applied to
`docs/architecture/2026-08-21-gradle-native-current-state-audit.md`:

- §3.2: nine code-bearing Maven AAR class counts restored (LowLightDreamLib 24, SettingsLib 1153,
  SettingsLibSettingsTheme 15, WifiTrackerLib 63, WindowManager-Shell 1888, WindowManager-Shell-shared 152,
  animationlib 13, iconloader 75, setupcompat 126; verified by nested-`classes.jar` `.class` counts).
- All 85 inventory digests replaced with full 64-hex SHA-256 (58 unique digests; Maven AARs byte-identical
  to their `libs/aars/` sources).
- `settings.gradle.kts` include span corrected to lines 25-37; root `build.gradle.kts` injection block end
  corrected to line 48 (flags-ordering block 26-35); SysUISdk stage citations now use actual function
  definition lines (stage_s0=196, s1=273, s2=287, s3=327, s3b=350, s4=456).
- `tracinglib-platform.jar` consumers corrected: `implementation` in `:SystemUI-compose:61`; compileOnly only
  in `:SystemUI-common:38` and `:SystemUI-shared:68`.
- Root-JAR provider/registration status added (§4.5 + §5.1): 13 tool-registered jars vs 15 manually
  maintained; includes new findings that only 8 of 11 aconfig flags jars are registered in
  `package_aconfig_jars.py` (settingslib/settingslib-media/device-state flags unregistered) and
  `PlatformMotionTestingComposeValues.jar` has no producing tool; SettingsLib recipe count corrected to 20.
- No recommendation, ledger totals, or packet dispositions changed; single worker commit amended.

## Second revision record (Task 043, 2026-08-21)

Architect fresh verification found an internal-consistency error after both earlier reviews: report §9 has
exactly 34 data rows with machine-parsed recommendation counts keep=26 / simplify=0 / consolidate=1 /
candidate rollback=4 / needs experiment=2 / needs history/context=1, while the report Totals and this issue
record both claimed higher keep/row figures than the table actually contains. Corrections applied to
`docs/architecture/2026-08-21-gradle-native-current-state-audit.md` and the stale total above:

- §9 Totals line corrected to keep 26 · simplify 0 · consolidate 1 · candidate rollback 4 · needs experiment 2 ·
  needs history/context 1 (34 ledger data rows); the execution-record total above corrected in place.
- A Task 043 revision-time ad-hoc/static verification command machine-parses the §9 table (data rows,
  recommendation column) and asserts row and per-category counts against the Totals line, so a stale total
  cannot pass; the persisted plan Task 10 acceptance gate itself was not modified.
- §4.4/§10 animationlib consumer wiring fixed (TRIVIAL): direct catalog aliases are `:SystemUI-customization:63`,
  `:SystemUI-animation:54`, `:SystemUI-compose:60`; `:SystemUI-core` has no direct animationlib alias and
  consumes it transitively via `implementation(project(":SystemUI-animation"))` at
  `SystemUI-core/build.gradle.kts:122`.
- All recommendations, ledger dispositions, and the 8 NOT APPROVED packets are unchanged; the sole worker
  commit was amended again. Gradle: NOT RUN (read-only audit boundary); Git history consulted: NO.
