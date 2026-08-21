# Task 045: SysUISdk single-entry AOSP composition

> Orchestrated exact brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract skill. Worker commits but never pushes.

## Authority

`redline-gated`, with user approval on 2026-08-21 for this exact SysUISdk Worker,
the frozen composition design, transactional independent output, heavy Debug/Release
validation, and deletion of only the seven repository paths explicitly listed below
after replacement proof.

Pre-approved red-line-adjacent scope is limited to replacing the SysUISdk tool and,
after all functional gates pass, deleting its proven-superseded repository helpers and
payloads. No AOSP-mirrored source/resource, project `res/`, dependency/version/module,
Gradle build configuration, rule/process file, official SDK base, legacy live SysUISdk,
or external backup mutation is approved.

## Reports To

Chief architect in the main SystemUI-Gradle herdr pane. Commit locally; never push.

## Required reading and sub-skills

After worker-contract startup sequence, read completely:

1. `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`
2. `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`
3. `docs/superpowers/plans/2026-08-21-sysuisdk-single-entry-composition.md`
4. `docs/adr/0006-sysuisdk-r8-library-class-bridge.md`
5. `docs/CURRENT_STATE.md`

Invoke `superpowers:test-driven-development` before production edits and
`superpowers:executing-plans` to execute the checkbox plan. Every behavior change must
have a witnessed RED failure before GREEN implementation.

## Goal

Deliver one cross-platform command:

```bash
python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp
```

It must compose an independent, generator-owned `android-SysUISdk` from a read-only
stock `android-37.0` plus exact already-built AOSP inputs, validate it transactionally,
and support the project's existing Debug and optimized Release builds. It must not
invoke Soong, patch a live SDK in place, expose S0–S5/apply/restore operations, or use
repository framework/resource payloads.

## Frozen artifact mapping

Use exactly the eight AOSP-relative paths and semantics in the architecture spec §2.
Do not glob, search for alternatives, select the newest candidate, or silently add an
artifact family. The aggregate framework turbine JAR is master over duplicate stock
SDK class entries. Framework resources come byte-exactly from the mapped
`framework-res.apk`. The bridge is exactly the unchanged Task 041 35 entries plus the
existing four dalvik optimization entries in both SDK JARs; `AssumeTrueForR8` stays out.
AIDL declarations must be derived from the two mapped primary-source AOSP files.

If this frozen map cannot compile, print:

```text
REDLINE: SysUISdk artifact map — <exact unresolved FQNs, failing command, and candidate provenance evidence>
```

Then stop without widening inputs or changing project code/build configuration.

## Allowed Paths

- `tools/build_sysuisdk.py`
- `tools/tests/test_build_sysuisdk.py`
- `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`
- `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`
- `docs/superpowers/plans/2026-08-21-sysuisdk-single-entry-composition.md`
- `docs/orchestration/tasks/045-sysuisdk-single-entry-composition.md`
- `docs/CURRENT_STATE.md`
- deletion only, after proof:
  - `libs/android-merged.jar`
  - `libs/framework-res.apk`
  - `tools/install_sdk.py`
  - `tools/patch_sdk_dalvik_annotations.py`
  - `tools/patch_sdk_r8_library_classes.py`
  - `tools/tests/test_patch_sdk_dalvik_annotations.py`
  - `tools/tests/test_patch_sdk_r8_library_classes.py`
- ignored worktree `local.properties`: temporary validation-only edit, restored
  byte-for-byte before commit; it is never staged
- `/tmp/task045-*`: temporary evidence/private SDK roots only

## Forbidden Paths

- `AGENTS.md`
- `docs/adr/**`
- `docs/orchestration/CHARTER.md`
- `docs/orchestration/STATE.md`
- `docs/orchestration/log.md`
- `README.md`, `README.en.md`, `docs/HANDOFF.md`, `docs/PLAN.md`
- all `SystemUI-*/src/**`, `SystemUI-*/res*/**`, manifests, AIDL mirrors, and `app/src/**`
- all Gradle files and properties: `*.gradle*`, `gradle/**`, `settings.gradle.kts`,
  `gradle.properties`
- every other `libs/**` path, especially `libs/keepanno-annotations.jar` and
  `libs/framework.jar`
- `/home/conv/myspace/aosp/**` mutation (read-only access only)
- `/home/conv/Android/Sdk/platforms/android-37.0/**` mutation
- `/home/conv/Android/Sdk/platforms/android-SysUISdk/**` mutation, including its nine
  historical backups
- non-Python scripts, stubs, source exclusions, suppressions, build-check bypasses,
  broad R8 rules, or additional dependencies

## Mandatory design constraints

- SDK discovery precedence: `--sdk-root`, `ANDROID_SDK_ROOT`, `ANDROID_HOME`, Linux,
  macOS, Windows defaults, exactly as spec §2.
- Default base `android-37.0`; default output
  `<sdk-root>/platforms/android-SysUISdk`.
- Standard library composition only; no shell/subprocess use for file/ZIP work.
- Sibling temporary staging and publish only after complete validation.
- Existing output refused unless `--replace` and valid generator marker; base output
  alias always refused.
- Failure cleans staging only. No `.orig`, `.bak-*`, permanent backup, `--apply`,
  restore, or live verification interface.
- Deterministic ZIP/file output and marker with exact input/output SHA-256 provenance.
- Preserve Task 041 allowlist semantics; do not package bridge classes into the APK.
- Keep the current exact release-only `AssumeTrueForR8` adapter unchanged.
- At most one Gradle build globally; all heavy commands use
  `-Dorg.gradle.workers.max=4`, `set -o pipefail`, and `tee`.
- Device installation/runtime remains deferred; never claim it ran.

## Execution checklist

Follow and tick every checkbox in:
`docs/superpowers/plans/2026-08-21-sysuisdk-single-entry-composition.md`.
Do not compress RED/GREEN cycles into after-the-fact tests.

## Acceptance

All commands are run from the isolated Worker worktree. The Worker owns the sole Gradle
slot until it finishes.

### A. Python and scope

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
git diff --check
git status --short
```

Expected: Python exit 0, `OK`, at least 200 tests; no whitespace errors; only Allowed
Paths changed; `local.properties` restored byte-for-byte.

### B. Real AOSP one-shot builds

```bash
python3 tools/build_sysuisdk.py \
  --aosp-root /home/conv/myspace/aosp \
  --sdk-root /tmp/task045-sdk-a
python3 tools/build_sysuisdk.py \
  --aosp-root /home/conv/myspace/aosp \
  --sdk-root /tmp/task045-sdk-b
```

The private roots must expose a read-only base platform appropriate for the command
without modifying the official SDK. Expected: both exit 0; complete generated relative
file inventories and SHA-256 values are equal; markers contain only stock-base/AOSP
provenance; both target JARs contain all and only the frozen bridge contribution;
resources/AIDL validate; no backup files.

Also demonstrate: existing unmarked output refusal, existing marked output refusal
without `--replace`, and successful deterministic marked replacement with `--replace`.

### C. Debug against generated SDK

Temporarily point ignored `local.properties` to the private validation SDK root, then:

```bash
set -o pipefail
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug \
  -Dorg.gradle.workers.max=4 --console=plain 2>&1 | tee /tmp/task045-debug.log
```

Expected: pipeline exit 0 and `BUILD SUCCESSFUL`.

### D. Release closure against generated SDK

```bash
set -o pipefail
./gradlew :app:minifyReleaseWithR8 --rerun-tasks \
  -Dorg.gradle.workers.max=4 --console=plain 2>&1 | tee /tmp/task045-r8.log
set -o pipefail
./gradlew :app:assembleRelease --no-daemon \
  -Dorg.gradle.workers.max=4 --console=plain 2>&1 | tee /tmp/task045-release.log
```

Expected: both pipeline exits 0; R8 missing references 0; full Release executes
`optimizeReleaseResources` and `convertShrunkResourcesToBinaryRelease`; APK is non-empty
and ZIP-valid; V2 signing true; none of the 39 bridge classes nor `AssumeTrueForR8` is
defined in packaged DEX. Record APK byte size and full SHA-256.

### E. Post-cleanup regression

Only after B–D pass, delete exactly the seven approved superseded paths. Re-run A and
the Debug command C. Expected: Python `OK` (>=200), Debug pipeline exit 0, no active
non-historical code/config reference to a deleted path, and no additional deletion.

## Completion report

Required four-part Worker completion plus:

- English commit hashes; never push.
- Actual RED/GREEN evidence summary.
- Exact AOSP input SHA-256 values and generated inventories/hashes.
- All heavy command pipeline exit codes and log paths.
- APK size/hash, ZIP result, bridge DEX count, and V2 result.
- Exact deleted-file list and retained `libs/keepanno-annotations.jar` proof.
- Any first-attempt failures, OOM/environment events, or deferred runtime work.
- Terminal-final `HANDOFF:` block.
