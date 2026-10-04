# Task 060b — Release round-3 crash forensics (lightweight, no build)

## Goal

The `-dontobfuscate` Release build (`app/build/outputs/apk/release/app-release.apk`,
sha256 `90c412d8c86fafc42ea1233474d2da9f2e3823ca0806b1ead822bb4e1c0f64fa`) STILL
crash-looped on device (new PID every 30 s, samples 3799→5413→7237→9420→11753→13638→
15746→18936→21978, 00:42–00:46). The previous worker pane died of host OOM before
capturing the round-3 crash stack. Your job: deploy that exact APK again, capture the
full fatal stack, restore the Debug baseline, and report. **NO Gradle, NO builds, NO
source edits.** Device operations + reading logs only.

## Context

- Device: emulator-5554, currently running healthy Debug baseline (on-device sha
  `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427`, PID ~833).
- Round-2 crash (before -dontobfuscate) was `IllegalArgumentException: 'a' already
  registered` in DumpManager — obfuscation collision, fixed in theory by -dontobfuscate.
  Round 3 still loops, so there is a SECOND, distinct crash. The stack is unknown —
  that's what you must capture.
- Mapping file (should be unnecessary now, names preserved): 
  `app/build/outputs/mapping/release/mapping.txt` if deobfuscation is ever needed.
- Report file: `docs/issues/2026-08-26-release-runtime-closure.md` — APPEND a
  "Round 3" section; do not rewrite earlier content.

## Authority

- Read-only on the working tree EXCEPT appending to the report file, one log.md line,
  and one local commit of the report. **No push, no Gradle, no edits to any other file.**
- Device mutation allowed only via the procedure below. Reboot allowed.

## Steps

1. **Preflight**: `adb devices` (only emulator-5554); record current on-device sha
   (expect e8aad131); verify release APK sha is 90c412d8; `free -h` snapshot for the
   report.
2. **Deploy round-3 APK** (proven procedure; note /system_ext is read-only after a
   reboot — remount first):
   ```
   adb -s emulator-5554 push app/build/outputs/apk/release/app-release.apk /data/local/tmp/r3.apk
   adb -s emulator-5554 shell 'su 0 mount -o remount,rw /system_ext && su 0 cp /data/local/tmp/r3.apk /system_ext/priv-app/SystemUI/SystemUI.apk.tmp && sync && su 0 sha256sum /system_ext/priv-app/SystemUI/SystemUI.apk.tmp'
   # sha MUST equal 90c412d8... before proceeding (toybox cp truncation guard)
   adb -s emulator-5554 shell 'su 0 mv /system_ext/priv-app/SystemUI/SystemUI.apk.tmp /system_ext/priv-app/SystemUI/SystemUI.apk && su 0 chown root:root /system_ext/priv-app/SystemUI/SystemUI.apk && su 0 chmod 0644 /system_ext/priv-app/SystemUI/SystemUI.apk && su 0 chcon u:object_r:system_file:s0 /system_ext/priv-app/SystemUI/SystemUI.apk; rm -rf /system_ext/priv-app/SystemUI/oat; su 0 rm -rf /data/dalvik-cache/*/system_ext*; sync'
   adb -s emulator-5554 reboot
   ```
3. **Capture the crash** (the money step — do it BEFORE any restore):
   - After boot, wait ~60–90 s for the loop to register.
   - `adb -s emulator-5554 logcat -b crash -d` → save FULL output.
   - Also: `adb -s emulator-5554 logcat -d -t 3000 | grep -B5 -A40 "FATAL EXCEPTION"` 
   - Capture 2–3 DIFFERENT crash instances if they alternate (loop may cycle multiple
     distinct crashes).
   - Note whether class names in the stack are REAL names (proves -dontobfuscate took
     effect) vs single letters (means it didn't).
   - Record `adb -s emulator-5554 shell pidof com.android.systemui` 3× at 30 s
     intervals to re-confirm the loop.
4. **Restore Debug baseline** (same procedure as step 2 with
   `app/build/outputs/apk/debug/app-debug.apk`, expect sha e8aad131):
   push → remount rw → staged cp → sha gate → atomic mv → perms → clear caches →
   reboot → verify boot_completed=1, on-device sha e8aad131, PID stable 2×30 s,
   crash buffer 0 FATAL after boot.
5. **Report**: append Round-3 section to
   `docs/issues/2026-08-26-release-runtime-closure.md`: full crash stacks (verbatim),
   loop evidence, name-reality check, restore verification, root-cause hypothesis
   classified (shrink missing keep? optimization bug? init-order?), recommended next
   diagnostic. One line in `docs/orchestration/log.md`. Single local commit
   (English message). Do NOT push.
6. Final message: four-part completion report per worker-contract.

## Acceptance

- Full round-3 crash stack captured verbatim (at least one complete FATAL instance
  with cause chain) + device restored to e8aad131 verified. Root-cause classification
  with evidence. That's a PASS for this task even though the Release verdict remains
  RELEASE_RUNTIME_FAIL.

## Model constraint

joycode GLM-5.3 or GLM-5.2 only.
