# SysUISdk Single-Entry AOSP Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the legacy staged/live-patching SysUISdk pipeline with one transactional, cross-platform, AOSP-`out/`-driven generator and prove existing Debug/Release functional parity.

**Architecture:** Copy a read-only official platform into temporary staging, deterministically compose framework headers/resources and the frozen 39-class bridge from exact AOSP paths, derive hidden AIDL declarations from primary sources, validate, then atomically publish an owned output. The script has one build interface; it neither invokes Soong nor patches an installed SDK in place.

**Tech Stack:** Python 3 standard library (`argparse`, `hashlib`, `json`, `pathlib`, `platform`, `shutil`, `tempfile`, `zipfile`, `unittest`), AGP 9.3.1, Gradle 9.5.0.

**Spec:** `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`

## Global Constraints

- Normal entry: `python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp`.
- Base `android-37.0` and all AOSP inputs are read-only.
- Consume existing AOSP `out/`; never invoke Soong.
- Python standard library only; no `cp`, `zip`, `jar`, `sed`, or shell subprocess composition.
- No S0–S5, `--verify`, `--apply`, live patch, restore, `.orig`, or `.bak-*` interface.
- Default output refusal; `--replace` only for a generator-owned marker and never for the base platform.
- Preserve the exact Task 041 35-entry allowlist plus the existing 4 dalvik entries; exclude `AssumeTrueForR8`.
- No SystemUI source/resource, Gradle configuration, dependency, version, or module changes.
- At most one Gradle build globally; use `-Dorg.gradle.workers.max=4` for heavy gates.
- Commit messages are English; Worker commits but never pushes.

---

## File map

- Rewrite: `tools/build_sysuisdk.py` — sole public generator and all composition/validation logic.
- Rewrite: `tools/tests/test_build_sysuisdk.py` — behavior-first unit/integration fixtures.
- Delete after proof: the seven superseded payload/helper/test paths listed in the spec §6.
- Create/update: architecture, issue, plan, exact brief, and `docs/CURRENT_STATE.md`.
- Do not modify orchestration state/log from the Worker; the architect owns those files.

## Task 1: Transactional single-entry generator

**Files:**
- Modify: `tools/build_sysuisdk.py`
- Modify: `tools/tests/test_build_sysuisdk.py`
- Delete after all functional gates: `libs/android-merged.jar`, `libs/framework-res.apk`, `tools/install_sdk.py`, `tools/patch_sdk_dalvik_annotations.py`, `tools/patch_sdk_r8_library_classes.py`, `tools/tests/test_patch_sdk_dalvik_annotations.py`, `tools/tests/test_patch_sdk_r8_library_classes.py`
- Modify: `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`
- Modify: `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`
- Modify: `docs/superpowers/plans/2026-08-21-sysuisdk-single-entry-composition.md`
- Modify: `docs/orchestration/tasks/045-sysuisdk-single-entry-composition.md`
- Modify: `docs/CURRENT_STATE.md`

**Interfaces:**
- Consumes: `--aosp-root PATH` (required), optional `--sdk-root PATH`, `--base-platform NAME_OR_PATH`, `--output PATH`, `--replace`.
- Produces: a complete generator-owned `android-SysUISdk` platform and a machine-readable marker such as `.sysuisdk-generated.json`.
- Internal design names may differ, but tests must directly exercise SDK discovery, exact input resolution, ZIP composition, AIDL derivation, validation, staging publication, and replacement ownership.

- [x] **Step 1: Capture the pre-change contract**

Run the current focused suite and record real output in the issue:

```bash
python3 -m unittest tools.tests.test_build_sysuisdk -v
```

Expected: current legacy tests pass. This is evidence only; it is not proof of the new design.

- [x] **Step 2: RED — write SDK-root and CLI contract tests**

Add tests that invoke the parser/main boundary and require:

```text
--aosp-root is required
--sdk-root > ANDROID_SDK_ROOT > ANDROID_HOME > OS default
base defaults to android-37.0
output defaults to <sdk-root>/platforms/android-SysUISdk
legacy --stages/--verify/--apply options are rejected
```

Use patched environment/home/platform values rather than the host installation.

Run:

```bash
python3 -m unittest tools.tests.test_build_sysuisdk -v
```

Expected: FAIL because the new CLI/discovery contract does not exist.

- [x] **Step 3: GREEN — implement CLI/discovery only**

Implement the minimum parser and pure discovery helpers required by Step 2. Re-run the
focused suite and obtain PASS before proceeding.

- [x] **Step 4: RED — exact AOSP input and primary-source AIDL tests**

Create a fake AOSP tree at the exact spec paths. Tests must prove all eight mapped
inputs resolve relative to `--aosp-root`, one missing input fails with its exact path,
and package/type declarations are derived from the two AOSP source files. A wrong
package, name, or declaration kind must fail.

Expected focused result: FAIL before implementation.

- [x] **Step 5: GREEN — implement exact input resolution and AIDL derivation**

Use fixed relative `Path` constants; do not glob or select among candidates. Parse the
source package and expected top-level interface/parcelable declaration, append each
fully-qualified declaration once, and pass Step 4 tests.

- [x] **Step 6: RED — deterministic JAR/resource composition tests**

Fixtures must assert:

```text
framework aggregate wins a duplicate stock SDK class
stock-only entries survive
framework-res resources.arsc + res/** match source bytes exactly
framework-res AndroidManifest.xml/META-INF/assets are excluded
duplicate names inside any input ZIP fail
identical builds produce byte-identical generated JARs
```

Expected: FAIL because the new composition engine is absent.

- [x] **Step 7: GREEN — implement standard-library composition**

Use `zipfile` only, stable sorted names, fixed timestamps/attributes/compression, and
atomic temporary-file replacement inside staging. Pass Step 6 tests.

- [x] **Step 8: RED — frozen bridge and collision tests**

Pin the unchanged 35-entry Task 041 set plus four dalvik optimization entries. Assert
all 39 are source-identical in both target JARs; `AssumeTrueForR8` and all unlisted
siblings remain absent. Test equal-byte idempotence, missing source, and unequal-byte
collision failure.

Expected: FAIL before bridge implementation.

- [x] **Step 9: GREEN — implement the bridge in the single script**

Keep the allowlist declarative in `build_sysuisdk.py`; do not import the legacy patch
modules. Pass Step 8 and the complete focused suite.

- [x] **Step 10: RED — transaction, marker, and replace protection tests**

Tests must require: sibling temporary staging, cleanup on injected failure, no partial
output, default refusal for any existing output, `--replace` refusal for an unmarked
output, successful replacement only for a valid generator marker, base/output alias
refusal, and no `.orig`/`.bak-*` artifacts.

Expected: FAIL before publication implementation.

- [x] **Step 11: GREEN — implement validation and atomic publication**

Write the marker only after inventory validation. Publish by rename; on replacement,
retain the old owned output only until the new staging validates and remove it within
the transaction. Pass the focused suite.

- [x] **Step 12: Full Python gate**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: exit 0, `OK`, at least 200 tests. Record the exact count.

- [x] **Step 13: Real AOSP deterministic build gate**

Build twice from `/home/conv/myspace/aosp` into two private SDK roots or outputs without
touching the official or legacy platforms. Compare complete relative file inventories
and SHA-256 values of generated files.

Expected: command exits 0 twice; inventories and hashes are identical; each marker
contains only official-base/AOSP input provenance; both target JARs contain exactly the
same frozen 39 bridge entries; no backup files exist.

- [x] **Step 14: Debug gate against the generated SDK**

Create a private validation SDK root, expose the required existing SDK tool directories
there without copying or modifying the official base, and temporarily point the ignored
worktree `local.properties` to it. Restore `local.properties` byte-for-byte afterward.

```bash
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug \
  -Dorg.gradle.workers.max=4 --console=plain 2>&1 | tee /tmp/task045-debug.log
```

Expected: pipeline exit 0 and `BUILD SUCCESSFUL`.

If platform FQNs are unresolved, stop with `REDLINE` and report exact FQNs/candidate
provenance; do not expand the frozen map.

- [x] **Step 15: Fresh R8 and full optimized Release gates**

With the same generated SDK and global build serialization:

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks \
  -Dorg.gradle.workers.max=4 --console=plain 2>&1 | tee /tmp/task045-r8.log
set -o pipefail
./gradlew :app:assembleRelease --no-daemon \
  -Dorg.gradle.workers.max=4 --console=plain 2>&1 | tee /tmp/task045-release.log
```

Expected: both pipeline exits 0; missing references 0; Release log executes
`optimizeReleaseResources` and `convertShrunkResourcesToBinaryRelease`.

- [x] **Step 16: APK content/signing gate**

Use Android SDK tools/Python ZIP inspection to prove: Release APK is non-empty and ZIP
valid; V2 signing is true; none of the 39 bridge FQNs nor `AssumeTrueForR8` is defined in
packaged DEX. Record APK size and SHA-256.

- [x] **Step 17: Delete only proven superseded repository files**

After Steps 12–16 pass, delete exactly the seven spec §6 paths. Do not delete
`libs/keepanno-annotations.jar`, `libs/framework.jar`, or any external SDK backup.
Search non-historical active code/config for references and remove no additional file.

- [x] **Step 18: Post-deletion regression gate**

Re-run the complete Python suite and Debug hard gate against the generated SDK.
Expected: exit 0, Python `OK` with at least 200 tests, Debug `BUILD SUCCESSFUL`.

- [x] **Step 19: Documentation and scope check**

Update the architecture/issue/current-state documents with actual input hashes, output
inventories, test/build results, deletions, and any failed attempts. Device install and
runtime validation must remain explicitly deferred.

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only Task 045 Allowed Paths changed; ignored
`local.properties` matches its original SHA-256; no external SDK change is claimed.

- [x] **Step 20: Focused English commits, never push**

Create meaningful commits (tests/design, implementation, cleanup/docs may be separate).
The final Worker report must include commit hashes, actual gates, remaining work, and a
`HANDOFF:` block.
