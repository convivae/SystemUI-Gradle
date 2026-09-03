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

Pending worker execution.
