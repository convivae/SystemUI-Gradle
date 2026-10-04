# Task 088 — Official toolchain upgrade feasibility

## Goal

Produce a cited, first-party-only report deciding whether an AGP/Gradle/Kotlin upgrade is available, compatible, and plausibly relevant to the current `AsmClassVisitorFactory` serialization failure. Do not upgrade anything.

## Base and ownership

- Base: Chief-provided pushed `main` commit.
- Topology: isolated worktree and dedicated Herdr tab.
- Authority: report-only; Worker may edit only the report path and must not commit or push.
- Reports to: Chief.

## Read first

1. `AGENTS.md` completely, then wait.
2. `docs/orchestration/CHARTER.md` completely, then wait.
3. `/home/conv/.pi/agent/skills/research/SKILL.md`
4. `/home/conv/.pi/agent/skills/android-cli/SKILL.md`
5. `docs/issues/2026-09-02-agp-gradle-upgrade-feasibility.md`
6. `docs/CURRENT_STATE.md`
7. `docs/issues/2026-09-02-c5-serialization-field-path.md`
8. `docs/issues/2026-09-02-c5-none-all-control-corrected.md`
9. `gradle/libs.versions.toml`, `gradle/wrapper/gradle-wrapper.properties`, `gradle.properties`, root and `buildSrc` build files as read-only evidence.

Print a `CONTRACT:` before research.

## Allowed path

- `docs/architecture/2026-09-02-agp-gradle-upgrade-feasibility.md`

## Network and source authority

Public network access is authorized only for first-party Android/Google, Gradle, JetBrains/Kotlin, and KSP/Google repositories, release artifacts, Maven metadata, and issue trackers. Use `android docs search/fetch` where applicable. Stable direct URLs and exact version/revision identities are mandatory. No credentials or private endpoints.

## Required questions

1. Latest stable and relevant preview AGP, Gradle, Android Studio, Kotlin, and KSP versions on the research date.
2. Official AGP↔Gradle↔JDK and built-in Kotlin compatibility constraints for current and candidate versions.
3. Official post-9.3.1 changes involving ASM instrumentation, `AsmClassVisitorFactory`, artifact/dependency transforms, worker isolation, configuration-cache serialization, `DefaultProperty`, or `InstrumentationContext.apiVersion`.
4. Evidence-based classification: targeted-fix candidate, maintenance-only candidate, or no justified upgrade.
5. If justified, one smallest reversible experiment with exact candidate versions, expected signal, rollback, and claim boundary. Do not execute it.

## Forbidden

- Any file except the one report.
- Gradle wrapper/tasks/status, tests, builds, Android Studio, device/emulator/ADB, Soong/Ninja.
- Package/tool/SDK installation or update, cache mutation, version edits, source/buildSrc edits.
- Third-party blogs/forums as decision evidence.
- Commit or push.

## Acceptance

- One complete report, separating verified facts, inference, recommendation, experiment, risks, and unresolved questions.
- Every consequential claim has a first-party citation and date/version.
- `git diff --check` passes and `git status --short` lists exactly the allowed report.
- Report explicitly says research alone authorizes no upgrade and proves no build/runtime result.

## Completion report

```text
STATUS: PASS|BLOCKED
REPORT_PATH=
LATEST_SUPPORTED_STACK=
POST_9_3_1_RELEVANT_FIX=YES|NO|UNPROVEN
RECOMMENDATION=
SOURCES=
DIFF_PATHS=
FORBIDDEN_ACTIONS=NONE|...
HANDOFF:
- done:
- verified:
- remaining:
```
