# 2026-08-21 — Narrow AGP/R8 adapter for `AssumeTrueForR8` (Task 044)

## Status

Design option **A** explicitly approved by the user on 2026-08-21. **Implemented 2026-08-21
(Task 044, worker worktree)**: fresh Release R8 now exits 0 with zero missing refs, and the first
full shrunk+signed Release APK was produced. Implementation evidence below is from the Task 044
worker worktree (`SystemUI-Gradle-wt-044`, commits `ec98a979` "build: add narrow aconfig R8
adapter" and `4a0a8b08` "docs: record Release R8 closure"; review range base `3cc95a49` → head
`4a0a8b08`); device/runtime validation remains deferred.

**Post-review adjudication (2026-08-21)**: dual-axis review at base `3cc95a49` / head `4a0a8b08`
returned Standards FAIL (MEDIUM: stale implementation hash `051ed6bd` left in this record — the
actual amended implementation commit is `ec98a979`; MEDIUM: acceptance reconciliation wording)
and Spec FAIL (BLOCKER: the Worker substituted AGP-native resource-shrink task evidence for the
brief's impossible literal criterion without raising a REDLINE — see below). After the architect
explicitly disclosed both concerns to the user, the user replied **OK** and authorized continuing.
Accordingly the architect **accepts the AGP-native optimized resource-shrink task evidence
(`:app:optimizeReleaseResources` + `:app:convertShrunkResourcesToBinaryRelease`) as the corrected
semantic acceptance for closure**. This is a **post-review waiver/adjudication, not retroactive
Worker compliance** — the process deviation below stands recorded as-is.

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

All items below were executed in the Task 044 worker worktree on 2026-08-21 (real outputs, no
fabrication; logs preserved under `/tmp/task044-*` in that session):

- **Pre-change R8 baseline**: `./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain
  -Dorg.gradle.workers.max=4` → real exit **1** (2m43s); failure reached R8 missing-reference
  diagnostics (`Missing class com.android.aconfig.annotations.AssumeTrueForR8 (referenced from:
  boolean com.android.wifi.flags.FeatureFlags.androidVWifiApi() and 1 other context)`);
  `missing_rules.txt` parsed to the exact singleton {`com.android.aconfig.annotations.AssumeTrueForR8`}
  (`TASK044_BASELINE_PASS refs=1`).
- **TDD RED**: focused `python3 -m unittest tools.tests.test_gradle_r8_adapter_rules -v` → exit **1**,
  4 failures / 6 tests, each caused by the absent adapter file / absent release wiring.
- **GREEN**: focused suite 6/6 OK; full `python3 -m unittest discover -s tools/tests -p 'test_*.py' -v`
  → **239/239 OK** (233 pre-existing + 6 new).
- **Debug gate**: `:app:checkDebugDuplicateClasses :app:assembleDebug` → exit **0**, `BUILD
  SUCCESSFUL in 2m30s`.
- **Post-change fresh R8**: `:app:minifyReleaseWithR8 --rerun-tasks` → exit **0**, `BUILD
  SUCCESSFUL in 3m28s`; generated missing refs **0** (`TASK044_R8_CLOSURE_PASS refs=0`);
  `configuration.txt` contains exactly one line mentioning the FQN:
  `-dontwarn com.android.aconfig.annotations.AssumeTrueForR8` — no keep/assumevalues/
  assumenosideeffects treatment (`TASK044_EFFECTIVE_RULE_PASS exact_dontwarn=1 assume_rules=0`).
- **Effective-config note**: the first R8 run failed the configuration check because R8 echoes
  adapter-file comments into `configuration.txt`, and the original comments contained the literal
  FQN. Fixed by rewording comments (comment-only change; the single active rule is unchanged) and
  re-running a fresh R8; the check then passed verbatim.
- **Full Release**: `:app:assembleRelease` → first attempt aborted with `Gradle build daemon
  disappeared unexpectedly` (daemon crash under memory pressure, not an R8/packaging failure);
  immediate retry → exit **0**, `BUILD SUCCESSFUL in 3m49s`.
- **Resource shrinking — process deviation recorded**: brief acceptance item 7 required the literal
task name `:app:shrinkReleaseRes` to appear in the release log. That task **does not exist under
AGP 9.3.1** (the toolchain installed for this project), so the literal criterion was **NOT
satisfied** — it was unsatisfiable as written. The Worker should have **stopped with a REDLINE**
before substituting the AGP-native evidence instead of silently reinterpreting the criterion;
this substitution was a process deviation. What was actually verified: the release log shows
`:app:optimizeReleaseResources` and `:app:convertShrunkResourcesToBinaryRelease` (plus
`:app:compileReleaseArtProfile`), i.e. AGP 9.x's optimized resource shrinker ran on the minified
release. Post-review (user-approved), this AGP-native evidence is accepted as the corrected
semantic acceptance for closure — see the adjudication in Status above.
- **Release APK**: `app/build/outputs/apk/release/app-release.apk`, **28,600,808 bytes**, SHA-256
  `ea7425d624143ac775914ff04cd8238105eafea7595d27debf0695cf1b0e920b`; `unzip -t` →
  `No errors detected in compressed data`.
- **Annotation absence**: `apkanalyzer dex packages` output contains no
  `com.android.aconfig.annotations.AssumeTrueForR8` (grep count 0, `TASK044_APK_CLASS_PASS
  packaged=0`).
- **Signature**: `apksigner verify --verbose --print-certs` → exit **0**; `Verified using v2 scheme
  (APK Signature Scheme v2): true`; 1 signer, platform certificate (CN=Android,
  SHA-256 `c8a2e9bc...`). v1/v3/v4 false (V2-only, as configured).
- **Device validation**: **NOT run** — no compatible device/emulator was used in this task;
  install/SystemUI-restart/runtime smoke test remains a separately scheduled gate.
