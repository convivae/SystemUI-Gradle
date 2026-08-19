# Task 012: Preserve `androidprv` through the AGP resource pipeline

> Orchestrated brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract skill. Use systematic-debugging and test-driven-development. Worker commits but never pushes.

## Goal

Fix Factor 2 from task 011: AGP 9.3.1 drops `xmlns:androidprv` while merging values resources. Implement the smallest build-only repair so `:app:processDebugResources` resolves all private framework references without touching AOSP resources.

## Spec and plan

Read completely before work:

1. `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md`
2. `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md` §8.2
3. `docs/issues/2026-08-13-sysuisdk-reproducible-build.md` §8.4
4. `docs/superpowers/plans/2026-08-13-agp-androidprv-namespace-fix.md`

## Authority

`redline-gated`. The user explicitly approved the recommended build-logic repair on 2026-08-13. This approval covers `app/build.gradle.kts` plus a Python helper/tests for post-merge/pre-link handling. It does **not** cover source/res edits, Gradle property changes, version changes, task bypasses, or new build modules.

## Allowed Paths

- `app/build.gradle.kts`
- `tools/patch_androidprv_merged_resources.py` (new, only if needed)
- `tools/tests/test_patch_androidprv_merged_resources.py` (new, only if needed)
- `docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md` (new)
- `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md`
- `docs/orchestration/tasks/012-preserve-androidprv-namespace.md`
- `docs/superpowers/plans/2026-08-13-agp-androidprv-namespace-fix.md` (checkbox/evidence updates only)

## Forbidden Paths

Everything else. In particular: all `SystemUI-*/src/**`, all `SystemUI-*/res*/**`, every source resource, `gradle.properties`, `gradle/libs.versions.toml`, `settings.gradle.kts`, `buildSrc/`, and AGP/AAPT task disabling.

If the only viable route crosses a Forbidden Path, output:

```text
REDLINE: androidprv build-only repair unavailable — <evidence and proposed next option>
```

and stop.

## Required execution

- [ ] 1. Reproduce the baseline on this branch:

```bash
./gradlew :app:processDebugResources --console=plain 2>&1 | tee /tmp/task012-before.log >/dev/null
grep -E 'BUILD (SUCCESSFUL|FAILED)' /tmp/task012-before.log | tail -1
grep -c 'androidprv' /tmp/task012-before.log
```

Expected before fix: BUILD FAILED and about 20 `androidprv` hits. Record the actual values.

- [ ] 2. Audit AGP 9.3.1 public APIs (`SingleArtifact`, `MultipleArtifact`, `Artifacts`, `SdkComponents`) and document the result. Prefer a public transformable merged-resource artifact if one exists. Known fact to verify: `SdkComponents.aapt2.executable` is public; a public `SingleArtifact.MERGED_RES` was not visible in the architect's initial `gradle-api-9.3.1.jar` inspection.

- [ ] 3. Perform one disposable, minimal hypothesis test before production code: add the declaration only to temporary copies of affected merged values XML, compile those files with AGP's selected AAPT2, replace only the corresponding build-intermediate flats, and retry link. Clean app outputs afterward. If this does not eliminate the 20 errors, return to root-cause analysis; do not stack fixes.

- [ ] 4. If the public artifact route is unavailable, implement the concrete fallback in the plan:
  - write fixture tests first;
  - run them and capture the expected RED;
  - implement the Python CLI with `--merged-dir`, `--compiled-dir`, `--aapt2`;
  - patch temporary copies only, compile affected values XML, atomically replace matching `.arsc.flat` files;
  - print `scanned=<n> patched=<n> compiled=<n> unresolved=0`;
  - use AGP's `androidComponents.sdkComponents.aapt2` provider, not a hard-coded build-tools path;
  - wire `merge<Variant>Resources → patch<Variant>AndroidPrvMergedResources → process<Variant>Resources` in `app/build.gradle.kts`.

- [ ] 5. Run unit tests:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tee /tmp/task012-tests.log
grep -E '^(Ran|OK|FAILED)' /tmp/task012-tests.log
```

Expected: `Ran` greater than 116 and `OK`.

- [ ] 6. Acceptance from a clean app resource state:

```bash
./gradlew :app:clean :app:processDebugResources --console=plain 2>&1 | tee /tmp/task012.log >/dev/null
grep -E 'BUILD (SUCCESSFUL|FAILED)' /tmp/task012.log | tail -1
grep -c 'androidprv' /tmp/task012.log || echo '0 (androidprv errors gone)'
```

Expected: `BUILD SUCCESSFUL` and 0 `androidprv` hits. The helper log must show `unresolved=0` if the fallback is used.

- [ ] 7. APK diagnostics:

```bash
./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/task012-app.log >/dev/null
grep -E 'BUILD (SUCCESSFUL|FAILED)' /tmp/task012-app.log | tail -1
```

If successful, record APK path, byte size, and SHA-256. If a new task fails, record the task and first errors, then stop without widening scope.

- [ ] 8. Update the architecture and issue docs with actual evidence; tick the plan/brief checkboxes truthfully. Run `git diff --check`.

- [ ] 9. Commit in English, never push:

```bash
git add app/build.gradle.kts tools/patch_androidprv_merged_resources.py \
  tools/tests/test_patch_androidprv_merged_resources.py \
  docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md \
  docs/issues/2026-08-13-agp-androidprv-namespace-fix.md \
  docs/orchestration/tasks/012-preserve-androidprv-namespace.md \
  docs/superpowers/plans/2026-08-13-agp-androidprv-namespace-fix.md
git commit -m "build(app): preserve androidprv namespace through resource linking"
```

Drop optional tool/test paths from `git add` if a public artifact transform makes them unnecessary.

## Acceptance

Architect re-runs Steps 5 and 6, checks `git diff --check`, and verifies the commit touches only Allowed Paths. Success means `:app:processDebugResources` is green with 0 `androidprv` hits; APK success is diagnostic and may expose a new layer.

## Reports To

Chief architect in the main herdr pane. Completion requires an English commit, updated docs/checklists, real output, and a terminal-final `HANDOFF:` block.
