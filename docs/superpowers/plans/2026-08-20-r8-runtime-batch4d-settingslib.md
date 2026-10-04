# R8 Runtime Batch 4D — SettingsLib Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the missing SettingsLib program and resource closure so fresh release R8 moves exactly from 81 missing refs to 7 while debug assembly remains successful.

**Architecture:** Keep the existing main SettingsLib and SettingsTheme AAR boundaries. Add owning Soong Kotlin outputs to the correct AAR, represent each of the ten newly reachable resource namespaces as its own byte-exact res-only AAR, and expose those AARs through the existing ADR 0005 transitive-POM mechanism.

**Tech Stack:** Python 3 deterministic ZIP packaging, `unittest`, AOSP Soong javac/kotlin/R.txt outputs, local Maven AAR repository, Gradle 9.5, AGP 9.3.1, R8.

**Spec:** `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md`

## Global Constraints

- User-approved versions are exact: `SettingsLib:1.0.1`, `SettingsLibSettingsTheme:1.0.1`, and each new per-target AAR `1.0.0`.
- Do not change any other dependency version or module boundary.
- Do not modify `SystemUI-*/src/**`, `SystemUI-*/res*/**`, AOSP source files, or any resource bytes.
- Do not add stubs, R-only JARs, keep rules, dontwarn rules, suppressions, source exclusions, or disabled checks.
- SettingsTheme code belongs only to `SettingsLibSettingsTheme.aar`; it must not enter the main AAR.
- New resource artifacts are res-only; their classes.jar remains empty and AGP generates R from original manifest/R.txt/resources.
- `libs/SettingsLib-full.jar` and its `compileOnly` reference must be removed after main AAR gains the owning Kotlin output.
- All Gradle builds are serialized. Use `-Dorg.gradle.workers.max=4`; every piped Gradle command uses `set -o pipefail`, `tee`, and a saved real exit code.
- Any debug failure, SettingsLib class overlap, resource-byte mismatch, or R8 result other than exact 81→7 with zero additions is a REDLINE.

---

## File Map

### Packaging and tests

- Modify `tools/package_aosp_aar.py`: add two owning Kotlin inputs to main SettingsLib, one owning Kotlin input to Theme, and ten res-only target configs.
- Modify `tools/tests/test_package_aosp_aar.py`: test class ownership/union, resource provenance, empty code, deterministic output, and registry membership.
- Modify `tools/install_aar_to_maven.py`: bump two approved versions, register ten artifacts, and expand the main POM dependency list to seventeen AOSP-ordered edges.
- Modify `tools/tests/test_install_aar_to_maven.py`: test exact coordinates, dependency order/count, skeleton child POMs, and installation registry.

### Build graph and catalog

- Modify `SystemUI-core/build.gradle.kts`: remove only the `SettingsLib-full.jar` comment and `compileOnly` line.
- Modify `gradle/libs.versions.toml`: bump the two approved aliases and register ten `1.0.0` aliases.
- Delete `libs/SettingsLib-full.jar`.

### Generated artifacts

- Replace `libs/aars/SettingsLib.aar` and `libs/aars/SettingsLibSettingsTheme.aar`.
- Create ten `libs/aars/SettingsLib*.aar` files named exactly after their Soong targets.
- Delete `libs/maven/com/android/systemui/SettingsLib/1.0.0/` and create `1.0.1/`.
- Delete `libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0/` and create `1.0.1/`.
- Create the ten new target directories under `libs/maven/com/android/systemui/`: `SettingsLibMainSwitchPreference/1.0.0/`, `SettingsLibAppPreference/1.0.0/`, `SettingsLibBannerMessagePreference/1.0.0/`, `SettingsLibBarChartPreference/1.0.0/`, `SettingsLibButtonPreference/1.0.0/`, `SettingsLibFooterPreference/1.0.0/`, `SettingsLibIllustrationPreference/1.0.0/`, `SettingsLibSliderPreference/1.0.0/`, `SettingsLibUsageProgressBarPreference/1.0.0/`, and `SettingsLibSettingsSpinner/1.0.0/`.

### Evidence

- Modify `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md`: append only real command output, counts, hashes, exit codes, and final delta.

---

### Task 1: Capture the Fresh 81-Ref Baseline

**Files:**
- Read: `app/build/outputs/mapping/release/missing_rules.txt`
- Write outside repo: `/tmp/task040-r8-before.log`, `/tmp/task040-r8-before.status`, `/tmp/task040-missing-before.txt`, `/tmp/task040-settingslib-before.txt`

**Interfaces:**
- Consumes: main at the plan commit, before implementation changes.
- Produces: an immutable pre-change set of 81 missing refs and the exact 74 SettingsLib targets used by Tasks 4 and 5.

- [ ] **Step 1: Run a fresh pre-change R8 build**

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task040-r8-before.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task040-r8-before.status
test "$status" -eq 1
```

Expected: Gradle exits 1 because the known closure remains incomplete; the failure reaches R8 missing-reference diagnostics rather than an earlier task.

- [ ] **Step 2: Normalize and assert the baseline**

```bash
python3 - <<'PY'
from pathlib import Path
import re
src = Path('app/build/outputs/mapping/release/missing_rules.txt')
refs = sorted({m.group(1) for line in src.read_text().splitlines()
               if (m := re.fullmatch(r'-dontwarn (\S+)', line.strip()))})
settings = [x for x in refs if x.startswith('com.android.settingslib.')]
assert len(refs) == 81, len(refs)
assert len(settings) == 74, len(settings)
assert 'com.android.aconfig.annotations.AssumeTrueForR8' in refs
Path('/tmp/task040-missing-before.txt').write_text('\n'.join(refs) + '\n')
Path('/tmp/task040-settingslib-before.txt').write_text('\n'.join(settings) + '\n')
print(f'BASELINE={len(refs)} SETTINGSLIB={len(settings)} OTHER={len(refs)-len(settings)}')
PY
```

Expected: `BASELINE=81 SETTINGSLIB=74 OTHER=7`.

---

### Task 2: Package the Program-Class Owners Test-First

**Files:**
- Modify: `tools/tests/test_package_aosp_aar.py`
- Modify: `tools/package_aosp_aar.py`
- Replace: `libs/aars/SettingsLib.aar`
- Replace: `libs/aars/SettingsLibSettingsTheme.aar`

**Interfaces:**
- Consumes: current `_discover_settingslib_code_jars()` javac closure and owning Soong Kotlin JARs.
- Produces: main AAR with exactly 1153 classes and Theme AAR with exactly 15 disjoint classes.

- [ ] **Step 1: Write failing program-closure tests**

Add tests that assert these exact code inputs:

```python
MAIN_KOTLIN = (
    paar.SOONG_DIR
    / 'frameworks/base/packages/SettingsLib/SettingsLib/android_common/kotlin/SettingsLib.jar'
)
DEVICE_KOTLIN = (
    paar.SOONG_DIR
    / 'frameworks/base/packages/SettingsLib/DeviceStateRotationLock/'
      'SettingsLibDeviceStateRotationLock/android_common/kotlin/'
      'SettingsLibDeviceStateRotationLock.jar'
)
THEME_KOTLIN = (
    paar.SOONG_DIR
    / 'frameworks/base/packages/SettingsLib/SettingsTheme/'
      'SettingsLibSettingsTheme/android_common/kotlin/SettingsLibSettingsTheme.jar'
)
```

The tests must mechanically read class bytes from every configured code JAR after applying the packager's R-class exclusion and assert:

- main configured inputs are the existing javac discovery followed by `MAIN_KOTLIN` and `DEVICE_KOTLIN`;
- the input class sets are pairwise disjoint and their union has exactly 1153 entries;
- built main classes.jar exactly equals that union, including class bytes;
- `RestrictedPreferenceHelperProvider.class` and `PosturesHelper.class` are present;
- `GroupSectionDividerMixin.class` and `SettingsThemeHelper.class` are absent from main;
- Theme config code is exactly `[THEME_KOTLIN]`;
- Theme classes.jar exactly equals the 15-class source JAR and contains both Theme target classes;
- main and Theme classes.jar class sets are disjoint;
- each artifact rebuilt twice is byte-identical;
- main/Theme res, manifest, and R.txt provenance tests remain green.

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestArtifactConfigs.test_settingslib_program_code_inputs \
  tools.tests.test_package_aosp_aar.TestSettingsLibProgramClosure \
  tools.tests.test_package_aosp_aar.TestSettingsLibSettingsThemeProvenance -v
```

Expected: failures show missing main/device/theme Kotlin inputs, main 780 rather than 1153 classes, and Theme 0 rather than 15 classes. Existing resource provenance assertions remain green.

- [ ] **Step 3: Implement the minimal owner-correct configuration**

In `CONFIGS['SettingsLib']['code']`, keep `_discover_settingslib_code_jars()` and append only:

```python
[
    SOONG_DIR / 'frameworks/base/packages/SettingsLib/SettingsLib/android_common/kotlin/SettingsLib.jar',
    SOONG_DIR / 'frameworks/base/packages/SettingsLib/DeviceStateRotationLock/'
                'SettingsLibDeviceStateRotationLock/android_common/kotlin/'
                'SettingsLibDeviceStateRotationLock.jar',
]
```

Set `CONFIGS['SettingsLibSettingsTheme']['code']` to only:

```python
[
    SOONG_DIR / 'frameworks/base/packages/SettingsLib/SettingsTheme/'
                'SettingsLibSettingsTheme/android_common/kotlin/'
                'SettingsLibSettingsTheme.jar',
]
```

Update nearby comments to state the true owners. Do not add recursive Kotlin discovery and do not include Theme in main.

- [ ] **Step 4: Rebuild both AARs and verify GREEN**

```bash
python3 tools/package_aosp_aar.py SettingsLib
python3 tools/package_aosp_aar.py SettingsLibSettingsTheme
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestArtifactConfigs.test_settingslib_program_code_inputs \
  tools.tests.test_package_aosp_aar.TestSettingsLibProgramClosure \
  tools.tests.test_package_aosp_aar.TestSettingsLibSettingsThemeProvenance -v
```

Expected: all focused tests pass; main is 1153 exact classes, Theme is 15 exact classes, overlap is zero.

- [ ] **Step 5: Commit the program packaging unit**

```bash
git add tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py \
  libs/aars/SettingsLib.aar libs/aars/SettingsLibSettingsTheme.aar
git commit -m "build: complete SettingsLib program AAR closure"
```

---

### Task 3: Add the Ten Real Resource AARs Test-First

**Files:**
- Modify: `tools/tests/test_package_aosp_aar.py`
- Modify: `tools/package_aosp_aar.py`
- Create: `libs/aars/SettingsLibMainSwitchPreference.aar`
- Create: `libs/aars/SettingsLibAppPreference.aar`
- Create: `libs/aars/SettingsLibBannerMessagePreference.aar`
- Create: `libs/aars/SettingsLibBarChartPreference.aar`
- Create: `libs/aars/SettingsLibButtonPreference.aar`
- Create: `libs/aars/SettingsLibFooterPreference.aar`
- Create: `libs/aars/SettingsLibIllustrationPreference.aar`
- Create: `libs/aars/SettingsLibSliderPreference.aar`
- Create: `libs/aars/SettingsLibUsageProgressBarPreference.aar`
- Create: `libs/aars/SettingsLibSettingsSpinner.aar`

**Interfaces:**
- Consumes: each owning AOSP res directory, AndroidManifest.xml, and Soong R.txt.
- Produces: ten deterministic res-only AARs with independent namespaces and 346 byte-exact resource files in total.

- [ ] **Step 1: Write failing registry and provenance tests**

Use this exact mapping in tests and implementation:

```python
NEW_RESOURCE_TARGETS = {
    'SettingsLibMainSwitchPreference': 'MainSwitchPreference',
    'SettingsLibAppPreference': 'AppPreference',
    'SettingsLibBannerMessagePreference': 'BannerMessagePreference',
    'SettingsLibBarChartPreference': 'BarChartPreference',
    'SettingsLibButtonPreference': 'ButtonPreference',
    'SettingsLibFooterPreference': 'FooterPreference',
    'SettingsLibIllustrationPreference': 'IllustrationPreference',
    'SettingsLibSliderPreference': 'SliderPreference',
    'SettingsLibUsageProgressBarPreference': 'UsageProgressBarPreference',
    'SettingsLibSettingsSpinner': 'SettingsSpinner',
}
```

For every mapping entry assert:

- config `code == []`;
- config res is exactly the owning AOSP `res` directory;
- manifest ends in the owning `AndroidManifest.xml`;
- R.txt equals `paar.SOONG_DIR / 'frameworks/base/packages/SettingsLib' / subdir / target / 'android_common/R.txt'`;
- output equals `f'libs/aars/{target}.aar'`;
- built `res/**` names and bytes equal the AOSP source tree;
- classes.jar has no class entries;
- manifest and R.txt bytes equal the configured source files;
- two builds are byte-identical.

Also assert the ten source trees have counts `22,91,96,6,23,91,6,5,1,5`, totaling 346, and `CONFIGS` has exactly 29 artifacts after expansion.

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestArtifactConfigs.test_settingslib_ten_new_resource_configs \
  tools.tests.test_package_aosp_aar.TestSettingsLibNewResourceProvenance -v
```

Expected: failures are missing config keys/artifacts; source-side count checks pass.

- [ ] **Step 3: Add ten declarative res-only configs**

Add the ten configs adjacent to the existing seven ADR 0005 target configs. Each config contains only `code: []`, one owning res directory, owning manifest, owning R.txt, and the exact output path. Do not copy resource files into the repository outside generated AARs.

- [ ] **Step 4: Build all ten AARs and verify GREEN**

```bash
for target in \
  SettingsLibMainSwitchPreference SettingsLibAppPreference \
  SettingsLibBannerMessagePreference SettingsLibBarChartPreference \
  SettingsLibButtonPreference SettingsLibFooterPreference \
  SettingsLibIllustrationPreference SettingsLibSliderPreference \
  SettingsLibUsageProgressBarPreference SettingsLibSettingsSpinner
do
  python3 tools/package_aosp_aar.py "$target" || exit 1
done
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestArtifactConfigs.test_settingslib_ten_new_resource_configs \
  tools.tests.test_package_aosp_aar.TestSettingsLibNewResourceProvenance -v
```

Expected: all focused tests pass, all ten AARs exist, total resource files are 346, and all classes.jar files are empty.

- [ ] **Step 5: Commit the resource packaging unit**

```bash
git add tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py \
  libs/aars/SettingsLibMainSwitchPreference.aar \
  libs/aars/SettingsLibAppPreference.aar \
  libs/aars/SettingsLibBannerMessagePreference.aar \
  libs/aars/SettingsLibBarChartPreference.aar \
  libs/aars/SettingsLibButtonPreference.aar \
  libs/aars/SettingsLibFooterPreference.aar \
  libs/aars/SettingsLibIllustrationPreference.aar \
  libs/aars/SettingsLibSliderPreference.aar \
  libs/aars/SettingsLibUsageProgressBarPreference.aar \
  libs/aars/SettingsLibSettingsSpinner.aar
git commit -m "build: add SettingsLib resource namespace AARs"
```

---

### Task 4: Wire Maven Closure and Retire the Temporary JAR Test-First

**Files:**
- Modify: `tools/tests/test_install_aar_to_maven.py`
- Modify: `tools/install_aar_to_maven.py`
- Modify: `gradle/libs.versions.toml`
- Modify: `SystemUI-core/build.gradle.kts`
- Delete: `libs/SettingsLib-full.jar`
- Replace directory: `libs/maven/com/android/systemui/SettingsLib/1.0.0/` with `1.0.1/`
- Replace directory: `libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0/` with `1.0.1/`
- Create: ten new target directories under `libs/maven/com/android/systemui/`

**Interfaces:**
- Consumes: twelve AARs produced by Tasks 2 and 3.
- Produces: two upgraded coordinates, ten new coordinates, a seventeen-edge main POM, and no temporary full JAR.

- [ ] **Step 1: Write failing Maven registry tests**

Assert:

```python
iam.ARTIFACTS['SettingsLib']['version'] == '1.0.1'
iam.ARTIFACTS['SettingsLibSettingsTheme']['version'] == '1.0.1'
```

Assert every entry in `NEW_RESOURCE_TARGETS` maps to `{'group': 'com.android.systemui', 'name': name, 'version': '1.0.0'}`. Assert the main POM dependency names are exactly this AOSP-filtered order:

```python
[
    'SettingsLibActionButtonsPreference',
    'SettingsLibAdaptiveIcon',
    'SettingsLibAppPreference',
    'SettingsLibBannerMessagePreference',
    'SettingsLibBarChartPreference',
    'SettingsLibButtonPreference',
    'SettingsLibFooterPreference',
    'SettingsLibIllustrationPreference',
    'SettingsLibLayoutPreference',
    'SettingsLibMainSwitchPreference',
    'SettingsLibProgressBar',
    'SettingsLibRestrictedLockUtils',
    'SettingsLibSelectorWithWidgetPreference',
    'SettingsLibSettingsSpinner',
    'SettingsLibSliderPreference',
    'SettingsLibTwoTargetPreference',
    'SettingsLibUsageProgressBarPreference',
]
```

Every dependency uses group `com.android.systemui`, its own name, and version `1.0.0`. All seventeen children and Theme keep skeleton POMs with no `deps` field. `ARTIFACTS` has exactly 27 entries after expansion.

- [ ] **Step 2: Run registry tests and verify RED**

```bash
python3 -m unittest tools.tests.test_install_aar_to_maven.ArtifactRegistryTest -v
```

Expected: failures show old main/Theme versions, seven rather than seventeen dependency edges, and missing new artifact registrations.

- [ ] **Step 3: Implement exact registry and catalog wiring**

- Replace `_SETTINGS_LIB_CLOSURE_DEPS` with the exact seventeen-name order above.
- Change only main and Theme registry versions from `1.0.0` to `1.0.1`.
- Register the ten new artifacts at version `1.0.0`.
- In `gradle/libs.versions.toml`, change only the main and Theme aliases to `1.0.1` and add ten aliases at `1.0.0`; retain the existing seven aliases.
- In `SystemUI-core/build.gradle.kts`, remove only the two-line `SettingsLib-full.jar` comment/dependency block.
- Delete `libs/SettingsLib-full.jar`.

- [ ] **Step 4: Install only changed/new artifacts**

```bash
rm -rf \
  libs/maven/com/android/systemui/SettingsLib/1.0.0 \
  libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0
python3 tools/install_aar_to_maven.py \
  SettingsLib SettingsLibSettingsTheme \
  SettingsLibMainSwitchPreference SettingsLibAppPreference \
  SettingsLibBannerMessagePreference SettingsLibBarChartPreference \
  SettingsLibButtonPreference SettingsLibFooterPreference \
  SettingsLibIllustrationPreference SettingsLibSliderPreference \
  SettingsLibUsageProgressBarPreference SettingsLibSettingsSpinner
```

Expected: main/Theme are installed only under `1.0.1`; ten new targets are installed under `1.0.0`.

- [ ] **Step 5: Run Maven tests and static retirement checks**

```bash
python3 -m unittest tools.tests.test_install_aar_to_maven -v
test ! -e libs/SettingsLib-full.jar
test ! -d libs/maven/com/android/systemui/SettingsLib/1.0.0
test ! -d libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0
! rg -n 'SettingsLib-full\.jar' --glob '!docs/**' .
```

Expected: tests pass, both old directories and the temporary JAR are absent, and no non-document functional reference remains.

- [ ] **Step 6: Commit the delivery unit**

```bash
git add tools/install_aar_to_maven.py tools/tests/test_install_aar_to_maven.py \
  gradle/libs.versions.toml SystemUI-core/build.gradle.kts \
  libs/SettingsLib-full.jar libs/maven
git commit -m "build: deliver SettingsLib closure through Maven AARs"
```

---

### Task 5: Verify Determinism, Debug APK, and Exact R8 Delta

**Files:**
- Modify: `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md`
- Write outside repo: `/tmp/task040-*` evidence files

**Interfaces:**
- Consumes: final implementation from Tasks 2–4 and the 74-target baseline from Task 1.
- Produces: hard-gate evidence for review and a truthful issue ledger.

- [ ] **Step 1: Run focused and full Python tests**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v \
  2>&1 | tee /tmp/task040-tests.log
test ${PIPESTATUS[0]} -eq 0
```

Expected: all 179 baseline tests plus newly added tests pass with final `OK`.

- [ ] **Step 2: Rebuild all twelve AARs twice and compare hashes**

```bash
targets='SettingsLib SettingsLibSettingsTheme SettingsLibMainSwitchPreference SettingsLibAppPreference SettingsLibBannerMessagePreference SettingsLibBarChartPreference SettingsLibButtonPreference SettingsLibFooterPreference SettingsLibIllustrationPreference SettingsLibSliderPreference SettingsLibUsageProgressBarPreference SettingsLibSettingsSpinner'
rm -rf /tmp/task040-aar-first /tmp/task040-aar-second
mkdir -p /tmp/task040-aar-first /tmp/task040-aar-second
for target in $targets; do
  python3 tools/package_aosp_aar.py "$target"
  cp "libs/aars/$target.aar" "/tmp/task040-aar-first/$target.aar"
done
for target in $targets; do
  python3 tools/package_aosp_aar.py "$target"
  cp "libs/aars/$target.aar" "/tmp/task040-aar-second/$target.aar"
done
for target in $targets; do
  cmp "/tmp/task040-aar-first/$target.aar" "/tmp/task040-aar-second/$target.aar" || exit 1
done
sha256sum /tmp/task040-aar-second/*.aar | sort | tee /tmp/task040-aar-sha256.txt
```

Expected: all twelve `cmp` checks exit 0. Re-run the install command from Task 4 afterward so Maven copies match the final deterministic AAR bytes.

- [ ] **Step 3: Run the debug hard gate**

```bash
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task040-debug.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task040-debug.status
test "$status" -eq 0
```

Expected: exit 0 and `BUILD SUCCESSFUL`.

- [ ] **Step 4: Prove all 74 pre-change targets are defined in the debug APK**

```bash
apkanalyzer dex packages --defined-only \
  app/build/outputs/apk/debug/app-debug.apk > /tmp/task040-debug-defined.txt
python3 - <<'PY'
from pathlib import Path
targets = set(Path('/tmp/task040-settingslib-before.txt').read_text().splitlines())
defined = set()
for line in Path('/tmp/task040-debug-defined.txt').read_text(errors='replace').splitlines():
    parts = line.split()
    if len(parts) >= 3 and parts[0] == 'C' and parts[1] == 'd':
        defined.add(parts[-1])
missing = sorted(targets - defined)
assert len(targets) == 74, len(targets)
assert not missing, missing
print(f'TOTAL={len(targets)} DEFINED={len(targets)} MISSING=0')
PY
```

Expected: `TOTAL=74 DEFINED=74 MISSING=0`.

- [ ] **Step 5: Run fresh post-change R8 and assert exact 81→7**

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task040-r8-after.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task040-r8-after.status
test "$status" -eq 1
python3 - <<'PY'
from pathlib import Path
import re
before = set(Path('/tmp/task040-missing-before.txt').read_text().splitlines())
settings = set(Path('/tmp/task040-settingslib-before.txt').read_text().splitlines())
src = Path('app/build/outputs/mapping/release/missing_rules.txt')
after = {m.group(1) for line in src.read_text().splitlines()
         if (m := re.fullmatch(r'-dontwarn (\S+)', line.strip()))}
removed = before - after
added = after - before
assert len(before) == 81, len(before)
assert len(settings) == 74, len(settings)
assert len(after) == 7, sorted(after)
assert removed == settings, (len(removed), sorted(removed ^ settings))
assert not added, sorted(added)
assert not any(x.startswith('com.android.settingslib.') for x in after), sorted(after)
assert 'com.android.aconfig.annotations.AssumeTrueForR8' in after
Path('/tmp/task040-missing-after.txt').write_text('\n'.join(sorted(after)) + '\n')
print(f'BEFORE={len(before)} AFTER={len(after)} REMOVED={len(removed)} ADDED={len(added)}')
PY
```

Expected: R8 still exits 1 only because seven deferred refs remain; assertion prints `BEFORE=81 AFTER=7 REMOVED=74 ADDED=0`.

- [ ] **Step 6: Record evidence and run hygiene checks**

Append the actual test count, AAR SHA-256 values, class/resource counts, Maven/POM checks, debug exit/time, APK 74/74 result, R8 exit/time, exact delta, and remaining seven refs to the issue document.

```bash
git diff --check
git status --short
git diff --name-only HEAD~3..HEAD
```

Expected: `git diff --check` emits nothing; every changed path is within the worker brief.

- [ ] **Step 7: Commit evidence and produce HANDOFF**

```bash
git add docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md
git commit -m "docs: record SettingsLib closure evidence"
```

The terminal-final report must contain:

```text
HANDOFF:
- done: SettingsLib program and ten real resource AAR closures delivered; temporary full JAR retired
- verified: tests exit 0; twelve AARs deterministic; debug exit 0; APK targets 74/74 defined; R8 81→7 with 74 removed and 0 added
- remaining: seven deferred non-SettingsLib R8 refs
```

Do not push.
