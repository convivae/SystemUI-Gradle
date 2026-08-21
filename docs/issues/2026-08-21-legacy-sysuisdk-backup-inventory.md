# 2026-08-21 — Legacy live SysUISdk backup inventory

## Status

Design approved by the user; exact Worker brief awaiting dispatch approval. The task is
strictly read-only with respect to `/home/conv/Android/Sdk` and `/home/conv/myspace/aosp`.

## Background

The legacy live platform contains nine historical backup files created by superseded
patch/install workflows:

- four `android.jar` backups;
- four `core-for-system-modules.jar` backups;
- one `framework.aidl` backup.

They are outside the repository and were deliberately excluded from Task 045. Before
any irreversible deletion, the project needs a byte-level inventory and a per-file
retention recommendation.

## Steps

1. Snapshot exact path, size, mtime, SHA-256, and type for all nine files.
2. Validate every JAR as ZIP, detect duplicate names, and inspect entry counts.
3. Generate one canonical current SysUISdk under `/tmp/task047-*` from the read-only
   official base and frozen AOSP inputs; never replace the live platform.
4. Compare backups with stock base files, live primary files, canonical generated
   files, and each other.
5. Classify each backup as byte-identical/redundant, unique historical snapshot, or
   malformed/unknown; report recoverability and potential reclaimed bytes.
6. Re-hash the live platform backup set after inspection to prove no mutation.

## Prohibition

This task must not delete, rename, chmod, touch, replace, or write any file under either
SDK platform. It may only write its report in the repository and evidence beneath
`/tmp/task047-*`.

## Error-count evolution

Not applicable. No build or source change is allowed, and no Gradle task will run.

## Open questions

Deletion remains unapproved. After the report is reviewed, the architect will present
an exact candidate list and reclaimed-byte total for a separate irreversible-action
decision.
