# Task 061 — Release round 4: -keep fix for R8 horizontal class merging

## Goal

Apply the chief-approved (user-delegated, 2026-08-26) fix for the round-3 crash
(R8 horizontal class merging breaking DumpManager's name-keyed registration),
rebuild, redeploy, and re-run the runtime gate. Target: `RELEASE_RUNTIME_PASS`.

## Root cause being fixed (from task 060b forensics, report
## `docs/issues/2026-08-26-release-runtime-closure.md` Round 3)

R8 full-mode horizontal class merging collapses structurally-identical no-op
CoreStartables into one runtime class. `DumpManager.registerDumpable` keys by
`module::class.java.name` and rejects distinct instances sharing a name →
`IllegalArgumentException: 'com.android.systemui.CoreStartable$Nop' is already
registered` → 195-FATAL crash loop. Class names in the stack were REAL
(`-dontobfuscate` works); this is the second, distinct R8 divergence.

## Authority

- You MAY edit `app/proguard_gradle.flags` (add the approved lines + minimal comment).
  No other source file. Report + one log.md line + local commits; **no push**.
- Device emulator-5554 mutation only via the established staged procedure.
- Only Gradle activity on the tree. Stop idle Kotlin/AS daemons before building
  (memory: host 30 GiB, swap nearly full; two OOM kills happened in task 060).

## Approved fix (exact)

Add to `app/proguard_gradle.flags`:

```proguard
# R8 horizontal class merging collapses identity-distinct CoreStartables into one
# runtime class; DumpManager registers dumpables by class name and rejects distinct
# instances sharing a name. Keep these classes un-merged (task 060b round-3 crash).
-keep class com.android.systemui.CoreStartable$Nop { *; }
-keep class com.android.systemui.NoOpCoreStartable { *; }
-keep class com.android.systemui.flags.FeatureFlagsReleaseStartable { *; }
```

## Steps

1. **Preflight**: emulator-5554 healthy on Debug baseline (on-device sha e8aad131,
   PID stable — task 060b just restored it; if not true, stop and report).
   `free -h`; stop idle daemons.
2. Apply the fix; `git diff` sanity.
3. `./gradlew :app:assembleRelease --console=plain --max-workers=4` → expect
   BUILD SUCCESSFUL (~2 min). Record size + sha256.
4. **Static merge validation** (before deploying): in
   `app/build/outputs/mapping/release/mapping.txt`, confirm the three kept classes
   appear as identity mappings (name -> same name) and find no remaining case where
   a `com.android.systemui.**` class whose simple name ends in `Startable` or `Nop`
   maps to a DIFFERENT class name (residual horizontal merge among dumpable
   registrants). If residual merges among CoreStartable-registered classes remain,
   stop and report with the mapping evidence (do NOT add more keeps on your own).
5. Deploy via staged procedure (push → remount rw → staged cp → **sha gate** →
   atomic mv → root:root 0644 system_file → clear oat/dalvik → reboot).
6. Runtime gate: boot_completed=1; PID stable 10×30 s; `logcat -b crash -d` zero
   FATAL; full logcat `FATAL EXCEPTION|NoClassDefFoundError`=0; dumpsys StatusBar
   (+NotificationShade/Taskbar); QS expand/collapse bonus via
   `cmd statusbar expand-settings`.
7. **Failure protocol**: new failure class → capture full stack(s), classify with
   file:line evidence, restore Debug e8aad131 (verify), stop, report. No speculative
   fixes.
8. **Report**: append "Round 4" to
   `docs/issues/2026-08-26-release-runtime-closure.md`; one log.md line; local
   commits (fix commit separate from report commit). Final four-part report.

## Acceptance

- PASS: verdict `RELEASE_RUNTIME_PASS` (Release APK on device, sha verified, PID
  stable 10×30 s, zero FATAL/NCDFE, StatusBar visible).
- FAIL acceptable if root cause captured + Debug restored + classified.

## Model constraint

joycode GLM-5.3 or GLM-5.2 only.
