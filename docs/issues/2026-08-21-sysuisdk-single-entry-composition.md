# 2026-08-21 — SysUISdk single-entry AOSP composition

## Background

The current `tools/build_sysuisdk.py` reproduces and patches a legacy live SDK through
S0–S5, repository payload blobs, helper scripts, `--apply`, and permanent backup files.
That model served the migration but is no longer the desired maintenance interface.
The approved replacement is a single transactional generator that consumes an official
read-only SDK platform and an already-built AOSP tree.

Architecture and frozen artifact mapping:
`docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`.

## Approved outcome

```bash
python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp
```

The command creates `<sdk-root>/platforms/android-SysUISdk` by default. It uses Python
standard library ZIP/file operations, does not invoke Soong, never patches the official
base, and has no public S0–S5/apply/backup interface.

## Planned steps

1. Add TDD coverage for SDK-root discovery, exact input resolution, deterministic ZIP
   composition, framework-master collision behavior, byte-exact resources, source-derived
   AIDL declarations, the frozen 39-class bridge, transactional publication, ownership
   marker, and protected replacement.
2. Rewrite `tools/build_sysuisdk.py` around the one-shot command.
3. Build two independent generated SDKs and prove deterministic output.
4. Compile Debug, fresh R8, and full optimized Release against a private SDK root so the
   official and legacy installed platforms remain untouched.
5. Prove APK ZIP/V2 integrity and bridge-class absence.
6. Only after those gates pass, delete repository payloads/helpers proven superseded.
7. Update the live technical state truthfully; device validation remains deferred.

## Error-count/build evolution

This task is not driven by source error counts. Baseline before implementation:

- Python tools: 239/239 passing (Task 044 main fresh)
- Debug: passing
- Release R8: missing refs 0
- full optimized Release: passing

Task 045 must report fresh real results. A failed first attempt is retained as evidence,
not rewritten as success.

## Boundaries

- No SystemUI source, AIDL mirror, or resource edits.
- No Gradle dependency/version/module/build-check changes.
- No AOSP source/output mutation and no Soong invocation.
- No live/custom SDK mutation; validation uses a private SDK root.
- No deletion of external historical SDK backups.
- `libs/keepanno-annotations.jar` stays because it remains a compile-only project input.
- If the frozen artifact map is insufficient, stop with REDLINE evidence rather than
  adding a guessed family or widening the allowlist.

## Current status

Planning and exact brief approved by the user; isolated GLM-5.3 Worker dispatch is next.
Implementation/build results: **not run yet**.
