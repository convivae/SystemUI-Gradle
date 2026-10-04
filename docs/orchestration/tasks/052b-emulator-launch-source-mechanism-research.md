# Task 052B — Android Emulator launcher/QEMU source mechanism research

> **Research-only worker task. Do not launch, stop, reset, or mutate any emulator/device.**

## Goal

Trace the first-party source path from the `emulator` launcher to final ARM64 QEMU argv and
explain, without speculation, the observed cross-architecture rejection and ARM `ranchu` plus
PCI virtio-device mismatch.

## Authority

`self-commit` — commit the single report with an English commit message; never push.

## Reports To

Task 052 architect in `/home/conv/myspace/SystemUI-Gradle`.

## Allowed Paths

- Create and edit only:
  `docs/issues/2026-08-23-android-emulator-launch-source-mechanism.md`
- Read any repository file, `/home/conv/myspace/aosp/**`, installed SDK/AOSP Emulator binaries,
  symbols/strings/help output, and public first-party source mirrors.
- Run bounded read-only binary help/version/query commands that cannot boot a guest.

## Forbidden Paths and Actions

- Do not modify any file outside the single allowed report.
- Do not run Gradle, Soong, Ninja, `m`, `lunch`, or any build.
- Do not start/stop/reset an emulator, use ADB, create/delete an AVD, or alter current QEMU.
- Do not patch binaries, AOSP source/output, SDK files, system images, AVD files, or runtime logs.
- Do not recommend a flag until the source path proves what it changes.

## Global Constraints

- Primary evidence is source code and first-party command help; record immutable AOSP/Gitiles URLs
  or exact checkout paths and line ranges.
- Locate the exact source/condition for `QEMU2 emulator does not support arm64 CPU architecture`.
- Separate launcher policy from QEMU capability and acceleration availability.
- Trace how guest ABI, host architecture, AVD config, feature flags, machine type, and virtio
  transport produce the final `-machine`, `-device`, and `-soundhw` arguments.
- Compare the observed 35.3.8/36.6.6 argv only through retained logs; do not rerun the emulator.
- Treat the trailing `-machine type=virt` launch as a diagnostic probe, not an accepted fix.

## File Map

- Create: `docs/issues/2026-08-23-android-emulator-launch-source-mechanism.md`
- Read evidence:
  `/home/conv/myspace/task052-aosp-arm64-runtime/logs/emulator-isolated-avd.log`
- Read evidence:
  `/home/conv/myspace/task052-aosp-arm64-runtime/logs/emulator-sdk36.log`
- Read evidence:
  `/home/conv/myspace/task052-aosp-arm64-runtime/logs/emulator-sdk36-virt.log`
- Reference: `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md`

## Steps

- [ ] Record binary versions, paths, local AVD config, and exact generated argv from retained logs.
- [ ] Find the launcher architecture-rejection source and enumerate its exact predicates.
- [ ] Trace launcher/backend selection for `qemu-system-aarch64-headless` on x86_64 Linux.
- [ ] Trace machine selection (`ranchu`/alternatives) and whether duplicate `-machine` options merge
      properties or replace the selected machine.
- [ ] Trace audio, input, Wi-Fi, vsock, and serial virtio transport selection; explain why PCI
      models were emitted and what first-party configuration selects MMIO/device models.
- [ ] Identify any source-controlled official invocation that launches this ARM64 goldfish product.
- [ ] Build a cause/evidence table separating proven facts, likely interpretations, and unknowns.
- [ ] Recommend the narrowest source-proven next probe, including exact expected argv delta and
      stop condition; do not modify or run it.
- [ ] Run the acceptance command and commit the report with an English message.

## Required Report Sections

1. Observed binaries, AVD, and argv
2. Launcher architecture gate
3. Backend and accelerator selection
4. Machine selection
5. Virtio transport/device selection
6. Why the observed command fails
7. Source-proven next probe
8. Evidence table and first-party sources

## Acceptance

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('docs/issues/2026-08-23-android-emulator-launch-source-mechanism.md')
s = p.read_text()
required = [
    'Launcher architecture gate',
    'Backend and accelerator selection',
    'Machine selection',
    'Virtio transport/device selection',
    'Why the observed command fails',
    'Source-proven next probe',
    'Evidence table and first-party sources',
]
assert all(x in s for x in required), [x for x in required if x not in s]
for needle in ['QEMU2 emulator does not support arm64 CPU architecture', 'ranchu',
               'virtio-snd-pci', 'emulator-sdk36-virt.log']:
    assert needle in s, needle
assert s.count('/home/conv/myspace/aosp/') >= 3
print('TASK052B_REPORT=PASS')
PY
git diff --check HEAD^..HEAD
git diff --name-only HEAD^..HEAD
```

Expected output includes `TASK052B_REPORT=PASS`; `git diff --check` exits `0`; the only changed
path is the allowed report.
