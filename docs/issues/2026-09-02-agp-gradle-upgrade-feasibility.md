# Task 088 — AGP / Gradle / Kotlin upgrade feasibility research

- Date: 2026-09-02
- Type: read-only primary-source research
- Status: planned
- Report owner: `docs/architecture/2026-09-02-agp-gradle-upgrade-feasibility.md`

## Background

The project currently uses AGP 9.3.1, Gradle 9.5.0, built-in Kotlin 2.2.10, and JDK 25. Android Studio suggests that build-tool upgrades may be available. The active application build is blocked at `:app:desugarDebugFileDependencies` by isolation/serialization of the custom AGP ASM visitor factory. The user asked us to verify, rather than assume, whether a supported newer toolchain exists and whether its official changes could address this failure.

## Question

Using first-party sources only, determine:

1. the latest stable and relevant preview versions of AGP, Gradle, Android Studio, Kotlin, and KSP available on the research date;
2. the official compatibility matrix among those versions, including JDK requirements and AGP built-in Kotlin constraints;
3. whether any official release note, fixed issue, source diff, or compatibility note after AGP 9.3.1 mentions ASM instrumentation, `AsmClassVisitorFactory`, dependency transforms, worker isolation, configuration-cache serialization, `DefaultProperty`, or `InstrumentationContext.apiVersion`;
4. whether a toolchain upgrade is a credible targeted fix, a useful later maintenance upgrade, or unsupported speculation;
5. the smallest safe upgrade experiment, if evidence justifies one, without performing it.

## Source policy

Prefer Android Developers/Android Studio/AGP release notes and API docs, Google Maven metadata, Gradle release and compatibility documentation, Kotlin/KSP official documentation and repositories, Android Gradle Plugin source on `android.googlesource.com`, and first-party issue trackers. Record exact URLs, versions, access date, and source revisions where available. Search via the official `android docs` command where useful. Third-party blogs, forum posts, AI answers, and uncited snippets are not decision evidence.

## Boundaries

This task is research-only. It must not edit build files, versions, lockfiles, source, current issues/state/log, or existing reports; run Gradle; install/update tools; start Android Studio or a device; mutate caches/SDK/AOSP; commit; or push. It writes only its one report in an isolated worktree. Research does not authorize an upgrade.

## Required report shape

Separate verified facts, inferred relevance to the current stacktrace, recommendation, proposed bounded experiment, risks/rollback, and unresolved questions. Explicitly state whether an upgrade is supported by direct evidence or only worth testing after the current minimal diagnosis.

## Verification

- Report exists at the owner path and contains stable citations for every consequential version/compatibility/fix claim.
- `git diff --check` passes.
- Diff contains exactly the report path.
- No Gradle command, package installation, toolchain mutation, commit, or push occurred.
