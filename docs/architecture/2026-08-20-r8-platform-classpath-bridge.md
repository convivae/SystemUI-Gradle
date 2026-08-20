# R8 Platform-Classpath Bridge — Architecture Report

| Field | Value |
|-------|-------|
| Date | 2026-08-20 (amended on architect FAIL review) |
| Task | 032 — R8 platform-classpath bridge |
| Status | Report-only (no code/SDK/tools mutated; report-only contract) |
| Author | Task 032 research worker |
| Primary sources | AOSP Soong (`build/soong/java/{dex,base,java,classpath_element}.go`), `build/soong/aconfig/codegen/java_aconfig_library.go`, `libcore/JavaLibrary.bp`, AGP 9.3.1, live `android-SysUISdk`, AOSP module jars |

> Companion to `docs/issues/2026-08-20-release-r8-alignment-decisions.md` and
> `docs/architecture/2026-08-20-aosp-release-config-analysis.md`.

## 1. Executive summary

The four "B-class" classes R8 flagged (Task 030 `missing_rules.txt`) reach AOSP
Soong R8 via **different** `-libraryjars` channels, and only one of them is the
platform bootclasspath. Per-class, after tracing actual Soong dependency tags:

| ID | Class | AOSP Soong R8 channel (proven) | Platform/device class? |
|----|-------|-------------------------------|------------------------|
| B2a | `libcore.io.IoUtils` | **Ch2 bootClasspath** (core-libart, ART bootclasspath fragment) | Yes — real libcore, device-provided |
| B2b | `libcore.util.NativeAllocationRegistry` | **Ch2 bootClasspath** (same) | Yes — real libcore, device-provided |
| B1 | `android.compat.annotation.UnsupportedAppUsage` | **Ch4 transitive header jars** (aconfig codegen `AddSharedLibrary` → flags-lib `libs:` → SystemUI-core static_libs transitive) | No — build-time CLASS-retention annotation library; no runtime provider required |
| B3 | `com.android.aconfig.annotations.AconfigFlagAccessor` | **Ch4 transitive header jars** (same path as B1) | No — build-time annotation; `@Retention(CLASS)`, not reflective at runtime |

**Root cause (proven):** AGP 9.3.1 R8 `-libraryjars` = `BaseR8Task.getBootClasspath()`
← `getFullBootClasspath()` + `core-for-system-modules.jar` + lambda-stubs, all
derived from the compileSdk platform dir. AGP has **no** equivalent of Soong's
Ch3/Ch4 (dexClasspath / transitive header jars as `-libraryjars`). So classes
that AOSP resolves via Ch3/Ch4 are invisible to AGP R8 unless they are placed on
the compileSdk bootclasspath (SysUISdk `android.jar`).

**Recommendation (per user-approved order, re-evaluated after the trace):**
- **B2 (IoUtils + NativeAllocationRegistry):** declarative SysUISdk injection —
  evidence supports it (real platform bootclasspath class). Faithful mirror.
- **B1 (UnsupportedAppUsage):** SysUISdk injection is the user-sanctioned
  structural bridge, but it is a **workaround** (AOSP uses Ch4, not bootclasspath),
  not a faithful channel mirror. The class needs no runtime provider
  (`@Retention(CLASS)`, non-reflective); AOSP supplies the definition to R8 via
  Ch4, not via packaging. SysUISdk injection is a Ch4→Ch2 workaround to expose a
  library definition to AGP R8 without packaging it into the APK — authorized by
  the user, not because the device provides the class.
- **B3 (AconfigFlagAccessor):** per user order, seek supported library input
  first → **none exists** (`useLibrary` covers only 6 predefined optional jars;
  aconfig is not among them) → exact single-class `-dontwarn` as last resort.

Live SDK mutation must go through `tools/build_sysuisdk.py --apply` only. The
structural SysUISdk/library bridge for B1+B2 and the exact B3 `-dontwarn` fallback
are directionally approved by the user on 2026-08-20 (per task brief Authority
and STATE.md); the
implementation task brief remains constrained to declarative
`build_sysuisdk.py --apply` + unit tests, no direct live SDK patch.

## 2. Soong R8 `-libraryjars` channels (proven, primary source)

`build/soong/java/dex.go` wires **four** `-libraryjars` inputs to R8:

| Ch | dex.go line | Source | Populated by (base.go tag dispatch) |
|----|-------------|--------|-------------------------------------|
| 1 | 446 | `proguardRaiseDeps` (`RepackagedHeaderJars` from `proguardRaiseTag` deps) | `proguardRaiseTag` (`java.go:575`); `FrameworkLibraries` appended at `java.go:679` |
| 2 | 450 | `flags.bootClasspath` | `bootClasspathTag` deps → `deps.bootClasspath` (`base.go:2449`); platform bootclasspath |
| 3 | 452 | `flags.dexClasspath` | `libTag`/`sdkLibTag`/`usesLibraryDependencyTag` (`libs:`) → `deps.dexClasspath` (`base.go:2456`) |
| 4 | 468 | `transitiveClasspath` (transitive libs header jars minus static-packaged) | `collectTransitiveHeaderJarsForR8` (`base.go:2125`) visits direct `libTag`/`staticLibTag` deps and collects transitive `TransitiveLibsHeaderJarsForR8` |

Ch4 is built in dex.go:454-468 as `transitiveLibsHeaderJarsForR8` minus
`transitiveStaticLibsHeaderJarsForR8` (to avoid re-listing jars already packaged
as static libs). The docstring at `base.go:2121-2124` describes these as "only used
to expand the --lib arguments to R8" — note this docstring says `--lib`, but the
actual wiring at dex.go:468 feeds `-libraryjars` (the `FormJavaClassPath("-libraryjars")`
call). Both are R8 library-class inputs.

**AGP 9.3.1 has no Ch3/Ch4 equivalent.** `BaseR8Task.getBootClasspath()` is the
sole library-classpath, and it is derived only from the compileSdk platform dir
(Ch2 analog). There is no public DSL to feed arbitrary transitive header jars as
`-libraryjars`.

## 3. Per-class Soong trace (proven)

### B2 — `libcore.io.IoUtils` + `libcore.util.NativeAllocationRegistry` → Ch2

| Field | Value |
|-------|-------|
| AOSP source | `libcore/luni/src/main/java/libcore/io/IoUtils.java`, `libcore/luni/src/main/java/libcore/util/NativeAllocationRegistry.java` |
| Soong module | `core-libart` (`libcore/JavaLibrary.bp:360`), `sdk_version: "none"` (line 384) |
| Bootclasspath membership | **Proven** via `art/build/boot/Android.bp:41,48-50` — the `bootclasspath_fragment` "art-bootclasspath-fragment" `contents:` explicitly lists `core-oj` (:49) and `core-libart` (:50). `build/soong/java/classpath_element.go:111-118` is the Soong reader of this fragment (explanatory, not the binding source). Not inferred from `sdk_version`. |
| R8 channel | Ch2 (`flags.bootClasspath`) — core-libart is on the platform bootclasspath, so its classes are library classes to every R8 run. |
| Direct reference | `IoUtils` is directly called by SystemUI source: `IoUtils.closeQuietly` at `SystemUI-core/src/com/android/systemui/controls/controller/ControlsFavoritePersistenceWrapper.kt:141,177` (import at :25; verified) |
| Runtime | device libcore provides these classes (platform bootclasspath); not in APK |
| Source jar (for injection) | `out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar` (already the S3 source for `patch_sdk_dalvik_annotations.py`) |
| Entries to inject | IoUtils + `$FileReader` (2); NativeAllocationRegistry + `$CleanerRunner` + `$CleanerThunk` + `$Metrics` (4) = **6 classes** |
| Absent from | live `android.jar`, `core-for-system-modules.jar`, `framework.jar`, `android-merged.jar` (verified); BUT **present** in `libs/android_module_lib_stubs_current.jar` (compileOnly) — compileOnly does not reach AGP R8 library input, so B2 is still missing from R8's `-libraryjars` |

### B1 — `android.compat.annotation.UnsupportedAppUsage` → Ch4

| Field | Value |
|-------|-------|
| AOSP source | `tools/platform-compat/java/android/compat/annotation/UnsupportedAppUsage.java` |
| Soong module | `unsupportedappusage` (`tools/platform-compat/.../Android.bp:59`), `sdk_version: "core_current"` |
| Retention | `@Retention(CLASS)`, `{@hide}` — in bytecode for R8, not reflective at runtime |
| How it reaches SystemUI-core R8 | **Proven** via `build/soong/aconfig/codegen/java_aconfig_library.go:74`: aconfig codegen calls `module.AddSharedLibrary("unsupportedappusage")` on every `java_aconfig_library` whose `sdk_version != none` (line 69). The SystemUI flags lib `com_android_systemui_flags_lib` has `sdk_version: "system_current"` → `addLibraries=true` → it gets `unsupportedappusage` as a `libs:` (libTag) dep. The flags lib is a `static_libs` dep of SystemUI-core, so `collectTransitiveHeaderJarsForR8` (`base.go:2125`) pulls the flags lib's transitive `libs` header jars (including `unsupportedappusage`) into SystemUI-core's Ch4 `transitiveClasspath`. |
| R8 channel | Ch4 (transitive header jars). **Not** Ch2 — `unsupportedappusage` is a `libs:` dep, not a `bootClasspathTag` dep. (It is also a `libs:` dep of `framework` at `frameworks/base/Android.bp:400` and `core/java/Android.bp:287`, but `libs:` → Ch3 dexClasspath, still not Ch2 bootclasspath.) |
| Referenced by | aconfig-generated flag bytecode (across the several generated flags jars — `systemui-flags.jar`, `settingslib-flags.jar`, etc.); verified via `strings` on `systemui-flags.jar`. SystemUI's own handwritten source does NOT reference it. Scope is "aconfig-generated flag bytecode", not mechanically proven to be a single `Flags.class` across all R8 program inputs. |
| Runtime | `@Retention(CLASS)` build-time annotation; non-reflective, so no runtime provider is required. AOSP supplies the definition to R8 via Ch4 (transitive header jars), not via packaging. Not in APK. |
| Source jar (if injected) | `out/soong/.intermediates/tools/platform-compat/.../unsupportedappusage/linux_glibc_common/javac/unsupportedappusage.jar` — **2 classes** (`UnsupportedAppUsage`, `$Container`) |
| Absent from | live `android.jar`, `core-for-system-modules.jar`, `framework.jar`, `android-merged.jar`, all `libs/` jars (verified) |

Note: the `app-compat-annotations` module (the 6-annotation set in `framework.jar`)
deliberately **excludes** `UnsupportedAppUsage` (`Android.bp:22` module srcs vs
`:42` `app-compat-annotations-source` filegroup). It lives in its own module.

### B3 — `com.android.aconfig.annotations.AconfigFlagAccessor` → Ch4

| Field | Value |
|-------|-------|
| AOSP source | `frameworks/libs/modules-utils/java/com/android/aconfig/annotations/AconfigFlagAccessor.java` |
| Soong module | `aconfig-annotations-lib` (`frameworks/libs/modules-utils/java/Android.bp`), `sdk_version: "core_current"` |
| Retention/target | `@Retention(CLASS)`, `@Target({METHOD})` — marker, no members (verified `AconfigFlagAccessor.java:37-39`) |
| How it reaches SystemUI-core R8 | **Proven** via `java_aconfig_library.go:72`: `module.AddSharedLibrary("aconfig-annotations-lib")`. Same Ch4 path as B1 (flags-lib `libs:` dep → SystemUI-core transitive header jars). |
| R8 channel | Ch4. **Not** Ch2. |
| Referenced by | aconfig-generated flag bytecode (the `@AconfigFlagAccessor` marker on flag accessor methods; across the several generated flags jars). Scope is "aconfig-generated flag bytecode", not a single `Flags.class`. |
| Runtime | `@Retention(CLASS)` build-time annotation; not reflective at runtime. Not in APK. |
| Source jar (if injected) | `out/soong/.intermediates/frameworks/libs/modules-utils/java/aconfig-annotations-lib/linux_glibc_common/javac/aconfig-annotations-lib.jar` — **5 classes** (`AconfigFlagAccessor`, `AssumeFalseForR8`, `AssumeTrueForR8`, `VisibleForTesting`, `VisibleForTesting$Visibility`) |
## 4. AGP 9.3.1 R8 library classpath (proven)

AGP's R8 task exposes its library classpath via a single `ConfigurableFileCollection`:

- `BaseR8Task.getBootClasspath()` — wired by `setBootClasspathForCodeShrinker` from
  `GlobalTaskCreationConfig.getFullBootClasspath()` + `core-for-system-modules.jar`
  (Java ≥ 9) + lambda-stubs (Java ≥ 8). This collection becomes R8's `-libraryjars`
  (the sole AGP library-classpath — the Ch2 analog).
- `getFullBootClasspath()` delegates to `BootClasspathConfigImpl` →
  `BootClasspathBuilder.computeClasspath()`, which takes **five**
  `VersionedSdkLoader` providers: `targetBootClasspath`, `targetAndroidVersion`,
  `additionalLibraries`, `optionalLibraries`, `annotationsJar`.
- All five resolve against the **compileSdk platform directory** (`android-SysUISdk`).

The only user-facing channels that add jars to this set:

| Channel | DSL | Scope | Covers B1–B3? |
|---------|-----|-------|----------------|
| `android.useLibrary` | `useLibrary "..."` | SDK `optional/*.jar` only (**6 jars**, verified: `android.car`, `android.test.base`, `android.test.mock`, `android.test.runner`, `org.apache.http.legacy`, `wear-sdk`) | No — none of the four classes are in `optional/` |
| `compileOnly` jars | `compileOnly(files(...))` | compile classpath, **not** R8 library classpath | No — `compileOnly` does not reach `BaseR8Task.getBootClasspath()` (this is exactly why B1–B3 are missing: the stubs/flags jars are compileOnly) |
| `data/annotations.zip` | (SDK-internal) | `annotationsJar` provider | No — verified empty for all four classes |

**Conclusion:** The only AGP-supported way to put a class on R8's `-libraryjars`
is to place it inside the SysUISdk platform jars (`android.jar` and/or
`core-for-system-modules.jar`). There is no supported DSL for Ch3/Ch4-equivalent
(transitive header jars as library classes).

## 5. Runtime (implementation/program-input) vs R8 library-classpath analysis

For each class, two questions: (a) is it a runtime **program** class (shrunk into
the APK) or an R8 **library** class (provided externally, not shrunk)? (b) should
it be in the APK?

| Class | Runtime provider | `@Retention` | In APK? | Correct R8 role |
|-------|-----------------|--------------|---------|-----------------|
| IoUtils | device libcore (platform bootclasspath) | n/a (real class) | No | library class (Ch2) |
| NativeAllocationRegistry | device libcore (platform bootclasspath) | n/a (real class) | No | library class (Ch2) |
| UnsupportedAppUsage | none (build-time CLASS-retention annotation; no runtime provider required) | CLASS | No | library class (Ch4 in AOSP) |
| AconfigFlagAccessor | none (build-time only) | CLASS | No | library class (Ch4 in AOSP) |

**Implication:** `implementation` (program class → shrunk into APK) is the
**wrong** semantic for all four — AOSP keeps them as library classes, not in the
APK. The user's note ("通常不应把 platform/build annotation 打进 APK") aligns.
So the only AGP-reachable correct semantic is placing them on the bootclasspath
(SysUISdk), which makes them library classes to R8 and keeps them out of the APK
(`android.jar` is compile/R8-only, never packaged).

## 6. Recommendation per class (respecting user-approved order)

User order (2026-08-20): first 3 (B1, B2a, B2b) may use declarative SysUISdk
**only if evidence supports it**; B3 (Aconfig) must first seek supported library
input, exact single-class `-dontwarn` is last resort. Do not broaden dontwarn.

### B2 (IoUtils + NativeAllocationRegistry) — SysUISdk injection (faithful)

**Evidence supports SysUISdk:** these are real platform bootclasspath classes
(Ch2, proven via `art/build/boot/Android.bp`). Injecting into `android.jar` +
`core-for-system-modules.jar` faithfully mirrors AOSP's Ch2. Sanctioned by
AGENTS.md §2.4 Rule F point 1. Reuse the `patch_sdk_dalvik_annotations.py` S3
pattern (idempotent, only-absent-entries, `.orig` backup, both jars patched).

### B1 (UnsupportedAppUsage) — SysUISdk injection (workaround, user-sanctioned)

**Evidence is mixed:** B1 reaches AOSP R8 via Ch4 (transitive header jars),
**not** Ch2 bootclasspath. So injecting it into `android.jar` is **not a faithful
channel mirror** — AOSP does not put it on the bootclasspath. The class needs no
runtime provider (`@Retention(CLASS)`, non-reflective); AOSP supplies the
definition to R8 via Ch4 only, not via packaging. SysUISdk injection is a
Ch4→Ch2 workaround to expose a library definition to AGP R8 without packaging it
into the APK — authorized by the user, not because the device provides the class.
No supported AGP DSL achieves this "library definition without packaging"
semantic for a non-platform class. The user sanctioned the structural bridge for
B1 ("first 3"), so this is the recommended path — but it must be labeled honestly
as a workaround that exposes a library definition via a different channel than
AOSP, not as "faithfully mirrors AOSP".

**Comparison to supported AGP paths:**
- `useLibrary`: no (not in `optional/`).
- `compileOnly`: already the case (stubs); doesn't reach R8 library classpath.
- `implementation`: wrong semantic (puts annotation in APK).
- `-dontwarn`: suppression only; R8 cannot read the annotation (build-time/R8-resolution, not runtime). B1 uses the structural bridge per 2026-08-20 user policy, not suppression.
- SysUISdk injection: workaround; achieves library-class semantic; user-sanctioned.

### B3 (AconfigFlagAccessor) — exact `-dontwarn` (last resort, per user order)

**Step 1 — seek supported library input:** `useLibrary` covers only the 6
`optional/` jars; aconfig is not among them (verified). No public bootclasspath
DSL. → **No supported library input exists.**

**Step 2 — SysUISdk injection?** Possible, but B3 is a build-time-only annotation
(`@Retention(CLASS)`, not reflective at runtime, no device provider). It reaches
AOSP via Ch4, not Ch2. Injecting a non-platform build-time annotation into
`android.jar` is a weaker semantic fit than B2 (real platform class) or even B1
(also non-platform, but user-sanctioned for the structural bridge). The user
order for B3 does **not** sanction SysUISdk — it sanctions seek-supported-library
→ dontwarn.

**Step 3 — exact single-class `-dontwarn` (last resort, user-approved):**

```
-dontwarn com.android.aconfig.annotations.AconfigFlagAccessor
```

**Why safe:** `AconfigFlagAccessor` is `@Retention(CLASS) @Target(METHOD)` marker
with no members (verified). R8 already cannot resolve it (it is missing), so
`-dontwarn` silences the warning without changing R8's behavior — R8 still cannot
read the annotation. It is not reflective at runtime, so stripping is harmless.

**Do not broaden:** only the single `AconfigFlagAccessor` class is approved. If
R8 also flags `AssumeTrueForR8`/`AssumeFalseForR8`, that is a **separate**
decision requiring its own authorization (those are R8-optimization annotations;
suppressing them may affect flag-assumption behavior). The Task 030 record
flagged only `AconfigFlagAccessor`; verify against the regenerated
`missing_rules.txt` before finalizing.

## 7. Live SDK mutation path (proven mechanism)

Live SysUISdk mutation is **only** via `tools/build_sysuisdk.py --apply` after
explicit user authorization (build_sysuisdk.py docstring lines 9-10, 33-34).
There is no direct "patched in place" path — `_live_guard` (line 99) hard-fails
if the staging target is the live SDK.

- `apply_to_live(source)` (line 579) syncs `APPLY_FILES = ("android.jar",
  "core-for-system-modules.jar", "framework.aidl")` from staging to live, with
  timestamped `<name>.bak-<ts>` backups of every differing live file.
- `stage_verify(target, live)` (line 519) = S5: compares staging vs live by entry
  names + CRC; reports per-file PASS/DIFF.

### New stage requirements (for the implementation task)

A new build_sysuisdk.py stage (e.g. `s3b`, after S3 and before S5) injecting
B1+B2 must:

1. **Patch tool**: generalize `patch_sdk_dalvik_annotations.py` to accept a
   package-list config (or add a sibling `patch_sdk_r8_platform_classes.py`).
   Preserve the S3 guarantees: idempotent, only-absent-entries, `.orig` backup,
   both `android.jar` + `core-for-system-modules.jar` patched, package-scoped.
2. **Stage function**: `stage_s3b(target, ...)` taking the source jars
   (`unsupportedappusage` javac, `core-libart` javac) and injecting the
   2 + 6 = 8 classes.
3. **Exact unit tests** (mirror `tools/tests/test_patch_sdk_dalvik_annotations.py`):
   - `test_lists_only_class_files_under_package` per package slice
   - `test_injects_only_missing_classes` (2 for B1, 6 for B2)
   - `test_idempotent_re_run_is_noop`
   - `test_does_not_overwrite_existing_entries`
   - `test_creates_orig_backup_on_first_mutation_only`
   - `test_patches_both_android_jar_and_core_for_system_modules`
   - `test_rejects_live_sdk_path` (via `_live_guard`)
   Plus a `test_build_sysuisdk.py` case: `stage_s3b` then S5 verify reports the
   8 entries as staging-only DIFF until `--apply` syncs them to live.
4. **S5 staging/live verification behavior**: until `--apply` runs, S5 must
   report the 8 injected entries as DIFF (staging has them, live does not).
   After `--apply`, S5 must report ALL PASS. The implementer patches live first
   (via `--apply`) or updates the verify baseline — never both out of sync.

## 8. Proven facts vs assumptions / unknowns

### Proven (primary-source verified)

1. Soong R8 has four `-libraryjars` channels (dex.go:446/450/452/468); Ch2 =
   `flags.bootClasspath`, Ch3 = `flags.dexClasspath`, Ch4 = `transitiveClasspath`,
   Ch1 = `proguardRaiseDeps`. (dex.go + base.go tag dispatch)
2. `core-libart` `sdk_version: "none"` (libcore/JavaLibrary.bp:360 name, :384 sdk);
   it IS on the platform bootclasspath — binding source
   `art/build/boot/Android.bp:41,48-50` (`bootclasspath_fragment` contents:
   `core-oj` :49, `core-libart` :50); `classpath_element.go:111-118` is the Soong
   reader (explanatory, not the proof). Not inferred from sdk_version. (verified)
3. B2 (IoUtils/NativeAllocationRegistry) reach R8 via Ch2. (art/build/boot/Android.bp)
4. B1 (UnsupportedAppUsage) reaches SystemUI-core R8 via Ch4:
   `java_aconfig_library.go:74` `AddSharedLibrary("unsupportedappusage")` →
   flags-lib `libs:` (libTag) → SystemUI-core static_libs transitive header jars.
   It is NOT on Ch2. (java_aconfig_library.go + base.go:2456/2118)
5. B3 (AconfigFlagAccessor) reaches via Ch4, same path (java_aconfig_library.go:72).
   NOT on Ch2. (verified)
6. `AddSharedLibrary` → `libs:` (libTag) → `deps.dexClasspath` (base.go:2456). The
   flags lib `com_android_systemui_flags_lib` has `sdk_version: "system_current"`
   ≠ none → `addLibraries=true` (java_aconfig_library.go:69). (verified)
7. AGP 9.3.1 R8 `-libraryjars` = `BaseR8Task.getBootClasspath()` ← compileSdk
   only; no Ch3/Ch4 equivalent; `useLibrary` covers 6 `optional/` jars;
   `compileOnly` does not reach R8 library classpath. (AGP source + verified)
8. Per-class absence (verified):
   - **B1 (UnsupportedAppUsage)** + **B3 (AconfigFlagAccessor)**: absent from
     live `android.jar`, `core-for-system-modules.jar`, `data/annotations.zip`,
     `framework.jar`, `android-merged.jar`, all `libs/` jars.
   - **B2 (IoUtils + NativeAllocationRegistry)**: absent from live `android.jar`,
     `core-for-system-modules.jar`, `framework.jar`, `android-merged.jar`; BUT
     present in `libs/android_module_lib_stubs_current.jar` (compileOnly).
     compileOnly does not reach AGP R8 library input
     (`BaseR8Task.getBootClasspath()`), so B2 is still missing from R8's
     `-libraryjars` despite the compileOnly jar.
9. Source jar class counts: `unsupportedappusage` (2), core-libart libcore slice
   (6), `aconfig-annotations-lib` (5). (verified via `unzip -l`)
10. `IoUtils` directly called by SystemUI source
    (`SystemUI-core/src/com/android/systemui/controls/controller/ControlsFavoritePersistenceWrapper.kt:141,177`,
    `IoUtils.closeQuietly` calls; import at :25). (verified)
11. `AconfigFlagAccessor` is `@Retention(CLASS) @Target(METHOD)` marker, no
    members. (verified AconfigFlagAccessor.java:37-39)
12. `build_sysuisdk.py --apply` is the only sanctioned live mutation path
    (`apply_to_live` line 579, `APPLY_FILES`, `_live_guard` line 99); S5
    `stage_verify` (line 519) compares staging vs live names+CRC. (verified)
13. AGENTS.md §2.4 Rule F point 1 sanctions patching SysUISdk with AOSP
    framework.jar / core-libart classes.

### Assumptions / unknowns (not yet traced)

1. **Ch1 (proguardRaiseDeps) for these classes.** Not traced whether any of the
   four reach via `proguardRaiseTag`. The recommendation does not depend on Ch1
   (Ch2/Ch4 are proven for these classes), but a complete trace would confirm.
2. **Whether R8 reads `AssumeTrueForR8`/`AssumeFalseForR8`.** Names imply R8
   consumes them, but R8 source was not traced. Task 030 flagged only
   `AconfigFlagAccessor`; verify against regenerated `missing_rules.txt`. If
   `Assume*ForR8` are also flagged, that is a separate decision (do not broaden
   the B3 dontwarn without separate authorization).
3. **`VisibleForTesting` collision.** `com.android.aconfig.annotations.VisibleForTesting`
   is a distinct package from `androidx.annotation.VisibleForTesting` and
   `com.google.common.annotations.VisibleForTesting`; collision unlikely. Not
   relevant to the B3 dontwarn (which targets only `AconfigFlagAccessor`); only
   relevant if B3 were ever injected (not recommended here).
4. **Whether `unsupportedappusage` is installed on the device at runtime.**
   Framework lists it as `libs:` (frameworks/base/Android.bp:400); `libs:` is
   classpath-only and does not package the dependency. The recommendation does
   **not** depend on a runtime provider: B1 is `@Retention(CLASS)` and
   non-reflective, so runtime resolution is unnecessary; AOSP supplies the
   definition to R8 via Ch4, and SysUISdk injection mirrors that (definition
   exposure, not runtime packaging). Whether the class physically exists on the
   device is immaterial to the R8 bridge decision.

Note: no claim appears in both "proven" and "assumption". B1/B3 Ch4
non-bootclasspath status is proven (not assumed); the open items are Ch1, R8
annotation consumption, and `VisibleForTesting` collision. (B1 device-runtime
location is now immaterial — see assumption #4.)

## 9. Risks

- **Authorization scope.** The 2026-08-20 user approval (per task brief Authority and STATE.md)
  directionally approves the structural SysUISdk/library bridge for B1+B2 and
  the exact B3 `-dontwarn` fallback. The earlier 2026-08-13 authorization
  (dalvik.annotation.optimization) is superseded for this scope. The
  implementation task brief remains constrained to declarative
  `build_sysuisdk.py --apply` + unit tests, no direct live SDK patch. No further
  Rule H escalation is required unless a precise unapproved product choice arises.
- **B1 semantic honesty.** SysUISdk injection for B1 is a workaround (Ch4→Ch2),
  not a faithful mirror. It achieves the correct library-class effect but via a
  different channel. Must be documented as such; do not claim it mirrors AOSP.
- **B3 dontwarn narrowness.** Only `AconfigFlagAccessor`; broadening to
  `com.android.aconfig.annotations.*` would mask `Assume*ForR8` and is forbidden.
- **Determinism.** Source jars are Soong `javac` variants (deterministic
  timestamps). The S3 pattern is already deterministic with these jars.
- **Kotlin/Compose pollution.** Injecting into `android.jar` changes the
  bootclasspath javac/KotlinCompile sees. Risk is low (annotation/libcore classes,
  no API surface change) but must be verified (`compileDebugKotlin` error count
  unchanged). If Compose inline errors reappear, halt (Rule H).

## 10. Primary-source citations

| Claim | Source (file:line) |
|-------|-------------------|
| Soong R8 Ch1 proguardRaiseDeps | `build/soong/java/dex.go:446`, `java.go:575,679` |
| Soong R8 Ch2 bootClasspath | `build/soong/java/dex.go:450`, `base.go:2449` |
| Soong R8 Ch3 dexClasspath | `build/soong/java/dex.go:452`, `base.go:2456` |
| Soong R8 Ch4 transitiveClasspath | `build/soong/java/dex.go:468`, `base.go:2125` (collectTransitiveHeaderJarsForR8 function; docstring 2121-2124) |
| core-libart module + sdk_version none | `libcore/JavaLibrary.bp:360` (name), `:384` (sdk_version) |
| core-libart on ART bootclasspath | `art/build/boot/Android.bp:41,48-50` (`bootclasspath_fragment` contents: `core-oj` :49, `core-libart` :50) |
| classpath_element.go (explanatory reader, not binding) | `build/soong/java/classpath_element.go:111-118` (Soong reader of the bp fragment) |
| B1/B3 reach via aconfig AddSharedLibrary | `build/soong/aconfig/codegen/java_aconfig_library.go:72,74` |
| AddSharedLibrary→libTag→dexClasspath | `base.go:2456` (libTag case) |
| flags-lib sdk_version system_current | `frameworks/base/packages/SystemUI/aconfig/Android.bp` |
| unsupportedappusage module | `tools/platform-compat/.../Android.bp:59` |
| app-compat-annotations excludes UnsupportedAppUsage | `tools/platform-compat/.../Android.bp:22` (module) vs `:42` (filegroup) |
| AconfigFlagAccessor retention/target | `frameworks/libs/modules-utils/java/com/android/aconfig/annotations/AconfigFlagAccessor.java:37-39` |
| IoUtils/NativeAllocationRegistry source | `libcore/luni/src/main/java/libcore/{io/IoUtils,util/NativeAllocationRegistry}.java` |
| IoUtils direct caller | `SystemUI-core/src/com/android/systemui/controls/controller/ControlsFavoritePersistenceWrapper.kt:141,177` (`IoUtils.closeQuietly` calls; import at :25) |
| AGP R8 library classpath = compileSdk | AGP 9.3.1 `BaseR8Task.getBootClasspath()`, `BootClasspathBuilder.computeClasspath()` |
| optional/ = 6 jars | `android-SysUISdk/optional/` (listed) |
| --apply only live mutation | `tools/build_sysuisdk.py:9-10,33-34,579` (`apply_to_live`), `:99` (`_live_guard`), `:519` (`stage_verify`) |
| S3 patch pattern | `tools/patch_sdk_dalvik_annotations.py` (full read) |
| Existing tests | `tools/tests/test_build_sysuisdk.py`, `tools/tests/test_patch_sdk_dalvik_annotations.py` |
| Rule F sanction | `AGENTS.md §2.4 point 1` |
