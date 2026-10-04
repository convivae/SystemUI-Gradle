# Task 058 — Full DEBUG_RUNTIME_PASS test & gate suite run

## Objective

Run the complete gate and test suite for the current debug runtime state (post task
057 single-jar merge, PID 835 verified alive on emulator-5554):

1. `uv run pytest tools/tests/ -q` (all 243+ unit tests).
2. Root `:app:checkDebugDuplicateClasses`.
3. Alignment check: `python3 tools/check_source_alignment.py --strict` (assert 0 MISSING,
   0 MISPLACED, 0 EXTRA).
4. Manifest closure check: `python3 tools/check_manifest_dex_closure.py` (all manifest
   entry classes resolved in APK dex).
5. Clean build: `./gradlew clean :app:assembleDebug` (verify debug APK rebuilds cleanly
   from scratch; compare new APK sha256 to known `b827df78...` baseline).
6. Live emulator-5554 health snapshot: confirm `sys.boot_completed=1`, SystemUI process
   still alive, record PID and uptime, sample logcat for any new FATAL or NCDFE.

## Deliverable

Report `docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md` with output from every
command, summary table, and verdict on whether current debug runtime is ready to be
declared `DEBUG_RUNTIME_PASS`.

Commit (English, local only): `test: run full DEBUG_RUNTIME_PASS gate suite (task 058)`.
Do NOT push.

## Authority

Read-only tests + gradle assembleDebug + clean + adb shell read commands against
emulator-5554 ONLY. No modifications to build.gradle.kts or source files. Write ONLY
the one issue report + orchestration logs if needed.

---

## Update 2026-08-25 (post task 059, chief)

- Task 059 has landed (commits `dea5fe37` + `0f683bdc`): 4 single-consumer AAR
  families now consumed directly from `libs/aars/`. Expected APK sha256 is now
  **`e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427`**
  (157 MB, clean-build form), NOT the old b827df78 baseline. The 204 MB → 157 MB
  difference is a known clean-build dex-packing artifact; task 059 verified class
  sets equal to the deployed baseline — see `docs/issues/2026-08-25-aar-direct-consumption-migration.md`.
- An earlier contaminated run of this suite (concurrent with task 059's tree
  mutations) was halted and discarded. This run must be the ONLY Gradle
  activity on the tree — verify no other Gradle builds are running first.
- Reference APK for diffing: `/tmp/task059-apk-reference/app-debug-b827df78.apk`
  (the proven deployed baseline; on-device sha256 b827df78…).
- **New step 7 (deploy + runtime verify)**: deploy the freshly built APK
  (e8aad131) to emulator-5554 using the task 054 staging procedure
  (root → remount rw /system_ext → atomic same-dir replace → root:root 0644
  u:object_r:system_file:s0 → clear oat/dalvik-cache → verify target sha256),
  reboot is NOT required if only this app changes — use `adb shell am force-stop` +
  wait for system restart of SystemUI; verify PID stable ≥5 min,
  `logcat -b crash` zero FATAL/NCDFE, `dumpsys StatusBar` window visible.
  Restore SELinux/perms state per procedure.
- **Model constraint (user rule 2026-08-25)**: workers must run joycode
  GLM-5.3 or GLM-5.2 only. This run was dispatched on joycode/GLM-5.3.
