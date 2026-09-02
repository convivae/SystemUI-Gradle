# Task 090 — Make the custom file-parameter transform execution observable

**Status:** Closed `PASS` on 2026-09-02; temporary diff fully restored, no production change.

## Goal

Run one fully reversible application-only `InstrumentationScope.ALL` micro-control that retains the production `AconfigReferenceRewriteParameters` shape and field-free no-op behavior, changes one declared file input to a unique scratch probe, and emits a sentinel only from actual factory execution. Conclusively classify the run as `CUSTOM_PARAMS_FAILURE`, `PASS`, `INCONCLUSIVE`, or `OTHER_FAILURE`.

## Why now

Task 087 exited 0 but its target was `UP-TO-DATE`; it therefore did not prove artifact-transform execution. Tasks 088/089 found no targeted-upgrade evidence and recommend changing an annotated transform input plus recording execution before choosing a production seam.

## Sources of truth

- `AGENTS.md`
- `docs/orchestration/CHARTER.md`
- `docs/issues/2026-09-02-c5-observable-file-params-control.md`
- `docs/issues/2026-09-02-c5-custom-file-params-control.md`
- `docs/issues/2026-09-02-c5-serialization-field-path.md`
- `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md`
- Current `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/{AconfigReferenceRewritePlugin,AconfigReferenceRewriteFactory}.kt`

## Base and dependencies

- Base: exact pushed `main` selected by Chief after this brief is committed.
- Blocked by: Tasks 087–089 closure and a clean/no-build-process shared checkout.
- Reports to: Chief.

## Authority

Temporary diagnostic only; no commit and no production fix. The Worker may create the exact temporary diff and scratch input, run the one exact Gradle command only after Chief inspects the patch, restore exactly, and report evidence.

## Scope

### Allowed paths (temporary; mandatory restoration)

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpFileParamsFactory.kt`
- `/tmp/task090-c5-observable-file-params-control/**`

### Forbidden

All other tracked/untracked paths; production factory/parameter interface; frozen rules/allowlist; app wiring; AOSP/SDK/`libs/**`; source/resources/manifests/ProGuard; network/package/tool/version changes; full assemble; Release/R8; checker; emulator/ADB; Soong/Ninja; a second Gradle-wrapper invocation; commit/push; direct `python`/`python3`.

## Required startup

1. Read all of `AGENTS.md`; wait for the call to return.
2. In a separate call, read all of `docs/orchestration/CHARTER.md`; wait for the call to return.
3. Read worker-contract, this brief, the Task 090/087/084 issues, Task 089 report, current plugin/factory, and the complete Task 087 log.
4. Print `CONTRACT:`. Do not create scratch, edit, or run commands before Chief accepts it.

## Work

1. Preflight using only `git`, `ps`, `pgrep`, and read-only file/hash tools. Require clean tracked/untracked state and no Gradle/Kotlin/Soong/Ninja process. **Do not invoke the Gradle wrapper in preflight.**
2. Create the scratch root. Record base, original plugin SHA-256, production rules/allowlist SHA-256, and prove the temporary factory absent.
3. Create `probe-rules.txt` by copying the production four-rule file byte-for-byte and appending exactly `# task090-observable-input\n`. Record both hashes and prove only the scratch probe differs; do not edit the production file.
4. Create a field-free `NoOpFileParamsFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`:
   - `isInstrumentable` always returns `false`;
   - immediately before returning, print exactly `TASK090_FACTORY_EXECUTED=android.os.CustomFeatureFlags` only when `classData.className == "android.os.CustomFeatureFlags"`;
   - `createClassVisitor` returns `nextClassVisitor` unchanged;
   - no parameter reads and no instance/static cache fields.
5. Switch only the temporary registration to this factory and set `rulesFile` to `/tmp/task090-c5-observable-file-params-control/probe-rules.txt`; retain the production allowlist path/configuration, application-only gate, `InstrumentationScope.ALL`, and `FramesComputationMode.COPY_FRAMES`. Do not edit the parameter interface.
6. Save the original plugin, temporary factory, probe, and `git diff --binary` under scratch. Run `git diff --check`; report exact changed paths and hashes. Stop for Chief inspection.
7. After Chief approval, run once and only once:
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task090-c5-observable-file-params-control/desugar-observable-file-params.log
   ```
8. Record pipeline exit, target outcome, log line count/SHA-256, exact sentinel count, all `AsmClassesTransform` execution/cache lines, deepest cause, and literal field path.
9. Classify:
   - `CUSTOM_PARAMS_FAILURE`: required Task 084-style literal path through the temporary factory;
   - `PASS`: exit 0 **and sentinel count ≥1**;
   - `INCONCLUSIVE`: exit 0 and sentinel count 0;
   - `OTHER_FAILURE`: every other failure.
10. Restore plugin byte-for-byte, delete temporary factory, terminate Gradle/Kotlin daemons from this run, and prove clean worktree/no remaining build process. Preserve scratch evidence.

## Acceptance

- Pre-run repository diff is exactly the two Allowed tracked paths; production factory/interface/rules/allowlist/app wiring are unchanged.
- Probe is scratch-only and demonstrably changes an existing annotated `@InputFile` value without being read by the no-op factory.
- Temporary factory is field-free and class-byte no-op; sentinel can only arise from `isInstrumentable` invocation for the frozen runtime-JAR class.
- Exactly one Gradle command runs.
- `PASS` is forbidden without the sentinel, regardless of task-level `UP-TO-DATE` or `BUILD SUCCESSFUL`.
- Final worktree is clean, production hashes restored, no residual build process, and no stronger Debug/Release/runtime claim is made.

## Build/run profile

- Revision: pushed Task 090 planning base.
- Mode: focused diagnostic.
- Writable roots: Gradle's existing build/cache outputs plus the exact `/tmp/task090-c5-observable-file-params-control/**` scratch root and two temporary tracked paths.
- Shared state: exclusive shared checkout and Gradle/Kotlin daemons; no concurrent Gradle/Soong.
- Network: offline.
- Ready signal: Chief accepts exact temporary diff/hashes.
- Pass signal: command exit 0 and sentinel count ≥1.
- Cleanup: exact source restoration, temporary factory deletion, daemon termination, clean status.
- Claim scope: only whether this custom file-parameter no-op control reached factory execution or reproduced isolation; no APK/build/runtime proof.

## Delivery

- Commit policy: none.
- Push policy: forbidden; Chief only.
- Completion report:
  ```text
  STATUS: PASS|FAIL
  CONTROL_PATCH_PATHS=
  LOOP_EXIT=
  TARGET_OUTCOME=
  CONTROL_RESULT=CUSTOM_PARAMS_FAILURE|PASS|INCONCLUSIVE|OTHER_FAILURE
  SENTINEL_COUNT=
  ASM_TRANSFORM_EVIDENCE=
  DEEPEST_CAUSE=
  FIELD_PATH=
  PRODUCTION_FACTORY_AND_INPUTS_UNCHANGED=YES|NO
  TRACKED_WORKTREE=
  FORBIDDEN_ACTIONS=NONE|...
  NEXT=Chief defines the result-conditioned next task
  ```
- End with a concise `HANDOFF:` block.

## Closure

The sole authorized Gradle wrapper invocation exited `0`. The 398-line log at `/tmp/task090-c5-observable-file-params-control/desugar-observable-file-params.log` has SHA-256 `762d53cb40bd3f3d81f79444444daa8aeee7c47efbaf6b9ef59fb1ff8da4352f`; line 386 contains the exact factory sentinel once. The log contains 45 `Caching disabled for AsmClassesTransform:` lines, zero `NotSerializableException`/`__instrumentationContext__`/`__apiVersion__`, and ends with `BUILD SUCCESSFUL in 8s`. The direct target remained task-level `UP-TO-DATE`, but the sentinel independently proves factory execution, so the frozen result matrix requires `PASS`.

The plugin was restored byte-for-byte, the temporary factory was deleted, production factory/rules/allowlist hashes remained unchanged, the worktree was clean, and no build process remained. One cleanup-process deviation was recorded: the worker initially used non-mandated patterns; Chief then required the exact three bracket-pattern commands and all returned exit 1 (no matching process). This result proves only the custom file-parameter/no-op control rung; it does not prove production behavior, an APK, R8, or runtime.
