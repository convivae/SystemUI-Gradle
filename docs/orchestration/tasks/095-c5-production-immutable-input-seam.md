# Task 095 — C5 production immutable-input seam and visitor proof

## Authority and startup contract

You are the sole production implementation worker for this bounded task. Work in the shared checkout `/home/conv/myspace/SystemUI-Gradle`; do not create a worktree. Chief will supply the exact pushed `main` commit containing this brief. Before any preflight, mutation, scratch write, Python, or Gradle command:

1. Read separately and completely, in this order: `AGENTS.md`; `docs/HANDOFF.md`; `docs/orchestration/CHARTER.md`; `docs/orchestration/STATE.md`; the tail of `docs/orchestration/log.md`; this brief; `docs/issues/2026-09-02-c5-production-immutable-input-seam.md`; `docs/issues/2026-09-02-c5-immutable-input-snapshot-control.md`; then every mandatory source below.
2. Print exactly one `CONTRACT:` paragraph stating base, goal, allowed writes, two-command Gradle budget, scratch root, proof gates, cleanup no-rerun rule, forbidden work, and reports-to authority.
3. Stop until Chief explicitly accepts the contract. Before acceptance, do not preflight, create scratch, mutate, invoke Python, or run Gradle.
4. After contract acceptance, perform read-only preflight: `HEAD`, `origin/main`, clean worktree, absence of Java/Gradle/Kotlin/Soong/Ninja processes, production/input hashes, and current direct-output RED baseline. Do not kill processes. Stop on mismatch and wait for Chief acceptance before the first write.

Use explicit `joycode/GLM-5.3` with `thinking=high`. Do not commit or push. Chief owns acceptance, commit, review dispatch, and push.

## Objective

Migrate the Task 094-proven configuration-time validated managed-value / field-free factory seam into production and restore the existing `referenceOnlyVisitor(...)`. Prove it with focused semantic tests and one real dependency transform whose DEX output changes from two absent hidden references to two present hidden references without hidden definitions.

This task does not run or prove a full Debug APK, Release/R8, final four-mapping static gate, device runtime, reboot durability, a sole Task 093 cache sub-trigger, or Task 079 broad replay.

## Mandatory complete reads

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewriteFactory.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/FrozenAconfigInputs.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/ReferenceOnlyClassRewriter.kt`
- `buildSrc/src/test/kotlin/com/android/systemui/aconfigrewrite/FrozenAconfigInputsTest.kt`
- `buildSrc/src/test/kotlin/com/android/systemui/aconfigrewrite/AconfigInstrumentationRegistrationTest.kt`
- `buildSrc/src/test/kotlin/com/android/systemui/aconfigrewrite/ReferenceOnlyClassRewriterTest.kt`
- `buildSrc/build.gradle.kts`
- `gradle/aosp17-critical-aconfig-reference-rules.txt`
- `gradle/aosp17-critical-aconfig-reference-classes.txt`
- `tools/check_aconfig_jarjar_references.py`
- `/tmp/task094-c5-immutable-input-snapshot/post-run-evidence.txt`
- `/tmp/task094-c5-immutable-input-snapshot/post-run-javap.txt`
- `/tmp/task094-c5-immutable-input-snapshot/final-verification.txt`

If a `/tmp` evidence file is missing, report it and stop; do not recreate Task 094 evidence.

## Allowed writes

Tracked writes only:

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewriteFactory.kt`
- `buildSrc/src/test/kotlin/com/android/systemui/aconfigrewrite/AconfigInstrumentationRegistrationTest.kt`
- `buildSrc/src/test/kotlin/com/android/systemui/aconfigrewrite/ReferenceOnlyClassRewriterTest.kt`
- `docs/issues/2026-09-02-c5-production-immutable-input-seam.md`

Scratch writes only below `/tmp/task095-c5-production-immutable-input-seam/**`.

No other repository writes are allowed. In particular, do not modify `FrozenAconfigInputs.kt`, `ReferenceOnlyClassRewriter.kt`, `FrozenAconfigInputsTest.kt`, `buildSrc/build.gradle.kts`, rules/allowlist bytes, app/module build files, AOSP/SystemUI source or resources, SDK, `libs/**`, ProGuard/R8, orchestration docs, ADRs, or tools. Never use `git add`, `git commit`, or `git push`.

## Exact production shape

1. Replace the two file-backed production parameters with exactly:

```kotlin
@get:Input
val mappings: MapProperty<String, String>

@get:Input
val allowlist: SetProperty<String>
```

2. In `AconfigReferenceRewritePlugin.apply`, after the application plugin is present and before `onVariants`, resolve the production rules and allowlist files and call `FrozenAconfigInputs.load(rulesFile, allowlistFile)` exactly once. Pass the resulting `FrozenAconfigInputs` into registration. Do not load once per variant.
3. Change `AconfigInstrumentationRegistration.registerForPlugin(...)` to accept the validated snapshot rather than `File` arguments. For the application plugin only, register exact `AconfigReferenceRewriteFactory`, `InstrumentationScope.ALL`, set both managed values from the snapshot, and retain `FramesComputationMode.COPY_FRAMES`. Non-application plugin IDs must return false without touching instrumentation.
4. Make `AconfigReferenceRewriteFactory` behavior-only. It may declare no class-body property, worker-authored instance/static/companion field, cache, external/static mutable cache, thread-local, synchronization, `@Transient`, or `@Volatile`. Move the pure `isAllowlistedClass(...)` helper out of the factory companion into a top-level internal function and update its focused test.
5. `isInstrumentable` must use the managed allowlist. `createClassVisitor` must read the managed mappings, convert source and target dot-FQCNs to JVM internal names, derive the current class internal name, and call the existing `referenceOnlyVisitor(nextClassVisitor, currentClass, internalMappings)` exactly as the production visitor seam. Do not add logging, sentinels, suppression, class deletion, hidden definitions, or a second rewriter.
6. Preserve application-only scope, `ALL`, `COPY_FRAMES`, the four mappings, 166-class allowlist, and every reference-only invariant. Do not change `ReferenceOnlyClassRewriter.kt`.

## Required focused tests

Update the registration test so it verifies all of the following, not only method names:

- application registration uses exact `AconfigReferenceRewriteFactory`, `InstrumentationScope.ALL`, and `COPY_FRAMES`;
- the transform parameter action writes the exact four mappings and 166 allowlist identities from a validated `FrozenAconfigInputs` snapshot into managed `MapProperty`/`SetProperty` recording doubles;
- non-application plugin IDs return false and make no instrumentation calls.

Update the reference-only test only as needed for the top-level allowlist helper. Preserve all five visitor semantic tests and all three frozen-input tests. Do not add a Gradle dependency.

After Chief inspects and accepts the complete source/test diff, run exactly one focused wrapper invocation:

```bash
set -o pipefail
./gradlew -p buildSrc test \
  --tests 'com.android.systemui.aconfigrewrite.*' \
  --stacktrace --console=plain --max-workers=4 \
  2>&1 | tee /tmp/task095-c5-production-immutable-input-seam/focused-tests.log
```

Save the pipeline exit code immediately. A nonzero result stops the task; do not run the direct transform. Do not use `--rerun-tasks` or `--no-build-cache`. If Gradle reports the tests `UP-TO-DATE`, report `INCONCLUSIVE_FOCUSED_TESTS` and stop rather than forcing them.

## Real direct-transform proof

Before any production mutation, capture a RED baseline from the existing direct-task outputs using `uv run python` and the repository DEX parser. Across exactly `*_systemui-aconfig-flags.jar` and `*_tracinglib-platform.jar` below `app/build/intermediates/external_file_lib_dex_archives/debug/desugarDebugFileDependencies`, require:

- old source definitions: `android.os.Flags` and `com.android.window.flags.Flags` = `2/2`;
- corresponding hidden target references = `0/2`;
- corresponding hidden target definitions = `0/2`.

After focused tests pass and Chief explicitly authorizes the real proof, invoke the Gradle wrapper exactly once more:

```bash
set -o pipefail
JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
  ./gradlew :app:desugarDebugFileDependencies \
    --info --stacktrace --console=plain --max-workers=4 \
    2>&1 | tee /tmp/task095-c5-production-immutable-input-seam/desugar-production-visitor.log
```

Save the pipeline exit immediately. No third Gradle wrapper invocation is permitted for any reason.

Then rerun the same read-only `uv run python` DEX scan against exactly those two outputs. PASS requires:

- command exit 0 and terminal `BUILD SUCCESSFUL`;
- at least one real `AsmClassesTransform` execution record;
- known serialization marker counts all zero: `NotSerializableException`, production decorated-factory `__instrumentationContext__`, and `InstrumentationContext_Decorated.__apiVersion__`;
- hidden target references changed from pre-run `0/2` to post-run `2/2`;
- hidden target definitions remain `0/2`;
- old source definitions remain `2/2` (reference-only definition preservation).

The aggregate old source references may remain present because the old definitions and current-class self references are intentionally preserved. Do not misclassify that as failure. The other two mappings are outside this bounded external-file task and remain for the full Debug gate.

## Static/source evidence

Capture before Gradle and after compilation:

- exact diff, `git diff --check`, file hashes, rules/allowlist unchanged hashes and 4/166 counts;
- source counts: exactly one `FrozenAconfigInputs.load(` call in the plugin; managed parameter types present; forbidden file properties/cache/synchronization/annotations absent from production factory;
- `javap -p` for the compiled production factory proving no worker-authored declared fields, and for the parameters interface proving only the two managed accessors;
- all nine focused tests discovered and completed with zero failures/errors;
- direct log hash/line count, task summary, ASM records, serialization marker counts, and pre/post DEX reports.

Task-level `UP-TO-DATE` does not override direct DEX evidence. Conversely, `BUILD SUCCESSFUL` without the 0/2 → 2/2 DEX change is `INCONCLUSIVE_DIRECT_VISITOR`, not PASS.

## Forbidden work

Do not run full `assembleDebug`, Release/R8, APK checker, device/ADB/emulator, Soong/Ninja, source alignment, all Python tests, Task 079, or any additional Gradle command. Do not use `--rerun-tasks`, `--no-build-cache`, stub classes, copied/packaged hidden platform classes, `dontwarn`, source import rewrites, JarJar, class deletion, post-R8/DEX rewriting, suppression, or external cache state.

Python is allowed only as `uv run python` for the frozen DEX evidence and read-only session/evidence processing. Direct `python`/`python3`, `pip`, `uv pip`, package installation, and new scripts are forbidden.

## Restoration, cleanup, and final report

This is a production implementation task: do not restore accepted production/test changes. If a gate fails, stop with the exact diff and evidence; Chief decides whether to retain or revert.

After the final authorized Gradle action, run the following cleanup shell block exactly once. The complete wrapper command line must not contain a self-matching full target regex literal. Save each exit code immediately and never rerun or补跑 a lost cleanup command:

```bash
set +e
first_pattern='Gradle'; first_pattern="${first_pattern}Daemon"
second_pattern='Kotlin'; second_pattern="${second_pattern}CompileDaemon"
third_pattern='kotlin-daemon-'; third_pattern="${third_pattern}embeddable"
pkill -9 -f "$first_pattern"; first_rc=$?
printf '%s\n' "$first_rc" > /tmp/task095-c5-production-immutable-input-seam/cleanup-1.exit
pkill -9 -f "$second_pattern"; second_rc=$?
printf '%s\n' "$second_rc" > /tmp/task095-c5-production-immutable-input-seam/cleanup-2.exit
pkill -9 -f "$third_pattern"; third_rc=$?
printf '%s\n' "$third_rc" > /tmp/task095-c5-production-immutable-input-seam/cleanup-3.exit
printf 'one=%s\ntwo=%s\nthree=%s\n' "$first_rc" "$second_rc" "$third_rc"
```

Finish with one read-only process census, status, exact allowed-path diff, hashes, and issue update. Report model/session JSON, base, command count, focused result, direct result, pre/post DEX results, source/classfile invariants, cleanup exits, process census, deviations, and a terminal `HANDOFF:` block. Stop for Chief acceptance; do not commit.
