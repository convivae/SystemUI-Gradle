# Task 102 — restore shared SystemUI runtime identity

## Goal

Fix the Gradle APK so that replacement of the stock SystemUI APK preserves Android's shared SystemUI identity and the first-boot runtime permission grants.

## Required change

Add `android:sharedUserId="android.uid.systemui"` to the root `<manifest>` element of `app/src/main/AndroidManifest.xml`. Task 101 proved that the attribute in `:SystemUI-application`'s library manifest does not survive app-level manifest merging, so it must be declared in the app module's main manifest.

Do not add duplicate `<uses-permission>` entries and do not change AOSP-aligned source/resource files.

## Validation

1. Build Debug with `./gradlew :app:assembleDebug --rerun-tasks` and stop Gradle/Kotlin daemons afterward.
2. Verify the built APK manifest contains `android:sharedUserId="android.uid.systemui"` using `aapt2 dump xmltree`.
3. Deploy the rebuilt Debug APK to the current research emulator `emulator-5554` using the established root/remount/staged-copy/atomic-mv/metadata/cache procedure, then reboot.
4. After reboot verify:
   - on-device APK SHA matches the rebuilt APK;
   - boot ID changed;
   - `dumpsys package com.android.systemui` shows shared user `android.uid.systemui` / appId `10123` (or the same shared user identity as stock on this image);
   - both `BLUETOOTH_CONNECT` and `READ_CONTACTS` are granted without any manual `pm grant` in this task;
   - SystemUI PID remains stable, no new `FATAL EXCEPTION` entries appear, and SystemUI windows are present via `dumpsys window windows`.
5. If the old appId `10160` package state prevents the shared-user identity from being restored after replacement, capture the exact PMS evidence and stop rather than silently wiping data.

## Boundaries

- No screenshots or image reads.
- Do not deploy Release.
- Do not run `enable-verity`.
- Do not change versionCode/targetSdk/coreApp in this task unless the minimal sharedUserId fix is proven insufficient.
- Save evidence under `/tmp/task102-shareduserid-fix/`.

## Result required

Report `FIX_PASS` or `FIX_FAIL`, with APK SHA, manifest evidence, dumpsys identity/permission evidence, PID stability, crash count, and window evidence.
