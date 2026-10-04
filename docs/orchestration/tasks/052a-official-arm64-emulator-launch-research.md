# Task 052A — Official AOSP ARM64 Emulator launch research

> **Research-only worker task. Do not launch, stop, reset, or mutate any emulator/device.**

## Goal

Establish the officially documented build, packaging, AVD creation, and launch path for an
AOSP ARM64 phone image, with explicit evidence for x86_64-host/ARM64-guest support and
software-emulation constraints.

## Authority

`self-commit` — commit the single report with an English commit message; never push.

## Reports To

Task 052 architect in `/home/conv/myspace/SystemUI-Gradle`.

## Allowed Paths

- Create and edit only:
  `docs/issues/2026-08-23-official-aosp-arm64-emulator-launch-research.md`
- Read any repository file, `/home/conv/myspace/aosp/**`, installed Android SDK/Emulator
  metadata, and public documentation.
- Use read-only commands, `android docs search/fetch`, and network retrieval of public pages.

## Forbidden Paths and Actions

- Do not modify any file outside the single allowed report.
- Do not run Gradle, Soong, Ninja, `m`, `lunch`, or any build.
- Do not start/stop/reset an emulator, use ADB, create/delete an AVD, or alter current QEMU.
- Do not change AOSP output, SDK packages, system images, repository source/resources, or Git history.
- Do not cite an AI answer, search-result snippet, or unsourced forum post as evidence.

## Global Constraints

- Primary sources first: `source.android.com`, `developer.android.com`, official Android
  Emulator release notes, AOSP source/docs, and first-party command help.
- Secondary sources may only corroborate a primary-source conclusion and must be labeled.
- Distinguish clearly between the Android guest image/kernel and the host Emulator/QEMU binary.
- Distinguish `emulator` launcher support, direct `qemu-system-aarch64-headless`, KVM, and TCG.
- Every decisive claim must include a URL or exact local source path plus quoted text/line range.
- Do not infer that “emulation is theoretically possible” means Google's launcher supports it.

## File Map

- Create: `docs/issues/2026-08-23-official-aosp-arm64-emulator-launch-research.md`
- Reference: `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md`
- Reference: `docs/superpowers/plans/2026-08-22-same-tree-arm64-emulator-runtime.md`

## Steps

- [ ] Read the Task 052 issue/plan and record the exact local product and observed failures.
- [ ] Find official documentation for building AOSP Emulator images and identify exact current
      `lunch`/`m`/packaging commands relevant to `sdk_phone64_arm64` or its supported successor.
- [ ] Find official AVD/system-image installation and launch instructions for locally built images.
- [ ] Find first-party statements on host/guest architecture support, KVM requirements, and
      software ARM emulation on an x86_64 Linux host.
- [ ] Check official Emulator release notes for ARM64 guest, cross-architecture, TCG, ranchu,
      or virtio device restrictions/fixes relevant to versions 35.3.8 and 36.6.6.
- [ ] Produce a command table: command, owning source, prerequisites, expected artifact/device,
      and whether it is officially supported for this host/guest combination.
- [ ] End with a bounded recommendation and explicit unknowns; do not prescribe undocumented flags.
- [ ] Run the acceptance command and commit the report with an English message.

## Required Report Sections

1. Question and current local facts
2. Official build and packaging commands
3. Official AVD/image installation and launch commands
4. Host/guest architecture and acceleration support
5. Emulator-version evidence
6. Supported-command matrix
7. Recommendation, confidence, and unresolved questions
8. Primary sources (full URLs/paths)

## Acceptance

Run from the worktree root:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('docs/issues/2026-08-23-official-aosp-arm64-emulator-launch-research.md')
s = p.read_text()
required = [
    'Official build and packaging commands',
    'Official AVD/image installation and launch commands',
    'Host/guest architecture and acceleration support',
    'Supported-command matrix',
    'Recommendation, confidence, and unresolved questions',
    'Primary sources',
]
assert all(x in s for x in required), [x for x in required if x not in s]
assert s.count('https://') >= 4, s.count('https://')
assert '/home/conv/myspace/aosp/' in s
print('TASK052A_REPORT=PASS')
PY
git diff --check HEAD^..HEAD
git diff --name-only HEAD^..HEAD
```

Expected output includes `TASK052A_REPORT=PASS`; `git diff --check` exits `0`; the only changed
path is the allowed report.
