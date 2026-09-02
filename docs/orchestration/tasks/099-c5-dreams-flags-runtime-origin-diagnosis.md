# Task 099 — C5 `android.service.dreams.Flags` runtime origin diagnosis

## Goal

Produce a bounded, read-only diagnosis of the Task 098 `Landroid/service/dreams/Flags;` runtime failure: establish a tight static RED loop on the frozen Debug APK, enumerate every real instruction-level caller, prove canonical artifact/AOSP provenance, and explain exactly why existing four-rule/166-caller coverage did not rewrite it. Do not fix, build, or touch the device.

## Frozen startup — no substitutions

Before the unique `CONTRACT:` block, perform only separate serial `read` operations in this exact order. Do not use bash, `wc`, `rg`, `find`, git, scratch, Herdr control, emulator/ADB, or any write during this sequence.

1. Read `AGENTS.md` completely.
2. Read `docs/HANDOFF.md` completely.
3. Read `docs/orchestration/CHARTER.md` completely.
4. Read `docs/orchestration/STATE.md` completely.
5. Read the Chief-specified frozen tail of `docs/orchestration/log.md` completely.
6. Read this brief completely.
7. Read `docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md` completely.
8. Read each mandatory source below completely, one file per read call, in listed order.
9. Output exactly one `CONTRACT:` block and stop for Chief acceptance.

Reading this brief early, parallelizing reads, inserting any command, or omitting/reordering a source retires the attempt before technical acceptance.

## Mandatory sources after the brief/issue

1. `docs/issues/2026-09-02-c5-debug-runtime-reboot-gate.md`
2. `docs/issues/2026-09-01-c5-focused-reference-origins.md`
3. `docs/issues/2026-09-02-c5-production-immutable-input-seam.md`
4. `docs/issues/2026-09-02-c5-debug-build-static-gate.md`
5. `gradle/aosp17-critical-aconfig-reference-rules.txt`
6. `gradle/aosp17-critical-aconfig-reference-classes.txt`
7. `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/FrozenAconfigInputs.kt`
8. `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewriteFactory.kt`
9. `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/ReferenceOnlyClassRewriter.kt`
10. `tools/check_aconfig_jarjar_references.py`
11. `/home/conv/myspace/aosp/frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/keyguard/KeyguardTransitionHandler.java`
12. `/home/conv/myspace/aosp/frameworks/base/libs/WindowManager/Shell/Android.bp`
13. `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`

## Required CONTRACT values

```text
CONTRACT:
- task: docs/orchestration/tasks/099-c5-dreams-flags-runtime-origin-diagnosis.md
- goal: bounded read-only origin and coverage diagnosis for the frozen Debug APK android.service.dreams.Flags instruction reference
- allowed_paths: [docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md, /tmp/task099-c5-dreams-flags-diagnosis/**, read-only mandatory sources/artifacts/intermediates]
- forbidden_paths: [production source/build logic, gradle/aosp17-critical-aconfig-reference-rules.txt, gradle/aosp17-critical-aconfig-reference-classes.txt, tests, SDK, libs/**, AOSP/out writes, every other tracked path]
- acceptance: deterministic frozen-APK RED loop + complete instruction callers + canonical provenance + coverage-membership matrix + falsified hypotheses + bounded root cause, with no build/fix/device action
- authority: no commit/push; Chief owns durable closure
```

## Frozen input and evidence root

- APK: `app/build/outputs/apk/debug/app-debug.apk`
- Required size: `190547804`
- Required SHA-256: `f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`
- Old owner: `android.service.dreams.Flags` / `Landroid/service/dreams/Flags;`
- Hidden owner: `com.android.internal.hidden_from_bootclasspath.android.service.dreams.Flags` / `Lcom/android/internal/hidden_from_bootclasspath/android/service/dreams/Flags;`
- Full mapping authority: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`, expected SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`
- Evidence root: `/tmp/task099-c5-dreams-flags-diagnosis/`
- DEX disassembler: `/home/conv/Android/Sdk/build-tools/37.0.0/dexdump`

## Allowed actions after CONTRACT acceptance

1. Read-only preflight: prove clean pushed base, frozen APK/full-rule identity, no Gradle/Soong/Ninja build process. Do not stop or kill processes.
2. Create only the evidence root above.
3. Phase 1 first: define and run a deterministic static loop against the frozen APK. It must return RED for a real old-owner instruction and report old/hidden referenced/defined state. Save exact command/output/exit.
4. Only after RED, list 3–5 ranked falsifiable hypotheses in scratch and report them to Chief before deeper probes. Continue unless Chief stops/reorders them.
5. Use read-only DEX/class/JAR/AAR/source analysis to enumerate every actual caller and canonical origin. Ordinary UTF-8/string/type-table hits alone are insufficient.
6. Update only the issue document with evidence, verdict and truthful no-build/no-device record. Stop before any commit.

## Forbidden actions

- No Gradle wrapper, Gradle, Soong, Ninja, D8, R8, JarJar, emulator, ADB, runtime mutation, rebuild, APK replacement, or Task 079 replay.
- No production fix and no edits to build logic, mappings, allowlist, tests, SDK, `libs/**`, AOSP source/out, generated artifacts, or any tracked path except the one issue.
- No new script. If Python is needed for an inline/read-only probe, invoke only `uv run python`; never `python`, `python3`, `pip`, or `uv pip`.
- No commit or push. No Herdr control actions by the worker.
- Do not claim Debug or Release runtime PASS.

## Acceptance evidence

- Frozen identities and clean/no-build preflight.
- A command already run that is deterministic, agent-runnable, and RED-capable for this exact old instruction reference; exact exit/output saved.
- Complete DEX entry + caller class + method/offset inventory, explicitly separating instruction references from definitions/self-reference/strings.
- Canonical program input and class SHA; AOSP source, `Android.bp`, and Soong artifact provenance.
- Membership matrix: caller(s) in 166 allowlist; dreams mapping in four frozen rules; dreams mapping in full 725 rules; relevant existing test/static-gate scope.
- 3–5 ranked hypotheses with prediction, evidence, and ACCEPTED/REJECTED verdict.
- Minimal root-cause statement and minimal proposed fix/regression-gate scope, without implementing it.
- Issue updated; `git diff --check`; only the issue may differ; no build/device mutation; terminal `HANDOFF:`.
