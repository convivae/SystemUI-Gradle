# Task 048: Disposable-emulator SystemUI runtime validation

> Orchestrated exact brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract. Worker commits but never pushes.

## Authority

`redline-gated` only for target-identity escape. The user explicitly authorized all SDK,
AVD, and ADB operations—including download, create/start/stop/remove, root,
disable-verity, remount, push, chmod/chown/restorecon, kill/restart, reboot, and
rollback—on one dedicated disposable emulator created by this task.

Stop with:

```text
REDLINE: Emulator-only boundary — target is physical, unknown, pre-existing, or cannot be proven to be the dedicated sysui-gradle-task048-* AVD
```

No second approval is needed for authorized operations after the identity gate passes.

## Reports To

Chief architect in the main SystemUI-Gradle herdr pane. Commit locally; never push.

## Required reading and sub-skills

After worker-contract startup, read completely:

1. `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`
2. `docs/superpowers/plans/2026-08-21-device-systemui-runtime-preflight.md`
3. `docs/issues/2026-08-20-device-emulator-validation-plan.md`
4. `docs/CURRENT_STATE.md`
5. `/home/conv/.pi/agent/skills/android-cli/SKILL.md`
6. `/home/conv/.pi/agent/skills/android-cli/references/interact.md`

Invoke the `android-cli` skill and `superpowers:executing-plans`.

## Goal

Provision one dedicated disposable rootable emulator, replace its exact platform
SystemUI APK with the frozen accepted Release artifact, collect process/UI/log evidence,
and restore or remove the AVD. Never mutate a physical device or pre-existing AVD.

## Allowed Paths and external mutations

- create `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md`
- modify `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`
- modify `docs/superpowers/plans/2026-08-21-device-systemui-runtime-preflight.md`
- modify `docs/orchestration/tasks/048-device-systemui-runtime-preflight.md`
- read accepted main APK, project signing metadata, frozen AOSP/SysUISdk inputs
- `/tmp/task048-*` evidence, pulled originals, screenshots, layouts, logs
- `android --sdk=/home/conv/Android/Sdk` info/SDK/emulator commands
- official `sdkmanager`, `avdmanager`, and emulator fallback when CLI lacks required control
- install needed emulator/system-image SDK packages; do not remove shared packages
- create/start/mutate/stop/delete only `sysui-gradle-task048-*`
- all ADB commands against the proven dedicated emulator, including root/remount/push/reboot/process/UI operations

## Frozen APK

```text
path=/home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
size=28600808
sha256=cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374
```

Stop if any value differs. Do not build or substitute another APK.

## Mandatory pre-mutation identity gate

Before `root`, `disable-verity`, `remount`, `push`, package/process mutation, reboot, or UI
input, prove all of:

```text
serial matches emulator-*
ro.kernel.qemu == 1
resolved AVD name starts sysui-gradle-task048-
```

Print `EMULATOR_ONLY_GATE=PASS`. Repeat after every reconnect/reboot before further
mutation. Existing devices/AVDs are inventory-only and must not be changed.

## Forbidden Paths and actions

- every other repository file; all source/resource/build configuration; all Gradle tasks
- any mutation of a physical device, unknown serial, or AVD not created by this task
- overwrite/remove a pre-existing AVD
- remove shared SDK platforms/system images/emulator packages
- use an APK with a different frozen size/hash
- call a mismatch/crash/boot-loop/UI failure `RUNTIME_PASS`
- leave the dedicated AVD running or present after completion
- delete `/tmp/task048-*` before architect review

## Execution

Follow every checkbox in
`docs/superpowers/plans/2026-08-21-device-systemui-runtime-preflight.md`. Android CLI is
preferred with explicit SDK root; document every official-tool fallback. Use discovered
`pm path com.android.systemui`, never a guessed path.

## Acceptance

**EXECUTED 2026-08-21/22 — OUTCOME=RUNTIME_FAIL.** Full evidence:
`docs/architecture/2026-08-21-device-systemui-runtime-preflight.md`; day record:
`docs/issues/2026-08-21-device-systemui-runtime-preflight.md`.

```text
FROZEN_APK=PASS
EMULATOR_ONLY_GATE=PASS
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
OUTCOME=RUNTIME_FAIL
ADB_ROOT=success
ADB_REMOUNT=success
SYSTEMUI_PATH=/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk
ON_DEVICE_APK_HASH=cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374
SIGNATURE_MATCH=false
FRAMEWORK_RES_MATCH=false
PID_STABILITY_60S=fail
BASIC_UI=fail
FATAL_CRASH_LOOP=true
```

Root cause (corrected 2026-08-22): two independent defects of the Application entry
point — (1) the packaged manifest references the nonexistent FQN
`com.android.systemui.app.SystemUIApplication` (AGP expanded the source manifest's
`.SystemUIApplication` against the `:app` namespace `com.android.systemui.app`; the
real class is `com.android.systemui.SystemUIApplication`), which is the immediate
launch failure; (2) R8 separately renamed the real class to `kvc` (mapping.txt), so
manifest-entry keep semantics also require fixing. A verbatim
`EMULATOR_ONLY_GATE=PASS`/on-device-hash transcript extracted from the worker session
JSONL remained at `/tmp/task048-task048-37-20260822-005602/logs/replacement-session-verification.txt`
through corrected dual review and architect fresh acceptance. The dedicated AVD was
stopped/deleted and rollback proven via `-wipe-data`; all `/tmp/task048-*` evidence was
then removed during post-push cleanup.

The report/issue and retained `/tmp/task048-*` evidence must support all of:

```text
FROZEN_APK=PASS
EMULATOR_ONLY_GATE=PASS
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
OUTCOME=RUNTIME_PASS|RUNTIME_FAIL|ENVIRONMENT_BLOCKED
```

For an executed replacement, evidence must additionally include:

```text
ADB_ROOT=<actual>
ADB_REMOUNT=<actual>
SYSTEMUI_PATH=<discovered path>
ON_DEVICE_APK_HASH=<actual>
SIGNATURE_MATCH=<true|false|unknown>
FRAMEWORK_RES_MATCH=<true|false|unknown>
PID_STABILITY_60S=<pass|fail>
BASIC_UI=<pass|fail>
FATAL_CRASH_LOOP=<true|false>
```

Run repository gates:

```bash
git diff --check
git status --short
```

Expected: only Allowed repository paths changed; no project implementation or Gradle
output. The dedicated AVD is absent/stopped at handoff, while evidence remains under
`/tmp/task048-*`.

## Completion report

Provide one focused English commit, exact CLI/tool fallback commands, image/AVD/serial,
identity-gate outputs, baseline/rollback hashes, root/remount/push/restart results,
compatibility facts, runtime/UI/log outcome, final AVD cleanup, and terminal-final
`HANDOFF:` block.
