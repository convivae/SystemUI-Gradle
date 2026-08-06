# Soong APK Research, Progress Policy, and Checkpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain and document how AOSP Soong builds `SystemUI.apk` from an app module with no own sources, replace error-count/compile-gate rules with a forward-progress principle, then preserve and push the existing work in two focused checkpoint commits.

**Architecture:** Keep `SystemUIApplication` and `SystemUIService` in `:SystemUI-core`, while `:app` remains the APK-producing shell. Document the Soong-to-Gradle mapping from primary source code. Separate the existing implementation WIP from the policy/research documentation in git history.

**Tech Stack:** AOSP Soong (`android_app`, `android_library`), Android Gradle Plugin, Gradle Kotlin DSL, Git, Python 3 utilities.

## Global Constraints

- Only AOSP `frameworks/base/packages/SystemUI/` code may be source-copied.
- Non-SystemUI code must use jar/AAR or the custom SDK.
- SystemUI src/AIDL/res must remain complete and exact relative to AOSP.
- Resource files may only come from AOSP source, AAR, or official upstream dependencies.
- Build error counts are diagnostic data, not commit gates.
- Compiling every modification or commit is not mandatory; run builds only when they provide useful evidence.
- Never claim an APK builds until `:app:assembleDebug` exits successfully.
- Preserve the current WIP, including documented non-building intermediate state.

---

### Task 1: Record the Soong-to-Gradle APK architecture

**Files:**
- Create: `docs/architecture/2026-08-06-soong-android-app-vs-gradle-app.md`
- Modify: `docs/adr/0003-app-module-aligns-aosp-bp.md`

**Interfaces:**
- Consumes: AOSP `frameworks/base/packages/SystemUI/Android.bp`, `build/soong/java/app.go`, `build/soong/java/base.go`; Gradle `app/build.gradle.kts` and runtime dependency report.
- Produces: Authoritative explanation of the APK packaging seam and Gradle equivalence.

- [ ] **Step 1: Document the AOSP module graph**

Record `SystemUI-res → SystemUI-core → android_app SystemUI`, including manifests, sources, resources, and static libraries.

- [ ] **Step 2: Document Soong implementation evidence**

Cite `AndroidApp` embedding `Library`, `hasCode()` accepting static libraries, static implementation jar collection, AAPT resource processing, dexing, signing, and install path.

- [ ] **Step 3: Document the Gradle equivalent**

Record `com.android.application` plus `implementation(project(":SystemUI-core"))`, AGP resource/manifest merging, D8/R8 packaging, and the difference between APK construction and system-image installation.

- [ ] **Step 4: Record current evidence and limitations**

Record that `debugRuntimeClasspath` includes `:SystemUI-core` and that `assembleDebug`/`packageDebug` tasks exist. State that the current AAR transform blocker prevents claiming a successful APK build.

### Task 2: Replace error-count and mandatory-compile rules

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/PLAN.md`
- Modify: `docs/GRADLE_MIGRATION_LOG.md` only if it describes error reduction as a mandatory gate.

**Interfaces:**
- Consumes: User directive from 2026-08-06.
- Produces: One consistent project-wide forward-progress policy.

- [ ] **Step 1: Remove all mandatory error-decrease thresholds**

Delete rules requiring every commit to reduce errors, rollback above +50, or user approval/escalation above +200.

- [ ] **Step 2: Add the forward-progress principle**

Define progress by structural correctness, AOSP alignment, dependency provenance, resource exactness, and movement toward a buildable APK. Permit temporary error increases/decreases.

- [ ] **Step 3: Remove mandatory compile-per-change wording**

State that compilation is evidence used when relevant, not a ritual required for every edit or commit. Require honest recording of whether a build was run and its actual result.

- [ ] **Step 4: Make current priorities explicit**

Prioritize source-vs-jar/AAR boundaries, complete/exact SystemUI source/AIDL/resources, removal of illegal external source copies, and removal of SystemUI prebuilt duplicates.

### Task 3: Verify the existing WIP checkpoint without requiring compilation

**Files:**
- Inspect all tracked and untracked worktree changes.

**Interfaces:**
- Consumes: Existing source deletions, Gradle dependency changes, jar additions, Python utilities, and AAR rewrite WIP.
- Produces: A truthful checkpoint description and evidence that files are structurally readable.

- [ ] **Step 1: Review staged and unstaged diffs**

Use `git diff --cached`, `git diff`, and `git status --short`; verify no credentials or unrelated generated outputs are included.

- [ ] **Step 2: Verify Python syntax**

Run:

```bash
python3 -m py_compile \
  tools/gen_aar_maven.py \
  tools/rebuild_settingslib_aar.py \
  tools/check_source_alignment.py \
  tools/fix_r_imports_to_res.py
```

- [ ] **Step 3: Verify jar integrity**

Run `unzip -t` on `libs/PlatformMotionTestingComposeValues.jar` and `libs/contextualeducationlib.jar`.

- [ ] **Step 4: Verify Gradle APK wiring without compiling**

Run:

```bash
./gradlew :app:dependencies --configuration debugRuntimeClasspath --console=plain
./gradlew :app:tasks --all --console=plain
```

Confirm `project :SystemUI-core`, `assembleDebug`, and `packageDebug` appear.

### Task 4: Create and push two checkpoint commits

**Files:**
- Commit 1: Existing implementation WIP and its pre-existing issue/ADR records.
- Commit 2: 2026-08-06 policy, research, and documentation updates.

**Interfaces:**
- Consumes: Verified worktree from Tasks 1–3.
- Produces: Two commits on `main`, pushed to `origin/main`.

- [ ] **Step 1: Stage implementation checkpoint only**

Include source deletions, entry-class deduplication, dependency jar additions, Gradle changes, Python tooling WIP, `docs/issues/2026-07-31-gen_aar_maven-rewrite.md`, and the existing ADR 0003 correction. Exclude the new 2026-08-06 policy/research docs.

- [ ] **Step 2: Commit implementation checkpoint**

Use a message that explicitly describes it as a structural/dependency WIP checkpoint and does not claim the build passes.

- [ ] **Step 3: Stage policy and research documentation**

Stage `AGENTS.md`, handoff/state/plan updates, ADR 0001, the July architecture correction notices, the new reference-project rationale, the Soong/Gradle APK research, and this plan.

- [ ] **Step 4: Run documentation verification**

Run `git diff --cached --check` and scan for removed threshold wording.

- [ ] **Step 5: Commit documentation**

Use a message describing the forward-progress policy and Soong/Gradle APK documentation.

- [ ] **Step 6: Push and verify remote state**

Run:

```bash
git push origin main
git status -sb
git log --oneline -4
```

Report the exact commit hashes and whether the worktree remains dirty.
