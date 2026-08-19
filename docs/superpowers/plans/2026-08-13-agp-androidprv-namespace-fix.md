# AGP androidprv namespace fix implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:systematic-debugging and superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the private Android resource namespace through the AGP 9.3.1 resource pipeline so `:app:processDebugResources` resolves all `androidprv:` references without modifying AOSP resource sources.

**Architecture:** First confirm whether AGP 9.3.1 exposes a public transformable merged-resource artifact. If it does, use that public API. If it does not, use a deterministic Python helper wired between `merge<Variant>Resources` and `process<Variant>Resources`: copy only merged values XML files containing `androidprv:`, inject the missing namespace in the temporary copy, recompile those files with AGP's own `SdkComponents.aapt2` executable, and atomically replace the corresponding `.arsc.flat` intermediates. Source resources remain untouched.

**Tech Stack:** AGP 9.3.1 Variant/SdkComponents API, Gradle Kotlin DSL, Python 3, AAPT2, unittest.

**Spec:** `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md` §8.2 and `docs/issues/2026-08-13-sysuisdk-reproducible-build.md` §8.4.

## Global Constraints

- User approved the build-logic repair on 2026-08-13; no AOSP mirrored `res/` or source file may be edited.
- Rule R remains absolute: if build logic cannot solve the issue, stop with `REDLINE:` rather than changing resources.
- Use AGP's `androidComponents.sdkComponents.aapt2` provider; do not hard-code an SDK build-tools path.
- Scripts under `tools/` must be Python.
- No task disabling, AAPT bypass, generated stub, dependency/version change, or module-boundary change.
- Worker commits in English and never pushes.

---

## File Map

- Create `tools/patch_androidprv_merged_resources.py`: deterministic CLI that patches temporary merged-values copies and recompiles their AAPT2 flat outputs.
- Create `tools/tests/test_patch_androidprv_merged_resources.py`: red/green fixture coverage for namespace injection, qualifier-to-flat mapping, no-op/error behavior, and idempotence.
- Modify `app/build.gradle.kts`: register per-variant ordering between `merge<Variant>Resources`, the patch task, and `process<Variant>Resources`; resolve AAPT2 through the public SDK components provider.
- Create `docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md`: public-API audit, evidence, chosen mechanism, and limitations.
- Create/update `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md`: command evidence and truthful build result.

---

### Task 1: Reproduce and audit the AGP seam

**Files:**
- Create: `docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md`
- Modify: `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md`

**Interfaces:**
- Consumes: overlaid live SysUISdk from task 011; `/tmp/task011.log`; AGP 9.3.1 `gradle-api` and plugin jars.
- Produces: an evidence-backed verdict on public artifact-transform support and the exact fallback task ordering.

- [ ] **Step 1: Reproduce the baseline**

Run `./gradlew :app:processDebugResources --console=plain` and record `BUILD FAILED`, the failing task, and the `androidprv` count (expected 20 before the fix).

- [ ] **Step 2: Audit the public API**

Inspect AGP 9.3.1's public `SingleArtifact`, `MultipleArtifact`, `Artifacts`, and `SdkComponents` APIs with `javap`. Record whether a transformable merged-resource artifact exists. `SdkComponents.aapt2.executable` is known public API and must be used by the fallback.

- [ ] **Step 3: Test one hypothesis manually**

On disposable build intermediates only, inject `xmlns:androidprv="http://schemas.android.com/apk/prv/res/android"` into temporary copies of all merged values XML files containing `androidprv:`, compile them with the AGP-selected AAPT2, replace the matching temporary flat outputs, and retry link. Revert by cleaning `app` outputs. If the hypothesis fails, stop and return to root-cause investigation; do not layer another workaround.

- [ ] **Step 4: Document the chosen mechanism**

Prefer a public artifact transform if available. Otherwise document why the fallback is required: AGP 9.3.1 has no public merged-resource transform, so a narrowly ordered post-merge/pre-link recompilation is the smallest build-only fix.

### Task 2: Implement the helper test-first

**Files:**
- Create: `tools/tests/test_patch_androidprv_merged_resources.py`
- Create: `tools/patch_androidprv_merged_resources.py`

**Interfaces:**
- CLI consumes `--merged-dir`, `--compiled-dir`, and `--aapt2`.
- CLI produces a summary `scanned=<n> patched=<n> compiled=<n> unresolved=0`; exits non-zero for missing inputs, zero patch candidates, duplicate namespace declarations, compile failures, or missing expected flat outputs.

- [ ] **Step 1: Write failing fixture tests**

Cover: root namespace injection; existing declaration remains single; only files containing `androidprv:` are selected; `values[-qualifier]/name.xml` maps to AAPT2's generated flat filename; missing directories fail; zero candidates fail; second run is deterministic/idempotent.

- [ ] **Step 2: Run the new test module and confirm RED**

Run `python3 -m unittest tools.tests.test_patch_androidprv_merged_resources -v`. Expected: failure because the production module/API does not yet exist.

- [ ] **Step 3: Implement the minimal helper**

Patch a temporary copy, never the source or AGP merged XML. Invoke AAPT2 once per selected values file with the flags proven by Task 1. Atomically replace only the matching files under `compiled-dir`.

- [ ] **Step 4: Run GREEN and full tests**

Run the new module, then `python3 -m unittest discover -s tools/tests -p 'test_*.py'`. Expected: all pass, total greater than 116.

### Task 3: Wire the build and verify from a clean app resource state

**Files:**
- Modify: `app/build.gradle.kts`
- Modify: `docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md`
- Modify: `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md`

**Interfaces:**
- Consumes: helper CLI and `androidComponents.sdkComponents.aapt2`.
- Produces: per-variant ordering `merge<Variant>Resources → patch<Variant>AndroidPrvMergedResources → process<Variant>Resources`.

- [ ] **Step 1: Add minimal Gradle wiring**

Register one task per app variant, pass the variant-specific merged XML and compiled-flat directories plus the public AAPT2 provider, and enforce dependency ordering. Do not claim ownership of AGP's output directory; the patch task is intentionally a narrow intermediate repair.

- [ ] **Step 2: Verify from clean app outputs**

Run `./gradlew :app:clean :app:processDebugResources --console=plain 2>&1 | tee /tmp/task012.log`. Expected: `BUILD SUCCESSFUL`, helper summary with `unresolved=0`, and `grep -c androidprv /tmp/task012.log` equals 0.

- [ ] **Step 3: Run APK diagnostics**

Run `./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/task012-app.log`. If successful, record APK path, byte size, and SHA-256. If a new layer fails, record its task and first errors and stop; do not widen scope.

- [ ] **Step 4: Commit**

Commit only the File Map paths with an English message; never push.
