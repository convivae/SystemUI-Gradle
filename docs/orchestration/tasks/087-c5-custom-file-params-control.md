# Task 087 — Isolate the custom file-parameter shape with a no-op `ALL` factory

## Goal

Use one temporary, fully reversible `InstrumentationScope.ALL` control that keeps the production `AconfigReferenceRewriteParameters` and its two configured `RegularFileProperty` inputs while replacing only production visitor behavior with a field-free no-op factory. Determine whether that custom parameter shape is sufficient to restore the Task 084 serialization failure.

## Authority

This is a serialized, temporary buildSrc-diff, one-Gradle-command diagnostic worker:

- May: read the repository, Task 084–087 evidence, and local AGP/Gradle cache; create only the designated scratch root; temporarily edit the two Allowed Paths; run the one exact Gradle command after Chief approval; restore exactly and terminate daemons from this run.
- May NOT: modify any other tracked path, production factory/parameter interface, rules/allowlist, `:app` wiring, AOSP/SDK/`libs/**`, ProGuard, or SystemUI source; run another Gradle task, full assemble, Release/R8, checker, device, Soong/Ninja; commit/push; invoke direct `python`/`python3`.
- Reports To: Chief.

## Allowed Paths (temporary and mandatory restoration)

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpFileParamsFactory.kt`
- `/tmp/task087-c5-custom-file-params-control/**`

## Required startup

1. Read all of `AGENTS.md`; wait for the call to return.
2. In a separate call, read all of `docs/orchestration/CHARTER.md`; wait for the call to return.
3. Read worker-contract, this brief, Task 087 issue, Task 086 issue, Task 084 issue, and the Task 086 scratch log/temporary factory evidence.
4. Print `CONTRACT:`. Do not create scratch, edit, or run commands before Chief accepts it.

## Procedure

1. Create scratch. Record branch/HEAD; require a clean tracked/untracked worktree and no Gradle/Kotlin/Soong/Ninja process using only `ps`/`pgrep`-style checks. **Do not invoke the Gradle wrapper in preflight.** Stop if dirty/busy.
2. Record original plugin SHA-256 and prove the temporary factory is absent. Create:
   - `internal abstract class NoOpFileParamsFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`;
   - no fields;
   - `isInstrumentable(classData: ClassData): Boolean = false`;
   - `createClassVisitor(classContext: ClassContext, nextClassVisitor: ClassVisitor): ClassVisitor = nextClassVisitor`.
3. Only switch `AconfigInstrumentationRegistration` to `NoOpFileParamsFactory`. Registration must remain application-only and exactly retain the production scope and parameter configuration:
   ```kotlin
   instrumentation.transformClassesWith(
       NoOpFileParamsFactory::class.java,
       InstrumentationScope.ALL,
   ) { parameters ->
       parameters.rulesFile.fileValue(rulesFile)
       parameters.allowlistFile.fileValue(allowlistFile)
   }
   ```
   Keep `FramesComputationMode.COPY_FRAMES`. Do not change `AconfigReferenceRewriteParameters` or read the files in the no-op factory.
4. Save original plugin, temporary factory, and `git diff --binary` patch under scratch. Run `git diff --check`; report exact changed paths and SHA-256 values. Stop for Chief inspection.
5. After Chief approval, run once and only once:
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task087-c5-custom-file-params-control/desugar-custom-file-params.log
   ```
6. Record the actual pipeline exit code, line count, log SHA-256, deepest cause, and literal field path. Do not run a second Gradle task/control.
7. Regardless of result, restore the plugin byte-for-byte, delete the temporary factory, terminate Gradle/Kotlin daemons from this run, and prove clean worktree/no remaining build process.
8. Print the report and a concise `HANDOFF:`. Do not edit docs or commit/push.

## Acceptance

- Pre-run diff has exactly the two Allowed Paths; production factory/interface, rules, allowlist, app wiring, and all other paths are unchanged.
- Temporary factory is field-free, uses exactly `AconfigReferenceRewriteParameters`, and is behaviorally no-op.
- Production file-property configuration, `ALL`, application-only gate, and `COPY_FRAMES` remain exact.
- The only Gradle command runs once, with actual exit and exact result recorded.
- `CONTROL_RESULT=CUSTOM_PARAMS_FAILURE|PASS|OTHER_FAILURE`.
- `CUSTOM_PARAMS_FAILURE` requires both `InstrumentationContext_Decorated.__apiVersion__` and `NoOpFileParamsFactory_Decorated.__instrumentationContext__` in the literal path.
- Final tracked/untracked worktree is clean; no second task, full build, Release/device/Soong operation.

## Execution result

Executed once on 2026-09-02. The command exited 0 and printed `BUILD SUCCESSFUL in 17s`, but `:app:desugarDebugFileDependencies` was `UP-TO-DATE`. No evidence established that `AsmClassesTransform` or the temporary factory executed. Chief classification: **`INCONCLUSIVE`**, superseding the original three-way result enum for this run. The two temporary paths were restored/removed exactly, the worktree was clean, and no production/build/runtime claim was made. Successor: Task 090.

## Report format

```text
STATUS: PASS|FAIL
CONTROL_PATCH_PATHS=
LOOP_EXIT=
CONTROL_RESULT=CUSTOM_PARAMS_FAILURE|PASS|OTHER_FAILURE
DEEPEST_CAUSE=
FIELD_PATH=
PRODUCTION_FACTORY_AND_INPUTS_UNCHANGED=YES|NO
TRACKED_WORKTREE=
FORBIDDEN_ACTIONS=NONE|...
NEXT=Chief chooses production seam or next minimal isolation
```

End with a concise `HANDOFF:` block.
