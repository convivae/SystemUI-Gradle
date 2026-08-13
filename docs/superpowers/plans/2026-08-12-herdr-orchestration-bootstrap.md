# Herdr Orchestration Bootstrap Implementation Plan

> **For agentic workers:** This plan is executed **inline by the architect session** (pi-subagent has been removed; subagent-driven-development is unavailable). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the herdr orchestration workflow (spec: `docs/superpowers/specs/2026-08-12-herdr-orchestration-design.md`): create `docs/orchestration/` (CHARTER/STATE/log/tasks), write the `orchestrator` and `worker-contract` pi skills, and validate the whole workflow with one real pilot task dispatched to a herdr worker pane.

**Architecture:** Files are the single source of truth for constraints and state; herdr CLI handles only pane/agent lifecycle. The pilot task (refresh `libs/SystemUI-tags.jar` from the AOSP Soong jar) is small, has a mechanical acceptance check (`javap`), and fixes one of the eight Task 7 javac root-cause groups.

**Tech Stack:** Markdown docs, pi skills (YAML frontmatter), herdr 0.8.0 CLI, git, `javap`, Python 3 unittest.

## Global Constraints

- Commit messages in English; commit after every task; push when the user asks or at plan completion (user preference: timely push — push at end of this plan).
- `docs/orchestration/` content must be derived from the spec `docs/superpowers/specs/2026-08-12-herdr-orchestration-design.md`, not invented.
- CHARTER rules cite AGENTS.md anchors; never copy full rule text (avoid dual-write drift).
- The two skills live at `~/.pi/agent/skills/` — **outside this repo**, so they are not committed here.
- herdr command syntax must be verified against the installed binary (`herdr <group> --help`) before first use; the binary is the syntax authority.
- No stubs, no `res/` changes, no build-check bypasses, no `@Suppress`. `tools/` scripts stay Python (none are added in this plan).
- Do not modify `AGENTS.md` or `docs/adr/` in this plan (red-line area; the post-pilot AGENTS.md index update is explicitly out of scope and needs user approval).
- The pilot task touches only `libs/SystemUI-tags.jar` + `docs/issues/` + `docs/orchestration/`; nothing else.

---

## File Map

| File | Responsibility |
|------|----------------|
| `docs/orchestration/CHARTER.md` | Full constraint charter (spec §3 Parts 1–8 materialized) |
| `docs/orchestration/STATE.md` | Live orchestration state (workers/queue/blocked) |
| `docs/orchestration/log.md` | Append-only event log |
| `docs/orchestration/tasks/001-refresh-systemui-tags-jar.md` | Pilot task brief |
| `~/.pi/agent/skills/worker-contract/SKILL.md` | Worker self-constraint protocol |
| `~/.pi/agent/skills/orchestrator/SKILL.md` | Architect operations manual |

---

### Task 1: Create `docs/orchestration/` skeleton (CHARTER, STATE, log)

**Files:**
- Create: `docs/orchestration/CHARTER.md`
- Create: `docs/orchestration/STATE.md`
- Create: `docs/orchestration/log.md`

**Interfaces:**
- Produces: the three files every later task (and every future session) reads. `CHARTER.md` section order must be exactly Part 1–8 as in spec §3.

- [ ] **Step 1: Write `docs/orchestration/CHARTER.md`**

Materialize spec §3 Parts 1–8 into a full document. Structure and required content (section headings verbatim; body expands each spec bullet into 1–3 sentences, citing the AGENTS.md/PITFALLS/ADR anchors listed in the spec — do not copy rule full text):

```markdown
# Orchestration Charter (CHARTER)

> Single source of truth for mandatory constraints in the herdr orchestration
> workflow. Re-read this file after any context compaction, before any action.
> Companion state file: docs/orchestration/STATE.md

## Part 1 · Project Identity and Rule Priority
## Part 2 · The Ten Mandatory Rules
## Part 3 · Dependency Three-Tier Decision Tree
## Part 4 · Toolchain Facts
## Part 5 · Red-Line Areas
## Part 6 · Current Project State Snapshot
## Part 7 · Worker Contract
## Part 8 · User Preference Hard Clauses
```

Part 2 must contain the ten-rule table from spec §3 Part 2 verbatim (columns: #, rule, one-line prohibition, source). Part 3 must contain the decision-tree code block and the static_libs warning from spec §3 Part 3. Part 5 must list all seven red-line areas from spec §3 Part 5. Part 6 must contain exactly the one-line conclusion + pointer style from spec §3 Part 6 (current: KSP 0 errors / core Kotlin 0 errors / `:app:assembleDebug` blocked by 42 javac errors, details in `docs/CURRENT_STATE.md` and `docs/issues/2026-08-12-current-progress-standards-review.md`). Part 7 must contain the five-step startup sequence and the four-part completion report from spec §3 Part 7, including these two exact output templates:

```text
CONTRACT:
- task: <brief path>
- goal: <one line>
- allowed_paths: [...]
- forbidden_paths: [...]
- acceptance: <command + expected output>
- authority: self-commit | redline-gated
```

```text
HANDOFF:
- done: <what was done>
- verified: <command> -> <actual output summary>
- remaining: <what is left, or "none">
```

- [ ] **Step 2: Write `docs/orchestration/STATE.md`**

Exact initial content:

```markdown
# Orchestration State

> The architect MUST re-read this file (with CHARTER.md and the tail of log.md)
> before every dispatch, review, or merge action.

## Active Workers

| Pane | Agent | Task brief | Worktree | Stage | Since |
|------|-------|-----------|----------|-------|-------|
| (none) | | | | | |

## Queue

1. (empty)

## Blocked

(none)

## Last Updated

2026-08-12 — architect session (bootstrap)
```

- [ ] **Step 3: Write `docs/orchestration/log.md`**

Exact initial content:

```markdown
# Orchestration Log

> Append-only. One line per event, newest at the bottom:
> `YYYY-MM-DD HH:MM | pane | task | event | detail`
> Events: dispatch, contract-ok, blocked, redline, review-pass, review-fail,
> merge, push, done, abort.

2026-08-12 | w2:p1 | bootstrap | dispatch | orchestration files initialized (Task 1)
```

- [ ] **Step 4: Verify structure**

```bash
ls docs/orchestration/ docs/orchestration/tasks/ 2>&1
grep -c '^## Part' docs/orchestration/CHARTER.md   # expect: 8
grep -c 'CONTRACT:' docs/orchestration/CHARTER.md  # expect: >=1
grep -c 'HANDOFF:' docs/orchestration/CHARTER.md   # expect: >=1
git diff --check                                    # expect: no output
```

Expected: CHARTER exists with 8 `## Part` headings; STATE and log exist; no whitespace errors. (`docs/orchestration/tasks/` may not exist yet — Task 4 creates it; `ls` error for it is acceptable here.)

- [ ] **Step 5: Commit**

```bash
git add docs/orchestration/
git commit -m "docs: initialize orchestration charter, state, and log"
```

---

### Task 2: Write `worker-contract` skill

**Files:**
- Create: `~/.pi/agent/skills/worker-contract/SKILL.md`

**Interfaces:**
- Consumes: `docs/orchestration/CHARTER.md` Part 5/7 (Task 1).
- Produces: skill name `worker-contract` that the architect references in dispatch prompts (Task 5).

- [ ] **Step 1: Write the skill file**

Frontmatter exactly:

```yaml
---
name: worker-contract
description: "SystemUI-Gradle herdr worker self-constraint protocol. Use when dispatched as a worker pane: mandates the reading sequence (AGENTS.md → CHARTER → task brief), CONTRACT: echo, red-line halt behavior, and the four-part completion report."
---
```

Body (~100 lines max), sections in this order:

1. `# Worker Contract` + one-line purpose.
2. `## Startup Sequence` — the five steps from CHARTER Part 7 verbatim (read AGENTS.md fully → read CHARTER.md → read own task brief → read brief-referenced issue/plan docs → print the `CONTRACT:` block). State explicitly: **do not write any code before the CONTRACT block is printed.**
3. `## CONTRACT Block` — the exact template from CHARTER Part 7.
4. `## During Work` — before every commit, re-check the diff against the brief's Allowed/Forbidden Paths (`git diff --name-only`); when unsure whether something is a red-line area, treat it as red-line (false positives are cheap); on build failure use the systematic-debugging skill, never trial-and-error edits.
5. `## Red-Line Halt` — when touching any CHARTER Part 5 area becomes necessary: stop, do not modify, print `REDLINE: <area> — <what you intended to do and why>`, then wait for the architect.
6. `## Completion Report` — the four parts from CHARTER Part 7 (English commit / brief checkboxes with real verification output / `docs/issues/` update / `HANDOFF:` block), including the exact `HANDOFF:` template.
7. `## Never Do` — one line each: no stubs; no `res/` edits; no `@Suppress`; no disabling javac/D8/KSP checks; no source exclusions to hide errors; no scope expansion beyond the brief.

- [ ] **Step 2: Validate the skill**

```bash
python3 - <<'EOF'
from pathlib import Path
p = Path.home() / '.pi/agent/skills/worker-contract/SKILL.md'
t = p.read_text()
assert t.startswith('---\nname: worker-contract'), 'frontmatter name'
assert 'description:' in t.split('---')[1], 'frontmatter description'
for s in ['Startup Sequence', 'CONTRACT', 'Red-Line Halt', 'Completion Report', 'Never Do', 'HANDOFF']:
    assert s in t, f'missing section: {s}'
lines = t.splitlines()
assert len(lines) <= 130, f'too long: {len(lines)} lines'
print('worker-contract skill OK,', len(lines), 'lines')
EOF
```

Expected: `worker-contract skill OK` with ≤130 lines.

- [ ] **Step 3: No repo commit**

The skill lives outside the repo. Nothing to commit; note the file path in `docs/orchestration/log.md` via Task 4's commit instead (keeps this task atomic).

---

### Task 3: Write `orchestrator` skill

**Files:**
- Create: `~/.pi/agent/skills/orchestrator/SKILL.md`

**Interfaces:**
- Consumes: spec §4 (lifecycle protocol), CHARTER (Task 1), `worker-contract` skill name (Task 2).
- Produces: skill name `orchestrator`; the architect's six-stage checklist used in Task 5.

- [ ] **Step 1: Write the skill file**

Frontmatter exactly:

```yaml
---
name: orchestrator
description: "Orchestrate herdr worker panes for SystemUI-Gradle. Use when acting as chief architect: decomposing goals into task briefs, dispatching workers, monitoring via herdr, reviewing output, merging. Loads the orchestration charter before any action."
---
```

Body (~150 lines max), sections in this order:

1. `# Orchestrator` + purpose.
2. `## Entry Checks` — `test "${HERDR_ENV:-}" = 1` (else stop and say not inside herdr); verify `docs/orchestration/CHARTER.md`, `STATE.md`, `log.md` exist.
3. `## Mandatory Re-Read` — before every dispatch/review/merge: read CHARTER.md, STATE.md, and the last 20 lines of log.md. This line must be near the top so it survives compaction.
4. `## Stage 0 – Decompose` — use superpowers writing-plans or Matt to-tickets; parallel only if no shared files AND no ordering dependency AND no state coupling, else serial; brief format = existing plan template plus the five extra fields (`Authority`, `Allowed Paths`, `Forbidden Paths`, `Acceptance`, `Reports To`); user approves briefs before dispatch.
5. `## Stage 1 – Dispatch` — command templates (verify flags against installed binary first): serial tasks use the current checkout; parallel tasks use `herdr worktree create`; then `herdr pane split`, `herdr agent start`, and `herdr agent prompt` with a prompt that only points at files and demands the `CONTRACT:` block, e.g.:

    ```text
    You are a worker. Invoke the worker-contract skill. Read in order:
    (1) AGENTS.md (2) docs/orchestration/CHARTER.md
    (3) docs/orchestration/tasks/NNN-<slug>.md
    Then print your CONTRACT: block and start work.
    ```

    Dispatch is confirmed only when `herdr agent read` shows the CONTRACT block.
6. `## Stage 2 – Monitor` — `herdr agent list` / `herdr agent wait --state blocked,idle` / `herdr agent read`; working → do not interrupt; blocked → read and classify (REDLINE → relay to user, wait for approval; in-brief problem → let worker debug; out-of-brief → escalate); `unknown` state → trust `agent read`, not the state.
7. `## Stage 3 – Review` — four checks in order: (a) `git log`/`git diff --name-only` for English focused commits and no Forbidden/red-line paths (violation = reject regardless of outcome); (b) personally re-run the brief's Acceptance command and compare real output; (c) `docs/issues/` updated and `git diff --check` clean; (d) no new stubs/res edits, and `python3 tools/check_source_alignment.py --strict` still reports MISSING/MISPLACED/EXTRA = 0 when the source tree was touched. Failures go back to the worker via `agent prompt` as a concrete issue list.
8. `## Stage 4 – Merge & Push` — serial: push after review; parallel: merge worktrees one at a time in dependency order, re-run acceptance after each; red-line diffs are shown to the user and pushed only after explicit user confirmation.
9. `## Stage 5 – Wrap-Up` — update STATE.md, append log.md, sync maintained docs (CURRENT_STATE etc.), `herdr pane close` or reuse the pane.
10. `## Failure Handling` — the four-row table from spec §4 (stuck worker / repeated failure / architect compaction / unknown state).
11. `## Red-Line Relay Template` — fixed format for reporting to the user: `REDLINE from <pane>: area=<area>; worker intended=<what>; my recommendation=<option>; awaiting your decision.`

- [ ] **Step 2: Validate the skill**

```bash
python3 - <<'EOF'
from pathlib import Path
p = Path.home() / '.pi/agent/skills/orchestrator/SKILL.md'
t = p.read_text()
assert t.startswith('---\nname: orchestrator'), 'frontmatter name'
for s in ['Entry Checks', 'Mandatory Re-Read', 'Stage 0', 'Stage 1', 'Stage 2',
          'Stage 3', 'Stage 4', 'Stage 5', 'Failure Handling', 'Red-Line Relay']:
    assert s in t, f'missing section: {s}'
lines = t.splitlines()
assert len(lines) <= 180, f'too long: {len(lines)} lines'
print('orchestrator skill OK,', len(lines), 'lines')
EOF
```

Expected: `orchestrator skill OK` with ≤180 lines.

- [ ] **Step 3: No repo commit** (skill outside repo; see Task 2 Step 3 note)

---

### Task 4: Write pilot task brief `001-refresh-systemui-tags-jar`

**Files:**
- Create: `docs/orchestration/tasks/001-refresh-systemui-tags-jar.md`

**Interfaces:**
- Consumes: CHARTER (Task 1); Task 7 root-cause evidence in `docs/issues/2026-08-12-current-progress-standards-review.md` (group 7: stale `SystemUI-tags.jar`).
- Produces: the brief dispatched to the pilot worker in Task 5.

- [ ] **Step 1: Verify the evidence is still true**

```bash
javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep -c writeSysuiKeyguard || echo 'absent in libs jar'
javap -classpath /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard
```

Expected: first command prints `0` (or "absent"); second prints the `writeSysuiKeyguard(int,int)` method. If the AOSP jar path is missing, stop and report — do not substitute another source.

- [ ] **Step 2: Write the brief**

Exact content skeleton (fill `<...>` from Step 1 output):

```markdown
# Task 001: Refresh libs/SystemUI-tags.jar from AOSP Soong output

## Goal
Replace the stale `libs/SystemUI-tags.jar` (2026 bytes, lacks
`EventLogTags.writeSysuiKeyguard(int,int)`) with the current AOSP Soong javac
jar (2086 bytes, contains it). This fixes one of the eight javac root-cause
groups recorded in `docs/issues/2026-08-12-current-progress-standards-review.md`.

## Context
- Source of truth: /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar
- Consumer: `SystemUI-core/build.gradle.kts` (`implementation(files(".../libs/SystemUI-tags.jar"))`)
- Generated from: `SystemUI-core/src/com/android/systemui/EventLogTags.logtags` (AOSP module `SystemUI-tags`)

## Authority
self-commit (no red-line areas expected)

## Allowed Paths
- `libs/SystemUI-tags.jar`
- `docs/issues/2026-08-12-current-progress-standards-review.md` (append a short result note)
- `docs/orchestration/log.md` is updated by the architect, not the worker

## Forbidden Paths
- Everything else, especially: `SystemUI-*/src/**`, `SystemUI-*/res*/**`,
  `**/build.gradle.kts`, `gradle/**`, `AGENTS.md`, `docs/adr/**`

## Steps
- [ ] 1. Confirm the stale jar lacks the method:
  `javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep -c writeSysuiKeyguard` → expect `0`
- [ ] 2. Copy the AOSP jar over: `cp <aosp-jar-path> libs/SystemUI-tags.jar`
- [ ] 3. Confirm the new jar has the method:
  `javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard` → expect the method signature
- [ ] 4. Append a dated note to the issue record stating old/new sizes and the javap evidence
- [ ] 5. Commit: `git add libs/SystemUI-tags.jar docs/issues/2026-08-12-current-progress-standards-review.md`
  message: `fix(libs): refresh SystemUI-tags.jar from AOSP Soong output`

## Acceptance
`javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard`
prints a line containing `writeSysuiKeyguard(int, int)`. `git status --short` shows
no other modified files outside Allowed Paths.

## Reports To
Architect appends one line to `docs/orchestration/log.md` on completion.
```

- [ ] **Step 3: Commit**

```bash
git add docs/orchestration/tasks/001-refresh-systemui-tags-jar.md
git commit -m "docs: add pilot task brief for SystemUI-tags.jar refresh"
```

---

### Task 5: Pilot execution — dispatch worker, monitor, review, merge

**Files:**
- Modify: `docs/orchestration/STATE.md`
- Modify: `docs/orchestration/log.md`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: pilot verdict recorded in log.md; merged commit from the worker (or a documented abort).

- [ ] **Step 1: Verify herdr command syntax against the installed binary**

```bash
herdr pane split --help
herdr agent start --help
herdr agent prompt --help
herdr agent wait --help
herdr agent read --help
```

Record the real flag syntax; use it (not this plan's templates) in Steps 2–4.

- [ ] **Step 2: Dispatch (serial — current checkout, no worktree)**

Split a pane, start pi in it, then prompt (exact prompt body):

```text
You are a worker in the SystemUI-Gradle project at /home/conv/myspace/SystemUI-Gradle.
Invoke the worker-contract skill. Read in order:
(1) AGENTS.md (2) docs/orchestration/CHARTER.md
(3) docs/orchestration/tasks/001-refresh-systemui-tags-jar.md
Then print your CONTRACT: block and start work.
```

Update STATE.md (Active Workers row: pane id, task 001, stage=dispatched) and append a `dispatch` line to log.md.

- [ ] **Step 3: Confirm the contract**

`herdr agent read <target>` until the `CONTRACT:` block appears. If it does not appear after the worker's first response, re-send the prompt once; if it still fails, abort the pilot and record `abort` in log.md with the reason.

Append a `contract-ok` line to log.md; set STATE stage=working.

- [ ] **Step 4: Monitor to completion**

`herdr agent wait <target> --state blocked,idle` (with the real flag syntax). On `blocked`: `agent read`, classify per CHARTER (REDLINE → relay to user; in-brief problem → let it debug). On `idle/done`: proceed to review.

- [ ] **Step 5: Review (architect personally re-runs acceptance)**

```bash
git log --oneline -3
git show --stat HEAD           # only libs/SystemUI-tags.jar + the issue record
javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard
git diff --check
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -1
```

Expected: worker commit has an English message; only the two allowed files changed; javap prints the method; tests `OK`. Any violation → send the concrete issue list back to the worker via `herdr agent prompt`; log `review-fail`.

- [ ] **Step 6: Wrap up**

- STATE.md: clear Active Workers row, note task 001 done.
- log.md: append `review-pass`, `merge` (trivial — already on main), `done` lines plus a one-line pilot verdict (what worked, what surprised).
- Close or keep the worker pane (`herdr pane close`), your call based on whether another task follows immediately.
- Commit:

```bash
git add docs/orchestration/
git commit -m "docs: record pilot orchestration run for task 001"
```

- [ ] **Step 7: Final push and report**

```bash
git push
git log --oneline -8
```

Report to the user: pilot verdict, worker behavior observations, and any proposed CHARTER/skill adjustments (do not apply adjustments without user approval — CHARTER is a red-line-adjacent process file).
