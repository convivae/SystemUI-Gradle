# Task 093 — Isolate the production transient cache layer

## Goal

Run one reversible application-only `InstrumentationScope.ALL` control that retains Task 092's proven parameter loading, positive allowlist admission, and class-byte no-op visitor, while adding exactly the production-shaped transient cache layer. Classify whether that layer activates the known factory-isolation path.

## Outcome

Closed as **`CACHE_ACTIVATED_ISOLATION_FAILURE`** from pushed base `81e190e322424d8779a2d1949b355ab40427721c`. The sole frozen Gradle command exited 1 at `:app:desugarDebugFileDependencies`; the 9387-line log has SHA-256 `7f760669721065eb672c4a7ee8c07c848c45ce32c07a77c0aa7e6248c102ff31`. All three Task 093 sentinels and ASM transform records have count 0, while `NotSerializableException`, `InstrumentationContext_Decorated.__apiVersion__`, and `TransientCacheControlFactory_Decorated.__instrumentationContext__` each have count 46. The failure therefore precedes factory callbacks and exactly reproduces the Task 084 isolation path.

The full cache layer is the minimum known activation boundary relative to Task 092, not proof that any individual field, annotation, accessor, or writeback is the sole trigger. Temporary paths were fully restored and the final worktree/process census was clean. Session audit found exactly one Gradle-wrapper call and zero direct Python calls. Cleanup deviated: saved exit codes are 0 and 1, the third file was never created, and no cleanup command was rerun; see the issue for full evidence.

## Sources of truth

- `AGENTS.md`
- `docs/orchestration/CHARTER.md`
- `docs/issues/2026-09-02-c5-transient-cache-control.md`
- `docs/issues/2026-09-02-c5-positive-allowlist-control.md`
- `docs/issues/2026-09-02-c5-serialization-field-path.md`
- `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/{AconfigReferenceRewritePlugin,AconfigReferenceRewriteFactory,FrozenAconfigInputs,ReferenceOnlyClassRewriter}.kt`
- Complete Task 092 log, saved patch, temporary source copies, and cleanup evidence under `/tmp/task092-c5-positive-allowlist-control/`

## Base and authority

- Base: exact pushed `main` selected by Chief after Task 092 closure and this brief are committed.
- Reports to: Chief.
- Temporary diagnostic only. No commit, production fix, second variant, full build, Release/R8, or device work.

## Allowed paths

Temporary tracked paths, both mandatory restoration:

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/TransientCacheControlFactory.kt`

Scratch: `/tmp/task093-c5-transient-cache-control/**` only. All other paths and actions are forbidden, including production factory/inputs/rewriter, rules/allowlist, app wiring, AOSP/SDK/`libs/**`, source/resources/manifests/ProGuard, network/tool/version changes, direct `python`/`python3`, commit/push, full assemble, Release/R8, checker, emulator/ADB, Soong/Ninja, a second Gradle-wrapper invocation, or repeated cleanup.

## Required startup

1. Read all of `AGENTS.md` in one completed call and print `AGENTS_READ`.
2. In a later completed call, read all of `docs/orchestration/CHARTER.md` and print `CHARTER_READ`.
3. Read worker-contract, this brief, Task 093/092/084 issues, Task 089 report, all four production Kotlin files, and the complete Task 092 scratch evidence/log.
4. Print `CONTRACT:`. Do not preflight, create scratch, edit, invoke Gradle, or clean processes until Chief accepts it.

## Work

1. Preflight with only `git`, `ps`/`pgrep`, and read-only file/hash tools. Require exact pushed base, clean tracked/untracked state, and no Gradle/Kotlin/Soong/Ninja process. Do not invoke the Gradle wrapper.
2. Create the scratch root and record base plus production hashes. Copy production rules byte-for-byte to `task093-frozen-rules.txt`; require exact equality and SHA `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`. Keep production allowlist unchanged and require SHA `926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b` plus exactly one `android.os.CustomFeatureFlags` entry.
3. Create `TransientCacheControlFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>` with exactly one instance field:
   ```kotlin
   @Transient
   @Volatile
   private var cachedInputs: FrozenAconfigInputs? = null
   ```
   Add exactly this production-shaped accessor (apart from formatting, no accessor semantic variation is allowed):
   ```kotlin
   private fun inputs(): FrozenAconfigInputs {
       cachedInputs?.let { return it }
       return synchronized(this) {
           cachedInputs ?: FrozenAconfigInputs.load(
               parameters.get().rulesFile.asFile.get(),
               parameters.get().allowlistFile.asFile.get(),
           ).also { cachedInputs = it }
       }
   }
   ```
   Therefore the accessor contains one `FrozenAconfigInputs.load(...)` call site and exactly two `parameters.get()` calls, one per managed file. Do not combine them through a local parameters/provider value, add another accessor, or introduce static/companion cache or other state.
4. In `isInstrumentable`, reject every non-sentinel before reading parameters/cache. For `android.os.CustomFeatureFlags`, print `TASK093_CACHE_ENTERED=android.os.CustomFeatureFlags`, obtain inputs through the cache accessor, require 4 mappings/166 allowlist, call exactly `AconfigReferenceRewriteFactory.isAllowlistedClass(...)`, require true, print `TASK093_CACHE_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166`, and return true.
5. In `createClassVisitor`, require the sentinel class, print `TASK093_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags`, and return `nextClassVisitor` unchanged. It must not read parameters/cache, map names, or call/construct `referenceOnlyVisitor(...)`.
6. Switch only the temporary registration and scratch-rules path. Preserve production allowlist assignment, app-only gate, `ALL`, `COPY_FRAMES`, and parameter interface. Save original plugin, temporary source, scratch rule copy, and `git diff --binary`; run `git diff --check`, report exact paths/hashes, and stop for Chief inspection.
7. After Chief approval, run exactly once:
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task093-c5-transient-cache-control/desugar-transient-cache.log
   ```
8. Record pipeline exit, target outcome, line count/SHA, exact three sentinel counts, ASM transform lines/count, deepest cause, and literal field path. Classify only by the issue matrix.
9. Restore plugin byte-for-byte and delete the temporary factory. Run the issue's frozen cleanup block exactly once as one shell invocation. Its variable/output labels intentionally avoid the daemon literals so the wrapper shell cannot match its own later arguments. Save all three exit-code files immediately; never rerun a cleanup command. Then use only read-only process census and prove clean status, restored production hashes, and temporary-factory absence.

## Acceptance

- Pre-run tracked diff is exactly the two Allowed Paths; scratch rules are byte-identical under a unique declared path.
- Temporary factory has only the one transient/volatile cache field and the exact production-shaped accessor: one load call site, two `parameters.get()` calls, fast path, synchronized second read, and writeback. Positive admission and class-byte no-op visitor remain identical in scope to Task 092; `referenceOnlyVisitor(...)` is absent.
- Exactly one Gradle wrapper invocation. `PASS` requires exit 0 plus accepted and visitor sentinels each at least once.
- Cleanup block executes once without shell self-match, each exit code is saved, worktree returns clean, and production hashes are restored.
- Claims do not extend to production visitor, complete caller coverage, APK, R8, or runtime.

## Build/run profile

- Mode: focused diagnostic; shared checkout and Gradle/Kotlin state are exclusive.
- Network: offline.
- Ready signal: Chief accepts the exact temporary diff and hashes.
- Pass signal: exit 0, accepted sentinel ≥1, no-op visitor sentinel ≥1.
- Failure log: `/tmp/task093-c5-transient-cache-control/desugar-transient-cache.log`.
- Commit/push: forbidden; Chief only.

## Delivery

```text
STATUS: PASS|FAIL
CONTROL_PATCH_PATHS=
PIPELINE_EXIT=
TARGET_OUTCOME=
CONTROL_RESULT=PASS|CACHE_ACTIVATED_ISOLATION_FAILURE|CACHE_LOAD_FAILURE|INCONCLUSIVE|OTHER_FAILURE
CACHE_ENTERED_COUNT=
CACHE_ACCEPTED_COUNT=
NOOP_VISITOR_CREATED_COUNT=
ASM_TRANSFORM_EVIDENCE=
DEEPEST_CAUSE=
FIELD_PATH=
PRODUCTION_PATHS_UNCHANGED=YES|NO
TRACKED_WORKTREE=
CLEANUP_EXIT_CODES=
FORBIDDEN_ACTIONS=NONE|...
NEXT=Chief defines the result-conditioned next task
```

End with a concise `HANDOFF:` block.
