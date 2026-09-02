# Task 096 — C5 fresh Debug APK build/static gate

## Goal

在Task 095 review-PASS production seam上执行一次fresh `:app:assembleDebug`，产出可证明为本次构建生成的Debug APK，并静态验证四条runtime-critical hidden mappings全部落入DEX、全规则hidden target definitions为0且无非法critical old-name caller。

## Authority

本任务是**no-fix、只构建/只读、零tracked写入**的shared-checkout串行worker，reports to Chief。

May：读取owner文档与tracked源码；在唯一scratch root写证据；删除构建前的stale generated Debug APK；运行唯一Gradle wrapper命令；读取build outputs；运行`sha256sum`、`unzip`、`uv run python` checker及SDK 37 `dexdump`；按冻结block停止Gradle/Kotlin daemons；报告结果。

May NOT：修改/创建/删除任何tracked文件；运行第二个Gradle wrapper命令；运行Release/R8/clean；运行ADB/emulator/device或Soong/Ninja；修改AOSP/SDK/libs/source/res/build logic/checker；创建脚本；直接调用`python`/`python3`；commit/push；恢复Task 079；把局部结果声明为Release/runtime成功。

## Required startup — exact order

必须使用独立read调用并等待每一步完成：

1. 完整读取`AGENTS.md`。
2. 完整读取`docs/HANDOFF.md`。
3. 完整读取`docs/orchestration/CHARTER.md`。
4. 完整读取`docs/orchestration/STATE.md`。
5. 读取`docs/orchestration/log.md`尾部。
6. 完整读取本brief。
7. 完整读取`docs/issues/2026-09-02-c5-debug-build-static-gate.md`。
8. 读取mandatory source：
   - `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
   - `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewriteFactory.kt`
   - `tools/check_aconfig_jarjar_references.py`
9. 输出唯一`CONTRACT:`，必须写明：shared checkout、Reports To Chief、唯一Gradle命令、allowed/forbidden writes、失败即停、无tracked edits/commit/push、PASS边界。Chief明确接受前不得创建scratch、删除APK、运行preflight或执行任何命令。

## Frozen identity and paths

- Required production ancestor: `2994fa8f391233cdbc6bbfb7b121bf08c0d74f35`
- Dispatch base: require `HEAD == origin/main`; record the actual planning/dispatch commit in preflight evidence
- Branch: `main`
- Scratch root only: `/tmp/task096-c5-debug-build-static/**`
- Candidate APK: `app/build/outputs/apk/debug/app-debug.apk`
- Rules: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`
- DEX tool: `/home/conv/Android/Sdk/build-tools/37.0.0/dexdump`

## Procedure

### 1. Read-only preflight

After Chief accepts CONTRACT:

- Confirm `HERDR_ENV=1`.
- Confirm `HEAD == origin/main` and that frozen production commit `2994fa8f391233cdbc6bbfb7b121bf08c0d74f35` is an ancestor of `HEAD`.
- Confirm `git status --short --untracked-files=all` is empty.
- Use bracket-safe process census that cannot self-match. If any Gradle/Kotlin/Soong/Ninja process is active, stop and report; do not kill it.
- Confirm rules parse as exactly 725 entries, frozen critical rules are 4 lines, and allowlist is 166 lines. Python, if used, must be `uv run python`; shell line counts are preferred.
- Create the scratch root only after all checks pass; save preflight evidence.

### 2. Make stale success impossible

Record whether the candidate APK exists and its prior size/SHA/mtime, then remove only:

```bash
rm -f app/build/outputs/apk/debug/app-debug.apk
```

Confirm it is absent. Do not delete any tracked input or other build output.

### 3. Sole Gradle invocation

Run exactly once, with pipeline exit preserved:

```bash
set -o pipefail
./gradlew :app:assembleDebug --console=plain --rerun-tasks --max-workers=4 \
  2>&1 | tee /tmp/task096-c5-debug-build-static/assemble-debug.log
rc=${PIPESTATUS[0]}
printf '%s\n' "$rc" > /tmp/task096-c5-debug-build-static/assemble-debug.exit
```

No other Gradle wrapper invocation is authorized. If exit is nonzero or log lacks`BUILD SUCCESSFUL`, skip all APK acceptance scans, run final status/cleanup once, and report the first actionable failure without attempting a fix.

### 4. APK identity and ZIP gate

Only after successful build:

- Require candidate APK exists and is nonempty.
- Record `stat`, byte size and SHA-256.
- Run `unzip -t` and save full output/exit. ZIP gate requires exit 0.
- Record all `classes*.dex` entries.

### 5. Authoritative checker

Run exactly:

```bash
set -o pipefail
uv run python tools/check_aconfig_jarjar_references.py \
  --apk app/build/outputs/apk/debug/app-debug.apk \
  --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt \
  2>&1 | tee /tmp/task096-c5-debug-build-static/checker.log
checker_rc=${PIPESTATUS[0]}
printf '%s\n' "$checker_rc" > /tmp/task096-c5-debug-build-static/checker.exit
```

Checker exit 1 does not automatically fail Debug because legal old definitions/self-references remain. Acceptance requires its evidence to show all four critical hidden targets referenced and zero hidden target definitions across all 725 rules. Exit 2 is always FAIL.

### 6. Old-owner residual gate

Extract only `classes*.dex` from the candidate APK under scratch. For each of the four old descriptors, stream every extracted DEX through SDK 37 `dexdump -d`; use `awk` to retain the most recent `Class descriptor` line and print that class context together with every line containing the old descriptor. Save the complete outputs and command exits. Do not create a repository script and do not use `apkanalyzer` (known OOM on this APK class).

Critical old descriptors:

```text
Landroid/app/Flags;
Landroid/os/Flags;
Landroid/view/accessibility/Flags;
Lcom/android/window/flags/Flags;
```

PASS permits each descriptor only under its same current class context, representing the preserved source definition/current-class self-reference. Any occurrence while the current `Class descriptor` is another class is an illegal residual and fails this task. Ordinary string values are outside this descriptor-line gate and reference-only semantics leave them unchanged.

### 7. Final status and one cleanup block

Record `git status --short --untracked-files=all`; tracked/untracked repository state must remain empty. Then execute each cleanup command once, immediately saving each exit code. Use bracket-safe patterns; do not rerun if output is lost. Record a final bracket-safe census. Cleanup evidence deviations must be disclosed independently of technical PASS/FAIL.

## Acceptance

PASS requires all of:

- Sole Gradle invocation exit 0 and `BUILD SUCCESSFUL`.
- Fresh candidate APK exists, nonempty, SHA/size/mtime captured, ZIP test exit 0.
- Critical hidden references `4/4`.
- Hidden target definitions across 725 rules `0`.
- Old-owner residual gate finds no descriptor occurrence under a different current class.
- Checker exit is not 2; exit 1 is accepted only for legal Debug definitions/self-references.
- Repository status remains clean; no forbidden action occurred; final process census is empty.

PASS does **not** claim Release/R8, deployment, runtime, reboot stability, or Task 079 completion.

## Report format

```text
STATUS: PASS|FAIL|BLOCKED_PREFLIGHT
BASE=
HERDR_ENV=
GRADLE_INVOCATIONS=
GRADLE_EXIT=
BUILD_RESULT=
APK_PATH=
APK_SIZE=
APK_SHA256=
ZIP_TEST=
DEX_ENTRIES=
CRITICAL_HIDDEN_REFERENCES=/4
HIDDEN_TARGET_DEFINITIONS=
OLD_OWNER_RESIDUAL_GATE=PASS|FAIL|NOT_RUN
CHECKER_EXIT=
TRACKED_WORKTREE=
CLEANUP_EXITS=
FINAL_PROCESS_CENSUS=
FORBIDDEN_ACTIONS=NONE|...
EVIDENCE=
NEXT=Chief records result; Release build/static remains separate
```

End with a concise `HANDOFF:` block and wait. Do not commit or push.

## Outcome

**PASS** on dispatch base `69d332f4104ada726ed16f3d5e46a8bb9d551fc1`. The sole Gradle invocation exited 0 with `BUILD SUCCESSFUL in 3m 55s` and produced a 190,547,804-byte Debug APK, SHA-256 `f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`; ZIP test passed over 13 DEX files. Checker exit 1 was accepted only after proving critical hidden references `4/4`, all-725 hidden target definitions `0`, and no old descriptor outside its same-class definition/self-reference context via SDK 37 `dexdump`. Final worktree and Chief process census were clean; cleanup exits were `0/0/1`.

The worker additionally ran one unnecessary read-only `git fetch --all --quiet`, updating `.git/FETCH_HEAD` only. This disclosed procedural deviation did not alter `HEAD`, `origin/main`, tracked files, APK evidence, or technical PASS. No Release, device, fix, second Gradle invocation, or Task 079 action occurred. Full result: `docs/issues/2026-09-02-c5-debug-build-static-gate.md`; scratch: `/tmp/task096-c5-debug-build-static/`.
