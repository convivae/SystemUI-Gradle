# Task 036 — R8 Runtime Closure Batch 4A: iconloader Kotlin AAR

## Goal

Complete the existing iconloader AAR with its owning Soong Kotlin implementation output, replace local-Maven `iconloader:1.0.0` with the user-approved `1.0.1`, and prove an exact R8 109→106 delta with no additions.

## Read First

1. `AGENTS.md` in full
2. `docs/orchestration/CHARTER.md`
3. This brief
4. `docs/issues/2026-08-20-r8-runtime-batch4a-iconloader.md`
5. `docs/superpowers/plans/2026-08-20-r8-runtime-batch4a-iconloader.md`
6. `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §§3.1 A11, 5.3, 7 Batch 4

Then invoke `worker-contract`, print the required `CONTRACT:` block, invoke `superpowers:test-driven-development`, and begin only after the contract is visible.

## Authority

`redline-gated`

The user explicitly approved the design and the local AAR coordinate change `com.android.systemui:iconloader:1.0.0`→`1.0.1` in the current chat. This authorizes only the exact iconloader version changes listed in Allowed Paths. Worker commits but never pushes. No source/res/SDK, dependency scope, other coordinate, or module red line is authorized.

## Allowed Paths

- `tools/package_aosp_aar.py` (iconloader config only)
- `tools/tests/test_package_aosp_aar.py` (iconloader tests only)
- `tools/install_aar_to_maven.py` (iconloader registry version only)
- `tools/tests/test_install_aar_to_maven.py` (iconloader coordinate test only)
- `libs/aars/iconloader.aar`
- `libs/maven/com/android/systemui/iconloader/1.0.0/iconloader-1.0.0.aar` (delete)
- `libs/maven/com/android/systemui/iconloader/1.0.0/iconloader-1.0.0.pom` (delete)
- `libs/maven/com/android/systemui/iconloader/1.0.1/iconloader-1.0.1.aar` (create)
- `libs/maven/com/android/systemui/iconloader/1.0.1/iconloader-1.0.1.pom` (create)
- `gradle/libs.versions.toml` (only `systemui-iconloader` 1.0.0→1.0.1)
- `docs/issues/2026-08-20-r8-runtime-batch4a-iconloader.md`
- `/tmp/task036-*` evidence files outside git

## Forbidden Paths

- All `SystemUI-*/src/**`, `SystemUI-*/res*/**`, and every source or `res/` file
- `SystemUI-core/build.gradle.kts` and all other module build files; iconloader scope is already correct
- `AGENTS.md`, `docs/adr/**`, `docs/orchestration/CHARTER.md`
- `settings.gradle.kts`, module includes/boundaries, manifests
- `app/build.gradle.kts`, ProGuard/R8 rules, SysUISdk/live SDK
- Any AAR/local-Maven artifact except the exact iconloader paths above
- Any version/catalog coordinate except exact `systemui-iconloader` 1.0.0→1.0.1
- Traceur, SettingsLib, SettingsTheme, WM-Shell, or B1–B4 bridge work

## Mandatory Constraints

- Follow the plan in order: fresh 109 baseline → failing tests → minimal config/version changes → deterministic artifact → debug/APK → fresh R8.
- Use only owning Soong `javac/iconloader.jar` and `kotlin/iconloader.jar`; no turbine/header/combined/FAT input.
- Output class bytes/set must be the exact disjoint union 59+16=75, under `com/android/launcher3/**`.
- Preserve AOSP `res/**`, `AndroidManifest.xml`, and Soong `R.txt` exactly; do not edit any resource.
- Keep `implementation(libs.systemui.iconloader)` unchanged.
- Remove superseded local-Maven `1.0.0`; install selected iconloader only at `1.0.1`; AAR bytes must match `libs/aars/iconloader.aar`; POM has no dependencies.
- No stub, keep/dontwarn, source exclusion, disabled check, direct source/resource edits, or scope broadening.
- `AssumeTrueForR8` and all non-iconloader missing refs remain untouched.
- Piped Gradle commands use `set -o pipefail`, save full logs, and record `${PIPESTATUS[0]}`.
- All waits/polls are at most 90 seconds; use pane output, logs and real processes together.
- Any R8 delta other than exact 109→106 with three removals and zero additions is a `REDLINE`, not permission to improvise.

## Acceptance

1. **Fresh baseline:** `:app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` → true exit 1, exactly 109 refs, all three targets present.
2. **TDD red/green:** focused tests first fail for missing Kotlin input/old coordinate, then five selected tests pass.
3. **Full tests:** `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → 164 tests, `OK`.
4. **Artifact:** two `python3 tools/package_aosp_aar.py iconloader` runs have identical SHA-256; exact input/output class-byte union 59+16=75; resource/meta provenance exact.
5. **Local Maven:** only iconloader `1.0.1` remains; installed AAR byte-identical; POM version/package/no-deps exact; catalog points to 1.0.1 and no other version changes.
6. **Debug:** `:app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4` → true exit 0, `BUILD SUCCESSFUL`.
7. **APK:** one `apkanalyzer ... --defined-only` output has `C d` rows for all three target classes.
8. **Fresh R8:** true exit 1 at remaining missing classes; exactly 109→106, removed exact three, added empty, `AssumeTrueForR8` retained.
9. **Hygiene:** `git diff --check` clean; changed files are a subset of Allowed Paths; issue records actual evidence.
10. **Delivery:** one focused English commit, no push, terminal-final `HANDOFF:`.

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
