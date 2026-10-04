# Task 098 — C5 fresh Debug APK runtime reboot gate

## Status

PLANNED — no emulator launch or deployment has occurred.

## Objective

Deploy the exact Task 096 Debug APK to the Task 077 AOSP-17 emu64x durable overlay environment, then prove SystemUI cold-start/runtime health before and after a second whole-device reboot. This is a no-fix runtime-only gate.

## Frozen startup order

Before any preflight, scratch creation, Herdr mutation, emulator/ADB command, generated-qcow deletion, or repository write, read these files **completely, serially, and in this exact order**:

1. `AGENTS.md`
2. `docs/HANDOFF.md`
3. `docs/orchestration/CHARTER.md`
4. `docs/orchestration/STATE.md`
5. the final 180 lines of `docs/orchestration/log.md`
6. this task brief
7. `docs/issues/2026-09-02-c5-debug-runtime-reboot-gate.md`
8. all mandatory sources below, one file at a time

Then emit exactly one `CONTRACT:` block and wait for explicit Chief acceptance. Parallel or out-of-order startup reads retire the worker. No `git fetch`, `git pull`, network/ref mutation, or speculative command is permitted.

## Mandatory sources

Read completely before CONTRACT:

1. `docs/issues/2026-08-26-emulator-relaunch-runbook.md`
2. `docs/orchestration/tasks/077-b3-emulator-super-slack.md`
3. `docs/issues/2026-09-01-c5-emulator-super-slack.md`
4. `docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md`
5. `docs/issues/2026-09-02-c5-debug-build-static-gate.md`
6. `/home/conv/.pi/agent/skills/android-cli/SKILL.md`
7. `/home/conv/.pi/agent/skills/android-cli/references/interact.md`
8. `/home/conv/.pi/agent/skills/worker-contract/SKILL.md`

## Required CONTRACT

The single block must state:

- Task `098`, shared checkout, Reports To Chief, expected `HEAD == origin/main`, and Task 096 closure `7c0f4f0c` plus Task 097 closure `a47ed877` as ancestors.
- `joycode/GLM-5.3`, `thinking=high`, and `HERDR_ENV=1` must be independently verified before execution.
- Existing Debug APK is an immutable input: exact path, size and SHA; no Gradle/Soong/build/replacement artifact is allowed.
- Exact scratch root, dedicated emulator service tab, `emulator-5554`, generated-qcow reset boundary, stock baseline, deployment target, two runtime checkpoints and four planned device reboots.
- Allowed and forbidden writes/actions, fail-closed rule, no tracked edit/commit/push, no Release/Task 079 claim.
- PASS means only `DEBUG_RUNTIME_REBOOT_PASS`; any input/deploy/runtime mismatch stops without repair.

## Frozen identity

- Required ancestors: `7c0f4f0c7230f2925971e52dc562f204147c5966` and `a47ed877d28f9e7a04817d4b0ede7203a2542fe0`.
- Candidate: `app/build/outputs/apk/debug/app-debug.apk`.
- Candidate size: `190547804` bytes.
- Candidate SHA-256: `f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`.
- Product out: `/home/conv/myspace/aosp/out/target/product/emu64x`.
- `super.img`: `3028287488` bytes; SHA-256 `50496c9b542aa49939840b4f1befb4ca11767b707148a7b77b395844740d040e`.
- Expected base stock SystemUI APK SHA-256: `d0e36b33a5170c44b092da00efbf3e0aced2b8dbc5862b2fc3d088d3b77a5e25`.
- Device: `emulator-5554` only.
- Device target: `/system_ext/priv-app/SystemUI/SystemUI.apk`.
- Host evidence root only: `/tmp/task098-c5-debug-runtime-reboot/**` plus the owned emulator runtime directory `/tmp/acloud_gf_temp/local-goldfish-instance-1/**`.

## Scope

### May

- Read repository, AOSP outputs, process/device state and generated evidence.
- Create only the frozen scratch root and exact emulator runtime directory.
- After proving no emulator/QEMU owns them, inventory then delete only generated top-level `PRODUCT_OUT/*.qcow2` files and the exact task-owned emulator runtime directory, so the launch starts from base images. Do not delete any `.img`, textproto or other AOSP output.
- Create one dedicated Herdr emulator service tab and launch exactly the runbook prebuilt emulator command with `-ports 5554,5555`, `-read-only`, `-writable-system`, three required environment variables and pre-touched log files.
- Operate only `emulator-5554` with `adb`; apply the two known pristine-data permission grants; run root/disable-verity/remount, staged APK replacement, cache cleanup, four frozen device reboots, runtime inspection, `android layout`, screenshot capture, and visual image reads.
- Write all command outputs, exits, identities, PID samples, layouts and screenshots under scratch.
- Remove only the owned staging/candidate files after successful replacement.

### May not

- Modify any tracked repository file, source/resource/build logic/tool/checker/rule, SDK, AOSP source, base `.img`, `VerifiedBootParams.textproto`, or `super.img`.
- Run Gradle, Soong, Ninja, tests, APK rebuild, `adb install`, Release APK work, Task 079, or another emulator/device.
- Enable verity, wipe data with emulator flags, resize partitions, alter super metadata manually, use `/data` scratch workarounds, change the APK, bypass SHA gates, suppress a crash, or repair a failure.
- Run direct `python`/`python3`; no Python is expected. Do not create scripts.
- Commit, push, fetch, pull, rebase, merge, checkout another ref, or write durable docs.
- Stop/restart an unrelated process or rerun a one-shot destructive/reboot command because output was lost.

## Procedure

### 1. Read-only preflight

After Chief accepts CONTRACT:

1. Verify `HERDR_ENV=1`, `HEAD == origin/main`, both frozen ancestors, and empty `git status --short --untracked-files=all`.
2. Independently record worker model/session identity. Do not use network/ref mutation.
3. Record candidate `stat`, size and SHA; require exact frozen identity. Record `super.img` identity; require exact frozen identity. Require emulator binary, `system-qemu.img`, `userdata-qemu.img`, `vendor-qemu.img`, `VerifiedBootParams.textproto` and launch paths to exist.
4. Use non-self-matching process census. Require no emulator/QEMU, Gradle/Kotlin/Soong/Ninja process and no attached ADB device. If anything conflicts, stop; do not kill it.
5. Record free disk, memory, current generated-qcow inventory, and instance-directory inventory. Run and save `android layout --help` and `android screen --help` as required by the Android interaction skill. Create scratch only after all preceding checks pass; help output may be captured immediately after scratch creation.

### 2. Fresh dedicated emulator launch

1. After saving inventories, remove only the exact generated top-level `PRODUCT_OUT/*.qcow2` files and exact instance directory. Recreate the instance directory and pre-touch `kernel.log` and `logcat.txt`.
2. Create a separate Herdr tab labelled `task098-emulator`, record its tab/pane IDs, and run the exact launch shape from the runbook in that pane. Keep the worker itself in its own independent tab.
3. Wait for `emulator-5554` with bounded polls (no single sleep over 90 seconds). Require `sys.boot_completed=1`, `ro.kernel.qemu=1`, emu64x fingerprint, `ro.boot.verifiedbootstate=orange`, one connected device, and live emulator process.
4. Apply only:
   - `pm grant com.android.systemui android.permission.BLUETOOTH_CONNECT`
   - `pm grant com.android.systemui android.permission.READ_CONTACTS`
   Then clear all logcat buffers once so pre-grant stock crashes cannot contaminate the baseline reboot window.
5. **Reboot 1/4 (permission-baseline reboot)**. Require boot completion, stock target SHA equals the frozen stock SHA, stock PID exists, crash buffer has no crash entry after a fresh log window, and no crash/ANR dialog is visible. Any mismatch stops.

### 3. Durable overlay setup

1. Run `adb root`, `adb disable-verity`, and preserve complete output.
2. **Reboot 2/4 (disable-verity reboot)**. Wait for boot, root again, and remount `/system_ext` read-write exactly as the runbook permits.
3. Require `/mnt/scratch` is f2fs/super-backed and total bytes are at least 512 MiB, all five expected overlay mounts exist, verified boot remains orange, SELinux is enforcing, stock target SHA still matches, and available scratch exceeds candidate size plus 64 MiB. Save `df`, mount and dm evidence.

### 4. SHA-gated atomic deployment

1. Push the candidate to `/data/local/tmp/task098-app-debug.apk`; require staged size/SHA exactly match host.
2. Force-stop SystemUI and terminate any remaining old SystemUI PID before copying. Remove only a stale task-owned target temp if present.
3. Copy staged APK to `/system_ext/priv-app/SystemUI/.tmp-task098-SystemUI.apk`, `sync`, and require temp size/SHA exact. ENOSPC, short write or SHA mismatch is immediate FAIL; remove only the incomplete temp and stop without retry.
4. Atomic same-filesystem `mv` temp over target; set `root:root`, mode `0644`, label `u:object_r:system_file:s0`; delete target `oat/` and only SystemUI-related dalvik-cache entries; `sync`.
5. Require target size/SHA, owner/mode/label all exact before reboot. Remove the `/data/local/tmp` staging copy, verify host SHA again, record package baseline, then clear all logcat buffers once.

### 5. Checkpoint A — deployed cold boot

1. **Reboot 3/4 (deployment cold boot)**. Record pre-reboot boot ID/uptime, issue reboot once, wait for boot, and record new boot ID/uptime.
2. Require device target size/SHA exact, `pm path com.android.systemui` points to the system_ext target, package dump responds, scratch/overlays persist, boot complete, orange state and SELinux enforcing.
3. Save 11 PID samples at 30-second intervals. Every sample must contain exactly one identical PID; final process elapsed must be at least 300 seconds.
4. Save complete crash buffer and full logcat. Require zero crash entries and zero `FATAL EXCEPTION`, `NoClassDefFoundError`, SystemUI crash-loop or ANR evidence in this fresh boot window.
5. Save full `dumpsys window windows`; require StatusBar, NotificationShade, Taskbar and ImageWallpaper. Save lowercase `dumpsys statusbar`; require exit 0, nonempty response and no missing-service error.
6. Wake/dismiss keyguard and return HOME only if needed. Run `android layout --device=emulator-5554`, capture a PNG with `android screen capture --device=emulator-5554`, then use the image-reading tool to visually inspect it. Require usable system UI and no black screen, crash or ANR dialog. Preserve layout, PNG and written visual finding.

### 6. Checkpoint B — whole-device reboot persistence

1. After Checkpoint A fully passes, clear all logcat buffers once and record boot ID/uptime/target SHA.
2. **Reboot 4/4 (explicit whole-device reboot)**. Issue once, wait for boot, and require a different boot ID.
3. Repeat every Checkpoint A identity/package/mount/PID 11×30s/crash/full-log/window/statusbar/layout/screenshot/visual gate. Device target SHA must still equal the frozen host SHA.
4. Record final host SHA and empty repository status. Remove only task-owned staging/temp files if any. Do not enable verity, restore stock, stop the emulator, or close its service tab on PASS.

## Fail-closed rules

- Any frozen identity, stock baseline, launch, grant, scratch, overlay, staged/temp/target SHA, permission/label, boot-ID, PID, crash, window, statusbar, layout or visual mismatch is `FAIL` or `BLOCKED` as appropriate.
- Save the first actionable evidence and stop. Do not retry deployment, substitute an APK, add grants/fixes beyond the two frozen grants, alter the device gate, or proceed from Checkpoint A failure to Checkpoint B.
- If an authorized reboot or destructive command's result/exit is lost, do not rerun it; disclose and stop for Chief adjudication.
- Herdr state is not acceptance evidence; command outputs, device state and scratch artifacts are.

## Acceptance

`DEBUG_RUNTIME_REBOOT_PASS` requires all of:

- Exact host/device APK identity before and after both runtime reboots.
- Reboots 3 and 4 proven by changed boot IDs; `sys.boot_completed=1` after each.
- Two independent 11×30s stable single-PID windows with final elapsed ≥300s.
- Two fresh runtime log windows with no crash/FATAL/NCDFE/SystemUI ANR.
- StatusBar, NotificationShade, Taskbar and ImageWallpaper plus responsive `dumpsys statusbar` at both checkpoints.
- Two successful layouts and visually inspected screenshots with normal usable UI.
- Durable scratch/overlay, orange verified state, SELinux enforcing, clean repository, no forbidden action.

PASS claims only Debug runtime/reboot. It does not claim Release runtime, C6, or Task 079 completion.

## Required report

```text
STATUS=DEBUG_RUNTIME_REBOOT_PASS|FAIL|BLOCKED_PREFLIGHT
BASE_HEAD=
ORIGIN_MAIN=
MODEL=joycode/GLM-5.3
THINKING=high
HERDR_ENV=
APK_HOST_SIZE=
APK_HOST_SHA_INITIAL=
APK_HOST_SHA_FINAL=
SUPER_SIZE=
SUPER_SHA=
EMULATOR_TAB=
EMULATOR_PANE=
DEVICE_SERIAL=
STOCK_SHA=
SCRATCH_TOTAL=
OVERLAYS=
DEPLOY_STAGED_SHA=
DEPLOY_TEMP_SHA=
DEPLOY_TARGET_SHA=
REBOOT_COUNT=/4
CHECKPOINT_A_BOOT_ID=
CHECKPOINT_A_DEVICE_SHA=
CHECKPOINT_A_PID_SAMPLES=
CHECKPOINT_A_PID_ELAPSED=
CHECKPOINT_A_CRASH_ENTRIES=
CHECKPOINT_A_FATAL_NCDFE=
CHECKPOINT_A_WINDOWS=
CHECKPOINT_A_STATUSBAR=
CHECKPOINT_A_LAYOUT=
CHECKPOINT_A_VISUAL=
CHECKPOINT_B_BOOT_ID=
CHECKPOINT_B_DEVICE_SHA=
CHECKPOINT_B_PID_SAMPLES=
CHECKPOINT_B_PID_ELAPSED=
CHECKPOINT_B_CRASH_ENTRIES=
CHECKPOINT_B_FATAL_NCDFE=
CHECKPOINT_B_WINDOWS=
CHECKPOINT_B_STATUSBAR=
CHECKPOINT_B_LAYOUT=
CHECKPOINT_B_VISUAL=
SELINUX=
VERIFIED_BOOT_STATE=
FINAL_STATUS=
FORBIDDEN_ACTIONS=
DEVIATIONS=
EVIDENCE_ROOT=/tmp/task098-c5-debug-runtime-reboot
NEXT=Chief durable closure; then a separate Release runtime reboot gate
```

End with a concise `HANDOFF:` and wait. Do not edit tracked files, commit or push.
