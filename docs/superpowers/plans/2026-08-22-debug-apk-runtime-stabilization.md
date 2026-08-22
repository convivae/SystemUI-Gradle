# Debug APK Runtime Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:systematic-debugging and the android-cli skill. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, push, diagnose, and minimally fix the Debug APK until real SystemUI runtime and basic UI interaction are stable, then hand the proven changes back for review and repository push.

**Architecture:** Use one dedicated disposable API 37 AVD throughout the Debug diagnose/fix loop. Keep build, packaged-manifest/DEX, on-device hash, process, logcat, and UI-interaction evidence at every boundary; change one evidenced root cause at a time. Release is explicitly outside this plan.

**Tech Stack:** Gradle/AGP Debug build, Android SDK emulator, ADB root/remount/push, apkanalyzer, dexdump, logcat, dumpsys, Android CLI layout/screen tools.

**Spec:** `docs/issues/2026-08-22-debug-apk-runtime-stabilization.md`

## Global Constraints

- At most one Gradle build runs anywhere; use `-Dorg.gradle.workers.max=4`.
- Only a newly created `sysui-gradle-task049-debug-*` AVD may be mutated.
- Repeat the serial/qemu/AVD-name identity gate before mutation after every reconnect.
- No Release build or Release APK validation.
- No stubs, source exclusion, broad suppression, disabled checks, fabricated resources,
  or unapproved AOSP source/res changes.
- Every fix requires a written single hypothesis and pre-fix evidence.
- Worker commits in English and never pushes.

---

## Task 1: Fresh Debug artifact and static boundary

- [ ] Run `./gradlew :app:assembleDebug -Dorg.gradle.workers.max=4 --console=plain`
  under `set -o pipefail` with output retained under `/tmp/task049-*`; require exit 0.
- [ ] Freeze `app/build/outputs/apk/debug/app-debug.apk` size and SHA-256.
- [ ] Extract the packaged manifest Application/component FQNs and enumerate DEX classes.
- [ ] Record whether every manifest entry class exists in Debug DEX; do not fix yet.

## Task 2: Dedicated AVD and baseline

- [ ] Inventory `adb devices -l` and existing AVDs without mutating them.
- [ ] Create/start one `sysui-gradle-task049-debug-*` AVD from the installed API 37
  rootable image with writable-system/no-snapshot controls.
- [ ] Prove `emulator-*`, `ro.kernel.qemu=1`, and exact AVD prefix before any mutation.
- [ ] Discover SystemUI with `pm path`, pull/hash the original APK and framework-res,
  and capture baseline PID/logcat/dumpsys/layout/screenshot.

## Task 3: First Debug push and reproduction

- [ ] Root/remount, repeating the identity gate after each reconnect/reboot.
- [ ] Push the Debug APK to the discovered base path, restore owner/mode/SELinux context,
  sync, and verify the on-device SHA-256 equals the frozen Debug artifact.
- [ ] Activate package rescan/SystemUI restart and observe PID/logcat for at least 60 seconds.
- [ ] Record `DEBUG_RUNTIME_PASS`, `DEBUG_RUNTIME_FAIL`, or `ENVIRONMENT_BLOCKED` with
  exact exception/PID evidence.

## Task 4: Evidence-driven fix loop

- [ ] For the first reproduced product defect, add one hypothesis/evidence entry to the issue.
- [ ] Add the smallest static regression check that fails on the reproduced defect when a
  durable check is practical; otherwise preserve a deterministic APK inspection command.
- [ ] Apply exactly one minimal fix within allowed paths. If the fix requires a red-line
  area, stop with `REDLINE:` before editing.
- [ ] Re-run the relevant cheap/static test, fresh Debug build, APK inspection, ADB push,
  process observation, and logcat check.
- [ ] Repeat only for a newly evidenced next root cause; after three failed fix hypotheses,
  stop and escalate architecture rather than attempting a fourth speculative fix.

## Task 5: UI stability acceptance

- [ ] Require one stable SystemUI PID for 60 seconds after the final push.
- [ ] Expand/collapse notification shade and Quick Settings; capture layout/screenshot.
- [ ] Lock, wake, and unlock; return to launcher; verify SystemUI PID remains unchanged.
- [ ] Capture a clean post-interaction logcat boundary and assert no new SystemUI fatal,
  crash loop, watchdog restart, or ANR.
- [ ] Print the complete acceptance block with `DEBUG_RUNTIME_PASS` only if every gate passes.

## Task 6: Cleanup, docs, and handoff

- [ ] Stop/delete the dedicated AVD and prove zero remaining Task 049 AVD/device/process.
- [ ] Update the issue with builds, hypotheses, fixes, hashes, runtime/UI evidence, and cleanup.
- [ ] Run `git diff --check`, scope checks, and all relevant non-Gradle tests.
- [ ] Commit focused changes in English; do not push.
- [ ] Finish with a terminal `HANDOFF:` containing actual commands/results and remaining work.

## Acceptance block

```text
DEBUG_BUILD=PASS
DEBUG_APK_HASH=<sha256>
MANIFEST_ENTRY_DEX_CLOSURE=PASS
EMULATOR_ONLY_GATE=PASS
ON_DEVICE_APK_HASH_MATCH=true
SYSTEMUI_PID_STABLE_60S=pass
STATUS_BAR_INTERACTION=pass
QUICK_SETTINGS_INTERACTION=pass
LOCK_WAKE_UNLOCK=pass
POST_INTERACTION_FATAL_CRASH=false
PHYSICAL_DEVICE_MUTATIONS=0
PREEXISTING_AVD_MUTATIONS=0
DEDICATED_AVD_REMAINS=0
OUTCOME=DEBUG_RUNTIME_PASS
RELEASE_BUILD_OR_PUSH=NOT_RUN
```
