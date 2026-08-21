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

- [ ] **Step 1: Verify the frozen APK**

```bash
test -f /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
stat -c '%s' /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
sha256sum /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
/home/conv/Android/Sdk/build-tools/37.0.0/apksigner verify --print-certs \
  /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk
```

Expected exact size/hash above. Any mismatch stops the task.

- [ ] **Step 2: Record tools, AOSP target facts, existing AVDs/devices**

Run `android --version`, `android --sdk=/home/conv/Android/Sdk info`, Android CLI SDK and
emulator listings, official tool versions, and `adb devices -l`. Capture existing AVDs
before creation so none can be mistaken for the disposable target.

- [ ] **Step 3: Select/install a rootable image**

Prefer an AOSP/default x86_64 image closest to the AOSP platform/API; reject Google Play
images. Use Android CLI SDK install with explicit `--sdk` when possible. Network/package
failure is evidence; try only documented viable candidates and do not delete shared
packages.

## Task 2: Create and identity-gate one disposable AVD

- [ ] **Step 1: Create a unique AVD**

Name it `sysui-gradle-task048-<api>-<timestamp>`. Use Android CLI create when it permits
exact image/name selection; otherwise use official `avdmanager` and record the CLI
capability gap. Do not overwrite an existing AVD.

- [ ] **Step 2: Start cold with writable system**

If Android CLI start cannot carry `-writable-system -no-snapshot`, use the official
emulator binary. Wait for device and `sys.boot_completed=1`; capture startup logs.

- [ ] **Step 3: Freeze the mutation target**

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

- [ ] **Step 1: Collect device/platform facts**

Record fingerprint, API, build type/tags, debuggable/verity state, SELinux, boot state,
SystemUI package/path/version/signing data, framework-res path/hash, PID, dumpsys,
status-bar baseline, screenshot, and layout.

- [ ] **Step 2: Pull original artifacts**

Pull every `pm path com.android.systemui` APK and `/system/framework/framework-res.apk`
under `/tmp/task048-<avd>/baseline/`; record source path, size, SHA-256, ZIP/signature
status. These are the rollback and compatibility evidence.

- [ ] **Step 3: Compare compatibility**

Compare full signer certificate SHA-256 and framework-res SHA-256 with project/AOSP
inputs. Record `SIGNATURE_MATCH=true|false|unknown` and
`FRAMEWORK_RES_MATCH=true|false|unknown` before replacement.

## Task 4: Establish writable system and replace SystemUI

- [ ] **Step 1: Root/remount**

Run `adb -s SERIAL root`; reconnect and re-run the identity gate. Attempt
`disable-verity` plus reboot if remount requires it, re-running the identity gate after
every reconnect. Require `adb remount` success before push.

- [ ] **Step 2: Push to the discovered path**

Use the actual base APK path from `pm path`, not a guessed `priv_app`/`priv-app` path.
Push the frozen APK, then set original owner/group/mode and run `restorecon` on the file
and parent as needed. Run `sync` and verify on-device size/hash before restart.

- [ ] **Step 3: Activate replacement**

Clear/capture a logcat boundary, then use the least disruptive effective method: kill
SystemUI and wait for system_server restart; reboot if package rescanning or mount state
requires it. Every reconnect repeats the identity gate.

## Task 5: Functional runtime acceptance

- [ ] **Step 1: Prove package/process stability**

Record package scan state, PID before/after, and repeated PID checks over at least 60
seconds. Capture crash/fatal/watchdog/PackageManager/SystemUI logs. Detect repeated PID
turnover or boot animation loops explicitly.

- [ ] **Step 2: Exercise basic UI**

Use `android layout` as primary inspection and screenshots as visual evidence. Check:

- boot reaches the launcher/lockscreen;
- status bar renders;
- quick settings can expand;
- keyguard/screen transition remains responsive;
- `dumpsys` reports SystemUI services without a fatal loop.

Visually inspect every captured screenshot before drawing a conclusion.

- [ ] **Step 3: Assign one outcome**

Exactly one:

```text
RUNTIME_PASS
RUNTIME_FAIL
ENVIRONMENT_BLOCKED
```

A pass requires replacement loaded, stable process, no fatal loop, and all basic UI
checks. Preserve mismatch facts independently.

## Task 6: Rollback and cleanup

- [ ] **Step 1: Restore or discard**

If useful for rollback proof, remount and restore the original pulled APK, then verify
boot. Otherwise stop the emulator and remove the dedicated AVD. A failed/boot-looping
AVD may be force-stopped and removed.

- [ ] **Step 2: Prove host/device scope**

Record final AVD list and `adb devices -l`. Report:

```text
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
```

Downloaded SDK packages may remain and must be listed with approximate disk use.

## Task 7: Documentation and repository checks

- [ ] **Step 1: Publish exact evidence**

Separate commands actually executed from rejected/unused alternatives. Include exit
codes, timestamps, serial/AVD identity, hashes, certs, log paths, screenshots, result,
and cleanup proof.

- [ ] **Step 2: Scope checks**

```bash
git diff --check
git status --short
```

Expected: only File map documentation paths changed. No Gradle or project implementation
file changed.

- [ ] **Step 3: Commit and hand off**

Commit in English without pushing. Keep `/tmp/task048-*` evidence until architect review.
Finish with a `HANDOFF:` stating outcome, exact image/AVD, replacement path, compatibility,
runtime checks, rollback/cleanup, and remaining blockers.
