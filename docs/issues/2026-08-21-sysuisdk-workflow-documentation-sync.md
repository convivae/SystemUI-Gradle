# 2026-08-21 — SysUISdk workflow documentation sync

## Status

Design approved by the user; exact Worker brief awaiting dispatch approval. This task is
factual documentation synchronization only. It does not change SysUISdk generation or
Gradle behavior.

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

## Steps

1. Capture every stale active-workflow reference in the approved files.
2. Replace it with the single-entry, read-only-base, transactional owned-output model.
3. Keep historical implementation identifiers out of both public READMEs.
4. Run static wording/scope gates and the full Python suite; do not run Gradle.
5. Record actual results and commit in English without pushing.

## Error-count evolution

Not applicable: this is documentation/comment synchronization and must not change the
build graph. Build error counts are not measured. Python test count is recorded only as
a regression gate.

## Open questions

None for the approved factual scope. Any policy change beyond replacing stale workflow
facts is a REDLINE and requires separate user approval.
