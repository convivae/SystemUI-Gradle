# Task 042 — R8 aconfig assumption closure

## Authority

`redline-gated`, `self-commit`, never push. Dispatch requires explicit user approval of this
exact brief, including the complete byte-exact exported AOSP rule file.

Task 042 is the second stage of ADR 0006. It owns only the final
`com.android.aconfig.annotations.AssumeTrueForR8` R8 closure and must preserve the real
AOSP flag-assumption semantics.

## Goal

Add independent declarative SysUISdk stage `S3c` for exactly one source-identical
`AssumeTrueForR8.class`, import the complete byte-exact AOSP `aconfig_proguard.flags`, keep
debug assembly green, keep all 36 bridged library classes out of the APK, and move fresh R8
exactly from one missing ref to zero with the two return-true assumption rules effective.

## Required reading

After `worker-contract`, `AGENTS.md`, and `docs/orchestration/CHARTER.md`, read:

1. `docs/issues/2026-08-21-r8-aconfig-assumption-closure.md`
2. `docs/superpowers/plans/2026-08-21-r8-aconfig-assumption-closure.md`
3. `docs/adr/0006-sysuisdk-r8-library-class-bridge.md`
4. `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md`
5. `tools/patch_sdk_r8_library_classes.py`
6. `tools/build_sysuisdk.py`
7. `app/build.gradle.kts`
8. AOSP `frameworks/libs/modules-utils/java/Android.bp`
9. AOSP `frameworks/libs/modules-utils/java/aconfig_proguard.flags`

Follow the plan checklist exactly. Use TDD; use systematic debugging for unexpected results.

## Exact source and rule inputs

Annotation source artifact:

```text
/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/libs/modules-utils/java/aconfig-annotations-lib/linux_glibc_common/javac/aconfig-annotations-lib.jar
SHA-256 ef431f923f6925ec835282afb3ee62c909987dd2f053dbcdccc1f7294923f551
```

Exact entry:

```text
com/android/aconfig/annotations/AssumeTrueForR8.class
413 bytes
SHA-256 d4602718f42729ea476648dc391f88db7e9a1b21a344c566eadb6077e4691468
```

Exported rule source:

```text
/home/conv/myspace/aosp/frameworks/libs/modules-utils/java/aconfig_proguard.flags
778 bytes
SHA-256 b6a85445ea517fc4861c0a5d68ea8af8d1b6b4f2e7a4a569c7830891e73b2f01
```

The complete rule file must be copied byte-for-byte to `app/aconfig_proguard.flags`; no
subsetting, rewriting, or added provenance comments inside that file.

## Allowed paths

Worker may create/modify only:

- `tools/patch_sdk_aconfig_r8_annotation.py`
- `tools/tests/test_patch_sdk_aconfig_r8_annotation.py`
- `tools/build_sysuisdk.py`
- `tools/tests/test_build_sysuisdk.py`
- `tools/tests/test_aconfig_r8_rules.py`
- `app/aconfig_proguard.flags`
- `app/build.gradle.kts`
- `docs/issues/2026-08-21-r8-aconfig-assumption-closure.md`
- `docs/orchestration/tasks/042-r8-aconfig-assumption-closure.md`
- `/tmp/task042-*`

The sole permitted live SDK mutation is:

```bash
python3 tools/build_sysuisdk.py --apply --source /tmp/task042-sdk-a
```

## Forbidden paths and mechanisms

- Direct writes/copies/ZIP edits under the live SysUISdk.
- Modification of Task 041's exact 35-entry constants or `task041_slices()`.
- Injection of any class other than the exact one Task 042 entry.
- `SystemUI-*/src/**`, `SystemUI-*/res*/**`, `app/src/**`, any `res/**`, AOSP source.
- Existing `app/proguard.flags`, `app/proguard_common.flags`, `app/proguard_kotlin.flags`, or
  plugin ProGuard files.
- Any other root/module build file, catalog/version/module boundary, `libs/**`, local Maven,
  `AGENTS.md`, ADRs, CHARTER, maintained state/roadmap docs, or Task 041 frozen docs.
- Runtime `implementation`, new `compileOnly`, JAR/AAR/Maven dependency, stubs, copied source.
- Any `dontwarn`, broad keep, disabled R8/shrink/check, source exclusion, suppression, or AGP
  private-task hack.
- Any hand-selected or edited subset of the AOSP rule file.
- Worker push.

## Build serialization

Only one SystemUI Gradle build may run system-wide. Check before every Gradle command. Use
`-Dorg.gradle.workers.max=4`. Every piped Gradle command must use `set -o pipefail`, `tee`,
and preserve the real Gradle exit status. Reviewers are static-only.

## Checklist

- [ ] Fresh baseline: real R8 exit 1; exact one missing ref.
- [ ] Source JAR, class entry, and AOSP rule file hashes/sizes match the brief.
- [ ] Add focused patcher tests first and capture RED.
- [ ] Implement exact one-entry patcher by reusing the generic Task 041 engine; capture GREEN.
- [ ] Commit `build: add exact AssumeTrueForR8 SDK patcher`.
- [ ] Add `S3c` tests first and capture RED.
- [ ] Implement stage order/default/two-target prevalidation and capture GREEN.
- [ ] Commit `build: add SysUISdk aconfig R8 assumption stage`.
- [ ] Add rule provenance/wiring test first and capture RED.
- [ ] Copy the complete AOSP rule file byte-exact and wire both build types; capture GREEN.
- [ ] Commit `build: import AOSP aconfig R8 assumption rules`.
- [ ] Full Python suite exits 0 and count is not below baseline 233.
- [ ] Two full staging SDKs have inventory-identical target pairs.
- [ ] Each target contains the one source-identical new entry; prior 35 remain unchanged.
- [ ] Pre-apply S5 differs only by one entry per target.
- [ ] Guarded apply only; post-apply strict S5 `ALL PASS`.
- [ ] Debug duplicate-class + assemble hard gate exits 0.
- [ ] Debug APK reports `BRIDGED=36 PACKAGED=0`.
- [ ] Fresh R8 exits 0, `BUILD SUCCESSFUL`, and has zero missing refs.
- [ ] Effective release configuration contains both `AssumeTrueForR8` return-true rules.
- [ ] Issue records truthful commands/status/counts/hashes and immutable scope evidence.
- [ ] `git diff --check` passes; focused English commits; clean worktree; never push.

## Acceptance

```text
Baseline R8: exit 1; exact set {AssumeTrueForR8}
New SDK slice: exactly 1 source-identical class per target
Prior Task 041 bridge: all 35 entries unchanged
Staging A/B: complete target name→CRC inventories equal
S5 after guarded apply: ALL PASS
Python suite: exit 0; count >= 233
Debug hard gate: real exit 0; BUILD SUCCESSFUL
Debug APK: BRIDGED=36 PACKAGED=0
AOSP rules: committed file byte-identical, SHA pinned, no dontwarn
Effective R8 config: assumevalues + assumenosideeffects return-true rules present
Fresh R8: real exit 0; BUILD SUCCESSFUL; zero missing refs
git diff --check: exit 0
```

## REDLINE conditions

Stop immediately, print `REDLINE: <area> — <facts and intended action>`, and wait if:

1. Baseline is not exactly one ref or it is not `AssumeTrueForR8`.
2. Source/rule hashes, sizes, class retention/target, or owner differ.
3. More than the exact one class is needed or any source entry is missing.
4. Existing target bytes conflict with approved source bytes.
5. Task 041's 35 entries/constants would need modification.
6. The complete rule file cannot be imported byte-exact or AGP rejects it.
7. Direct live-SDK mutation or any forbidden path/mechanism appears necessary.
8. Staging A/B differ, pre-apply S5 has unrelated deltas, or post-apply S5 fails.
9. Debug fails, any bridged class enters APK, or Kotlin/Compose regresses.
10. Fresh R8 is nonzero, emits any missing ref, or lacks either effective return-true rule.
11. Another SystemUI Gradle build is active.

Do not broaden scope, suppress the warning, package the annotation, or retry a failed approach
without diagnosis and architect/user adjudication.

## Reports to

Chief architect. Final terminal report must be:

```text
HANDOFF:
- done: <S3c + exact class + byte-exact rules>
- verified: <tests/S5/debug/APK/effective-config/R8 real outputs>
- commits: <hashes and English subjects>
- remaining: <release packaging milestone, or exact blockers>
```
