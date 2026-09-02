# Task 089 — Official AGP instrumentation isolation research

- Date: 2026-09-02
- Type: read-only primary-source research
- Status: planned
- Report owner: `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md`

## Background

The application registers an app-only `InstrumentationScope.ALL` `AsmClassVisitorFactory` to perform four exact, reference-only class-name mappings before D8/R8. Focused tests pass, but the real `:app:desugarDebugFileDependencies` transform fails while Gradle isolates `AsmClassesTransform.Parameters`. JDK extended serialization evidence identifies `InstrumentationContext_Decorated.__apiVersion__` (`DefaultProperty`) through the decorated factory's `__instrumentationContext__`. A field-free `InstrumentationParameters.None` no-op `ALL` control passes. Task 087 is separately testing the same no-op behavior with the production two `RegularFileProperty` parameters.

## Question

Using first-party documentation, source, release notes, tests, and issue trackers, determine the supported contract and likely correct seam for this use case:

1. What serialization/isolation contract applies to `AsmClassVisitorFactory`, `InstrumentationParameters`, `transformClassesWith`, `InstrumentationScope.ALL`, and AGP dependency instrumentation?
2. Are factory instances expected to be Java-serializable inside AGP dependency artifact transforms, or does the observed raw-factory serialization indicate an AGP bug/regression or an unsupported registration shape?
3. What restrictions apply to `RegularFileProperty` parameters and configuration values? Are direct `fileValue(File)` assignments supported, or should providers/artifacts/value parameters be used differently?
4. Are there official examples/tests for custom ASM visitors with `InstrumentationScope.ALL` and file-backed parameters?
5. Which supported alternative pre-D8/R8 seams can cover app project classes plus runtime JAR/AAR program inputs without touching compileOnly platform classes?
6. Which single smallest production change or next diagnostic follows from the official evidence and Task 087's possible result?

## Source policy

Prefer AGP API docs, Android Developers guides, Android Gradle Plugin source/tests on `android.googlesource.com`, Gradle isolation/configuration-cache/serialization documentation and source, and first-party Google/Gradle issue trackers. Record direct stable URLs, AGP/Gradle versions, source revisions, and access date. Use `android docs search/fetch` where useful. Public third-party discussions may be listed only as non-authoritative leads and must not support the recommendation.

## Boundaries

Research-only. It must not modify production files, run Gradle, alter the active Task 087 experiment, install/update tools, operate devices, change SDK/AOSP/caches, commit, or push. It writes only one report in an isolated worktree. It must not recommend forbidden shortcuts such as stubs, source import rewrites, packaged platform classes, `dontwarn`, raw post-R8/DEX rewriting, class deletion, or weakening the four-rule/166-class contract.

## Required report shape

Separate exact API/source facts, documented examples, interpretation of the observed field path, supported seam options with coverage and isolation tradeoffs, a decision table conditioned on Task 087 (`CUSTOM_PARAMS_FAILURE|PASS|OTHER_FAILURE`), one recommended next step, and unresolved questions. Clearly distinguish official guarantees from source-derived inference.

## Verification

- Report exists with stable first-party citations for every consequential claim.
- `git diff --check` passes.
- Diff contains exactly the report path.
- No Gradle/build/device/toolchain mutation, commit, or push occurred.
