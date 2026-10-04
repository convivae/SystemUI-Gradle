# Task 049: Debug APK runtime stabilization

> Orchestrated exact brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract. Worker commits but never pushes.

## Authority

`redline-gated`. The user explicitly authorized the Debug build → ADB push → diagnose →
minimal fix → rebuild/push loop until SystemUI is stable, followed by repository review
and push. Release build/push/validation is deferred to a later task.

Device mutation is authorized only on one newly created disposable AVD whose name starts
`sysui-gradle-task049-debug-`. Stop if the target cannot be proven to be that AVD.

## Reports To

Chief architect in the main SystemUI-Gradle herdr pane. Commit locally; never push.

## Required reading and sub-skills

After worker-contract startup, read completely:

1. `docs/issues/2026-08-22-debug-apk-runtime-stabilization.md`
2. `docs/superpowers/plans/2026-08-22-debug-apk-runtime-stabilization.md`
3. `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md`
4. `docs/issues/2026-08-20-device-emulator-validation-plan.md`
5. `docs/CURRENT_STATE.md`
6. `/home/conv/.pi/agent/skills/android-cli/SKILL.md`
7. `/home/conv/.pi/agent/skills/android-cli/references/interact.md`

Invoke `superpowers:systematic-debugging`, `superpowers:test-driven-development` when a
product fix begins, `android-cli`, and `superpowers:verification-before-completion`.

## Goal

Produce a fresh Debug APK, push it to a dedicated emulator, reproduce and diagnose real
runtime failures, apply one minimal evidenced fix at a time, and repeat until SystemUI is
stable through basic UI interaction. Do not touch Release.

## Allowed repository paths

- `app/build.gradle.kts`
- `app/proguard*.flags` only if evidence proves they affect Debug (otherwise do not touch)
- focused test/tooling under `tools/**` (Python only) when needed for a durable static gate
- `docs/issues/2026-08-22-debug-apk-runtime-stabilization.md`
- `docs/superpowers/plans/2026-08-22-debug-apk-runtime-stabilization.md`
- `docs/orchestration/tasks/049-debug-apk-runtime-stabilization.md`
- create `docs/architecture/2026-08-22-debug-apk-runtime-stabilization.md` only if evidence
  requires a durable architecture record
- Gradle-generated outputs and `/tmp/task049-*` evidence

## External mutations allowed

- build `:app:assembleDebug`, serialized with max four Gradle workers
- create/start/root/disable-verity/remount/push/reboot/interact/stop/delete only the new
  `sysui-gradle-task049-debug-*` AVD
- reuse installed API 37 `google_apis;x86_64` system image; do not remove shared packages
- all ADB operations only after the identity gate passes

## Forbidden without a new explicit REDLINE approval

- any `SystemUI-*/src/**`, `SystemUI-*/res*/**`, or other AOSP-mirrored source/resource
- `app/src/main/AndroidManifest.xml` or creation of an unapproved replacement/overlay manifest
- stubs, fabricated resources, source exclusions, disabled checks, broad suppressions/keeps
- dependency versions, module boundaries, rule/process files
- any Release Gradle task or Release APK push/validation
- physical devices, unknown targets, pre-existing AVDs, shared SDK package removal
- pushing git commits (architect only)

## Mandatory emulator identity gate

Before root/remount/push/reboot/process mutation/UI input and after every reconnect, prove:

```text
serial matches emulator-*
ro.kernel.qemu == 1
resolved AVD name starts sysui-gradle-task049-debug-
EMULATOR_ONLY_GATE=PASS
```

## Diagnosis/fix protocol

1. Fresh Debug build and static manifest-to-DEX inspection before ADB mutation.
2. Reproduce once and preserve complete PID/logcat/dumpsys evidence.
3. State one hypothesis. Do not edit before evidence supports it.
4. Add a focused failing regression gate where practical.
5. Apply one minimal fix and rerun build/static/runtime/UI gates.
6. Never stack speculative changes. Three failed hypotheses trigger a stop/escalation.

## Acceptance

Run the complete plan. The terminal report must contain:

```text
DEBUG_BUILD=PASS
DEBUG_APK_HASH=<actual>
MANIFEST_ENTRY_DEX_CLOSURE=PASS
EMULATOR_ONLY_GATE=PASS
ON_DEVICE_APK_HASH_MATCH=true
SYSTEMUI_PID_STABLE_60S=pass
STATUS_BAR_INTERACTION=pass
QUICK_SETTINGS_INTERACTION=pass
LOCK_WAKE_UNLOCK=pass
POST_INTERACTION_FATAL_CRASH=false
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
OUTCOME=DEBUG_RUNTIME_PASS
RELEASE_BUILD_OR_PUSH=NOT_RUN
```

Also require `git diff --check`, relevant tests, exact changed-path scope, an English
commit, no push, and terminal-final `HANDOFF:`. A build-only success is not acceptance.
