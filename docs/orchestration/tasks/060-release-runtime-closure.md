# Task 060 — Release runtime closure on emulator-5554

## Goal

Prove the optimized Release APK (R8 full mode) runs on the same-tree x86_64 emulator
with the same health bar as Debug. Debug runtime is closed (DEBUG_RUNTIME_PASS,
task 058); **Release runtime is an independent risk surface** — R8 shrinking, resource
optimization and minification can break things Debug cannot reveal. Do NOT infer
Release health from Debug results.

## Context

- Debug gate passed 2026-08-25 on emulator-5554: APK sha256
  `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427` deployed via
  atomic same-dir replace, PID stable, zero FATAL/NoClassDefFoundError.
- Release static side is green (task 045): `:app:assembleRelease` exit 0, R8 missing
  refs 0, V2 signature, 0/39 bridge classes in dex. Expected APK size ≈ 28.6 MB.
- Release is signed with the SAME platform keystore as Debug
  (`keystore/platform.keystore`, alias `androiddebugkey`) — no signature change vs the
  currently deployed Debug APK.
- Device state: verity DISABLED (must stay disabled — `enable-verity` tears down the
  overlay and silently reverts the deployed APK to stock, PITFALLS §14.1).
- Rollback artifacts (verify presence BEFORE deploying):
  - Debug APK: `app/build/outputs/apk/debug/app-debug.apk` (sha256 e8aad131…)
  - Stock backup: `/home/conv/myspace/task053-same-tree-x86_64-runtime/deploy/stock-backup/SystemUI.apk`
    (35 MB, sha256 `dd1ff45acdf82700897a4adc587f67ff3f4f626d6ef240c6d75f1544f194b837`)

## Authority

- Working tree: **no source/resource edits**. You may write build outputs, the report
  file, and one orchestration log line. Everything else is read-only.
- Device emulator-5554: mutation allowed ONLY via the established deployment
  procedure (below). Reboot allowed. No factory reset, no wipe, no enable-verity.
- Git: report commit allowed locally; **do not push**.
- You must be the ONLY Gradle activity on this tree (single-Gradle rule, kernel OOM
  hazard). If you see another Gradle daemon building this tree, stop and report.

## Steps

1. **Preflight**: `adb devices` shows only emulator-5554; `ro.kernel.qemu=1`;
   verity disabled; rollback artifacts present (hashes above); record current device
   APK sha256 (expect e8aad131).
2. **Build**: `./gradlew :app:assembleRelease --console=plain` (expect ≈ 3–5 min;
   R8 daemon memory spike is normal; on daemon disappearance retry once with
   `--max-workers=4`). Record APK size + sha256.
3. **Static sanity**: `unzip -t` clean; apksigner V2 verify; confirm package name and
   `android:sharedUserId`/`appComponentFactory` match the Debug APK manifest
   (aapt2 dump badging / AndroidManifest diff at the attribute level).
4. **Deploy** (proven procedure from tasks 054/058):
   `adb push` to `/data/local/tmp` staging → `su 0 cp` to same-dir temp name on
   `/system_ext/priv-app/SystemUI/` → `sync` → atomic `mv` onto `SystemUI.apk` →
   `chown root:root`, `chmod 0644`, `chcon u:object_r:system_file:s0` → clear `oat/`
   dir and dalvik-cache → **on-device `su 0 sha256sum` MUST equal the build hash
   BEFORE any restart** (toybox cp silently truncates on ENOSPC, PITFALLS §14.2;
   if truncated: `am force-stop` + `kill -9` SystemUI, rm the candidate, retry) →
   reboot.
5. **Runtime health gate** (same bar as Debug):
   - `sys.boot_completed=1`
   - SystemUI PID stable across **10 samples × 30 s**
   - `logcat -b crash -d` = 0 FATAL lines; full logcat grep
     `FATAL EXCEPTION|NoClassDefFoundError` = 0
   - `dumpsys window windows` shows StatusBar (+ NotificationShade/Taskbar)
   - bonus: open QS panel via `cmd statusbar expand-settings` + screenshot, collapse,
     confirm no crash.
6. **Failure protocol** (expected novel class — R8 closure):
   - Capture the FULL fatal stack + 200 lines of context to the report.
   - Do NOT attempt speculative proguard/source fixes; do NOT add broad
     `-dontwarn`/keep rules. Classify the root cause (missing keep? aconfig
     assumption? reflection entry? resource shrink?) and report.
   - Restore the Debug APK (step 4 procedure with
     `app/build/outputs/apk/debug/app-debug.apk`) so the device returns to the known
     good state; verify on-device sha256 = e8aad131.
7. **Report**: `docs/issues/2026-08-26-release-runtime-closure.md` — every command +
   output, hashes, timeline, verdict (`RELEASE_RUNTIME_PASS` / `RELEASE_RUNTIME_FAIL
   + root-cause classification` + next-action recommendation). One line in
   `docs/orchestration/log.md`. Commit locally (English message, do not push).
8. Final message: four-part completion report per worker-contract.

## Acceptance

- PASS: Release APK on device, sha256 verified, PID stable 10×30 s, zero FATAL/NCDFE,
  StatusBar visible — verdict `RELEASE_RUNTIME_PASS`.
- FAIL is an acceptable outcome IF the root cause is captured with evidence and the
  device is restored to Debug e8aad131.

## Model constraint

Run on joycode **GLM-5.3** or **GLM-5.2** only (chief directive 2026-08-25).
