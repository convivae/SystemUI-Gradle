# Device and SystemUI Runtime Preflight Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use the android-cli skill and superpowers:executing-plans to execute this read-only preflight task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether any connected device or existing AVD is a viable candidate for a reversible SystemUI installation experiment, without changing device state.

**Architecture:** Discover tools and targets, branch cleanly when none are connected, and collect only read-only build/package/framework/signing evidence for connected targets. Produce a compatibility matrix and, only when justified, an unexecuted replacement/rollback packet for a later approval.

**Tech Stack:** Official `android` CLI, Android SDK `adb`, `apksigner`, `sha256sum`, read-only shell/property/package commands.

**Spec:** `docs/issues/2026-08-21-device-systemui-runtime-preflight.md`

## Global Constraints

- This task is read-only. Do not install, replace, stop, start, kill, reboot, root, remount, create/start/remove an AVD, or write to a device.
- `adb pull` into `/tmp/task048-*` is allowed; `adb push` is forbidden.
- Do not run Gradle. Use the existing Release APK if present; otherwise report it absent.
- Do not infer signature, framework-resource, root/remount, or runtime compatibility without direct evidence.
- A candidate result authorizes only a later proposal, never installation or SystemUI restart.
- No source/resource/build configuration changes. Worker commits in English and never pushes.

---

## File map

- Create: `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md` — tool/target matrix, evidence, classification, unexecuted rollback packet if applicable.
- Modify: `docs/issues/2026-08-21-device-systemui-runtime-preflight.md` — command log and actual result.
- Modify: this plan and `docs/orchestration/tasks/048-device-systemui-runtime-preflight.md` — checkbox/evidence state.
- Temporary only: `/tmp/task048-*`.

## Task 1: Discover tools and targets

- [ ] **Step 1: Record tool versions and environment**

```bash
command -v android
android --version
android info
/home/conv/Android/Sdk/platform-tools/adb version
android emulator list
/home/conv/Android/Sdk/platform-tools/adb devices -l
```

Record every exit code and output. Do not install/update a CLI or SDK component in this
task.

- [ ] **Step 2: Branch on connected target count**

If no `device`-state serial exists, write `CONNECTED_TARGETS=0`, inventory existing AVD
names without starting them, classify runtime validation as deferred, and skip Tasks 2
and 3. Offline/unauthorized targets are reported separately and are not queried.

## Task 2: Collect read-only target evidence when connected

- [ ] **Step 1: Query immutable/runtime properties**

For each `device` serial, run only read-only commands equivalent to:

```bash
adb -s SERIAL shell getprop ro.build.fingerprint
adb -s SERIAL shell getprop ro.build.type
adb -s SERIAL shell getprop ro.build.version.sdk
adb -s SERIAL shell getprop ro.debuggable
adb -s SERIAL shell getprop ro.boot.verifiedbootstate
adb -s SERIAL shell getenforce
adb -s SERIAL shell id
adb -s SERIAL shell pm path com.android.systemui
adb -s SERIAL shell dumpsys package com.android.systemui
```

Do not run `adb root` to test a hypothesis.

- [ ] **Step 2: Pull evidence without modifying the target**

When readable, pull installed SystemUI APK path(s) and
`/system/framework/framework-res.apk` to `/tmp/task048-SERIAL/`. Record pull exit codes,
source paths, sizes, and SHA-256. Failure is evidence; do not change permissions.

- [ ] **Step 3: Compare certificates and framework resources**

Use `/home/conv/Android/Sdk/build-tools/37.0.0/apksigner verify --print-certs` for the
existing project Release APK and pulled installed APK. Compare full signer certificate
SHA-256 values. Compare the pulled framework-res SHA-256 byte-for-byte with the frozen
AOSP input used by the SysUISdk generator. Never label a mismatch compatible.

## Task 3: Classify targets and prepare—but do not execute—a proposal

- [ ] **Step 1: Assign one result per target**

Use exactly:

```text
INCOMPATIBLE
INSUFFICIENT_EVIDENCE
READY_FOR_REPLACEMENT_REVIEW
```

`READY_FOR_REPLACEMENT_REVIEW` requires direct signature equality, framework-res byte
equality, suitable API/build evidence, readable current APK, and a plausible reversible
system-partition path. `ro.debuggable=1` alone does not prove root/remount.

- [ ] **Step 2: Draft a gated execution packet only for a ready candidate**

The report may list unexecuted commands for original-APK backup, snapshot/rollback,
replacement, process restart, logcat/dumpsys capture, and restoration. Prefix the packet
with `NOT EXECUTED — REQUIRES USER APPROVAL`. If no target qualifies, do not invent a
command sequence for a hypothetical device.

## Task 4: Scope and report verification

- [ ] **Step 1: Scan for forbidden state-changing commands in executed-command log**

The issue must separate commands actually executed from proposed commands. Verify the
executed list contains none of:

```text
adb root
adb remount
adb install
adb push
pm install
pm uninstall
stop
start
kill
reboot
emulator start
emulator create
emulator remove
```

- [ ] **Step 2: Repository checks**

```bash
git diff --check
git status --short
```

Expected: only the File map documentation paths changed; no Gradle output or project
implementation change.

- [ ] **Step 3: Commit and hand off**

Update actual evidence, commit in English without pushing, and finish with a `HANDOFF:`
that states connected-target count, classification, and whether a second approval
packet exists.
