# Task 079 — C5 JarJar E1–E4 bounded experiments

**Phase**: C5 blocker evidence closure
**Status**: dispatched; initial preflight correctly blocked on a brief count typo, then Chief corrected the frozen RSP total to 464 tokens (463 `.jar` + 1 `.srcjar`) without changing scope
**Authority**: `self-commit` — worker may commit only Allowed Paths and must never push
**Reports To**: Chief architect in the current herdr workspace

## Goal

Produce every evidence input required to adjudicate the pre-R8 JarJar implementation seam, with zero project behavior change: complete the 464-entry stock R8 variant/ownership inventory (463 JARs plus one source JAR), dry-run affected AAR and project/JVM artifacts in scratch, and prove or disprove SysUISdk hidden-name resolution through a standalone AGP 9.3.1 bundled-R8 positive/negative probe. Do not implement the rewrite.

## Required reading

1. `AGENTS.md`
2. `docs/orchestration/CHARTER.md`
3. `docs/issues/2026-09-01-c5-jarjar-e1-e4.md`
4. `docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md`, especially §§2.3, 4.1, 4.5, and 5
5. `docs/issues/2026-09-01-c5-aconfig-jarjar-closure.md`
6. `tools/check_aconfig_jarjar_references.py` and its tests

## Frozen inputs

- Dispatch base: record exact `git rev-parse HEAD` in the issue before experimentation.
- Stock R8 input list:
  `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI/android_common/withres/SystemUI.jar.rsp`
  (expected 464 shell tokens: exactly 463 `.jar` entries and one `.srcjar` entry, `SystemUI-flag-types.srcjar`).
- JarJar rules:
  `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`
  (expected 725 exact rules / 726 physical lines / SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`).
- Host JarJar:
  `/home/conv/myspace/aosp/out/host/linux-x86/framework/jarjar.jar`.
- AGP bundled R8:
  `/home/conv/.gradle/caches/modules-2/files-2.1/com.android.tools.build/builder/9.3.1/9cd910fdf4b695abce90ed6a07b6dd348541fc7a/builder-9.3.1.jar`
  (expected `R8 9.3.16`, build `65eb2ed…`).
- Positive library:
  `/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar`.
- Negative-control library:
  `/home/conv/Android/Sdk/platforms/android-37.0/android.jar`.
- Current Release comparator:
  `/home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk`.
- Stock comparator:
  `/home/conv/myspace/aosp/out/target/product/emu64x/system_ext/priv-app/SystemUI/SystemUI.apk`.
- Scratch root, exclusively:
  `/tmp/task079-c5-jarjar-e1-e4/`.

All frozen inputs are read-only. If an input is absent or its frozen count/hash/version differs, stop before interpreting the experiment and report `BLOCKED` to Chief; do not rebuild it.

## Global constraints

- Same checkout and serial execution. No other worker is authorized to mutate this checkout.
- **Never run Gradle, Soong/Ninja, `m`, lunch, emulator, or ADB.** Direct `java -jar .../jarjar.jar process ...` in scratch and direct `java -cp builder-9.3.1.jar com.android.tools.r8.R8 ...` are the only build-like commands authorized.
- Do not write `/home/conv/myspace/aosp/**`, including `out/`; copy inputs into scratch first when a tool needs an output-side path.
- Do not write `app/build/**`, any module `build/**`, `libs/**`, or either SDK platform.
- No stub, platform-class packaging, `dontwarn`, ProGuard suppression, source import rewrite, source/resource/manifest edit, or behavior-changing Gradle wiring.
- Do not modify the Task 078 checker or weaken its semantics. The new tool may import/reuse it.
- Python must run via `uv run`; scripts under `tools/` must be Python.
- Scratch AAR/JAR/DEX/log/JSON/CSV and probe artifacts must never be added to git.
- Stage files with explicit Allowed Path names only. **`git add -A` and `git add .` are forbidden.**
- A failed E2/E3 candidate condition is valid experimental evidence: do not patch around it. Record the exact artifact and continue independent experiments where safe. Do not select a fallback architecture.

## Allowed Paths

Exactly these five paths:

1. `tools/analyze_aconfig_jarjar_experiments.py` — new, read-only analysis/scratch experiment driver
2. `tools/tests/test_analyze_aconfig_jarjar_experiments.py` — new focused tests
3. `docs/issues/2026-09-01-c5-jarjar-e1-e4.md` — experiment journal and actual outputs
4. `docs/architecture/2026-09-01-c5-jarjar-e1-e4.md` — new complete inventory/experiment report
5. `docs/orchestration/tasks/079-c5-jarjar-e1-e4-experiments.md` — this brief, checkbox/evidence updates only

## Forbidden Paths

- `tools/check_aconfig_jarjar_references.py` and its existing tests
- all `*.gradle*`, `settings.gradle.kts`, `gradle.properties`, and version catalogs
- `libs/**`, `app/proguard*.flags`, `app/build/**`, and every module `build/**`
- all `SystemUI-*/src/**`, `SystemUI-*/res*/**`, manifests, generated sources, and AOSP-mirrored files
- SDK files, `AGENTS.md`, `docs/adr/**`, `docs/orchestration/CHARTER.md`, `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, and `docs/PLAN.md`
- all writes under `/home/conv/myspace/aosp/**`
- any implementation of the selected rewrite

## File map

| Path | Responsibility |
|---|---|
| `tools/analyze_aconfig_jarjar_experiments.py` | Parse/classify RSP inputs, inspect JAR/AAR/class references and definitions, prepare scratch packages, invoke the frozen JarJar/R8 tools, and print stable machine-checkable summaries |
| `tools/tests/test_analyze_aconfig_jarjar_experiments.py` | Synthetic tests for RSP tokenization, archive/class inspection, ownership preconditions, AAR invariants, and positive/negative result interpretation |
| `docs/architecture/2026-09-01-c5-jarjar-e1-e4.md` | Complete 464-row inventory or lossless equivalent (463 JARs + 1 source JAR), 17-module classification, E2/E3 matrices, E4 commands/diagnostics, and final candidate verdict |
| `docs/issues/2026-09-01-c5-jarjar-e1-e4.md` | Chronological commands, actual outputs, deviations, and unresolved questions |
| this brief | Contract and checked execution record |

## Work plan

### P0 — Preconditions and reproducible driver

- [ ] Record dispatch base and prove all frozen input paths, rule hash/count, RSP token count, R8 version, and scratch isolation before running E1–E4.
- [ ] Add focused failing tests first, then implement a stdlib-only Python driver. It must never infer success from filename alone when archive contents are inspectable.
- [ ] Make the driver emit stable summary keys including `RULES`, `RSP_INPUTS`, `RSP_CLASSIFIED`, `RSP_UNKNOWN`, `RSP_JARS`, `RSP_SRCJARS`, `GRADLE_MODULES`, `GRADLE_MODULES_CLASSIFIED`, `E1`, `E2`, `E3`, `E4_POSITIVE`, `E4_NEGATIVE`, `CANDIDATE`, and `EXPERIMENTS_COMPLETE`.

### P1 — E1 complete variant/ownership inventory

- [ ] Parse every RSP shell token in original order; preserve duplicates as separate rows and report unique-path count separately.
- [ ] For all 464 rows (463 `.jar` + 1 `.srcjar`), record path, inferred Soong owner with evidence, ordinary versus `repackaged-jarjar` variant, archive SHA-256, rule-source/rule-target references and definitions, Gradle counterpart or a reasoned no-counterpart category, and E2/E3 disposition. No sampling and no `UNKNOWN` are allowed.
- [ ] Trace the exact Soong decision that selects ordinary versus repackaged variants. Clearly separate direct source evidence from path/content inference.
- [ ] Classify all 17 Gradle modules as Android class-producing, JVM class-producing, res-only, source-empty app, or other evidenced category. Freeze every existing Release local-output path used by E3 with size/SHA; distinguish local PROJECT output from merged/external dependencies.
- [ ] Produce the exact affected-AAR list and exact affected project/JVM output list. Do not invent implementation Allowed Paths or coordinates beyond what E1 proves.

E1 completeness gate: `RSP_INPUTS=464`, `RSP_CLASSIFIED=464`, `RSP_UNKNOWN=0`, `GRADLE_MODULES=17`, `GRADLE_MODULES_CLASSIFIED=17`, and no unclassified affected artifact. The report must additionally prove the expected composition `RSP_JARS=463` and `RSP_SRCJARS=1`.

### P2 — E2 affected-AAR scratch dry-run

- [ ] For every AAR selected by E1, construct a scratch candidate from existing AOSP `repackaged-jarjar` outputs. Record every source archive and why it matches the current AAR ownership closure.
- [ ] Compare current versus scratch AAR: all non-code entries byte-identical, class entry-name sets equal, and no unexplained class addition/removal.
- [ ] Scan all embedded code containers. Require every critical original reference relevant to that AAR to disappear, corresponding hidden references to appear, and all 725 hidden target definition counts to remain zero.
- [ ] Report a complete E2 matrix; selected count must equal covered count. A missing repackaged input or invariant failure sets `E2=FAIL` and `CANDIDATE=FAIL`, never a silent skip.

### P3 — E3 project/JVM output scratch JarJar dry-run

- [ ] Build scratch JARs only from existing per-module local javac/Kotlin outputs identified by E1; never include external/merged dependency classes.
- [ ] Inventory every module, including no-op/res-only/source-empty/JVM handling. For each candidate artifact, assert before transformation that definitions matching any of the 725 source names equal zero.
- [ ] If a candidate artifact has a matching source definition, do not transform that artifact. Record `E3=FAIL`, identify the owner, continue only independent safe experiments, and leave architecture adjudication to Chief/user.
- [ ] For each safe affected artifact, run the frozen host JarJar in scratch, capture wall time, and verify: each pre-existing source reference maps to its target; matching source references become zero; all 725 target definitions remain zero; unrelated class entry-name sets remain unchanged.
- [ ] Report selected/covered/no-op counts and per-artifact timing. Any omission or invariant failure sets `E3=FAIL` and `CANDIDATE=FAIL`.

### P4 — E4 standalone R8 positive and negative controls

- [ ] Generate a scratch-only valid program JAR defining one probe class whose field/signature types reference exactly the four critical hidden targets and which defines none of them. Do not add Java/Kotlin source or class files to the repository.
- [ ] Pre-scan the program JAR: all four hidden targets referenced, zero target definitions, zero critical original references.
- [ ] Positive command must directly invoke `com.android.tools.r8.R8` with exactly the frozen R8 JAR, `--release --no-tree-shaking --no-minification --no-desugaring`, SysUISdk `android.jar` as `--lib`, a scratch output, and the scratch program. Do not use `--pg-conf` or warning suppression.
- [ ] Positive gate: exit 0; stderr contains no missing-class diagnostic; output DEX retains all four hidden target references; all 725 target definitions are zero.
- [ ] Negative command is identical except official `android-37.0/android.jar` is `--lib`. Gate: nonzero exit and missing-class diagnostics identify all four hidden targets. A negative control that exits 0 is `E4_NEGATIVE=FAIL`; do not reinterpret it as success.
- [ ] Record exact commands, R8 version, exit codes, diagnostic excerpts, output hashes, and descriptor scan results.

### P5 — Synthesis, invariance gates, and commit

- [ ] Write the architecture report with complete E1 inventory, E2/E3 matrices, E4 positive/negative evidence, direct-observation versus inference labels, and exactly one verdict: `CANDIDATE=PASS`, `CANDIDATE=FAIL`, or `CANDIDATE=BLOCKED`.
- [ ] If PASS, list the evidence-derived implementation seam/module/artifact inputs for a future brief but do not implement it. If FAIL/BLOCKED, state which assumption failed and which user decision is required; do not propose a hidden workaround.
- [ ] Re-run Task 078 tests and both real-APK gates. Release must remain exit 1 `RESULT=FAIL`; stock must remain exit 0 `RESULT=PASS`, proving zero behavior change.
- [ ] Verify no files outside Allowed Paths changed and no scratch artifacts are tracked.
- [ ] Update the issue and this brief with actual results, commit only explicit Allowed Paths with an English message, never push, and finish with the CHARTER four-part report plus terminal `HANDOFF:` block.

## Chief correction after initial preflight

The initial worker preflight at dispatch base `e87f29d23a76004d8a262367f58c841b456d5492` stopped exactly as required because this brief said 463 shell tokens while `shlex.split` and `wc -w` both showed 464. Chief independently verified that the list is 464 unique tokens composed of exactly 463 `.jar` entries plus one `.srcjar`, `out/soong/.intermediates/frameworks/base/packages/SystemUI/shared/SystemUI-flag-types/android_common/SystemUI-flag-types.srcjar`. Thus Task 078's 463 figure was the JAR-only count and this brief had mislabeled it as the total token count. The frozen rule hash/count remained unchanged. This correction preserves the approved requirement to classify every RSP input without sampling; it does not expand behavior-change authority. The worker may resume from the same clean checkout after re-reading this corrected contract.

## Acceptance

### A. Focused tests

```bash
uv run pytest \
  tools/tests/test_analyze_aconfig_jarjar_experiments.py \
  tools/tests/test_check_aconfig_jarjar_references.py -q
```

Expected: all tests pass.

### B. Full E1–E4 replay

```bash
rm -rf /tmp/task079-c5-jarjar-e1-e4
uv run python tools/analyze_aconfig_jarjar_experiments.py run \
  --repo-root /home/conv/myspace/SystemUI-Gradle \
  --aosp-root /home/conv/myspace/aosp \
  --sysui-sdk /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar \
  --base-sdk /home/conv/Android/Sdk/platforms/android-37.0/android.jar \
  --r8-jar /home/conv/.gradle/caches/modules-2/files-2.1/com.android.tools.build/builder/9.3.1/9cd910fdf4b695abce90ed6a07b6dd348541fc7a/builder-9.3.1.jar \
  --scratch /tmp/task079-c5-jarjar-e1-e4
```

Expected candidate result:

```text
RULES=725
RSP_INPUTS=464
RSP_CLASSIFIED=464
RSP_UNKNOWN=0
RSP_JARS=463
RSP_SRCJARS=1
GRADLE_MODULES=17
GRADLE_MODULES_CLASSIFIED=17
E1=PASS
E2=PASS
E3=PASS
E4_POSITIVE=PASS
E4_NEGATIVE=PASS
CANDIDATE=PASS
EXPERIMENTS_COMPLETE=PASS
```

An experimentally proven E2/E3 failure is not permission to weaken the gate. The worker may complete the evidence task with `EXPERIMENTS_COMPLETE=PASS` and `CANDIDATE=FAIL`, but must report the exact failed invariant and must not implement or select a fallback. Missing/unclassified inputs produce `EXPERIMENTS_COMPLETE=FAIL`/`BLOCKED`.

### C. Frozen APK comparators

```bash
set +e
RULES=/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
uv run python tools/check_aconfig_jarjar_references.py \
  --apk /home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk \
  --rules "$RULES"
release_rc=$?
uv run python tools/check_aconfig_jarjar_references.py \
  --apk /home/conv/myspace/aosp/out/target/product/emu64x/system_ext/priv-app/SystemUI/SystemUI.apk \
  --rules "$RULES"
stock_rc=$?
printf 'RELEASE_RC=%s STOCK_RC=%s\n' "$release_rc" "$stock_rc"
test "$release_rc" -eq 1 && test "$stock_rc" -eq 0
```

Expected: Release `RESULT=FAIL`, stock `RESULT=PASS`, final line `RELEASE_RC=1 STOCK_RC=0`.

### D. Scope, scratch, and formatting

```bash
git diff --check <dispatch-base>..HEAD
git diff --name-only <dispatch-base>..HEAD
find /tmp/task079-c5-jarjar-e1-e4 -type f | wc -l
git status --short
```

Expected: clean diff check; diff contains exactly the five Allowed Paths; scratch contains the replay evidence but no scratch path is tracked; worktree clean after the worker commit.
