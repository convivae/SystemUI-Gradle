# NeverCompile classpath gap — background research

> Task 005 (docs-only research). Produced 2026-08-13.
> Companion: `docs/issues/2026-08-12-current-progress-standards-review.md` §Task 7
> (group "NeverCompile"). Brief: `docs/orchestration/tasks/005-nevercompile-research.md`.
>
> **Scope: research only.** No build file, jar, or SDK was modified to produce this
> document. All command evidence below was re-run on 2026-08-13 in the task-005
> worktree unless noted otherwise (the Task 7 failing build ran in the main
> worktree `/home/conv/myspace/SystemUI-Gradle/`; sources and classpath are
> identical).

---

## 1. Problem statement

`./gradlew :app:assembleDebug` fails in `:SystemUI-core:compileDebugJavaWithJavac`
with, for each of 11 source files:

```
.../SomeFile.java:167: error: cannot find symbol
import dalvik.annotation.optimization.NeverCompile;
                                     ^
  symbol:   class NeverCompile
  location: package dalvik.annotation.optimization
```

(Source: `/tmp/final-app.log` lines 238–283, captured 2026-08-12 13:10.)

`NeverCompile` is an AOSP `@SystemApi(client = MODULE_LIBRARIES)` annotation in
`libcore/dalvik/src/main/java/dalvik/annotation/optimization/NeverCompile.java`,
`@Retention(CLASS)`, `@Target(METHOD)`, no-op at runtime — it only instructs
the ART ahead-of-time compiler (dex2oat) to skip compiling the annotated method.
It therefore has **no runtime behavior**; the class need only be present at
**compile time**.

The non-obvious part: the class **is already available** in a `compileOnly` jar
that is already wired into `:SystemUI-core`. The gap is a classpath/SDK-layering
bug, not a missing dependency. Sections 2–5 establish this with command evidence;
section 6 gives three fix options with a recommendation.

---

## 2. Usage in SystemUI (step 1)

```bash
$ grep -rn 'NeverCompile' SystemUI-core/src SystemUI-*/src 2>/dev/null
```

11 unique source files import and apply `@NeverCompile` (each import line +
each annotation line, so the grep prints 22 lines; deduped file list):

1. `SystemUI-core/src/com/android/keyguard/KeyguardUpdateMonitor.java:167,4158`
2. `SystemUI-core/src/com/android/systemui/qs/QSImpl.java:73,1022`
3. `SystemUI-core/src/com/android/systemui/ScreenDecorations.java:98,1124`
4. `SystemUI-core/src/com/android/systemui/volume/VolumeDialogControllerImpl.java:82,340`
5. `SystemUI-core/src/com/android/systemui/shade/NotificationPanelViewController.java:239,3461`
6. `SystemUI-core/src/com/android/systemui/shade/QuickSettingsControllerImpl.java:108,2074`
7. `SystemUI-core/src/com/android/systemui/model/SysUiState.java:28,131`
8. `SystemUI-core/src/com/android/systemui/statusbar/connectivity/NetworkControllerImpl.java:86,1165`
9. `SystemUI-core/src/com/android/systemui/statusbar/notification/logging/NotificationMemoryDumper.kt:28,43`
10. `SystemUI-core/src/com/android/systemui/statusbar/phone/CentralSurfacesImpl.java:240,1786`
11. `SystemUI-core/src/com/android/systemui/navigationbar/NavigationBarControllerImpl.java:67,483`

All are `@NeverCompile` on methods (debug/dump or rarely-called paths), matching
the annotation's documented purpose. The `.kt` file (`NotificationMemoryDumper`)
means the class must be visible to **both** `compileDebugKotlin` and
`compileDebugJavaWithJavac`. The Task 7 run reports Kotlin already compiles
cleanly (0 errors) and only javac fails — see §4 for why the two compilers
behave differently here.

No other `dalvik.annotation.optimization.*` member is used in SystemUI
(`NeverInline`, `DeadReferenceSafe`, `ReachabilitySensitive` return 0 hits).

---

## 3. Where the class really lives (step 2)

### 3.1 AOSP source

```
/home/conv/myspace/aosp/libcore/dalvik/src/main/java/dalvik/annotation/optimization/
├── CriticalNative.java
├── DeadReferenceSafe.java
├── FastNative.java
├── NeverCompile.java        ← @SystemApi(client=MODULE_LIBRARIES), @Retention(CLASS), @Target(METHOD)
├── NeverInline.java
└── ReachabilitySensitive.java
```

### 3.2 Soong `core-libart` javac jar — **contains all 6**

```bash
$ unzip -l /home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar | grep 'dalvik/annotation/optimization/'
      410  dalvik/annotation/optimization/CriticalNative.class
      416  dalvik/annotation/optimization/DeadReferenceSafe.class
      402  dalvik/annotation/optimization/FastNative.class
      633  dalvik/annotation/optimization/NeverCompile.class
      650  dalvik/annotation/optimization/NeverInline.class
      439  dalvik/annotation/optimization/ReachabilitySensitive.class
```

### 3.3 Soong `art.module.public.api.stubs.module_lib` combined jar — **contains 4**

```bash
$ unzip -l /home/conv/myspace/aosp/out/soong/.intermediates/libcore/art.module.public.api.stubs.module_lib/android_common/combined/art.module.public.api.stubs.module_lib.jar | grep 'dalvik/annotation/optimization'
      410  dalvik/annotation/optimization/CriticalNative.class
      402  dalvik/annotation/optimization/FastNative.class
      406  dalvik/annotation/optimization/NeverCompile.class
      423  dalvik/annotation/optimization/NeverInline.class
```

### 3.4 Our `libs/android_module_lib_stubs_current.jar` (already in git, already wired) — **contains 4**

```bash
$ unzip -l libs/android_module_lib_stubs_current.jar | grep 'dalvik/annotation/optimization/'
      410  dalvik/annotation/optimization/CriticalNative.class
      402  dalvik/annotation/optimization/FastNative.class
      406  dalvik/annotation/optimization/NeverCompile.class
      423  dalvik/annotation/optimization/NeverInline.class
```

### 3.5 Absence from the three places javac searches first

```bash
# SysUISdk android.jar (compileSdk bootclasspath) — has the PACKAGE but only 2 of 6 classes
$ unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar | grep 'dalvik/annotation/optimization/'
      410  dalvik/annotation/optimization/CriticalNative.class
      402  dalvik/annotation/optimization/FastNative.class
# NeverCompile: ABSENT

# core-for-system-modules.jar in SysUISdk — same partial set
$ unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/core-for-system-modules.jar | grep 'dalvik/annotation/optimization'
      410  dalvik/annotation/optimization/CriticalNative.class
      402  dalvik/annotation/optimization/FastNative.class
# NeverCompile: ABSENT

# libs/framework.jar (injected into JavaCompile.bootstrapClasspath by root build.gradle.kts)
$ unzip -l libs/framework.jar | grep -i 'dalvik/annotation/optimization'
# (rc=1) — no dalvik.* entries at all
```

### 3.6 The wire is already there

```bash
$ grep -n 'android_module_lib_stubs_current' SystemUI-core/build.gradle.kts
152:    // 添加 android_module_lib_stubs_current.jar 提供缺失的 framework stub
153:    compileOnly(files("${rootProject.projectDir}/libs/android_module_lib_stubs_current.jar"))
```

`git log -S` shows this `compileOnly` line and the jar have been present since
commit `000b1261` (2026-07-21). **So the class is on the compile classpath via
a tracked, rule-compliant tier-② jar — yet javac still cannot resolve it.** This
is the central finding that drives the option analysis in §6.

---

## 4. Why AOSP javac sees the class but ours does not (step 3)

`frameworks/base/packages/SystemUI/Android.bp` `android_library "SystemUI-core"`
does **not** list `core-libart` or any `dalvik.*` provider in `libs:`/`static_libs:`:

```bash
$ sed -n '423,560p' /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/Android.bp | grep -n 'libs\|core\|optimization'
2:    name: "SystemUI-core",
19:    static_libs: [
50:    androidx.slice_slice-core",
94:    libs: [
136:    static_libs: [
```

The only `libs:` entry is `keepanno-annotations` (line 516). So SystemUI never
declares `NeverCompile` explicitly — it reaches javac through the **platform
default bootclasspath**: every `android_library`/`android_app` in Soong compiles
against the platform's `core-for-system-modules` / `core-libart`, which carries
the full `dalvik.annotation.optimization.*` set (§3.2). Soong's
`core-for-system-modules` for the **module-lib** SDK (the one
`android_library` targets) does contain `NeverCompile`:

```bash
$ unzip -l /home/conv/myspace/aosp/out/soong/.intermediates/prebuilts/sdk/sdk_module-lib_34_core-for-system-modules/android_common/combined/sdk_module-lib_34_core-for-system-modules.jar | grep NeverCompile
      406  dalvik/annotation/optimization/NeverCompile.class   # HAS
```

Our SysUISdk's `core-for-system-modules.jar`, by contrast, is the **public-SDK**
variant (only `CriticalNative` + `FastNative`, §3.5). That is the proximate
origin of the gap: the SysUISdk was built/selected from a public SDK slice
that omits the `@SystemApi(client = MODULE_LIBRARIES)` annotations.

### 4.1 The shadowing mechanism (why the wired compileOnly jar does not help)

The Task 7 error message is diagnostic:

```
error: cannot find symbol
import dalvik.annotation.optimization.NeverCompile;
  symbol:   class NeverCompile
  location: package dalvik.annotation.optimization   ← package IS visible
```

`location: package X` (rather than `package X does not exist`) means javac
**found the package** `dalvik.annotation.optimization` but not the class in it.
The only place that partial package lives is the compileSdk `android.jar`
(bootclasspath) — which has `CriticalNative`/`FastNative` but not `NeverCompile`
(§3.5).

This is the classic **bootclasspath split-package shadowing**: when a package
is resolved on the bootclasspath, javac does **not** merge in additional
members of that same package from the regular compile classpath. The
`compileOnly` `android_module_lib_stubs_current.jar` (regular classpath) has
`NeverCompile.class`, but because `android.jar` already "owns"
`dalvik.annotation.optimization` on the bootclasspath, that class is invisible
to javac.

### 4.2 Proof that compileOnly itself works

Other `compileOnly` jars in the same `build.gradle.kts` resolve their classes
without error, confirming the `compileOnly(files(...))` mechanism is on the
javac classpath and functional:

```bash
$ grep -c 'keepanno\|KeepTarget\|UsesReflection' /tmp/final-app.log   # keepanno is compileOnly
0
$ grep -c 'motiontool\|monet\.\|ColorScheme' /tmp/final-app.log        # motion_tool_lib + monet are compileOnly
0
$ grep -c 'NeverCompile' /tmp/final-app.log                            # only NeverCompile fails
80
```

`keepanno-annotations.jar`, `monet.jar`, `motion_tool_lib.jar` are all
`compileOnly` and all resolve. The differentiator for `NeverCompile` is
exactly that its package **also exists on the bootclasspath `android.jar`** —
which none of the keepanno/monet/motiontool packages do
(`com.android.tools.r8.keepanno.*`, `com.android.systemui.monet.*`,
`com.android.app.motiontool.*` are not in `android.jar`).

### 4.3 Why Kotlin compiles but javac does not

The Task 7 record reports `:SystemUI-core:compileDebugKotlin` = 0 errors while
`compileDebugJavaWithJavac` fails on the same import. Kotlin's type resolver
does not treat the compileSdk `android.jar` as a non-mergeable bootclasspath
owner for split packages; it searches the full compile classpath (where
`android_module_lib_stubs_current.jar` provides `NeverCompile`). javac's
bootclasspath-first package resolution is stricter. (Note: root
`build.gradle.kts` deliberately does **not** inject `framework.jar` into
KotlinCompile — §2.4 — but that is unrelated to this specific gap; the
difference here is javac vs. Kotlin classpath semantics, not framework.jar.)

### 4.4 Could not reproduce the exact bootclasspath behavior standalone

Modern javac (target 25) rejects `-Xbootclasspath/a:` and `-Xbootclasspath/p:`
("option not allowed with target 25"), so the AGP bootclasspath layering could
not be reproduced in isolation with the default JDK. The diagnosis above rests
on (a) the error message shape, (b) the presence of `NeverCompile.class` in the
wired compileOnly jar, (c) the presence of the partial
`dalvik.annotation.optimization` package on `android.jar`, and (d) the
control case (keepanno/monet/motiontool compileOnly jars resolving). A
plain classpath split (two `-cp` jars) merges correctly in standalone javac,
confirming the failure is specific to the **bootclasspath vs. classpath**
boundary, not split packages in general.

---

## 5. Reference project (step 4)

```bash
$ grep -rn 'NeverCompile\|dalvik' /home/conv/myspace/CarSystemUIGradle --include='*.kts' --include='*.md'
# (no NeverCompile references in source)
$ grep -rn 'android_module_lib_stubs_current' /home/conv/myspace/CarSystemUIGradle --include='*.kts'
app/build.gradle.kts:132:        compileOnly(files("${rootProject.projectDir}/libs/android_module_lib_stubs_current.jar"))
SystemUI-core/build.gradle.kts:94:    compileOnly(files("${rootProject.projectDir}/libs/android_module_lib_stubs_current.jar"))
```

Findings:

- CarSystemUIGradle uses the **same mechanism** we already use
  (`compileOnly(android_module_lib_stubs_current.jar)`) — it did not invent a
  different solution.
- CarSystemUIGradle's SystemUI sources (CarSystemUI) **do not use
  `@NeverCompile` at all**, so the bootclasspath shadowing never triggers
  there. The class is on the classpath but never imported; the partial package
  on `android.jar` is never asked for `NeverCompile`.
- The Car SDK (`compileSdkPreview = "JdJkcSdk"`) is not installed on this
  machine (`/home/conv/Android/Sdk/platforms/` has no `android-JdJkcSdk`), so
  its `android.jar` optimization-package contents could not be inspected. Even
  if it happened to ship a complete package, that would not generalize to our
  SysUISdk, which demonstrably ships the partial set (§3.5).

**Conclusion: the reference project does not solve this gap; it sidesteps it
by not importing the annotation. Our project hits it because phone SystemUI
uses `@NeverCompile` on 11 files.**

---

## 6. Options and recommendation

All three options below are **compile-time only** (the annotation is
`@Retention(CLASS)` and a no-op at runtime; no dex/runtime change, no APK
size impact, no behavioral change). Runtime implications are therefore
identical across options and limited to "annotation metadata is present in
the .class files, ART ignores it on a non-AOSP runtime."

Provenance compliance is the deciding axis (rules F and R; AGENTS.md §2.4
explicitly allows patching SysUISdk `android.jar` with AOSP `framework.jar`/
`core-libart` classes; tier-② jar packaging is the flags-jar precedent).

### Option (a) — Patch SysUISdk `android.jar` (and/or `core-for-system-modules.jar`)

**What:** Merge the missing `dalvik.annotation.optimization.*` classes from
the AOSP `core-libart` javac jar (§3.2) into
`/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar` (and, for
consistency, `core-for-system-modules.jar`). A small Python tool (ADR 0002)
extracts just those 4 classes (`NeverCompile`, `NeverInline`,
`DeadReferenceSafe`, `ReachabilitySensitive`) from the Soong jar and
`jar uf`'s them into the SDK jars. Idempotent; mirrors the existing
`tools/install_sdk.py` pattern for `framework.aidl`.

**Provenance:** Rule F explicitly sanctions patching SysUISdk with AOSP
`framework.jar`/`core-libart` classes (AGENTS.md §2.4 point 1). The source is
AOSP `libcore`, not hand-written. Rule R untouched (no res).

**Runtime:** None (`@Retention(CLASS)`, no-op annotation).

**Pros:**
- Fixes the **root cause**: the bootclasspath package becomes complete, so
  javac resolves `NeverCompile` directly from `android.jar`. No build-file
  change, no new tracked jar on the compile classpath, no shadowing.
- Also fixes the latent `NeverInline` gap (present in
  `android_module_lib_stubs_current.jar` but shadowed) and future-proofs
  against `DeadReferenceSafe`/`ReachabilitySensitive` if SystemUI adopts them.
- No `compileOnly`/`implementation` change in any module's `build.gradle.kts`
  → stays clear of CHARTER Part 5 "version matrix / module boundaries".
- Helps every module that ever imports these annotations, not just `:SystemUI-core`.

**Cons:**
- Modifies the shared SysUISdk (outside the repo, at
  `/home/conv/Android/Sdk/...`). Not version-controlled; must be recorded in
  `docs/issues/` and ideally scripted (`tools/install_sdk.py` extended) so a
  fresh machine can reproduce. This is the same trade-off already accepted for
  the `framework.aidl` patches and the `framework.jar`/android.jar merge done
  on 2026-07-22 (AGENTS.md §4.1).
- Touching the SDK is a user-authorization area (rule F / CHARTER Part 5 —
  "SysUISdk is patchable" but the act of patching should be user-gated like
  other SDK regenerations).

### Option (b) — A new tracked `compileOnly` dalvik-annotations jar on the **bootclasspath**

**What:** A Python tool (flags-jar precedent: `tools/package_aconfig_jars.py`)
packages the 6 `dalvik.annotation.optimization.*` classes from the AOSP
`core-libart` javac jar into `libs/dalvik-optimization-annotations.jar`, and
the root `build.gradle.kts` injects it into
`JavaCompile.bootstrapClasspath` **ahead of** `android.jar` (exactly the
existing `framework.jar` injection pattern, AGENTS.md §2.4 / root
`build.gradle.kts`).

> ⚠️ **Critical caveat discovered by this research:** putting this jar on the
> **regular** `compileOnly` compile classpath (as
> `android_module_lib_stubs_current.jar` already is) **will not work** because
> of the bootclasspath split-package shadowing documented in §4.1. Option (b)
> is viable **only** if the jar is placed on `JavaCompile.bootstrapClasspath`,
> where it merges with `android.jar`'s package on the boot side. A plain
> `compileOnly(files(...))` declaration is insufficient — that is precisely
> the configuration that is already failing today.

**Provenance:** Tier-② AOSP artifact (no res), packaged by a Python tool,
tracked in git. Rule-compliant. Rule F is not violated (no framework source
copied into a SystemUI module; the classes live in a jar).

**Runtime:** None.

**Pros:**
- Reproducible from source (`tools/package_dalvik_annotations.py` +
  `libs/dalvik-optimization-annotations.jar` committed). No out-of-repo SDK
  mutation; a fresh clone + `./gradlew` sees the same classpath.
- Sits next to `framework.jar` in the existing bootstrapClasspath injection,
  so the mechanism is already understood and documented.

**Cons:**
- Requires a `build.gradle.kts` change in the **red-line adjacent** area
  (CHARTER Part 5.4 "dependency version matrix" / build configuration). Must
  be user-authorized. The root build already injects `framework.jar` into
  `JavaCompile.bootstrapClasspath` only (not KotlinCompile — §2.4); the same
  restriction would apply here, and Kotlin already resolves the class via the
  regular classpath, so Kotlin is unaffected.
- Introduces a new tracked jar + tool, increasing the surface that must be
  kept in sync with AOSP.
- Ordering matters: the annotations jar must appear on `bootstrapClasspath`
  before `android.jar`, and **must not** be shadowed by `framework.jar`
  (framework.jar has no `dalvik.*` entries, §3.5, so this is safe).

### Option (c) — Extend the existing `libs/keepanno-annotations.jar` mechanism

**What:** Add the 4 missing `dalvik.annotation.optimization.*` classes to the
existing `libs/keepanno-annotations.jar` (currently `compileOnly`,
`com.android.tools.r8.keepanno.*` only) and keep its `compileOnly`
declaration.

> ⚠️ **Same caveat as (b), fatal here:** `keepanno-annotations.jar` is
> `compileOnly` on the **regular** compile classpath. Per §4.1, a regular
> classpath jar cannot contribute classes to a package that already exists on
> the `android.jar` bootclasspath. Adding `NeverCompile` to
> `keepanno-annotations.jar` would therefore **not** resolve the javac error.
> To make (c) work, `keepanno-annotations.jar` would have to be moved to
> `JavaCompile.bootstrapClasspath` — at which point (c) is just (b) with a
> reused filename and a co-mingled package, which is worse for provenance
> clarity (one jar carrying two unrelated upstream origins: r8 keepanno +
> libcore dalvik).

**Provenance:** Mixing two upstream origins (r8 keepanno from
`prebuilts/r8/keepanno-annotations.jar`, dalvik annotations from
`libcore/core-libart`) into one tracked jar muddies provenance and makes
regeneration non-idempotent. Not recommended on those grounds alone.

**Runtime:** None.

**Pros:**
- No new jar filename; reuses an existing `compileOnly` line.

**Cons:**
- **Does not work** without moving the jar to the bootclasspath (§4.1), which
  defeats the "reuse existing compileOnly line" benefit.
- Co-mingles two unrelated upstreams in one artifact → provenance regression
  (rules F/R spirit; ADR 0001 hygiene).
- `keepanno-annotations.jar` today is a verbatim copy of the AOSP prebuilt;
  repackaging it breaks that 1:1 correspondence and complicates future
  upgrades.

### Recommendation

**Option (a) — patch SysUISdk `android.jar` (and `core-for-system-modules.jar`)
with the 4 missing `dalvik.annotation.optimization.*` classes from AOSP
`core-libart`, via a Python tool that extends the `tools/install_sdk.py`
idiom.**

Reasoning:

1. It fixes the actual root cause (the bootclasspath package is incomplete)
   rather than working around it. The other options only work if they
   effectively also put the classes on the bootclasspath, which is what (a)
   does directly.
2. It is explicitly sanctioned by AGENTS.md §2.4 point 1 ("将 AOSP
   `framework.jar` 的类合并/暴露到 SysUISdk `android.jar`") and follows the
   2026-07-22 precedent (AGENTS.md §4.1: "合并 SDK android.jar + framework.jar").
3. It requires **no** `build.gradle.kts` change and **no** new tracked compile
   dependency, keeping the module graph and version matrix untouched — the
   cleanest path w.r.t. CHARTER Part 5.
4. It is the only option that also closes the latent `NeverInline` shadowing
   gap and future-proofs `DeadReferenceSafe`/`ReachabilitySensitive`.
5. It keeps the already-correct, rule-compliant
   `compileOnly(android_module_lib_stubs_current.jar)` line as a harmless
   redundant second source (Kotlin still uses it; javac will resolve from
   `android.jar`).

**Required guardrails if (a) is chosen:**
- User authorization first (rule F / CHARTER Part 5 — patching SysUISdk).
- Implement as a Python tool (`tools/install_sdk.py` extension or a new
  `tools/patch_sdk_dalvik_annotations.py`), idempotent, recording the exact
  AOSP source jar + class list in `docs/issues/`.
- Re-verify `:SystemUI-core:compileDebugJavaWithJavac` resolves all 11
  `NeverCompile` imports and that `keepanno`/`monet`/`motiontool` still
  resolve (regression guard for the shadowing boundary).
- Record the patch in `docs/HANDOFF.md` / `docs/CURRENT_STATE.md` so a fresh
  machine knows to re-run the tool after cloning (the SDK is not in git).

**If the user does not want to mutate the shared SDK**, option (b) with the
**bootclasspath** placement (not plain `compileOnly`) is the second-best
choice and is fully in-repo/reproducible; option (c) is not recommended.

---

## 7. Evidence index (commands re-run 2026-08-13)

| Step | Command | Key result |
|---|---|---|
| 1 | `grep -rn 'NeverCompile' SystemUI-core/src SystemUI-*/src` | 11 files use `@NeverCompile` |
| 2 | `unzip -l .../core-libart/.../javac/core-libart.jar \| grep optimization` | all 6 classes present |
| 2 | `unzip -l libs/android_module_lib_stubs_current.jar \| grep optimization` | 4 classes present, incl. NeverCompile |
| 2 | `unzip -l SysUISdk/android.jar \| grep optimization` | only CriticalNative + FastNative |
| 2 | `unzip -l SysUISdk/core-for-system-modules.jar \| grep optimization` | only CriticalNative + FastNative |
| 2 | `unzip -l libs/framework.jar \| grep dalvik` | no dalvik.* entries |
| 2 | `grep -n android_module_lib_stubs_current SystemUI-core/build.gradle.kts` | line 153, `compileOnly` |
| 3 | `sed -n 423,560p .../SystemUI/Android.bp` | no `core-libart`/`dalvik` in libs/static_libs |
| 3 | `unzip -l sdk_module-lib_34_core-for-system-modules.jar \| grep NeverCompile` | present (module-lib SDK has it) |
| 4 | `grep -rn NeverCompile /home/conv/myspace/CarSystemUIGradle` | 0 hits (CarSystemUIGradle sidesteps) |
| 4 | `grep android_module_lib_stubs_current CarSystemUIGradle/**/*.kts` | same mechanism, compileOnly |
| 4.2 | `grep -c keepanno /tmp/final-app.log` → 0; `grep -c NeverCompile` → 80 | compileOnly works; only NeverCompile fails |
| 4.4 | `javac -Xbootclasspath/a:...` | rejected by target 25; could not reproduce standalone |

## 8. Out of scope (per brief)

- No build file, jar, SDK, or source was modified.
- No `tools/` script was written (the options describe tools that a future
  implementation task would create, with user authorization).
- Other Task 7 root-cause groups (setupcompat, zxing, wifi/wm-shell flags,
  shared Dagger factories, SystemUI-tags, media version) are tracked in
  `docs/issues/2026-08-12-current-progress-standards-review.md` and the
  implementation plan `docs/superpowers/plans/2026-08-12-build-to-apk-readiness.md`;
  not investigated here.
