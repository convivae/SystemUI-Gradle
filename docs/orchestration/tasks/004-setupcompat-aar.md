# Task 004: setupcompat AAR via local Maven

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: package `external/setupcompat` as a real AAR (code + resources) and deliver it through the local Maven catalog so `com.google.android.setupcompat.util.WizardManagerHelper` resolves. User decision 2026-08-13: AAR because the module has resources (`resource_dirs: ["main/res"]`); jar-only was waived for this case.

Authority: redline-gated — `gradle/libs.versions.toml` catalog-alias addition is a red-line area (CHARTER Part 5.4) and is **pre-approved by the user on 2026-08-13** for this exact change; any other toml edit remains forbidden. Commit but never push.

Allowed Paths: `tools/package_aosp_aar.py`, `tools/tests/test_package_aosp_aar.py`, `gradle/libs.versions.toml` (alias lines only), `SystemUI-core/build.gradle.kts`, `libs/aars/setupcompat.aar`, `libs/maven/com.android.systemui/setupcompat/**`, `docs/issues/`, `docs/orchestration/tasks/004-*.md`.

Forbidden Paths: everything else; especially `SystemUI-*/src/**`, any `res/` outside the packaging script's output, version numbers in the toml, `AGENTS.md`, `docs/adr/**`.

Steps:

- [ ] 1. Discover the AOSP inputs (all must exist; otherwise stop and report):

```bash
ls -l /home/conv/myspace/aosp/out/soong/.intermediates/external/setupcompat/setupcompat/android_common/javac/setupcompat.jar
ls -d /home/conv/myspace/aosp/external/setupcompat/main/res
ls -l /home/conv/myspace/aosp/external/setupcompat/AndroidManifest.xml
find /home/conv/myspace/aosp/out/soong/.intermediates/external/setupcompat -name 'R.txt' | head -3
```

- [ ] 2. Add a `"setupcompat"` entry to `CONFIGS` in `tools/package_aosp_aar.py`, following the existing config pattern (code jars list, res dirs, manifest, R.txt; no `exclude_prefixes` needed). Keep output deterministic.

- [ ] 3. Add a test in `tools/tests/test_package_aosp_aar.py` mirroring the existing config tests: source paths are the expected Soong/AOSP locations, no turbine paths, output name `setupcompat.aar`.

- [ ] 4. Package, install to local Maven, verify:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
python3 tools/package_aosp_aar.py --all
python3 tools/install_aar_to_maven.py
unzip -l libs/aars/setupcompat.aar | grep -E 'classes.jar|AndroidManifest.xml|res/' | head -5
unzip -l libs/maven/com.android.systemui/setupcompat/1.0.0/setupcompat-1.0.0.aar | grep -c 'com/google/android/setupcompat/'
```

Expected: tests OK; AAR contains classes.jar + manifest + res; Maven copy contains setupcompat classes.

- [ ] 5. Add the catalog alias in `gradle/libs.versions.toml` following the existing `systemui-*` alias pattern (e.g. `systemui-setupcompat = { group = "com.android.systemui", name = "setupcompat", version = "1.0.0" }`), then wire `implementation(libs.systemui.setupcompat)` into `SystemUI-core/build.gradle.kts` beside the other catalog AARs. No other toml changes.

- [ ] 6. Acceptance run:

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task004.log >/dev/null; grep -c 'setupcompat' /tmp/task004.log || echo '0 (setupcompat group gone)'
```

Expected: `0` setupcompat errors (overall failure on remaining groups is fine; record both numbers).

- [ ] 7. Append the dated result note to the issue record (user decision quoted, AAR contents, alias, error-group delta).

- [ ] 8. Worker commit (never push):

```bash
git add tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py gradle/libs.versions.toml \
  SystemUI-core/build.gradle.kts libs/aars/setupcompat.aar libs/maven/com.android.systemui/setupcompat \
  docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "feat(libs): package setupcompat AAR from AOSP and deliver via local Maven"
```

Acceptance (architect re-runs): Step 4 unzip checks + Step 6 grep; `git show --stat HEAD` limited to Allowed Paths.
