# SysUISdk Workflow Documentation Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this documentation plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every active project-facing SysUISdk instruction describe the supported single-entry generator while keeping public READMEs free of internal development identifiers.

**Architecture:** Change documentation and comments only. Preserve historical context in the ADR, but clearly distinguish the superseded staged/live-patch mechanism from the current read-only-base, transactional, generator-owned output model.

**Tech Stack:** Markdown, Kotlin DSL comments, Python unittest/static text checks.

**Spec:** `docs/issues/2026-08-21-sysuisdk-workflow-documentation-sync.md`

## Global Constraints

- Supported command: `python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp`.
- Do not describe `tools/install_sdk.py`, S0–S5, `--apply`, live patching, or permanent backups as active workflows.
- `README.md` and `README.en.md` are public user documentation: no task numbers,
  stage labels, rule-letter/ADR-number shorthand, CONV, packets, Worker/REDLINE,
  orchestration/reviewer details, commit IDs, internal closure batch codes, or the former
  implementation-only missing-class name.
- Public status must be outcome-oriented: 220 Python tests, Debug and optimized Release build, R8 missing refs zero, runtime validation pending.
- Preserve ADR history; mark the composition mechanism as amended rather than pretending the earlier decision never existed.
- No source/resource, dependency, version, module, Gradle behavior, generator, R8 rule, or external SDK change.
- No Gradle task. Worker commits in English and never pushes.

---

## File map

- Modify: `AGENTS.md` — factual rule/index/tool references only.
- Modify: `README.md` — Chinese public workflow and status.
- Modify: `README.en.md` — English public workflow and status.
- Modify: `SystemUI-core/build.gradle.kts` — two comments only.
- Modify: `docs/adr/0006-sysuisdk-r8-library-class-bridge.md` — amended mechanism and historical consequences.
- Modify: `docs/issues/2026-08-21-sysuisdk-workflow-documentation-sync.md` — actual evidence.
- Modify: this plan and `docs/orchestration/tasks/046-sysuisdk-workflow-documentation-sync.md` — checkbox/evidence state.

## Task 1: Capture the stale-reference baseline

- [ ] **Step 1: Record exact stale references**

Run:

```bash
rg -n -C 2 'install_sdk|--apply|S[0-5]|Task 0|AssumeTrueForR8|233|195' \
  AGENTS.md README.md README.en.md SystemUI-core/build.gradle.kts \
  docs/adr/0006-sysuisdk-r8-library-class-bridge.md
```

Expected: stale active-workflow/status references are present. Copy the relevant lines
into the issue before editing; do not reinterpret unrelated historical records.

## Task 2: Synchronize internal rule and decision documents

- [ ] **Step 1: Update AGENTS and Gradle comments**

Replace only the deleted-installer/staged-pipeline facts with the normal single-entry
command and source-derived AIDL/composition ownership. Keep rule F and §2.4 semantics
unchanged. Add a dated AGENTS history entry for this factual synchronization.

- [ ] **Step 2: Amend ADR 0006 without erasing history**

The current decision must state:

```text
one invocation consumes the frozen eight-input AOSP map
39 exact bridge entries enter both SDK target JARs
stock android-37.0 stays read-only
generation uses sibling staging and generator ownership
--replace accepts only a valid owned output
AssumeTrueForR8 remains outside SysUISdk and is handled by one exact release-only adapter
```

Move S0–S5/`--apply`/live-backup wording into an explicitly superseded historical note,
not the current decision or rollback instructions.

## Task 3: Rewrite the public README status without internal codenames

- [ ] **Step 1: Update Chinese README**

Describe the supported command, current 220-test/Debug/optimized-Release results, zero
R8 missing references, and pending device validation in user-facing terms. Replace
existing Task/rule/ADR/CONV and A/B closure shorthand with plain language. Do not name
internal stages, packets, workers, reviews, commits, red-line procedures, or the former
implementation-only missing class.

- [ ] **Step 2: Apply semantically equivalent English wording**

Keep the two READMEs aligned in facts, commands, and completion state; translation need
not be word-for-word.

## Task 4: Static and regression verification

- [ ] **Step 1: Verify public README hygiene**

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
```

Expected: `README_PUBLIC_HYGIENE=PASS`.

- [ ] **Step 2: Verify active workflow references**

```bash
! rg -n 'tools/install_sdk\.py|build_sysuisdk\.py --apply' \
  AGENTS.md README.md README.en.md SystemUI-core/build.gradle.kts
python3 tools/build_sysuisdk.py --help
```

Expected: grep produces no output; help shows required `--aosp-root` plus optional
`--sdk-root`, `--base-platform`, `--output`, and `--replace`, with no legacy option.

- [ ] **Step 3: Run regression and scope gates**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
git diff --check
git status --short
```

Expected: exit 0, `Ran 220 tests`, `OK`; no whitespace errors; only the File map paths
changed. No Gradle command is run.

- [ ] **Step 4: Record evidence and commit**

Update the issue with actual commands/results and any wording deviations. Commit in
English, never push, and finish with the required `HANDOFF:` block.
