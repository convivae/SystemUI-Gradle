# SystemUI runtime permission grant research (2026-09-03)

Source worker report: `/tmp/task100-permission-crash/research/final-report.md`.

Date: 2026-09-03 · Worker: task100-grant-research · Scope: research only (no build, no deploy, no Release, no tracked-file change, no screenshots)

Device baseline for all live evidence: fresh relaunch of `emu64x` per the 2026-08-26 runbook
(`-read-only -writable-system`, fresh userdata), stock `SystemUI.apk` SHA
`d0e36b33a5170c44b092da00efbf3e0aced2b8dbc5862b2fc3d088d3b77a5e25`, fingerprint
`Android/sdk_phone64_x86_64/emu64x:Baklava/CP2A.260605.016/eng.conv:userdebug/test-keys`,
`sys.boot_completed=1`, verity enabled, `device_provisioned=1`. This boot is exactly the
"fresh emu64x userdata + stock SystemUI" scenario Q1 asks about.

---

## 1. Q1 — Who grants BLUETOOTH_CONNECT / READ_CONTACTS to stock SystemUI on first boot

**Mechanism: `DefaultPermissionGrantPolicy.grantDefaultPermissions(userId)`, gated per-user on a
build-fingerprint check inside `PackageManagerService.systemReady()`. Not a default-permissions
XML — the image has no SystemUI entry in `/system/etc/default-permissions/` (only
bips/printrecommendationservice/telecomui).**

Call chain (AOSP `android-17.0.0_r1`):

1. `SystemServer.java:3256` calls `mPackageManagerService.systemReady()` (before SystemUI is
   started by AMS later in boot).
2. `PackageManagerService.java:4585-4600` (`systemReady`): for every living user, computes
   `isPermissionUpgradeNeeded = !Objects.equals(getDefaultPermissionGrantFingerprint(userId), Build.FINGERPRINT)`.
   Only for users where this is true it calls `mLegacyPermissionManager.grantDefaultPermissions(userId)`
   and then persists `setDefaultPermissionGrantFingerprint(Build.FINGERPRINT, userId)`.
   ⇒ The grant pass runs exactly once per (image fingerprint, userdata) pair — first boot or after
   an OTA fingerprint change. Never again on ordinary reboots.
   (Fingerprint storage: `PermissionService.kt:2426-2433` get/set; persisted as
   `default-permission-grant fingerprint` in the per-user permission APEX data file
   `AccessPersistence.kt:177-180` → `PermissionApex.kt` →
   `/data/misc_de/0/apexdata/com.android.permission/access.abx`.)
3. `DefaultPermissionGrantPolicy.java:415-426` `grantDefaultPermissions(int)` →
   `grantPermissionsToSysComponentsAndPrivApps` (line 470-489).
4. Eligibility filter `isSysComponentOrPersistentPlatformSignedPrivApp`
   (`DefaultPermissionGrantPolicy.java:1806-1828`): uid < `FIRST_APPLICATION_UID`, **or**
   privileged **+ `FLAG_PERSISTENT` + platform-signed**. SystemUI qualifies via the second branch:
   `/system_ext/priv-app/SystemUI/SystemUI.apk` (privileged, `privateFlags` contains `PRIVILEGED`),
   `android:persistent="true"` in its manifest, platform-signed.
5. `grantRuntimePermissionsForSystemPackage` (`DefaultPermissionGrantPolicy.java:440-465`):
   collects **every runtime (dangerous) permission the package requests** and grants them all with
   `systemFixed = true` (line 462). BLUETOOTH_CONNECT and READ_CONTACTS are both requested runtime
   permissions of AOSP SystemUI, so both are granted.

**Device confirmation (this session, fresh boot):**

```
adb shell dumpsys package com.android.systemui
  android.permission.BLUETOOTH_CONNECT: granted=true, flags=[ SYSTEM_FIXED|GRANTED_BY_DEFAULT|RESTRICTION_UPGRADE_EXEMPT]
  android.permission.READ_CONTACTS:      granted=true, flags=[ SYSTEM_FIXED|GRANTED_BY_DEFAULT]
```

9 permissions carry `SYSTEM_FIXED|GRANTED_BY_DEFAULT` — the DefaultPermissionGrantPolicy
signature. SystemUI ran stably (PID 398, identical across two samples 30 s apart; crash buffer
empty; `bluetooth_on=1`). The consumed fingerprint was verified persisted on-device: strings of
`/data/misc_de/0/apexdata/com.android.permission/access.abx` contains
`default-permission-grant fingerprint = Android/sdk_phone64_x86_64/emu64x:Baklava/CP2A.260605.016/eng.conv:userdebug/test-keys`.

Note: earlier sessions checked `/data/system/users/0/runtime-permissions.xml` to conclude "no
grants" — that is the **legacy** location; on Android 17 runtime permission state lives in the
permission APEX `access.abx` (appId-scoped), so the absence of `runtime-permissions.xml` is not
diagnostic on this image.

## 2. Q2 — Why the deployed Gradle Debug APK showed both grants false after reboot

### Proven facts

- **F1 — Crash cause.** The crash-loop was caused by the app-id `android.uid.systemui` (10123)
  lacking the two runtime grants; worker 1's `pm grant` of exactly these two stopped the loop and
  survived a reboot (Task 100 phase-1 PASS, Debug APK `bc0da86d…`).
- **F2 — Signature is NOT the cause.** apksigner SHA-256 of signer cert:
  stock `SystemUI.apk` = `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`;
  Gradle debug APK = same; Gradle release APK = same; AOSP `platform.x509.pem` = same; project
  keystore cert = same. All three APKs are platform-signed with the in-tree testkey.
- **F3 — Package identity deltas (the only structural differences found).**
  stock: `versionCode=37`, `versionName=Baklava`, `targetSdk=10000` (Baklava codename, i.e.
  CUR_DEVELOPMENT). Gradle APK: `versionCode=''` (absent ⇒ 0/1), `versionName=''`,
  `targetSdk=35`. Same package name, same `sharedUserId=android.uid.systemui`, same install path.
- **F4 — Grant state is appId-scoped and durable.** Grants live in `access.abx` keyed by appId
  (`AppIdPermissionPolicy.kt`), and the boot-time package-replacement code paths preserve runtime
  grants: `AppIdPermissionPolicy.onPackageAdded` (line 152) → `evaluatePermissionState` keeps
  `newFlags = oldFlags and MASK_RUNTIME` (line ~1166-1170) and even retains grants via
  `SYSTEM_OR_POLICY_FIXED_MASK` (line ~1276); `PermissionService.onPackageInstalled` early-returns
  on `DEFAULT` params (PermissionService.kt:2500-2509). Empirically: worker 1's manual grants
  survived reboot on the Gradle APK, and Task 099's manual BLUETOOTH_CONNECT grant survived the
  later Debug→Release swap.
- **F5 — Fingerprint gate.** Once a userdata's first boot has consumed the fingerprint
  (`DefaultPermissionGrantPolicy` pass run with stock in place), **no automatic re-grant ever runs
  on that userdata again** (PackageManagerService.java:4585-4600), regardless of which APK is
  later placed at the SystemUI path.
- **F6 — First boot of a /data with an APK at the SystemUI path is when grants are decided.**
  Today's fresh boot proves the pass grants stock. There is no evidence any affected session ever
  first-booted a fresh userdata with the Gradle APK already in the partition; in every crash
  session the sequence was: fresh boot with stock (or an earlier APK state) → replace with Gradle
  APK → reboot → grants observed false.
- **F7 — The affected userdata never had the grants at all.** 2026-09-01 (task077 Blocker A):
  after the Gradle Release APK had crash-looped, even the *restored stock* APK crash-looped on
  that same /data with the identical two SecurityExceptions until the manual grants were applied.
  If the grants had been present at stock's first boot and merely revoked by the Gradle
  replacement, stock would have run; it didn't.

### Synthesis

Since (a) appId runtime grants survive same-identity replacements and reboots (F4), and (b) even
stock lacked the grants on the affected userdata (F7), the grants on the crashing userdata were
**absent before/independent of the Gradle replacement, and the fingerprint gate (F5) guaranteed
nothing would ever re-grant them**. The remaining open question is why that userdata's first-boot
grant pass did not leave the grants in place. Ranked hypotheses:

- **H1 (leading, but unproven): the affected userdata's first boot happened with SystemUI's
  package state not qualifying for the pass** — e.g., the instance first-booted mid-deployment
  (APK replaced around first boot), or the userdata was first provisioned while the SystemUI
  setting was in a transient/re-scanned state, or an earlier image/super rebuild (task077 grew and
  rebuilt `super.img`/`systemimage`) left the persisted fingerprint and the actual first full boot
  out of sync so the pass ran against a state where SystemUI did not resolve as
  persistent+platform-signed+privileged. Any of these would consume the fingerprint while granting
  nothing, and F5 then prevents any later re-grant.
- **H2 (possible, not found in code): the versionCode downgrade (37 → 0) at same-path re-scan
  triggers a reset.** The traced code paths (`InstallPackageHelper.scanPackageForInitLI`
  4600-4684: the `isSystemPkgBetter`/downgrade logic applies to cross-partition updates, not
  same-path replacement; `AppIdPermissionPolicy` preserves runtime flags) do **not** revoke on
  same-path replacement. I found no code that wipes appId permission state on versionCode
  decrease, so this remains a hypothesis only.
- **H3 (unlikely): targetSdk 35 vs 10000 changes evaluation.** Both are ≥ M, so the runtime
  branch (`evaluatePermissionState`) treats them equivalently; no revoke path identified.

**What was NOT the cause, with evidence:** signature mismatch (F2), sharedUid/appId change (same
10123), default-permissions XML absence (mechanism is code-based), permission state loss on
replacement per se (F4 code + F4 empirical).

## 3. Q3 — Compliant permanent fix, ranked

**Fix 1 (build-side, restores AOSP package identity — recommended primary).**
Give the Gradle APK stock-equivalent identity: `versionCode` ≥ 37 (AGP
`versionCode = 37` in `:app` defaultConfig; prefer matching `platformBuildVersionCode`) and
`targetSdkPreview`/codename parity with the platform (stock is `Baklava`; in Gradle terms
`targetSdkPreview = "Baklava"`, or the numeric equivalent the SysUISdk platform maps to — must be
resolved against `compileSdkPreview = "SysUISdk"`). This removes the only structural deltas (F3),
makes the Gradle APK indistinguishable to the grant pass and to PMS reconciliation, and is purely
a build-config change to our own artifact — no stubs, no resource fabrication, no image surgery.

**Fix 2 (image-side, uses AOSP's own configurable mechanism — belt-and-braces).**
Ship a sysconfig default-permissions exception XML for `com.android.systemui`, exactly like
AOSP ships for telecomui (`/system/etc/default-permissions/*.xml`,
`<exception package="com.android.systemui"><permission name="android.permission.BLUETOOTH_CONNECT"
fixed="true"/>…</exception>`), consumed by
`DefaultPermissionGrantPolicy.grantDefaultPermissionExceptions` (line 1503). Caveat to validate:
like the main pass, it is invoked from `grantDefaultPermissions(userId)` under the same
fingerprint gate (PMS.java:4598/4765), so on an already-provisioned userdata it will not re-run;
it does make every *fresh* userdata (and every future image bump, since any fingerprint change
re-triggers the pass) grant SystemUI regardless of which APK occupies the path.

**Fix 3 (operational fallback, already documented).** `pm grant` of the two permissions after
deployment, per the runbook's Blocker-A row. Proven to work and persist (F1/F4), but manual and
per-userdata; keep it as the documented stopgap, not the fix.

### Required validation (next experiment, needs deploy authorization)

Fresh instance (fresh userdata), deploy the fixed Gradle APK *before first full boot completes is
not required — the decisive test is*: (a) boot fresh with stock, replace with the identity-fixed
Gradle APK, reboot twice, `dumpsys package com.android.systemui` must show both permissions
`granted=true` with `SYSTEM_FIXED|GRANTED_BY_DEFAULT` (if H1 is right, grants from first boot
persist and this passes today already); (b) the stronger test for Fix 1/H2: wipe userdata,
deploy the identity-fixed APK first, first-boot, and confirm the default grant pass grants it
(`dumpsys` flags as above) with zero BLUETOOTH_CONNECT/READ_CONTACTS SecurityExceptions and a
stable PID. If (b) still shows `granted=false`, H2 is falsified only if versionCode was ≥ stock;
if it then passes, publish the result as proof. Also re-check `versionCode`/`targetSdk` deltas
are the only remaining manifest-level differences via `aapt dump badging` diff.

## Evidence index (all under /tmp/task100-permission-crash/research/ unless noted)

- `access.abx` (CE), `access_de_user0.abx` (DE, contains `default-permission-grant fingerprint`),
  `packages.xml` (contains `buildFingerprint`), emulator boot log `kernel.log`/`logcat.txt` paths
  under `/tmp/acloud_gf_temp/local-goldfish-instance-1/`.
- Live `dumpsys package com.android.systemui` output (permission flags, versionCode, pkgFlags,
  signatures `b4addb29`, firstInstallTime = boot time), `ps` stability samples.
- apksigner/openssl/keytool cert comparisons (F2), aapt badging comparison (F3).
- AOSP sources cited inline with file:line, tree at `/home/conv/myspace/aosp`
  (`android-17.0.0_r1`).
- Historical: `docs/issues/2026-09-01-c5-emulator-super-slack.md` P2.6.2 Blocker A;
  `docs/issues/2026-08-26-emulator-relaunch-runbook.md`; Task 099 STATE/log entries (grant
  persistence across Debug→Release swap).
