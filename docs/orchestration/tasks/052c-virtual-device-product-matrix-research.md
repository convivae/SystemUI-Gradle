# Task 052C — Same-tree virtual-device product and launch matrix research

> **Research-only worker task. Do not launch, stop, reset, or mutate any emulator/device.**

## Goal

Enumerate virtual-device products this AOSP checkout can build and the officially intended host
launch mechanism for each, then rank practical same-tree SystemUI runtime environments for this
x86_64 Linux host.

## Authority

`self-commit` — commit the single report with an English commit message; never push.

## Reports To

Task 052 architect in `/home/conv/myspace/SystemUI-Gradle`.

## Allowed Paths

- Create and edit only:
  `docs/issues/2026-08-23-same-tree-virtual-device-product-matrix.md`
- Read any repository file, `/home/conv/myspace/aosp/**`, installed SDK/Emulator metadata,
  retained Task 052 evidence, and public documentation/issues.
- Run read-only product/config inventory commands that do not invoke lunch/build/emulator/ADB.

## Forbidden Paths and Actions

- Do not modify any file outside the single allowed report.
- Do not run Gradle, Soong, Ninja, `m`, `lunch`, or any build/config-regeneration command.
- Do not start/stop/reset an emulator, use ADB, create/delete an AVD, or alter current QEMU.
- Do not modify AOSP output, SDK files/packages, AVDs, system images, or repository source/resources.
- Do not treat third-party reports as authoritative; label them as corroboration or contradiction.

## Global Constraints

- Start from product makefiles/AndroidProducts files, official docs, image metadata, and
  source-controlled launch scripts.
- Include at least: `sdk_phone64_arm64`, the corresponding x86_64 goldfish phone product if
  present, `aosp_arm64` GSI, Cuttlefish ARM64/x86_64 candidates, and any officially supplied
  local virtual-device runner in this checkout.
- For each option record guest ABI, build variant, artifacts, host launcher, acceleration,
  cross-architecture behavior, same-tree framework/platform-key fidelity, expected disk/build
  cost, and suitability for SystemUI replacement.
- Distinguish “listed product”, “buildable in this checkout”, “artifact already built”, and
  “runtime proven”. Do not collapse them into one status.
- Secondary-source research should look for reproducible ARM64-on-x86 Android Emulator practice,
  but each claim must be reconciled with official docs/source.

## File Map

- Create: `docs/issues/2026-08-23-same-tree-virtual-device-product-matrix.md`
- Reference: `/home/conv/myspace/aosp/device/generic/goldfish/**`
- Reference: `/home/conv/myspace/aosp/device/google/cuttlefish/**` if present
- Reference: `/home/conv/myspace/aosp/out/target/product/emu64a/**`
- Reference: `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md`

## Steps

- [ ] Inventory product declarations and source-controlled launch/package targets without running lunch.
- [ ] Map each product to required artifacts and its intended host-side launcher/runner.
- [ ] Inventory already-built `generic_arm64` and `emu64a` artifacts and label exact status.
- [ ] Determine whether an x86_64 same-tree phone image is available/buildable and whether it removes
      the host cross-architecture issue while retaining framework/source/platform-key fidelity.
- [ ] Determine whether Cuttlefish is present and usable on this host without unsupported hardware
      assumptions; cite official prerequisites.
- [ ] Gather at least two independently accessible secondary reports/issues about ARM64 guest on
      x86_64 Android Emulator/TCG, then reconcile each with official evidence.
- [ ] Produce a ranked matrix and recommend primary, fallback, and rejected paths with reasons.
- [ ] State the exact next build or launch command only where first-party evidence supports it;
      otherwise state what must be proven first.
- [ ] Run the acceptance command and commit the report with an English message.

## Required Report Sections

1. Checkout and host facts
2. Product inventory
3. Artifact and launcher mapping
4. Host/guest/acceleration matrix
5. Secondary corroboration
6. Ranked same-tree runtime options
7. Recommended next command and stop conditions
8. Sources

## Acceptance

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('docs/issues/2026-08-23-same-tree-virtual-device-product-matrix.md')
s = p.read_text()
required = [
    'Product inventory',
    'Artifact and launcher mapping',
    'Host/guest/acceleration matrix',
    'Secondary corroboration',
    'Ranked same-tree runtime options',
    'Recommended next command and stop conditions',
    'Sources',
]
assert all(x in s for x in required), [x for x in required if x not in s]
for needle in ['sdk_phone64_arm64', 'aosp_arm64', 'Cuttlefish', 'x86_64', 'arm64']:
    assert needle in s, needle
assert s.count('https://') >= 4, s.count('https://')
print('TASK052C_REPORT=PASS')
PY
git diff --check HEAD^..HEAD
git diff --name-only HEAD^..HEAD
```

Expected output includes `TASK052C_REPORT=PASS`; `git diff --check` exits `0`; the only changed
path is the allowed report.
