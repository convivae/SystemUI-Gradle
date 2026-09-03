# Task 100 — runtime permission crash experiment and AOSP grant-path research

## Scope

Use the currently running visible emulator `emulator-5554`. First perform the direct experiment requested by the user:

1. Record current APK SHA, PID, crash status, and the two permission states.
2. Manually grant `android.permission.BLUETOOTH_CONNECT` and `android.permission.READ_CONTACTS` to `com.android.systemui`.
3. Reboot the device.
4. Verify whether the permission grant survives and whether the SystemUI crash-loop is gone. Collect before/after PID, boot ID, permission state, first fatal/crash entries, and a screenshot.

Only if that direct experiment removes the crash-loop, investigate why AOSP's packaged SystemUI does not require this manual workaround. Find the real stock grant mechanism, why the Gradle-built replacement loses the grants, and whether the compliant permanent fix belongs in the product image, package identity/signing, or Gradle packaging.

## Boundaries

- Do not deploy the frozen Release APK.
- Do not run Gradle/Soong builds.
- Do not modify tracked project files unless a concrete, user-approved permanent fix is identified after the experiment.
- Do not change the APK or replace the SystemUI package.
- Do not execute `enable-verity`.
- Keep the emulator visible and preserve evidence under `/tmp/task100-permission-crash/` if needed.

## Expected result

A clear yes/no answer to whether the two runtime grants alone solve the current crash-loop, followed by an evidence-backed explanation and recommended permanent fix.
