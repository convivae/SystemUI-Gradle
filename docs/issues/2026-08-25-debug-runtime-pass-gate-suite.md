# 2026-08-25 — Task 058: Full DEBUG_RUNTIME_PASS gate & test suite run (post task 059)

## 背景 (Background)

Task 059 landed (commits `dea5fe37` + `0f683bdc`): 4 single-consumer AAR families
(WifiTrackerLib, iconloader, setupcompat, LowLightDreamLib) now consumed directly from
`libs/aars/`. Expected clean-build APK sha256 is now
`e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427` (157 MB clean-build
form). This run executes the full gate suite on the post-migration tree to decide whether
debug runtime can be declared `DEBUG_RUNTIME_PASS`.

Pre-flight:
- No other Gradle build active: `ps` showed only an idle Gradle daemon (no launcher/client);
  this run was the only Gradle activity on the tree.
- `adb devices`: emulator-5554 only (device rule satisfied).
- Pre-deploy health: `sys.boot_completed=1`, SystemUI PID 3021 (47:44 elapsed), crash
  buffer zero FATAL/NCDFE.

## Gate results

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | Unit tests | `uv run pytest tools/tests/ -q` | **PASS** — 243 passed, 4 warnings, 52 subtests passed in 70.54s |
| 2 | Duplicate classes | `./gradlew :app:checkDebugDuplicateClasses` | **PASS** — BUILD SUCCESSFUL (UP-TO-DATE; task previously executed green) |
| 3 | Source alignment | `python3 tools/check_source_alignment.py --strict` | **PASS** — MISSING=0, MISPLACED=0, EXTRA=0; MODIFIED=1 (`UncaughtExceptionPreHandlerManager.kt`, carries 4 CONV markers — tracked per ADR 0004); RES-MODIFIED=86 (known, strict does not gate MODIFIED) |
| 4 | Manifest dex closure | `python3 tools/check_manifest_dex_closure.py --apk app/build/outputs/apk/debug/app-debug.apk` | **PASS** — RESULT=PASS: 24 dex files, 77,832 defined classes, 95 manifest entry classes (93 present + 2 alias, missing=0) |
| 5 | Clean build | `./gradlew clean :app:assembleDebug` | **PASS** — BUILD SUCCESSFUL in 3m 33s (229/229 tasks executed); APK sha256 `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427` == expected (163,896,493 bytes) |
| 6 | Emulator health snapshot (pre-deploy) | adb getprop/pidof/ps/logcat | **PASS** — `sys.boot_completed=1`, PID 3021 uptime 47:44, crash buffer zero FATAL/NCDFE (only an unrelated pre-session 21:48 crash_dump helper line) |
| 7 | Deploy + runtime verify | task 054/055 staging procedure | **PASS** — see below |

## Step 7 detail — deploy & runtime verify (emulator-5554)

Procedure (per task 054/055 docs + chief guidance): root → disable-verity → reboot →
wait-for-device → root → `su 0 mount -o remount,rw /system_ext` → push APK to
`/data/local/tmp` staging (sha256 MATCH e8aad131) → cp to same-dir `.tmp-SystemUI.apk` →
sync → atomic same-fs `mv` over `SystemUI.apk` → `chown root:root`, `chmod 0644`,
`chcon u:object_r:system_file:s0` → rm `oat/` + dalvik-cache → **verify on-device
sha256 == e8aad131 before restart** → reboot → verify.

### Incident 1 — overlay ENOSPC (known pitfall, task 055 déjà vu)

First replace attempt truncated to 6,561,792 bytes (sha `67ba07cf…` ≠ e8aad131): the
261 MB f2fs scratch overlay was 100% full because the running SystemUI process still held
the unlinked 204 MB b827df78 inode. Exactly the failure mode documented in
`docs/issues/2026-08-25-aconfig-flags-batch-closure.md` (toybox cp silently truncates on
ENOSPC). Recovery: `am force-stop` + `kill -9` SystemUI to release the handle → rm the
truncated candidate → df recovered to 202M avail → re-ran staged cp → sync → atomic mv →
perms → **on-device sha256 verified e8aad131** → caches cleared → reboot. The sha256
verification gate caught the truncation, as designed.

### Incident 2 — `enable-verity` tears down the overlay

After the first successful deploy, I attempted to restore pre-run verity state with
`adb enable-verity` + reboot. This **tore down the adb-remount overlay**: on next boot
`/system_ext/priv-app/SystemUI/SystemUI.apk` had reverted to the stock 36,378,017-byte
image (sha `dd1ff45a…` = stock backup hash from task 054). Conclusion: the persistent
deployed-APK end-state (as left by tasks 054/055) requires verity to stay **disabled**
with the overlay in place. Re-deployed e8aad131 from scratch (scratch now clean, 202M
free, direct staged procedure, no truncation), verified on-device sha256 again
e8aad131, rebooted.

### Final runtime verification (post second deploy)

- On-device target after reboot: sha256 `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427`
  (deployment survives reboot), `root:root 0644 u:object_r:system_file:s0`.
- `sys.boot_completed=1` (~15 s after wait-for-device).
- SystemUI PID **837 stable across 10 samples × 30 s (22:50:39–22:55:09, >5 min)**,
  `ps` elapsed 05:23 at final sample.
- `logcat -b crash -d`: **0 lines**; full `logcat -d` grep `FATAL EXCEPTION|NoClassDefFoundError`: **0**.
- `dumpsys window windows`: StatusBar window present (`Window #4 StatusBar`), plus
  NotificationShade, Taskbar, ShellDropTarget, ImageWallpaper (SystemUI-owned) all present.
- `dumpsys statusbar` responds (note: lowercase service name; `dumpsys StatusBar` is not
  a registered name on this build).
- Staging copy removed; oat/ + dalvik-cache cleared before boot; SELinux enforcing
  throughout (never disabled); verity left disabled per task 055 end-state precedent.

## Verdict

**DEBUG_RUNTIME_PASS: ACHIEVED.** All 7 gates green on the post-task-059 tree:

- clean-build APK is bit-for-bit reproducible (e8aad131, matches expected baseline);
- class set 77,832, zero duplicate classes, zero manifest-closure gaps;
- source tree aligned (0 MISSING / 0 MISPLACED / 0 EXTRA);
- runtime stable ≥5 min with zero FATAL/NCDFE and StatusBar window visible on the
  freshly built + freshly deployed APK.

## Build record (rule D truthfulness)

- `uv run pytest tools/tests/ -q`: 243 passed / 52 subtests (run once).
- `./gradlew :app:checkDebugDuplicateClasses`: BUILD SUCCESSFUL (UP-TO-DATE from task 059
  serial clean run; not re-executed as part of this suite's clean build — the clean build
  below re-ran it from scratch).
- `./gradlew clean :app:assembleDebug`: BUILD SUCCESSFUL in 3m 33s, 229/229 executed,
  sha256 e8aad131 == expected.
- No other Gradle invocation; single serialized build per CHARTER Part 4.

## 待解决 (Open issues)

- The 1 MODIFIED source file (`UncaughtExceptionPreHandlerManager.kt`) is CONV-marked and
  accounted for; RES-MODIFIED=86 is the long-standing known set (strict does not gate it).
- Verity on emulator-5554 must remain disabled while a custom APK is deployed via the
  adb-remount overlay; re-enabling verity reverts `/system_ext` to the stock image
  (Incident 2). Worth a PITFALLS entry — flagging to chief rather than editing
  `docs/PITFALLS.md` (not in this brief's allowed paths).
