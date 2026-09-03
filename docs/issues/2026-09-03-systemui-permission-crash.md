# SystemUI permission crash hypothesis verification (2026-09-03)

## Background

The final visible runtime verification stopped because the deployed Debug APK crash-loops after a whole-device reboot. The first fatal exception is a `SecurityException` for `android.permission.BLUETOOTH_CONNECT`, and `dumpsys package com.android.systemui` shows both `BLUETOOTH_CONNECT` and `READ_CONTACTS` as `granted=false`. Before investigating AOSP packaging or package-identity root causes, the user requested the simplest direct experiment: re-grant the two permissions manually on the current emulator, reboot, and determine whether the crash disappears.

## Direct experiment

On `emulator-5554`, grant:

- `android.permission.BLUETOOTH_CONNECT`
- `android.permission.READ_CONTACTS`

Then reboot the device and record whether SystemUI reaches a stable PID with no new FATAL/crash entries and with usable status/navigation UI.

## Follow-up only if the direct experiment passes

Investigate why AOSP's own built SystemUI APK does not hit the same failure while the Gradle-built APK does. The investigation must identify the actual PackageManager/default-permission path used by the stock image, why replacement or reboot loses those grants for our APK, and which compliant mechanism can be copied or added permanently.

## Results

### Phase 1 — direct grant experiment: PASS

Worker `task100-permission-crash` granted `BLUETOOTH_CONNECT` and `READ_CONTACTS` on the affected Debug deployment. The crash-loop stopped immediately, and after a whole-device reboot both permissions remained `granted=true`, SystemUI PID 848 remained stable for more than three minutes, and the fresh crash buffer contained zero `FATAL EXCEPTION` entries. Evidence was collected under `/tmp/task100-permission-crash/`.

### Phase 2 — AOSP grant mechanism research

Worker `task100-grant-research` proved that stock SystemUI receives these permissions through `DefaultPermissionGrantPolicy.grantDefaultPermissions(userId)`, called from `PackageManagerService.systemReady()` only when the persisted default-permission fingerprint differs from `Build.FINGERPRINT`. On a fresh userdata boot, stock SystemUI receives all requested runtime permissions as `SYSTEM_FIXED|GRANTED_BY_DEFAULT` because it is privileged, persistent, and platform-signed. The complete report is copied to `docs/architecture/2026-09-03-systemui-runtime-permission-grants.md`.

The research also proved that stock, Gradle Debug, and Gradle Release APKs are signed by the same AOSP platform test key. The remaining package-identity differences are that stock has `versionCode=37`, `versionName=Baklava`, and `targetSdk=Baklava`, while the Gradle APK currently has no explicit `versionCode`/`versionName` and uses `targetSdk=35`. The exact historical grant-reset mechanism is not yet proven; the next controlled experiment is Task 101 (`docs/orchestration/tasks/101-runtime-permission-ab.md`).
