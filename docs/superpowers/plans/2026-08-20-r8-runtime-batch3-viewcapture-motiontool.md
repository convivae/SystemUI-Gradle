# R8 Runtime Closure Batch 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace polluted/incomplete view-capture and motion-tool JARs with deterministic owning-Soong implementation closures, add latest-stable official protobuf-javalite, pin official coroutines to the highest compatible stable release without changing AOSP source, and remove exactly 11 R8 missing refs.

**Architecture:** A focused Python packager merges only approved class namespaces from five fixed Soong implementation JARs into two deterministic tier② JARs. Gradle models the AOSP `static_libs` runtime closure using direct JAR `implementation` edges plus official Maven protobuf-javalite 4.35.1; view-capture/protobuf land before motion-tool. Removing the old FAT view-capture JAR also removes its accidental AOSP-coroutines 1.9.0 compile-classpath shadow. The user approved official coroutines 1.10.2—the immediately preceding and diagnostically proven highest compatible stable release—so AOSP mirrored source remains unchanged.

**Tech Stack:** Python 3 `zipfile`/`unittest`, Gradle Kotlin DSL/version catalog, AOSP Soong outputs, AGP 9.3.1/D8/R8.

**Spec:** `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3.1/§7 Batch 3 and `docs/issues/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md`

## Global Constraints

- Rules P/S/C/F/R/B/H/D and ADR 0001–0005 remain mandatory.
- No source/res edits, stubs, keep/dontwarn, source exclusions, disabled checks, or direct live-SDK changes.
- `tools/` additions are Python only.
- JARs are direct files under `libs/`; never install JARs into local Maven.
- Use owning Soong `javac`/`kotlin` implementation outputs only; reject turbine/header/FAT inputs by exact namespace validation.
- `protobuf-javalite` uses latest public stable 4.35.1 under the user's existing latest-stable policy.
- **Approved REDLINE resolution:** change only `kotlinxCoroutines = "1.11.0"` to `"1.10.2"`. The worker proved 1.11.0's new `SharedFlow.collectLatest` overload breaks the unchanged AOSP expression-body function, while a reverted 1.10.2 probe compiles. 1.10.2 is the immediately preceding stable release and therefore the highest compatible official version currently proven. Do not add a coroutines shadow JAR, modify AOSP source, or silently lower below 1.10.2; a 1.10.2 acceptance failure requires a new REDLINE.
- Heavy Gradle commands use `-Dorg.gradle.workers.max=4`; piped commands use `set -o pipefail` and persist full logs plus true Gradle exit status.
- Every wait/poll timeout is at most 90 seconds.

---

## File Map

- Create `tools/package_viewcapture_motiontool_jars.py`: fixed-input deterministic class-only JAR packager.
- Create `tools/tests/test_package_viewcapture_motiontool_jars.py`: synthetic input tests for clean merge, determinism, namespace rejection, duplicate rejection, and invalid inputs.
- Replace `libs/view_capture.jar`: 56-class clean output.
- Replace `libs/motion_tool_lib.jar`: 65-class clean output.
- Modify `gradle/libs.versions.toml`: add protobuf-javalite 4.35.1 version and alias; change only existing `kotlinxCoroutines` 1.11.0→1.10.2 under explicit user approval.
- Modify `SystemUI-core/build.gradle.kts`: program/runtime edges for protobuf, view-capture, and motion-tool.
- Modify `SystemUI-shared/build.gradle.kts`: self-contained runtime edges for protobuf and view-capture.
- Update `docs/issues/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md`: actual hashes, tests, debug, APK and R8 evidence.

### Task 1: Capture fresh 119-ref baseline

**Files:**
- Read: `app/build/outputs/mapping/release/missing_rules.txt`
- Write outside repo: `/tmp/task035-r8-before.log`, `/tmp/task035-r8-before.status`, `/tmp/task035-missing-before.txt`

- [ ] **Step 1: Run fresh release R8 before edits**

```bash
rm -f /tmp/task035-r8-before.{log,status} /tmp/task035-missing-before.txt
set -o pipefail
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
  2>&1 | tee /tmp/task035-r8-before.log
printf 'GRADLE_EXIT=%s\n' "${PIPESTATUS[0]}" | tee /tmp/task035-r8-before.status
cp app/build/outputs/mapping/release/missing_rules.txt /tmp/task035-missing-before.txt
```

Expected: true Gradle exit `1` at R8 missing classes; exactly 119 unique `-dontwarn` class lines; all 11 target refs and `AssumeTrueForR8` present.

- [ ] **Step 2: Assert baseline mechanically**

```bash
python3 - <<'PY'
from pathlib import Path
refs = {x.removeprefix('-dontwarn ').strip() for x in Path('/tmp/task035-missing-before.txt').read_text().splitlines() if x.startswith('-dontwarn ')}
assert len(refs) == 119, len(refs)
assert 'com.android.app.viewcapture.ViewCapture' in refs
assert 'com.android.app.motiontool.MotionToolManager' in refs
assert 'com.google.protobuf.GeneratedMessageLite' in refs
assert 'com.android.aconfig.annotations.AssumeTrueForR8' in refs
print('BASELINE=119 PASS')
PY
```

### Task 2: Implement the deterministic clean-JAR packager with TDD

**Files:**
- Create: `tools/package_viewcapture_motiontool_jars.py`
- Create: `tools/tests/test_package_viewcapture_motiontool_jars.py`

**Interfaces:**
- Produces `package_target(inputs: tuple[Path, ...], output: Path, approved_prefix: str) -> tuple[int, ...]`.
- CLI `python3 tools/package_viewcapture_motiontool_jars.py --all [--aosp-root PATH]` writes both repository JARs and prints per-input/total counts.
- Fixed view inputs contribute `(9, 23, 24)` classes; fixed motion inputs contribute `(8, 57)` classes.

- [ ] **Step 1: Write six focused failing tests**

Tests must use synthetic ZIPs and prove:

1. view target merges three clean inputs and returns `(2, 1, 2)` for the synthetic fixture;
2. motion target merges two clean inputs and returns `(2, 2)`;
3. repeated packaging is byte-identical with sorted paths, timestamp `(1980,1,1,0,0,0)`, and mode `0644`;
4. any class outside the target's approved namespace is rejected;
5. duplicate classes within/across inputs are rejected;
6. missing, invalid-ZIP, or class-empty inputs are rejected.

Run:

```bash
python3 -m unittest tools.tests.test_package_viewcapture_motiontool_jars
```

Expected before implementation: import/file/function failure.

- [ ] **Step 2: Implement minimal packager**

Use:

```python
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
VIEW_PREFIX = 'com/android/app/viewcapture/'
MOTION_PREFIX = 'com/android/app/motiontool/'
```

For every input, iterate `.class` entries only; reject non-approved namespaces and duplicate class names. Write only sorted class entries with fixed timestamp, DEFLATED compression, Unix `0644`; omit manifests, directory entries, and Kotlin/AndroidX/protobuf dependencies. Catch missing files and `zipfile.BadZipFile` as the script's domain exception with actionable path/label messages.

Fixed production inputs, relative to AOSP root:

```text
out/soong/.intermediates/frameworks/libs/systemui/viewcapturelib/view_capture/android_common/javac/view_capture.jar
out/soong/.intermediates/frameworks/libs/systemui/viewcapturelib/view_capture/android_common/kotlin/view_capture.jar
out/soong/.intermediates/frameworks/libs/systemui/viewcapturelib/view_capture_proto/android_common/javac/view_capture_proto.jar
out/soong/.intermediates/frameworks/libs/systemui/motiontoollib/motion_tool_lib/android_common/kotlin/motion_tool_lib.jar
out/soong/.intermediates/frameworks/libs/systemui/motiontoollib/motion_tool_proto/android_common/javac/motion_tool_proto.jar
```

- [ ] **Step 3: Run focused tests green**

```bash
python3 -m unittest tools.tests.test_package_viewcapture_motiontool_jars
```

Expected: six tests, `OK`.

### Task 3: Generate and verify clean artifacts

**Files:**
- Replace: `libs/view_capture.jar`
- Replace: `libs/motion_tool_lib.jar`

- [ ] **Step 1: Generate both artifacts twice**

```bash
python3 tools/package_viewcapture_motiontool_jars.py --all
sha256sum libs/view_capture.jar libs/motion_tool_lib.jar > /tmp/task035-hash-first.txt
python3 tools/package_viewcapture_motiontool_jars.py --all
sha256sum libs/view_capture.jar libs/motion_tool_lib.jar > /tmp/task035-hash-second.txt
diff -u /tmp/task035-hash-first.txt /tmp/task035-hash-second.txt
```

Expected: first run reports view `(9,23,24)=56`, motion `(8,57)=65`; hash files are identical.

- [ ] **Step 2: Assert exact class namespaces/counts**

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile
for path, prefix, count in (
    (Path('libs/view_capture.jar'), 'com/android/app/viewcapture/', 56),
    (Path('libs/motion_tool_lib.jar'), 'com/android/app/motiontool/', 65),
):
    with ZipFile(path) as z:
        names = z.namelist()
    assert len(names) == count, (path, len(names))
    assert all(x.startswith(prefix) and x.endswith('.class') for x in names)
    assert names == sorted(names)
    print(path, count)
PY
```

### Task 4: Wire the ordered Gradle runtime closure

**Files:**
- Modify: `gradle/libs.versions.toml`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `SystemUI-shared/build.gradle.kts`

- [ ] **Step 1: Verify latest stable protobuf-javalite metadata**

Fetch Maven Central metadata and record latest/release, last ten versions, and the latest non-`RC`/alpha/beta stable selection in the issue. Expected selection: `4.35.1`. If it differs, stop with `REDLINE` before editing the version matrix.

- [ ] **Step 2: Apply the exact approved catalog entries**

```toml
kotlinxCoroutines = "1.10.2"
protobufJavalite = "4.35.1"
protobuf-javalite = { module = "com.google.protobuf:protobuf-javalite", version.ref = "protobufJavalite" }
```

Do not change any other version or alias. Record in the issue that 1.11.0 failed both debug and release compilation only after clean-JAR removal exposed the real classpath; the old FAT JAR had accidentally shadowed it with AOSP 1.9.0. Record the temporary, reverted 1.10.2 diagnostic success and the user's explicit approval.

- [ ] **Step 3: Wire view/protobuf before motion-tool**

In `SystemUI-core/build.gradle.kts`:

```kotlin
implementation(files("${rootProject.projectDir}/libs/view_capture.jar"))
implementation(libs.protobuf.javalite)
implementation(files("${rootProject.projectDir}/libs/motion_tool_lib.jar"))
```

Replace the two existing `compileOnly` declarations rather than duplicating them. Keep comments explicit that these are AOSP `static_libs` program/runtime inputs and that the clean JARs exclude Maven dependencies.

In `SystemUI-shared/build.gradle.kts` replace its view-capture `compileOnly` with:

```kotlin
implementation(files("${rootProject.projectDir}/libs/view_capture.jar"))
implementation(libs.protobuf.javalite)
```

No settings/module/POM changes.

- [ ] **Step 4: Run focused and full tests**

```bash
python3 -m unittest tools.tests.test_package_viewcapture_motiontool_jars
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: focused six tests `OK`; full discovery baseline 154 plus six new tests = 160 tests, `OK`.

### Task 5: Verify debug packaging and dex definitions

**Files:**
- Output only: `app/build/outputs/apk/debug/app-debug.apk`

- [ ] **Step 1: Run duplicate check and debug assembly**

```bash
rm -f /tmp/task035-debug.{log,status}
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug \
  -Dorg.gradle.workers.max=4 2>&1 | tee /tmp/task035-debug.log
printf 'GRADLE_EXIT=%s\n' "${PIPESTATUS[0]}" | tee /tmp/task035-debug.status
```

Expected: `GRADLE_EXIT=0`, `BUILD SUCCESSFUL`, no duplicate-class failure, and no mirrored source change. If 1.10.2 fails for a new version-related reason, preserve the log and halt with a new REDLINE; do not lower the version or edit source.

- [ ] **Step 2: Prove representative main/proto/runtime classes are defined**

Generate one `apkanalyzer dex packages --defined-only` output and assert class-definition (`C d`) rows for:

```text
com.android.app.viewcapture.ViewCapture
com.android.app.viewcapture.data.ExportedData
com.android.app.motiontool.MotionToolManager
com.android.app.motiontool.MotionToolsRequest
com.google.protobuf.GeneratedMessageLite
```

Expected: all five are `DEFINED`, not merely referenced.

### Task 6: Verify exact fresh R8 delta and document evidence

**Files:**
- Modify: `docs/issues/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md`
- Output: `app/build/outputs/mapping/release/missing_rules.txt`

- [ ] **Step 1: Run fresh post-change R8**

```bash
rm -f /tmp/task035-r8-after.{log,status}
set -o pipefail
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
  2>&1 | tee /tmp/task035-r8-after.log
printf 'GRADLE_EXIT=%s\n' "${PIPESTATUS[0]}" | tee /tmp/task035-r8-after.status
```

Expected: true Gradle exit remains `1` because later closure batches remain; failure is still missing classes, not D8 duplicates or protobuf incompatibility.

- [ ] **Step 2: Compare sets mechanically**

Parse unique `-dontwarn` lines from `/tmp/task035-missing-before.txt` and the fresh `missing_rules.txt`. The original assertion was:

- before = 119;
- after = 108;
- removed = exactly the 11 refs listed in the issue;
- added = empty;
- `com.android.aconfig.annotations.AssumeTrueForR8` remains after.

Fresh verification instead produced after = 109: exactly the planned 11 refs were removed, while the newly resolvable motion-tool closure added exactly one `org.apache.harmony.dalvik.ddmc.ChunkHandler` ref. The user accepted this truthful result and classified `ChunkHandler` as device-provided `@hide` `core-libart` B2 library-classpath work. Task 035 must record that exact set, retain `AssumeTrueForR8`, and must not add a suppression, package the class into the APK, or implement the B2 bridge.

If any assertion beyond this adjudicated single addition differs, do not add suppressions or broaden scope; diagnose and report `REDLINE` with both sets.

- [ ] **Step 3: Update issue evidence**

Record Maven metadata selection, input/output class counts, SHA-256 values, focused/full test counts, true Gradle exits, debug summary, five dex rows, R8 before/after/removed/added sets, and remaining work. Never state release success.

- [ ] **Step 4: Final hygiene and commit**

```bash
git diff --check
git status --short
git diff --name-only HEAD
```

Expected changed paths are only those in the File Map. Commit once with an English message, for example:

```bash
git add tools/package_viewcapture_motiontool_jars.py \
  tools/tests/test_package_viewcapture_motiontool_jars.py \
  libs/view_capture.jar libs/motion_tool_lib.jar \
  gradle/libs.versions.toml SystemUI-core/build.gradle.kts \
  SystemUI-shared/build.gradle.kts \
  docs/issues/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md
git commit -m "fix: package view capture runtime closure"
```

Worker must not push. End with the required `HANDOFF:` block.
