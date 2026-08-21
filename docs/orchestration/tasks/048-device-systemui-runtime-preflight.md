# Task 048: Device and SystemUI runtime preflight

> Orchestrated exact brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract. Worker commits but never pushes.

## Authority

`redline-gated`, read-only preflight only. Installation, root/remount, package/system
partition mutation, emulator start/create/remove, and SystemUI process restart are not
approved. If a compatible target is found, stop after documenting an unexecuted packet:

```text
REDLINE: Device runtime execution — <serial, compatibility proof, proposed replacement/restart/rollback commands>
```

## Reports To

Chief architect in the main SystemUI-Gradle herdr pane. Commit locally; never push.

## Required reading and sub-skills

After worker-contract startup, read completely:

1. `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`
2. `docs/superpowers/plans/2026-08-21-device-systemui-runtime-preflight.md`
3. `docs/issues/2026-08-20-device-emulator-validation-plan.md`
4. `docs/CURRENT_STATE.md`

Invoke the `android-cli` skill (including `references/interact.md`) and
`superpowers:executing-plans`.

## Goal

Discover connected devices and existing AVDs, collect only direct read-only evidence,
and classify each connected target as `INCOMPATIBLE`, `INSUFFICIENT_EVIDENCE`, or
`READY_FOR_REPLACEMENT_REVIEW`. Do not install or restart anything.

## Allowed Paths

- create `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md`
- modify `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`
- modify `docs/superpowers/plans/2026-08-21-device-systemui-runtime-preflight.md`
- modify `docs/orchestration/tasks/048-device-systemui-runtime-preflight.md`
- execute read-only `android info`, `android emulator list`, `adb devices -l`
- execute read-only device `getprop`, `getenforce`, `id`, `pm path`, `dumpsys package`
- `adb pull` installed APK/framework-res into `/tmp/task048-*`
- read existing project APK, keystore certificate, AOSP framework-res, SDK tools
- `/tmp/task048-*` evidence only

## Forbidden Paths and actions

- every other repository file and all Gradle tasks
- `adb root`, `adb remount`, `adb install`, `adb push`, package install/uninstall
- `stop`, `start`, `kill`, `reboot`, process/package mutation
- emulator create/start/stop/remove
- device filesystem writes, permission/context/SELinux/verified-boot changes
- SDK/AOSP mutation or tool/package installation/update
- claiming root/remount, signature, API/resource, or runtime compatibility without evidence

## Execution

Follow every checkbox in
`docs/superpowers/plans/2026-08-21-device-systemui-runtime-preflight.md`.

## Acceptance

```bash
command -v android
android --version
android info
/home/conv/Android/Sdk/platform-tools/adb version
android emulator list
/home/conv/Android/Sdk/platform-tools/adb devices -l
git diff --check
git status --short
```

Expected environmental branch:

- always record all exit codes and `CONNECTED_TARGETS=<n>`;
- if `n=0`, report AVD inventory and explicit deferment, with no per-device command;
- if `n>0`, one classification row per `device` serial, direct certificate/resource
  comparisons where readable, and no query against offline/unauthorized targets;
- executed-command log contains no forbidden state-changing command;
- only Allowed repository paths changed; no Gradle task ran.

A `READY_FOR_REPLACEMENT_REVIEW` result must end in REDLINE and an explicitly
`NOT EXECUTED — REQUIRES USER APPROVAL` packet. It is not permission to proceed.

## Completion report

Provide one focused English commit, tool/target/AVD summary, exact classifications,
forbidden-command scan, whether a REDLINE packet exists, and the required terminal-final
`HANDOFF:` block.
