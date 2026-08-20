# Task 035 — R8 Runtime Closure Batch 3: protobuf-javalite + view_capture + motion_tool

## Goal

Implement the already-approved ordered Batch 3 closure: latest-stable official protobuf-javalite, deterministic clean view-capture/motion-tool JARs from owning Soong implementation outputs, the user-approved highest-compatible official coroutines pin, and exact R8 reduction 119→108 with zero additions.

## Read First

1. `AGENTS.md` in full
2. `docs/orchestration/CHARTER.md`
3. This brief
4. `docs/issues/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md`
5. `docs/superpowers/plans/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md`
6. `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §§3.1, 7 Batch 3

Then print the required `CONTRACT:` block before any edit.

## Authority

`redline-gated`

The user authorized continuing this Batch 3 in the current chat and has an existing hard preference to try the latest public stable dependency first. Therefore the exact `gradle/libs.versions.toml` addition `protobuf-javalite:4.35.1` is pre-approved **only if fresh Maven metadata still selects 4.35.1 as latest non-prerelease stable**.

**2026-08-20 REDLINE approval:** clean `view_capture.jar` exposed that the old FAT JAR had silently shadowed official coroutines 1.11.0 with AOSP coroutines 1.9.0. The worker proved the exact cause: 1.11.0 adds the `SharedFlow.collectLatest` overload; AOSP `isDozing: StateFlow<Boolean>` then makes `OriginalUnseenKeyguardCoordinator.kt:142` infer `Nothing`. Both debug and release compilation fail with 1.11.0, while a temporary, reverted official Maven 1.10.2 probe succeeds. The user chose the architect's recommendation: preserve AOSP source exactly and use the highest compatible official version. Maven metadata shows 1.10.2 is the immediately preceding stable release, so changing only `kotlinxCoroutines = "1.11.0"` to `"1.10.2"` is now explicitly authorized. Do not test or adopt a lower version unless 1.10.2 fails a fresh required acceptance command; in that case halt with a new `REDLINE`.

Worker commits but never pushes. No source/res/SDK red-line area is authorized.

## Allowed Paths

- `tools/package_viewcapture_motiontool_jars.py` (new)
- `tools/tests/test_package_viewcapture_motiontool_jars.py` (new)
- `libs/view_capture.jar` (replace)
- `libs/motion_tool_lib.jar` (replace)
- `gradle/libs.versions.toml` (protobuf-javalite 4.35.1 version + alias; user-approved `kotlinxCoroutines` 1.11.0→1.10.2 compatibility pin only)
- `SystemUI-core/build.gradle.kts` (only Batch 3 dependency scopes/comments)
- `SystemUI-shared/build.gradle.kts` (only view-capture/protobuf runtime edges/comments)
- `docs/issues/2026-08-20-r8-runtime-batch3-viewcapture-motiontool.md`
- `/tmp/task035-*` evidence files (outside git)

## Forbidden Paths

- All `SystemUI-*/src/**`, `SystemUI-*/res*/**`, and every `res/` file
- `AGENTS.md`, `docs/adr/**`, `docs/orchestration/CHARTER.md`
- `settings.gradle.kts`, module includes/boundaries, manifests
- `app/build.gradle.kts`, ProGuard/R8 rule files, SysUISdk/live SDK
- `libs/maven/**`, `libs/aars/**`, `tools/install_aar_to_maven.py`
- Any existing dependency version/alias except the protobuf-javalite additions and the exact user-approved `kotlinxCoroutines` 1.11.0→1.10.2 change
- Batch 4 AARs, Traceur, SettingsLib, WM-Shell, iconloader, or B1–B4 bridge work

## Mandatory Constraints

- Follow the plan in order: fresh 119 baseline → TDD packager → clean view/protobuf → motion-tool → debug → fresh R8.
- Inputs must be owning Soong `javac`/`kotlin` implementation outputs, never turbine/header/combined/FAT outputs.
- Output class sets must be exactly:
  - view-capture: 56 classes under `com/android/app/viewcapture/` from contributions 9+23+24;
  - motion-tool: 65 classes under `com/android/app/motiontool/` from contributions 8+57.
- Package class entries only; reject namespace pollution, duplicate classes, missing/invalid/empty inputs; deterministic byte-identical output.
- No stub, resource/source modification, keep/dontwarn, source exclusion, disabled check, local-Maven JAR, silent protobuf downgrade, or compile-only coroutines shadow JAR.
- Keep official protobuf-javalite at 4.35.1. Set the shared official coroutines version to exactly 1.10.2; this is the highest compatible stable version proven by the red-line investigation. If a fresh required command fails because of 1.10.2, preserve evidence and halt with a new `REDLINE` rather than lowering it or modifying source.
- `AssumeTrueForR8` remains untouched and present.
- Piped Gradle commands use `set -o pipefail`, save full logs, and record `${PIPESTATUS[0]}`.
- All waits/polls ≤90 seconds; use process info plus logs, not agent status alone.
- If 4.35.1 causes a real incompatibility or R8 delta differs, preserve evidence and halt with `REDLINE`; do not improvise.

## Acceptance

All commands and expected results are mandatory:

1. **Fresh pre-change R8:** `:app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` → true exit 1, exactly 119 refs, all 11 targets + `AssumeTrueForR8` present.
2. **Focused tests:** `python3 -m unittest tools.tests.test_package_viewcapture_motiontool_jars` → six tests, `OK`.
3. **Full tests:** `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → 160 tests, `OK`.
4. **Artifacts:** twice running `python3 tools/package_viewcapture_motiontool_jars.py --all` gives identical SHA-256; exact class counts/namespaces 56 and 65.
5. **Debug:** after the exact coroutines 1.10.2 pin, `:app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4` → true exit 0, `BUILD SUCCESSFUL`; the AOSP mirrored source remains untouched.
6. **APK definitions:** one `apkanalyzer dex packages --defined-only` output contains `C d` rows for ViewCapture, ExportedData, MotionToolManager, MotionToolsRequest, GeneratedMessageLite.
7. **Fresh post-change R8:** true exit remains 1 at missing classes; exact set delta 119→108, exactly the issue's 11 refs removed, 0 added, `AssumeTrueForR8` retained.
8. **Hygiene:** `git diff --check` clean; changed files are a subset of Allowed Paths; issue contains actual evidence.
9. **Delivery:** one focused English commit, no push, terminal-final `HANDOFF:` block.

## Reports To

Architect in the main herdr session. On any red line print:

```text
REDLINE: <area> — <attempt, evidence, and exact decision needed>
```

On completion print:

```text
HANDOFF:
- done: <what changed>
- verified: <commands and actual outputs>
- remaining: <none, or exact blocker>
```
