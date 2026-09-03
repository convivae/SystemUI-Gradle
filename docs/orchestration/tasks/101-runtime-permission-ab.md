# Task 101 — controlled stock-to-Gradle permission persistence experiment

## Goal

Determine whether replacing the stock SystemUI APK with the current Gradle Debug APK actually clears the two runtime grants, or whether the affected historical userdata simply never received the first-boot default grants.

## Starting state

Use the current research emulator on `emulator-5554`: fresh userdata, stock `SystemUI.apk` SHA `d0e36b33a5170c44b092da00efbf3e0aced2b8dbc5862b2fc3d088d3b77a5e25`, and both target permissions granted with `SYSTEM_FIXED|GRANTED_BY_DEFAULT`.

## Procedure

1. Capture baseline: boot ID, stock APK SHA, PID, both permission flags, crash count, and `dumpsys window windows` evidence. Screenshots are forbidden.
2. Deploy the existing Gradle Debug APK `/tmp/final-visible-runtime/app-debug.apk` (expected SHA `bc0da86d487c2b9350d911cd40b70c430003ade3740265555ce489945f79e320`) using the established root/remount/staged-copy/atomic-mv/metadata/cache procedure.
3. Reboot and verify device APK SHA, boot ID change, both permission states, SystemUI PID stability, crash/FATAL count, and text-based window/service state.
4. If both permissions remain true and SystemUI is stable, conclude that same-identity replacement preserves grants and the earlier failure was userdata-history-specific. If either permission becomes false and SystemUI crash-loops, conclude that the stock→Gradle replacement path is implicated and capture the first fatal.

## Boundaries

- No screenshots or image reads; use `dumpsys window windows` and related text commands.
- No Gradle/Soong build in this task.
- No Release deployment.
- No `enable-verity`.
- Do not modify tracked source/build files.
- Save evidence under `/tmp/task101-runtime-permission-ab/`.

## Result required

Report `GRANTS_PERSIST` or `GRANTS_LOST`, with exact command outputs and evidence paths.
