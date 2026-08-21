# Disposable-emulator SystemUI runtime validation — execution record (Task 048)

> Environment, exact commands, compatibility facts, runtime evidence, rollback, and cleanup
> for the first privileged on-device execution of the frozen Release APK.
> Spec: `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`.
> Brief: `docs/orchestration/tasks/048-device-systemui-runtime-preflight.md`.
> Evidence root (retained for architect review): `/tmp/task048-task048-37-20260822-005602`.

## 1. Top-level result

```text
FROZEN_APK=PASS
EMULATOR_ONLY_GATE=PASS
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
OUTCOME=RUNTIME_FAIL
```

Executed-replacement evidence:

```text
ADB_ROOT=success
ADB_REMOUNT=success (verity disabled + overlayfs after one reboot; /system_ext RW)
SYSTEMUI_PATH=/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk (discovered via pm path)
ON_DEVICE_APK_HASH=cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374 (== frozen)
SIGNATURE_MATCH=false
FRAMEWORK_RES_MATCH=false
PID_STABILITY_60S=fail
BASIC_UI=fail
FATAL_CRASH_LOOP=true
```

**Bottom line:** the environment side worked end to end (provision, root, remount, push,
rescan, rollback, cleanup). The replacement APK cannot start its own Application class:
the optimized Release APK's `AndroidManifest.xml` declares
`android:name="com.android.systemui.app.SystemUIApplication"`, but R8 obfuscation renamed
that class away — it does not exist in `classes.dex`/`classes2.dex` (14,238 classes
enumerated with `dexdump`; only 20 `Lcom/android/systemui/*` descriptors survive). The
result is an immediate, intrinsic `ClassNotFoundException` crash loop that is fully
reproducible from the frozen artifact alone (host-side static check, no device needed).
Build acceptance (Task 044/045 static gates) did not cover "manifest-referenced classes
survive minification" — this is the gap Task 048 was designed to expose.

## 2. Session lineage

- **First worker session** (ended early on a model-service 500 while reading a baseline
  screenshot; no repository commit; per its preserved evidence, no root/remount/push yet):
  downloaded the system image, created/started the AVD, passed the identity gate, captured
  baseline facts, dumpsys, UI XML, and a screenshot. All of its outputs live under the
  evidence root and `/tmp/task048-*.txt`; nothing had to be redone except the frozen-APK
  verification, which was re-run from scratch by the replacement session.
- **Replacement session** (this record): re-verified the frozen APK, re-ran the identity
  gate independently, pulled original artifacts, executed the replacement, collected
  runtime evidence, performed rollback + cleanup, and wrote the documentation.

## 3. Environment and tooling

| Item | Value |
|------|-------|
| SDK root | `/home/conv/Android/Sdk` |
| Emulator binary | `/home/conv/Android/Sdk/emulator/emulator` (package 36.6.6) |
| System image (downloaded by this task) | `system-images;android-37.0;google_apis;x86_64` (~4.4 GB; NOT installed before the task — the first worker's `sdklist.txt` "Installed packages" section contains zero system-images entries) |
| AVD (created by this task, now deleted) | `sysui-gradle-task048-37-20260822-005602` |
| Serial | `emulator-5554` |
| Device identity | `google/sdk_gphone64_x86_64/emu64xa:17/CE2A.260420.019/15611780:userdebug/dev-keys`, API 37, userdebug, `ro.debuggable=1`, SELinux Enforcing, `vm.partition.image=overlay` |
| Host tools | `adb`, emulator binary, `avdmanager`, `aapt2`, `apksigner`, `dexdump` (build-tools 37.0.0), `keytool` |

CLI fallback record: image download/AVD creation/startup were performed by the first
worker session using the official SDK tools (`sdkmanager`/`avdmanager`/emulator binary);
its exact commands are not reconstructible beyond the preserved logs, so all replacement
session operations below were executed with official tools directly and are listed in
full. Screenshots were captured with `adb exec-out screencap` and preserved as evidence
but were **not** model-read (the first session died on model image-reading; all UI
conclusions here come from UI XML dumps, dumpsys, and file facts).

## 4. Frozen APK verification (re-run from scratch)

```text
$ stat -c '%s' .../app-release.apk        -> 28600808
$ sha256sum .../app-release.apk           -> cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374
$ apksigner verify --print-certs          -> V2 signer cert SHA-256 c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8
$ keytool -list -keystore keystore/platform.keystore -> SHA256 C8:A2:E9:BC:...:2A:B8 (match)
```

Additional manifest facts discovered from the frozen APK (relevant to follow-up work):
`sharedUserId=android.uid.systemui`, `minSdk=35 targetSdk=35` (image is API 37),
`android:testOnly=true`, `versionCode`/`versionName` empty (parses as `0`/`null` on
device, while the image's SystemUI is `versionCode=37 versionName=17`).

## 5. Identity gate (re-run independently by the replacement session)

Re-executed before the first mutation and after **every** reconnect/reboot (five PASS
runs total). Machine-checkable form used:

```text
SERIAL=emulator-5554            (matches emulator-*)
RO_KERNEL_QEMU=1
AVD_NAME=sysui-gradle-task048-37-20260822-005602   (starts sysui-gradle-task048-)
EMULATOR_ONLY_GATE=PASS
```

No mutating ADB command preceded the first PASS; no gate run ever failed.

## 6. Baseline and rollback material

```text
pm path com.android.systemui -> package:/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk
original SystemUIGoogle.apk : 49,841,504 B, sha256 a6340f94dc027dc396a891b2ddb78997a9470e863e1f35cbb9568e6edfb01304
                              (pulled to baseline/, unzip -t OK)
framework-res.apk           : 37,160,781 B, sha256 0203794633d0012ff28741a80fd11217d71f7921bfbfe17b61941ec4deea89a0
                              (pulled to baseline/, unzip -t OK)
baseline SystemUI PID       : 1126 (stable)
baseline statusbar          : mDisableRecords.size=2
baseline UI dump            : 93 nodes (packages: bard 41, nexuslauncher 35, quicksearchbox 17)
```

Compatibility (recorded **before** replacement):

- `SIGNATURE_MATCH=false` — on-device APK signer cert SHA-256
  `301aa3cb081134501c45f1422abc66c24224fd5ded5fdc8f17e697176fd866aa` (Google platform
  key of the emulator image) vs frozen APK `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`
  (project `platform.keystore`, AOSP test platform key).
- `FRAMEWORK_RES_MATCH=false` — on-device `02037946…` (37,160,781 B) vs project AOSP
  `out/target/product/generic_arm64/.../framework-res.apk` `7e76ce7d…` (36,079,832 B).

Per the brief these mismatches do not block the disposable experiment but can never be
reported as product-compatible success.

## 7. Replacement execution

1. `adb root` → `restarting adbd as root` (uid=0).
2. `adb remount` → verity disabled + overlayfs enabled, required reboot; after reboot
   `adb remount` → `Remounted /system_ext as RW … Remount succeeded`. Identity gate
   re-run and PASSed after each reconnect.
3. Push via staging + in-place copy (never a guessed path):
   ```bash
   adb push app-release.apk /data/local/tmp/task048-systemui.apk
   adb shell 'dd if=/data/local/tmp/task048-systemui.apk of=/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk bs=4194304 && sync'
   adb shell 'chown root:root ...; chmod 644 ...; restorecon ...; restorecon <parent>; sync'
   # verify: -rw-r--r-- root root u:object_r:system_file:s0  28600808
   # on-device sha256sum -> cd4b885e... (exact frozen match)
   ```
4. Activation attempt A (least disruptive): logcat cleared, SystemUI killed (pid 896).
   Result: crash loop #1 — `ClassNotFoundException:
   com.android.systemui.application.impl.SystemUIApplicationImpl`. The cached
   PackageManager metadata still pointed at Google's Application class; 377 crash
   entries. Kill-only restart is insufficient after an in-place APK swap.
5. Activation attempt B: reboot → PackageManager rescan succeeded:
   `/system_ext/priv-app/SystemUIGoogle changed; collecting certs` +
   `System package com.android.systemui signature changed; retaining data`.
   Manifest now correctly resolves to our class, but crash loop #2:
   `ClassNotFoundException: com.android.systemui.app.SystemUIApplication`
   (5,434 entries in the post-reboot logcat). PID churn (896→7977→3184→3203→…→13922→
   17427→20246→22864→…), then ActivityManager stopped restarting the process.

## 8. Root cause (static, host-side, reproducible without any device)

```bash
unzip -p app-release.apk classes.dex  > /tmp/task048-dex-classes.dex
unzip -p app-release.apk classes2.dex > /tmp/task048-dex-classes2.dex
dexdump classes.dex  | grep 'Class descriptor' | grep -i systemuiapplication  -> (none)
dexdump classes2.dex | grep 'Class descriptor' | grep -i systemuiapplication  -> (none)
# classes.dex defines 14,238 classes; strings keeps only 20 'Lcom/android/systemui/' descriptors
aapt2 dump xmltree --file AndroidManifest.xml app-release.apk
#   E: application ... A: android:name="com.android.systemui.app.SystemUIApplication"
```

The manifest-referenced Application class was obfuscated away by R8; the packaged
manifest was not rewritten to the obfuscated name. Consequences: the APK can never
instantiate its Application on any device; `RUNTIME_FAIL` is intrinsic to the artifact,
independent of the signature/framework-res mismatches (those would surface as separate,
later failures). Recommended follow-up (out of Task 048 scope): release builds must keep
manifest-referenced entry classes (AGP normally feeds aapt-generated keep rules for
manifest components — verify why they were missing/ineffective in this project's release
pipeline), and static APK acceptance should assert every manifest-referenced class exists
in the shipped DEX.

## 9. Runtime acceptance data

- `PID_STABILITY_60S=fail` — formal observation: pids 19542→22338→(dead)→28161→31051→
  (dead)→(dead) over 70 s.
- `BASIC_UI=fail` — post-replacement UI dump had 1 node and zero SystemUI windows;
  `dumpsys statusbar` mDisableRecords dropped 2→0 (SystemUI binder clients gone).
  Screenshot preserved (`screens/post-replacement-screen.png`, 125,652 B vs baseline
  1,312,633 B) but not model-read, per replacement-session instructions.
- `FATAL_CRASH_LOOP=true` — 5,422–5,434 `ClassNotFoundException` entries across two
  logcat captures; logs preserved as `logs/replacement-logcat.txt` (37,513 lines) and
  `logs/post-reboot-logcat.txt` (191,011 lines).
- `OUTCOME=RUNTIME_FAIL` — the replacement was executed and the failure is a genuine
  runtime failure of the artifact, not an environment problem.

## 10. Rollback

1. Direct file restore of the pulled original failed with ENOSPC: the overlayfs scratch
   (`/dev/block/dm-5`, 79 MB total, shared by all remounted partitions' upper dirs) held
   the replacement; growing the file back to 49,841,504 B stopped at 35,467,264 B
   ("No space left on device"). Even `rm` of the target failed until the file was first
   truncated to zero.
2. Overlay-native rollback succeeded: truncate → `rm` created a whiteout; the whiteout
   char device at `/mnt/scratch/overlay/system_ext/upper/priv-app/SystemUIGoogle/
   SystemUIGoogle.apk` was deleted directly; after reboot the merged view exposed the
   pristine base image file — on-device sha256 `a6340f94…` == pulled baseline (exact
   byte-for-byte restoration, zero scratch space needed).
3. **Poisoned-state finding:** even with the original APK bytes and original signature
   (`b2d95fc0`) restored, SystemUI kept crash-looping on OUR class name, because the
   earlier signature flip-flop left PackageManager's retained data poisoned
   (`versionCode=0`, `versionName=null`, Application class still
   `com.android.systemui.app.SystemUIApplication`). In-place APK rollback does **not**
   undo PackageManager retained state after a system-package signature change.
4. Full recovery via userdata wipe: `adb emu kill`, restart with
   `-wipe-data -no-snapshot -no-window -gpu swiftshader_indirect`; pristine boot gave:
   original hash, `veritymode=enforcing` (no overlay), `versionCode=37 versionName=17`,
   signatures `b2d95fc0`, SystemUI PID 1131 stable across 60 s,
   `mDisableRecords.size=2`, zero `ClassNotFoundException`, and a UI dump identical to
   the baseline (93 nodes, same package distribution). Rollback proven; logs/screens
   preserved (`logs/rollback-verified-logcat.txt`, `screens/rollback-verified-*`).

## 11. Cleanup proof

```text
$ adb devices -l          -> List of devices attached (empty)
$ emulator -list-avds     -> (no output; 0 AVDs)
$ avdmanager delete avd -n sysui-gradle-task048-37-20260822-005602 -> AVD deleted
$ pgrep qemu/emulator     -> none
PHYSICAL_DEVICE_MUTATIONS=0    (no physical device was ever attached)
PREEXISTING_AVD_MUTATIONS=0    (the only AVD ever present was the one this task created)
DEDICATED_AVD_REMAINS=0        (deleted; emulator stopped; 0 AVDs remain)
```

Downloaded SDK package retained (allowed, listed): `system-images;android-37.0;
google_apis;x86_64` ≈ 4.4 GB. Evidence retained under `/tmp/task048-*` (152 MB) for
architect review.

## 12. Evidence index

```text
/tmp/task048-task048-37-20260822-005602/
  baseline/device-facts.txt                 fingerprint, API, build, verity, pm path, signatures, baseline PID
  baseline/pm-path.txt                      discovered SystemUI path
  baseline/SystemUIGoogle.apk               pulled original (rollback artifact, hash-verified)
  baseline/framework-res.apk                pulled framework-res
  baseline/baseline-ui.xml, screens/baseline-home.png   first-session baseline UI
  baseline/dumpsys-services.txt, baseline/dumpsys-statusbar.txt
  logs/emulator-startup.log                 first-session AVD startup (boot 26.3 s)
  logs/replacement-logcat.txt               crash loop #1 (kill-only restart)
  logs/post-reboot-logcat.txt               crash loop #2 (after rescan)
  logs/rollback-logcat.txt                  poisoned-state crash loop after file rollback
  logs/rollback-verified-logcat.txt         pristine boot after wipe (clean)
  logs/wipe-restart-emulator.log            -wipe-data restart
  screens/post-replacement-ui.xml, post-replacement-screen.png, dumpsys-statusbar-post.txt
  screens/rollback-ui.xml, rollback-verified-ui.xml, rollback-verified-screen.png,
         dumpsys-statusbar-rollback-verified.txt
/tmp/task048-avd.txt, task048-avd-name.txt, task048-evidence-dir.txt, task048-sdklist.txt
```
