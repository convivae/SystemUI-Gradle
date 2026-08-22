# Disposable-emulator SystemUI runtime validation — execution record (Task 048)

> Environment, exact commands, compatibility facts, runtime evidence, rollback, and cleanup
> for the first privileged on-device execution of the frozen Release APK.
> Spec: `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`.
> Brief: `docs/orchestration/tasks/048-device-systemui-runtime-preflight.md`.
> Evidence root used for Worker/reviewer/architect acceptance: `/tmp/task048-task048-37-20260822-005602`.
> It was retained intact through final acceptance, then removed with the other `/tmp/task048-*`
> artifacts during post-push cleanup on 2026-08-22; the evidence index below is historical.

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
rescan, rollback, cleanup). The replacement APK cannot start its own Application class,
for two independent defects of the same entry point (static, host-side, reproducible
without any device):

1. **Manifest namespace/class mismatch (the immediate launch failure).** The source
   manifest declares `android:name=".SystemUIApplication"` and the `:app` module's AGP
   namespace is `com.android.systemui.app`, so the packaged manifest expands the
   relative name to `com.android.systemui.app.SystemUIApplication` — an FQN that **never
   existed as a source class**. The real class is `com.android.systemui.SystemUIApplication`
   (`SystemUI-core/src/com/android/systemui/SystemUIApplication.java`, matching AOSP).
   The classloader therefore fails before anything else can run.
2. **R8 also obfuscates the real Application class.** `mapping.txt` (line 453874) maps
   `com.android.systemui.SystemUIApplication -> kvc`, and `Lkvc;` is present in the
   shipped DEX — so even with a namespace-aligned manifest, instantiation would still
   fail unless the manifest were rewritten to the obfuscated name or the manifest-entry
   class were kept.

DEX facts (corrected): the shipped DEX contains **602** `Lcom/android/systemui/*` class
descriptors (600 in `classes.dex` + 2 in `classes2.dex`; 15,683 classes total across
both files) — an earlier draft of this report said "only 20", which was an artifact of
sampling the DEX string table with `strings` instead of enumerating class definitions
with `dexdump`. No `SystemUIApplication` descriptor exists in either DEX file (neither
the nonexistent `com.android.systemui.app.` FQN nor the real one, which R8 renamed to
`kvc`).

The result is an immediate, intrinsic `ClassNotFoundException` crash loop that is
fully reproducible from the frozen artifact alone. Build acceptance (Task 044/045
static gates) did not cover "manifest-referenced classes exist and survive
minification" — this is the gap Task 048 was designed to expose.

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
full.

**Screenshot policy provenance:** the first worker session ended on a model-service 500
while model-reading a baseline screenshot. The architect's replacement-session
dispatch instruction therefore superseded visual model-reading: "Do not retry model
image-reading; preserve screenshots as evidence and use UI XML/dumpsys/file checks."
Screenshots were captured with `adb exec-out screencap` and retained as evidence, but
were never model-read; every UI conclusion in this record is derived from UI XML dumps,
dumpsys output, logcat, and file facts.

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

Re-executed before the first mutation and after **every** reconnect/reboot. The session
record (verbatim transcript: `logs/replacement-session-verification.txt`) contains
**six** `EMULATOR_ONLY_GATE=PASS` token outputs — after the adb-root reconnect, after
the verity-disable reboot, after the replacement-activation reboot, at rollback start,
after the whiteout-removal reboot, and after the `-wipe-data` restart — plus one earlier
raw-property identity verification (serial / `ro.kernel.qemu` / AVD name, all three
facts confirmed) that **preceded the first mutating command** (`adb root`). An earlier
draft of this report said "five PASS runs total"; that was an undercount — all six are
preserved verbatim in the transcript with JSONL line numbers and timestamps. No gate
run ever failed.

```text
SERIAL=emulator-5554            (matches emulator-*)
RO_KERNEL_QEMU=1
AVD_NAME=sysui-gradle-task048-37-20260822-005602   (starts sysui-gradle-task048-)
EMULATOR_ONLY_GATE=PASS
```

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
   Result: crash loop #1 — the cached PackageManager metadata still pointed at the
   Google image's entry classes: `ClassNotFoundException` on
   `com.android.systemui.application.impl.SystemUIApplicationImpl` and on
   `com.google.android.systemui.SystemUIGoogleAppComponentFactory`, **377 each = 754
   CNF entries total** in `logs/replacement-logcat.txt` (an earlier draft of this
   report quoted only the 377 `SystemUIApplicationImpl` count). Kill-only restart is
   insufficient after an in-place APK swap.
5. Activation attempt B: reboot → PackageManager rescan succeeded:
   `/system_ext/priv-app/SystemUIGoogle changed; collecting certs` +
   `System package com.android.systemui signature changed; retaining data`.
   The manifest now resolves to our packaged (nonexistent) Application FQN, and crash
   loop #2 followed: `ClassNotFoundException: com.android.systemui.app.SystemUIApplication`
   — **5,434 entries, which is every CNF entry in `logs/post-reboot-logcat.txt`**.
   PID churn (896→7977→3184→3203→…→13922→17427→20246→22864→…), then ActivityManager
   stopped restarting the process.

## 8. Root cause (static, host-side, reproducible without any device)

```bash
# packaged manifest (frozen APK)
aapt2 dump xmltree --file AndroidManifest.xml app-release.apk
#   E: application ... A: android:name="com.android.systemui.app.SystemUIApplication"
#   A: android:appComponentFactory=".PhoneSystemUIAppComponentFactory"   (relative, unexpanded)

# source manifest (app/src/main/AndroidManifest.xml, line 397)
#   android:name=".SystemUIApplication"
# app namespace (app/build.gradle.kts, line 16)
#   namespace = "com.android.systemui.app"
#   -> AGP expands ".SystemUIApplication" to com.android.systemui.app.SystemUIApplication

# the real class (never in an .app subpackage):
ls SystemUI-core/src/com/android/systemui/SystemUIApplication.java          # exists
ls SystemUI-core/src/com/android/systemui/app/SystemUIApplication.java     # NOT PRESENT

# R8 mapping (app/build/outputs/mapping/release/mapping.txt, line 453874)
#   com.android.systemui.SystemUIApplication -> kvc

# shipped DEX (dexdump)
#   Lcom/android/systemui/ descriptors: 600 (classes.dex) + 2 (classes2.dex) = 602 total
#   SystemUIApplication descriptor: none in either file; 'Lkvc;' present
```

Two independent defects of the same entry point:

1. **Manifest namespace/class mismatch — the immediate launch failure.** The `:app`
   module's AGP namespace (`com.android.systemui.app`) differs from the AOSP package
   (`com.android.systemui`), and the source manifest's relative
   `android:name=".SystemUIApplication"` was expanded against the **namespace**,
   producing `com.android.systemui.app.SystemUIApplication` — an FQN that never existed
   as a source class. The real class is `com.android.systemui.SystemUIApplication`
   (matching AOSP's location). At runtime the classloader cannot find the manifest FQN,
   so the process dies before `Application.onCreate()`.
2. **R8 obfuscates the real Application class.** `mapping.txt` maps
   `com.android.systemui.SystemUIApplication -> kvc` and `Lkvc;` exists in the shipped
   DEX, so even a namespace-aligned manifest (`com.android.systemui.SystemUIApplication`)
   would still fail unless the manifest were rewritten to the obfuscated name or the
   manifest-entry class were kept through R8.

Note: an earlier draft of this report claimed "R8 obfuscated away the
manifest-referenced Application class". That was wrong — the manifest FQN never existed
as a source class, so R8 could not have obfuscated it; R8 obfuscated the **real** class
under a different FQN. Both the manifest alignment and the manifest-entry keep
semantics require follow-up.

`RUNTIME_FAIL` is intrinsic to the artifact, independent of the signature/framework-res
mismatches (those would surface as separate, later failures). Recommended follow-up
(out of Task 048 scope): align the packaged manifest's Application FQN with the real
class (or move/rename the class to match the expansion), keep manifest-referenced entry
classes through R8 (AGP normally feeds aapt-generated keep rules for manifest
components — verify why they were missing/ineffective in this project's release
pipeline), and add a static APK acceptance check asserting every manifest-referenced
class exists in the shipped DEX.

## 9. Runtime acceptance data

- `PID_STABILITY_60S=fail` — formal observation: pids 19542→22338→(dead)→28161→31051→
  (dead)→(dead) over 70 s.
- `BASIC_UI=fail` — **corrected (an earlier draft claimed the post-replacement UI dump
  had "1 node"; that was a `grep -c 'node'` line-count artifact on single-line XML).
  Actual facts:** baseline, post-replacement, and rollback UI dumps each contain **93
  node elements** (`grep -o '<node' | wc -l`); baseline and post are **not**
  byte-identical (geometry differs) but have the same package distribution (bard 41 /
  nexuslauncher 35 / quicksearchbox 17); and the UI XML is **non-discriminating** for
  SystemUI presence — no `com.android.systemui` package element appears in the baseline
  dump either (SystemUI surfaces are exposed via dumpsys, not uiautomator, when the
  launcher is foregrounded). `BASIC_UI=fail` is therefore supported by the fatal crash
  loop and PID churn, plus `dumpsys statusbar` `mDisableRecords.size` dropping 2→0
  (SystemUI binder clients gone). Screenshots retained
  (`screens/post-replacement-screen.png` 125,652 B vs `screens/baseline-home.png`
  1,312,633 B) as file evidence, not model-read (see §3 screenshot policy).
- `FATAL_CRASH_LOOP=true` — exact per-file counts with exact grep definitions:
  - `logs/replacement-logcat.txt` (37,513 lines): **754** CNF = 377 ×
    `ClassNotFoundException ... "com.android.systemui.application.impl.SystemUIApplicationImpl"`
    + 377 × `ClassNotFoundException ... "com.google.android.systemui.SystemUIGoogleAppComponentFactory"`.
  - `logs/post-reboot-logcat.txt` (191,011 lines): **5,434** CNF, every one
    `ClassNotFoundException: com.android.systemui.app.SystemUIApplication`.
  - `logs/rollback-logcat.txt` (278,228 lines): **6,216** CNF = 3,108 ×
    `ClassNotFoundException ... "com.android.systemui.app.SystemUIApplication"` +
    3,108 × `ClassNotFoundException ... "com.android.systemui.PhoneSystemUIAppComponentFactory"`
    (poisoned PackageManager retained data still naming OUR entry classes against the
    restored original APK).
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
   `mDisableRecords.size=2`, **zero SystemUI Application CNF** in
   `logs/rollback-verified-logcat.txt` (that file still contains 2 unrelated
   non-SystemUI `ClassNotFoundException` entries for
   `com.google.android.settings.display.comfortfilters.ui.ComfortViewDetailsController`
   from a Settings slices-converter warning — "zero CNF" must not be claimed), and a UI
   dump **byte-identical** to the baseline (`cmp` clean; 93 nodes, same package
   distribution). Rollback proven; logs/screens preserved
   (`logs/rollback-verified-logcat.txt`, `screens/rollback-verified-*`).

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
google_apis;x86_64` ≈ 4.4 GB. The `/tmp/task048-*` evidence set (152 MB) remained intact
through corrected dual review and architect fresh acceptance, then was removed during
post-push cleanup. The installed system-image package was not removed.

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
  logs/replacement-session-verification.txt verbatim gate/hash/cleanup transcript extracted
                                           from the GLM-5.3 session JSONL (corrective pass)
  logs/replacement-logcat.txt               crash loop #1 (kill-only restart)
  logs/post-reboot-logcat.txt               crash loop #2 (after rescan)
  logs/rollback-logcat.txt                  poisoned-state crash loop after file rollback
  logs/rollback-verified-logcat.txt         pristine boot after wipe (zero SystemUI CNF)
  logs/wipe-restart-emulator.log            -wipe-data restart
  screens/post-replacement-ui.xml, post-replacement-screen.png, dumpsys-statusbar-post.txt
  screens/rollback-ui.xml, rollback-verified-ui.xml, rollback-verified-screen.png,
         dumpsys-statusbar-rollback-verified.txt
/tmp/task048-avd.txt, task048-avd-name.txt, task048-evidence-dir.txt, task048-sdklist.txt
```

## 13. Corrective pass (2026-08-22, docs/evidence-only)

A dual review (Standards MEDIUM: missing retained gate/on-device-hash transcript;
Spec MEDIUM: false "1-node UI" claim) required this docs/evidence-only corrective
commit. No Gradle, ADB, emulator/AVD, or device operations were run; every
re-verification below is a host-side read-only check.

**Transcript extraction.** All verbatim outputs below were extracted programmatically
from the replacement session's JSONL
(`/home/conv/.pi/agent/sessions/--home-conv-myspace-SystemUI-Gradle-wt-048--/
2026-08-21T17-01-56-423Z_01a02545-a547-7945-b36d-bd3cf7a56e42.jsonl`, session id
`01a02545-a547-7945-b36d-bd3cf7a56e42`, model GLM-5.3, started 2026-08-21T17:01:56Z)
into `logs/replacement-session-verification.txt`, including per-block provenance
(JSONL result/call line numbers, message timestamps, tool name, verbatim command and
output). It contains **six** `EMULATOR_ONLY_GATE=PASS` token outputs plus the initial
raw-property verification that preceded `adb root`, and the actual on-device hash
output `cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374
/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk` (JSONL result line 56).

**Host-side re-verification commands and actual results (2026-08-22):**

```text
$ grep -o '<node' <each UI xml> | wc -l
  baseline/baseline-ui.xml: 93   screens/post-replacement-ui.xml: 93
  screens/rollback-ui.xml: 93    screens/rollback-verified-ui.xml: 93
$ cmp baseline/baseline-ui.xml screens/post-replacement-ui.xml   -> differ: byte 3186, line 1
$ cmp baseline/baseline-ui.xml screens/rollback-verified-ui.xml  -> identical
$ grep -oE 'package="[^"]+"' screens/post-replacement-ui.xml | sort | uniq -c
  -> 41 bard / 35 nexuslauncher / 17 quicksearchbox (same distribution as baseline)
$ grep -c 'package="com.android.systemui"' <each UI xml>       -> 0 in all four (incl. baseline)
$ dexdump classes.dex  | grep 'Class descriptor' | grep -c 'Lcom/android/systemui/'  -> 600
$ dexdump classes2.dex | grep 'Class descriptor' | grep -c 'Lcom/android/systemui/'  -> 2
$ dexdump <both> | grep 'Class descriptor' | grep -i systemuiapplication            -> (none)
$ dexdump <both> | grep 'Class descriptor' | grep -E 'Lkvc;'                        -> present
$ grep -n 'SystemUIApplication' app/build/outputs/mapping/release/mapping.txt
  -> 453874: com.android.systemui.SystemUIApplication -> kvc:
$ grep -n 'android:name="\.SystemUIApplication"' app/src/main/AndroidManifest.xml   -> 397
$ grep -n 'namespace = ' app/build.gradle.kts                                       -> 16: com.android.systemui.app
$ ls SystemUI-core/src/com/android/systemui/SystemUIApplication.java                -> exists
$ ls SystemUI-core/src/com/android/systemui/app/SystemUIApplication.java            -> NOT PRESENT
$ grep -c 'ClassNotFoundException' logs/<file>   (exact per-file counts in §9)
```

**Facts corrected by this pass:** (1) gate transcript retained and the "five PASS runs"
undercount corrected to six token outputs + one initial raw verification; (2) the
"post-replacement UI dump had 1 node" claim replaced by the real 93-node facts and the
`grep -c` line-count artifact explanation; (3) DEX descriptor count corrected from 20
to 602 (600+2); (4) root cause corrected from "R8 obfuscated away the
manifest-referenced class" to the manifest namespace/class mismatch (nonexistent FQN
`com.android.systemui.app.SystemUIApplication` expanded from `.SystemUIApplication`
under the `com.android.systemui.app` namespace) plus the independent fact that R8
renamed the real `com.android.systemui.SystemUIApplication` to `kvc`; (5) crash counts
restated with exact per-file grep definitions, and the rollback-verified log correctly
described as zero **SystemUI Application** CNF (2 unrelated non-SystemUI CNF entries
remain); (6) screenshot-policy provenance recorded (architect instruction after the
model 500 superseded visual model-reading); (7) this verification section added.

The `OUTCOME=RUNTIME_FAIL` verdict and all top-level acceptance tokens are unchanged.
