# Task 009: Fix WM-Shell `android:featureFlag` resource linking via AGP `additionalParameters`

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: unblock `:app:processDebugResources` by supplying the missing AAPT feature flag through AGP's official DSL, per the user-approved Option (b) in `docs/architecture/2026-08-13-aapt-feature-flags-options.md` (read the Option (b) section first — it is the spec).

Authority: redline-gated — `app/build.gradle.kts` AAPT configuration change is **pre-approved by the user on 2026-08-13** for exactly this edit. Commit but never push.

Allowed Paths: `app/build.gradle.kts`, `docs/issues/`, `docs/orchestration/tasks/009-*.md`.

Forbidden Paths: everything else — no manifest edits, no AAR repackaging, no SDK changes, no version catalog, no other module build scripts.

Steps:

- [x] 1. Read the Option (b) section of `docs/architecture/2026-08-13-aapt-feature-flags-options.md` (lines ~271 onward) for the exact DSL and the rationale.
- [x] 2. Apply to `app/build.gradle.kts`, inside the existing `android { }` block, with a short comment referencing the research doc:

```kotlin
androidResources {
    // WM-Shell AAR manifest uses android:featureFlag (AOSP original); supply the
    // flag to aapt2 link. See docs/architecture/2026-08-13-aapt-feature-flags-options.md
    additionalParameters(
        "--feature-flags",
        "com.android.wm.shell.enable_retrievable_bubbles=true"
    )
}
```

- [x] 3. Acceptance run:

```bash
./gradlew :app:processDebugResources --console=plain 2>&1 | tee /tmp/task009.log >/dev/null
grep -E 'BUILD (SUCCESSFUL|FAILED)' /tmp/task009.log | tail -1
grep -c 'feature_flags\|enable_retrievable_bubbles' /tmp/task009.log || echo '0 (featureFlag errors gone)'
```

Expected: BUILD SUCCESSFUL and `0` feature-flag errors.

- [x] 4. Diagnostics (not acceptance): run `./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/task009-app.log >/dev/null` and truthfully record the outcome — if it fails, capture the failing task and first error lines for the architect. Do NOT attempt to fix anything beyond this brief's scope.

- [x] 5. Append a dated note to `docs/issues/2026-08-13-aapt-feature-flags-research.md`: the applied diff, acceptance output, and the assembleDebug diagnostics result.

- [x] 6. Worker commit (never push):

```bash
git add app/build.gradle.kts docs/issues/2026-08-13-aapt-feature-flags-research.md docs/orchestration/tasks/009-feature-flags-additional-parameters.md
git commit -m "build(app): pass WM-Shell feature flag to aapt2 link via additionalParameters"
```

Acceptance (architect re-runs): Step 3 commands on the merged tree; `git show --stat HEAD` limited to Allowed Paths.
