# Task 003: KSP + Dagger for :SystemUI-shared

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: make `:SystemUI-shared` run Dagger annotation processing via KSP so the three missing `SystemUnfoldSharedModule_*Factory` classes (used by `:SystemUI-unfold` sources compiled into core javac) are generated. Mirrors AOSP `shared/Android.bp` `SystemUISharedLib` `plugins: ["dagger2-compiler"]`.

Authority: self-commit (never push). No red-line areas.

Allowed Paths: `SystemUI-shared/build.gradle.kts`, `docs/issues/`, `docs/orchestration/tasks/003-*.md`.

Forbidden Paths: everything else; especially `SystemUI-shared/src/**`, `SystemUI-*/res*/**`, `gradle/**`, version catalogs, `AGENTS.md`.

Steps:

- [ ] 1. Read `SystemUI-unfold/build.gradle.kts` (the proven KSP pattern) and `SystemUI-shared/build.gradle.kts` (current state: has `implementation(libs.dagger)` but no KSP).

- [ ] 2. Apply the minimal diff to `SystemUI-shared/build.gradle.kts`: add `id("com.google.devtools.ksp")` to the plugins block and `ksp(libs.dagger.compiler)` to dependencies, mirroring the unfold module's exact style and placement. Do not change versions, do not add other processors.

- [ ] 3. Build and check generated factories:

```bash
./gradlew :SystemUI-shared:kspDebugKotlin --console=plain 2>&1 | tail -5
find SystemUI-shared/build/generated/ksp -name 'SystemUnfoldSharedModule*Factory*' | sort
```

Expected: BUILD SUCCESSFUL; the three factories from the Task 7 issue record (`SystemUnfoldSharedModule_Companion_ProvideBgLooperFactory`, `UnfoldBgDispatcherFactory`, `UnfoldBgProgressHandlerFactory`) are generated (exact filenames may live under `java/` or `kotlin/` output dirs — find must list them).

- [ ] 4. Acceptance run:

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task003.log >/dev/null; grep -cE 'SystemUnfoldSharedModule_.*Factory|UnfoldBg(Dispatcher|ProgressHandler)Factory' /tmp/task003.log || echo '0 (factory group gone)'
```

Expected: `0` matches for the factory group (overall build may still fail on other groups; record both numbers).

- [ ] 5. Append the dated result note to `docs/issues/2026-08-12-current-progress-standards-review.md` (pattern mirrored, generated evidence, error-group delta).

- [ ] 6. Worker commit (never push):

```bash
git add SystemUI-shared/build.gradle.kts docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build(shared): run Dagger via KSP in SystemUI-shared"
```

Acceptance (architect re-runs): Step 3 find command + Step 4 grep.
