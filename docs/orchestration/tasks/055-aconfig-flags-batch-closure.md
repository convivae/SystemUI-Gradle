# Task 055 — Batch-close the 11 remaining aconfig runtime-closure hazards

## Background (chief-approved direction)

Task 054 fixed `android/os/Flags` and prescanned the APK: **11 residual same-family
hazards** confirmed — each is a `Flags`-family class our APK references by public name,
the device defines only the `hidden_from_bootclasspath` twin, and our APK doesn't bundle.
(chief decision 2026-08-25: batch-fix the whole family in ONE task instead of one
crash loop per member.)

Current boot-critical one: `NoClassDefFoundError Landroid/service/notification/Flags;`
at `NotificationStackScrollLayout.<init>`. The other 10 are lazy-trigger landmines.

The 11 hazards (from task054 report §7):

| # | Public package | Owning Soong java_aconfig_library (expected) |
|---|---|---|
| 1 | android/app/smartspace/flags | android.app.smartspace.flags-aconfig-java |
| 2 | android/content/pm | android.content.pm.flags-aconfig-java |
| 3 | android/hardware/biometrics | android.hardware.biometrics.flags-aconfig-java |
| 4 | android/hardware/usb/flags | android.hardware.usb.flags-aconfig-java |
| 5 | android/net/platform/flags | android.net.platform.flags-aconfig-java |
| 6 | android/permission/flags | android.permission.flags-aconfig-java |
| 7 | android/provider | android.provider.flags-aconfig-java |
| 8 | android/security | android.security.flags-aconfig-java |
| 9 | android/service/controls/flags | android.service.controls.flags-aconfig-java |
| 10 | android/service/notification | android.service.notification.flags-aconfig-java |
| 11 | android/service/quickaccesswallet | android.service.quickaccesswallet.flags-aconfig-java |

The "expected" module names are hypothesis — you MUST verify each owning module by
searching AOSP `Android.bp`/`AconfigFlags.bp` (start: frameworks/base/AconfigFlags.bp).
The device hidden twin path tells you the true package; the Soong module name may
differ from my guess. Wrong module = wrong classes = validator rejects anyway.

## Objective

For all 11: package byte-identical owning-javac JARs into `libs/`, wire into
`:SystemUI-core`, redeploy, verify stable PID ≥ 5 min with zero NoClassDefFoundError.

## Steps

1. **Locate owning modules**: for each of the 11 packages, find the owning
   `java_aconfig_library` in AOSP bp. Record module name + intermediate javac path.
2. **Check which javac JARs already exist** under
   `$AOSP_ROOT/out/soong/.intermediates/...`. For missing ones (task054 report says
   android.service.notification flags javac is NOT built), build them:
   - `cd $AOSP_ROOT && bash -c 'export TOP=$(pwd); . build/envsetup.sh; lunch sdk_phone64_x86_64-trunk_staging-userdebug; m -j4 <module1> <module2> ...'`
   - Hard constraints: `m -j4` max; abort build if free disk < 10 GiB (check `df` first);
     only `out/` may be written; batch ALL missing modules into as FEW `m` invocations
     as practical (one invocation if possible).
3. **Extend `tools/package_aconfig_jars.py` CONFIGS** with all 11 entries
   (dst `libs/<short>-flags.jar`, short names consistent with existing style, e.g.
   `service-notification-flags`, `provider-flags`... AOSP root via the existing
   `tools/aosp_paths.py` single source). Keep the five-class validator.
   - NOTE android/content/pm and android/provider may have MULTIPLE flag classes or
     extra runtime classes — if the validator rejects, inspect the actual class set
     and adjust validation for those entries ONLY, documenting why.
4. **Package all 11** via `uv run python tools/package_aconfig_jars.py <name>`.
   Verify each: `sha256sum` byte-identical vs source. The packager currently takes a
   single artifact arg — you may add an `--all`-style batch flag if useful, keeping
   backward compatibility and updating tests accordingly.
5. **`uv run pytest tools/tests/ -q`** — extend tests for new configs; all pass.
6. **Wire all 11** in `SystemUI-core/build.gradle.kts` next to the existing flags
   block with the same comment style (one grouped comment + 11 lines, ordered).
7. Rebuild `./gradlew :app:assembleDebug`. Verify EACH of the 11 public `L.../Flags;`
   now has exactly one definition across all APK dexes (dexdump sweep, script it).
8. **Redeploy to emulator-5554 only** using the established procedure (root →
   disable-verity → reboot → wait-for-device → root → remount /system_ext → atomic
   replace with sha256 check (use the /data-local-tmp staging workaround from task054
   report §8 if overlay space is tight) → restore root:root 0644
   u:object_r:system_file:s0 → clear oat + dalvik-cache → reboot).
   Stock backup path unchanged.
9. **Verify**: `sys.boot_completed=1`; SystemUI PID stable ≥ 5 min (sample pidof
   every 30 s); logcat contains ZERO `NoClassDefFoundError` for ANY of the 11
   packages, zero DumpManager `alreadyRegistered` crash loops; SystemUI visibly
   renders (status bar present e.g. via `dumpsys window` or screenshot evidence).
10. **Docs + commit**: report `docs/issues/2026-08-25-aconfig-flags-batch-closure.md`
    (owning-module table, sha256s, build evidence, deployment record, logcat proof);
    sync docs/CURRENT_STATE.md, docs/orchestration/STATE.md + log.md (NOTE: STATE.md/
    log.md currently have uncommitted chief lines — commit them together with an
    English commit covering docs/orchestration + AGENTS.md changes from today,
    message like `docs: rule updates and task 053/054 orchestration state`).
    Code+jars+report as one English commit (e.g. `fix(aconfig): batch-package 11
    remaining flags runtime JARs for APK closure (task 055)`). Do NOT push.

## Authority

- Edit: `tools/package_aconfig_jars.py`, `tools/tests/test_package_aconfig_jars.py`,
  `tools/aosp_paths.py` (if needed), `SystemUI-core/build.gradle.kts`,
  new `libs/*-flags.jar`, docs listed, pyproject.toml/uv.lock (if needed via uv add).
- Run: gradle, pytest (uv), AOSP `m -j4` inside $AOSP_ROOT with out/ writes only,
  adb against emulator-5554 ONLY.

## Forbidden

- No AOSP source-tree modification. No SysUISdk modification.
- No touching other libs jars. No stubs, no suppressions.
- No `git push`. No touching w3M/w3N/w4 (LingerLane). No other tabs.
- adb: emulator-5554 only; if `adb devices` shows anything else, STOP.

## Acceptance

1. 11 jars in libs/, each sha256 == its AOSP javac source; owning module table in report.
2. `uv run pytest tools/tests/ -q` all pass.
3. Debug APK: each of the 11 `L.../Flags;` defined exactly once across dexes.
4. emulator-5554: boot_completed=1, stable SystemUI PID ≥ 5 min,
   zero NoClassDefFoundError for all 11 packages in logcat.
5. Report with full evidence; 2 English commits (docs-sync + code); not pushed.

## Reports To

Chief architect, tab w2:t1 (pane w2:p1). Report done/blocked via herdr message; never
idle silently. On hard block: print REDLINE-style stop reason and wait.
