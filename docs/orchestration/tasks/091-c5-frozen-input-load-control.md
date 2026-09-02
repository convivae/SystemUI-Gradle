# Task 091 — Make frozen input loading observable inside the custom-parameter factory

**Status:** Closed `PASS` on 2026-09-02; temporary diff fully restored. Experimental evidence passed, with a separately recorded cleanup-procedure deviation.

## Goal

Run one fully reversible application-only `InstrumentationScope.ALL` micro-control that keeps Task 090's proven production parameter shape and field-free class-byte no-op, but executes exactly one sentinel-scoped production `FrozenAconfigInputs.load(...)`. Conclusively classify whether managed file access/frozen-input validation can complete before restoring any production filter, cache, or visitor behavior.

## Why now

Task 090 is `PASS`: the exact custom parameter type and two file-property slots reached observable factory execution without the Task 084 serialization failure. The next smallest production-implementation layer is parameter access plus frozen-input loading. Filter admission, cache state, and the reference-only visitor must remain excluded so a result is attributable to this layer.

## Sources of truth

- `AGENTS.md`
- `docs/orchestration/CHARTER.md`
- `docs/issues/2026-09-02-c5-frozen-input-load-control.md`
- `docs/issues/2026-09-02-c5-observable-file-params-control.md`
- `docs/issues/2026-09-02-c5-serialization-field-path.md`
- `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/{AconfigReferenceRewritePlugin,AconfigReferenceRewriteFactory,FrozenAconfigInputs}.kt`
- Complete Task 090 log and saved patch under `/tmp/task090-c5-observable-file-params-control/`

## Base and dependencies

- Base: exact pushed `main` selected by Chief after this brief is committed.
- Blocked by: Task 090 closure recorded, clean shared checkout, and no Gradle/Kotlin/Soong/Ninja process.
- Reports to: Chief.

## Authority

Temporary diagnostic only; no commit and no production fix. The Worker may create the exact temporary diff and scratch input, run the one exact Gradle command only after Chief inspects the patch/hashes, restore exactly, and report evidence.

## Scope

### Allowed paths (temporary; mandatory restoration)

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/FrozenInputLoadControlFactory.kt`
- `/tmp/task091-c5-frozen-input-load-control/**`

### Forbidden

All other tracked/untracked paths; production factory/parameter interface/input loader/reference rewriter; frozen rules/allowlist; app wiring; AOSP/SDK/`libs/**`; source/resources/manifests/ProGuard; network/package/tool/version changes; full assemble; Release/R8; checker; emulator/ADB; Soong/Ninja; a second Gradle-wrapper invocation; commit/push; direct `python`/`python3`.

## Required startup

1. Read all of `AGENTS.md`; wait for the call to return and print `AGENTS_READ`.
2. In a separate call, read all of `docs/orchestration/CHARTER.md`; wait for the call to return and print `CHARTER_READ`.
3. Read worker-contract, this brief, the Task 091/090/084 issues, Task 089 report, current plugin/factory/input-loader, and the complete Task 090 log and saved patch.
4. Print `CONTRACT:`. Do not create scratch, edit, or run commands before Chief accepts it.

## Work

1. Preflight using only `git`, `ps`, `pgrep`, and read-only file/hash tools. Require the exact pushed base, clean tracked/untracked state, and no Gradle/Kotlin/Soong/Ninja process. **Do not invoke the Gradle wrapper in preflight.**
2. Create `/tmp/task091-c5-frozen-input-load-control/`. Record base and SHA-256 for the original plugin, production factory, input loader, rules, and allowlist; prove the temporary factory absent.
3. Copy production `gradle/aosp17-critical-aconfig-reference-rules.txt` byte-for-byte to `/tmp/task091-c5-frozen-input-load-control/task091-frozen-rules.txt`. Require SHA-256 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`, exact byte equality, and no appended probe text. Keep the production allowlist path unchanged.
4. Create `FrozenInputLoadControlFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>` with no instance/static cache:
   - for every class other than `android.os.CustomFeatureFlags`, return `false` immediately without reading parameters;
   - for exactly that sentinel, print `TASK091_LOAD_ENTERED=android.os.CustomFeatureFlags`, call `FrozenAconfigInputs.load(parameters.get().rulesFile.asFile.get(), parameters.get().allowlistFile.asFile.get())`, require mappings size 4 and allowlist size 166, print exactly `TASK091_INPUTS_LOADED=android.os.CustomFeatureFlags;mappings=4;allowlist=166`, then return `false`;
   - `createClassVisitor` returns `nextClassVisitor` unchanged;
   - do not call `AconfigReferenceRewriteFactory.isAllowlistedClass`, `AconfigReferenceRewriteFilter`, or `referenceOnlyVisitor`; do not add `cachedInputs` or any other cache/state field.
5. Switch only the temporary registration to this factory and set `rulesFile` to the scratch byte-exact copy. Retain the production allowlist assignment, application-only gate, `InstrumentationScope.ALL`, `FramesComputationMode.COPY_FRAMES`, and parameter interface.
6. Save the original plugin, temporary factory, scratch rule copy, and `git diff --binary` under the Task 091 scratch root. Run `git diff --check`; report exact changed paths and hashes. Stop for Chief inspection.
7. After Chief approval, run once and only once:
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task091-c5-frozen-input-load-control/desugar-frozen-input-load.log
   ```
8. Record pipeline exit, target outcome, log line count/SHA-256, exact entered/loaded sentinel counts, all `AsmClassesTransform` execution/cache lines, deepest cause, and literal field path.
9. Classify exactly as defined by the issue: `PASS`, `SAME_ISOLATION_FAILURE`, `INPUT_LOAD_FAILURE`, `INCONCLUSIVE`, or `OTHER_FAILURE`. A literal isolation failure with entered count 0 must not be attributed to the load body.
10. Restore the plugin byte-for-byte and delete the temporary factory. Run exactly these mandatory cleanup commands directly, preserving each exit code:
    ```bash
    pkill -9 -f 'Gradle[D]aemon'
    pkill -9 -f 'KotlinCompile[D]aemon'
    pkill -9 -f 'kotlin-daemon-[e]mbeddable'
    ```
    Do not substitute or add another cleanup pattern. Prove clean worktree, production hashes restored, and no Gradle/Kotlin/Soong/Ninja process. Preserve scratch evidence.

## Acceptance

- Pre-run repository diff is exactly the two Allowed tracked paths; production factory/interface/input loader/rules/allowlist/app wiring are unchanged.
- The scratch rules file is byte-identical to production but has the unique Task 091 path/name, changing a declared `@InputFile` value while satisfying the frozen SHA/count contract.
- The temporary factory has no cache/state field and changes no class bytes. It reads/validates both production inputs only for the Task 090-proven runtime-JAR sentinel and still returns `false`.
- Exactly one Gradle wrapper invocation runs. No `PASS` without exit 0 and loaded-sentinel count ≥1.
- Final worktree is clean, production hashes restored, temporary factory absent, and no residual build process remains.
- No claim beyond the managed file access + `FrozenAconfigInputs.load(...)` rung is made.

## Build/run profile

- Revision/artifact: pushed Task 091 planning base.
- Mode: focused diagnostic.
- Prerequisites: clean shared checkout; Task 090 evidence readable; no Gradle/Kotlin/Soong/Ninja process.
- Writable roots: Gradle's existing build/cache outputs, the exact Task 091 scratch root, and two temporary tracked paths.
- Shared state: exclusive shared checkout and Gradle/Kotlin daemons; no concurrent Gradle/Soong.
- Network: offline.
- Ready signal: Chief accepts exact temporary diff and scratch/input hashes.
- Pass signal: command exit 0 and exact loaded sentinel count ≥1.
- Failure log: `/tmp/task091-c5-frozen-input-load-control/desugar-frozen-input-load.log`.
- Cleanup: exact source restoration, temporary factory deletion, three mandated process commands, clean status.
- Claim scope: only whether one sentinel-scoped production frozen-input load completes in the proven custom-parameter transform; no cache/filter/visitor/APK/R8/runtime proof.

## Delivery

- Commit policy: none.
- Push policy: forbidden; Chief only.
- Completion report:
  ```text
  STATUS: PASS|FAIL
  CONTROL_PATCH_PATHS=
  LOOP_EXIT=
  TARGET_OUTCOME=
  CONTROL_RESULT=PASS|SAME_ISOLATION_FAILURE|INPUT_LOAD_FAILURE|INCONCLUSIVE|OTHER_FAILURE
  LOAD_ENTERED_COUNT=
  INPUTS_LOADED_COUNT=
  ASM_TRANSFORM_EVIDENCE=
  DEEPEST_CAUSE=
  FIELD_PATH=
  PRODUCTION_FACTORY_AND_INPUTS_UNCHANGED=YES|NO
  TRACKED_WORKTREE=
  CLEANUP_EXIT_CODES=
  FORBIDDEN_ACTIONS=NONE|...
  NEXT=Chief defines the result-conditioned next task
  ```
- End with a concise `HANDOFF:` block.

## Closure

The sole authorized Gradle wrapper invocation exited `0`. The 1463-line log at `/tmp/task091-c5-frozen-input-load-control/desugar-frozen-input-load.log` has SHA-256 `de243bd45b8b56995562cf17ba6a9ddb96451d91303d3202370b8e7fadbb8eb5`; `TASK091_LOAD_ENTERED=android.os.CustomFeatureFlags` appears once at line 1450 and `TASK091_INPUTS_LOADED=android.os.CustomFeatureFlags;mappings=4;allowlist=166` appears once at line 1453. The log contains 45 `Caching disabled for AsmClassesTransform:` records, zero known serialization-path markers, and ends with `BUILD SUCCESSFUL in 17s` / `5 actionable tasks: 2 executed, 3 up-to-date`. Target-level `UP-TO-DATE` does not negate the direct loaded sentinel, so the frozen matrix requires `PASS`.

The scratch rules were byte-identical to production. The temporary plugin/factory/patch hashes were `826412b…`, `ba850194…`, and `316b0b1e…`; session audit found one Gradle-wrapper tool call and no direct Python. Restoration returned the plugin/factory/input-loader/reference-rewriter/rules/allowlist to the documented production hashes, removed the temporary factory, left a clean worktree, and ended with no build process.

Cleanup was not fully contract-compliant: `pkill -9 -f 'Gradle[D]aemon'` ran twice, the other two mandated patterns ran once each, and none of the three exit codes were preserved after command output was lost. This deviation does not alter the execution/load evidence or `PASS` classification, but it is not waived. Task 092 freezes all three cleanup commands into one shell block with immediate scratch exit-code writes and forbids any rerun.

This result proves only managed-file access plus one production `FrozenAconfigInputs.load(...)` in the negative-admission control. Task 092 restores only positive allowlist admission with a byte-no-op visitor; cache state, `referenceOnlyVisitor(...)`, APK, R8, and runtime remain unproved.
