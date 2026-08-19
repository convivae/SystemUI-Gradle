# AGP androidprv namespace fix — build-logic repair (task 012)

Date: 2026-08-13 (implemented 2026-08-19 on branch `task-012`)
Status: implemented; androidprv goal met (0 errors); new latent layer exposed (SettingsLib AAR missing drawables) — escalated

## 1. Problem recap

`docs/architecture/2026-08-13-sysuisdk-reproducible-build.md` §8.2 established
two independent factors behind the 20 `androidprv:` link errors:

- **Factor 1** (stale framework resource table) — fixed by task 011's S4 overlay.
- **Factor 2** — AGP 9.3.1 `MergeResources` reserializes merged values XML and
  **drops `xmlns:androidprv`** because the prefix only occurs inside attribute
  *values*; serializers discard "unused" namespace declarations. Task 012
  addresses this factor.

Baseline on this branch (2026-08-19, `/tmp/task012-before.log`):

```
$ ./gradlew :app:processDebugResources --console=plain
BUILD FAILED in 18s        # failing task: :app:processDebugResources
$ grep -c androidprv /tmp/task012-before.log
20                          # 11 distinct symbols: 7 attrs, 2 colors, 2 styles
```

Live confirmation of Factor 2 in this checkout: the merger output
`app/build/intermediates/incremental/debug/mergeDebugResources/merged.dir`
contains **8** values XML files with `androidprv:` references (81 refs in
`values/values.xml` alone) and **0** declarations of
`http://schemas.android.com/apk/prv/res/android`.

## 2. Public API audit (AGP 9.3.1 `gradle-api-9.3.1.jar`)

Audited with `javap` against
`~/.gradle/caches/modules-2/files-2.1/com.android.tools.build/gradle-api/9.3.1/…/gradle-api-9.3.1.jar`:

- `com.android.build.api.artifact.SingleArtifact` constants: `AAR`, `APK`,
  `APK_FROM_BUNDLE`, `ASSETS`, `BUNDLE`, `MERGED_MANIFEST`,
  `MERGED_NATIVE_LIBS`, `OBFUSCATION_MAPPING_FILE`,
  `OBFUSCATION_MAPPING_PARTITION_FILE`, `PUBLIC_ANDROID_RESOURCES_LIST`,
  `RUNTIME_SYMBOL_LIST`, `VERSION_CONTROL_INFO_FILE`, `METADATA_LIBRARY_DEPENDENCIES_REPORT`,
  LINT reports. **No `MERGED_RES`.**
- `com.android.build.api.artifact.MultipleArtifact` constants:
  `MULTIDEX_KEEP_PROGUARD`, `NATIVE_DEBUG_METADATA`, `NATIVE_SYMBOL_TABLES`,
  `PRE_COMPILATION_CLASSES`. No merged resources.
- Grepping all `*Artifact*` classes for `MERGED_RES` finds nothing.
- `com.android.build.api.variant.Aapt2` **is public**:
  `Provider<RegularFile> getExecutable()`, `Provider<String> getVersion()`.

**Verdict:** AGP 9.3.1 exposes no public transformable merged-resource
artifact, so an artifact-transform repair is unavailable. The approved fallback
(post-merge/pre-link recompilation of affected values flats) is required.
The AAPT2 executable must come from `androidComponents.sdkComponents.aapt2`
(Kotlin DSL: `sdkComponents.aapt2.get().executable.get().asFile` — resolved at
execution time, not configuration time).

## 3. Mechanism (as implemented)

Per-variant Gradle task chain in `app/build.gradle.kts`:

```
merge<Variant>Resources → patch<Variant>AndroidPrvMergedResources → process<Variant>Resources
```

- `patch<Variant>AndroidPrvMergedResources` is an `Exec` task running
  `tools/patch_androidprv_merged_resources.py` with
  `--merged-dir`  = `build/intermediates/incremental/<v>/merge<V>Resources/merged.dir`
  `--compiled-dir` = `build/intermediates/merged_res/<v>/merge<V>Resources`
  `--aapt2` = from `sdkComponents.aapt2`
- The helper: scans merged values XML for `androidprv:` references; copies the
  affected files to a temp tree (`agp-merged-values-staging-*`); injects
  `xmlns:androidprv="http://schemas.android.com/apk/prv/res/android"` on the
  `<resources>` root of the copies; compiles each copy with the AGP-selected
  AAPT2 (`aapt2 compile <file> -o <dir>` → flat named
  `<parent-dir>_<stem>.arsc.flat`, identical to AGP's naming); atomically
  replaces only the matching flats. The merger XML and AOSP sources are never
  modified. Prints `scanned=<n> patched=<n> compiled=<n> unresolved=0`;
  exits non-zero on missing inputs, zero candidates, duplicate declarations,
  compile failure, or missing flats.
- The task declares no outputs and deliberately claims no ownership of AGP's
  output directories (narrow intermediate repair). Consequence: on the next
  build Gradle sees merge's outputs as changed, re-runs merge (regenerating
  unpatched flats), then the patch task re-applies. Deterministic, correct,
  slightly non-incremental — accepted.
- **Important ordering lesson (why a Gradle task is required):** replacing the
  flats externally *outside* a build makes `mergeDebugResources` out-of-date,
  so Gradle re-runs merge before link and overwrites the patched flats. The
  patch must run *mid-build* between merge and process; Gradle does not
  re-verify merge's outputs between tasks in the same build.

## 4. Evidence

### 4.1 Disposable hypothesis test (brief step 3)

Manual patch of temp copies + `aapt2 compile` + flat replacement + retry link:
all 20 `androidprv` errors eliminated (first attempt also showed 2
`settingslib_switch` errors — later proven to be a pre-existing masked layer,
see §5, not a patch artifact).

### 4.2 Test-first helper

- `tools/tests/test_patch_androidprv_merged_resources.py`: 15 tests covering
  namespace injection, duplicate-declaration failure, candidate selection,
  flat-name mapping, missing dirs, zero candidates, compile failure, missing
  flats, atomic replace, merged-dir immutability, idempotence, summary format.
  RED confirmed (ModuleNotFoundError) before implementation; GREEN after.
- Full suite: `python3 -m unittest discover -s tools/tests -p 'test_*.py'` →
  **Ran 131 tests, OK** (was 116).

### 4.3 Clean-state acceptance (brief step 6)

```
$ ./gradlew :app:clean :app:processDebugResources --console=plain
scanned=419 patched=8 compiled=8 unresolved=0
> Task :app:processDebugResources FAILED
BUILD FAILED in 5s
$ grep -c androidprv /tmp/task012.log
0
```

**androidprv goal met: 0 androidprv errors, helper unresolved=0.** The build
still fails on the new layer below.

### 4.4 APK diagnostics (brief step 7)

```
$ ./gradlew :app:assembleDebug --console=plain
> Task :app:processDebugResources FAILED
BUILD FAILED in 11s   # same settingslib_switch layer; no APK produced
```

## 5. New layer exposed: SettingsLib AAR missing drawables (escalated)

Once androidprv resolves, AAPT2 proceeds past values.xml line 14385 (the
highest line among the 20 baseline errors) and validates the rest of the file,
finding:

```
values/values.xml:15398: error: resource drawable/settingslib_switch_track not found.
values/values.xml:15399: error: resource drawable/settingslib_switch_thumb not found.
```

Root cause (evidence, 2026-08-19):

- The references come from style `ScreenRecord.Switch`
  (AOSP `SystemUI/res/values/styles.xml:973ff`, unchanged in our mirror).
- The drawables are defined in AOSP
  `SettingsLib/SettingsTheme/res/drawable-v31/settingslib_switch_{track,thumb}.xml`.
- Our tracked `libs/maven/com/android/systemui/SettingsLib/1.0.0/SettingsLib-1.0.0.aar`
  contains **no** `settingslib_switch*` drawables and no `drawable-v31/` dir
  (its `res/` only has `drawable/`, layouts, values...). Neither SystemUI-res
  nor any other dependency defines them.
- Hence this failure is a **pre-existing latent gap** in the packaged SettingsLib
  AAR, masked until now by the androidprv errors (AAPT2 stops validating a
  values file after earlier errors).

Fixing it requires re-packaging SettingsLib to include `SettingsTheme` res —
a dependency-artifact change outside task 012's Allowed Paths
(CHARTER Part 5.4 adjacent / rule R) → **REDLINE escalated**; not attempted.

## 6. Limitations

- The wiring hard-codes AGP's *internal* intermediate layout
  (`intermediates/incremental/<v>/…/merged.dir`, `intermediates/merged_res/…`).
  Audited on AGP 9.3.1; an AGP upgrade may move them (guard: the helper fails
  loudly with a non-zero exit rather than silently mis-linking).
- Merge is intentionally re-run every build (patch task owns no outputs).
- The patch recompiles every merged values file containing `androidprv:`
  (8 files / 20 KB-class each — negligible).
