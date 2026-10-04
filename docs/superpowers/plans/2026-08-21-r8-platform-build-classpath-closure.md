# R8 Platform/Build Library Classpath Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a declarative, source-proven SysUISdk library-class bridge that moves fresh release R8 exactly from 7 missing refs to 1 while preserving debug assembly and keeping every bridged class out of the APK.

**Architecture:** A new exact-entry Python patcher reads six approved class slices from four real AOSP artifacts and injects exactly 35 source-identical class entries into both SysUISdk library JARs. `tools/build_sysuisdk.py` owns this as stage `S3b`; live SDK mutation remains staging-only plus the existing guarded `--apply` path.

**Tech Stack:** Python 3 stdlib (`dataclasses`, `zipfile`, `hashlib`, `unittest`), AOSP Soong javac artifacts, SysUISdk, Gradle 9.5, AGP 9.3.1, R8, `apkanalyzer`.

**Spec:** `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`

## Global Constraints

- The pre-change missing-ref set must be exactly the documented 7 refs.
- Task 041 owns exactly six refs; `com.android.aconfig.annotations.AssumeTrueForR8` remains untouched for Task 042.
- Inject exactly 35 allowlisted class entries into each of `android.jar` and `core-for-system-modules.jar`; never inject a whole source JAR implicitly.
- Real source artifacts only; no hand-written Java/Kotlin classes, generated stubs, synthetic resource files, or copied framework source.
- No `implementation`, `compileOnly`, dependency/version/module, ProGuard, keep, or dontwarn changes.
- No `SystemUI-*/src/**`, `SystemUI-*/res*/**`, app source/resource, or AOSP source changes.
- The only live-SDK mutation is `python3 tools/build_sysuisdk.py --apply --source <staging>` after a complete staging build.
- Existing target entries are never overwritten. A byte mismatch against the approved source is a REDLINE, not a repair opportunity.
- All Gradle builds are serialized and use `-Dorg.gradle.workers.max=4`; piped Gradle commands use `set -o pipefail`, `tee`, and saved real exit status.
- `:app:assembleDebug` must succeed. Fresh R8 must be exact 7→1, removed=6, added=0, remaining only `AssumeTrueForR8`.

---

## File Map

### New exact-entry patch module

- Create `tools/patch_sdk_r8_library_classes.py`: immutable class-slice declarations, exact source inventory validation, deterministic ZIP rewrite, collision rejection, scoped backup, idempotent patching.
- Create `tools/tests/test_patch_sdk_r8_library_classes.py`: fixture-only tests for all 35 entries, scope, source-byte identity, target collision rejection, backup, idempotency, and deterministic output.

### SysUISdk pipeline integration

- Modify `tools/build_sysuisdk.py`: add source defaults/CLI flags, `S3b`, stage ordering, full-pipeline wiring, output, and docstring.
- Modify `tools/tests/test_build_sysuisdk.py`: add four source fixtures, `S3b` tests for both target JARs, exact count/provenance, full-pipeline verification, and apply-path tests without touching the real SDK.

### Evidence and task tracking

- Modify `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`: append real red/green, staging/apply, debug/APK, and R8 evidence.
- Modify `docs/orchestration/tasks/041-r8-platform-build-classpath-closure.md`: check completed steps and record commit/evidence references.

### Explicitly outside the worker scope

- The architect may separately create the ADR 0006 SysUISdk R8 library-class bridge record and add its factual index link to `AGENTS.md` only after explicit H.6 authorization. The worker must not touch either path.

---

### Task 1: Capture the Seven-Ref Baseline and Pin Source Inventories

**Files:**
- Read: `app/build/outputs/mapping/release/missing_rules.txt`
- Read: four approved source JARs
- Write outside repo: `/tmp/task041-*`
- Modify: `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`

**Interfaces:**
- Consumes: Task 040 main state and current live SysUISdk.
- Produces: immutable `/tmp/task041-missing-before.txt`, source-entry manifests, and hashes used by later delta checks.

- [ ] **Step 1: Run a fresh serialized R8 baseline**

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task041-r8-before.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task041-r8-before.status
test "$status" -eq 1
```

Expected: real Gradle exit 1 at R8 missing-reference analysis.

- [ ] **Step 2: Normalize and assert the exact baseline**

```bash
python3 - <<'PY'
from pathlib import Path
import re
expected = {
    'android.compat.annotation.UnsupportedAppUsage',
    'com.android.aconfig.annotations.AconfigFlagAccessor',
    'com.android.aconfig.annotations.AssumeTrueForR8',
    'com.android.tools.r8.keepanno.annotations.UsesReflection',
    'libcore.io.IoUtils',
    'libcore.util.NativeAllocationRegistry',
    'org.apache.harmony.dalvik.ddmc.ChunkHandler',
}
src = Path('app/build/outputs/mapping/release/missing_rules.txt')
actual = {m.group(1) for line in src.read_text().splitlines()
          if (m := re.fullmatch(r'-dontwarn (\S+)', line.strip()))}
assert actual == expected, (sorted(expected - actual), sorted(actual - expected))
Path('/tmp/task041-missing-before.txt').write_text(
    '\n'.join(sorted(actual)) + '\n', encoding='utf-8')
print('BASELINE=7')
PY
```

Expected: `BASELINE=7`.

- [ ] **Step 3: Record the approved source artifacts and exact inventories**

Use these inputs:

```text
core-libart:
/home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar

unsupportedappusage:
/home/conv/myspace/aosp/out/soong/.intermediates/tools/platform-compat/java/android/compat/annotation/unsupportedappusage/linux_glibc_common/javac/unsupportedappusage.jar

aconfig annotations:
/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/libs/modules-utils/java/aconfig-annotations-lib/linux_glibc_common/javac/aconfig-annotations-lib.jar

keepanno annotations:
libs/keepanno-annotations.jar
```

Assert counts `2 + 4 + 4 + 2 + 1 + 22 = 35`, write sorted paths to
`/tmp/task041-approved-entries.txt`, and write `sha256sum` output for all four source JARs to
`/tmp/task041-source-sha256.txt`.

Expected approved entries:

```python
IO_UTILS = (
    'libcore/io/IoUtils.class',
    'libcore/io/IoUtils$FileReader.class',
)
NATIVE_ALLOCATION = (
    'libcore/util/NativeAllocationRegistry.class',
    'libcore/util/NativeAllocationRegistry$CleanerRunner.class',
    'libcore/util/NativeAllocationRegistry$CleanerThunk.class',
    'libcore/util/NativeAllocationRegistry$Metrics.class',
)
DDMC = (
    'org/apache/harmony/dalvik/ddmc/Chunk.class',
    'org/apache/harmony/dalvik/ddmc/ChunkHandler.class',
    'org/apache/harmony/dalvik/ddmc/DdmServer.class',
    'org/apache/harmony/dalvik/ddmc/DdmVmInternal.class',
)
UNSUPPORTED = (
    'android/compat/annotation/UnsupportedAppUsage.class',
    'android/compat/annotation/UnsupportedAppUsage$Container.class',
)
ACONFIG = ('com/android/aconfig/annotations/AconfigFlagAccessor.class',)
KEEPANNO = (
    'com/android/tools/r8/keepanno/annotations/AnnotationPattern.class',
    'com/android/tools/r8/keepanno/annotations/CheckOptimizedOut.class',
    'com/android/tools/r8/keepanno/annotations/CheckRemoved.class',
    'com/android/tools/r8/keepanno/annotations/ClassAccessFlags.class',
    'com/android/tools/r8/keepanno/annotations/ClassNamePattern.class',
    'com/android/tools/r8/keepanno/annotations/FieldAccessFlags.class',
    'com/android/tools/r8/keepanno/annotations/InstanceOfPattern.class',
    'com/android/tools/r8/keepanno/annotations/KeepBinding.class',
    'com/android/tools/r8/keepanno/annotations/KeepCondition.class',
    'com/android/tools/r8/keepanno/annotations/KeepConstraint.class',
    'com/android/tools/r8/keepanno/annotations/KeepEdge.class',
    'com/android/tools/r8/keepanno/annotations/KeepForApi.class',
    'com/android/tools/r8/keepanno/annotations/KeepItemKind.class',
    'com/android/tools/r8/keepanno/annotations/KeepOption.class',
    'com/android/tools/r8/keepanno/annotations/KeepTarget.class',
    'com/android/tools/r8/keepanno/annotations/MemberAccessFlags.class',
    'com/android/tools/r8/keepanno/annotations/MethodAccessFlags.class',
    'com/android/tools/r8/keepanno/annotations/StringPattern.class',
    'com/android/tools/r8/keepanno/annotations/TypePattern.class',
    'com/android/tools/r8/keepanno/annotations/UsedByNative.class',
    'com/android/tools/r8/keepanno/annotations/UsedByReflection.class',
    'com/android/tools/r8/keepanno/annotations/UsesReflection.class',
)
```

No non-class or out-of-package keepanno entry is allowed.

- [ ] **Step 4: Append only real baseline/source evidence to the issue**

Record the Gradle status, exact seven refs, four source hashes, six slice counts, and total 35.
Do not claim post-change success.

---

### Task 2: Build the Exact-Entry Patcher Test-First

**Files:**
- Create: `tools/tests/test_patch_sdk_r8_library_classes.py`
- Create: `tools/patch_sdk_r8_library_classes.py`

**Interfaces:**
- Produces:
  - `ClassSlice(label: str, source_jar: Path, entries: tuple[str, ...])`
  - `task041_slices(core_libart_jar, unsupported_jar, aconfig_jar, keepanno_jar) -> tuple[ClassSlice, ...]`
  - `validate_target(target: Path, slices: tuple[ClassSlice, ...]) -> dict`
  - `patch_target(target: Path, slices: tuple[ClassSlice, ...], backup_suffix: str = '.bak-prer8lib') -> dict`
- `validate_target` is read-only and returns sorted `missing`, `already`, `source_by_entry`; `patch_target` revalidates and returns `injected`, `already`, `backup`, `source_by_entry`.

- [ ] **Step 1: Write failing inventory tests**

Tests must assert:

```python
slices = module.task041_slices(core, unsupported, aconfig, keepanno)
entries = [entry for item in slices for entry in item.entries]
self.assertEqual(len(entries), 35)
self.assertEqual(len(set(entries)), 35)
self.assertNotIn(
    'com/android/aconfig/annotations/AssumeTrueForR8.class', entries)
```

Also assert exact group counts `2,4,4,2,1,22`; each declared entry exists in its assigned
source; keepanno contains exactly the approved 22-class set; and no source package expansion
occurs at runtime.

- [ ] **Step 2: Write failing mutation-safety tests**

Cover all of these behaviors with temporary fixture JARs:

1. target missing all 35 → exactly 35 source-identical bytes injected;
2. target already has source-identical entry → reported in `already`, not rewritten;
3. target has same path with different bytes → `RuntimeError` containing `collision`;
4. undeclared source classes are never injected;
5. duplicate class paths across slices are rejected before mutation;
6. missing declared source entry is rejected before mutation;
7. first mutation creates `<target>.bak-prer8lib` preserving pre-mutation bytes;
8. an existing backup is never overwritten;
9. second run is a byte-for-byte no-op with no new backup;
10. two independent identical target/source inputs produce byte-identical patched JARs;
11. unrelated target entries and metadata remain present with identical uncompressed bytes;
12. missing target/source files raise `FileNotFoundError`.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
python3 -m unittest tools.tests.test_patch_sdk_r8_library_classes -v
```

Expected: import/module failure because the implementation file does not exist.

- [ ] **Step 4: Implement the minimal deterministic patcher**

Use `zipfile` only. Validate every slice and collision before creating a backup or temporary
output. Rebuild to a sibling temporary JAR, preserving each existing non-directory
`ZipInfo`/bytes in original order, then append missing entries sorted by archive path using
the approved source entry's `ZipInfo` and bytes. Replace atomically with `os.replace`.

Do not invoke `jar`, extract source trees into the repository, infer package contents from a
prefix, or overwrite any existing class path.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
python3 -m unittest tools.tests.test_patch_sdk_r8_library_classes -v
```

Expected: all patcher tests pass.

- [ ] **Step 6: Commit the patcher unit**

```bash
git add tools/patch_sdk_r8_library_classes.py \
  tools/tests/test_patch_sdk_r8_library_classes.py
git commit -m "build: add exact SysUISdk library class patcher"
```

---

### Task 3: Integrate Declarative SysUISdk Stage S3b Test-First

**Files:**
- Modify: `tools/tests/test_build_sysuisdk.py`
- Modify: `tools/build_sysuisdk.py`

**Interfaces:**
- Consumes: Task 2's `task041_slices` and `patch_target`.
- Produces:
  - `stage_s3b(target, core_libart_jar, unsupported_jar, aconfig_jar, keepanno_jar) -> None`
  - CLI flags `--unsupportedappusage-jar`, `--aconfig-annotations-jar`, `--keepanno-annotations-jar`
  - `s3b` in `ALL_STAGES` and `_run_stages` after `s3`, before `s4`.

- [ ] **Step 1: Add realistic source fixtures**

Extend test fixtures with four source JARs carrying all 35 approved fake fixture bytes plus
unrelated out-of-scope entries. Fixture `.class` bytes are test data only; they are never
written to product artifacts or the live SDK.

- [ ] **Step 2: Write failing S3b tests**

Assert:

1. `stage_s3b` injects exactly 35 entries into both target JARs;
2. bytes for each entry equal its assigned source fixture;
3. no unrelated source entry is injected;
4. both target backups use `.bak-prer8lib` and preserve pre-S3b bytes;
5. rerun is byte-for-byte no-op;
6. a target/source byte collision raises before either target JAR is partially changed;
7. `android.jar` manifest remains `ANDROID_MANIFEST_BYTES`;
8. `ALL_STAGES` and `_run_stages` place `s3b` after `s3` and before `s4`;
9. the default CLI stage list includes `s3b` while `s4` remains explicit;
10. two independent `s0,s1,s2,s3,s3b,s4` fixture builds have equal inventories;
11. strict S5 passes when the live fixture was built through the same stages;
12. an S3-only live fixture reports exactly 35 extras per JAR before apply-equivalent sync.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
python3 -m unittest \
  tools.tests.test_build_sysuisdk.StageS3bTest \
  tools.tests.test_build_sysuisdk.FullPipelineTest -v
```

Expected: failures show missing `stage_s3b`, source defaults, and stage registration.

- [ ] **Step 4: Implement S3b and CLI wiring**

Add exact defaults for the three new AOSP/tracked artifacts, import the Task 2 module, patch
both `_dalvik.TARGET_JARS`, and normalize the audited android manifest after patching.

Update:

```python
ALL_STAGES = ('s0', 's1', 's2', 's3', 's3b', 's4')
```

Default CLI stages become `s0,s1,s2,s3,s3b`; help text continues to require explicit `s4`
for the framework-resource overlay. `_run_stages` must invoke S3b between S3 and S4.

Before mutating either target, call `validate_target` for both target JARs; only after both
read-only validations succeed may the stage call `patch_target` for either one. This prevents
a source/collision failure from leaving one target patched and the other untouched.

- [ ] **Step 5: Run focused and full SysUISdk tests**

```bash
python3 -m unittest \
  tools.tests.test_patch_sdk_r8_library_classes \
  tools.tests.test_build_sysuisdk -v
```

Expected: all tests pass; the real live SDK is untouched by tests.

- [ ] **Step 6: Commit the pipeline integration**

```bash
git add tools/build_sysuisdk.py tools/tests/test_build_sysuisdk.py
git commit -m "build: add SysUISdk R8 library bridge stage"
```

---

### Task 4: Rebuild, Prove Determinism, and Apply Through the Guarded Path

**Files:**
- Modify: `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`
- Write outside repo: `/tmp/task041-sdk-a`, `/tmp/task041-sdk-b`, `/tmp/task041-sdk-*`
- Mutate outside repo only via sanctioned command: live SysUISdk artifact files

**Interfaces:**
- Consumes: committed Tasks 2–3.
- Produces: two equivalent staging platforms and a live SDK strictly equal to staging after apply.

- [ ] **Step 1: Run all Python tests before SDK mutation**

```bash
set -o pipefail
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v \
  2>&1 | tee /tmp/task041-python-tests.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task041-python-tests.status
test "$status" -eq 0
```

Expected: exit 0 and at least the 195-test pre-change baseline, plus new Task 041 tests.

- [ ] **Step 2: Build two independent full staging SDKs**

```bash
rm -rf /tmp/task041-sdk-a /tmp/task041-sdk-b
python3 tools/build_sysuisdk.py --target /tmp/task041-sdk-a --clean \
  --stages s0,s1,s2,s3,s3b,s4 2>&1 | tee /tmp/task041-sdk-a.log
python3 tools/build_sysuisdk.py --target /tmp/task041-sdk-b --clean \
  --stages s0,s1,s2,s3,s3b,s4 2>&1 | tee /tmp/task041-sdk-b.log
```

Expected: both commands exit 0.

- [ ] **Step 3: Compare staging inventories and exact source bytes**

For both target JARs, assert:

- all `/tmp/task041-approved-entries.txt` paths exist;
- exactly 35 are Task 041-owned;
- each entry's bytes equal its approved source JAR entry;
- `AssumeTrueForR8.class` is absent;
- staging A and B have identical full entry-name→CRC inventories;
- staging A and B JAR SHA-256 values are recorded as diagnostic evidence. Existing S3 uses
  inventory-level reproducibility, so full ZIP byte identity is not a Task 041 gate.

Expected: two inventory-identical target JAR pairs and exact 35/35 source provenance.

- [ ] **Step 4: Confirm pre-apply S5 difference is only Task 041 entries**

```bash
python3 tools/build_sysuisdk.py --target /tmp/task041-sdk-a --verify \
  2>&1 | tee /tmp/task041-s5-before-apply.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task041-s5-before-apply.status
test "$status" -eq 1
```

Expected: `android.jar` and `core-for-system-modules.jar` each report exactly 35 staging-only
entries and zero unexpected missing/CRC differences; all other checks pass.

- [ ] **Step 5: Apply through `build_sysuisdk.py` only**

```bash
python3 tools/build_sysuisdk.py --apply --source /tmp/task041-sdk-a \
  2>&1 | tee /tmp/task041-sdk-apply.log
```

Expected: exit 0; timestamped backups are reported for changed live JARs; no direct SDK file
operation is performed by the worker.

- [ ] **Step 6: Require strict S5 equality after apply**

```bash
python3 tools/build_sysuisdk.py --target /tmp/task041-sdk-a --verify \
  2>&1 | tee /tmp/task041-s5-after-apply.log
```

Expected: exit 0 and `S5: ALL PASS`.

- [ ] **Step 7: Append real staging/apply evidence to the issue**

Record Python test count/status, staging hashes, exact 35/35 inventories, pre-apply expected
diff, apply backup names, and post-apply strict PASS.

---

### Task 5: Verify Debug Packaging and Exact Fresh R8 Delta

**Files:**
- Modify: `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`
- Modify: `docs/orchestration/tasks/041-r8-platform-build-classpath-closure.md`
- Write outside repo: `/tmp/task041-debug*`, `/tmp/task041-r8-after*`

**Interfaces:**
- Consumes: live SysUISdk equal to Task 4 staging.
- Produces: hard-gate debug evidence and exact 7→1 R8 evidence.

- [ ] **Step 1: Run the serialized debug hard gate**

```bash
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task041-debug.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task041-debug.status
test "$status" -eq 0
```

Expected: exit 0 and `BUILD SUCCESSFUL`.

- [ ] **Step 2: Prove no bridged library class is packaged**

```bash
apkanalyzer dex packages --defined-only \
  app/build/outputs/apk/debug/app-debug.apk > /tmp/task041-debug-defined.txt
python3 - <<'PY'
from pathlib import Path
entries = Path('/tmp/task041-approved-entries.txt').read_text().splitlines()
expected_absent = {x.removesuffix('.class').replace('/', '.') for x in entries}
defined = set()
for line in Path('/tmp/task041-debug-defined.txt').read_text(errors='replace').splitlines():
    parts = line.split()
    if len(parts) >= 3 and parts[0] == 'C' and parts[1] == 'd':
        defined.add(parts[-1])
packaged = sorted(expected_absent & defined)
assert len(expected_absent) == 35, len(expected_absent)
assert not packaged, packaged
print('BRIDGED=35 PACKAGED=0')
PY
```

Expected: `BRIDGED=35 PACKAGED=0`.

- [ ] **Step 3: Run fresh post-change R8**

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task041-r8-after.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > /tmp/task041-r8-after.status
test "$status" -eq 1
```

Expected: real exit 1 because only Task 042's annotation remains.

- [ ] **Step 4: Assert exact 7→1 with zero additions**

```bash
python3 - <<'PY'
from pathlib import Path
import re
before = set(Path('/tmp/task041-missing-before.txt').read_text().splitlines())
src = Path('app/build/outputs/mapping/release/missing_rules.txt')
after = {m.group(1) for line in src.read_text().splitlines()
         if (m := re.fullmatch(r'-dontwarn (\S+)', line.strip()))}
expected_after = {'com.android.aconfig.annotations.AssumeTrueForR8'}
expected_removed = before - expected_after
removed = before - after
added = after - before
assert len(before) == 7, len(before)
assert after == expected_after, sorted(after)
assert removed == expected_removed, sorted(removed ^ expected_removed)
assert not added, sorted(added)
Path('/tmp/task041-missing-after.txt').write_text(
    '\n'.join(sorted(after)) + '\n', encoding='utf-8')
print('BEFORE=7 AFTER=1 REMOVED=6 ADDED=0')
PY
```

Expected: `BEFORE=7 AFTER=1 REMOVED=6 ADDED=0`.

- [ ] **Step 5: Run static scope and cleanliness checks**

```bash
! git diff --name-only HEAD~2..HEAD | grep -E \
  '(^|/)(src|res[^/]*)/|^app/|^SystemUI-|^libs/|^gradle/|^AGENTS\.md$|^docs/adr/|^docs/orchestration/CHARTER\.md$'
! git diff HEAD~2..HEAD -- app/proguard.flags app/proguard_common.flags | grep -E \
  'dontwarn|keep|implementation|compileOnly'
git diff --check
```

Expected: all commands exit 0; only allowed tools/tests/issue/task paths changed.

- [ ] **Step 6: Finalize evidence and commit**

Append exact command statuses, hashes, debug result, APK non-packaging proof, and R8 delta to
the issue. Tick the task brief checkboxes truthfully.

```bash
git add docs/issues/2026-08-21-r8-platform-build-classpath-closure.md \
  docs/orchestration/tasks/041-r8-platform-build-classpath-closure.md
git commit -m "docs: record SysUISdk classpath closure evidence"
```

Expected: clean worktree, focused English commits, no push.

---

## Self-Review

- Spec coverage: all six scoped refs, 35 exact entries, real source provenance, guarded apply,
  no APK packaging, debug gate, and exact 7→1 delta each have implementation and acceptance
  steps.
- Placeholder scan: no TBD/TODO/implicit test steps remain.
- Type consistency: `ClassSlice`, `task041_slices`, `validate_target`, `patch_target`, and
  `stage_s3b` names and signatures are consistent across producing and consuming tasks.
- Task 042 boundary: `AssumeTrueForR8.class` is explicitly absent from Task 041 declarations
  and remains the sole expected post-change ref.
