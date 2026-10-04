# Javac Root-Cause Fixes Implementation Plan

> **For the architect:** Execute via the herdr orchestration workflow (orchestrator skill). Each fix task below is dispatched as a worker brief copied into `docs/orchestration/tasks/NNN-<slug>.md`. Steps use checkbox (`- [x]`) syntax.

**Goal:** Fix the remaining seven javac root-cause groups from Task 7 (`docs/issues/2026-08-12-current-progress-standards-review.md`) so that `:app:assembleDebug` can proceed past `:SystemUI-core:compileDebugJavaWithJavac`, using only real AOSP artifacts or official Maven coordinates.

**Architecture:** Extend the existing deterministic packaging tools (`tools/package_aconfig_jars.py`, `tools/package_aosp_aar.py`) for new AOSP artifacts; mirror the proven `:SystemUI-unfold` KSP wiring for `:SystemUI-shared`; pin `androidx.media` to the highest public version; research the `NeverCompile` classpath gap before deciding (user directive 2026-08-13).

**Tech Stack:** Python 3 unittest, AOSP Soong javac intermediates, Gradle 9.5.0 / AGP 9.3.1 builtInKotlin, KSP 2.2.10-2.0.2, Dagger 2.59.2, herdr 0.8.0 orchestration.

## Global Constraints

- Orchestration protocol per `docs/orchestration/CHARTER.md` and the orchestrator skill: brief → dispatch → CONTRACT check → monitor → architect re-runs acceptance → architect merges/pushes. **Workers commit but never push.**
- User decisions on 2026-08-13 (pre-approvals, record in each affected brief):
  - setupcompat: jar preferred for code-only, but it **has resources** (`resource_dirs: ["main/res"]`) → **AAR** (rule ② with-resources path, ADR 0001).
  - `androidx.media`: **highest usable public version = 1.8.0** (stable; verified in `maven-metadata.xml`).
  - `NeverCompile`: **research first** — produce background analysis before any fix; the fix itself is out of scope for this plan.
- No stubs, no `res/` edits outside packaging real AOSP resources, no `@Suppress`, no disabling build checks, no source exclusions (rules P/R/I).
- `tools/` scripts stay Python with deterministic output and unittest coverage (ADR 0002 + existing tool conventions).
- `gradle/libs.versions.toml` and version-matrix edits are red-line (CHARTER Part 5.4); tasks 004/005 carry the user's pre-approval recorded above.
- Error counts are diagnostics only (rule I): each task records the javac error-count delta as evidence, never as a gate.
- Commit messages in English; every task ends with worker commit + architect review.

## File Map

| File | Responsibility |
|------|----------------|
| `tools/package_aconfig_jars.py` | Package zxing-core, wifi flags, WM-Shell flags JARs from Soong javac outputs |
| `tools/tests/test_package_aconfig_jars.py` | Tests for the three new JAR configs |
| `tools/package_aosp_aar.py` | New setupcompat AAR config (code jar + main/res + manifest) |
| `tools/tests/test_package_aosp_aar.py` | Test for the setupcompat config |
| `libs/zxing-core.jar`, `libs/wifi-flags.jar`, `libs/wm-shell-flags.jar` | New tracked JAR artifacts |
| `libs/aars/setupcompat.aar` + `libs/maven/com.android.systemui/setupcompat/...` | New AAR artifact and Maven delivery |
| `gradle/libs.versions.toml` | setupcompat catalog alias; `androidx.media` 1.8.0 entry (red-line, pre-approved) |
| `SystemUI-core/build.gradle.kts` | Wire the three JARs, setupcompat alias, and explicit media dependency |
| `SystemUI-shared/build.gradle.kts` | KSP + Dagger wiring mirroring `:SystemUI-unfold` |
| `docs/architecture/2026-08-13-nevercompile-classpath-options.md` | Research deliverable for the NeverCompile gap |

## Dispatch Waves

- **Wave A (parallel, disjoint files):** Task 1 (three JARs: `tools/` + `libs/` + core build), Task 2 (`SystemUI-shared` build only), Task 4 (research doc only).
- **Wave B (serial, after Task 1 — they share `SystemUI-core/build.gradle.kts` and `libs.versions.toml`):** Task 3 (setupcompat AAR), then Task 5 (media 1.8.0).
- **Wave C:** Task 6 (architect verification + docs sync) after all fixes merge.

For each worker task: copy the task's Brief section verbatim into `docs/orchestration/tasks/NNN-<slug>.md`, dispatch per the orchestrator skill, and on review personally re-run the task's Acceptance command before merging.

---

### Task 1: Package zxing-core / wifi-flags / wm-shell-flags JARs (brief 002)

**Files:**
- Modify: `tools/package_aconfig_jars.py` (CONFIGS dict)
- Modify: `tools/tests/test_package_aconfig_jars.py`
- Modify: `SystemUI-core/build.gradle.kts` (dependencies block only)
- Create: `libs/zxing-core.jar`, `libs/wifi-flags.jar`, `libs/wm-shell-flags.jar`

**Interfaces:**
- Produces: three tracked JARs wired into `:SystemUI-core`; later tasks may rely on the classes existing on the core compile classpath.

**Brief for worker (NNN=002):**

Goal: extend `tools/package_aconfig_jars.py` with three new entries and wire the resulting JARs into `:SystemUI-core` so the `com.google.zxing.*`, `com.android.wifi.flags.Flags`, and `com.android.wm.shell.Flags` javac errors disappear.

Authority: self-commit (never push). No red-line areas (build-script dependency wiring only; no version-matrix change).

Allowed Paths: `tools/package_aconfig_jars.py`, `tools/tests/test_package_aconfig_jars.py`, `SystemUI-core/build.gradle.kts`, `libs/zxing-core.jar`, `libs/wifi-flags.jar`, `libs/wm-shell-flags.jar`, `docs/issues/`, `docs/orchestration/tasks/002-*.md`.

Forbidden Paths: everything else; especially `SystemUI-*/src/**`, `SystemUI-*/res*/**`, `gradle/**`, `settings.gradle.kts`, `AGENTS.md`, `docs/adr/**`.

Steps:

- [x] 1. Verify the three AOSP sources exist and are valid zips:

```bash
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/external/zxing/zxing-core/android_common/javac/zxing-core.jar
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/packages/modules/Wifi/flags/wifi_aconfig_flags_lib/android_common/javac/wifi_aconfig_flags_lib.jar
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/libs/WindowManager/Shell/aconfig/com_android_wm_shell_flags_lib/android_common/javac/com_android_wm_shell_flags_lib.jar
```

Expected: three files listed. If any is missing, stop and report (do not substitute another artifact).

- [x] 2. Add three entries to `CONFIGS` in `tools/package_aconfig_jars.py`, following the existing `"systemui-shared-flags"` pattern (source `Path` constants at module top, turbine guard already in `copy_jar`):

```python
"zxing-core": (ZXING_CORE_JAVAC, Path("libs/zxing-core.jar")),
"wifi-flags": (WIFI_FLAGS_JAVAC, Path("libs/wifi-flags.jar")),
"wm-shell-flags": (WM_SHELL_FLAGS_JAVAC, Path("libs/wm-shell-flags.jar")),
```

- [x] 3. Extend `tools/tests/test_package_aconfig_jars.py`: for each new config assert (a) the source path contains `/javac/` and not `turbine`, (b) destination is under `libs/` with the expected name, (c) `copy_jar` produces a byte-identical copy (reuse the existing test helpers/patterns).

- [x] 4. Run the tool tests:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
```

Expected: `OK`, test count > 60 (new tests included).

- [x] 5. Run the packager and verify content:

```bash
python3 tools/package_aconfig_jars.py --all   # use the real CLI flag from --help if different
unzip -l libs/zxing-core.jar | grep -c 'com/google/zxing/'
unzip -l libs/wifi-flags.jar | grep 'com/android/wifi/flags/Flags.class'
unzip -l libs/wm-shell-flags.jar | grep 'com/android/wm/shell/Flags.class'
```

Expected: zxing classes present; both `Flags.class` entries present.

- [x] 6. Wire into `SystemUI-core/build.gradle.kts` dependencies, next to the existing flags-jar lines, with comments matching house style:

```kotlin
// zxing-core: static lib of SettingsLib (packaged into the APK in AOSP)
implementation(files("${rootProject.projectDir}/libs/zxing-core.jar"))
// Wi-Fi aconfig flags (platform-provided on device; compile-time only)
compileOnly(files("${rootProject.projectDir}/libs/wifi-flags.jar"))
// WM-Shell aconfig flags (platform-provided on device; compile-time only)
compileOnly(files("${rootProject.projectDir}/libs/wm-shell-flags.jar"))
```

Rationale to keep in the issue note: zxing is a Soong `static_libs` entry whose classes are dexed into the APK (`implementation`); aconfig flags classes are provided by the system image (`compileOnly`), matching the `settingslib-flags.jar` precedent.

- [x] 7. Acceptance run (from repo root):

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task002.log | grep -cE 'error:'
grep -cE 'com\.google\.zxing|com\.android\.wifi\.flags|com\.android\.wm\.shell\.Flags' /tmp/task002.log || echo '0 (target groups gone)'
```

Expected: build still fails overall (other groups remain — that is fine, rule I), but the second command prints `0` matches for the three target groups. Record both numbers.

- [x] 8. Update `docs/issues/2026-08-12-current-progress-standards-review.md` (append a dated note under the Task 7 section: what was packaged, source paths, scopes chosen, javap/unzip evidence, error-group delta).

- [x] 9. Worker commit (never push):

```bash
git add tools/package_aconfig_jars.py tools/tests/test_package_aconfig_jars.py \
  SystemUI-core/build.gradle.kts libs/zxing-core.jar libs/wifi-flags.jar libs/wm-shell-flags.jar \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "fix(libs): package zxing-core and wifi/wm-shell flags jars from AOSP"
```

Acceptance (architect re-runs): Step 7's two commands; plus `git show --stat HEAD` shows only Allowed Paths.

---

### Task 2: KSP + Dagger for `:SystemUI-shared` (brief 003)

**Files:**
- Modify: `SystemUI-shared/build.gradle.kts`

**Interfaces:**
- Consumes: the proven pattern in `SystemUI-unfold/build.gradle.kts` (`id("com.google.devtools.ksp")`, `ksp(libs.dagger.compiler)`, `implementation(libs.dagger)`).
- Produces: generated Dagger factories for `SystemUnfoldSharedModule` under `SystemUI-shared/build/generated/ksp/`.

**Brief for worker (NNN=003):**

Goal: make `:SystemUI-shared` run Dagger annotation processing via KSP so the three missing `SystemUnfoldSharedModule_*Factory` classes (used by `:SystemUI-unfold` sources compiled into core javac) are generated. Mirrors AOSP `shared/Android.bp` `SystemUISharedLib` `plugins: ["dagger2-compiler"]`.

Authority: self-commit (never push). No red-line areas.

Allowed Paths: `SystemUI-shared/build.gradle.kts`, `docs/issues/`, `docs/orchestration/tasks/003-*.md`.

Forbidden Paths: everything else; especially `SystemUI-shared/src/**`, `SystemUI-*/res*/**`, `gradle/**`, version catalogs, `AGENTS.md`.

Steps:

- [x] 1. Read `SystemUI-unfold/build.gradle.kts` (the proven KSP pattern) and `SystemUI-shared/build.gradle.kts` (current state: has `implementation(libs.dagger)` but no KSP).

- [x] 2. Apply the minimal diff to `SystemUI-shared/build.gradle.kts`: add `id("com.google.devtools.ksp")` to the plugins block and `ksp(libs.dagger.compiler)` to dependencies, mirroring the unfold module's exact style and placement. Do not change versions, do not add other processors.

- [x] 3. Build and check generated factories:

```bash
./gradlew :SystemUI-shared:kspDebugKotlin --console=plain 2>&1 | tail -5
find SystemUI-shared/build/generated/ksp -name 'SystemUnfoldSharedModule*Factory*' | sort
```

Expected: BUILD SUCCESSFUL; the three factories from the Task 7 issue record (`SystemUnfoldSharedModule_Companion_ProvideBgLooperFactory`, `UnfoldBgDispatcherFactory`, `UnfoldBgProgressHandlerFactory`) are generated (exact filenames may live under `java/` or `kotlin/` output dirs — find must list them).

- [x] 4. Acceptance run:

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task003.log >/dev/null; grep -cE 'SystemUnfoldSharedModule_.*Factory|UnfoldBg(Dispatcher|ProgressHandler)Factory' /tmp/task003.log || echo '0 (factory group gone)'
```

Expected: `0` matches for the factory group (overall build may still fail on other groups; record both numbers).

- [x] 5. Append the dated result note to `docs/issues/2026-08-12-current-progress-standards-review.md` (pattern mirrored, generated evidence, error-group delta).

- [x] 6. Worker commit (never push):

```bash
git add SystemUI-shared/build.gradle.kts docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build(shared): run Dagger via KSP in SystemUI-shared"
```

Acceptance (architect re-runs): Step 3 find command + Step 4 grep.

---

### Task 3: setupcompat AAR (brief 004) — Wave B, after Task 1

**Files:**
- Modify: `tools/package_aosp_aar.py` (CONFIGS)
- Modify: `tools/tests/test_package_aosp_aar.py`
- Modify: `gradle/libs.versions.toml` (catalog alias — red-line, user pre-approved 2026-08-13)
- Modify: `SystemUI-core/build.gradle.kts` (dependency line)
- Create: `libs/aars/setupcompat.aar`, `libs/maven/com.android.systemui/setupcompat/1.0.0/`

**Interfaces:**
- Consumes: Task 1 merged (shares `SystemUI-core/build.gradle.kts`).
- Produces: `libs.systemui.setupcompat` catalog alias available to all modules.

**Brief for worker (NNN=004):**

Goal: package `external/setupcompat` as a real AAR (code + resources) and deliver it through the local Maven catalog so `com.google.android.setupcompat.util.WizardManagerHelper` resolves. User decision 2026-08-13: AAR because the module has resources (`resource_dirs: ["main/res"]`); jar-only was waived for this case.

Authority: redline-gated — `gradle/libs.versions.toml` catalog-alias addition is a red-line area (CHARTER Part 5.4) and is **pre-approved by the user on 2026-08-13** for this exact change; any other toml edit remains forbidden. Commit but never push.

Allowed Paths: `tools/package_aosp_aar.py`, `tools/tests/test_package_aosp_aar.py`, `gradle/libs.versions.toml` (alias lines only), `SystemUI-core/build.gradle.kts`, `libs/aars/setupcompat.aar`, `libs/maven/com.android.systemui/setupcompat/**`, `docs/issues/`, `docs/orchestration/tasks/004-*.md`.

Forbidden Paths: everything else; especially `SystemUI-*/src/**`, any `res/` outside the packaging script's output, version numbers in the toml, `AGENTS.md`, `docs/adr/**`.

Steps:

- [x] 1. Discover the AOSP inputs (all must exist; otherwise stop and report):

```bash
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/external/setupcompat/setupcompat/android_common/javac/setupcompat.jar
ls -d /home/conv/myspace/aosp/external/setupcompat/main/res
ls -l /home/conv/myspace/aosp/external/setupcompat/AndroidManifest.xml
find /home/conv/myspace/aosp/out/soong/.intermediates/external/setupcompat -name 'R.txt' | head -3
```

- [x] 2. Add a `"setupcompat"` entry to `CONFIGS` in `tools/package_aosp_aar.py`, following the existing config pattern (code jars list, res dirs, manifest, R.txt; no `exclude_prefixes` needed). Keep output deterministic.

- [x] 3. Add a test in `tools/tests/test_package_aosp_aar.py` mirroring the existing config tests: source paths are the expected Soong/AOSP locations, no turbine paths, output name `setupcompat.aar`.

- [x] 4. Package, install to local Maven, verify:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
python3 tools/package_aosp_aar.py --all
python3 tools/install_aar_to_maven.py
unzip -l libs/aars/setupcompat.aar | grep -E 'classes.jar|AndroidManifest.xml|res/' | head -5
unzip -l libs/maven/com.android.systemui/setupcompat/1.0.0/setupcompat-1.0.0.aar | grep -c 'com/google/android/setupcompat/'
```

Expected: tests OK; AAR contains classes.jar + manifest + res; Maven copy contains setupcompat classes.

- [x] 5. Add the catalog alias in `gradle/libs.versions.toml` following the existing `systemui-*` alias pattern (e.g. `systemui-setupcompat = { group = "com.android.systemui", name = "setupcompat", version = "1.0.0" }`), then wire `implementation(libs.systemui.setupcompat)` into `SystemUI-core/build.gradle.kts` beside the other catalog AARs. No other toml changes.

- [x] 6. Acceptance run:

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task004.log >/dev/null; grep -c 'setupcompat' /tmp/task004.log || echo '0 (setupcompat group gone)'
```

Expected: `0` setupcompat errors (overall failure on remaining groups is fine; record both numbers).

- [x] 7. Append the dated result note to the issue record (user decision quoted, AAR contents, alias, error-group delta).

- [x] 8. Worker commit (never push):

```bash
git add tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py gradle/libs.versions.toml \
  SystemUI-core/build.gradle.kts libs/aars/setupcompat.aar libs/maven/com.android.systemui/setupcompat \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "feat(libs): package setupcompat AAR from AOSP and deliver via local Maven"
```

Acceptance (architect re-runs): Step 4 unzip checks + Step 6 grep; `git show --stat HEAD` limited to Allowed Paths.

---

### Task 4: NeverCompile research (brief 005) — Wave A, docs only

**Files:**
- Create: `docs/architecture/2026-08-13-nevercompile-classpath-options.md`

**Brief for worker (NNN=005):**

Goal: produce a background research document for the `dalvik.annotation.optimization.NeverCompile` classpath gap so the user can choose a fix. **Research only — do not change any build file, jar, or SDK.** User directive 2026-08-13: more background is needed before deciding.

Authority: self-commit (never push), docs only.

Allowed Paths: `docs/architecture/2026-08-13-nevercompile-classpath-options.md`, `docs/orchestration/tasks/005-*.md`.

Forbidden Paths: everything else (no build files, no libs, no SDK changes).

Steps:

- [x] 1. Establish usage: `grep -rn 'NeverCompile' SystemUI-core/src SystemUI-*/src 2>/dev/null` — which files use it and for what.
- [x] 2. Establish where the class really lives: `unzip -l` the Soong `core-libart` javac jar(s) and `art.module.public.api.stubs.module_lib` for `dalvik/annotation/optimization/NeverCompile.class`; confirm absence from SysUISdk `android.jar`, `core-for-system-modules.jar`, and `libs/framework.jar` (evidence already in the Task 7 issue record — verify, don't assume).
- [x] 3. Check how AOSP SystemUI gets it: inspect `frameworks/base/packages/SystemUI/Android.bp` and Soong system-modules mechanics for why javac sees the class in AOSP builds.
- [x] 4. Check the reference project: `grep -rn 'NeverCompile\|dalvik' /home/conv/myspace/CarSystemUIGradle --include='*.kts' --include='*.md' | head -20` — did CarSystemUIGradle solve this, and how?
- [x] 5. Write the research doc with: problem statement; findings from steps 1–4 with command evidence; at least three options — (a) patch SysUISdk `android.jar` with the dalvik annotation classes from `core-libart` (AGENTS.md §2.4 precedent), (b) a new tracked `compileOnly` annotations jar packaged from `core-libart` by a Python tool (flags-jar precedent), (c) extend the existing `libs/keepanno-annotations.jar` mechanism — each with provenance compliance (rules F/R), runtime implications (annotation retention, `@NeverCompile` is a no-op annotation), and a recommendation.
- [x] 6. Worker commit (never push): `git add docs/architecture/2026-08-13-nevercompile-classpath-options.md && git commit -m "docs: research NeverCompile classpath options"`

Acceptance (architect re-runs): doc exists, contains command evidence for steps 1–4, three options with a recommendation, no other files in the commit.

---

### Task 5: Pin `androidx.media` to 1.8.0 (brief 006) — Wave B, after Task 3

**Files:**
- Modify: `gradle/libs.versions.toml` (red-line, user pre-approved 2026-08-13: highest usable public version)
- Modify: `SystemUI-core/build.gradle.kts` (explicit dependency)

**Brief for worker (NNN=006):**

Goal: add an explicit `androidx.media:media:1.8.0` dependency so `MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE` resolves (the transitive 1.4.1 from `mediarouter:1.9.0-alpha01` lacks it). User pre-approved 1.8.0 (highest public stable per `maven-metadata.xml`).

Authority: redline-gated — toml version-matrix edit pre-approved by the user 2026-08-13 for `androidx.media = 1.8.0` only. Commit but never push.

Allowed Paths: `gradle/libs.versions.toml` (media version + library entry only), `SystemUI-core/build.gradle.kts`, `docs/issues/`, `docs/orchestration/tasks/006-*.md`.

Forbidden Paths: everything else; especially any other version in the toml, `SystemUI-*/src/**`, `AGENTS.md`.

Steps:

- [x] 1. Confirm the current resolution evidence: `./gradlew :SystemUI-core:dependencyInsight --configuration debugCompileClasspath --dependency androidx.media:media 2>&1 | grep -E '1\.4\.1|1\.8\.0' | head -5` (expect 1.4.1 via mediarouter).
- [x] 2. Add to `gradle/libs.versions.toml`: version `media = "1.8.0"` and library `androidx-media = { group = "androidx.media", name = "media", version.ref = "media" }`, following existing entry style. Nothing else in the file changes.
- [x] 3. Add `implementation(libs.androidx.media)` to `SystemUI-core/build.gradle.kts` dependencies with a comment (`// explicit pin: mediarouter 1.9.0-alpha01 transitively resolves media 1.4.1 which lacks DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`).
- [x] 4. Acceptance run:

```bash
./gradlew :SystemUI-core:dependencyInsight --configuration debugCompileClasspath --dependency androidx.media:media 2>&1 | grep -E 'androidx.media:media' | head -3
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task006.log >/dev/null; grep -c 'DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE' /tmp/task006.log || echo '0 (media group gone)'
```

Expected: insight shows 1.8.0 selected; `0` matches for the constant error. Record the overall javac error count as diagnostics.

- [x] 5. Append the dated result note to the issue record; worker commit (never push):

```bash
git add gradle/libs.versions.toml SystemUI-core/build.gradle.kts docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build(deps): pin androidx.media to 1.8.0 for completion-percentage extra"
```

Acceptance (architect re-runs): Step 4 both commands; toml diff touches only the media entries.

---

### Task 6: Architect verification + docs sync (architect-executed)

**Files:**
- Modify: `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `AGENTS.md` §4.2/§4.4, `README.md` known-issues, `docs/issues/2026-08-12-current-progress-standards-review.md`

Steps:

- [x] 1. After Tasks 1–5 merge, run the full gate:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -1
python3 tools/check_source_alignment.py --strict 2>&1 | tail -3
./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/post-fixes-app.log | tail -15
```

- [x] 2. Record the truthful outcome: remaining javac error count by group (expected: only the `NeverCompile` group may remain, pending the research decision), or the next failing task if the build advanced past javac. No success claims without the log.
- [x] 3. Sync the maintained docs with the outcome (same edit set as the Task 7 documentation pass); append the wave summary to `docs/orchestration/log.md`; mark this plan's checkboxes.
- [x] 4. Commit and push:

```bash
git add docs/ AGENTS.md README.md
git commit -m "docs: record javac root-cause fix wave results"
git push
```
