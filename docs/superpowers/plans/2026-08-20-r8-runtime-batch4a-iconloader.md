# R8 Runtime Closure Batch 4A iconloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild iconloader as a complete deterministic 75-class AAR from its owning Soong javac and Kotlin implementation outputs, publish it at the user-approved local coordinate `1.0.1`, and remove exactly three R8 missing refs.

**Architecture:** Keep the existing resource-bearing tier② AAR boundary and `implementation` scope. Extend only the iconloader declarative packager input list, prove class/resource provenance with tests, install the byte-identical AAR into the repository-local Maven tree under a new coordinate, and remove the superseded coordinate.

**Tech Stack:** Python 3 `zipfile`/`unittest`, AOSP Soong implementation outputs, local Maven AAR repository, Gradle Kotlin DSL/version catalog, AGP 9.3.1/D8/R8.

**Spec:** `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §§3.1 A11, 5.3, 7 Batch 4 and `docs/issues/2026-08-20-r8-runtime-batch4a-iconloader.md`

## Global Constraints

- Rules P/S/C/F/R/B/H/D and ADR 0001–0005 remain mandatory.
- The user explicitly approved `com.android.systemui:iconloader` `1.0.0`→`1.0.1`; no other version/catalog changes are authorized.
- No source/res edits, stubs, keep/dontwarn, source exclusions, disabled checks, or SysUISdk work.
- Use only owning Soong `android_common/javac/iconloader.jar` and `android_common/kotlin/iconloader.jar`, never turbine/header/combined/FAT inputs.
- Preserve AOSP resource, manifest and Soong `R.txt` bytes exactly.
- Keep the existing `implementation(libs.systemui.iconloader)` edge unchanged.
- Install only an AAR in local Maven; do not put JARs there.
- Heavy Gradle commands use `-Dorg.gradle.workers.max=4`; piped commands use `set -o pipefail` and save true Gradle exits.
- Every wait/poll timeout is at most 90 seconds.

---

## File Map

- Modify `tools/tests/test_package_aosp_aar.py`: iconloader javac+Kotlin config, exact class-byte union, metadata/resource provenance, determinism tests.
- Modify `tools/package_aosp_aar.py`: add the fixed Kotlin implementation JAR to iconloader `code` inputs.
- Modify `tools/tests/test_install_aar_to_maven.py`: assert the approved iconloader `1.0.1` coordinate.
- Modify `tools/install_aar_to_maven.py`: change only iconloader registry version to `1.0.1`.
- Replace `libs/aars/iconloader.aar`: deterministic complete AAR.
- Delete `libs/maven/com/android/systemui/iconloader/1.0.0/iconloader-1.0.0.aar` and `.pom`.
- Create `libs/maven/com/android/systemui/iconloader/1.0.1/iconloader-1.0.1.aar` and `.pom`.
- Modify `gradle/libs.versions.toml`: change only `systemui-iconloader` to `1.0.1`.
- Update `docs/issues/2026-08-20-r8-runtime-batch4a-iconloader.md`: actual evidence.

### Task 1: Capture the fresh 109-ref baseline

**Files:**
- Read: `app/build/outputs/mapping/release/missing_rules.txt`
- Write outside repo: `/tmp/task036-r8-before.log`, `.status`, and `/tmp/task036-missing-before.txt`

- [ ] **Step 1: Run R8 before edits and preserve the true exit**

```bash
rm -f /tmp/task036-r8-before.{log,status} /tmp/task036-missing-before.txt
set -o pipefail
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
  2>&1 | tee /tmp/task036-r8-before.log
printf 'GRADLE_EXIT=%s\n' "${PIPESTATUS[0]}" | tee /tmp/task036-r8-before.status
cp app/build/outputs/mapping/release/missing_rules.txt /tmp/task036-missing-before.txt
```

Expected: true exit `1` at R8 missing classes; exactly 109 unique `-dontwarn` refs.

- [ ] **Step 2: Assert the exact baseline targets**

```bash
python3 - <<'PY'
from pathlib import Path
refs = {line.removeprefix('-dontwarn ').strip() for line in Path('/tmp/task036-missing-before.txt').read_text().splitlines() if line.startswith('-dontwarn ')}
targets = {
    'com.android.launcher3.icons.IconThemeController',
    'com.android.launcher3.icons.ThemedBitmap',
    'com.android.launcher3.icons.mono.ThemedIconDrawable',
}
assert len(refs) == 109, len(refs)
assert targets <= refs, targets - refs
assert 'com.android.aconfig.annotations.AssumeTrueForR8' in refs
print('BASELINE=109 TARGETS=3 PASS')
PY
```

### Task 2: Add failing artifact and coordinate tests

**Files:**
- Modify: `tools/tests/test_package_aosp_aar.py`
- Modify: `tools/tests/test_install_aar_to_maven.py`

- [ ] **Step 1: Extend the existing config test**

Make `test_iconloader_config_paths` assert an exact two-element ordered code list ending in:

```text
iconloader/android_common/javac/iconloader.jar
iconloader/android_common/kotlin/iconloader.jar
```

- [ ] **Step 2: Add three iconloader provenance tests**

Add `TestIconloaderProvenance` tests that:

1. read both canonical input JARs, build a temporary iconloader AAR, and assert every output class name and byte equals the exact disjoint input union; assert contributions `59 + 16 = 75` and all class names start with `com/android/launcher3/`;
2. assert output `res/**`, `AndroidManifest.xml`, and `R.txt` names/bytes equal the configured AOSP/Soong sources exactly;
3. build twice and assert the complete AAR bytes are identical.

- [ ] **Step 3: Add the exact coordinate test**

In `ArtifactRegistryTest`, add:

```python
def test_iconloader_coordinate(self):
    self.assertEqual(
        iam.ARTIFACTS['iconloader'],
        {'group': 'com.android.systemui', 'name': 'iconloader', 'version': '1.0.1'},
    )
```

- [ ] **Step 4: Run focused tests red**

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestArtifactConfigs.test_iconloader_config_paths \
  tools.tests.test_package_aosp_aar.TestIconloaderProvenance \
  tools.tests.test_install_aar_to_maven.ArtifactRegistryTest.test_iconloader_coordinate
```

Expected before implementation: failures showing the missing Kotlin input and old `1.0.0` coordinate.

### Task 3: Implement the minimal declarative fixes

**Files:**
- Modify: `tools/package_aosp_aar.py`
- Modify: `tools/install_aar_to_maven.py`

- [ ] **Step 1: Add only the owning Kotlin implementation JAR**

Set iconloader `code` to the ordered list:

```python
[
    SOONG_DIR / 'frameworks/libs/systemui/iconloaderlib/iconloader/android_common/javac/iconloader.jar',
    SOONG_DIR / 'frameworks/libs/systemui/iconloaderlib/iconloader/android_common/kotlin/iconloader.jar',
]
```

Do not alter resource/manifest/R inputs or general merge behavior.

- [ ] **Step 2: Apply only the approved local version**

Change the `ARTIFACTS['iconloader']['version']` value from `1.0.0` to `1.0.1`. Do not alter any other coordinate or POM dependency edge.

- [ ] **Step 3: Run focused tests green**

Run the focused command from Task 2. Expected: five selected tests, `OK` (one config + three provenance + one coordinate).

### Task 4: Rebuild and install the complete AAR

**Files:**
- Replace: `libs/aars/iconloader.aar`
- Delete: `libs/maven/com/android/systemui/iconloader/1.0.0/*`
- Create: `libs/maven/com/android/systemui/iconloader/1.0.1/*`
- Modify: `gradle/libs.versions.toml`

- [ ] **Step 1: Build twice and prove determinism**

```bash
python3 tools/package_aosp_aar.py iconloader
sha256sum libs/aars/iconloader.aar > /tmp/task036-iconloader-hash-first.txt
python3 tools/package_aosp_aar.py iconloader
sha256sum libs/aars/iconloader.aar > /tmp/task036-iconloader-hash-second.txt
diff -u /tmp/task036-iconloader-hash-first.txt /tmp/task036-iconloader-hash-second.txt
```

Expected: hash files identical; AAR classes are the exact 75-class union.

- [ ] **Step 2: Replace the local Maven coordinate**

```bash
rm -rf libs/maven/com/android/systemui/iconloader/1.0.0
python3 tools/install_aar_to_maven.py iconloader
```

Expected: only `1.0.1/iconloader-1.0.1.aar` and `.pom` remain under the iconloader artifact; installed AAR is byte-identical to `libs/aars/iconloader.aar`; POM declares version `1.0.1`, packaging `aar`, and no dependencies.

- [ ] **Step 3: Point only the catalog alias to 1.0.1**

Change:

```toml
systemui-iconloader = { group = "com.android.systemui", name = "iconloader", version = "1.0.1" }
```

No other catalog line may change.

### Task 5: Verify tests, Debug and APK definitions

- [ ] **Step 1: Run focused and full tests**

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestArtifactConfigs.test_iconloader_config_paths \
  tools.tests.test_package_aosp_aar.TestIconloaderProvenance \
  tools.tests.test_install_aar_to_maven.ArtifactRegistryTest.test_iconloader_coordinate
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: focused five tests `OK`; full baseline 160 + four new tests = 164, `OK`.

- [ ] **Step 2: Run duplicate check and Debug assembly**

```bash
rm -f /tmp/task036-debug.{log,status}
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task036-debug.log
printf 'GRADLE_EXIT=%s\n' "${PIPESTATUS[0]}" | tee /tmp/task036-debug.status
```

Expected: `GRADLE_EXIT=0`, `BUILD SUCCESSFUL`, no duplicate-class failure.

- [ ] **Step 3: Prove all three classes are defined**

Generate one `apkanalyzer dex packages --defined-only` output and assert `C d` rows for the three exact target classes. Expected: all three `DEFINED`, not merely referenced.

### Task 6: Verify exact R8 delta and deliver

**Files:**
- Modify: `docs/issues/2026-08-20-r8-runtime-batch4a-iconloader.md`

- [ ] **Step 1: Run fresh post-change R8**

```bash
rm -f /tmp/task036-r8-after.{log,status}
set -o pipefail
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
  2>&1 | tee /tmp/task036-r8-after.log
printf 'GRADLE_EXIT=%s\n' "${PIPESTATUS[0]}" | tee /tmp/task036-r8-after.status
```

Expected: true exit remains `1` at remaining missing classes.

- [ ] **Step 2: Compare unique sets mechanically**

Expected assertions:

- before = 109;
- after = 106;
- removed = exactly the three iconloader targets;
- added = empty;
- `AssumeTrueForR8` remains.

Any deviation requires `REDLINE` with the preserved sets; do not broaden scope or add suppressions.

- [ ] **Step 3: Record evidence and run hygiene checks**

Record exact hashes, 59+16=75 provenance, resource/meta equality, focused/full test counts, true Gradle exits, APK rows and R8 sets in the issue.

```bash
git diff --check
git status --short
git diff --name-only HEAD
```

Expected: clean diff check and only File Map paths.

- [ ] **Step 4: Commit once and hand off**

Use a focused English commit such as:

```bash
git commit -m "fix: complete iconloader runtime closure"
```

Worker must never push. End with the required terminal-final `HANDOFF:` block.
