# Task 094 — C5 immutable input snapshot isolation control

## Authority and startup contract

You are the sole implementation/diagnostic worker for this bounded control. Work in the shared checkout `/home/conv/myspace/SystemUI-Gradle`; do not create a worktree. Chief will supply the exact pushed `main` commit containing this brief. Before any mutation, preflight, or Gradle command:

1. Read `AGENTS.md`, `docs/HANDOFF.md`, `docs/orchestration/CHARTER.md`, `docs/orchestration/STATE.md`, this brief, `docs/issues/2026-09-02-c5-immutable-input-snapshot-control.md`, `docs/issues/2026-09-02-c5-transient-cache-control.md`, `/tmp/task093-c5-transient-cache-control/final-evidence-summary.txt`, and all production/test sources named below completely.
2. Print exactly one `CONTRACT:` paragraph stating base, scope, allowed paths, single-command budget, scratch root, cleanup no-rerun rule, forbidden work, acceptance classes, and reports-to authority.
3. Stop until Chief explicitly accepts the contract. Before that acceptance, do not preflight, mutate, create scratch, or run Gradle.
4. After contract acceptance, verify `HEAD`, `origin/main`, clean worktree, absence of Java/Gradle/Kotlin/Soong/Ninja processes, and production hashes. Stop on mismatch; preflight may not kill processes. Do not mutate or run Gradle until Chief explicitly accepts the preflight.

Use `joycode/GLM-5.3` with `thinking=high`. Do not push or commit. Chief owns classification and acceptance.

## Objective

Test one falsifiable candidate seam: configuration-time validated inputs copied into Gradle-managed immutable `MapProperty<String, String>` and `SetProperty<String>` values, consumed by a field-free no-op `AsmClassVisitorFactory`. Determine whether this exact seam reaches positive allowlist admission and class-byte visitor creation in the real `:app:desugarDebugFileDependencies` pipeline without Task 084/093 serialization failure.

This task does not implement or prove the production visitor, Debug APK, Release/R8, static checker, device runtime, a sole cache sub-trigger, or any alternative seam.

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

## Allowed writes

Temporary tracked writes only:

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/ImmutableInputsControlFactory.kt`

Scratch writes only below `/tmp/task094-c5-immutable-input-snapshot/**`.

No documentation writes. No other tracked/untracked repository writes are allowed. Never use `git add`, `git commit`, or `git push`.

## Exact control shape

Implement a temporary `ImmutableInputsControlParameters : InstrumentationParameters` with exactly two managed properties:

```kotlin
@get:Input
val mappings: MapProperty<String, String>

@get:Input
val allowlist: SetProperty<String>
```

Implement `ImmutableInputsControlFactory` with no class-body properties, fields, companion object, object reference, external/static cache, thread-local, synchronized state, or annotations such as `@Transient`/`@Volatile`. The factory must be behavior-only.

In the plugin, before `onVariants`, call production `FrozenAconfigInputs.load(rulesFile, allowlistFile)` exactly once. Require 4 mappings and 166 allowlist entries. Inside the existing application-only variant registration, retain `InstrumentationScope.ALL` and configure the control parameters from that one frozen snapshot. Retain `FramesComputationMode.COPY_FRAMES`.

`isInstrumentable` must immediately return false for every class except `android.os.CustomFeatureFlags`. For that class only, print:

```text
TASK094_VALUES_ENTERED=android.os.CustomFeatureFlags
```

Then read both managed values, require sizes 4 and 166, require production helper `AconfigReferenceRewriteFactory.isAllowlistedClass(...)` returns true, and print:

```text
TASK094_VALUES_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166
```

Return true. `createClassVisitor` must require the same class name, read/validate the managed values again, print:

```text
TASK094_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags
```

and return `nextClassVisitor` unchanged. It must not reference, call, or construct `referenceOnlyVisitor(...)`.

Do not modify `AconfigReferenceRewriteFactory.kt`, `FrozenAconfigInputs.kt`, `ReferenceOnlyClassRewriter.kt`, the rules, or the allowlist. Do not change the application-only gate, scope, frames mode, or any app/module build wiring.

## Pre-run evidence

Before mutation, save to scratch:

- base/remote/status/process census;
- SHA-256 for plugin, production factory, frozen loader, reference rewriter, rules, and allowlist;
- line/entry counts and exact 4/166 input validation using existing read-only shell tools only;
- a copy of original plugin for byte-for-byte restoration.

After temporary mutation but before Gradle, save:

- exact diff and SHA-256 of both temporary tracked files;
- source-level counts proving one `FrozenAconfigInputs.load(` call site in the temporary plugin, two managed properties, zero factory class-body state/cache annotations, zero `referenceOnlyVisitor` text in the temporary factory;
- unchanged hashes for all forbidden production/input files.

If any invariant fails, restore and report without running Gradle.

## Single Gradle command

Exactly one shell tool invocation containing `./gradlew` is permitted, and it must execute exactly this pipeline once:

```bash
set -o pipefail
JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
  ./gradlew :app:desugarDebugFileDependencies \
    --info --stacktrace --console=plain --max-workers=4 \
    2>&1 | tee /tmp/task094-c5-immutable-input-snapshot/desugar-immutable-inputs.log
```

Immediately save the pipeline exit code. Do not run a second wrapper command for any reason. Forbidden: focused Gradle tests, `--rerun-tasks`, `--no-build-cache`, full assemble, Release/R8, checker, device/ADB/emulator, Soong/Ninja, or direct `python`/`python3`. Python via `uv run` is also unnecessary and forbidden in this task.

## Classification

Chief will make the final classification. Report evidence for exactly one provisional class:

- `PASS`: pipeline exit 0; all three Task 094 sentinels occur at least once; at least one `AsmClassesTransform` execution record exists; `NotSerializableException`, temporary `__instrumentationContext__`, and `InstrumentationContext_Decorated.__apiVersion__` marker counts are all zero.
- `IMMUTABLE_VALUES_ISOLATION_FAILURE`: pipeline nonzero and the exact Task 084/093 literal path reaches the temporary decorated factory before callbacks.
- `CONFIGURATION_LOAD_FAILURE`: pre-callback failure from the one configuration-time load or managed-value wiring without the known isolation path.
- `INCONCLUSIVE`: exit 0 but accepted/visitor sentinel or ASM execution evidence is absent.
- `OTHER_FAILURE`: any other result.

A `PASS` proves only this immutable-value/field-free no-op control seam. It does not prove production rewrite output or any APK/runtime gate.

## Post-run evidence

Without another Gradle command, capture:

- log SHA-256 and line count;
- pipeline exit and Gradle terminal summary;
- counts and representative lines for all three Task 094 sentinels;
- count/representative lines for `AsmClassesTransform` execution;
- counts and deepest excerpts for all known serialization markers;
- if emitted, `javap -p` or equivalent read-only class inspection showing the temporary factory declares no worker-authored fields; inability to locate output is disclosed, not repaired with Gradle;
- task execution summary and any `UP-TO-DATE` lines, without using target status to override direct sentinel evidence.

## Restoration and cleanup

Restore the plugin byte-for-byte and delete the temporary factory before cleanup. Verify all production/input hashes match pre-run and worktree is clean.

Execute the following cleanup as one shell invocation exactly once. Do not include any complete target regex literal elsewhere in that wrapper command line. Each exit code must be saved immediately; if output is lost, do not rerun or补跑:

```bash
set +e
first_pattern='Gradle'; first_pattern="${first_pattern}Daemon"
second_pattern='Kotlin'; second_pattern="${second_pattern}CompileDaemon"
third_pattern='kotlin-daemon-'; third_pattern="${third_pattern}embeddable"
pkill -9 -f "$first_pattern"; first_rc=$?
printf '%s\n' "$first_rc" > /tmp/task094-c5-immutable-input-snapshot/cleanup-1.exit
pkill -9 -f "$second_pattern"; second_rc=$?
printf '%s\n' "$second_rc" > /tmp/task094-c5-immutable-input-snapshot/cleanup-2.exit
pkill -9 -f "$third_pattern"; third_rc=$?
printf '%s\n' "$third_rc" > /tmp/task094-c5-immutable-input-snapshot/cleanup-3.exit
printf 'one=%s\ntwo=%s\nthree=%s\n' "$first_rc" "$second_rc" "$third_rc"
```

Then perform one read-only final process census and final repository status/hash verification. Report every deviation permanently; cleanup compliance is separate from experiment classification.

## Final report

Report: exact base; model/session path; preflight; temporary hashes/diff invariants; exact command count; pipeline exit; log path/size/hash; sentinel and ASM counts; serialization marker counts and excerpts; provisional classification with bounded meaning; restoration hashes/status; cleanup exit files; final process census; all deviations. Stop and wait for Chief acceptance.

## Accepted outcome

Chief accepted Task 094 as **`PASS`**. The one wrapper command returned `PIPELINE_RC=0` / `BUILD SUCCESSFUL in 17s`; the 1464-line log SHA-256 is `53fbffec9cff08f3349762effca125725a8781f8a4e26f92a74a7f73e1c2f4c0`. Entered, 4/166 accepted, and no-op visitor sentinels each occurred exactly once; 45 ASM records occurred; all known serialization markers were zero. `javap` showed no temporary-factory fields. Session audit found one Gradle wrapper call and zero Python calls.

Restoration and final process/worktree checks passed. Cleanup commands each ran once with exits `0/0/1`. Four caveats remain disclosed: an initial self-matching census later replaced by authoritative bracket-safe census; corrected test hash paths; ordinary diff omission of the separately saved untracked factory; and its gitignored compiled class output. This outcome proves only the immutable managed-value / field-free no-op isolation seam. Production visitor migration and proof are Task 095.
