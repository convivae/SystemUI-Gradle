# Task 089 — Official AGP instrumentation isolation research

## Goal

Produce a cited first-party report identifying the supported AGP/Gradle contract and best pre-D8/R8 seam for the current `AsmClassVisitorFactory` isolation failure. Do not implement or run a build.

## Base and ownership

- Base: Chief-provided pushed `main` commit.
- Topology: isolated worktree and dedicated Herdr tab.
- Authority: report-only; Worker may edit only its report and must not commit or push.
- Reports to: Chief.

## Read first

1. `AGENTS.md` completely, then wait.
2. `docs/orchestration/CHARTER.md` completely, then wait.
3. `/home/conv/.pi/agent/skills/research/SKILL.md`
4. `/home/conv/.pi/agent/skills/android-cli/SKILL.md`
5. `docs/issues/2026-09-02-agp-instrumentation-isolation-research.md`
6. `docs/orchestration/tasks/087-c5-custom-file-params-control.md`
7. `docs/issues/2026-09-02-c5-serialization-field-path.md`
8. `docs/issues/2026-09-02-c5-none-all-control-corrected.md`
9. Current `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/**` as read-only evidence.

Print a `CONTRACT:` before research.

## Allowed path

- `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md`

## Network and source authority

Public network access is authorized only for first-party Android/Google and Gradle documentation, source, tests, release notes, artifacts, and issue trackers. Use `android docs search/fetch` where applicable. Stable direct URLs plus AGP/Gradle version or source revision are mandatory. Third-party sources may only be labeled as non-authoritative leads.

## Required questions

1. Exact official contract for `AsmClassVisitorFactory`, `InstrumentationParameters`, `transformClassesWith`, `InstrumentationScope.ALL`, and dependency instrumentation.
2. Whether factory Java serialization in `AsmClassesTransform.Parameters` is intended, a known bug/regression, or an unsupported shape.
3. Restrictions and supported examples for `RegularFileProperty` parameters, `fileValue(File)`, providers, and file-backed visitor configuration.
4. First-party examples/tests combining `ALL` with file-backed parameters.
5. Supported alternative pre-D8/R8 seams and whether each covers project classes, runtime JARs, AAR `classes.jar`, and excludes compileOnly `framework.jar`.
6. A result-conditioned decision table for Task 087 outcomes and one smallest recommended next step.

## Forbidden

- Any file except the report.
- Gradle wrapper/tasks/status, tests/builds, Android Studio, device/emulator/ADB, Soong/Ninja.
- Production/buildSrc/rules/allowlist/source/SDK/AOSP/cache edits.
- Stubs, source import rewrite, packaged platform classes, `dontwarn`, class deletion, post-R8/DEX rewrite, weakened mappings or allowlist.
- Commit or push.

## Acceptance

- One report clearly separates API guarantees, source-derived facts, inference, options, recommendation, and unknowns.
- Every consequential claim has a first-party citation and exact version/revision/date.
- Coverage table explicitly addresses project classes, runtime JARs, AAR classes, and compileOnly exclusion.
- Task 087-conditioned recommendation does not claim research as build/runtime proof.
- `git diff --check` passes and `git status --short` lists exactly the allowed report.

## Completion report

```text
STATUS: PASS|BLOCKED
REPORT_PATH=
SUPPORTED_CONTRACT=
KNOWN_BUG_OR_FIX=
RECOMMENDED_SEAM=
TASK087_DECISION_TABLE=COMPLETE|INCOMPLETE
SOURCES=
DIFF_PATHS=
FORBIDDEN_ACTIONS=NONE|...
HANDOFF:
- done:
- verified:
- remaining:
```
