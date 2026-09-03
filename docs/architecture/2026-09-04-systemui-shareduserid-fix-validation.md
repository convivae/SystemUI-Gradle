# Task 102 — sharedUserId runtime identity fix: results

Date: 2026-09-04 · Worker: task102-shareduserid-runtime-identity · Instance: emulator-5554 (research, reused; userdata carries Task 101's identity-less boot history) · Evidence: `/tmp/task102-shareduserid-fix/`

## Verdict

**FIX_FAIL** — but with a precisely-scoped failure: the manifest fix itself worked exactly as
designed (shared-user identity restored), while the pass criteria (grants restored without
manual `pm grant`) are not met on this userdata because the appId-10123 grant state was already
destroyed by Task 101's boot. Per contract, evidence captured and stopped; no data wipe, no
manual grant, no Release, no enable-verity.

## What was done

1. **Manifest change** — `app/src/main/AndroidManifest.xml` (only file modified): added
   `android:sharedUserId="android.uid.systemui"` to the root `<manifest>` element and rewrote
   the comment to state that AGP's merger does NOT propagate sharedUserId from library manifests
   (replacing the Task 072 claim that it did). No uses-permission entries added; no
   versionCode/targetSdk/minSdk/coreApp change; no AOSP-aligned file touched.
2. **Build** — `./gradlew :app:assembleDebug --rerun-tasks` → BUILD SUCCESSFUL in 4m 10s (278
   tasks). Daemons stopped (`./gradlew --stop`, 1 daemon). New APK SHA-256:
   `e61d5485d86977417172fcb22825b73c544436a0a9cbe8820008546804894e71`.
3. **Manifest verification** (`manifest-tree.txt`) — `aapt2 dump xmltree` of the built APK shows
   `sharedUserId(0x0101000b)="android.uid.systemui"`, `package="com.android.systemui"`,
   `persistent=true`.
4. **Deploy + reboot** (`deploy.log`) — root/remount/staged-copy/atomic-mv/chown/chmod/chcon/
   sync, sha256 gate passed on-device (`e61d5485…`), stale dalvik-cache entries removed, reboot.
   Boot ID changed `012361a0…` → `f987bc64-6686-42d1-be92-7e5690019685`; on-device APK SHA
   still `e61d5485…` after reboot.

## What the fix accomplished (proven)

**Shared-user identity fully restored** (`post-reboot.txt`, `post-dumpsys.txt`):

- `sharedUser=SharedUserSetting{9ea850a android.uid.systemui/10123}` — present again (was
  absent in Task 101).
- `appId=10123`, process runs as `u0_a123` (Task 101 had appId 10160 / u0_a160).
- The crash's AttributionSource now shows `uid = 10123` (Task 101's fatal showed 10160).

## Why the verdict is FAIL — grant state for appId 10123 no longer exists on this userdata

- `BLUETOOTH_CONNECT` / `READ_CONTACTS`: **not granted** (absent from the runtime permissions
  section entirely; requested-only). SystemUI SYSTEM_FIXED grant count: **0** (Task 101 baseline
  with stock APK: 9). The runtime-permissions block for the package now holds only
  `ACCESS_LOCAL_NETWORK`, `READ_EXTERNAL_STORAGE=false`, `WRITE_EXTERNAL_STORAGE=false`, and
  `POST_NOTIFICATIONS: granted=false` — the latter was granted=true under appId 10160 in Task
  101, i.e. even that role grant did not follow the identity change back to 10123.
- Crash-loop continues: first fatal `00:15:05.907` PID 850, same
  `java.lang.SecurityException: Need android.permission.BLUETOOTH_CONNECT permission …
  uid = 10123` (identity fixed, grant still missing); 37 → 93 → 149 FATALs across samples; PID
  churn 4281 → 7309 → 8290; no SystemUI windows.
- **Control group proves the loss is appId-10123-specific**: `com.android.phone` (20),
  `com.android.settings` (23), `com.android.nfc` (7) all still hold their first-boot
  SYSTEM_FIXED/GRANTED_BY_DEFAULT grants on this same userdata (`evidence-control.txt`). The
  Android-17 permission subsystem's appId-keyed state for 10123 was evidently destroyed during
  Task 101's boot(s), when the package occupied appId 10160 and shared user `android.uid.systemui`
  had no member package.
- DPGP cannot re-run on this userdata: the first-boot fingerprint gate was already consumed
  (Task 100 research: `default-permission-grant fingerprint` persisted in
  `access_de_user0.abx`, PackageManagerService.java:4585-4600).
- `access.abx` byte-comparison of the BLUETOOTH_CONNECT/READ_CONTACTS string entries between
  Task 100's file (grants present) and now is inconclusive (abx string pool shows identical
  entry bytes regardless of owner appId); dumpsys is authoritative.

## Conclusion for the Chief

The sharedUserId fix is correct and necessary — it is proven to restore the shared identity on
replacement — but it is not sufficient *on a userdata that has already booted a sharedUserId-less
SystemUI APK once*, because that boot both moved the package to a new appId and destroyed the
10123 grant state while the shared user was empty. The fix should be fully self-sufficient in
the deployment modes that matter going forward:

1. **Fresh userdata / image bake-in**: first boot with the fixed APK → DPGP
   (persistent ✓ priv-app ✓ platform-signed ✓) grants everything at first boot; no dependency on
   prior state. This is the AOSP-modeled deployment the project targets.
2. **Current research userdata only**: recovery requires either a manual `pm grant` of the two
   permissions (operationally proven, out of scope here) or a userdata wipe (forbidden here).
   Recommendation: treat this emulator instance as spent; validate end-to-end on the next fresh
   instance.

Suggested follow-up task: fresh-instance validation (new userdata, deploy fixed APK before
first boot or at first boot, verify 9 SYSTEM_FIXED grants + stability), plus the secondary
items from Task 101 (versionCode≥37 / targetSdk parity / coreApp decision).

## Evidence index (/tmp/task102-shareduserid-fix/)

`apk-sha.txt`, `manifest-tree.txt` (aapt2 xmltree with sharedUserId), `pre-deploy.txt`,
`deploy.log` (procedure + sha gate), `post-reboot.txt` (boot ID, APK SHA, identity, PID),
`post-dumpsys.txt`, `post-crash.txt` (fatal loop, uid=10123), `evidence-perm-state.txt` (PID
samples, granted= list), `evidence-control.txt` (control apps vs SystemUI SYSTEM_FIXED counts,
POST_NOTIFICATIONS loss), `access_de_user0.abx`, `access_system.abx`, `post-logcat-main.txt`.
