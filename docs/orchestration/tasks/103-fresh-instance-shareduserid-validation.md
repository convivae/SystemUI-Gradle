# Task 103 — commit sharedUserId fix, rebuild Release, fresh visible-instance Debug validation

## Context

- Task 102's manifest fix is in the working tree but uncommitted: `app/src/main/AndroidManifest.xml` now declares `android:sharedUserId="android.uid.systemui"` (only file modified).
- Fixed Debug APK already built and verified: SHA `e61d5485d86977417172fcb22825b73c544436a0a9cbe8820008546804894e71`, manifest contains sharedUserId, aconfig static gate PASS.
- Task 102 proved the fix restores shared identity `android.uid.systemui/10123` on device, but the current research emulator's userdata is polluted (appId-10123 grant state destroyed by Task 101's identity-less boot) and must be discarded.
- Task 102 report already copied to `docs/architecture/2026-09-04-systemui-shareduserid-fix-validation.md`; raw evidence under `/tmp/task102-shareduserid-fix/`.

## Scope

### 1. Documentation updates

- `docs/issues/2026-09-03-systemui-permission-crash.md`: add Phase 4 section with Task 102 result (fix works; old userdata unrecoverable without wipe/grant; control-group evidence).
- `docs/orchestration/tasks/102-shareduserid-runtime-identity-fix.md`: replace "Result required" with the actual result summary (`FIX_FAIL` on polluted userdata; fix proven correct; fresh-instance validation required).
- `docs/issues/2026-09-03-final-visible-dual-variant-runtime-verification.md`: update the plan — remove the manual `pm grant` step; on fresh userdata the grants must come from `DefaultPermissionGrantPolicy` automatically (that is the acceptance criterion); record that the previous research emulator was discarded as polluted.

### 2. Local commit (NO push)

Commit `app/src/main/AndroidManifest.xml` plus the three docs above (and the copied architecture report if not yet tracked) with an English message, e.g. "Restore shared SystemUI user identity in app manifest". Do not push — Chief pushes after review.

### 3. Fresh Release build + static gate

- `./gradlew :app:assembleRelease --rerun-tasks`
- Record APK size + SHA-256.
- Run `uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/release/app-release.apk` — must be PASS.
- Verify Release APK manifest also contains sharedUserId via aapt2.
- Stop Gradle/Kotlin daemons (`./gradlew --stop`).

### 4. Fresh visible emulator

- Stop the old polluted emulator completely (QEMU PID 36896 plus its crashpad/netsimd children).
- Create a fresh instance directory (e.g. `/tmp/acloud_gf_temp/local-goldfish-instance-2/`) and launch a **visible** emulator (omit `-no-window`; `DISPLAY=:0` is available) on ports 5554,5555, following `docs/issues/2026-08-26-emulator-relaunch-runbook.md` (env vars `ANDROID_PRODUCT_OUT`/`ANDROID_BUILD_TOP`/`ANDROID_TMP`, pre-touched log files, `-read-only -writable-system`). Launch it in a separate herdr tab so it survives.
- Wait for boot completed; record stock first-boot state: boot ID, stock APK SHA, SystemUI sharedUser/appId, both permission flags (should be granted via DPGP on fresh userdata), crash count.

### 5. Deploy fixed Debug APK and validate

- Fresh userdata has verity enabled: run the root / disable-verity / reboot / remount chain first.
- Deploy the fixed Debug APK (`e61d5485…`) via the staged-copy/atomic-mv/metadata/cache procedure; verify on-device SHA; reboot.
- Post-reboot acceptance (NO manual `pm grant` anywhere in this task):
  - on-device APK SHA matches; boot ID changed;
  - `dumpsys package com.android.systemui` shows sharedUser `android.uid.systemui` / appId 10123;
  - both `BLUETOOTH_CONNECT` and `READ_CONTACTS` are `granted=true` (DPGP first-boot grants reattach);
  - SystemUI PID stable for ≥3 minutes; 0 new FATAL EXCEPTION; SystemUI windows present via `dumpsys window windows`.
- Then STOP. Do not deploy Release — that waits for the user's visual confirmation.

## Boundaries

- No screenshots or image reads; text-only verification.
- No `enable-verity`.
- No push.
- No versionCode/targetSdk/minSdk/coreApp/permission changes.
- Do not modify AOSP-aligned source/resource files.
- Save evidence under `/tmp/task103-fresh-instance-validation/`.

## Result required

Report per-stage status: `DOCS_COMMITTED <sha>` / `RELEASE_BUILD_PASS <sha256>` / `FRESH_BOOT_PASS` / `DEBUG_DEPLOY_PASS` (or `*_FAIL` with exact evidence), plus evidence paths. End in the stopped state awaiting user visual confirmation.
