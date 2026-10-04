# Task 006: Pin androidx.media to 1.8.0

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: add an explicit `androidx.media:media:1.8.0` dependency so `MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE` resolves (the transitive 1.4.1 from `mediarouter:1.9.0-alpha01` lacks it). User pre-approved 1.8.0 (highest public stable per `maven-metadata.xml`).

Authority: redline-gated — toml version-matrix edit pre-approved by the user 2026-08-13 for `androidx.media = 1.8.0` only. Commit but never push.

Allowed Paths: `gradle/libs.versions.toml` (media version + library entry only), `SystemUI-core/build.gradle.kts`, `docs/issues/`, `docs/orchestration/tasks/006-*.md`.

Forbidden Paths: everything else; especially any other version in the toml, `SystemUI-*/src/**`, `AGENTS.md`.

Steps:

- [ ] 1. Confirm the current resolution evidence: `./gradlew :SystemUI-core:dependencyInsight --configuration debugCompileClasspath --dependency androidx.media:media 2>&1 | grep -E '1\.4\.1|1\.8\.0' | head -5` (expect 1.4.1 via mediarouter).
- [ ] 2. Add to `gradle/libs.versions.toml`: version `media = "1.8.0"` and library `androidx-media = { group = "androidx.media", name = "media", version.ref = "media" }`, following existing entry style. Nothing else in the file changes.
- [ ] 3. Add `implementation(libs.androidx.media)` to `SystemUI-core/build.gradle.kts` dependencies with a comment (`// explicit pin: mediarouter 1.9.0-alpha01 transitively resolves media 1.4.1 which lacks DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`).
- [ ] 4. Acceptance run:

```bash
./gradlew :SystemUI-core:dependencyInsight --configuration debugCompileClasspath --dependency androidx.media:media 2>&1 | grep -E 'androidx.media:media' | head -3
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task006.log >/dev/null; grep -c 'DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE' /tmp/task006.log || echo '0 (media group gone)'
```

Expected: insight shows 1.8.0 selected; `0` matches for the constant error. Record the overall javac error count as diagnostics.

- [ ] 5. Append the dated result note to the issue record; worker commit (never push):

```bash
git add gradle/libs.versions.toml SystemUI-core/build.gradle.kts docs/issues/2026-08-12-current-progress-standards-review.md
git commit -m "build(deps): pin androidx.media to 1.8.0 for completion-percentage extra"
```

Acceptance (architect re-runs): Step 4 both commands; toml diff touches only the media entries.
