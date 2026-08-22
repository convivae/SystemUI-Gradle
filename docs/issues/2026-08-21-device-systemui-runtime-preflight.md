# 2026-08-21 — Disposable-emulator SystemUI runtime validation

## Status

Exact execution scope approved by the user on 2026-08-21. Task 048 may provision and
fully mutate one dedicated disposable Android emulator, including SDK/system-image
download, AVD creation/removal, `adb root`, verity/remount, APK replacement, process
restart, reboot, and rollback. Physical devices and pre-existing AVDs remain outside
scope.

**EXECUTED 2026-08-21/22 (two worker sessions; see
`docs/architecture/2026-08-21-device-systemui-runtime-preflight.md` for the full
record).** Final result:

```text
FROZEN_APK=PASS  EMULATOR_ONLY_GATE=PASS  PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0  DEDICATED_AVD_REMAINS=0  OUTCOME=RUNTIME_FAIL
ADB_ROOT=success  ADB_REMOUNT=success
SYSTEMUI_PATH=/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk
ON_DEVICE_APK_HASH=cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374
SIGNATURE_MATCH=false  FRAMEWORK_RES_MATCH=false
PID_STABILITY_60S=fail  BASIC_UI=fail  FATAL_CRASH_LOOP=true
```

Root cause (host-side static, reproducible without a device; corrected 2026-08-22): two
independent defects of the same entry point. (1) **Manifest namespace/class mismatch**
— the source manifest's `android:name=".SystemUIApplication"` was expanded by AGP
against the `:app` namespace `com.android.systemui.app`, producing the packaged FQN
`com.android.systemui.app.SystemUIApplication`, which never existed as a source class
(the real class is `com.android.systemui.SystemUIApplication`, matching AOSP); this is
the immediate `ClassNotFoundException` launch failure. (2) **R8 obfuscates the real
Application class** — `mapping.txt` maps `com.android.systemui.SystemUIApplication ->
kvc` (`Lkvc;` present in DEX), so even a namespace-aligned manifest would fail unless
the manifest were rewritten to the obfuscated name or the class kept. The shipped DEX
contains 602 `Lcom/android/systemui/*` descriptors (600+2, not the "20" an earlier
draft claimed — that was a `strings` sampling artifact). Follow-up work (outside Task
048): fix manifest alignment AND manifest-entry keep semantics, and add a static APK
acceptance check asserting every manifest-referenced class exists in the shipped DEX.
A verbatim gate/hash/cleanup transcript extracted from the worker session JSONL is
retained at `logs/replacement-session-verification.txt` (six `EMULATOR_ONLY_GATE=PASS`
outputs plus the initial pre-mutation raw-property verification).

Rollback findings: (1) the overlayfs scratch (79 MB) is smaller than the original APK,
so direct file restore hits ENOSPC — the working overlay-native rollback is deleting
the whiteout in `/mnt/scratch/overlay/system_ext/upper/...`, which restores the pristine
base-image bytes exactly; (2) after a system-package signature flip-flop, in-place file
rollback does not undo poisoned PackageManager retained state
(`versionCode=0`/`versionName=null`/className still ours) — full recovery required a
`-wipe-data` restart, after which the original SystemUI was proven stable (PID stable
60 s, zero SystemUI Application CNF — 2 unrelated non-SystemUI CNF entries remain —
and a UI dump byte-identical to baseline).

Dedicated AVD `sysui-gradle-task048-37-20260822-005602` was stopped and deleted;
evidence retained under `/tmp/task048-*`.

## Background

Debug and optimized Release APKs build and pass static package acceptance, but no
runtime validation has replaced the platform SystemUI. SystemUI is a privileged,
platform-signed package under `/system_ext`; ordinary `adb install` is not representative.
A meaningful experiment must use a rootable writable emulator and replace the exact
preinstalled APK path.

The user explicitly accepted the disposable nature of this experiment: a failed or
boot-looping dedicated AVD may be deleted and recreated. This authorization removes the
previous read-only and second-approval gates for Task 048, but only inside the dedicated
emulator boundary.

## Hard safety boundary

Before the first mutating ADB command, all three conditions must be true:

1. serial matches `emulator-*`;
2. `adb -s SERIAL shell getprop ro.kernel.qemu` returns `1`;
3. the resolved AVD name starts with `sysui-gradle-task048-`.

A physical device, unknown serial, or pre-existing AVD must never receive a mutating
command. That condition is a REDLINE despite the broad emulator authorization.

## Steps

1. Inspect AOSP/API facts and available rootable images using
   `android --sdk=/home/conv/Android/Sdk`; install an appropriate emulator/system image
   if needed.
2. Create one uniquely named dedicated AVD. Use official SDK tools as a documented
   fallback when Android CLI cannot express the required system image, name, or
   `-writable-system` startup option.
3. Start cold and writable; verify the three-part emulator identity gate.
4. Capture baseline boot, package path, APK/framework-res hashes, signing certificates,
   SystemUI PID, UI screenshot/layout, and logs. Pull the original APK to `/tmp`.
5. Use `adb root`, `adb disable-verity`/reboot if needed, and `adb remount`.
6. Push the already accepted Release APK to the exact path returned by
   `pm path com.android.systemui`; restore root ownership, mode, and SELinux context;
   sync and restart/reboot as required.
7. Verify package acceptance, stable SystemUI PID, absence of a fatal crash loop,
   status bar, quick settings, lockscreen/basic UI, dumpsys, screenshot/layout, and logs.
8. Report signature/framework compatibility independently from observed behavior. A
   mismatch experiment may run, but cannot be described as product-compatible success.
9. Roll back by restoring the pulled APK when practical, or stop and delete the
   dedicated AVD. Preserve evidence under `/tmp/task048-*` until architect acceptance.

## Runtime outcomes

Exactly one top-level outcome must be reported:

- `RUNTIME_PASS`: replacement loaded, SystemUI remained stable, and basic UI checks passed;
- `RUNTIME_FAIL`: replacement was executed but crashed, failed scan/start, or failed UI checks;
- `ENVIRONMENT_BLOCKED`: no suitable image/AVD could be provisioned or root/remount could
  not be established.

No mismatch or failed replacement may be called a pass.

## Error-count evolution

Not applicable. No repository implementation change is allowed. The accepted APK is
used directly; Gradle is not run by this task.

## Open questions

None for the dedicated emulator experiment. Any physical-device operation, mutation of
a pre-existing AVD, project source/build change, or attempt to use an APK other than the
accepted artifact requires separate approval.

New follow-ups surfaced by execution (require architect/user direction, not Task 048
scope):

1. Release APK manifest/application entry point is doubly broken: the packaged manifest
   references a nonexistent FQN (`com.android.systemui.app.SystemUIApplication` — a
   namespace-expansion artifact), and R8 renames the real
   `com.android.systemui.SystemUIApplication` to `kvc`; both manifest alignment and
   manifest-entry keep semantics require fixing, and static APK acceptance should
   assert manifest-referenced classes exist in shipped DEX.
2. Frozen APK carries `android:testOnly=true`, empty `versionCode`/`versionName`, and
   `targetSdk=35` on an API 37 image — decide which of these (if any) should be
   adjusted for future runtime validation rounds.
3. `SIGNATURE_MATCH=false` (Google platform key vs project AOSP test platform key) and
   `FRAMEWORK_RES_MATCH=false` remain true blockers for any product-compatible
   runtime claim; a truly compatible validation needs an AOSP-built (or identically
   keyed) system image.
