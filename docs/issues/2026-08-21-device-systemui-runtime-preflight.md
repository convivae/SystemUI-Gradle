# 2026-08-21 — Device and SystemUI runtime preflight

## Status

Design approved by the user; exact Worker brief awaiting dispatch approval. This phase
is read-only discovery. Installation, root/remount, package replacement, and SystemUI
restart are not approved by this task.

## Background

Debug and optimized Release APKs build and pass static package acceptance, but no
compatible emulator/device runtime validation has run. SystemUI is a privileged,
platform-signed system component, so ordinary app-install assumptions are unsafe.

## Preflight questions

1. Is the official `android` CLI and SDK `adb` available?
2. Is any device connected, and what AVDs exist without starting one?
3. For each connected target, what are its API level, fingerprint, build type,
   debuggable state, verified-boot state, SELinux mode, and installed SystemUI path?
4. Can the installed SystemUI APK and device `framework-res.apk` be pulled read-only?
5. Does the installed SystemUI certificate match the project APK certificate?
6. Does device `framework-res.apk` byte-match the frozen AOSP artifact used to generate
   SysUISdk?
7. Is there enough evidence to propose a reversible replacement experiment?

## Steps

1. Run `android info`, `android emulator list`, and `adb devices -l` without starting or
   modifying a device.
2. If no target is connected, record exact evidence and stop as deferred.
3. If targets exist, collect only read-only properties, package/service state, APK and
   framework-res copies under `/tmp/task048-*`, hashes, and signing certificates.
4. Classify each target as incompatible, unknown, or ready for a separate replacement
   review. Do not infer root/remount support merely from `userdebug`/`ro.debuggable`.
5. If a candidate exists, prepare—but do not execute—exact backup, replacement,
   restart, log-capture, and rollback commands for user approval.

## Prohibition

Do not run `adb root`, `adb remount`, `adb install`, `pm install`, `pm uninstall`,
`stop`, `start`, `kill`, `reboot`, emulator start/create/remove, filesystem writes, or
any command that changes package/process/device state.

## Error-count evolution

Not applicable. No repository implementation or Gradle task is in scope.

## Open questions

Actual installation and SystemUI restart require a second explicit approval after the
preflight identifies a compatible target and a tested rollback path.
