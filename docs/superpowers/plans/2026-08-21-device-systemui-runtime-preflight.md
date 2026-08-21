# Disposable-Emulator SystemUI Runtime Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the android-cli skill and superpowers:executing-plans to execute this emulator plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision one dedicated disposable rootable emulator, replace its platform SystemUI with the accepted Release APK, collect functional runtime evidence, and remove or restore the AVD without ever mutating a physical device or pre-existing AVD.

**Architecture:** Use Android CLI with an explicit SDK root for discovery/download/provisioning, falling back to official SDK tools only where the CLI cannot express image/name/writable-system controls. Freeze a three-part emulator identity gate before mutation, collect a complete baseline and rollback artifact, perform the privileged replacement, then classify observed runtime behavior independently from signing/framework compatibility.

**Tech Stack:** Android CLI, SDK manager/AVD/emulator tools, ADB root/remount/push/shell, apksigner, logcat, dumpsys, screenshot/layout inspection.

**Spec:** `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`

## Global Constraints

- User authorization covers all SDK/AVD and ADB commands on one dedicated AVD named
  `sysui-gradle-task048-*`, including image download, root, disable-verity, remount,
  push, chmod/chown/restorecon, kill/restart, reboot, rollback, stop, and AVD deletion.
- Never mutate a physical device, unknown serial, or pre-existing AVD.
- Before mutation require serial `emulator-*`, `ro.kernel.qemu=1`, and exact dedicated
  AVD-name prefix. Failure is a REDLINE and immediate stop.
- Use `android --sdk=/home/conv/Android/Sdk` whenever the Android CLI supports the action.
  Record any fallback to `sdkmanager`, `avdmanager`, or the emulator binary and why.
- Do not modify/remove shared SDK platforms or system-image packages. Downloaded packages
  may remain; only the dedicated AVD is removed.
- Use only the accepted main-checkout Release APK at
  `/home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk`,
  expected size 28,600,808 bytes and SHA-256
  `cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374`.
  If absent or different, stop; do not build or substitute another APK.
- A signing/framework mismatch may be tested because the AVD is disposable, but it must
  be called out and can never produce `RUNTIME_PASS` without actual stable behavior.
- Do not change repository implementation/build files and do not run Gradle.
- Worker commits in English and never pushes.

---

## File map

- Create: `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md` — environment, exact commands, compatibility, runtime evidence, rollback.
- Modify: `docs/issues/2026-08-21-device-systemui-runtime-preflight.md` — actual execution record.
- Modify: this plan and `docs/orchestration/tasks/048-device-systemui-runtime-preflight.md` — checkbox/evidence state.
- Temporary only: `/tmp/task048-*`.
- External mutable scope: dedicated `sysui-gradle-task048-*` AVD and required newly
  downloaded emulator/system-image packages only.

## Task 1: Validate artifact, toolchain, and candidate images

- [x] **Step 1: Verify the frozen APK** (re-run from scratch by the replacement session: size 28600808, sha256 `cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374`, V2 signer cert `c8a2e9bc...` == project `platform.keystore`)

```bash
test -f /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
stat -c '%s' /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
sha256sum /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
/home/conv/Android/Sdk/build-tools/37.0.0/apksigner verify --print-certs \
  /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
```

Expected exact size/hash above. Any mismatch stops the task.

- [x] **Step 2: Record tools, AOSP target facts, existing AVDs/devices** (first session: `task048-sdklist.txt` captured installed/available SDK packages — zero system-images installed pre-task; emulator startup log + device facts recorded; replacement session: `adb devices -l`, `-list-avds` re-checked, only the dedicated AVD ever present)

Run `android --version`, `android --sdk=/home/conv/Android/Sdk info`, Android CLI SDK and
emulator listings, official tool versions, and `adb devices -l`. Capture existing AVDs
before creation so none can be mistaken for the disposable target.

- [x] **Step 3: Select/install a rootable image** (first session: downloaded `system-images;android-37.0;google_apis;x86_64` ~4.4 GB — rootable userdebug, API 37 matching the project's AOSP/API 37 platform; Google Play images rejected; package retained, listed in cleanup)

Prefer an AOSP/default x86_64 image closest to the AOSP platform/API; reject Google Play
images. Use Android CLI SDK install with explicit `--sdk` when possible. Network/package
failure is evidence; try only documented viable candidates and do not delete shared
packages.

## Task 2: Create and identity-gate one disposable AVD

- [x] **Step 1: Create a unique AVD** (first session: `sysui-gradle-task048-37-20260822-005602` via official `avdmanager`; no pre-existing AVD overwritten — it was the only AVD on the host)

Name it `sysui-gradle-task048-<api>-<timestamp>`. Use Android CLI create when it permits
exact image/name selection; otherwise use official `avdmanager` and record the CLI
capability gap. Do not overwrite an existing AVD.

- [x] **Step 2: Start cold with writable system** (first session: official emulator binary, boot completed in 26.3 s, `logs/emulator-startup.log`)

If Android CLI start cannot carry `-writable-system -no-snapshot`, use the official
emulator binary. Wait for device and `sys.boot_completed=1`; capture startup logs.

- [x] **Step 3: Freeze the mutation target** (replacement session re-ran the full gate independently and after every reconnect/reboot — five PASS runs, zero failures: `SERIAL_EMULATOR=true RO_KERNEL_QEMU=1 DEDICATED_AVD=true EMULATOR_ONLY_GATE=PASS`)

Record serial, `ro.kernel.qemu`, `ro.boot.qemu.avd_name`/`emu avd name`, and AVD path.
Run a machine-checkable gate that prints:

```text
SERIAL_EMULATOR=true
RO_KERNEL_QEMU=1
DEDICATED_AVD=true
EMULATOR_ONLY_GATE=PASS
```

No mutating ADB command may precede this PASS.

## Task 3: Capture baseline and rollback material

- [x] **Step 1: Collect device/platform facts** (device-facts.txt: fingerprint `google/sdk_gphone64_x86_64/emu64xa:17/CE2A.260420.019/15611780:userdebug/dev-keys`, API 37, SELinux Enforcing, verity enforcing, SystemUI PID 1126, signatures `3252fae/b2d95fc0`; dumpsys services/statusbar; baseline UI XML + screenshot)

Record fingerprint, API, build type/tags, debuggable/verity state, SELinux, boot state,
SystemUI package/path/version/signing data, framework-res path/hash, PID, dumpsys,
status-bar baseline, screenshot, and layout.

- [x] **Step 2: Pull original artifacts** (replacement session: pulled `SystemUIGoogle.apk` 49,841,504 B sha256 `a6340f94...` and `framework-res.apk` 37,160,781 B sha256 `02037946...`; both `unzip -t` OK)

Pull every `pm path com.android.systemui` APK and `/system/framework/framework-res.apk`
under `/tmp/task048-<avd>/baseline/`; record source path, size, SHA-256, ZIP/signature
status. These are the rollback and compatibility evidence.

- [x] **Step 3: Compare compatibility** (SIGNATURE_MATCH=false: on-device `301aa3cb...` Google platform cert vs frozen `c8a2e9bc...` AOSP test platform cert; FRAMEWORK_RES_MATCH=false: on-device `02037946...` vs AOSP out `7e76ce7d...`)

Compare full signer certificate SHA-256 and framework-res SHA-256 with project/AOSP
inputs. Record `SIGNATURE_MATCH=true|false|unknown` and
`FRAMEWORK_RES_MATCH=true|false|unknown` before replacement.

## Task 4: Establish writable system and replace SystemUI

- [x] **Step 1: Root/remount** (`adb root` success; `adb remount` disabled verity + enabled overlayfs, reboot required; identity gate re-PASSed; post-reboot `adb remount` -> `Remounted /system_ext as RW`, success)

Run `adb -s SERIAL root`; reconnect and re-run the identity gate. Attempt
`disable-verity` plus reboot if remount requires it, re-running the identity gate after
every reconnect. Require `adb remount` success before push.

- [x] **Step 2: Push to the discovered path** (pushed to `/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk` — the exact `pm path` result, never a guessed path; `dd` in-place, `chown root:root`, `chmod 644`, `restorecon` file+parent, `sync`; on-device size 28,600,808 and sha256 `cd4b885e...` verified)

Use the actual base APK path from `pm path`, not a guessed `priv_app`/`priv-app` path.
Push the frozen APK, then set original owner/group/mode and run `restorecon` on the file
and parent as needed. Run `sync` and verify on-device size/hash before restart.

- [x] **Step 3: Activate replacement** (logcat boundary captured; least disruptive kill attempted first — crash loop on stale PM metadata (377 entries); reboot forced rescan (`changed; collecting certs`, `signature changed; retaining data`) — crash loop on OUR Application class (5,434 entries); identity gate re-PASSed after every reconnect)

Clear/capture a logcat boundary, then use the least disruptive effective method: kill
SystemUI and wait for system_server restart; reboot if package rescanning or mount state
requires it. Every reconnect repeats the identity gate.

## Task 5: Functional runtime acceptance

- [x] **Step 1: Prove package/process stability** (rescan succeeded but SystemUI crash-looped: PID churn 896→7977→3184→...→19542→22338→(dead)→28161→31051→(dead); formal 70 s observation recorded; PID_STABILITY_60S=fail; FATAL_CRASH_LOOP=true; root cause isolated statically on host — R8 obfuscated away the manifest-referenced `SystemUIApplication`, absent from both DEX files)

Record package scan state, PID before/after, and repeated PID checks over at least 60
seconds. Capture crash/fatal/watchdog/PackageManager/SystemUI logs. Detect repeated PID
turnover or boot animation loops explicitly.

- [x] **Step 2: Exercise basic UI** (BASIC_UI=fail: post-replacement UI dump had 1 node with zero SystemUI windows vs 93 baseline; statusbar mDisableRecords 2→0; screenshots preserved as evidence and intentionally not model-read per replacement-session instructions — all conclusions from UI XML/dumpsys/file facts)

Use `android layout` as primary inspection and screenshots as visual evidence. Check:

- boot reaches the launcher/lockscreen;
- status bar renders;
- quick settings can expand;
- keyguard/screen transition remains responsive;
- `dumpsys` reports SystemUI services without a fatal loop.

Visually inspect every captured screenshot before drawing a conclusion.

- [x] **Step 3: Assign one outcome** — `RUNTIME_FAIL` (replacement executed; artifact intrinsically cannot instantiate its Application class; mismatch facts SIGNATURE_MATCH=false / FRAMEWORK_RES_MATCH=false preserved independently)

Exactly one:

```text
RUNTIME_PASS
RUNTIME_FAIL
ENVIRONMENT_BLOCKED
```

A pass requires replacement loaded, stable process, no fatal loop, and all basic UI
checks. Preserve mismatch facts independently.

## Task 6: Rollback and cleanup

- [x] **Step 1: Restore or discard** (rollback proof: direct file restore hit ENOSPC on the 79 MB overlay scratch; overlay-whiteout deletion restored pristine base bytes exactly — on-device hash == pulled original; but PackageManager retained data stayed poisoned, so full recovery completed via `emu kill` + `-wipe-data` restart: original SystemUI proven stable, PID stable 60 s, clean logs, UI dump identical to baseline; AVD then force-stopped and removed)

If useful for rollback proof, remount and restore the original pulled APK, then verify
boot. Otherwise stop the emulator and remove the dedicated AVD. A failed/boot-looping
AVD may be force-stopped and removed.

- [x] **Step 2: Prove host/device scope** (`adb devices -l` empty; `-list-avds` 0 AVDs; no emulator process; PHYSICAL_DEVICE_MUTATIONS=0, PREEXISTING_AVD_MUTATIONS=0, DEDICATED_AVD_REMAINS=0; retained download listed: `system-images;android-37.0;google_apis;x86_64` ~4.4 GB)

Record final AVD list and `adb devices -l`. Report:

```text
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
```

Downloaded SDK packages may remain and must be listed with approximate disk use.

## Task 7: Documentation and repository checks

- [x] **Step 1: Publish exact evidence** (`docs/architecture/2026-08-21-device-systemui-runtime-preflight.md` — environment, exact commands, session lineage, compatibility, runtime data, rollback, cleanup, evidence index; `/tmp/task048-*` retained)

Separate commands actually executed from rejected/unused alternatives. Include exit
codes, timestamps, serial/AVD identity, hashes, certs, log paths, screenshots, result,
and cleanup proof.

- [x] **Step 2: Scope checks** (`git diff --check` clean; `git status --short` shows only the four allowed documentation paths)

```bash
git diff --check
git status --short
```

Expected: only File map documentation paths changed. No Gradle or project implementation
file changed.

- [x] **Step 3: Commit and hand off** (one English commit, no push; `HANDOFF:` block at session end)

Commit in English without pushing. Keep `/tmp/task048-*` evidence until architect review.
Finish with a `HANDOFF:` stating outcome, exact image/AVD, replacement path, compatibility,
runtime checks, rollback/cleanup, and remaining blockers.
