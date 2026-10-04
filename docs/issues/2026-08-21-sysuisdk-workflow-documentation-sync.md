# 2026-08-21 — SysUISdk workflow documentation sync

## Status

Executed 2026-08-21 (Task 046, worker worktree `SystemUI-Gradle-wt-046`, branch
`task-046-sysuisdk-workflow-docs`). All verification gates passed; evidence below.
This task was factual documentation synchronization only; it did not change SysUISdk
generation or Gradle behavior.

## Background

The single-entry generator is now the only supported SysUISdk workflow:

```bash
python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp
```

Task 045 retired `tools/install_sdk.py`, staged S0–S5 operation, `--apply`, live SDK
patching, and permanent backup creation. Several rule, README, Gradle-comment, and ADR
texts still describe that retired mechanism. The user explicitly authorized correcting
those H.6 paths on 2026-08-21.

The user also required that public READMEs remain user-facing: internal development
identifiers such as task numbers, S0–S5 labels, rule-letter/ADR-number shorthand, CONV,
packet names, Worker/REDLINE terminology, commit IDs, internal missing-reference batch
codes, or orchestration details must not appear there. Implementation-only symbol names
such as the former final R8 missing class must be summarized by outcome instead.

## Approved scope

- `AGENTS.md`: factual SysUISdk generation references and ADR index/history.
- `README.md`, `README.en.md`: public status, supported command, prerequisites, current
  test/Debug/Release state, and runtime-validation wording.
- `SystemUI-core/build.gradle.kts`: two comments that name the deleted installer.
- `docs/adr/0006-sysuisdk-r8-library-class-bridge.md`: preserve the architectural
  decision and history while marking the composition mechanism amended by the
  single-entry generator.
- This issue, its plan, and exact task brief.

No source, resources, dependency, version, module, Gradle behavior, generator code,
R8 rule, or external SDK content may change.

## Baseline capture (2026-08-21, pre-edit)

`rg -n -C 2 'install_sdk|--apply|S[0-5]|Task 0|AssumeTrueForR8|233|195' AGENTS.md README.md README.en.md SystemUI-core/build.gradle.kts docs/adr/0006-sysuisdk-r8-library-class-bridge.md` — stale active-workflow/status hits:

- `AGENTS.md` L122（§1.7）：“（由 `tools/install_sdk.py` 幂等完成）”；L124 生成方法参考仍指向旧补丁流程；L209（§2.4）：“`tools/install_sdk.py` 当前负责此项”；L402（§7 工具表）：`tools/install_sdk.py` 整行。
- `README.md` L33：“`tools/build_sysuisdk.py --apply` 声明式生成”；L35：“233 个全部通过”；L37：R8 收敛至 1、仅剩 `AssumeTrueForR8`；L51：“Task 041 … 仅处理 `AssumeTrueForR8`”；L100：“由 `tools/install_sdk.py` / `build_sysuisdk.py` 生成”；L108：“195 个”。
- `README.en.md` L37/L39/L41/L66/L123/L131：同上英文版（含 `--apply`、233、Task 041、`AssumeTrueForR8`、`tools/install_sdk.py`）。
- `SystemUI-core/build.gradle.kts` L55、L337：两处注释引用 `tools/install_sdk.py`（仅注释，无 DSL 改动）。
- `docs/adr/0006-sysuisdk-r8-library-class-bridge.md` L36–39：决策 2/3 仍要求 staged pipeline + `--apply --source <staging>` + S5 staging/live 校验 + 备份；L55：回滚方式仍为 `build_sysuisdk.py --apply`。

Unrelated historical records (e.g. AGENTS.md Task 026/034/039 mentions, ADR background task
numbers) were left untouched.

## Steps

1. Capture every stale active-workflow reference in the approved files. ✅（上方 Baseline capture）
2. Replace it with the single-entry, read-only-base, transactional owned-output model. ✅
3. Keep historical implementation identifiers out of both public READMEs. ✅
4. Run static wording/scope gates and the full Python suite; do not run Gradle. ✅
5. Record actual results and commit in English without pushing. ✅

## Execution evidence (2026-08-21)

- Baseline capture: see “Baseline capture” above (rg hit list copied pre-edit).
- README hygiene gate: `python3 - <<'PY' ... PY` → `README_PUBLIC_HYGIENE=PASS` (no task
  numbers, stage labels, rule/ADR shorthand, CONV, packets, Worker/REDLINE, orchestration,
  commit IDs, or the former missing-class name; `--apply` and the retired installer absent;
  `220` present in both READMEs).
- Active workflow references: `rg -n 'tools/install_sdk\.py|build_sysuisdk\.py --apply'
  AGENTS.md README.md README.en.md SystemUI-core/build.gradle.kts` → no matches (exit 1).
  One intermediate hit (AGENTS.md history row naming the retired script) was reworded to
  “旧 SDK 补丁脚本已退役” so the gate is clean.
- `python3 tools/build_sysuisdk.py --help` → single-entry CLI only: required `--aosp-root`,
  optional `--sdk-root` / `--base-platform` / `--output` / `--replace`; no legacy option.
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 220 tests in 69.555s`
  / `OK`.
- `git diff --check` → exit 0 (no whitespace errors).
- `git status --short` / `git diff --name-only` → only Allowed Paths changed:
  AGENTS.md, README.md, README.en.md, SystemUI-core/build.gradle.kts,
  docs/adr/0006-sysuisdk-r8-library-class-bridge.md, this issue, the plan, and the task
  brief. `SystemUI-core/build.gradle.kts` diff consists exclusively of two comment lines
  (installer name → generator name); no DSL change.
- Gradle: not run (documentation-only task).

### Wording judgments

- Both READMEs now state outcome-oriented status: 220/220 toolchain tests, Debug hard gate
  green, optimized Release (R8 + resource shrinking + V2 signing) green with 0 missing R8
  references, on-device runtime validation pending.
- The R8 trajectory listing was replaced with “140 → 0” outcome wording to keep the public
  README free of internal closure-batch detail.
- AGENTS.md §2.4 keeps rule semantics unchanged; only the mechanism facts (single-entry
  generator, read-only base, marker/ownership, `--replace`) replace the retired patch
  workflow, and the supported command is shown verbatim.
- ADR 0006 keeps its original background/alternatives; the staged/S0–S5/`--apply`/backup
  mechanism moved verbatim-faithful into an explicit “历史修订记录（已被取代，仅存档）”
  note; the current decision states the frozen eight-input map, 39-entry bridge, read-only
  base, sibling staging + generator ownership, marker-gated `--replace`, and the
  release-only adapter for the former final missing class.

## Error-count evolution

Not applicable: this is documentation/comment synchronization and must not change the
build graph. Build error counts are not measured. Python test count is recorded only as
a regression gate.

## Open questions

None for the approved factual scope. Any policy change beyond replacing stale workflow
facts is a REDLINE and requires separate user approval.
