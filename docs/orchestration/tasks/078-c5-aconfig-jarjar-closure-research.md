# Task 078 — C5 platform aconfig jarjar closure research and static gate

**Phase**: C5 blocker diagnosis/design
**Status**: proposed → completed in `1f5e93e8`; chief review returned FAIL (fabricated R8-library claim, ownership-unsafe algorithm, sharding misattribution, 726-rule wording, gate robustness); corrective commit on top applies the six required fixes. Implementation of the selected rewrite remains out of scope pending user adjudication.
**Authority**: `self-commit` (worker may commit the allowed diagnostic/report files, must never push)
**Reports To**: Chief architect in the current herdr workspace

## Goal

Turn the AOSP-17 platform-aconfig package mismatch into a seconds-scale static Release APK gate, reconstruct the exact Soong rewrite stage from primary sources, and compare three legal solution families. Produce one recommendation and a bounded implementation brief, but do not modify the Gradle build or implement the rewrite in this task.

## Frozen evidence

- Current Gradle Release APK: `app/build/outputs/apk/release/app-release.apk`.
- Stock AOSP APK: `/home/conv/myspace/aosp/out/target/product/emu64x/system_ext/priv-app/SystemUI/SystemUI.apk`.
- Authoritative rule file: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt` (725 rules / 726 physical lines including trailing blank; SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`).
- AOSP host JarJar: `/home/conv/myspace/aosp/out/host/linux-x86/framework/jarjar.jar`.
- Four runtime-critical source descriptors currently present in Gradle Release and absent from stock: `android.app.Flags`, `android.os.Flags`, `android.view.accessibility.Flags`, and `com.android.window.flags.Flags`. Their required targets are under `com.android.internal.hidden_from_bootclasspath.`.
- A preliminary all-rule scan found Gradle Release has 30 original/0 relocated matching type descriptors; stock has 1 original/36 relocated. The stock original is a defined `android.app.admin.flags.FeatureFlagsImpl`, so a naive “all 725 rule sources must be absent” gate is invalid and must not be encoded.

## Global constraints

- Same checkout, serial work only. No Gradle, Soong, emulator, or ADB command in this research task.
- Read AOSP source and existing `out/` artifacts only; do not modify the AOSP checkout or generated outputs.
- No stub, platform-class packaging, `dontwarn`, source-import rewrite, resource edit, or runtime workaround.
- Python runs via `uv run`; scripts under `tools/` are Python only.
- Cite primary evidence with file path and line/rule context; distinguish direct observation from inference.
- Do not select a behavior-changing architecture silently. The recommendation goes to the user for adjudication.

## Allowed Paths

- `tools/check_aconfig_jarjar_references.py` (new diagnostic gate)
- `tools/tests/test_check_aconfig_jarjar_references.py` (new unit tests)
- `docs/issues/2026-09-01-c5-aconfig-jarjar-closure.md`
- `docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md` (new research report)
- this task brief, only to tick checkboxes/add actual evidence

## Forbidden Paths

- all `SystemUI-*/src/**`, `SystemUI-*/res*/**`, manifests, and AOSP-mirrored files
- all `*.gradle*`, `settings.gradle.kts`, `gradle/libs.versions.toml`, `gradle.properties`
- `app/proguard*.flags`, `libs/**`, SDK platform files, `AGENTS.md`, `docs/adr/**`, and `docs/orchestration/CHARTER.md`
- `/home/conv/myspace/aosp/**` writes of any kind
- `app/build/**` writes; existing APKs are read-only inputs

## Work plan

### P1 — Static descriptor gate

- [x] Add a minimal DEX type-table reader that distinguishes descriptor presence from class definitions and scans all `classes*.dex` entries without external Python packages.
- [x] Parse exact `rule <source> <target>` entries from the authoritative `repackaging.txt`; reject unsupported wildcard syntax rather than silently misinterpreting it.
- [x] Implement a critical-pair gate for the four frozen runtime classes. Output source/target type presence and definition presence per pair, plus stable totals and `RESULT=PASS|FAIL`.
- [x] Add unit tests using synthetic minimal DEX/ZIP/rule fixtures. Cover malformed DEX, duplicate descriptors across multidex, an unsupported rule, source-present failure, target-present pass, and source+target ambiguity.
- [x] Run the gate against both current Gradle Release and stock AOSP SystemUI. Record exact output. Do not weaken the critical set because the current APK fails. (Release exit 1 FAIL; stock exit 0 PASS; 19 tests at first pass; 23 after review fixes)

### P2 — Primary-source Soong reconstruction

- [x] Trace where `framework-minus-apex` declares `jarjar_prefix`/`jarjar_shards` and where Soong generates and propagates the rule mapping into `SystemUI-core`, `SystemUI-application`, and final SystemUI processing. (725 rules: 726 lines incl. trailing blank; see report §1.1. `jarjar_shards` applies only to the explicit-rules path, not the automatic per-module rewrite: report §2.4)
- [x] Establish the stage ordering relative to javac/kotlinc, static-library combination, R8/optimization, D8, and APK packaging. If a stage cannot be proven, label it unknown. (per-module post-compile rewrite proven; stock FeatureFlagsImpl R8-liveness chain labeled unknown)
- [x] Compare source/target **type references and class definitions** in current Release versus stock APK. Explain the 30/0 versus 1/36 observation and why the stock `FeatureFlagsImpl` exception rules out a blanket all-rule absence assertion.
- [x] Record exact reproducibility inputs: which rule file/tool are generated by AOSP, whether they can be regenerated from a clean AOSP tree, and what must or must not be committed to this repository. (report §2.6)

### P3 — Design comparison and recommendation

Evaluate, at minimum:

1. **Pre-R8 program-input rewrite**: official AGP scoped-artifact/instrumentation APIs and/or a narrow classfile transform; ability to rewrite references without accidentally shipping platform definitions; behavior across project classes and dependency jars; Debug/Release parity.
2. **Post-R8 DEX rewrite**: DEX correctness, multidex, checksums/signing, AGP task ordering, mapping/debug-info impact, and maintainability.
3. **Reuse/reprocess Soong JarJar artifacts**: source-first compliance, reproducibility from AOSP, classpath/program-input boundaries, and whether this would substitute prebuilt SystemUI code for Gradle-compiled source.

- [x] Give each option a supportability, correctness, reproducibility, and rule-compliance verdict.
- [x] Recommend exactly one seam, or state that evidence is insufficient and identify the missing experiment. (Review-corrected: pre-R8 transform family retained as preferred, but the concrete algorithm's evidence is insufficient — bounded experiments E1–E4 named in report §4.1/§4.5; user adjudication pending)
- [x] Draft a separate implementation brief with exact allowed paths, red lines, tests, and rollback criteria. Do not execute it. (report §5)

### P4 — Documentation and commit

- [x] Update the issue record after each phase with actual commands/results.
- [x] Write the architecture report and link it from the issue. (`docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md`)
- [x] Commit only allowed paths with an English commit message; never push.
- [x] End with the four-part worker completion report and `HANDOFF:` block required by CHARTER.

## Acceptance

1. Unit tests:

```bash
uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q
```

Expected: all tests pass.

2. Current Release red gate:

```bash
uv run python tools/check_aconfig_jarjar_references.py \
  --apk app/build/outputs/apk/release/app-release.apk \
  --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
```

Expected: exit 1, all four critical sources reported present, all four relocated targets reported absent, `RESULT=FAIL`.

3. Stock AOSP comparator:

```bash
uv run python tools/check_aconfig_jarjar_references.py \
  --apk /home/conv/myspace/aosp/out/target/product/emu64x/system_ext/priv-app/SystemUI/SystemUI.apk \
  --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
```

Expected: exit 0, all four critical sources absent, all four relocated targets present, `RESULT=PASS`.

4. Scope and formatting:

```bash
git diff --check
git diff --name-only <task-base>..HEAD
```

Expected: clean diff check; only Allowed Paths changed.
