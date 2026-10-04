# Task 002: Package zxing-core / wifi-flags / wm-shell-flags JARs

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: extend `tools/package_aconfig_jars.py` with three new entries and wire the resulting JARs into `:SystemUI-core` so the `com.google.zxing.*`, `com.android.wifi.flags.Flags`, and `com.android.wm.shell.Flags` javac errors disappear.

Authority: self-commit (never push). No red-line areas (build-script dependency wiring only; no version-matrix change).

Allowed Paths: `tools/package_aconfig_jars.py`, `tools/tests/test_package_aconfig_jars.py`, `SystemUI-core/build.gradle.kts`, `libs/zxing-core.jar`, `libs/wifi-flags.jar`, `libs/wm-shell-flags.jar`, `docs/issues/`, `docs/orchestration/tasks/002-*.md`.

Forbidden Paths: everything else; especially `SystemUI-*/src/**`, `SystemUI-*/res*/**`, `gradle/**`, `settings.gradle.kts`, `AGENTS.md`, `docs/adr/**`.

Steps:

- [x] 1. Verify the three AOSP sources exist and are valid zips:

```bash
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/external/zxing/zxing-core/android_common/javac/zxing-core.jar
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/packages/modules/Wifi/flags/wifi_aconfig_flags_lib/android_common/javac/wifi_aconfig_flags_lib.jar
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/libs/WindowManager/Shell/aconfig/com_android_wm_shell_flags_lib/android_common/javac/com_android_wm_shell_flags_lib.jar
```

Expected: three files listed. If any is missing, stop and report (do not substitute another artifact).

- [x] 2. Add three entries to `CONFIGS` in `tools/package_aconfig_jars.py`, following the existing `"systemui-shared-flags"` pattern (source `Path` constants at module top, turbine guard already in `copy_jar`):

```python
"zxing-core": (ZXING_CORE_JAVAC, Path("libs/zxing-core.jar")),
"wifi-flags": (WIFI_FLAGS_JAVAC, Path("libs/wifi-flags.jar")),
"wm-shell-flags": (WM_SHELL_FLAGS_JAVAC, Path("libs/wm-shell-flags.jar")),
```

- [x] 3. Extend `tools/tests/test_package_aconfig_jars.py`: for each new config assert (a) the source path contains `/javac/` and not `turbine`, (b) destination is under `libs/` with the expected name, (c) `copy_jar` produces a byte-identical copy (reuse the existing test helpers/patterns).

- [x] 4. Run the tool tests:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
```

Expected: `OK`, test count > 60 (new tests included).

- [x] 5. Run the packager and verify content:

```bash
python3 tools/package_aconfig_jars.py --all   # use the real CLI flag from --help if different
unzip -l libs/zxing-core.jar | grep -c 'com/google/zxing/'
unzip -l libs/wifi-flags.jar | grep 'com/android/wifi/flags/Flags.class'
unzip -l libs/wm-shell-flags.jar | grep 'com/android/wm/shell/Flags.class'
```

Expected: zxing classes present; both `Flags.class` entries present.

- [x] 6. Wire into `SystemUI-core/build.gradle.kts` dependencies, next to the existing flags-jar lines, with comments matching house style:

```kotlin
// zxing-core: static lib of SettingsLib (packaged into the APK in AOSP)
implementation(files("${rootProject.projectDir}/libs/zxing-core.jar"))
// Wi-Fi aconfig flags (platform-provided on device; compile-time only)
compileOnly(files("${rootProject.projectDir}/libs/wifi-flags.jar"))
// WM-Shell aconfig flags (platform-provided on device; compile-time only)
compileOnly(files("${rootProject.projectDir}/libs/wm-shell-flags.jar"))
```

Rationale to keep in the issue note: zxing is a Soong `static_libs` entry whose classes are dexed into the APK (`implementation`); aconfig flags classes are provided by the system image (`compileOnly`), matching the `settingslib-flags.jar` precedent.

- [x] 7. Acceptance run (from repo root):

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task002.log | grep -cE 'error:'
grep -cE 'com\.google\.zxing|com\.android\.wifi\.flags|com\.android\.wm\.shell\.Flags' /tmp/task002.log || echo '0 (target groups gone)'
```

Expected: build still fails overall (other groups remain — that is fine, rule I), but the second command prints `0` matches for the three target groups. Record both numbers.

- [x] 8. Update `docs/issues/2026-08-12-current-progress-standards-review.md` (append a dated note under the Task 7 section: what was packaged, source paths, scopes chosen, javap/unzip evidence, error-group delta).

- [x] 9. Worker commit (never push):

```bash
git add tools/package_aconfig_jars.py tools/tests/test_package_aconfig_jars.py \
  SystemUI-core/build.gradle.kts libs/zxing-core.jar libs/wifi-flags.jar libs/wm-shell-flags.jar \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "fix(libs): package zxing-core and wifi/wm-shell flags jars from AOSP"
```

Acceptance (architect re-runs): Step 7's two commands; plus `git show --stat HEAD` shows only Allowed Paths.
