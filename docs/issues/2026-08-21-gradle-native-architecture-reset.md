# 2026-08-21 — Gradle-native SystemUI architecture reset

## Status

Written architecture specification explicitly approved by the user on 2026-08-21.
Task 043 read-only audit plan and exact Worker brief are drafted for separate dispatch approval.
No worker has been dispatched, no build code has changed, and no rollback has started.

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

- User review of the exact Task 043 brief:
  `docs/orchestration/tasks/043-gradle-native-current-state-audit.md`.
- After explicit brief approval, dispatch one isolated read-only GLM-5.3 Worker; no Gradle,
  history-first investigation, implementation, or rollback.
- No rollback until the audit is reviewed and each later item is separately discussed and
  approved.
