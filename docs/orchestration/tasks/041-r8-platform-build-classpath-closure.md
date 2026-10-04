# Task 041 — R8 Platform/Build Library Classpath Closure

## Authority

`redline-gated`, `self-commit`, never push.

The user approved the two-stage structural classpath design on 2026-08-21. Task 041 owns the
first stage only: close the six B1–B4 platform/build refs through real library-class
definitions and leave `AssumeTrueForR8` for Task 042.

## Goal

Add declarative SysUISdk stage `S3b`, inject exactly 35 allowlisted source-identical classes
into both SysUISdk library JARs through staging + guarded `--apply`, keep debug assembly green,
and move fresh R8 exactly from 7 refs to 1 with zero additions.

## Required Reading

Read in order after `AGENTS.md` and `docs/orchestration/CHARTER.md`:

1. `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`
2. `docs/superpowers/plans/2026-08-21-r8-platform-build-classpath-closure.md`
3. `docs/architecture/2026-08-20-r8-platform-classpath-bridge.md`
4. `tools/build_sysuisdk.py`
5. `tools/tests/test_build_sysuisdk.py`
6. `tools/patch_sdk_dalvik_annotations.py`
7. `tools/tests/test_patch_sdk_dalvik_annotations.py`

Follow the plan checklist exactly. Use test-driven development and systematic debugging for
any unexpected result.

## Approved Exact Class Slices

Inject these six closed slices into each target JAR:

| Slice | Count |
|---|---:|
| `libcore/io/IoUtils.class` + `$FileReader` | 2 |
| `libcore/util/NativeAllocationRegistry.class` + `$CleanerRunner`, `$CleanerThunk`, `$Metrics` | 4 |
| complete `org/apache/harmony/dalvik/ddmc/*.class` four-class owner package | 4 |
| `UnsupportedAppUsage.class` + `$Container` | 2 |
| `AconfigFlagAccessor.class` only | 1 |
| complete tracked keepanno annotation package | 22 |
| **Total per target JAR** | **35** |

Targets:

- `android.jar`
- `core-for-system-modules.jar`

`com/android/aconfig/annotations/AssumeTrueForR8.class` is explicitly forbidden in Task 041.

## Allowed Paths

Worker may create/modify only:

- `tools/patch_sdk_r8_library_classes.py`
- `tools/tests/test_patch_sdk_r8_library_classes.py`
- `tools/build_sysuisdk.py`
- `tools/tests/test_build_sysuisdk.py`
- `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`
- `docs/orchestration/tasks/041-r8-platform-build-classpath-closure.md`

Outside the repository, the worker may create `/tmp/task041-*` evidence and may mutate the
live SysUISdk only through:

```bash
python3 tools/build_sysuisdk.py --apply --source /tmp/task041-sdk-a
```

## Forbidden Paths and Mechanisms

- Direct writes/copies/ZIP edits under `/home/conv/Android/Sdk/platforms/android-SysUISdk`.
- `SystemUI-*/src/**`, `SystemUI-*/res*/**`, `app/src/**`, any `res/**`, or AOSP source.
- `app/build.gradle.kts`, any ProGuard/R8 rule file, root/module build files, Gradle catalog,
  dependency versions, module boundaries, `libs/**`, local Maven artifacts.
- `AGENTS.md`, `docs/adr/**`, `docs/orchestration/CHARTER.md`, maintained state/roadmap docs.
- Stubs, copied framework source, `implementation`/runtime packaging, new `compileOnly`, any
  keep/dontwarn, suppression, disabled check, source exclusion, or private AGP task hack.
- Any injection outside the approved 35-entry set or any overwrite of an existing differing
  target entry.
- Any Task 042 implementation, including `AssumeTrueForR8.class`.
- Worker push.

## Build Serialization

At most one Gradle build may run across all panes. Before each Gradle command, verify no other
SystemUI Gradle build is active. Use `-Dorg.gradle.workers.max=4`. Every piped Gradle command
must use `set -o pipefail`, `tee`, and preserve the real Gradle exit status.

## Checklist

- [x] Capture fresh baseline: exact 7 refs and real R8 exit 1.
- [x] Assert four source artifacts and exact `2+4+4+2+1+22=35` inventory.
- [x] Add patcher tests first and capture RED.
- [x] Implement deterministic exact-entry patcher and capture GREEN.
- [x] Commit patcher as `build: add exact SysUISdk library class patcher`.
- [x] Add `S3b` pipeline tests first and capture RED.
- [x] Implement source defaults/CLI/stage order/both-target integration and capture GREEN.
- [x] Commit pipeline as `build: add SysUISdk R8 library bridge stage`.
- [x] Run full Python suite; exit 0 and test count not below baseline 195.
- [x] Build two full `s0,s1,s2,s3,s3b,s4` staging SDKs; prove inventory-identical target JAR pairs.
- [x] Prove exact 35 source-identical entries per target and no `AssumeTrueForR8`.
- [x] Pre-apply S5 differs only by 35 entries per target JAR.
- [x] Apply only through guarded `build_sysuisdk.py --apply`.
- [x] Post-apply strict S5 reports `ALL PASS`.
- [x] Debug duplicate-class + assemble hard gate exits 0.
- [x] Debug APK reports `BRIDGED=35 PACKAGED=0`.
- [x] Fresh R8 real exit 1 and exact `BEFORE=7 AFTER=1 REMOVED=6 ADDED=0`.
- [x] Sole remaining ref is `com.android.aconfig.annotations.AssumeTrueForR8`.
- [x] Issue contains truthful commands/status/counts/hashes; task checkboxes are accurate.
- [x] `git diff --check` passes; worktree clean after focused English commits; never push.

## Acceptance

All commands and expected outputs are defined in
`docs/superpowers/plans/2026-08-21-r8-platform-build-classpath-closure.md`. Final acceptance
requires all of the following together:

```text
Python suite: exit 0; count >= 195
Source inventory: 35 unique approved entries
Staging A/B: both target JAR pairs have identical name→CRC inventories
Per target JAR: 35 source-byte-identical entries; AssumeTrueForR8 absent
S5 after guarded apply: ALL PASS
Debug hard gate: real Gradle exit 0; BUILD SUCCESSFUL
Debug APK: BRIDGED=35 PACKAGED=0
Fresh R8: real Gradle exit 1
R8 set delta: BEFORE=7 AFTER=1 REMOVED=6 ADDED=0
Remaining: com.android.aconfig.annotations.AssumeTrueForR8 only
git diff --check: exit 0
```

## REDLINE Conditions

Stop immediately, print `REDLINE: <area> — <facts and intended action>`, and wait:

1. Baseline is not exact 7 or source inventory is not exact 35.
2. Any approved source entry is absent, duplicated, or owned by a different artifact.
3. Existing target bytes conflict with approved source bytes.
4. More/fewer than 35 entries are needed in either target JAR.
5. Direct live-SDK mutation or a path outside Allowed Paths appears necessary.
6. Any forbidden build/dependency/ProGuard/src/res/AOSP/Task-042 change appears necessary.
7. Staging A/B target JAR inventories differ, pre-apply S5 has unrelated diffs, or
   post-apply S5 is not strict PASS.
8. Debug fails, bridged classes enter the APK, Kotlin/Compose regresses, or R8 is not exact
   7→1 with zero additions.
9. Any second Gradle build is already active.

Do not broaden scope, add a workaround, restore a dontwarn recommendation, or retry the same
failed approach repeatedly.

## Reports To

Chief architect. Completion requires focused English commits, no push, all checklist evidence,
updated issue, and terminal-final:

```text
HANDOFF:
- done: <implementation and exact class counts>
- verified: <Python/S5/debug/APK/R8 real output summary>
- remaining: AssumeTrueForR8 Task 042 only, or exact blockers
```
