# 2026-08-21 — Disposable-emulator SystemUI runtime validation

## Status

Exact execution scope approved by the user on 2026-08-21. Task 048 may provision and
fully mutate one dedicated disposable Android emulator, including SDK/system-image
download, AVD creation/removal, `adb root`, verity/remount, APK replacement, process
restart, reboot, and rollback. Physical devices and pre-existing AVDs remain outside
scope.

## Background

Debug and optimized Release APKs build and pass static package acceptance, but no
runtime validation has replaced the platform SystemUI. SystemUI is a privileged,
platform-signed package under `/system_ext`; ordinary `adb install` is not representative.
A meaningful experiment must use a rootable writable emulator and replace the exact
preinstalled APK path.

The user explicitly accepted the disposable nature of this experiment: a failed or
boot-looping dedicated AVD may be deleted and recreated. This authorization removes the
previous read-only and second-approval gates for Task 048, but only inside the dedicated
emulator boundary.

## Hard safety boundary

Before the first mutating ADB command, all three conditions must be true:

1. serial matches `emulator-*`;
2. `adb -s SERIAL shell getprop ro.kernel.qemu` returns `1`;
3. the resolved AVD name starts with `sysui-gradle-task048-`.

A physical device, unknown serial, or pre-existing AVD must never receive a mutating
command. That condition is a REDLINE despite the broad emulator authorization.

## Steps

1. Inspect AOSP/API facts and available rootable images using
   `android --sdk=/home/conv/Android/Sdk`; install an appropriate emulator/system image
   if needed.
2. Create one uniquely named dedicated AVD. Use official SDK tools as a documented
   fallback when Android CLI cannot express the required system image, name, or
   `-writable-system` startup option.
3. Start cold and writable; verify the three-part emulator identity gate.
4. Capture baseline boot, package path, APK/framework-res hashes, signing certificates,
   SystemUI PID, UI screenshot/layout, and logs. Pull the original APK to `/tmp`.
5. Use `adb root`, `adb disable-verity`/reboot if needed, and `adb remount`.
6. Push the already accepted Release APK to the exact path returned by
   `pm path com.android.systemui`; restore root ownership, mode, and SELinux context;
   sync and restart/reboot as required.
7. Verify package acceptance, stable SystemUI PID, absence of a fatal crash loop,
   status bar, quick settings, lockscreen/basic UI, dumpsys, screenshot/layout, and logs.
8. Report signature/framework compatibility independently from observed behavior. A
   mismatch experiment may run, but cannot be described as product-compatible success.
9. Roll back by restoring the pulled APK when practical, or stop and delete the
   dedicated AVD. Preserve evidence under `/tmp/task048-*` until architect acceptance.

## Runtime outcomes

Exactly one top-level outcome must be reported:

- `RUNTIME_PASS`: replacement loaded, SystemUI remained stable, and basic UI checks passed;
- `RUNTIME_FAIL`: replacement was executed but crashed, failed scan/start, or failed UI checks;
- `ENVIRONMENT_BLOCKED`: no suitable image/AVD could be provisioned or root/remount could
  not be established.

No mismatch or failed replacement may be called a pass.

## Error-count evolution

Not applicable. No repository implementation change is allowed. The accepted APK is
used directly; Gradle is not run by this task.

## Open questions

None for the dedicated emulator experiment. Any physical-device operation, mutation of
a pre-existing AVD, project source/build change, or attempt to use an APK other than the
accepted artifact requires separate approval.
