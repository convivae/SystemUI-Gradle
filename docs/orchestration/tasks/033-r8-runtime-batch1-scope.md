# Task 033 — R8 Runtime Closure Batch 1: Pure Scope Corrections

## Goal

Implement Batch 1 from the approved Task 031 audit: map four clean AOSP `static_libs` JARs to Gradle `implementation`, verify they enter the debug APK, and measure the remaining release R8 missing-class set without applying any bypass.

## Required reading order

1. `AGENTS.md` in full
2. `docs/orchestration/CHARTER.md` in full
3. This brief
4. `docs/superpowers/plans/2026-08-20-r8-runtime-batch1-scope.md`
5. `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A6/A10/A12, §3.2, §6, §7 Batch 1
6. `docs/issues/2026-08-20-release-r8-alignment-decisions.md`

Before editing, print the CHARTER `CONTRACT:` block.

## Allowed paths

- `SystemUI-core/build.gradle.kts`
- `docs/issues/2026-08-20-r8-runtime-batch1-scope.md` (new)

No other tracked file may change.

## Exact implementation

Change only these four existing declarations from `compileOnly(files(...))` to `implementation(files(...))` and correct their adjacent scope comments:

- `libs/msdl.jar`
- `libs/monet.jar`
- `libs/wifi-flags.jar`
- `libs/wm-shell-flags.jar`

These map AOSP `static_libs` program/runtime edges. Do not modify or rebuild the JARs.

## Must remain unchanged

- `view_capture.jar`, `motion_tool_lib.jar`, `TraceurCommon.jar`, `traceur-res-R.jar`, `keepanno-annotations.jar` remain `compileOnly`.
- No JAR/AAR/local Maven/catalog/version/module/SysUISdk change.
- No source/res change.
- No keep/dontwarn/ProGuard change.
- No generated resource, stub, source exclusion, suppression, or disabled check.
- Do not broaden this task when release R8 still fails; record the measured remaining set.

## Acceptance

1. Pre-change issue evidence records target scope counts `compileOnly=4`, `implementation=0`.
2. Post-change mechanical assertion records target `implementation=4`, target `compileOnly=0`, and all five deferred JARs still `compileOnly`.
3. `git diff --check` clean.
4. `python3 -m unittest discover -s tools/tests -p 'test_*.py'` passes 147/147.
5. `./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4` succeeds.
6. `apkanalyzer dex packages --defined-only app/build/outputs/apk/debug/app-debug.apk` proves these representative definitions exist:
   - `com.android.systemui.monet.ColorScheme`
   - `com.google.android.msdl.domain.MSDLPlayer`
   - `com.android.wifi.flags.Flags`
   - `com.android.wm.shell.Flags`
7. `./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` is run and reported truthfully. Expected intermediate result is failure with 125 remaining rules/classes; actual count controls. New unexpected classes/errors require stop-and-report, not opportunistic fixes.
8. Only the two Allowed Paths differ from base.
9. English commit, no push, terminal-final `HANDOFF:`.

## Authority

User approved all structural A-class closure fixes after Task 030. This exact scope-only Batch 1 is authorized and is not a dependency-version or module-boundary red line. Any need to touch a forbidden path, add a keep/dontwarn, modify an artifact, or change another dependency is `REDLINE:` and must stop.
