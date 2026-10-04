# Task 050 — Direct Debug APK runtime closure

## Authority

`redline-gated`, with the following red lines already explicitly approved by the user for this task:

- modify `app/src/main/AndroidManifest.xml`;
- modify `app/build.gradle.kts`, including `namespace`;
- root/remount/push/reboot and destructive mutation, deletion, or recreation of the dedicated disposable emulator and its private/shared installed emulator image files.

Worker commits but never pushes.

## Goal

Build a Debug APK whose manifest entries resolve to real DEX classes, directly replace the dedicated emulator's SystemUI APK, reboot into it, and fix real crash evidence one cause at a time until SystemUI and required UI interactions are stable.

## Read first

1. `AGENTS.md`
2. `docs/orchestration/CHARTER.md`
3. this brief
4. `docs/issues/2026-08-22-direct-debug-apk-runtime-closure.md`
5. `docs/superpowers/plans/2026-08-22-direct-debug-apk-runtime-closure.md`
6. `docs/issues/2026-08-21-device-systemui-runtime-preflight.md` for historical runtime evidence only

## Allowed repository paths

- `app/build.gradle.kts`
- `app/src/main/AndroidManifest.xml`
- focused Python verification tooling/tests under `tools/**`
- `docs/issues/2026-08-22-direct-debug-apk-runtime-closure.md`
- `docs/superpowers/plans/2026-08-22-direct-debug-apk-runtime-closure.md`
- this brief
- `docs/CURRENT_STATE.md`, `docs/PLAN.md`, `docs/HANDOFF.md`, `docs/GRADLE_MIGRATION_LOG.md` for final factual synchronization
- generated Gradle outputs and `/tmp/task050-*` evidence

## Forbidden repository paths

- `SystemUI-*/src/**` and `SystemUI-*/res*/**` unless a real post-reboot crash specifically proves a product-source change is required; then print `REDLINE:` before editing
- dependency versions, module boundaries, SysUISdk, AAR/JAR artifacts
- stubs, source exclusions, disabled checks, broad suppression/keep rules
- Release configuration/tasks/artifacts

## Device authority

- Reuse the currently running dedicated `sysui-gradle-task049-debug-*` AVD or delete it and create one new disposable `sysui-gradle-task050-debug-*` AVD.
- Before the first mutation and after reconnect, prove `emulator-*`, `ro.kernel.qemu=1`, and one of those dedicated prefixes. Never touch a physical or unrelated device.
- The dedicated AVD may be rooted, disable-verity/remounted, repartitioned, have system images/APKs modified, become unbootable, and be deleted/recreated without another approval.
- Shared installed emulator image files may be modified if required; record exact paths changed. Reinstalling the SDK image is an acceptable recovery.
- First discover `pm path com.android.systemui`, then pull the original APK to `/tmp/task050-*`, recording size and SHA-256.
- Do not waste time preserving the AVD after a failed experiment. If it is damaged, recreate it.
- Every individual sleep/poll interval must be at most 30 seconds.

## Execution

### A. Confirm and fix manifest resolution

1. Use the existing packaged-manifest-to-DEX mismatch as the failing gate.
2. First hypothesis: changing only `:app` namespace to `com.android.systemui` lets AGP expand the AOSP relative component names correctly.
3. Run one fresh serialized `:app:assembleDebug` with `-Dorg.gradle.workers.max=4`, `set -o pipefail`, and `tee`.
4. If it builds, run the static closure gate. Do not add a manifest transform.
5. If the build itself proves duplicate-R or another namespace collision, revert only that change and directly rewrite the manifest's package-dependent entry attributes (`android:name`, `android:backupAgent`, `android:targetActivity`) to correct `com.android.systemui.*` FQCNs. Leave unrelated attributes unchanged. Rebuild and rerun closure.

### B. Direct deployment

1. Pull/hash the original emulator SystemUI APK locally.
2. Root/remount and push the complete Debug APK to the dynamic path.
3. If the remount overlay is too small, directly modify/expand the disposable AVD/system image so the full APK fits. Do not return to bind-mount or symlink workarounds.
4. Verify on-device size and SHA-256 exactly match the frozen host APK.
5. Full reboot; wait for boot completion with polls no longer than 30 seconds.

### C. Runtime debugging

1. Capture first fatal exception chain, SystemUI PID churn, and package/component metadata.
2. Write one hypothesis in the issue before editing.
3. Apply exactly one minimal fix, then fresh Debug build → hash → push → reboot.
4. Repeat from actual evidence. Three failed fixes to the same root-cause family require `REDLINE:` escalation; new crash roots continue normally.

## Acceptance

All must pass with retained evidence:

- fresh `:app:assembleDebug` exit 0;
- packaged manifest-to-DEX closure `PASS` for every runtime entry class;
- device APK SHA-256 equals the frozen Debug APK SHA-256;
- SystemUI PID stable for at least 60 seconds after full reboot;
- no new SystemUI fatal exception, ANR, watchdog, or crash loop;
- status bar, Quick Settings, and lock/wake/unlock interactions work;
- `git diff --check` passes;
- English focused commit(s), no push;
- terminal `HANDOFF:` includes exact commands, exit codes, APK hash, runtime result, and remaining issues.

## Reports to

Chief architect in the main SystemUI-Gradle workspace.
