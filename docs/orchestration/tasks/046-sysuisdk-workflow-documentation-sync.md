# Task 046: SysUISdk workflow documentation sync

> Orchestrated exact brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract. Worker commits but never pushes.

## Authority

`redline-gated`. On 2026-08-21 the user explicitly authorized factual H.6 updates to
`AGENTS.md` and ADR 0006 for the already-approved single-entry SysUISdk architecture.
The same approval covers the listed README and comment corrections. Any policy semantic
change beyond replacing stale workflow facts must stop with:

```text
REDLINE: Task 046 policy scope — <exact proposed semantic change and why factual synchronization is insufficient>
```

## Reports To

Chief architect in the main SystemUI-Gradle herdr pane. Commit locally; never push.

## Required reading and sub-skills

After worker-contract startup, read completely:

1. `docs/issues/2026-08-21-sysuisdk-workflow-documentation-sync.md`
2. `docs/superpowers/plans/2026-08-21-sysuisdk-workflow-documentation-sync.md`
3. `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`
4. `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`
5. `docs/adr/0006-sysuisdk-r8-library-class-bridge.md`
6. `docs/CURRENT_STATE.md`

Invoke `superpowers:executing-plans`. This is documentation/comment work; do not invent a
TDD production-code cycle and do not run Gradle.

## Goal

Synchronize active instructions with the sole supported command:

```bash
python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp
```

Preserve architecture/history while making both public READMEs understandable without
internal development identifiers.

## Allowed Paths

- `AGENTS.md` — only SysUISdk references at ADR index, §1.7, §2.4, tool table, and one dated history row.
- `README.md`
- `README.en.md`
- `SystemUI-core/build.gradle.kts` — comments naming `tools/install_sdk.py` only; no executable DSL change.
- `docs/adr/0006-sysuisdk-r8-library-class-bridge.md`
- `docs/issues/2026-08-21-sysuisdk-workflow-documentation-sync.md`
- `docs/superpowers/plans/2026-08-21-sysuisdk-workflow-documentation-sync.md`
- `docs/orchestration/tasks/046-sysuisdk-workflow-documentation-sync.md`
- `/tmp/task046-*` evidence only.

## Forbidden Paths

- `docs/orchestration/CHARTER.md`, `STATE.md`, `log.md`
- `docs/CURRENT_STATE.md`, `docs/HANDOFF.md`, `docs/PLAN.md`
- all source/resource/AIDL/manifest paths
- all executable Gradle DSL changes, settings/properties/version catalog
- `tools/**`, `libs/**`, SDK/AOSP content, R8 rules, dependencies, modules
- stubs, suppressions, source exclusions, build bypasses

## README hard clause

Both public READMEs must contain no internal task number, S0–S5 label,
rule-letter/ADR-number shorthand, CONV marker name, packet name,
Worker/REDLINE/orchestration/reviewer terminology, commit ID, internal closure batch
code, or the former implementation-only missing-class name. Describe only user-visible
capabilities, commands, limitations, and verification state. This user clause overrides
any temptation to copy `docs/CURRENT_STATE.md` verbatim.

## Execution

Follow every checkbox in
`docs/superpowers/plans/2026-08-21-sysuisdk-workflow-documentation-sync.md`.

## Acceptance

```bash
python3 - <<'PY'
from pathlib import Path
import re
pattern = re.compile(
    r'\bTask\s+\d{3}\b|\bS[0-5]\b|\bRule\s+[A-Z]\b|规则\s*[A-Z]\b|'
    r'\bADR\s+\d{4}\b|\bCONV\b|\bWorker\b|\bREDLINE\b|\bpacket\b|'
    r'orchestrat|\b[0-9a-f]{8,40}\b|AssumeTrueForR8',
    re.I,
)
for name in ('README.md', 'README.en.md'):
    text = Path(name).read_text()
    bad = pattern.findall(text)
    assert not bad, (name, bad)
    assert 'tools/install_sdk.py' not in text
    assert '--apply' not in text
    assert '220' in text
print('README_PUBLIC_HYGIENE=PASS')
PY
! rg -n 'tools/install_sdk\.py|build_sysuisdk\.py --apply' \
  AGENTS.md README.md README.en.md SystemUI-core/build.gradle.kts
python3 tools/build_sysuisdk.py --help
python3 -m unittest discover -s tools/tests -p 'test_*.py'
git diff --check
git status --short
```

Expected: hygiene PASS; both negative searches produce no output; help exposes only the
single-entry CLI; Python exit 0 with `Ran 220 tests` and `OK`; no whitespace errors; only
Allowed Paths changed; the Gradle file diff consists exclusively of comments. Gradle is
not run.

## Completion report

Provide one focused English commit, actual command results, a README internal-identifier
scan result, any wording judgment, and the required terminal-final `HANDOFF:` block.
