# Task 092 — Make positive allowlist admission observable

## Goal

Run one fully reversible application-only `InstrumentationScope.ALL` micro-control that retains Task 091's proven managed-file access and one sentinel-scoped `FrozenAconfigInputs.load(...)`, changes only the sentinel decision from negative to production positive allowlist admission, and keeps the resulting visitor class-byte no-op. Conclusively classify whether positive admission reaches no-op visitor creation or activates the known factory-isolation path.

## Why now

Task 091 is `PASS`: the production parameter type, both managed file slots, and one production frozen-input load executed in an observable field-free/no-cache factory without serialization failure. The next smallest production implementation layer is allowlist membership plus a true admission. Transient cache state and `referenceOnlyVisitor(...)` construction remain excluded.

## Sources of truth

- `AGENTS.md`
- `docs/orchestration/CHARTER.md`
- `docs/issues/2026-09-02-c5-positive-allowlist-control.md`
- `docs/issues/2026-09-02-c5-frozen-input-load-control.md`
- `docs/issues/2026-09-02-c5-serialization-field-path.md`
- `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/{AconfigReferenceRewritePlugin,AconfigReferenceRewriteFactory,FrozenAconfigInputs,ReferenceOnlyClassRewriter}.kt`
- Complete Task 091 log, saved patch, and pre-run hashes under `/tmp/task091-c5-frozen-input-load-control/`

## Base and dependencies

- Base: exact pushed `main` selected by Chief after Task 091 closure and this brief are committed.
- Blocked by: Task 091 closure recorded, clean shared checkout, and no Gradle/Kotlin/Soong/Ninja process.
- Reports to: Chief.

## Authority

Temporary diagnostic only; no commit and no production fix. The Worker may create the exact temporary diff and scratch input, run the one exact Gradle command only after Chief inspects the patch/hashes, restore exactly, run the frozen cleanup block once, and report evidence.

## Scope

### Allowed paths (temporary; mandatory restoration)

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/PositiveAllowlistControlFactory.kt`
- `/tmp/task092-c5-positive-allowlist-control/**`

### Forbidden

All other tracked/untracked paths; production factory/parameter interface/input loader/reference rewriter; frozen rules/allowlist; app wiring; AOSP/SDK/`libs/**`; source/resources/manifests/ProGuard; network/package/tool/version changes; full assemble; Release/R8; checker; emulator/ADB; Soong/Ninja; a second Gradle-wrapper invocation; any extra or repeated `pkill`; commit/push; direct `python`/`python3`.

## Required startup

1. Read all of `AGENTS.md`; wait for the call to return and print `AGENTS_READ`.
2. In a separate call, read all of `docs/orchestration/CHARTER.md`; wait for the call to return and print `CHARTER_READ`.
3. Read worker-contract, this brief, the Task 092/091/084 issues, Task 089 report, current plugin/factory/input-loader/reference rewriter, and the complete Task 091 log/saved patch/pre-run hashes.
4. Print `CONTRACT:`. Do not create scratch, edit, run process preflight, invoke Gradle, or execute cleanup before Chief accepts it.

## Work

1. Preflight using only `git`, `ps`, `pgrep`, and read-only file/hash tools. Require the exact pushed base, clean tracked/untracked state, and no Gradle/Kotlin/Soong/Ninja process. **Do not invoke the Gradle wrapper in preflight.**
2. Create `/tmp/task092-c5-positive-allowlist-control/`. Record base and SHA-256 for the original plugin, production factory, input loader, reference rewriter, rules, and allowlist; prove the temporary factory absent.
3. Copy production `gradle/aosp17-critical-aconfig-reference-rules.txt` byte-for-byte to `/tmp/task092-c5-positive-allowlist-control/task092-frozen-rules.txt`. Require SHA-256 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`, exact byte equality, and no appended probe text. Keep the production allowlist path unchanged and prove `android.os.CustomFeatureFlags` occurs exactly once in it.
4. Create field-free/no-cache `PositiveAllowlistControlFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`:
   - for every class other than `android.os.CustomFeatureFlags`, return `false` immediately without reading parameters;
   - for exactly that sentinel, print `TASK092_FILTER_ENTERED=android.os.CustomFeatureFlags`;
   - call `FrozenAconfigInputs.load(parameters.get().rulesFile.asFile.get(), parameters.get().allowlistFile.asFile.get())` exactly once for that invocation and require mappings size 4 / allowlist size 166;
   - call exactly `AconfigReferenceRewriteFactory.isAllowlistedClass(classData.className, inputs.allowlist)`, require the result is true, print `TASK092_FILTER_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166`, and return true;
   - in `createClassVisitor`, require `classContext.currentClassData.className == "android.os.CustomFeatureFlags"`, print `TASK092_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags`, and return `nextClassVisitor` unchanged;
   - do not call `referenceOnlyVisitor`, map names, read parameters in `createClassVisitor`, or add any instance/static cache/state field.
5. Switch only the temporary registration to this factory and set `rulesFile` to the scratch byte-exact copy. Retain the production allowlist assignment, application-only gate, `InstrumentationScope.ALL`, `FramesComputationMode.COPY_FRAMES`, and parameter interface.
6. Save the original plugin, temporary factory, scratch rule copy, and `git diff --binary` under the Task 092 scratch root. Run `git diff --check`; report exact changed paths and hashes. Stop for Chief inspection.
7. After Chief approval, run once and only once:
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task092-c5-positive-allowlist-control/desugar-positive-allowlist.log
   ```
8. Record pipeline exit, target outcome, log line count/SHA-256, exact entered/accepted/no-op-visitor sentinel counts, all `AsmClassesTransform` execution/cache lines, deepest cause, and literal field path.
9. Classify exactly as defined by the issue: `PASS`, `ADMISSION_ACTIVATED_ISOLATION_FAILURE`, `FILTER_FAILURE`, `INCONCLUSIVE`, or `OTHER_FAILURE`. A known isolation path after accepted admission must not be described as the membership operation itself being unserializable.
10. Restore the plugin byte-for-byte and delete the temporary factory. Execute this cleanup block exactly once as one shell invocation; each `pkill` must occur once, its exit code must be saved immediately, and no cleanup command may be rerun:
    ```bash
    set +e
    pkill -9 -f 'Gradle[D]aemon'; gradle_daemon_rc=$?
    printf '%s\n' "$gradle_daemon_rc" > /tmp/task092-c5-positive-allowlist-control/cleanup-gradle-daemon.exit
    pkill -9 -f 'KotlinCompile[D]aemon'; kotlin_compile_daemon_rc=$?
    printf '%s\n' "$kotlin_compile_daemon_rc" > /tmp/task092-c5-positive-allowlist-control/cleanup-kotlin-compile-daemon.exit
    pkill -9 -f 'kotlin-daemon-[e]mbeddable'; kotlin_embeddable_daemon_rc=$?
    printf '%s\n' "$kotlin_embeddable_daemon_rc" > /tmp/task092-c5-positive-allowlist-control/cleanup-kotlin-embeddable-daemon.exit
    printf 'GradleDaemon=%s\nKotlinCompileDaemon=%s\nKotlinDaemonEmbeddable=%s\n' \
      "$gradle_daemon_rc" "$kotlin_compile_daemon_rc" "$kotlin_embeddable_daemon_rc"
    ```
    Afterward use only read-only `ps`/`pgrep` to prove no Gradle/Kotlin/Soong/Ninja process. Prove clean worktree, production hashes restored, temporary factory absent, and preserve scratch evidence.

## Acceptance

- Pre-run repository diff is exactly the two Allowed tracked paths; production factory/interface/input loader/reference rewriter/rules/allowlist/app wiring are unchanged.
- Scratch rules are byte-identical to production but use the unique Task 092 path, changing a declared `@InputFile` value without changing frozen semantics.
- The temporary factory is field-free/no-cache. Only the proven sentinel reads the two inputs, executes one load, calls the production allowlist helper, and returns true; visitor creation is observable and byte-no-op.
- Exactly one Gradle wrapper invocation runs. No `PASS` without exit 0 plus accepted-sentinel and no-op-visitor-sentinel counts each at least one.
- The three mandatory cleanup commands each run exactly once and their separate exit codes remain in scratch. No rerun is allowed if terminal output is lost.
- Final worktree is clean, production hashes restored, temporary factory absent, and no residual build process remains.
- No claim beyond the positive-admission/no-op-visitor rung is made.

## Build/run profile

- Revision/artifact: pushed Task 092 planning base.
- Mode: focused diagnostic.
- Prerequisites: clean shared checkout; Task 091 evidence readable; no Gradle/Kotlin/Soong/Ninja process.
- Writable roots: Gradle's existing build/cache outputs, the exact Task 092 scratch root, and two temporary tracked paths.
- Shared state: exclusive shared checkout and Gradle/Kotlin daemons; no concurrent Gradle/Soong.
- Network: offline.
- Ready signal: Chief accepts exact temporary diff and scratch/input hashes.
- Pass signal: command exit 0, accepted sentinel ≥1, no-op visitor sentinel ≥1.
- Failure log: `/tmp/task092-c5-positive-allowlist-control/desugar-positive-allowlist.log`.
- Cleanup: exact source restoration, temporary factory deletion, one frozen three-command cleanup block with saved exit codes, clean status.
- Claim scope: only whether one positive production allowlist admission reaches a class-byte no-op visitor or activates the known isolation path; no cache/reference visitor/APK/R8/runtime proof.

## Delivery

- Commit policy: none.
- Push policy: forbidden; Chief only.
- Completion report:
  ```text
  STATUS: PASS|FAIL
  CONTROL_PATCH_PATHS=
  LOOP_EXIT=
  TARGET_OUTCOME=
  CONTROL_RESULT=PASS|ADMISSION_ACTIVATED_ISOLATION_FAILURE|FILTER_FAILURE|INCONCLUSIVE|OTHER_FAILURE
  FILTER_ENTERED_COUNT=
  FILTER_ACCEPTED_COUNT=
  NOOP_VISITOR_CREATED_COUNT=
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
