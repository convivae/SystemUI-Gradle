# 2026-08-22 — Debug APK runtime stabilization

## User direction

Build the Debug APK directly, push it to a disposable emulator, inspect real runtime
errors, and fix them one root cause at a time. Rebuild and push again until SystemUI is
stable and ordinary UI interaction does not crash it. Only after Debug is proven good
may this version be committed/pushed; Release validation is a separate later task.

## Scope

This task is Debug-only. It may build `:app:assembleDebug`, create and mutate one new
`sysui-gradle-task049-debug-*` AVD, and make the smallest repository fixes supported by
runtime evidence. It must not build, push, or validate a Release APK.

## Safety boundary

- Never mutate a physical device, unknown target, pre-existing AVD, or AVD without the
  `sysui-gradle-task049-debug-*` prefix.
- Before every mutation/reconnect, require serial `emulator-*`, `ro.kernel.qemu=1`, and
  the exact dedicated AVD-name prefix.
- Discover the SystemUI APK with `pm path com.android.systemui`; never guess it.
- Pull/hash the original APK before replacement and remove the disposable AVD at the end.
- Existing API 37 `google_apis;x86_64` system image may be reused; do not remove shared
  SDK packages.

## Diagnosis discipline

1. Fresh-build Debug and freeze its size/SHA-256.
2. Record packaged manifest entry classes and DEX class presence before device mutation.
3. Reproduce the runtime behavior and collect complete logcat/PID/dumpsys evidence.
4. Before each fix, write one explicit hypothesis and the evidence supporting it.
5. Apply one minimal fix, rebuild, push, and retest. Do not stack speculative fixes.
6. Any required AOSP-mirrored source/res edit, resource creation, stub, module-boundary
   change, or broad R8/build bypass remains a REDLINE requiring user approval.

## Debug runtime acceptance

`DEBUG_RUNTIME_PASS` requires all of:

- pushed on-device APK hash equals the fresh Debug artifact hash;
- packaged Application and manifest component classes resolve to classes present in DEX;
- SystemUI PID remains stable for at least 60 seconds after package activation;
- no repeated fatal exception, crash loop, watchdog restart, or SystemUI ANR;
- status bar expands/collapses, Quick Settings expands/collapses, and lock/wake/unlock
  interaction completes while SystemUI remains stable;
- post-interaction logcat contains no new SystemUI fatal crash;
- original device/AVD scope is untouched and the dedicated AVD is removed after evidence.

A launcher screen alone, a single PID sample, or a successful build is not a pass.

## Current hypothesis, not yet a fix

Task 048 proved the Release APK manifest references
`com.android.systemui.app.SystemUIApplication` while the real source class is
`com.android.systemui.SystemUIApplication`. The Debug experiment must independently
show whether the same manifest-resolution defect exists without R8. No build or manifest
change is allowed merely because Release showed it.

## Build reporting

Use serialized Gradle with `-Dorg.gradle.workers.max=4`, `set -o pipefail`, and retained
logs. Report every build/rebuild command and exit code truthfully. Debug success does not
imply Release success; Release remains pending after this task.
