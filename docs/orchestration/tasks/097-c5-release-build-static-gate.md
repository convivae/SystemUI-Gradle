# Task 097 — C5 fresh Release APK build/R8/static gate

## Status

PASS — no-fix fresh Release build/R8/static gate completed on 2026-09-02. Exactly one Gradle-wrapper invocation exited 0; runtime remains unclaimed.

## Objective

Build one fresh Release APK through R8 and prove the four runtime-critical AOSP-17 aconfig references are relocated in the final APK without packaging hidden platform definitions.

## Frozen startup order

Before any preflight, scratch creation, output deletion, Gradle command, or repository write, read these files **completely and in this exact order**:

1. `AGENTS.md`
2. `docs/HANDOFF.md`
3. `docs/orchestration/CHARTER.md`
4. `docs/orchestration/STATE.md`
5. the final 140 lines of `docs/orchestration/log.md`
6. this task brief
7. `docs/issues/2026-09-02-c5-release-build-static-gate.md`
8. all mandatory sources below

Then emit exactly one `CONTRACT:` block and wait for Chief acceptance. Any out-of-order read retires the worker. No `git fetch`, `git pull`, or other network/ref mutation is permitted.

## Mandatory sources

Read completely before CONTRACT:

- `docs/issues/2026-09-02-c5-debug-build-static-gate.md`
- `docs/issues/2026-09-02-c5-production-immutable-input-seam.md`
- `docs/adr/0008-pre-dex-aconfig-reference-rewrite.md`
- `tools/check_aconfig_jarjar_references.py`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewriteFactory.kt`
- `gradle/aosp17-critical-aconfig-reference-rules.txt`
- AOSP authoritative rules: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`

## Required CONTRACT

The single block must state:

- task ID `097`, shared checkout, exact intended base `HEAD == origin/main` with `7c0f4f0c` as ancestor;
- model `joycode/GLM-5.3`, `thinking=high`, and `HERDR_ENV=1` must be verified before execution;
- no-fix scope and exactly one Gradle-wrapper call;
- stale Release APK deletion, scratch root, exact build command, static gates, cleanup boundary, and forbidden work;
- on any mismatch or build/static failure: stop, preserve evidence, report; do not repair.

## Scope

### May

- Read repository/AOSP files and generated Release evidence.
- Create only `/tmp/task097-c5-release-build-static/` scratch evidence.
- Delete only stale generated `app/build/outputs/apk/release/app-release.apk` before the build.
- Allow Gradle to write its normal generated/cache outputs.
- Run the frozen build command once.
- After a successful build, use standard read-only tools plus `uv run python tools/check_aconfig_jarjar_references.py` for static evidence.
- Run the three frozen cleanup commands once each and save each exit code immediately.

### May not

- Modify any tracked source, build logic, resource, rule, checker, issue, or orchestration file.
- Commit, push, fetch, pull, rebase, merge, checkout another ref, or change Git refs.
- Run a second Gradle command, `clean`, any Debug task, a direct R8 retry, Soong/Ninja, ADB/emulator/device work, or Task 079.
- Use `apkanalyzer dex reference-tree`, raw JarJar, post-R8/DEX rewriting, class deletion, hidden platform class packaging, `dontwarn`, suppression, stub, or import rewrite.
- Run direct `python`/`python3`; Python must be `uv run python`.
- Repair a failure inside this task.

## Preflight

After CONTRACT acceptance only:

1. Verify `HERDR_ENV=1`, model/session identity, `HEAD == origin/main`, and `git merge-base --is-ancestor 7c0f4f0c HEAD`.
2. Verify `git status --short --untracked-files=all` is empty.
3. Verify no conflicting Gradle/Kotlin/Soong/Ninja process. Avoid a process-census command whose own command line can match the tested literal; if uncertain, stop and ask Chief rather than rerun variants.
4. Record Java runtime/toolchain facts without changing them: Gradle runtime JDK 25 and project toolchain 21 remain distinct.
5. Record authoritative rules path, count and SHA; verify exactly 725 rules and the four critical mappings match `gradle/aosp17-critical-aconfig-reference-rules.txt`.
6. Record the current stale Release APK identity if present, then delete only that APK. Verify it is absent before build.

## Sole Gradle invocation

Run exactly once, with true pipeline exit capture:

```bash
set -o pipefail
./gradlew :app:assembleRelease --console=plain --rerun-tasks --max-workers=4 \
  2>&1 | tee /tmp/task097-c5-release-build-static/assemble-release.log
printf '%s\n' "${PIPESTATUS[0]}" > /tmp/task097-c5-release-build-static/assemble-release.exit
```

Do not run any other `./gradlew`/`gradle` command. If exit is nonzero, preserve the first actionable failure, skip APK/static analysis, perform final status/cleanup once, and report FAIL.

## Successful-build evidence

Only if build exit is 0 and log contains `BUILD SUCCESSFUL`:

1. Verify the fresh `app/build/outputs/apk/release/app-release.apk` exists and is non-empty. Save `stat`, size, mtime and SHA-256.
2. Run `unzip -t` once and save output/exit. Enumerate `classes*.dex` entries.
3. Confirm log evidence that `:app:minifyReleaseWithR8` and `:app:packageRelease` executed, not `UP-TO-DATE`, `FROM-CACHE`, or skipped.
4. Run exactly:

```bash
uv run python tools/check_aconfig_jarjar_references.py \
  --apk app/build/outputs/apk/release/app-release.apk \
  --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
```

Save full output and true exit code. Exit 2 is always FAIL. Release PASS requires exit 0 and `RESULT=PASS`.
5. Verify the checker output explicitly proves:
   - the four critical source descriptors each `referenced=no, defined=no`;
   - the four critical hidden targets each `referenced=yes, defined=no`;
   - aggregate target descriptors `defined: 0` across all 725 rules.
6. Record existence, size, mtime and SHA for current Release R8 outputs under `app/build/outputs/mapping/release/` if present. These are diagnostic only and cannot override APK/checker failure.

## Cleanup and final state

After evidence collection (or immediately after build failure), record `git status --short --untracked-files=all`, then run each cleanup command exactly once and immediately save its exit code:

```bash
pkill -f '[o]rg.gradle.launcher.daemon.bootstrap.GradleDaemon'
pkill -f '[K]otlinCompileDaemon'
pkill -f '[k]otlin-compiler-embeddable'
```

Do not rerun a cleanup command if output is unclear or an exit code is lost. Use a non-self-matching final census and record it. Final tracked/untracked status must be empty.

## Acceptance

PASS requires all of:

- one and only one Gradle-wrapper invocation; build exit 0 and `BUILD SUCCESSFUL`;
- R8 minify and Release package tasks actually executed;
- fresh non-empty Release APK, ZIP test exit 0, identity frozen;
- checker exit 0 / `RESULT=PASS`;
- critical old source references/definitions `0/4`, critical hidden references `4/4`, critical hidden definitions `0/4`, and all-725 hidden target definitions 0;
- no tracked/untracked repository change, no forbidden action, cleanup recorded once, final process census clean.

Otherwise classify FAIL or BLOCKED without a fix. PASS does not claim device/runtime success.

## Required report

```text
STATUS=PASS|FAIL|BLOCKED
BASE_HEAD=...
ORIGIN_MAIN=...
PRODUCTION_ANCESTOR=yes|no
MODEL=joycode/GLM-5.3
THINKING=high
HERDR_ENV=...
GRADLE_WRAPPER_CALLS=...
BUILD_EXIT=...
BUILD_SUCCESSFUL_COUNT=...
R8_TASK_EXECUTED=yes|no
PACKAGE_TASK_EXECUTED=yes|no
APK_PATH=...
APK_SIZE=...
APK_SHA256=...
ZIP_TEST_EXIT=...
DEX_COUNT=...
CHECKER_EXIT=...
CHECKER_RESULT=...
CRITICAL_OLD_REFERENCED=...
CRITICAL_OLD_DEFINED=...
CRITICAL_HIDDEN_REFERENCED=...
CRITICAL_HIDDEN_DEFINED=...
ALL_TARGET_DEFINED=...
R8_OUTPUTS=...
CLEANUP_EXITS=...
FINAL_PROCESS_CENSUS=...
FINAL_STATUS=...
FORBIDDEN_ACTIONS=...
EVIDENCE_ROOT=/tmp/task097-c5-release-build-static
NEXT=Chief records result; Debug runtime remains separate
```

End with a concise `HANDOFF:` block and wait. Do not commit or push.

## Execution result

`task097-release-r3` completed the gate from pushed base `1420c7c5`. The sole wrapper call exited 0 (`BUILD SUCCESSFUL in 7m 5s`, 493/493 tasks executed); R8 minify and Release package executed. Fresh APK SHA-256 is `641c6533e78a5977f2d8de97f293be236976e1053b40ff3a05a182bc594a1756` at 45,030,130 B with two valid DEX files. The authoritative 725-rule checker exited 0 / `RESULT=PASS`: critical old refs/defs `0/4`, hidden refs `4/4`, hidden defs `0/4`, aggregate hidden target definitions 0. Worktree and final process census are clean. Cleanup command 1 self-matched its inline shell and lost its exit code after executing once; commands 2/3 each executed once with exits `1/1`. Evidence: `/tmp/task097-c5-release-build-static/`.
