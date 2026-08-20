# Task 034 — R8 Runtime Closure Batch 2: aconfig Runtime JARs

## Goal

Package five complete AOSP aconfig runtime JARs from their owning Soong `javac` outputs, migrate notification flags out of the illegal local-Maven JAR layout, wire all five AOSP `static_libs` artifacts as Gradle program/runtime inputs, and remove exactly seven A-class release R8 missing references.

## Required reading order

1. `AGENTS.md` in full
2. `docs/orchestration/CHARTER.md` in full
3. This brief
4. `docs/superpowers/plans/2026-08-20-r8-runtime-batch2-aconfig.md`
5. `docs/issues/2026-08-20-r8-runtime-batch2-aconfig.md`
6. `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A1/A2/A3/A11, §3.2, §6, §7 Batch 2
7. `docs/issues/2026-08-20-r8-runtime-batch1-scope.md` final R8 delta

Before editing, invoke `superpowers:test-driven-development`, then print the CHARTER `CONTRACT:` block. Before completion, invoke `superpowers:verification-before-completion`.

## User-approved authority

On 2026-08-20 the user approved this bounded design:

- package complete aconfig runtime JARs from five owning Soong `javac` outputs;
- migrate notification flags from local-Maven JAR delivery to direct `libs/notification-flags.jar`;
- map the five real AOSP `static_libs` edges to APK program/runtime closure;
- test exact five-class runtime sets and run fresh debug/R8 acceptance;
- leave `AssumeTrueForR8` in the later B3 classpath solution.

The approved catalog change is alias removal only. No dependency version change is authorized.

## Allowed paths

- `tools/package_aconfig_jars.py`
- `tools/tests/test_package_aconfig_jars.py`
- `libs/systemui-flags.jar`
- `libs/notification-flags.jar` (new)
- `libs/launcher3-flags.jar` (new)
- `libs/settingslib-widget-flags.jar` (new)
- `libs/settingslib-selector-flags.jar` (new)
- `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar` (delete)
- `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.pom` (delete)
- `gradle/libs.versions.toml`
- `build.gradle.kts`
- `SystemUI-core/build.gradle.kts`
- `docs/issues/2026-08-20-r8-runtime-batch2-aconfig.md`

No other tracked file may change. Empty directories are untracked and may disappear naturally.

## Exact owning inputs and outputs

All sources are below `/home/conv/myspace/aosp/out/soong/.intermediates/` and must use `android_common/javac`, never turbine:

1. `frameworks/base/packages/SystemUI/aconfig/com_android_systemui_flags_lib/android_common/javac/com_android_systemui_flags_lib.jar` → `libs/systemui-flags.jar` → `com/android/systemui`
2. `frameworks/base/services/core/java/com/android/server/notification/notification_flags_lib/android_common/javac/notification_flags_lib.jar` → `libs/notification-flags.jar` → `com/android/server/notification`
3. `packages/apps/Launcher3/aconfig/com_android_launcher3_flags_lib/android_common/javac/com_android_launcher3_flags_lib.jar` → `libs/launcher3-flags.jar` → `com/android/launcher3`
4. `frameworks/base/packages/SettingsLib/IllustrationPreference/settingslib_illustrationpreference_flags_lib/android_common/javac/settingslib_illustrationpreference_flags_lib.jar` → `libs/settingslib-widget-flags.jar` → `com/android/settingslib/widget/flags`
5. `frameworks/base/packages/SettingsLib/SelectorWithWidgetPreference/settingslib_selectorwithwidgetpreference_flags_lib/android_common/javac/settingslib_selectorwithwidgetpreference_flags_lib.jar` → `libs/settingslib-selector-flags.jar` → `com/android/settingslib/widget/selectorwithwidgetpreference/flags`

Every accepted JAR must have exactly these five classes under its configured package and no other `.class`: `CustomFeatureFlags`, `FakeFeatureFlagsImpl`, `FeatureFlags`, `FeatureFlagsImpl`, `Flags`. Output must be a byte-identical copy of the validated source.

## Must remain unchanged

- `settings.gradle.kts`: local Maven remains for AAR delivery.
- `AGENTS.md`, `docs/adr/**`, CHARTER, source/AIDL/res, SysUISdk, module graph, dependency versions, AARs.
- Batch 3/4 scopes and all B-class handling.
- No keep/dontwarn/ProGuard, stub, generated resource, suppression, exclusion, disabled check, or install-to-Maven call.
- `AssumeTrueForR8` remains unresolved and present in the post-change missing set.

If AGENTS inventory cleanup or any other path appears necessary, report it as remaining work; do not touch it.

## Acceptance

1. Fresh pre-change R8 baseline is captured with `set -o pipefail`, actual Gradle exit, full log, and exactly 126 unique refs including all seven target refs plus `AssumeTrueForR8`.
2. TDD RED is recorded before packager production edits; focused GREEN follows.
3. Three focused test behaviors are added: Batch-2 config matrix, incomplete runtime-set rejection, extra-class rejection. Existing copy tests use complete synthetic runtime sets. Full suite is 154/154.
4. Five output JARs are byte-identical to the five exact owning inputs and each has exactly the configured five-class runtime set.
5. Old local-Maven notification JAR/POM and catalog alias are gone; root classpath precedence uses direct `libs/notification-flags.jar`; `settings.gradle.kts` is unchanged.
6. All five JARs are direct `implementation` program inputs in `SystemUI-core`; no old alias/path reference remains in tracked build/catalog files.
7. `git diff --check` is clean.
8. `:app:checkDebugDuplicateClasses :app:assembleDebug` succeeds with max workers 4.
9. APK defines the five representative classes listed in the plan.
10. Fresh post-change R8 runs truthfully. Expected intermediate result is 119 refs: exact seven removals, zero additions, `AssumeTrueForR8` retained. Any different delta is REDLINE.
11. Only Allowed Paths differ from base.
12. English commit, no push, terminal-final `HANDOFF:`.

## Wait policy

No architect or worker wait/timeout may exceed 90 seconds. For long Gradle work, poll in short intervals and combine pane output, agent state, and actual foreground/process inspection.

## Authority boundary

The user approved this exact aconfig runtime closure and notification-JAR migration. Any need to change another dependency, add a keep/dontwarn, handle B3, touch AGENTS/source/res/SysUISdk, or expand the artifact set is a new `REDLINE:`.
