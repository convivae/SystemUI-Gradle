# Task 044 — Narrow `AssumeTrueForR8` Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans and follow the
> repository worker contract. Implement test-first, self-commit, and never push.

**Goal:** Close the sole remaining Release R8 diagnostic with the user-approved, single-FQN,
release-only AGP adapter and establish the first successful minified/shrunk Release APK.

**Architecture:** Keep build/optimizer annotations outside the runtime artifact graph and
SysUISdk. Add one project-owned R8 adapter file whose only active rule suppresses resolution of
the CLASS-retained `AssumeTrueForR8` descriptor, and consume it only from the minified release
build type. Preserve current aconfig runtime behavior by importing no assumption/folding rules.

**Tech Stack:** Kotlin Gradle DSL, AGP 9.3.1, Gradle 9.5, R8, Python 3 `unittest`, Android SDK
`apkanalyzer` and `apksigner`.

**Spec:** `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`

## Global constraints

- The user approved option A only: exact
  `-dontwarn com.android.aconfig.annotations.AssumeTrueForR8`.
- Do not revive rejected Task 042, create S3c, modify SysUISdk, supply the annotation class, or
  import any part of AOSP `aconfig_proguard.flags`.
- Do not modify existing AOSP-owned rule files, source, resources, artifacts, dependencies,
  versions, manifests, or module boundaries.
- No wildcard/package suppression, `keep`, `assumevalues`, `assumenosideeffects`, disabled R8,
  disabled shrinking, source exclusion, or private AGP task hook.
- All Gradle builds are serialized and use `-Dorg.gradle.workers.max=4`. Every piped Gradle command
  uses `set -o pipefail`, `tee`, and records the real Gradle exit code.
- Device installation and runtime smoke testing are not faked; they remain deferred if no compatible
  root/remount system image is available.

## File map

**Create:**

- `app/proguard_gradle.flags`
- `tools/tests/test_gradle_r8_adapter_rules.py`

**Modify:**

- `app/build.gradle.kts`
- `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`
- `docs/CURRENT_STATE.md`

All other repository paths are read-only.

---

## Task 1: Capture the fresh singleton baseline

**Files:**
- Read generated: `app/build/outputs/mapping/release/missing_rules.txt`
- Write outside repo: `/tmp/task044-r8-before.log`, `/tmp/task044-r8-before.status`,
  `/tmp/task044-missing-before.txt`

- [ ] **Step 1: Run fresh pre-change Release R8**

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task044-r8-before.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task044-r8-before.status
test "$status" -eq 1
```

Expected: failure reaches R8 missing-reference diagnostics, not an earlier task.

- [ ] **Step 2: Assert and freeze the exact missing set**

```bash
python3 - <<'PY'
from pathlib import Path
import re
path = Path('app/build/outputs/mapping/release/missing_rules.txt')
refs = sorted({m.group(1) for line in path.read_text().splitlines()
               if (m := re.fullmatch(r'-dontwarn (\S+)', line.strip()))})
expected = ['com.android.aconfig.annotations.AssumeTrueForR8']
assert refs == expected, refs
Path('/tmp/task044-missing-before.txt').write_text('\n'.join(refs) + '\n')
print(f'TASK044_BASELINE_PASS refs={len(refs)} value={refs[0]}')
PY
```

Expected: `TASK044_BASELINE_PASS refs=1` with the exact FQN. Any other result is REDLINE.

---

## Task 2: Pin the adapter contract test-first

**Files:**
- Create: `tools/tests/test_gradle_r8_adapter_rules.py`
- Read: `app/build.gradle.kts`, current `app/*.flags`

- [ ] **Step 1: Write the failing focused test**

Create a `unittest.TestCase` that mechanically asserts:

1. `app/proguard_gradle.flags` exists;
2. after removing comments and blank lines, its active lines equal exactly:
   `['-dontwarn com.android.aconfig.annotations.AssumeTrueForR8']`;
3. the file has no `**`, `-keep`, `-assumevalues`, or `-assumenosideeffects`;
4. the `debug { ... }` segment of `app/build.gradle.kts` does not mention
   `proguard_gradle.flags`;
5. the `release { ... }` segment mentions `"proguard_gradle.flags"` exactly once;
6. no other `app/*.flags` file contains an active rule mentioning `AssumeTrueForR8`.

The test may delimit build-type segments using the stable ordering `debug {` → `release {` →
`// AOSP bp: dxflags`; it must fail clearly if any marker is absent.

- [ ] **Step 2: Observe RED**

```bash
python3 -m unittest tools.tests.test_gradle_r8_adapter_rules -v \
  2>&1 | tee /tmp/task044-test-red.log
status=${PIPESTATUS[0]}
test "$status" -ne 0
grep -F 'proguard_gradle.flags' /tmp/task044-test-red.log
```

Expected: failure because `app/proguard_gradle.flags` is absent. Do not weaken the test.

---

## Task 3: Implement the minimal release-only adapter

**Files:**
- Create: `app/proguard_gradle.flags`
- Modify: `app/build.gradle.kts`

- [ ] **Step 1: Create the adapter file**

Use explanatory comments followed by exactly this one active rule:

```proguard
-dontwarn com.android.aconfig.annotations.AssumeTrueForR8
```

The comments must state that this is a Gradle-native adapter for a CLASS-retained generated aconfig
annotation descriptor, not runtime code and not an assumption/folding rule.

- [ ] **Step 2: Wire only the release build type**

Add `"proguard_gradle.flags"` to the existing `release.proguardFiles(...)` list immediately after
`"proguard.flags"`. Do not touch the debug list or any existing rule file.

- [ ] **Step 3: Observe GREEN and run all Python tests**

```bash
python3 -m unittest tools.tests.test_gradle_r8_adapter_rules -v
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v \
  2>&1 | tee /tmp/task044-python-tests.log
```

Expected: focused and full suites exit 0.

- [ ] **Step 4: Commit the test and implementation unit**

```bash
git add app/proguard_gradle.flags app/build.gradle.kts \
  tools/tests/test_gradle_r8_adapter_rules.py
git commit -m "build: add narrow aconfig R8 adapter"
```

---

## Task 4: Preserve the debug hard gate

**Files:** generated build outputs only.

- [ ] **Step 1: Run duplicate-class and debug assembly gates**

```bash
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task044-debug.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task044-debug.status
test "$status" -eq 0
grep -F 'BUILD SUCCESSFUL' /tmp/task044-debug.log
```

Expected: real Gradle exit 0. This confirms no debug behavior or dependency graph was changed.

---

## Task 5: Prove Release R8 closure and unchanged optimization semantics

**Files:** generated `app/build/outputs/mapping/release/**` only.

- [ ] **Step 1: Run fresh Release R8**

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task044-r8-after.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task044-r8-after.status
test "$status" -eq 0
grep -F 'BUILD SUCCESSFUL' /tmp/task044-r8-after.log
```

Expected: real Gradle exit 0.

- [ ] **Step 2: Assert zero generated missing refs**

```bash
python3 - <<'PY'
from pathlib import Path
import re
path = Path('app/build/outputs/mapping/release/missing_rules.txt')
refs = [] if not path.exists() else sorted({
    m.group(1) for line in path.read_text().splitlines()
    if (m := re.fullmatch(r'-dontwarn (\S+)', line.strip()))
})
assert refs == [], refs
print('TASK044_R8_CLOSURE_PASS refs=0')
PY
```

- [ ] **Step 3: Inspect the effective R8 configuration**

```bash
python3 - <<'PY'
from pathlib import Path
fqn = 'com.android.aconfig.annotations.AssumeTrueForR8'
path = Path('app/build/outputs/mapping/release/configuration.txt')
assert path.is_file(), path
lines = [line.strip() for line in path.read_text(errors='replace').splitlines()]
matching = [line for line in lines if fqn in line]
assert matching == [f'-dontwarn {fqn}'], matching
print('TASK044_EFFECTIVE_RULE_PASS exact_dontwarn=1 assume_rules=0')
PY
```

Expected: one exact `dontwarn`, no `assumevalues`/`assumenosideeffects` treatment for the FQN.
If AGP's emitted configuration format splits the directive over multiple lines, stop and report the
observed format rather than weakening semantic checks without approval.

---

## Task 6: Build, inspect, and verify the Release APK

**Files:** generated Release outputs only.

- [ ] **Step 1: Assemble the full shrunk Release**

```bash
set -o pipefail
./gradlew :app:assembleRelease --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task044-release.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task044-release.status
test "$status" -eq 0
grep -F 'BUILD SUCCESSFUL' /tmp/task044-release.log
```

Expected: `minifyReleaseWithR8`, resource shrinking, packaging, and signing complete successfully.

- [ ] **Step 2: Locate and inventory the APK**

```bash
apk=app/build/outputs/apk/release/app-release.apk
test -s "$apk"
sha256sum "$apk" | tee /tmp/task044-release-apk.sha256
unzip -t "$apk" > /tmp/task044-release-apk-ziptest.txt
```

- [ ] **Step 3: Prove the annotation class is not packaged**

```bash
apkanalyzer=/home/conv/Android/Sdk/cmdline-tools/latest/bin/apkanalyzer
"$apkanalyzer" dex packages "$apk" > /tmp/task044-release-packages.txt
! grep -F 'com.android.aconfig.annotations.AssumeTrueForR8' \
  /tmp/task044-release-packages.txt
printf '%s\n' 'TASK044_APK_CLASS_PASS packaged=0'
```

- [ ] **Step 4: Verify APK signatures, including V2**

```bash
apksigner=/home/conv/Android/Sdk/build-tools/37.0.0/apksigner
"$apksigner" verify --verbose --print-certs "$apk" \
  | tee /tmp/task044-apksigner.txt
grep -F 'Verified using v2 scheme (APK Signature Scheme v2): true' \
  /tmp/task044-apksigner.txt
```

Expected: signature verification exits 0 and V2 is true.

---

## Task 7: Record truthful state and finish

**Files:**
- Modify: `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`
- Modify: `docs/CURRENT_STATE.md`

- [ ] **Step 1: Record evidence**

Append the actual baseline and post-change exits, Python test count, debug result, R8 closure,
effective-rule result, Release result, APK size/SHA-256, annotation absence, signature result, and
explicitly state that device validation was not run unless a compatible device was truly used.
Update `docs/CURRENT_STATE.md` narrowly so it no longer says Release R8 is blocked by one ref and
truthfully distinguishes build completion from deferred device/runtime validation.

- [ ] **Step 2: Run static final gates**

```bash
python3 -m unittest tools.tests.test_gradle_r8_adapter_rules -v
git diff --check
git status --short
```

Inspect all changed paths. They must be a subset of the File map.

- [ ] **Step 3: Commit evidence**

```bash
git add docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md docs/CURRENT_STATE.md
git commit -m "docs: record Release R8 closure"
```

- [ ] **Step 4: Final report**

```text
HANDOFF:
- done: exact release-only AssumeTrueForR8 adapter and truthful state update
- verified: focused RED/GREEN, full Python tests, debug gate, R8 1→0, full shrunk Release, APK class absence, V2 signature
- remaining: compatible-device install/SystemUI restart/runtime smoke test; or exact blocker
```

## REDLINE conditions

Stop immediately and do not broaden scope if any occurs:

- fresh pre-change set is not exactly the singleton `AssumeTrueForR8` ref;
- focused RED is not caused by the missing approved adapter contract;
- another missing ref appears or post-change R8 still fails;
- effective configuration contains an `AssumeTrueForR8` keep/assumption rule or more than one
  treatment;
- debug fails, duplicate classes appear, resource shrinking fails, annotation class is packaged, or
  signature verification fails;
- resolution would require another rule, wildcard, class/JAR/AAR, SysUISdk, dependency, source,
  resource, artifact, version, manifest, module-boundary, or existing AOSP-rule-file change;
- a required tool/output has a different format that would require weakening an acceptance check;
- all compliant attempts fail.
