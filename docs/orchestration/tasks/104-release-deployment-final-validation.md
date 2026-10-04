# Task 104 — Release deployment final validation on visible instance

## Context

Task 103 completed the Debug half of the final dual-variant verification: fixed Debug APK `e61d5485…` deployed on the fresh visible(-capable) instance, survived full-device reboot with automatic DPGP grants, PID stable, 0 FATAL — and the **user has now visually confirmed the Debug UI is normal**.

The Release APK was rebuilt with the same sharedUserId fix in Task 103: SHA-256 `6d1d4254cf3b83cc637dd5a87b0650fd2dcd9440549a61fa5eb8b471a02562c8`, aconfig static gate PASS, manifest contains `android:sharedUserId="android.uid.systemui"`. It has NOT been deployed yet.

Current instance: headless emulator on ports 5554/5555 (herdr tab `task103-emulator`), running the fixed Debug APK, user is co-located with the machine and can view via local `scrcpy -s emulator-5554`. Do NOT restart or wipe the emulator.

## Scope

1. Deploy the Release APK (`app/build/outputs/apk/release/app-release.apk`, SHA `6d1d4254…`) using the same procedure as Task 103: adb root / remount (verity already disabled on this instance) / staged copy → device SHA verify → atomic mv → ownership/permissions/SELinux context → clear oat/dalvik cache for SystemUI.
2. Full-device reboot; wait for boot completed.
3. Post-reboot acceptance (text-only, NO manual `pm grant`):
   - on-device APK SHA = `6d1d4254…`; boot ID changed;
   - `dumpsys package com.android.systemui`: sharedUser `android.uid.systemui` / appId 10123;
   - `BLUETOOTH_CONNECT` and `READ_CONTACTS` still `granted=true` (flags include SYSTEM_FIXED);
   - SystemUI PID stable for ≥3 minutes; 0 new FATAL EXCEPTION in crash buffer;
   - SystemUI windows present via `dumpsys window windows`.
4. Then STOP and report — the user will do the final visual confirmation via scrcpy.

## Boundaries

- No screenshots or image reads; text-only verification.
- No `enable-verity`. No `pm grant`. No git push. No emulator restart/wipe.
- Do not modify AOSP-aligned source/resource files.
- Save evidence under `/tmp/task104-release-validation/`.

## Result

**RELEASE_DEPLOY_PASS** — with zero manual `pm grant` at any point, on the same fresh instance/userdata as Task 103 (Debug→Release same-identity swap):

| Criterion | Result |
|---|---|
| On-device SHA = `6d1d4254…` | ✅ (sha gate + post-reboot verification, exact host match) |
| New boot ID | ✅ `03244666-6066-4c4d-b9c4-baea3e441cdb` |
| sharedUser / appId | ✅ `SharedUserSetting{6745c30 android.uid.systemui/10123}`, process `u0_a123` |
| BLUETOOTH_CONNECT | ✅ `granted=true [SYSTEM_FIXED|GRANTED_BY_DEFAULT|RESTRICTION_UPGRADE_EXEMPT]` |
| READ_CONTACTS | ✅ `granted=true [SYSTEM_FIXED|GRANTED_BY_DEFAULT]` |
| PID stable ≥ 3 min | ✅ PID 855 at t=0/45/90/135/180s, state S |
| 0 new FATAL EXCEPTION | ✅ crash buffer 0 at every sample |
| SystemUI windows | ✅ 6 windows, all `mOwnerUid=10123 … package=com.android.systemui`; KeyguardService running |

The DPGP first-boot grants carried through the Debug→Release swap exactly as they did for stock→Debug — the sharedUserId fix closes the regression for both variants. Full report merged into `docs/architecture/2026-09-06-fresh-instance-dual-variant-validation.md`; raw evidence `/tmp/task104-release-validation/`.

## Result required (original contract, superseded by the result above)

`RELEASE_DEPLOY_PASS` (or `_FAIL` with exact evidence): host/device SHA, boot ID, identity/permission dumpsys, PID samples, crash count, window count, evidence paths. End stopped, awaiting user visual confirmation.
