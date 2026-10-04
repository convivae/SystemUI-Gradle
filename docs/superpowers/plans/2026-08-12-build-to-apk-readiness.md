# Build-to-APK Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Remove the currently proven core-compile and APK-packaging blockers while preserving AOSP provenance, then establish a truthful `:app:assembleDebug` baseline.

**Architecture:** Keep the existing 13-module topology unchanged. Fix dependency semantics at their owning boundary: public `jsr305` through Maven, platform-provided SettingsLib flags as compile-only, SystemUI shared flags as a concrete AOSP javac JAR, and WM-Shell overlap in the deterministic AAR packaging layer. Make AIDL/KSP wiring variant-aware before upgrading AGP and refreshing maintained documentation.

**Tech Stack:** Gradle 9.5.0, AGP 9.2.0→9.3.1 verification, AGP built-in Kotlin 2.2.10, KSP 2.2.10-2.0.2, Dagger 2.59.2, Python 3 unittest, AOSP Soong outputs.

## Global Constraints

- Do not create Java/Kotlin stubs or synthetic resources.
- Do not modify AOSP-mirrored `src/`, AIDL, or `res/` files for these dependency and packaging failures.
- SystemUI-owned code remains source-based; non-SystemUI code remains JAR/AAR/public Maven according to rules S/F/R.
- Keep `:app` source-free and dependent only on `:SystemUI-core`.
- All new scripts under `tools/` must be Python.
- Update tracked `libs/` artifacts when their canonical AOSP input changes.
- Run source alignment after implementation; `MISSING`, `MISPLACED`, and `EXTRA` must remain zero.
- Do not use `@Suppress("DEPRECATION")` or compiler suppression as a substitute for supported Gradle APIs.
- Each task ends with an English commit message and a review checkpoint.
- The issue record for this sequence is `docs/issues/2026-08-12-current-progress-standards-review.md`.

---

## File Map

| File | Responsibility in this plan |
|------|-----------------------------|
| `gradle/libs.versions.toml` | Public `jsr305` coordinate and AGP version catalog value |
| `settings.gradle.kts` | Actual AGP plugin version used during settings evaluation |
| `SystemUI-core/build.gradle.kts` | Dependency scopes and variant-aware AIDL/KSP task wiring |
| `tools/package_aconfig_jars.py` | Reproducibly copy concrete AOSP aconfig implementation JARs |
| `tools/tests/test_package_aconfig_jars.py` | Unit tests for aconfig artifact source policy and byte preservation |
| `tools/package_aosp_aar.py` | Deterministic exclusion of classes owned by a sibling AAR |
| `tools/tests/test_package_aosp_aar.py` | Regression tests for WM-Shell overlap removal |
| `libs/systemui-shared-flags.jar` | Concrete SystemUI shared flags runtime implementation |
| `libs/aars/WindowManager-Shell.aar` | Main WM-Shell AAR without classes owned by shared AAR |
| `libs/maven/com.android.systemui/WindowManager-Shell/1.0.0/WindowManager-Shell-1.0.0.aar` | Maven-delivered copy of corrected WM-Shell AAR |
| `README.md`, `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/README.md` | Truthful version and build-status documentation |

---

### Task 1: Resolve the two core Kotlin errors with the AOSP-declared JSR-305 dependency

**Files:**
- Modify: `gradle/libs.versions.toml`
- Modify: `SystemUI-core/build.gradle.kts`
- Update: `docs/issues/2026-08-12-current-progress-standards-review.md`

**Interfaces:**
- Consumes: AOSP `SystemUI/Android.bp` static dependency named `jsr305`.
- Produces: `libs.jsr305` resolving `javax.annotation.concurrent.GuardedBy` from `com.google.code.findbugs:jsr305:3.0.2`.

- [x] **Step 1: Preserve the failing compiler evidence**

Run:

```bash
./gradlew :SystemUI-core:compileDebugKotlin --console=plain 2>&1 | tee /tmp/task1-before.log
grep -E "Unresolved reference '(concurrent|GuardedBy)'" /tmp/task1-before.log
```

Expected: exactly the two existing errors in `CommunalAppWidgetHost.kt`.

- [x] **Step 2: Add the public dependency to the version catalog**

Add under `[versions]`:

```toml
jsr305 = "3.0.2"
```

Add under `[libraries]`:

```toml
jsr305 = { module = "com.google.code.findbugs:jsr305", version.ref = "jsr305" }
```

- [x] **Step 3: Add the dependency to SystemUI-core**

Add next to the other AOSP-declared annotation/runtime dependencies:

```kotlin
// AOSP SystemUI-core static_libs: "jsr305"; provides javax.annotation.concurrent.GuardedBy.
implementation(libs.jsr305)
```

Do not change `CommunalAppWidgetHost.kt`; its import matches AOSP.

- [x] **Step 4: Verify the core compiler and KSP**

Run:

```bash
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --console=plain
```

Expected: both tasks complete successfully and the two `GuardedBy` errors disappear.

- [x] **Step 5: Record and commit**

Append the command and actual result to the issue record, then run:

```bash
git add gradle/libs.versions.toml SystemUI-core/build.gradle.kts \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build: add AOSP jsr305 dependency"
```

---

### Task 2: Correct aconfig JAR compile/runtime semantics

**Files:**
- Create: `tools/package_aconfig_jars.py`
- Create: `tools/tests/test_package_aconfig_jars.py`
- Modify: `SystemUI-core/build.gradle.kts`
- Replace: `libs/systemui-shared-flags.jar`
- Update: `docs/issues/2026-08-12-current-progress-standards-review.md`

**Interfaces:**
- Consumes concrete AOSP JAR:
  `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/libs/systemui/aconfig/com_android_systemui_shared_flags_lib/android_common/javac/com_android_systemui_shared_flags_lib.jar`.
- Produces tracked runtime JAR: `libs/systemui-shared-flags.jar`.
- Keeps `libs/settingslib-flags.jar` as a compile header because its runtime implementation is platform-provided.

- [x] **Step 1: Write unit tests for canonical source policy**

Create `tools/tests/test_package_aconfig_jars.py` with this complete test module:

```python
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "package_aconfig_jars.py"
_spec = importlib.util.spec_from_file_location("package_aconfig_jars", _SCRIPT)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class TestAconfigJarPackaging(unittest.TestCase):
    def test_runtime_config_uses_javac_not_turbine(self):
        source, destination = module.CONFIGS["systemui-shared-flags"]
        self.assertIn("/javac/", str(source))
        self.assertNotIn("turbine", str(source))
        self.assertEqual(destination, Path("libs/systemui-shared-flags.jar"))

    def test_copy_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "javac" / "flags.jar"
            source.parent.mkdir()
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("com/example/Flags.class", b"class-bytes")
            destination = root / "out.jar"
            module.copy_jar(source, destination)
            self.assertEqual(destination.read_bytes(), source.read_bytes())
```

- [x] **Step 2: Run the new tests and verify they fail before the script exists**

Run:

```bash
python3 -m unittest tools.tests.test_package_aconfig_jars -v
```

Expected: import/file failure for `tools/package_aconfig_jars.py`.

- [x] **Step 3: Implement the focused Python packager**

Create `tools/package_aconfig_jars.py` with this complete implementation:

```python
#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil
import zipfile

AOSP_JAVAC = Path(
    "/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/libs/systemui/"
    "aconfig/com_android_systemui_shared_flags_lib/android_common/javac/"
    "com_android_systemui_shared_flags_lib.jar"
)
CONFIGS = {
    "systemui-shared-flags": (AOSP_JAVAC, Path("libs/systemui-shared-flags.jar")),
}


def copy_jar(source: Path, destination: Path) -> None:
    source = Path(source)
    destination = Path(destination)
    if "turbine" in source.parts:
        raise ValueError(f"runtime JAR must not come from turbine: {source}")
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise FileNotFoundError(f"missing or invalid AOSP JAR: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package concrete AOSP aconfig JARs")
    parser.add_argument("artifact", choices=sorted(CONFIGS))
    args = parser.parse_args()
    source, destination = CONFIGS[args.artifact]
    copy_jar(source, destination)
    print(f"{args.artifact}: {source} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The script performs a byte-preserving copy of the canonical AOSP javac output; no shell script or generated source is added.

- [x] **Step 4: Make dependency scopes match AOSP semantics**

In `SystemUI-core/build.gradle.kts`, change only SettingsLib flags:

```kotlin
// Android.bp lists aconfig_settingslib_flags_java_lib under libs and states that
// its implementation is already in framework.jar; use the header only for compilation.
compileOnly(files("${rootProject.projectDir}/libs/settingslib-flags.jar"))
```

Keep `systemui-shared-flags.jar` as `implementation`, because Task 2 replaces it with concrete bytecode.

- [x] **Step 5: Package and verify the concrete shared flags JAR**

Run:

```bash
python3 tools/package_aconfig_jars.py systemui-shared-flags
javap -classpath libs/systemui-shared-flags.jar -p -c \
  com.android.systemui.shared.Flags | grep -m1 -A2 'public static boolean'
```

Expected: `javap` prints a `Code:` block for a flag method.

- [x] **Step 6: Verify D8 no longer rejects flag JARs**

Run:

```bash
./gradlew :app:desugarDebugFileDependencies --rerun-tasks --console=plain \
  2>&1 | tee /tmp/task2-d8.log
! grep -q "Absent Code attribute" /tmp/task2-d8.log
```

Expected: no `Absent Code attribute` error.

- [x] **Step 7: Run all Python tests and commit**

Run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
git add tools/package_aconfig_jars.py tools/tests/test_package_aconfig_jars.py \
  SystemUI-core/build.gradle.kts libs/systemui-shared-flags.jar \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build: package concrete shared aconfig flags"
```

---

### Task 3: Remove the WM-Shell AAR class-set overlap at the packaging boundary

**Files:**
- Modify: `tools/package_aosp_aar.py`
- Modify: `tools/tests/test_package_aosp_aar.py`
- Replace: `libs/aars/WindowManager-Shell.aar`
- Replace: `libs/maven/com.android.systemui/WindowManager-Shell/1.0.0/WindowManager-Shell-1.0.0.aar`
- Update: `docs/issues/2026-08-12-current-progress-standards-review.md`

**Interfaces:**
- Consumes: the main and shared Soong javac/kotlin JARs already declared in `CONFIGS`.
- Produces: two AARs whose `classes.jar` entry sets have an empty intersection.

- [x] **Step 1: Add a failing exclusion test**

Add this complete method to `TestAssembleAar`:

```python
def test_excluded_prefix_is_omitted_but_other_classes_remain(self):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        code = root / "code.jar"
        _make_jar(
            code,
            {
                "com/android/wm/shell/shared/IHomeTransitionListener.class": b"aidl",
                "com/android/wm/shell/ShellTaskOrganizer.class": b"main",
            },
        )
        resources = root / "res"
        resources.mkdir()
        manifest = root / "AndroidManifest.xml"
        manifest.write_bytes(b"<manifest/>")
        rtxt = root / "R.txt"
        rtxt.write_bytes(b"")
        output = root / "library.aar"

        paar.assemble_aar(
            [code],
            resources,
            manifest,
            rtxt,
            output,
            exclude_prefixes=[
                "com/android/wm/shell/shared/IHomeTransitionListener"
            ],
        )

        with zipfile.ZipFile(output) as aar:
            with zipfile.ZipFile(BytesIO(aar.read("classes.jar"))) as classes:
                names = set(classes.namelist())
        self.assertNotIn(
            "com/android/wm/shell/shared/IHomeTransitionListener.class", names
        )
        self.assertIn("com/android/wm/shell/ShellTaskOrganizer.class", names)
```

- [x] **Step 2: Run the focused test and verify failure**

Run:

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestAssembleAar.test_excluded_prefix_is_omitted_but_other_classes_remain -v
```

Expected: failure because `assemble_aar` does not yet accept `exclude_prefixes`.

- [x] **Step 3: Implement deterministic exclusion**

Extend the function signature without changing existing rejection behavior:

```python
def assemble_aar(
    code_jars,
    res_dirs,
    manifest: Path,
    rtxt: Path,
    output: Path,
    reject_prefixes=None,
    exclude_prefixes=None,
) -> None:
    reject_prefixes = reject_prefixes or []
    exclude_prefixes = exclude_prefixes or []
```

In the class-entry loop, after forbidden-prefix rejection and before duplicate detection:

```python
if any(name.startswith(prefix) for prefix in exclude_prefixes):
    continue
```

Add these exact prefixes only to the main `WindowManager-Shell` config:

```python
"exclude_prefixes": [
    "com/android/wm/shell/shared/IFocusTransitionListener",
    "com/android/wm/shell/shared/IHomeTransitionListener",
    "com/android/wm/shell/shared/IShellTransitions",
],
```

Pass `cfg.get("exclude_prefixes", [])` from `build_artifact` to `assemble_aar`. Do not exclude the whole `com/android/wm/shell/shared/` package.

- [x] **Step 4: Run tests and regenerate the affected AAR delivery**

Run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/package_aosp_aar.py WindowManager-Shell
python3 tools/install_aar_to_maven.py
```

- [x] **Step 5: Verify zero class overlap**

Use a Python ZIP check that reads each AAR's `classes.jar` and computes the set intersection. Expected output:

```text
WindowManager-Shell ∩ WindowManager-Shell-shared = 0
```

Then run:

```bash
./gradlew :app:checkDebugDuplicateClasses --rerun-tasks --console=plain
```

Expected: `BUILD SUCCESSFUL` and no WM-Shell duplicate classes.

- [x] **Step 6: Commit source, tests and regenerated artifacts**

```bash
git add tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py \
  libs/aars/WindowManager-Shell.aar \
  libs/maven/com.android.systemui/WindowManager-Shell/1.0.0/WindowManager-Shell-1.0.0.aar \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build: deduplicate WM Shell AIDL classes"
```

---

### Task 4: Make KSP/AIDL wiring variant-aware and remove the deprecated provider escape hatch

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `gradle.properties`
- Update: `docs/PITFALLS.md`
- Update: `docs/issues/2026-08-12-current-progress-standards-review.md`

**Interfaces:**
- Produces task mapping `kspDebugKotlin → compileDebugAidl` and `kspReleaseKotlin → compileReleaseAidl`.
- Removes the need for `android.sourceset.disallowProvider=false`.

- [x] **Step 1: Preserve the failing release task graph**

Run:

```bash
./gradlew :SystemUI-core:kspReleaseKotlin --dry-run --console=plain \
  | grep -E 'SystemUI-core:(compile(Debug|Release)Aidl|kspReleaseKotlin)'
```

Expected before the fix: `compileDebugAidl` appears and `compileReleaseAidl` does not.

- [x] **Step 2: Stop passing Provider objects to the Kotlin source-set API**

Replace the two provider-based generated source directories with project-relative strings:

```kotlin
kotlin.srcDir("build/generated/aidl_source_output_dir/debug/out")
kotlin.srcDir("build/generated/aidl_source_output_dir/release/out")
```

Then remove this line from `gradle.properties`:

```properties
android.sourceset.disallowProvider=false
```

Keep `android.disallowKotlinSourceSets=false`; KSP still requires it under built-in Kotlin.

- [x] **Step 3: Replace the all-KSP debug dependency with explicit mappings**

Replace the current `startsWith("ksp")` block with:

```kotlin
tasks.matching { it.name == "kspDebugKotlin" }.configureEach {
    dependsOn("compileDebugAidl")
}
tasks.matching { it.name == "kspReleaseKotlin" }.configureEach {
    dependsOn("compileReleaseAidl")
}
```

- [x] **Step 4: Verify both task graphs and actual KSP tasks**

Run:

```bash
./gradlew :SystemUI-core:kspDebugKotlin --dry-run --console=plain \
  | grep -E 'SystemUI-core:(compile(Debug|Release)Aidl|kspDebugKotlin)'
./gradlew :SystemUI-core:kspReleaseKotlin --dry-run --console=plain \
  | grep -E 'SystemUI-core:(compile(Debug|Release)Aidl|kspReleaseKotlin)'
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:kspReleaseKotlin \
  --rerun-tasks --console=plain
```

Expected:

- debug graph includes only core `compileDebugAidl`;
- release graph includes only core `compileReleaseAidl`;
- both KSP tasks complete successfully;
- the AGP warning about `android.sourceset.disallowProvider=false` disappears.

- [x] **Step 5: Update the pitfall record and commit**

Document the variant mapping and removal of the deprecated property, then run:

```bash
git add SystemUI-core/build.gradle.kts gradle.properties docs/PITFALLS.md \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build: wire KSP to variant AIDL tasks"
```

---

### Task 5: Verify the latest stable AGP without changing the Kotlin/KSP matrix

**Files:**
- Modify: `settings.gradle.kts`
- Modify: `gradle/libs.versions.toml`
- Update: `docs/issues/2026-08-12-current-progress-standards-review.md`

**Interfaces:**
- Consumes: AGP 9.3.1, whose POM is already documented as embedding Kotlin 2.2.10.
- Preserves: Kotlin 2.2.10 and KSP 2.2.10-2.0.2.

- [x] **Step 1: Update both AGP version declarations atomically**

Set:

```kotlin
id("com.android.application") version "9.3.1" apply false
id("com.android.library") version "9.3.1" apply false
```

and:

```toml
agp = "9.3.1"
```

Do not change Kotlin or KSP in this task.

- [x] **Step 2: Verify configuration and the known milestones**

Run:

```bash
./gradlew help --console=plain
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin \
  --rerun-tasks --console=plain
./gradlew :app:checkDebugDuplicateClasses :app:desugarDebugFileDependencies \
  --rerun-tasks --console=plain
```

Expected: all commands complete successfully after Tasks 1–4.

- [x] **Step 3: Handle the result without overstating it**

If all commands pass, record AGP 9.3.1 as verified and commit:

```bash
git add settings.gradle.kts gradle/libs.versions.toml \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build: upgrade Android Gradle plugin to 9.3.1"
```

If an AGP-specific regression occurs, copy the exact task and exception into the issue record, restore only the two AGP declarations to 9.2.0, and commit the documented compatibility constraint:

```bash
git add settings.gradle.kts gradle/libs.versions.toml \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "docs: record AGP 9.3.1 compatibility blocker"
```

---

### Task 6: Remove version/documentation drift and formatting defects

**Files:**
- Modify: `build.gradle.kts`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `gradle/libs.versions.toml`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/PITFALLS.md`
- Modify: `docs/PLAN.md`
- Modify: `docs/README.md`

**Interfaces:**
- Consumes the actual versions and task results from Tasks 1–5.
- Produces a single truthful handoff/status description.

- [x] **Step 1: Correct build-script comments**

Replace stale references with the actual verified matrix:

- Kotlin 2.2.10, not 2.3.x/2.3.21;
- KSP 2.2.10-2.0.2, not 2.3.11;
- Dagger 2.59.2, not 2.60.1;
- Compose 1.11.4, with the note that AOSP originally referenced 1.9.0-alpha01 only where historical context is useful.

Comments must explain constraints rather than claim a newer unconfigured version.

- [x] **Step 2: Correct the root README resource mapping**

State that `SystemUI-res/res`, `SystemUI-res/res-keyguard`, and `SystemUI-res/res-product` own the AOSP resource copies. Remove the obsolete claim that these directories are under `SystemUI-core` or gitignored.

- [x] **Step 3: Synchronize maintained status documents**

Update the maintained documents with actual results from the prior tasks:

- current AGP version or the documented 9.3.1 blocker;
- core Kotlin success after JSR-305;
- corrected flag JAR and WM-Shell AAR packaging;
- variant-aware KSP/AIDL wiring;
- current known `:app:assembleDebug` blockers from the standards review, explicitly marking final post-fix APK verification as pending Task 7.

- [x] **Step 4: Fix whitespace defects and compile-SDK warning configuration**

Remove the EOF/trailing whitespace reported by `git diff --check`. Update:

```properties
android.suppressUnsupportedCompileSdk=JdJkcSdk,SysUISdk
```

only if the active AGP still emits the preview-SDK warning with that exact recommendation.

- [x] **Step 5: Verify documentation consistency**

Run:

```bash
git diff --check
rg -n "KSP 2\.3\.11|Kotlin 2\.3\.21|Dagger 2\.60\.1" \
  --glob '*.gradle.kts' --glob '*.toml' .
rg -n "SystemUI-core/res-keyguard|SystemUI-core/res-product" README.md docs AGENTS.md
```

Expected: all three commands produce no stale matches or whitespace errors, except historical documents that explicitly label old versions as superseded.

- [x] **Step 6: Commit documentation hygiene**

```bash
git add build.gradle.kts SystemUI-core/build.gradle.kts gradle/libs.versions.toml \
  gradle.properties README.md AGENTS.md docs
git commit -m "docs: align build guidance with verified toolchain"
```

---

### Task 7: Run the full verification ladder and establish the next truthful milestone

**Files:**
- Update: `docs/issues/2026-08-12-current-progress-standards-review.md`
- Update: `docs/CURRENT_STATE.md`
- Update: `docs/HANDOFF.md`
- Update: `AGENTS.md`
- Update: `docs/README.md`

**Interfaces:**
- Consumes all corrected dependencies and artifacts from Tasks 1–6.
- Produces either a verified debug APK or a fully recorded next blocker with no false success claim.

- [x] **Step 1: Run non-build integrity checks**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/check_source_alignment.py --strict
git diff --check
```

Expected:

- all Python tests pass;
- `MISSING=0`, `MISPLACED=0`, `EXTRA=0`;
- no whitespace errors.

- [x] **Step 2: Run annotation processing and core compilation from a clean project state**

```bash
./gradlew :SystemUI-core:clean
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin \
  --console=plain 2>&1 | tee /tmp/final-core.log
```

Expected: `BUILD SUCCESSFUL`, 2933 KSP files unless upstream processor output legitimately changes, and no Kotlin compiler errors.

- [x] **Step 3: Run the APK task**

```bash
./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/final-app.log
```

Success condition:

```bash
test -f app/build/outputs/apk/debug/app-debug.apk
```

- [x] **Step 4: Record the actual endpoint**

If the APK exists, record its path, size, SHA-256 and successful command in all maintained status documents.

If a new error appears, record:

- exact failing task;
- first causal exception/error;
- owning AOSP module or dependency;
- whether the issue is source, JAR, AAR, resource, manifest, D8/R8, or packaging;
- the next standards-compliant investigation command.

Stop at that recorded baseline. Do not add exclusions, stubs, generated resources, or source edits in this verification task.

- [x] **Step 5: Commit and push the verified state**

```bash
git add AGENTS.md docs
git commit -m "docs: record verified APK build baseline"
git push origin main
```

If Task 3 generated an APK, do not add `app/build/` to Git.

---

## Deferred Follow-ups

These are deliberately outside the known-blocker sequence and should receive separate issue records after Task 7:

1. Configure Room schema export through the official Room Gradle plugin or a documented KSP schema directory;
2. address Kotlin 2.3 data-class copy-visibility diagnostics without suppression and with CONV discipline if AOSP source must change;
3. investigate duplicated permissions in the AOSP-derived manifest merge without editing mirrored resources/manifests ad hoc;
4. evaluate removal of `android.disallowKotlinSourceSets=false` when AGP/KSP offer a supported built-in Kotlin source API.

## Plan Self-Review

- Spec coverage: rules P/S/C/F/R/B/D/I, fresh-checkout reproducibility, core compile, APK packaging, latest AGP verification, documentation and final build evidence are each mapped to a task.
- Placeholder scan: no implementation step relies on unspecified code or an unnamed future dependency.
- Interface consistency: Task 2 produces the concrete shared flags JAR consumed by the existing `implementation`; Task 3 produces non-overlapping AARs consumed through the existing catalog; Task 4 preserves debug/release generated-source paths while correcting task dependencies.
