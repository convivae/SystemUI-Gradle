# Task 007: AAPT `android:featureFlag` / `--feature_flags` research (docs only)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: investigate why `:app:processDebugResources` fails with `AAPT: error: element 'activity' has flag 'com.android.wm.shell.enable_retrievable_bubbles' not found in flags from --feature_flags parameter`, and produce a compliant-fix options document so the user can choose. **Research only — do not change any build file, manifest, AAR, or SDK.**

Context: the error comes from the original AOSP WindowManager-Shell manifest (`frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml:39,53`, `android:featureFlag="com.android.wm.shell.enable_retrievable_bubbles"`), packaged faithfully into `libs/aars/WindowManager-Shell.aar`. The blocker was latent at Task 7 (javac failed first; the task was never scheduled) and surfaced after the 2026-08-13 fix wave. Reproduction log: `/tmp/waveC-app.log`.

Authority: self-commit (never push), docs only.

Allowed Paths: `docs/architecture/2026-08-13-aapt-feature-flags-options.md`, `docs/issues/`, `docs/orchestration/tasks/007-*.md`.

Forbidden Paths: everything else (no build files, no manifests, no AAR/ARSC, no SDK edits).

Steps:

- [ ] 1. Reproduce and capture the complete error set: `./gradlew :app:processDebugResources --console=plain 2>&1 | tee /tmp/task007.log >/dev/null`; list **all** missing flags and **all** manifests involved (not just the first error).
- [ ] 2. Survey the dependency graph: which packaged AARs / module manifests use `android:featureFlag` (`for a in libs/aars/*.aar; do ...; done` extracting AndroidManifest.xml, plus `SystemUI-*/AndroidManifest.xml` and `app/src/main/AndroidManifest.xml`). Record the full flag inventory needed.
- [ ] 3. Establish where AAPT2's `--feature_flags` input comes from: check (a) AAPT2 help/source for the flag (`aapt2 link --help | grep -i feature`; AOSP `frameworks/base/tools/aapt2/` source), (b) how Soong passes it (`grep -rn 'feature' /home/conv/myspace/aosp/build/soong/java/aapt2.go` and related), (c) how AGP derives it — inspect the AGP 9.3.1 task/classes if reachable, and check what a **stock official SDK platform** (e.g. `~/Android/Sdk/platforms/android-3*`) contains for feature flags vs. our custom `android-SysUISdk` platform directory.
- [ ] 4. Check the reference project: `grep -rn 'featureFlag\|feature_flags' /home/conv/myspace/CarSystemUIGradle --include='*.md' --include='*.kts' --include='*.xml' | head` — did CarSystemUIGradle hit and solve this?
- [ ] 5. Write `docs/architecture/2026-08-13-aapt-feature-flags-options.md` with: problem statement; the full flag/manifest inventory from steps 1–2; the mechanism findings from step 3 with command evidence; the reference-project finding; at least three options — (a) patch SysUISdk with the feature-flags declarations (AGENTS.md §2.4 custom-SDK precedent), (b) an AGP/AAPT-level mechanism to supply flags if one exists (DSL, gradle property, or task input — cite official docs), (c) CONV-marked adjustment of the manifest inside the packaging pipeline (rule R / ADR 0004 path, needs explicit user approval) — each with provenance compliance and a recommendation.
- [ ] 6. Append a dated process note to a new `docs/issues/2026-08-13-aapt-feature-flags-research.md` (rule D).
- [ ] 7. Worker commit (never push):

```bash
git add docs/architecture/2026-08-13-aapt-feature-flags-options.md docs/issues/2026-08-13-aapt-feature-flags-research.md docs/orchestration/tasks/007-aapt-feature-flags-research.md
git commit -m "docs: research AAPT feature-flags options for WM-Shell manifest"
```

Acceptance (architect re-runs): doc exists with command evidence for steps 1–4, complete flag inventory, three options with a recommendation; `git show --stat HEAD` limited to Allowed Paths.
