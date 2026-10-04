# R8 Runtime Closure Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILLS: Use `superpowers:test-driven-development` for the packager, then `superpowers:verification-before-completion` before committing. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace polluted `monet.jar` with a reproducible 56-class clean artifact and move four AOSP `static_libs` JARs into the APK program/runtime closure, reducing release R8 missing classes from 140 to the predicted 125 without duplicate classes.

**Architecture:** The old turbine-combined monet artifact already flattened `libmonet` and `error_prone_annotations`; Gradle separately provides the official errorprone artifact, producing 27 duplicate classes. A focused Python packager will merge only the two owning Soong `javac` outputs (SystemUI monet + external libmonet). Gradle continues to obtain errorprone from official Maven. The four owning Soong edges are then represented as Gradle `implementation` program inputs.

**Tech Stack:** Python 3 `zipfile`/`unittest`, Gradle 9.5.0, AGP 9.3.1, builtInKotlin 2.2.10, D8/R8.

**Spec:** `docs/orchestration/tasks/033-r8-runtime-batch1-scope.md` and `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A6/A10/A12.

## Global Constraints

- No stub, source/res modification, generated resource, keep rule, dontwarn, source exclusion, Maven exclusion, or disabled check.
- Do not change any dependency version, module boundary, SysUISdk file, local Maven artifact, or artifact other than `libs/monet.jar`.
- Preserve `view_capture.jar`, `motion_tool_lib.jar`, Traceur, SettingsLib, and keepanno scopes for later batches.
- Use `-Dorg.gradle.workers.max=4` for heavy Gradle verification.
- Commit in English; worker must not push.

---

### Task 1: Build the deterministic clean monet artifact test-first

**Files:**
- Create: `tools/package_monet_jar.py`
- Create: `tools/tests/test_package_monet_jar.py`
- Modify: `libs/monet.jar`
- Update: `docs/issues/2026-08-20-r8-runtime-batch1-scope.md`

**Interfaces:**
- CLI: `python3 tools/package_monet_jar.py [--aosp-root PATH] [--output PATH]`
- Python function: `package_monet_jar(monet_input: Path, libmonet_input: Path, output: Path) -> tuple[int, int]`, returning each input's emitted class count.
- Inputs: exact Soong `javac` JARs named in the brief.
- Output: deterministic class-only JAR containing only the two approved namespaces.

- [ ] **Step 1: Preserve the diagnosed REDLINE evidence**

Ensure the issue record contains the actual first-attempt evidence: 83 old classes = 9 monet + 47 libmonet + 27 errorprone; `checkDebugDuplicateClasses` failed with exactly 27 collisions against official Maven `error_prone_annotations:2.50.0`; the user approved clean javac-output repackaging.

- [ ] **Step 2: Write four failing tests**

Create exactly these four test methods:

1. `test_merges_only_expected_class_namespaces`
2. `test_output_is_deterministic`
3. `test_rejects_duplicate_class_entries`
4. `test_rejects_unexpected_class_namespace`

Use temporary synthetic input JARs; do not depend on the live AOSP tree. Import the not-yet-existing production API and run:

```bash
python3 -m unittest tools.tests.test_package_monet_jar -v
```

Record the expected RED failure caused by the missing implementation.

- [ ] **Step 3: Implement the minimal packager**

Implement the exact CLI/function contract. Read only `.class` entries. Require every emitted class to start with either `com/android/systemui/monet/` or `com/google/ux/material/libmonet/`. Reject missing/empty input, duplicate class names, or any unexpected namespace. Write sorted entries with timestamp `(1980, 1, 1, 0, 0, 0)`, deflate compression, Unix mode `0644`, and no source manifests/directories.

- [ ] **Step 4: Make focused tests green**

Run the focused test module twice. Expected: four tests pass both times.

- [ ] **Step 5: Generate and mechanically verify the real artifact**

Run the packager twice, hashing after each run; hashes must match. Compare class sets from output and the two input javac JARs using a Python assertion. Expected current-tree evidence:

```text
monet input=9
libmonet input=47
output=56
missing=0
extra=0
errorprone=0
```

Do not source classes from turbine-combined JARs.

---

### Task 2: Correct the four runtime scopes

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Update: `docs/issues/2026-08-20-r8-runtime-batch1-scope.md`

- [ ] **Step 1: Retain the pre-change failing scope evidence**

The issue must retain the original assertion result `compileOnly=4, implementation=0`, with non-zero exit because the desired state was absent.

- [ ] **Step 2: Change exactly four scopes and comments**

Replace `compileOnly` with `implementation` for only:

```kotlin
files("${rootProject.projectDir}/libs/msdl.jar")
files("${rootProject.projectDir}/libs/monet.jar")
files("${rootProject.projectDir}/libs/wifi-flags.jar")
files("${rootProject.projectDir}/libs/wm-shell-flags.jar")
```

Comments must identify them as AOSP `static_libs` runtime/program inputs.

- [ ] **Step 3: Run the scope assertion**

Prove target `implementation=4`, target `compileOnly=0`, and deferred `view_capture.jar`, `motion_tool_lib.jar`, `TraceurCommon.jar`, `traceur-res-R.jar`, `keepanno-annotations.jar` remain `compileOnly`.

---

### Task 3: Verify debug and release progression

**Files:**
- Update: `docs/issues/2026-08-20-r8-runtime-batch1-scope.md`

- [ ] **Step 1: Run static and full unit checks**

```bash
git diff --check
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: clean diff and 151/151 tests.

- [ ] **Step 2: Verify duplicate classes and build debug APK**

```bash
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4
```

Expected: BUILD SUCCESSFUL. Failure from monet/errorprone means the clean artifact is incorrect; diagnose rather than adding an exclusion.

- [ ] **Step 3: Verify representative classes in the APK**

Use:

```bash
/home/conv/Android/Sdk/cmdline-tools/latest/bin/apkanalyzer dex packages --defined-only app/build/outputs/apk/debug/app-debug.apk
```

Prove definitions for `ColorScheme`, `Hct`, `MSDLPlayer`, Wi-Fi `Flags`, and WM-Shell `Flags` exactly as listed in the brief.

- [ ] **Step 4: Measure release R8 progression**

```bash
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4
```

Expected intermediate state: release R8 still fails on later closure batches. Count generated rules and unique missing classes; prediction is 125, but record actual output. Do not add keep/dontwarn or alter another scope.

- [ ] **Step 5: Finalize and commit**

Document all actual commands/results. Run `git diff --check`; confirm only the five allowed paths differ from base. Invoke `superpowers:verification-before-completion`, then commit:

```bash
git add SystemUI-core/build.gradle.kts libs/monet.jar tools/package_monet_jar.py tools/tests/test_package_monet_jar.py docs/issues/2026-08-20-r8-runtime-batch1-scope.md
git commit -m "fix: add clean AOSP runtime jars to APK closure"
```

Do not push. End with the required `HANDOFF:` block.
