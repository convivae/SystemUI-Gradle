# 2026-08-21 — Narrow AGP/R8 adapter for `AssumeTrueForR8` (Task 044)

## Status

Design option **A** explicitly approved by the user on 2026-08-21. Implementation has not started.
The exact Worker brief remains subject to separate dispatch approval.

## Background

Task 041 reduced Release R8 missing references from seven to one. Task 043 reclassified the
remaining symbol as a build/optimizer-only annotation descriptor rather than a runtime or platform
API:

```text
com.android.aconfig.annotations.AssumeTrueForR8
```

Current `app/build/outputs/mapping/release/missing_rules.txt` recommends exactly:

```proguard
-dontwarn com.android.aconfig.annotations.AssumeTrueForR8
```

Tasks 042–043 established that this is a CLASS-retained method annotation referenced by generated
aconfig flag JARs, with no APK runtime behavior. The rejected Task 042 proposal would have injected
the class into SysUISdk and imported the complete AOSP assumption-rule file; it remains rejected.

## Approved bounded design

Create one project-owned Gradle adapter, `app/proguard_gradle.flags`, containing comments and
exactly one active rule:

```proguard
-dontwarn com.android.aconfig.annotations.AssumeTrueForR8
```

Wire it only into the minified `release` build type in `app/build.gradle.kts`. Do not modify the
five byte-exact AOSP-owned rule files or wire the adapter into non-minified debug.

Boundaries:

- no wildcard or package-prefix suppression;
- no `keep`, `assumevalues`, or `assumenosideeffects` rule;
- no annotation class, JAR/AAR, Maven coordinate, or SysUISdk mutation;
- no aconfig flag folding; current runtime semantics remain unchanged;
- no source, resource, artifact, dependency, version, or module-boundary change.

## TDD and verification strategy

1. Capture a fresh pre-change R8 baseline: real exit `1`, exact singleton missing set.
2. Add a focused Python test first and observe RED because the adapter file is absent.
3. Add the exact file and release-only wiring; focused and full Python tests must turn GREEN.
4. Keep the debug hard gate green.
5. Require fresh Release R8 and full `assembleRelease` success, zero remaining missing refs,
   effective configuration containing only the exact adapter treatment for this annotation,
   successful resource shrinking, annotation absence from the APK, and V2 signature verification.
6. Device installation/SystemUI restart remains a separately scheduled environment-dependent gate.

## Error-count evolution

| Stage | Expected result |
|---|---|
| Pre-change fresh R8 | 1 missing reference; Gradle exit 1 |
| Post-change fresh R8 | 0 missing references; Gradle exit 0 |
| Full Release | `assembleRelease` exit 0 |

These counts are diagnostic evidence, not a general project rollback threshold.

## Risks and rollback

The rule suppresses only resolution of a CLASS-retained optimizer annotation descriptor. It does
not add runtime code or tell R8 that a flag is true. The main risk is accidental scope broadening;
static tests therefore pin the exact active rule and release-only wiring. If R8 exposes another
missing reference or requires broader treatment, implementation stops at REDLINE.

Rollback is the deletion of `app/proguard_gradle.flags`, its one release wiring entry, and its
focused test. No SDK or artifact restoration is involved.

## Pending implementation evidence

- Pre-change R8 command, real exit, and exact missing set: **not run for Task 044 yet**.
- Focused RED/GREEN test: **not run yet**.
- Full Python tests: **not run yet**.
- Debug build: **not run yet**.
- Fresh Release R8 / full Release / shrink / APK / signing: **not run yet**.
- Device validation: **deferred; no compatible device gate run**.
