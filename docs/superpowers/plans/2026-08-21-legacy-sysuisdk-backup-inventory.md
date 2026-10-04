# Legacy Live SysUISdk Backup Inventory Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this read-only audit plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a byte-level, reproducible inventory and retention recommendation for the nine legacy live SysUISdk backup files without mutating or deleting them.

**Architecture:** Hash and inspect the external backup set before and after the audit, generate a canonical current SDK only under `/tmp`, and compare each backup against stock, live-primary, canonical, and sibling versions. Persist conclusions in a repository architecture report.

**Tech Stack:** Python 3 standard library (`hashlib`, `json`, `pathlib`, `zipfile`), existing `tools/build_sysuisdk.py`.

**Spec:** `docs/issues/2026-08-21-legacy-sysuisdk-backup-inventory.md`

## Global Constraints

- `/home/conv/Android/Sdk/**` and `/home/conv/myspace/aosp/**` are read-only.
- Do not delete, rename, chmod, touch, replace, or write any SDK/AOSP file.
- Temporary writes are limited to `/tmp/task047-*`.
- Inspect exactly nine named live-platform backup files; do not widen cleanup scope.
- Generate comparison output with the supported single-entry generator only; never replace live SysUISdk.
- Recommendations are advisory. Irreversible deletion needs later explicit user approval.
- No Gradle task. Worker commits in English and never pushes.

---

## File map

- Create: `docs/architecture/2026-08-21-legacy-sysuisdk-backup-inventory.md` — full table, comparison evidence, recommendation.
- Modify: `docs/issues/2026-08-21-legacy-sysuisdk-backup-inventory.md` — execution record.
- Modify: this plan and `docs/orchestration/tasks/047-legacy-sysuisdk-backup-inventory.md` — checkbox/evidence state.
- Temporary only: `/tmp/task047-*`.

## Task 1: Freeze the before-state

- [x] **Step 1: Enumerate exactly nine files**

Use a Python manifest with fixed expected names, not a newest-file selector or deletion
glob. For each file record relative name, byte size, nanosecond mtime, SHA-256, type,
and—for JARs—ZIP test result, entry count, duplicate-name list, and manifest presence.
Write JSON only to `/tmp/task047-before.json`.

Expected summary:

```text
BACKUPS=9
HASHED=9
MISSING=0
```

Any missing, extra matching backup, unreadable, malformed, or duplicate-entry result is
reported, not repaired.

## Task 2: Generate a canonical comparison SDK outside the live platform

- [x] **Step 1: Build under `/tmp`**

```bash
rm -rf /tmp/task047-generated
python3 tools/build_sysuisdk.py \
  --aosp-root /home/conv/myspace/aosp \
  --sdk-root /home/conv/Android/Sdk \
  --base-platform /home/conv/Android/Sdk/platforms/android-37.0 \
  --output /tmp/task047-generated/android-SysUISdk
```

Expected: exit 0; output marker exists; no SDK platform file was changed.

- [x] **Step 2: Hash comparison targets**

Record stock, live-primary, and canonical hashes for `android.jar`,
`core-for-system-modules.jar`, and `framework.aidl`. For JAR backups, also compare entry
name sets and per-entry bytes so a unique archive can be explained rather than merely
labeled different.

## Task 3: Classify every backup

- [x] **Step 1: Apply explicit categories**

Every one of the nine rows must receive exactly one category:

```text
byte-identical/redundant
unique historical snapshot
malformed/unknown
```

For each row report equal targets, unique-entry/changed-entry counts, recoverability
from immutable stock/AOSP inputs, recommended action (`retain` or `candidate-delete`),
and reclaimed bytes if deleted. Unique or malformed files default to `retain`.

- [x] **Step 2: Explain limitations**

Do not claim semantic equivalence from matching entry names alone. Distinguish archive
metadata differences from class/resource byte differences, and state whether the live
platform itself is generator-owned or legacy/unmarked.

## Task 4: Prove no external mutation and publish the report

- [x] **Step 1: Repeat the exact manifest**

Write `/tmp/task047-after.json` using the same code and compare the normalized bytes of
the before/after manifests.

Expected:

```text
BACKUP_SET_UNCHANGED=true
BACKUPS=9
```

- [x] **Step 2: Repository scope checks**

```bash
git diff --check
git status --short
```

Expected: only the File map documentation paths changed; no deletion and no external
SDK/AOSP claim beyond recorded read-only evidence.

- [x] **Step 3: Commit and hand off**

Update the issue with actual results, commit in English without pushing, and provide an
exact candidate-delete list plus total bytes as a recommendation only. Finish with the
required `HANDOFF:` block.

## Completion evidence (Task 047 worker, 2026-08-22)

All checkboxes above are ticked with the following real outputs; full detail in
`docs/architecture/2026-08-21-legacy-sysuisdk-backup-inventory.md` and
`docs/issues/2026-08-21-legacy-sysuisdk-backup-inventory.md`.

- Task 1: `python3 /tmp/task047-inspect.py /tmp/task047-before.json` →
  `BACKUPS=9 / HASHED=9 / MISSING=0`, no extra backup-like files; 8 JARs zip_test OK,
  0 duplicate entry names.
- Task 2: generator run with the exact briefed command → exit 0
  (`base platform : android-37.0 (11382 files)`, `AOSP inputs : 8`,
  `bridge entries: 39 in both target jars`, `generated : 11381 files`); marker
  present; canonical hashes equal Task 045 main-fresh values. Per-entry (name set +
  bytes) comparisons for every backup × {stock, live, canonical} recorded in
  `/tmp/task047-comparison.json` and report §5.
- Task 3: 9/9 rows classified (8 byte-identical/redundant → candidate-delete,
  163,149,374 bytes; 1 unique historical snapshot → retain; 0 malformed/unknown);
  archive-metadata vs content distinctions and live-platform ownership
  (legacy/unmarked; live android.jar = canonical + 1,266 legacy entries) stated in
  report §6–§7.
- Task 4: `/tmp/task047-after.json` identical to before after normalization →
  `BACKUP_SET_UNCHANGED=true`, `BACKUPS=9`; `git diff --check` clean;
  `git status --short` shows only the four Allowed documentation paths;
  `DELETED=0`; English commit made locally, never pushed.
