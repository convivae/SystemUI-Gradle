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

The research also proved that stock, Gradle Debug, and Gradle Release APKs are signed by the same AOSP platform test key.

### Phase 3 — controlled stock→Gradle replacement experiment: GRANTS_LOST

Worker `task101-runtime-permission-ab` replaced the fresh stock APK with the current Gradle Debug APK on `emulator-5554`, rebooted, and confirmed that the two grants are lost deterministically. The root cause is a build defect: the Gradle APK's final merged manifest lacks `android:sharedUserId="android.uid.systemui"`. The library manifest in `:SystemUI-application` declares it and retains it in its own merged intermediate, but the final app-level merged manifest does not; AGP's manifest merger does not propagate `sharedUserId` from library manifests into the app manifest.

After reboot, PMS therefore assigned SystemUI a fresh appId `10160` instead of shared user `android.uid.systemui/10123`. Android 17 keys runtime grants by appId, so the first-boot `SYSTEM_FIXED|GRANTED_BY_DEFAULT` grants under appId `10123` do not apply to appId `10160`. The crash itself confirms the identity mismatch: `SecurityException: Need android.permission.BLUETOOTH_CONNECT permission ... uid = 10160`. The stock APK has `sharedUserId="android.uid.systemui"`, while the Gradle APK does not. This falsifies the userdata-history hypothesis and supersedes the earlier versionCode-focused hypothesis.

The complete Task 101 report is copied to `docs/architecture/2026-09-03-systemui-shareduserid-appid-regression.md`; raw evidence remains under `/tmp/task101-runtime-permission-ab/`.

### Phase 4 — sharedUserId manifest fix: correct but insufficient on the polluted research userdata

Worker `task102-shareduserid-runtime-identity` added `android:sharedUserId="android.uid.systemui"` to `app/src/main/AndroidManifest.xml` (the only file modified; no permission/versionCode/coreApp changes), rebuilt Debug (SHA `e61d5485d86977417172fcb22825b73c544436a0a9cbe8820008546804894e71`), verified the attribute in the built APK via `aapt2 dump xmltree`, and deployed + rebooted on the same research emulator. Result: `FIX_FAIL` with a precise scope —

- **The fix itself works as designed**: post-reboot `dumpsys package com.android.systemui` shows `sharedUser=SharedUserSetting{… android.uid.systemui/10123}`, `appId=10123`, process `u0_a123`, and the crash's AttributionSource reports `uid = 10123` (Task 101 had 10160). The identity regression is repaired.
- **The grants did not come back on that userdata**: `BLUETOOTH_CONNECT`/`READ_CONTACTS` remain ungranted (0 SYSTEM_FIXED grants vs stock baseline 9) and the crash-loop persists (`uid = 10123` in the SecurityException). Root cause: Task 101's identity-less boot destroyed the appId-10123 grant state while the shared user had no member package, and even the POST_NOTIFICATIONS role grant earned under appId 10160 did not follow the identity back to 10123. Control-group evidence: `com.android.phone` (20), `com.android.settings` (23), `com.android.nfc` (7) all still hold their first-boot SYSTEM_FIXED grants on the same userdata, proving the loss is appId-10123-specific. DPGP cannot re-run because the first-boot fingerprint gate was already consumed.

Conclusion: the fix is necessary and correct, and is expected to be fully self-sufficient on fresh userdata (first-boot DPGP grants attach to the shared identity directly); the old research emulator's userdata is polluted and was discarded. Fresh-instance validation is Task 103. The complete Task 102 report is copied to `docs/architecture/2026-09-04-systemui-shareduserid-fix-validation.md`; raw evidence remains under `/tmp/task102-shareduserid-fix/`.
