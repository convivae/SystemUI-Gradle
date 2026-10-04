# Task 054 — android.os.Flags runtime closure (package android-os-flags.jar)

## Background (chief-confirmed root cause, do NOT re-litigate)

Debug APK crash-loops because NLSUMI's first construction throws
`NoClassDefFoundError: Landroid/os/Flags;` at
`NotificationLockscreenUserManagerImpl.privateSpaceFlagsEnabled()` (source line 844,
`import static android.os.Flags.allowPrivateProfile`). The emulator's
`/system/framework/framework.jar` defines ONLY
`Lcom/android/internal/hidden_from_bootclasspath/android/os/Flags;` — the public
`Landroid/os/Flags;` does NOT exist on the device's bootclasspath. Stock AOSP SystemUI
references the hidden variant because Soong rewrites it via JarJarProvider; AGP does
not inherit that rewrite. Our compiled bytecode references the public name.

This is the **third** instance of the same family already fixed by
`libs/window-flags.jar` (task on 2026-08-24) and `libs/device-state-feature-flags.jar`.
User has approved fixing via the same precedent: package the owning Soong
`java_aconfig_library` javac JAR byte-identically into `libs/` and add an
`implementation(files(...))` edge in `SystemUI-core/build.gradle.kts`.

## Objective

1. Package `libs/android-os-flags.jar` from the AOSP Soong javac output.
2. Wire it into `:SystemUI-core` as `implementation(files(...))`.
3. Remove the three TEMP-DEBUG instrumentation blocks added for task053.
4. Prescan for any REMAINING same-family missing aconfig classes (public-name refs in
   our APK that have no public-name definition on the device bootclasspath).
5. Rebuild, redeploy to emulator-5554, verify crash loop is gone and PID is stable.
6. Update docs.

## Variant selection (evidence required)

Two candidate Soong javac JARs both contain the five runtime classes under
`android/os/`:

- **base**: `frameworks/base/android.os.flags-aconfig-java/android_common/javac/android.os.flags-aconfig-java.jar`
  — FeatureFlagsImpl reads via `android/os/flagging/PlatformAconfigPackageInternal.getBooleanFlagValue(I)Z`
- **export**: `frameworks/base/android.os.flags-aconfig-java-export/android_common/javac/android.os.flags-aconfig-java-export.jar`
  — FeatureFlagsImpl reads via `android/os/flagging/AconfigPackage.getBooleanFlagValue(Ljava/lang/String;Z)Z`

Selection rule, in order:
1. Follow the window-flags precedent: use the **base** (non-export) variant.
2. BUT first verify on the live emulator that the variant's backing API exists on the
   bootclasspath (`dexdump` the device framework.jar or the same-tree copy at
   `out/target/product/emu64x/system/framework/framework.jar`):
   - base requires `Landroid/os/flagging/PlatformAconfigPackageInternal;`
   - export requires `Landroid/os/flagging/AconfigPackage;`
3. If the chosen variant's backing API is absent on the device, pick the other variant
   and record the evidence. Whichever you pick, ALSO verify the backing API class is
   present in our SysUISdk android.jar or on the device — a bundled JAR whose backing
   API is missing would just move the crash.

Record the dexdump/javap evidence for the choice in the report.

## Steps

1. Add config entry to `tools/package_aconfig_jars.py` `CONFIGS`:
   `"android-os-flags"` → source above (chosen variant), destination
   `libs/android-os-flags.jar`, runtime package `android.os`.
   The existing validator requires exactly the five runtime `.class` entries
   (`.uau` metadata entries are ignored by design — verify).
2. Run `python3 tools/package_aconfig_jars.py android-os-flags`. Verify the packaged
   JAR is **byte-identical** to the AOSP source (`sha256sum` both, must match).
3. Add tests: extend `tools/tests/test_package_aconfig_jars.py` if it enumerates
   configs; run `python3 -m pytest tools/tests/test_package_aconfig_jars.py -q`.
4. In `SystemUI-core/build.gradle.kts`, add next to the existing window-flags /
   device-state-feature-flags block (same comment style, Chinese, referencing the
   JarJarProvider explanation):
   `implementation(files("${rootProject.projectDir}/libs/android-os-flags.jar"))`
5. **Remove TEMP-DEBUG instrumentation** added for task053 — three files, each block
   is marked `// CONV_ADD BEGIN: TEMP-DEBUG task053` … `// CONV_ADD END: TEMP-DEBUG task053`:
   - `SystemUI-core/src/com/android/systemui/dump/DumpManager.kt`
   - `SystemUI-core/src/com/android/systemui/SystemUIInitializer.java`
   - `SystemUI-core/src/com/android/systemui/SystemUIAppComponentFactoryBase.kt`
   Remove the blocks completely (restore byte-level match with AOSP source). Verify
   with `diff` against
   `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src/...` counterparts —
   must be identical. Then run `python3 tools/check_source_alignment.py --strict` and
   confirm MISSING/MISPLACED/EXTRA all 0.
6. **Prescan same-family hazards**: for every dex in the CURRENT debug APK
   (`app/build/outputs/apk/debug/app-debug.apk` — will be stale, rebuild first after
   step 4-5), list referenced `Flags`-family class descriptors of the form
   `L<package>/Flags;` where `<package>` starts with `android/` or
   `com/android/internal/`. For each, check whether the device bootclasspath defines
   the class (dexdump `out/target/product/emu64x/system/framework/framework.jar` and
   every jar in device `$BOOTCLASSPATH` if reachable, else the emu64x copies). Any
   referenced-but-not-defined class that is NOT bundled in our APK is a hazard —
   report the list. (`android/os/Flags` will now be bundled by this task.)
7. Rebuild: `./gradlew :app:assembleDebug`. Verify the new APK dexes contain a
   definition of `Landroid/os/Flags;` (`dexdump` grep `Class descriptor`), and that
   NO dex contains duplicate definitions (count must be exactly 1 across all dexes).
8. Deploy to **emulator-5554 ONLY** (verify `adb devices` shows exactly one emulator,
   `getprop ro.kernel.qemu`=1, product `emu64x`, ABI x86_64). Follow the established
   procedure: `adb root` → `disable-verity` → reboot → `wait-for-device` → `adb root`
   → `su 0 mount -o remount,rw /system_ext` → replace `/system_ext/priv-app/SystemUI/SystemUI.apk`
   atomically (same-dir tmp then mv), restore `root:root` `0644`
   `u:object_r:system_file:s0`, delete `oat/` and dalvik-cache for the app → reboot.
   Stock backup is at
   `/home/conv/myspace/task053-same-tree-x86_64-runtime/deploy/stock-backup/SystemUI.apk`
   (SHA-256 `dd1ff45acdf82700897a4adc587f67ff3f4f626d6ef240c6d75f1544f194b837`) —
   restore it if anything regresses.
9. Verify after boot: `sys.boot_completed=1`; SystemUI PID stable for ≥5 min (sample
   `pidof com.android.systemui` every 30s, must be constant); logcat has ZERO
   occurrences of `NoClassDefFoundError` for `android/os/Flags` and zero
   `alreadyRegistered` dump-name crash signatures; tag `SysUIDup` should be silent
   (instrumentation removed). Capture evidence to the report.
10. Write/update docs:
    - `docs/issues/2026-08-25-android-os-flags-runtime-closure.md` (evidence, variant
      choice, hashes, prescan results, deployment verification)
    - append a line to `docs/GRADLE_MIGRATION_LOG.md` if that file tracks such fixes
      (check how window-flags was logged, mirror it)
    - update `docs/CURRENT_STATE.md` blocker/dependency state minimally and
      `docs/orchestration/STATE.md` + `docs/orchestration/log.md`.
11. Commit with English message (e.g. `fix(aconfig): package android.os.flags runtime
    JAR for APK closure (task 054)`), do NOT push (chief pushes).

## Authority

- You may edit: `tools/package_aconfig_jars.py`, `tools/tests/test_package_aconfig_jars.py`,
  `SystemUI-core/build.gradle.kts`, the three instrumented source files (TEMP-DEBUG
  removal only), `libs/android-os-flags.jar` (new), docs listed above.
- You may run: gradle builds, adb against emulator-5554 only, pytest.

## Allowed Paths

- `/home/conv/myspace/SystemUI-Gradle/` (main worktree, this task works in main)
- Read-only: `/home/conv/myspace/aosp/out/` (javac JAR sources, framework.jar),
  `/home/conv/myspace/task053-same-tree-x86_64-runtime/`

## Forbidden Paths / Actions

- Do NOT modify AOSP source tree (`/home/conv/myspace/aosp/` outside `out/`).
- Do NOT modify SysUISdk (`/home/conv/Android/Sdk/platforms/android-SysUISdk/`).
- Do NOT touch other libs/*.jar (window-flags.jar and device-state-feature-flags.jar
  must stay byte-identical; do not re-run the packager for other configs).
- Do NOT create stubs, do NOT add broad suppressions.
- Do NOT push to remote. Do NOT touch the LingerLane workspace (w3M/w3N/w4).
- Do NOT close or restart other tabs/panes.
- Device writes: emulator-5554 ONLY. If `adb devices` shows anything else, STOP.

## Acceptance

1. `sha256sum libs/android-os-flags.jar` == sha256 of the chosen AOSP javac JAR.
2. `python3 -m pytest tools/tests/test_package_aconfig_jars.py -q` passes.
3. Three TEMP-DEBUG blocks removed; `diff` vs AOSP source clean;
   `check_source_alignment.py --strict` MISSING/MISPLACED/EXTRA = 0.
4. Rebuilt debug APK: exactly one dex defines `Landroid/os/Flags;` (definition, not
   just reference).
5. Prescan table in report: every referenced `Flags`-family descriptor →
   device-defined or APK-bundled; list any residual hazards.
6. Emulator: `sys.boot_completed=1`, stable SystemUI PID ≥5 min, zero
   `NoClassDefFoundError` for android/os/Flags in logcat, zero duplicate-dump-name
   crashes.
7. Report at `docs/issues/2026-08-25-android-os-flags-runtime-closure.md` with all
   evidence; commit made locally (English message), not pushed.

## Reports To

Chief architect in tab `w2:t1` (pane `w2:p1`). On completion or hard block, write the
report and send a herdr message; do not idle silently.
