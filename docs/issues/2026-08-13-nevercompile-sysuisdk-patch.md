# 2026-08-13 — Patch SysUISdk with dalvik.annotation.optimization classes (NeverCompile fix)

> Task 008 implementation record. Rule D (documentation first).
> Spec: `docs/architecture/2026-08-13-nevercompile-classpath-options.md` Option (a).
> Brief: `docs/orchestration/tasks/008-patch-sysuisdk-dalvik-annotations.md`.
> User pre-approval: 2026-08-13 ("同意a: Patch SysUISdk") — scoped to exactly
> the `dalvik.annotation.optimization.*` classes; any broader SDK change is
> forbidden.

## 1. Background

`:SystemUI-core:compileDebugJavaWithJavac` failed on 11 source files importing
`dalvik.annotation.optimization.NeverCompile` (20 errors, the last remaining
javac root-cause group after the 2026-08-13 修复波次 fixed the other 7 groups).
Root cause (spec §4.1): the SysUISdk `android.jar` / `core-for-system-modules.jar`
ship only `CriticalNative` + `FastNative` from that package (public-SDK slice),
so the package is resolved on the bootclasspath with a partial member set; javac's
bootclasspath-first package resolution then shadows the same classes that the
already-wired `compileOnly(android_module_lib_stubs_current.jar)` provides on
the regular compile classpath. Kotlin is unaffected (it merges the classpath).

Fix: Option (a) — inject the 4 missing optimization classes from AOSP
`core-libart` directly into the SDK jars so the bootclasspath package is
complete. Sanctioned by AGENTS.md §2.4 point 1 (patching SysUISdk `android.jar`
with AOSP framework/core-libart classes). No `build.gradle.kts` change, no new
tracked jar, no res.

## 2. Source jar

- Path: `/home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar`
- Variant: `javac/` (never `turbine`), `android_common_apex31`.
- Contains all 6 `dalvik/annotation/optimization/*.class`: `CriticalNative`,
  `DeadReferenceSafe`, `FastNative`, `NeverCompile`, `NeverInline`,
  `ReachabilitySensitive`.
- Env override: `CORE_LIBART_JAR`.

## 3. Injected class set (per target)

Injected = classes present in core-libart but absent from the target jar
(computed dynamically; existing entries are never overwritten):

- `dalvik/annotation/optimization/NeverCompile.class`
- `dalvik/annotation/optimization/NeverInline.class`
- `dalvik/annotation/optimization/DeadReferenceSafe.class`
- `dalvik/annotation/optimization/ReachabilitySensitive.class`

Pre-existing (untouched): `CriticalNative.class`, `FastNative.class`.

Scope boundary: only the `dalvik/annotation/optimization/` package is ever
injected — no other core-libart packages, no overwrites. This is the exact
scope of the user approval.

## 4. Targets & backups

| Target | Path | Backup created |
|---|---|---|
| android.jar | `/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar` | none — `android.jar.orig` already existed (2026-07-22 pre-merge pristine); preserved, not overwritten |
| core-for-system-modules.jar | `/home/conv/Android/Sdk/platforms/android-SysUISdk/core-for-system-modules.jar` | `core-for-system-modules.jar.orig` (new, created before first mutation) |

Backup policy: `<target>.orig` is created only if it does not already exist;
an existing `.orig` is never overwritten, so it always reflects the pristine
pre-any-mutation state.

## 5. Before / after (unzip counts)

`unzip -l <target> | grep 'dalvik/annotation/optimization/'`:

| Target | Before | After |
|---|---|---|
| android.jar | 3 lines (dir + CriticalNative + FastNative) | 7 lines (dir + 6 classes) |
| core-for-system-modules.jar | 3 lines (dir + CriticalNative + FastNative) | 7 lines (dir + 6 classes) |

(6 `.class` files + 1 bare directory entry = 7 grep matches; 4 injected + 2
pre-existing = 6 classes.) Idempotency verified: a second tool run reports
`already patched (no-op)` for both targets with `present: 6`.

## 6. Tool

`tools/patch_sdk_dalvik_annotations.py` (Python, ADR 0002). Idempotent, uses
`jar uf` (JDK 25) to update each target in place — preserving every existing
entry byte-for-byte and only adding the missing class entries. Creates the
`.orig` backup before the first mutation of each target. Prints a deterministic
summary of injected/already-present classes. Env overrides: `ANDROID_HOME` /
`ANDROID_SDK_ROOT` (SDK root), `CORE_LIBART_JAR` (source jar).

Tests: `tools/tests/test_patch_sdk_dalvik_annotations.py` — 12 tests covering
correct class set, idempotency, no-overwrite of existing entries, backup
creation, existing-backup preservation, no-mutation-when-complete, unrelated
entry preservation, and the package-scope boundary. Full suite:
`python3 -m unittest discover -s tools/tests -p 'test_*.py'` → Ran 77 tests, OK
(baseline was 65; +12).

## 7. Acceptance run (javac)

```
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain
```

Result (log `/tmp/task008.log`, re-verified in `/tmp/task008b.log`):

- Gradle exit code: **0**
- `BUILD SUCCESSFUL in 1m 41s` (first run; subsequent up-to-date run = 1s)
- `:SystemUI-core:compileDebugJavaWithJavac` → 0 errors, 2 warnings
  (`unknown enum constant Client.MODULE_LIBRARIES` /
  `class file for android.annotation.SystemApi$Client not found` — pre-existing,
  unrelated to this patch; and a `[dep-ann]` warning)
- `grep -c 'NeverCompile' /tmp/task008.log` → **0** (NeverCompile group gone)
- `grep -c 'error:' /tmp/task008.log` → **0** (javac milestone reached)
- Regression guard `grep -cE 'keepanno|monet|motiontool' /tmp/task008.log` → **0**
  (shadowing boundary intact; the other compileOnly jars still resolve)

**This is the javac milestone**: `:SystemUI-core:compileDebugJavaWithJavac` now
compiles with 0 errors. Prior to this task the 2026-08-13 修复波次 had reduced
the 42-error Task 7 set down to the 20-error NeverCompile group; this patch
resolves that final group.

## 8. ⚠️ SDK is not in git — re-run after a fresh SDK install

The SysUISdk at `/home/conv/Android/Sdk/platforms/android-SysUISdk/` is **not
version-controlled**. After cloning the repo onto a fresh machine (or after
re-installing/regenerating the SysUISdk), this patch must be re-applied:

```bash
python3 tools/patch_sdk_dalvik_annotations.py
```

The tool is idempotent, so re-running on an already-patched SDK is a safe
no-op. The `android.jar.orig` (2026-07-22 pristine) and
`core-for-system-modules.jar.orig` (this task) backups remain on disk as the
pre-mutation reference. The `compileOnly(android_module_lib_stubs_current.jar)`
line in `SystemUI-core/build.gradle.kts` is left in place as a harmless
redundant second source (Kotlin still uses it; javac now resolves from
`android.jar`).

## 9. Out of scope

- No `build.gradle.kts` change (Option (a) needs none).
- No `libs/` change, no new tracked jar.
- No `SystemUI-*/src/**` or `res/` change.
- Other Task 7 root-cause groups were already resolved by the 2026-08-13
  修复波次; `:app:assembleDebug` still has the `:app:processDebugResources`
  WM-Shell `android:featureFlag` AAPT `--feature_flags` blocker (AGENTS.md
  §4.2) — not touched here.
- The `android.annotation.SystemApi$Client` warning is pre-existing and
  unrelated; not investigated (out of scope).
