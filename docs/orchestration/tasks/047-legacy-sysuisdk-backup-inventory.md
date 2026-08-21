# Task 047: Legacy live SysUISdk backup inventory

> Orchestrated exact brief. Protocol: `docs/orchestration/CHARTER.md` + worker-contract. Worker commits but never pushes.

## Authority

`self-commit`, strictly read-only outside the repository and `/tmp/task047-*`. No backup
deletion or live SDK mutation is authorized. If inspection cannot be completed without
changing SDK/AOSP content, stop and report the exact blocker.

## Reports To

Chief architect in the main SystemUI-Gradle herdr pane. Commit locally; never push.

## Required reading and sub-skills

After worker-contract startup, read completely:

1. `docs/issues/2026-08-21-legacy-sysuisdk-backup-inventory.md`
2. `docs/superpowers/plans/2026-08-21-legacy-sysuisdk-backup-inventory.md`
3. `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`
4. `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`
5. `docs/CURRENT_STATE.md`

Invoke `superpowers:executing-plans`.

## Goal

Audit exactly the nine historical files under
`/home/conv/Android/Sdk/platforms/android-SysUISdk`, compare them byte-wise with stock,
live-primary, and a canonical current generated SDK, and recommend retain or
candidate-delete without executing deletion.

## Allowed Paths

- create `docs/architecture/2026-08-21-legacy-sysuisdk-backup-inventory.md`
- modify `docs/issues/2026-08-21-legacy-sysuisdk-backup-inventory.md`
- modify `docs/superpowers/plans/2026-08-21-legacy-sysuisdk-backup-inventory.md`
- modify `docs/orchestration/tasks/047-legacy-sysuisdk-backup-inventory.md`
- read-only `/home/conv/Android/Sdk/platforms/android-SysUISdk/**`
- read-only `/home/conv/Android/Sdk/platforms/android-37.0/**`
- read-only `/home/conv/myspace/aosp/**`
- `/tmp/task047-*` evidence and canonical generated output

## Frozen nine-file set

- `android.jar.orig`
- `android.jar.bak-20260813-210816`
- `android.jar.bak-20260821-011116`
- `android.jar.bak-20260821-013303`
- `core-for-system-modules.jar.orig`
- `core-for-system-modules.jar.bak-20260813-210816`
- `core-for-system-modules.jar.bak-20260821-011116`
- `core-for-system-modules.jar.bak-20260821-013303`
- `framework.aidl.bak-preaidl`

## Forbidden Paths and actions

- every other repository path, especially generator/build configuration/source/res
- any write/delete/rename/chmod/touch/replace under Android SDK or AOSP
- `rm`, `mv`, `cp`, `install`, or redirection targeting either SDK platform
- live generator output, `--replace`, Gradle, Soong, device operations
- broad cleanup globs outside `/tmp/task047-*`

## Execution

Follow every checkbox in
`docs/superpowers/plans/2026-08-21-legacy-sysuisdk-backup-inventory.md`.

## Acceptance

The report and issue must include machine-generated before/after manifests and this
summary from fixed-name Python inspection:

```text
BACKUPS=9
HASHED=9
MISSING=0
BACKUP_SET_UNCHANGED=true
```

Run the canonical comparison exactly outside the live platform:

```bash
python3 tools/build_sysuisdk.py \
  --aosp-root /home/conv/myspace/aosp \
  --sdk-root /home/conv/Android/Sdk \
  --base-platform /home/conv/Android/Sdk/platforms/android-37.0 \
  --output /tmp/task047-generated/android-SysUISdk
git diff --check
git status --short
```

Expected: generator exit 0; exactly nine report rows and nine recommendations; JAR ZIP
integrity/duplicate checks and per-entry comparisons recorded; before/after hashes,
sizes, and mtimes identical; no external deletion/mutation; only Allowed repository
paths changed. No Gradle task is run.

## Completion report

Provide one focused English commit, exact per-file category/recommendation, total
candidate-delete bytes, explicit `DELETED=0`, actual verification outputs, and the
required terminal-final `HANDOFF:` block.
