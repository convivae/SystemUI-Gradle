# Task 101 — stock→Gradle permission persistence A/B experiment: results

Date: 2026-09-03 · Worker: task101-runtime-permission-ab · Instance: emulator-5554 (research,
`-read-only -writable-system`, reused per brief) · Evidence dir: `/tmp/task101-runtime-permission-ab/`

## Verdict

**GRANTS_LOST.** After replacing the stock SystemUI APK with the Gradle Debug APK
(`bc0da86d487c2b9350d911cd40b70c430003ade3740265555ce489945f79e320`) and rebooting, SystemUI
crash-loops with `java.lang.SecurityException: Need android.permission.BLUETOOTH_CONNECT
permission … uid = 10160 …` — both target permissions are effectively revoked for the running
process, and the crash-loop has returned.

## Timeline

1. **Baseline (pre-deploy, `baseline.txt`, `baseline-windows.txt`, `baseline-services.txt`)** —
   boot_id `65f0eeb3-3224-4405-8313-ce5f478942fe`, device APK SHA `d0e36b33…` (stock),
   `BLUETOOTH_CONNECT: granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT|RESTRICTION_UPGRADE_EXEMPT]`,
   `READ_CONTACTS: granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT]`, PID 398 stable,
   0 FATALs, SystemUI windows/services present (`ScreenDecorOverlayBottom` uid 10123,
   KeyguardService running).
2. **Deploy (`deploy.log`)** — `adb root` → `disable-verity` → reboot → `remount,rw /system_ext` →
   push to `/data/local/tmp` → staged cp → `sync` → atomic mv → chown/chmod/chcon →
   `sync` → sha256 gate: on-device SHA `bc0da86d…` matches the briefed Gradle Debug APK exactly.
3. **Reboot + verify (`post-reboot.txt`, `post-dumpsys.txt`, `post-crash.txt`,
   `post-verification.txt`)** — boot_id changed to `012361a0-86d8-4b35-a0db-80d99b87c898`,
   on-device APK SHA still `bc0da86d…` (overlay survived reboot), but:
   - `dumpsys package com.android.systemui`: **no `sharedUser` line**, `appId=10160`
     (was: `sharedUser=SharedUserSetting{… android.uid.systemui/10123}`, uid u0_a123).
   - Runtime permission state: `BLUETOOTH_CONNECT`/`READ_CONTACTS` no longer granted (baseline
     dumpsys showed both `granted=true` with SYSTEM_FIXED flags; post-reboot runtime section has
     neither, and the process crashes on the very check).
   - Crash-loop: 240 FATAL EXCEPTIONs in crash buffer (first at `23:56:27.343`), PID churns
     (15414 → 17010 across a 30 s sample), 0 SystemUI windows in `dumpsys window windows`.

## Root cause (proven, supersedes Task 100 hypotheses)

The Gradle APK's **merged manifest does not contain `android:sharedUserId="android.uid.systemui"`**:

- `aapt2 dump xmltree` of `app/build/outputs/apk/debug/app-debug.apk`: manifest element has
  `persistent=true` and requests both `BLUETOOTH_CONNECT` and `READ_CONTACTS`, but **no
  `sharedUserId` attribute** (and no `coreApp`).
- The library manifest `SystemUI-application/src/main/AndroidManifest.xml:27` *does* declare
  `android:sharedUserId="android.uid.systemui"`, and the library's own merged intermediate
  (`SystemUI-application/build/intermediates/merged_manifest/debug/processDebugManifest/`) still
  has it — but the final app-level merged manifest
  (`app/build/intermediates/merged_manifest/debug/processDebugMainManifest/AndroidManifest.xml`)
  has **no** `sharedUserId` (it does still carry raw `coreApp="true"`, which aapt2 then drops at
  packaging). ⇒ **AGP's manifest merger does not propagate `android:sharedUserId` from a library
  manifest into the app's merged manifest.** The C4/Task 072 assumption recorded in
  `app/src/main/AndroidManifest.xml`'s comment ("sharedUserId / coreApp 根属性同样由 library
  manifest 合并带入") is empirically false for `sharedUserId`.

Consequence chain: without `sharedUserId`, the replacement package is no longer a member of the
`android.uid.systemui` shared user, so on the reboot scan PMS assigned it a fresh appId (10160,
uid u0_a160). Android 17's permission subsystem (`AppIdPermissionPolicy`, `access.abx`) keys all
runtime grants by **appId**; the SYSTEM_FIXED default grants from first boot live under appId
**10123** and therefore simply do not apply to the new appId 10160 — the "grants lost" state is
an identity change, not a revocation. The crash's own AttributionSource line proves the running
process is uid 10160, while the grant belongs to 10123. This also explains why worker 1's manual
`pm grant` (applied to whatever appId the package then had) both fixed and persisted, and why
the stock APK must be restored together with a fresh userdata to see first-boot grants again.

Corollary: Task 100's H1 (userdata-history) is **falsified** — the stock→Gradle replacement path
itself deterministically loses the grants via the appId change. Task 100's H2 (versionCode
downgrade) remains unproven and is now secondary; the versionCode=0 / targetSdk=35 deltas exist
but the sharedUserId absence alone fully accounts for the observation.

## Fix (minimal, build-side)

Declare `android:sharedUserId="android.uid.systemui"` in the **app module's main manifest**
(`app/src/main/AndroidManifest.xml`), since main-manifest attributes are the only ones that
survive the merger for this attribute. That restores membership in the shared user, restores
appId 10123, and the existing first-boot DPGP grants reattach. Validation for the next task:
rebuild (needs build authorization — not done here), redeploy with the same procedure, reboot,
and verify `dumpsys package com.android.systemui` shows `sharedUser=… android.uid.systemui/10123`
plus both permissions granted with stable PID. Secondarily, evaluate restoring `versionCode≥37`
and codename-parity targetSdk, and whether `coreApp` can/should be preserved (AOSP-only
attribute; AOSP's own build injects it via soong, not via the APK manifest, so it may be
acceptable as-is — needs a Chief decision if deemed material).

## Constraints compliance

No screenshots or image reads (all evidence is dumpsys/ps/logcat/aapt2 text). No Gradle/Soong
build run. No Release deploy. `enable-verity` NOT run (verity left disabled so the deployed
overlay state remains inspectable; reboot alone does not remove the overlay — PITFALLS §14.1).
No tracked files modified. Emulator was rebooted twice as authorized (once for disable-verity
chain, once for the experiment).

## Evidence index (/tmp/task101-runtime-permission-ab/)

`baseline.txt`, `baseline-windows.txt`, `baseline-services.txt`, `deploy.log`, `post-reboot.txt`,
`post-dumpsys.txt`, `post-crash.txt` (240 fatals, first-fatal excerpt), `post-verification.txt`,
`post-requested-perms-context.txt`, `gradle-manifest-tree.txt` (aapt2 xmltree of the deployed
APK, showing no sharedUserId).
