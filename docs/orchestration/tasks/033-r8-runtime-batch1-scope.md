# Task 033 — R8 Runtime Closure Batch 1: Clean Monet + Scope Corrections

## Goal

Replace the polluted turbine-combined `monet.jar` with a deterministic clean JAR built from the two owning Soong `javac` outputs, then map `monet`, `msdl`, `wifi-flags`, and `wm-shell-flags` AOSP `static_libs` to Gradle `implementation`. Verify duplicate-class safety, debug APK contents, and the remaining release R8 missing-class set without bypasses.

## Required reading order

1. `AGENTS.md` in full
2. `docs/orchestration/CHARTER.md` in full
3. This brief
4. `docs/superpowers/plans/2026-08-20-r8-runtime-batch1-scope.md`
5. `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A6/A10/A12, §3.2, §6, §7 Batch 1
6. `docs/issues/2026-08-20-release-r8-alignment-decisions.md`

Before resuming edits, print a revised CHARTER `CONTRACT:` block and invoke `superpowers:test-driven-development` for the new packager.

## User-approved REDLINE resolution

On 2026-08-20 the first attempt proved that the old 83-class turbine-combined `libs/monet.jar` embeds 27 `com.google.errorprone.annotations.**` classes and collides with official Maven `error_prone_annotations:2.50.0`. The user explicitly approved the recommended resolution:

- merge only the current AOSP Soong `javac` outputs for `monet` (9 classes) and `libmonet` (47 classes);
- keep official Maven `error_prone_annotations:2.50.0` as the dependency provider;
- replace `libs/monet.jar` with the resulting 56-class deterministic tier-② JAR;
- then complete all four runtime scope flips.

This is authorization to modify the monet artifact and add its Python packager/test. It does not authorize another artifact/dependency change.

## Allowed paths

- `SystemUI-core/build.gradle.kts`
- `libs/monet.jar`
- `tools/package_monet_jar.py` (new)
- `tools/tests/test_package_monet_jar.py` (new)
- `docs/issues/2026-08-20-r8-runtime-batch1-scope.md` (new)

No other tracked file may change.

## Exact implementation

### Clean monet artifact

Create `tools/package_monet_jar.py` with:

- default AOSP root `/home/conv/myspace/aosp`, overridable by `--aosp-root`;
- output `libs/monet.jar`, overridable by `--output`;
- these exact inputs below the AOSP root:
  - `out/soong/.intermediates/frameworks/libs/systemui/monet/monet/android_common/javac/monet.jar`
  - `out/soong/.intermediates/external/libmonet/libmonet/android_common/javac/libmonet.jar`;
- only `.class` entries under `com/android/systemui/monet/` or `com/google/ux/material/libmonet/`;
- rejection of missing inputs, duplicate class entries, empty inputs, and unexpected class namespaces including `com/google/errorprone/`;
- lexicographically sorted entries, fixed ZIP timestamp/permissions, and byte-identical repeated output.

Write four focused tests first: class-union/namespace filtering, determinism, duplicate rejection, and unexpected-namespace rejection. Generate and commit the real clean `libs/monet.jar`. Its class set must exactly equal the union of the two current javac inputs: 56 classes, zero errorprone classes.

### Runtime scopes

Change only these four existing declarations from `compileOnly(files(...))` to `implementation(files(...))` and correct their adjacent scope comments:

- `libs/msdl.jar`
- `libs/monet.jar`
- `libs/wifi-flags.jar`
- `libs/wm-shell-flags.jar`

These map AOSP `static_libs` program/runtime edges.

## Must remain unchanged

- `view_capture.jar`, `motion_tool_lib.jar`, `TraceurCommon.jar`, `traceur-res-R.jar`, `keepanno-annotations.jar` remain `compileOnly`.
- No other JAR/AAR/local Maven/catalog/version/module/SysUISdk change.
- No source/res change.
- No keep/dontwarn/ProGuard change.
- No generated resource, stub, source exclusion, suppression, disabled check, or Maven errorprone exclusion.
- Do not broaden this task when release R8 still fails; record the measured remaining set.

## Acceptance

1. Issue evidence preserves the original pre-change `compileOnly=4, implementation=0` result and the 27-class duplicate REDLINE/root cause.
2. `tools/tests/test_package_monet_jar.py` contains exactly four focused tests; full suite passes **151/151**.
3. Running `python3 tools/package_monet_jar.py` twice produces byte-identical `libs/monet.jar`.
4. Mechanical artifact comparison proves output class set equals the union of both Soong javac inputs: **56 classes**, **0 missing**, **0 extra**, **0 errorprone**.
5. Post-change scope assertion records target `implementation=4`, target `compileOnly=0`, and all five deferred JARs still `compileOnly`.
6. `git diff --check` clean.
7. `./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4` succeeds.
8. `apkanalyzer dex packages --defined-only app/build/outputs/apk/debug/app-debug.apk` proves these representative definitions exist:
   - `com.android.systemui.monet.ColorScheme`
   - `com.google.ux.material.libmonet.hct.Hct`
   - `com.google.android.msdl.domain.MSDLPlayer`
   - `com.android.wifi.flags.Flags`
   - `com.android.wm.shell.Flags`
9. `./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` is run and reported truthfully. Expected intermediate result remains a failure with 125 remaining rules/classes; actual count controls. New unexpected classes/errors require stop-and-report.
10. Only the five Allowed Paths differ from base.
11. English commit, no push, terminal-final `HANDOFF:`.

## Authority

The user explicitly approved clean-javac monet repackaging after the Task 033 REDLINE. This exact artifact/tool/test expansion and the four scope flips are authorized. Any need to change another dependency/artifact, add keep/dontwarn, or touch a forbidden path is a new `REDLINE:`.
