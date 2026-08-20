# R8 Runtime Closure Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move four proven AOSP `static_libs` JARs from compile-only visibility into the APK program/runtime closure, reducing the current R8 missing-class set from 140 to the predicted 125 without introducing duplicate classes.

**Architecture:** This batch changes only Gradle dependency scope; it does not rebuild artifacts or alter resources. `msdl.jar`, `monet.jar`, `wifi-flags.jar`, and `wm-shell-flags.jar` are already clean tier-② AOSP JARs whose owning Soong edges are `static_libs`, so `implementation(files(...))` is the correct Gradle program-input mapping. Later batches rebuild incomplete artifacts and are intentionally excluded.

**Tech Stack:** Gradle 9.5.0, AGP 9.3.1, builtInKotlin 2.2.10, R8, Python unittest.

**Spec:** `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A6/A10/A12 and §7 Batch 1.

## Global Constraints

- No stub, source/res modification, generated resource, keep rule, dontwarn, source exclusion, or build-check bypass.
- Do not modify any JAR/AAR, dependency version, module boundary, SysUISdk file, or local Maven artifact.
- Preserve `view_capture.jar`, `motion_tool_lib.jar`, Traceur, SettingsLib, and keepanno scopes for their later batches.
- Use `-Dorg.gradle.workers.max=4` for heavy Gradle verification; project heap remains `-Xmx16g`.
- Commit in English; worker must not push.

---

### Task 1: Correct the four runtime scopes

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Create: `docs/issues/2026-08-20-r8-runtime-batch1-scope.md`

**Interfaces:**
- Consumes: the four existing tier-② files under `libs/` and the AOSP `static_libs` evidence recorded by Task 031.
- Produces: four `implementation(files(...))` program inputs consumed by app debug D8 and release R8.

- [ ] **Step 1: Record the pre-change failing scope assertion**

Run a Python snippet that reads `SystemUI-core/build.gradle.kts`, confirms all four target paths exist as `compileOnly(files(...))`, and exits non-zero because none is `implementation`. Record the command and actual `compileOnly=4, implementation=0` result in the issue file.

- [ ] **Step 2: Write the issue record before the implementation edit**

Create the issue document with background, exact four Soong edges, allowed changes, verification commands, actual error-count evolution, and remaining batches. State that the pre-change release baseline is 140 missing classes and that 125 is a prediction until freshly measured.

- [ ] **Step 3: Change only the four dependency scopes and comments**

In `SystemUI-core/build.gradle.kts`, replace `compileOnly` with `implementation` for exactly:

```kotlin
files("${rootProject.projectDir}/libs/msdl.jar")
files("${rootProject.projectDir}/libs/monet.jar")
files("${rootProject.projectDir}/libs/wifi-flags.jar")
files("${rootProject.projectDir}/libs/wm-shell-flags.jar")
```

Update adjacent comments so they say these JARs are AOSP `static_libs` runtime/program inputs. Do not change any other dependency.

- [ ] **Step 4: Run the post-change scope assertion**

Run a Python snippet that proves the four exact paths now occur under `implementation`, occur zero times under `compileOnly`, and that the unrelated compile-only paths for `view_capture.jar`, `motion_tool_lib.jar`, `TraceurCommon.jar`, `traceur-res-R.jar`, and `keepanno-annotations.jar` are unchanged.

Expected: `target implementation=4`, `target compileOnly=0`, all five deferred paths still compileOnly.

- [ ] **Step 5: Run static and unit checks**

Run:

```bash
git diff --check
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: clean diff; 147 tests pass.

- [ ] **Step 6: Verify debug duplicate classes and APK program input**

Run:

```bash
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4
```

Expected: BUILD SUCCESSFUL. Then use `/home/conv/Android/Sdk/cmdline-tools/latest/bin/apkanalyzer dex packages --defined-only app/build/outputs/apk/debug/app-debug.apk` to prove representative classes are defined in the APK:

- `com.android.systemui.monet.ColorScheme`
- `com.google.android.msdl.domain.MSDLPlayer`
- `com.android.wifi.flags.Flags`
- `com.android.wm.shell.Flags`

- [ ] **Step 7: Measure release R8 progression without bypassing the remaining failure**

Run:

```bash
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4
```

Expected at this intermediate batch: task still fails on the remaining real closure gaps. Count the newly generated `app/build/outputs/mapping/release/missing_rules.txt` rules and unique classes. The predicted result is 125; record the actual result exactly. Any new/unexpected missing class or duplicate-class error is a diagnosis result, not permission to add dontwarn or alter another scope.

- [ ] **Step 8: Finalize documentation and commit**

Update the issue record with all actual commands/results, including whether debug APK was produced and the measured release missing count. Run `git diff --check`, confirm only the two allowed files changed, and commit:

```bash
git add SystemUI-core/build.gradle.kts docs/issues/2026-08-20-r8-runtime-batch1-scope.md
git commit -m "fix: add pure AOSP runtime jars to APK closure"
```

Do not push. End with the required `HANDOFF:` block.
