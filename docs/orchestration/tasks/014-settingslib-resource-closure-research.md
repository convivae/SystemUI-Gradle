# Task 014 — Research SettingsLib Resource Closure Packaging

**Authority:** `self-commit` for the two documentation files in Allowed Paths only. This is a read-only research task: no dependency, code, resource, artifact, SDK, or build-logic change is authorized.

**Reports To:** chief architect in the main herdr session.

**Issue:** `docs/issues/2026-08-19-settingslib-resource-closure-research.md`

**Output:** `docs/architecture/2026-08-19-settingslib-resource-closure-research.md`

## Goal

Determine from primary sources how the reference project packages SettingsLib resources and whether the current project should use one merged `SettingsLib.aar` or independent per-target res-only AARs.

## Primary Sources To Inspect

- `/home/conv/myspace/CarSystemUIGradle/`
  - SettingsLib-related Gradle files, Python packaging/install scripts, local Maven artifacts, dependency docs, and migration notes.
- `/home/conv/myspace/aosp/frameworks/base/packages/SettingsLib/Android.bp` and every relevant child `Android.bp`.
- `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SettingsLib/**`
  - Look for merged resource outputs, AAR/package artifacts, R.txt, and evidence of Soong resource ordering.
- Current project:
  - `tools/package_aosp_aar.py`
  - `tools/install_aar_to_maven.py`
  - `SystemUI-res/build.gradle.kts`
  - `gradle/libs.versions.toml`
  - Task 013 issue and implementation.

## Required Findings

1. State exactly what the reference project does for SettingsLib resources, with file paths and line-level evidence.
2. State whether it uses a monolithic merged AAR, multiple AARs, copied resource roots, or another mechanism.
3. Explain how duplicate relative resource paths are handled, or prove that the reference mechanism avoids them.
4. Determine whether AOSP Soong already emits a reusable complete SettingsLib merged-resource/AAR/package artifact. If yes, identify the exact artifact and whether its content is complete; if no, identify the closest useful intermediates.
5. Produce a quantitative resource-closure audit: direct SettingsLib static-lib targets with `resource_dirs`, total resource files, and duplicate relative-path groups across the relevant closure. Use read-only Python or shell commands; do not create repository scripts.
6. Compare at least these three options and recommend one:
   - one merged `SettingsLib.aar` containing the full resource closure;
   - one res-only AAR per Soong resource target with transitive POM dependencies;
   - one res-only AAR per target with explicit consumer dependencies.
7. The recommendation must address rule R/B, provenance, duplicate paths, reproducibility, local Maven semantics, consumer interface depth, and rollback/migration from the Task 013 `SettingsLibSettingsTheme` AAR.

## Allowed Paths

- `docs/architecture/2026-08-19-settingslib-resource-closure-research.md`
- `docs/issues/2026-08-19-settingslib-resource-closure-research.md`
- `docs/orchestration/tasks/014-settingslib-resource-closure-research.md`

## Forbidden Paths

- all source/resource/build/dependency files outside the three documentation paths above
- every `SystemUI-*/src/**` and `SystemUI-*/res*/**`
- every AOSP file under `/home/conv/myspace/aosp/`
- every reference-project file under `/home/conv/myspace/CarSystemUIGradle/`
- `libs/**`, `gradle/**`, `settings.gradle.kts`, `build.gradle.kts`, module build files, `tools/**`
- stubs, suppressions, source exclusions, generated resources, or build bypasses

## Mandatory Method

- Invoke `worker-contract`, then `research` and `systematic-debugging`.
- Use only primary sources. Cite exact paths; include line numbers for text files and file-entry names for archives.
- Do not infer reference behavior from memory. Open the actual files/artifacts.
- If evidence is absent, write `not found` and explain the search command/scope.
- Do not modify the reference project or AOSP checkout.
- Commit the two output documents and this checked-off brief in English. Never push.

## Acceptance

```bash
test -s docs/architecture/2026-08-19-settingslib-resource-closure-research.md
rg -n "CarSystemUIGradle|Soong|duplicate|Recommendation|monolithic|per-target" docs/architecture/2026-08-19-settingslib-resource-closure-research.md
git diff --check
```

Expected: first command exits 0; second prints evidence headings; third prints nothing.

## Checklist

- [ ] CONTRACT printed and model verified by architect
- [ ] reference-project mechanism identified with primary-source evidence
- [ ] AOSP/Soong reusable artifact search completed and documented
- [ ] duplicate-path behavior documented
- [ ] quantitative closure audit included
- [ ] three options compared and one recommended
- [ ] migration/rollback implications for Task 013 documented
- [ ] issue file updated with truthful execution record
- [ ] `git diff --check` clean
- [ ] English commit created; no push
- [ ] terminal-final `HANDOFF:` printed
