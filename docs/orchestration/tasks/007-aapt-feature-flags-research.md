# Task 007: AAPT `android:featureFlag` / `--feature_flags` research (docs only)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: investigate why `:app:processDebugResources` fails with `AAPT: error: element 'activity' has flag 'com.android.wm.shell.enable_retrievable_bubbles' not found in flags from --feature_flags parameter`, and produce a compliant-fix options document so the user can choose. **Research only — do not change any build file, manifest, AAR, or SDK.**

Context: the error comes from the original AOSP WindowManager-Shell manifest (`frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml:39,53`, `android:featureFlag="com.android.wm.shell.enable_retrievable_bubbles"`), packaged faithfully into `libs/aars/WindowManager-Shell.aar`. The blocker was latent at Task 7 (javac failed first; the task was never scheduled) and surfaced after the 2026-08-13 fix wave. Reproduction log: `/tmp/waveC-app.log`.

Authority: self-commit (never push), docs only.

Allowed Paths: `docs/architecture/2026-08-13-aapt-feature-flags-options.md`, `docs/issues/`, `docs/orchestration/tasks/007-*.md`.

Forbidden Paths: everything else (no build files, no manifests, no AAR/ARSC, no SDK edits).

Steps:

- [x] 1. Reproduced and captured the complete error set: `./gradlew :app:processDebugResources --console=plain 2>&1 | tee /tmp/task007.log` (exit 1). **All** missing flags = exactly one (`com.android.wm.shell.enable_retrievable_bubbles`); **all** manifests involved = one (transformed `WindowManager-Shell-1.0.0/AndroidManifest.xml`), two `<activity>` elements (lines 37, 51). grep confirms no other feature-flag errors. See options doc §2.1.
- [x] 2. Surveyed the dependency graph (`for a in libs/aars/*.aar; do unzip -p "$a" AndroidManifest.xml | grep -i featureFlag; done` + `libs/maven/**/*.aar` + `SystemUI-*/AndroidManifest.xml` + `app/src/main/AndroidManifest.xml`). Full inventory: `android:featureFlag` appears **only** in `libs/aars/WindowManager-Shell.aar` (lines 39, 53) and its Maven twin; no module/app manifest uses it. See options doc §2.2.
- [x] 3. Established where `--feature_flags` comes from: (a) `aapt2 link --help` shows `--feature-flags arg`; AOSP source `cmd/Link.h:337` + `link/FeatureFlagsFilter.cpp:86-90` + `FeatureFlagsFilter.h:36` (`fail_on_unrecognized_flags = true` default); (b) Soong `build/soong/java/aapt2.go:107,284` passes `--feature-flags @<aconfig-file>`; (c) **AGP 9.3.1 has zero support** (no class in gradle/builder jars mentions it); stock `android-35/36/37` and custom `android-SysUISdk` contain **no** feature-flag/aconfig/`.pb` files (flags are a build-time CLI input, not an SDK-platform property). See options doc §3.
- [x] 4. Checked the reference project: `grep -rniE 'featureFlag|feature_flags' CarSystemUIGradle --include='*.md' --include='*.kts' --include='*.xml'` → only the `FeatureFlags` Java class, never the manifest attribute. `diff` of the two AAR manifests shows CarSystemUIGradle's WindowManager-Shell AAR manifest is **stripped** (no `<application>`, no `featureFlag`); it never passes `--feature-flags`. Soong `manifest_fixer` intermediate **retains** featureFlag (lines 32, 39), so the reference's stripped manifest came from another packaging path. See options doc §4.
- [x] 5. Wrote `docs/architecture/2026-08-13-aapt-feature-flags-options.md` with: problem statement; full flag/manifest inventory (§2); mechanism findings with command evidence (§3); reference-project finding (§4); three options — (a) patch SysUISdk [NOT viable: category error, §3.5 evidence], (b) AGP `androidResources.additionalParameters` [viable, recommended], (c) CONV-marked manifest strip [viable but worse, needs user approval] — each with provenance compliance and a recommendation (§5–§6).
- [x] 6. Appended dated process note `docs/issues/2026-08-13-aapt-feature-flags-research.md` (rule D).
- [x] 7. Worker commit (never push):

```bash
git add docs/architecture/2026-08-13-aapt-feature-flags-options.md docs/issues/2026-08-13-aapt-feature-flags-research.md docs/orchestration/tasks/007-aapt-feature-flags-research.md
git commit -m "docs: research AAPT feature-flags options for WM-Shell manifest"
```

Acceptance (architect re-runs): doc exists with command evidence for steps 1–4, complete flag inventory, three options with a recommendation; `git show --stat HEAD` limited to Allowed Paths.
