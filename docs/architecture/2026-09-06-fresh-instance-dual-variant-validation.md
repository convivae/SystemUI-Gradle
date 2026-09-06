# Fresh-instance dual-variant runtime verification (Tasks 103 + 104)

> One verification in two halves: Task 103 rebuilt Release and deployed the fixed **Debug**
> APK (`e61d5485…`) on a fresh instance; Task 104 swapped it for **Release** (`6d1d4254…`)
> on the same instance. Both survived full-device reboots with automatic DPGP grants,
> stable PID, and zero fatals. Combined verdict: **DUAL_VARIANT_RUNTIME_PASS** — the
> `sharedUserId` fix (commit `9723a96e`) closed the permission regression for both variants.
> Raw evidence: `/tmp/task103-fresh-instance-validation/`, `/tmp/task104-release-validation/`.

---

# Task 103 — commit fix, Release rebuild, fresh-instance Debug validation: results

Date: 2026-09-04 · Worker: task103-fresh-instance-validation · Evidence: `/tmp/task103-fresh-instance-validation/`

## Per-stage results

| Stage | Status | Evidence |
|---|---|---|
| Docs + local commit | **DOCS_COMMITTED 9723a96e** | `git show 9723a96e` — 6 files, no push |
| Release build + gates | **RELEASE_BUILD_PASS 6d1d4254cf3b83cc637dd5a87b0650fd2dcd9440549a61fa5eb8b471a02562c8** | `release-build.log`, `release-apk-info.txt`, `aconfig-gate.log` (RESULT=PASS), `release-manifest-tree.txt` (sharedUserId present) |
| Fresh boot | **FRESH_BOOT_PASS** | `stock-baseline.txt` |
| Debug deploy + validate | **DEBUG_DEPLOY_PASS** | `deploy.log`, `post-deploy.txt`, `stability.txt` |

## Stage details

### 1+2. Docs and commit (9723a96e, NOT pushed)

- `docs/issues/2026-09-03-systemui-permission-crash.md`: added Phase 4 (Task 102 result — fix
  works, polluted userdata unrecoverable, control-group evidence, references).
- `docs/orchestration/tasks/102-…md`: appended actual result (FIX_FAIL scoped) above the
  original contract.
- `docs/issues/2026-09-03-final-visible-dual-variant-runtime-verification.md`: plan step 3 now
  requires automatic DPGP grants (no manual `pm grant`), records research-emulator disposal.
- Also committed: `docs/architecture/2026-09-04-systemui-shareduserid-fix-validation.md` (Task
  102 report copy) and the Task 103 brief, plus `app/src/main/AndroidManifest.xml`.
- Commit: `9723a96e09160e1d67ff10187246361dec256152` "Restore shared SystemUI user identity in
  app manifest". **No push performed** (Chief pushes).

### 3. Release build (rebuilt after a host reboot interrupted the first attempt)

Note: the host rebooted mid-task (~05:00 UTC): `/tmp` was wiped (tmpfs), the first Release
build attempt died, and the old polluted emulator (QEMU PID 36896) was confirmed dead — no
emulator processes and ports 5554/5555 were free, satisfying the "fully stopped" requirement
without further action.

- `./gradlew :app:assembleRelease --rerun-tasks` → BUILD SUCCESSFUL in 7m 12s (493 tasks).
- APK: 45,030,166 bytes, SHA-256 `6d1d4254cf3b83cc637dd5a87b0650fd2dcd9440549a61fa5eb8b471a02562c8`.
- aconfig static gate: `uv run python tools/check_aconfig_jarjar_references.py --apk …` →
  **RESULT=PASS** (VIOLATIONS: 0).
- `aapt2 dump xmltree`: `sharedUserId(0x0101000b)="android.uid.systemui"` present.
- Daemons stopped (`./gradlew --stop`, 1 daemon).

### 4. Fresh visible emulator — FRESH_BOOT_PASS, with a documented deviation

**Deviation**: the contract asked to omit `-no-window` (visible, `DISPLAY=:0`), but the host's
graphical session was lost in the reboot — only a GDM greeter (uid 60578) owns the display;
`DISPLAY=:0` is unreachable from user context ("could not connect to display :0" + Qt xcb fatal
→ emulator exited, crashpad dir `emu-crash-36.3.10.db` left behind; no passwordless sudo to fix
session access; no user X/Wayland session exists, `XDG_SESSION_TYPE=tty`). Per the
final-verification doc's own fallback ("若窗口不可见，则运行 `scrcpy -s emulator-5554` 供用户观看"),
the emulator was launched **headless** (`-no-window`, the runbook's original command) in a
dedicated herdr tab (`task103-emulator`, tab w2:t4N, pane w2:p4T). For visual confirmation the
user can run `scrcpy -s emulator-5554` (scrcpy 3.3.4 installed); all acceptance criteria are
text-verified regardless. The crashed-launch artifacts were cleaned before relaunch.

Fresh instance: `/tmp/acloud_gf_temp/local-goldfish-instance-2/`, ports 5554,5555, images from
`/home/conv/myspace/aosp/out/target/product/emu64x` (stock super; durable image boots stock
SystemUI).

Stock first-boot baseline (`stock-baseline.txt`, 05:18:46 UTC):
- boot_id `159ea665-4d20-4915-b8ae-2b6e176ee228`, fingerprint
  `Android/sdk_phone64_x86_64/emu64x:Baklava/CP2A.260605.016/eng.conv:userdebug/test-keys`,
  verifiedbootstate orange.
- stock APK SHA `d0e36b33…` (matches Task 100/101 baseline).
- `sharedUser=SharedUserSetting{a51f8e7 android.uid.systemui/10123}`, appId 10123.
- `BLUETOOTH_CONNECT: granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT|RESTRICTION_UPGRADE_EXEMPT]`,
  `READ_CONTACTS: granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT]` — DPGP first-boot
  grants, no manual anything.
- PID 395, 0 fatals.

### 5. Debug deploy + validation — DEBUG_DEPLOY_PASS (NO manual pm grant anywhere)

Chain: adb root → disable-verity → reboot → root → remount,rw /system_ext → push → staged cp →
sync → atomic mv → chown/chmod/chcon → sync → **sha256 gate: on-device `e61d5485…` matches
host** → dalvik-cache clear → reboot → boot_id changed to `a0f06e2e-e7c7-4fd7-addd-65faa57c4575`
(05:20:42 UTC).

Post-reboot (`post-deploy.txt`):
- APK SHA `e61d5485…` on-device (unchanged through reboot).
- `sharedUser=SharedUserSetting{5b78aa9 android.uid.systemui/10123}`, appId 10123, process
  `u0_a123`.
- **`BLUETOOTH_CONNECT: granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT|RESTRICTION_UPGRADE_EXEMPT]`**
  and **`READ_CONTACTS: granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT]`** — the
  first-boot DPGP grants reattached to the shared identity through the same-identity
  replacement, automatically.
- 3-minute stability (`stability.txt`): PID **854** at t=0/45/90/135/180s (state S), **0
  FATAL EXCEPTION** in every sample.
- 6 SystemUI windows owned by uid 10123 (`mOwnerUid=10123 … package=com.android.systemui`);
  KeyguardService, GradientColorWallpaper, ImageWallpaper,
  SysUiSelectionToolbarRenderService running.

This closes the crash regression end-to-end: the same stock→Gradle replacement that
deterministically crash-looped in Task 101 (identity loss → appId 10160) now boots stable
with grants intact (identity preserved → appId 10123).

## Boundaries compliance

No screenshots or image reads (all text). No `enable-verity` (disabled only). No push. No
Release deployment (Release APK built + gated only). No versionCode/targetSdk/minSdk/coreApp/
permission changes. No AOSP-aligned source/resource file edits. Old emulator fully stopped
(died with host reboot; verified ports free). Evidence under `/tmp/task103-fresh-instance-validation/`.

## Current state — STOPPED, awaiting user visual confirmation

Emulator running headless in herdr tab `task103-emulator` (w2:t4N) on ports 5554,5555; Debug
APK `e61d5485…` deployed and stable. Release deployment is intentionally NOT done. For visual
confirmation: `scrcpy -s emulator-5554` (headless fallback because the host has no accessible
graphical session; if the user logs into the desktop, a native-window emulator could be
relaunched in a future task, but that would discard this validated fresh userdata).

## Evidence index (/tmp/task103-fresh-instance-validation/)

`release-build.log`, `release-apk-info.txt` (size+sha), `aconfig-gate.log`, `release-manifest-tree.txt`,
`stock-baseline.txt`, `deploy.log` (verity chain + sha gate), `post-deploy.txt`, `stability.txt`
(PID samples + windows + services). Emulator runtime logs: `/tmp/acloud_gf_temp/local-goldfish-instance-2/{kernel.log,logcat.txt}`.

---

# Task 104 — Release deployment final validation: results

Date: 2026-09-06 · Worker: task104-release-validation · Evidence: `/tmp/task104-release-validation/`

## Verdict: **RELEASE_DEPLOY_PASS**

Release APK `6d1d4254cf3b83cc637dd5a87b0650fd2dcd9440549a61fa5eb8b471a02562c8` deployed on the
current instance (same fresh userdata as Task 103; Debug→Release swap, same identity), survived
a full-device reboot with all grants and stability intact. **No manual `pm grant` was executed
at any point.** Stopped as contracted; user to do final visual confirmation via
`scrcpy -s emulator-5554`.

## Deployment (deploy.log)

Same staged procedure as Task 103, on the current instance (verity already disabled; was NOT
re-enabled):

- Pre-deploy baseline (`pre-deploy.txt`, 05:36:51 UTC): boot_id `a0f06e2e-e7c7-4fd7-addd-65faa57c4575`,
  Debug APK `e61d5485…` on device, both perms granted, PID 854.
- adb root → `remount,rw /system_ext` (REMOUNT_OK) → push (45,030,166 bytes) → staged cp →
  sync → atomic mv → chown 0:0 / chmod 644 / chcon `u:object_r:system_file:s0` → sync.
- **SHA gate**: on-device `6d1d4254cf3b83cc637dd5a87b0650fd2dcd9440549a61fa5eb8b471a02562c8`
  == host Release APK SHA (exact match).
- Cleared SystemUI dalvik-cache entries, rebooted, boot completed 05:37:56 UTC.

## Post-reboot acceptance (post-reboot.txt, stability.txt)

| Criterion | Result |
|---|---|
| On-device SHA = `6d1d4254…` | ✅ (verified again post-reboot) |
| New boot ID | ✅ `03244666-6066-4c4d-b9c4-baea3e441cdb` |
| sharedUser / appId | ✅ `SharedUserSetting{6745c30 android.uid.systemui/10123}`, appId 10123, process `u0_a123` |
| BLUETOOTH_CONNECT | ✅ `granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT|RESTRICTION_UPGRADE_EXEMPT]` |
| READ_CONTACTS | ✅ `granted=true, flags=[SYSTEM_FIXED|GRANTED_BY_DEFAULT]` |
| PID stable ≥ 3 min | ✅ PID **855** at t=0/45/90/135/180s, state S (no churn) |
| 0 new FATAL EXCEPTION | ✅ crash buffer 0 at every sample |
| SystemUI windows | ✅ 6 windows, all `mOwnerUid=10123 … package=com.android.systemui` |
| Services | ✅ KeyguardService, GradientColorWallpaper, ImageWallpaper, SysUiSelectionToolbarRenderService |

The DPGP first-boot grants (attached to sharedUser 10123 on this fresh userdata in Task 103's
stock boot) carried through the Debug→Release same-identity replacement exactly as they did for
stock→Debug — confirming the sharedUserId fix closes the regression for both variants.

## Boundaries compliance

No screenshots/image reads (text only). No `enable-verity` (still disabled). No `pm grant`. No
git push. No emulator restart or wipe (same instance throughout, herdr tab `task103-emulator`,
ports 5554/5555). No source edits. Evidence under `/tmp/task104-release-validation/`.

## Evidence index

`pre-deploy.txt`, `deploy.log` (remount/push/sha gate), `post-reboot.txt`, `stability.txt`
(PID samples, window owners, services). Emulator runtime logs:
`/tmp/acloud_gf_temp/local-goldfish-instance-2/{kernel.log,logcat.txt}`.

## Current state — STOPPED, awaiting user visual confirmation

Instance runs the Release APK, stable. Final visual confirmation (via `scrcpy -s emulator-5554`)
belongs to the user per contract.
