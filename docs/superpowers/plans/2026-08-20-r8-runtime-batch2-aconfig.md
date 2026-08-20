# R8 Runtime Closure Batch 2 — aconfig Runtime JARs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILLS: use `superpowers:test-driven-development` for the packager changes and `superpowers:verification-before-completion` before committing. Track each checkbox in the issue record. No wait or timeout may exceed 90 seconds.

**Goal:** Replace incomplete aconfig header-like JARs with the five owning Soong `javac` runtime JARs, remove the illegal notification-flags local-Maven JAR delivery, and eliminate exactly seven A-class release R8 missing references.

**Architecture:** AOSP aconfig `java_aconfig_library` runtime outputs contain five generated classes. These modules are resource-free tier-② AOSP artifacts reached through SystemUI/SettingsLib/iconloader/WM-Shell `static_libs`, so Gradle must consume direct JARs as program/runtime `implementation`. The packaging tool copies owning `javac` outputs byte-for-byte but first validates the exact five-class package set. Local Maven remains AAR-only.

**Tech Stack:** Python 3 `zipfile`/`unittest`, Gradle 9.5.0, AGP 9.3.1, builtInKotlin 2.2.10, D8/R8.

**Spec:** `docs/orchestration/tasks/034-r8-runtime-batch2-aconfig.md`; `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A1/A2/A3/A11, §3.2, §7 Batch 2.

## Global constraints

- No stub, source/res/AIDL/SysUISdk/module/version/AAR change.
- No keep, dontwarn, ProGuard, suppression, source exclusion, disabled check, or broad dependency change.
- JARs must not be installed into `libs/maven/`; notification flags must leave local Maven completely.
- `AssumeTrueForR8` is B3 and remains unresolved in this batch.
- Use `-Dorg.gradle.workers.max=4` for heavy Gradle verification.
- Use `set -o pipefail` for every piped Gradle command and save the complete log.
- Commit in English; worker never pushes.

---

### Task 1: Capture the fresh pre-change R8 baseline

**Files:**
- Update: `docs/issues/2026-08-20-r8-runtime-batch2-aconfig.md`

- [ ] Run, before production changes:

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
  2>&1 | tee /tmp/task034-r8-before.log
status=${PIPESTATUS[0]}
cp app/build/outputs/mapping/release/missing_rules.txt /tmp/task034-missing-before.txt
printf 'GRADLE_EXIT=%s\n' "$status"
```

Expected current intermediate result: Gradle exit 1 from R8 missing classes and exactly 126 unique `-dontwarn` class refs. Verify the seven target refs are present and `AssumeTrueForR8` is present. If the baseline differs, document and stop before editing.

---

### Task 2: Extend the aconfig packager test-first

**Files:**
- Modify: `tools/tests/test_package_aconfig_jars.py`
- Modify: `tools/package_aconfig_jars.py`
- Update: `docs/issues/2026-08-20-r8-runtime-batch2-aconfig.md`

**Target config shape:** each `CONFIGS` entry carries `(source, destination, runtime_package)` for all existing and new aconfig artifacts. The runtime package determines this exact class set:

```text
CustomFeatureFlags.class
FakeFeatureFlagsImpl.class
FeatureFlags.class
FeatureFlagsImpl.class
Flags.class
```

- [ ] Add failing tests before production edits:
  1. a Batch-2 config matrix requiring the five exact source/destination/package triples;
  2. incomplete runtime class set rejection;
  3. unexpected extra `.class` rejection.

Update existing synthetic copy tests to construct the complete expected five-class set and pass the package metadata. Run the focused test module and record RED caused by missing config/validation behavior.

- [ ] Implement the minimum GREEN change:
  - add exact owning `android_common/javac` paths for the five artifacts;
  - reject `turbine` paths, missing/non-ZIP inputs, missing expected classes, extra classes, and wrong namespaces;
  - preserve the source JAR bytes exactly after successful validation;
  - keep the CLI artifact selector behavior stable.

- [ ] Run the focused tests twice and record GREEN.

---

### Task 3: Generate and verify the five real JARs

**Files:**
- Modify: `libs/systemui-flags.jar`
- Create: `libs/notification-flags.jar`
- Create: `libs/launcher3-flags.jar`
- Create: `libs/settingslib-widget-flags.jar`
- Create: `libs/settingslib-selector-flags.jar`

- [ ] Run the packager once for each artifact name.
- [ ] For every result, prove:
  - byte-identical to its configured owning Soong `javac` JAR (`cmp`/SHA-256);
  - exactly five classes under the configured package;
  - contains `FeatureFlagsImpl` and `FakeFeatureFlagsImpl`;
  - no class outside the configured package.

Do not merge JARs or synthesize class files.

---

### Task 4: Migrate dependency delivery and runtime scopes

**Files:**
- Modify: `build.gradle.kts`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `gradle/libs.versions.toml` (remove one alias only; no version change)
- Delete: `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`
- Delete: `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.pom`
- Update: `docs/issues/2026-08-20-r8-runtime-batch2-aconfig.md`

- [ ] Change root JavaCompile classpath precedence from the old local-Maven notification path to `libs/notification-flags.jar`. Preserve the requirement that internal flags precede `framework.jar`; avoid unrelated classpath refactoring.
- [ ] Replace `implementation(libs.android.server.notification.flags)` with direct `implementation(files(.../libs/notification-flags.jar))`.
- [ ] Keep `systemui-flags.jar` as implementation and add direct implementation declarations for launcher3, SettingsLib widget, and SettingsLib selector flags.
- [ ] Remove only `android-server-notification-flags` from the catalog.
- [ ] Delete the old notification JAR/POM; remove empty directories if possible. Do not change `settings.gradle.kts`: the local Maven repository remains required for AARs.
- [ ] Mechanical assertions:
  - all five direct JARs are `implementation` program inputs;
  - no tracked build/catalog file references `libs.android.server.notification.flags` or the old local-Maven path;
  - local Maven contains no notification-flags artifact;
  - existing deferred Batch 3/4/B-class scopes are unchanged.

---

### Task 5: Verify debug closure and exact release progression

**Files:**
- Update: `docs/issues/2026-08-20-r8-runtime-batch2-aconfig.md`

- [ ] Static/full unit verification:

```bash
git diff --check
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected test count after the three focused additions: 154 tests, all OK.

- [ ] Debug verification:

```bash
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug \
  -Dorg.gradle.workers.max=4
```

Expected: BUILD SUCCESSFUL.

- [ ] Use `apkanalyzer dex packages --defined-only` to prove definitions for:
  - `com.android.systemui.FeatureFlagsImpl`
  - `com.android.server.notification.FeatureFlagsImpl`
  - `com.android.launcher3.Flags`
  - `com.android.settingslib.widget.flags.Flags`
  - `com.android.settingslib.widget.selectorwithwidgetpreference.flags.Flags`

- [ ] Fresh release R8 measurement:

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
  2>&1 | tee /tmp/task034-r8-after.log
status=${PIPESTATUS[0]}
cp app/build/outputs/mapping/release/missing_rules.txt /tmp/task034-missing-after.txt
printf 'GRADLE_EXIT=%s\n' "$status"
```

Expected intermediate result: exit 1 from later missing classes, 119 unique refs. Diff must show exactly the seven approved A-class removals, zero additions, and `AssumeTrueForR8` retained. Any addition or different failure is REDLINE.

- [ ] Confirm allowed-path boundary and invoke `superpowers:verification-before-completion`.
- [ ] Commit in English, suggested message:

```text
fix: package complete aconfig runtime jars
```

Do not push. End with the required four-part report and terminal-final `HANDOFF:`.
