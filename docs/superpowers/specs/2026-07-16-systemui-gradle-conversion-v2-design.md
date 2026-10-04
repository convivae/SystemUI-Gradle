# SystemUI Gradle Conversion v2 — Full Rewrite Design

**Date:** 2026-07-16
**Status:** Draft (awaiting user approval)
**Author:** Cursor Agent
**Supersedes:** `2026-04-30-systemui-gradle-conversion-design.md`
**Technical reference:** `/home/conv/myspace/CarSystemUIGradle` — key commit `c0ae96b`

> **Important:** `CarSystemUIGradle` is a third-party (JD) project and is used
> **only as a technical reference** — i.e. we look at how it solves Gradle
> migration problems. We do **not** inherit its codebase conventions:
> - No `// JD MOD:` style code annotations — we use plain `// SYSOPS:` or
>   project-neutral comments.
> - No JD-specific app names (`JDCarSystemUI`), keystores, or namespace
>   suffixes (`com.android.systemui.car`).
> - No dependency on JD-only AARs (`car-ui-lib`, `car-uxr-client-lib`, …).

## 1. Background and Motivation

The previous spec (April 2026) aimed to make the SystemUI module from AOSP
(`/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/`) compilable
under Gradle while preserving a dual-build story (Gradle for development,
Android.bp for AOSP integration). That spec emphasized non-interference with
AOSP and preserving source layout.

The user has now re-scoped the work:

- The project's purpose is to **rewrite SystemUI from scratch as a Gradle
  project**, not to wrap the existing AOSP source tree.
- All source code is allowed to be **copied locally** from
  `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/` and adapted.
- Third-party dependencies (AndroidX, Compose, Material, Kotlinx, Dagger,
  Guava, …) are fetched **online via Gradle** when needed.
- The project must continue to **compile under both Gradle and Android.bp
  when placed inside the AOSP source tree** — i.e. dual build.
- The **first deliverable is the dual-build skeleton**, with the actual
  SystemUI functionality filled in later, iteratively.
- Hidden platform APIs are made available via the **real AOSP-compiled
  `framework.jar`** (not stub classes).

## 2. Goals (in priority order)

1. **G1 — Gradle dual-compile skeleton works.** `./gradlew :app:assembleDebug`
   in this repo (without an AOSP checkout) produces a signed SystemUI APK.
2. **G2 — Android.bp build works in-tree.** Copying this repo into
   `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/` and running
   `m SystemUI` (or `mm frameworks/base/packages/SystemUI`) compiles.
3. **G3 — No external runtime dependency on AOSP.** No symlinks pointing
   out of this repo. `framework.jar` and any AOSP-specific prebuilts are
   copied locally.
4. **G4 — Idiomatic Gradle 9.x setup.** Uses `libs.versions.toml` version
   catalogs, `build.gradle.kts`, KMP-aware source sets.
5. **G5 — Iterative feature completeness.** The skeleton initially builds a
   minimal SystemUI (essentially a no-op service entry point); features are
   ported module by module.

## 3. Non-Goals

- Supporting build environments older than AGP 9 / Gradle 9.
- Keeping the existing partial AOSP-copy layout that mixes `res-keyguard/`
  files alongside untouched AOSP code.
- Replacing every AOSP hidden API with public SDK calls — that would
  require a behavior rewrite and is out of scope for the skeleton.
- R8/ProGuard release builds in v1 of the skeleton; debug builds only.

## 4. High-Level Architecture

```
SystemUI-Gradle/                          <- standalone repo
├── Android.bp                            <- AOSP build entry
├── AndroidManifest.xml                   <- SystemUI's main manifest
├── CleanSpec.mk                          <- AOSP clean rules
├── OWNERS
├── build.gradle.kts                      <- root Gradle script
├── settings.gradle.kts                   <- includes :app and modules
├── gradle.properties
├── gradle/
│   ├── wrapper/                          <- gradlew wrapper jar+props
│   └── libs.versions.toml                <- version catalog
├── gradlew, gradlew.bat
├── libs/
│   ├── framework.jar                     <- AOSP-compiled (copied, not symlink)
│   ├── platform/                         <- AOSP platform classes used by tooling
│   └── prebuilts/                        <- AOSP-only AARs (WindowManager-Shell, etc.)
├── keystore/                             <- platform signing keys
├── app/
│   ├── build.gradle.kts
│   └── src/main/...                      <- SystemUI service + entry classes
├── SystemUI-core/                        <- compileOnly shared library code
├── SystemUI-shared/                      <- shared utilities (prebuilt jar)
├── SystemUI-animation/                   <- (prebuilt jar in v1)
├── SystemUI-customization/               <- (prebuilt jar in v1)
├── SystemUI-plugin-core/                 <- (compiled source)
├── SystemUI-plugin/                      <- (prebuilt jar in v1)
└── tools/
    ├── sync_aosp_sources.sh              <- one-shot copy from aosp/
    ├── extract_prebuilts.sh              <- copies AOSP-only AARs into libs/prebuilts/
    └── install_sdk.sh                    <- installs the SysUISdk platform
```

### Module layout

The AOSP layout puts everything under
`frameworks/base/packages/SystemUI/` as one giant module with sub-folders.
We mirror that for the Gradle build by treating each top-level sub-folder as
a separate Gradle module. For v1 the split is:

| Gradle module        | AOSP source folder                          | Build type        |
|----------------------|---------------------------------------------|-------------------|
| `:app`               | `src/` (main SystemUI service)              | `com.android.application` |
| `:SystemUI-core`     | `src/com/android/systemui/`                | `com.android.library`     |
| `:SystemUI-shared`   | `shared/`                                   | prebuilt jar      |
| `:SystemUI-plugin-core` | `plugin_core/`                           | `com.android.library`     |
| `:SystemUI-plugin`   | `plugin/`                                   | prebuilt jar      |
| `:SystemUI-animation` | `animation/`                              | prebuilt jar      |
| `:SystemUI-customization` | `customization/`                       | prebuilt jar      |

**Prebuilt jars** (for v1): For modules we haven't yet ported, we copy the
AOSP-compiled `*.jar` output into
`libs/prebuilts/SystemUI-<module>.jar` and reference it as
`compileOnly(files(...))` from `:app` and `:SystemUI-core`. This lets the
skeleton link and run before we finish porting all the Java source.

### Source-set layout per module

Each library module uses the same source-set naming convention as AOSP to
keep `Android.bp` parallel:

```
SystemUI-core/
├── build.gradle.kts
└── src/
    ├── main/
    │   ├── AndroidManifest.xml
    │   ├── java/...
    │   ├── res/...
    │   ├── res-keyguard/...
    │   └── aidl/...
    ├── debug/
    │   └── java/...
    └── proto/
        └── ...
```

`aidl/` uses `aidl.srcDirs` and proto uses `proto.srcDirs` plus the
`com.google.protobuf` plugin.

## 5. Dependency Strategy

### 5.1 Online (Maven Central / Google Maven)

Resolved by Gradle through `settings.gradle.kts`:

```kotlin
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
```

All third-party libraries — AndroidX, Material, Compose, Kotlinx,
Dagger, Guava, Protobuf — are declared in `libs.versions.toml` and pulled
at build time. No offline Maven mirror is needed.

### 5.2 AOSP-only libraries (local)

Some libraries are not published to Maven Central and only exist inside
the AOSP tree (e.g. `WindowManager-Shell`, `SystemUISharedLib`,
`SettingsLib`, `iconloader`, `WifiTrackerLib`). These are extracted from
AOSP build outputs once, copied into `libs/prebuilts/`, and declared as
local dependencies in `libs.versions.toml`:

```toml
[versions]
windowManagerShell = "1.0"

[libraries]
systemui-windowManagerShell = { module = "com.android.systemui:WindowManager-Shell", version.ref = "windowManagerShell" }
```

with a matching flatDir/AAR resolution block in `settings.gradle.kts`.

The extraction script `tools/extract_prebuilts.sh` automates this from
`/home/conv/myspace/aosp/out/soong/.intermediates/...` paths.

### 5.3 framework.jar (compileOnly)

`/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/turbine-combined/framework.jar`
is copied to `libs/framework.jar` once and used as a `compileOnly`
dependency. The same trick the CarSystemUI project uses is applied
here: the root `build.gradle.kts` prepends `framework.jar` to every
Java/Kotlin compile classpath so hidden APIs are visible.

### 5.4 Custom SDK platform

We install a custom SDK platform named `SysUISdk` that contains the
AOSP-extended `android.jar` (resources and stub classes for hidden
APIs). This was already created at
`/home/conv/Android/Sdk/platforms/android-SysUISdk/` and works in the
prior CarSystemUI project. We document the install procedure in
`tools/install_sdk.sh`.

Each module uses:

```kotlin
android {
    compileSdkPreview = "SysUISdk"
}
```

with `android.suppressUnsupportedCompileSdk=SysUISdk` in
`gradle.properties`.

## 6. Dual Build (Gradle + Android.bp)

### 6.1 Goal

When this repo is placed at
`/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/` and the
AOSP build system runs, `Android.bp` should describe the same modules
in AOSP terms (`android_library`, `android_app`).

### 6.2 Approach

- All Java/Kotlin sources live in `src/...` directories that match the
  AOSP layout, so `Android.bp` `srcs:` paths can be shared with Gradle's
  `sourceSets.main.java.srcDirs`.
- `Android.bp` declares modules with the AOSP names
  (`SystemUI-core`, `SystemUI-shared`, `app`, …) and uses
  `aaptflags: ["--rename-manifest-package", "com.android.systemui"]` for
  the Gradle side's namespace (the previous CarSystemUI trick).
- `gradle.properties` carries
  `android.experimental.disableCompileSdkChecks=true` and
  `android.useNonFinalResourceIds=false` to match AOSP behaviour.
- `CleanSpec.mk` mirrors what CarSystemUI has.

### 6.3 Manifest package vs Gradle namespace

The Gradle `:app` module uses `namespace = "com.android.systemui"` (which
is what AOSP expects). The previous attempt used
`"com.android.systemui.res"` to dodge an R-class collision; we revert
that and instead fix the collision by using
`android.nonTransitiveRClass=true` plus carefully scoped `res` source
sets per library module — same pattern as CarSystemUI.

## 7. Repository Hygiene

- `.gitignore` excludes:
  - `.gradle/`, `build/`, `local.properties`
  - `.idea/`, `*.iml`
  - `captures/`
- All large JARs/AARs **are committed** to keep the repo self-contained.
  - `framework.jar` (~70MB)
  - `prebuilts/*.jar` and `prebuilts/*.aar` (~500MB combined)
- Git LFS is **not** used; we just commit binaries directly. (Total
  repo size stays under ~1GB, which is acceptable.)

## 8. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| AGP 9 / Gradle 9 still has rough edges | Pin to known-good AGP 9.2.0 + Gradle 9.5.0 combination that worked in the prior attempt; document fallback to AGP 8.7 if needed. |
| framework.jar changes whenever AOSP is rebuilt | Document the refresh procedure; commit a snapshot; treat framework.jar as versioned binary. |
| AOSP-only prebuilt AARs change between AOSP versions | Same as above; each `tools/extract_prebuilts.sh` run is checked into git. |
| Manifest package collision when dual building | Use `aaptflags: ["--rename-manifest-package", "com.android.systemui"]` + `nonTransitiveRClass`. |
| Kotlin metadata mismatch with AOSP | Set `kotlinJvmTarget` to a version that matches AOSP's `kotlinc` (currently 2.0+). |

## 9. Deliverable for v1 (the skeleton)

A repo that:

1. Clones cleanly and `./gradlew :app:assembleDebug` succeeds without
   AOSP checkout (other than the framework.jar / prebuilts that are
   committed).
2. Produces a SystemUI APK that boots to a stub "Hello SystemUI"
   notification surface.
3. Has `Android.bp` + `CleanSpec.mk` committed so that placing the repo
   inside an AOSP tree and running `m SystemUI` succeeds.
4. Documents in `docs/GRADLE_MIGRATION_LOG.md` what is left to port.

The actual SystemUI feature work is **explicitly deferred** to v2 (and
later), as agreed with the user.

## 10. Open Questions

None — the brainstorming Q&A answered all design-defining questions.

## 11. Migration Log Discipline

This project inherits a long-running, multi-task Gradle migration. To keep
the work reviewable and to avoid losing solutions to problems we have
already solved, we maintain `docs/GRADLE_MIGRATION_LOG.md` as a living
document. Every non-trivial problem we hit during the build MUST be
recorded there before the task is marked done.

### 11.1 When to write an entry

Write an entry when **any** of the following happens during a task:

- The build fails and we change source / config / dependency to fix it.
- A hidden API or AOSP-specific class is referenced and we have to teach
  Gradle where to find it (or accept the limitation).
- A resource is missing, renamed, or duplicated and we patch it.
- A `// SYSOPS:` annotation is added to source code (see 11.4).
- A prebuilt AAR/JAR is added to `libs/` (record source path).
- A new module, source set, or build flag is introduced.
- AGP / Gradle / Kotlin version behaviour bites us.

**Do not** write entries for routine stuff like "added a new file" or
"updated a dependency version".

### 11.2 Required structure per entry

Each entry follows a fixed schema so entries are easy to scan:

```markdown
## 问题 N：<short title>

### 问题描述
<error message, command, or symptom, verbatim where possible>

### 问题分析
<root cause — what is actually happening?>

### 解决方案
<the change we made — file paths + diff/commands, not vague>

### 修改文件
- <path> — <one-line reason>

### 制品来源（如适用）
| 文件 | 来源 | 说明 |
|------|------|------|
| X.jar | /home/conv/myspace/aosp/out/soong/.../X.jar | purpose |

### 状态
✅ 已解决 / ⚠️ 部分解决 / ❌ 未解决
```

The Chinese headers (`问题描述`, `问题分析`, `解决方案`, `修改文件`, `制品来源`,
`状态`) are kept because the project predates this spec and the existing
log uses them. **Do not change the schema** — append entries only.

### 11.3 Numbering

Numbering is global across the whole log (`问题一`, `问题二`, …). Before
adding a new entry, `grep -c '^## 问题' docs/GRADLE_MIGRATION_LOG.md` and
use the next integer.

### 11.4 Source code annotation convention

When we patch AOSP-copied source to make it compile under Gradle, the
patch is marked with a short comment **immediately above** the change:

```kotlin
// SYSOPS: <one-line reason>
```

Rules:

- Use `// SYSOPS:` (project-neutral). **Never** use `// JD MOD:` —
  that belongs to the third-party reference project.
- One line only; longer explanation goes into the migration log.
- Place the comment at the **smallest enclosing scope** that still makes
  sense (line above a class, a method, or a single statement).
- For Kotlin use `//`, for Java use `//`, for XML/manifest use
  `<!-- SYSOPS: ... -->`.
- The comment must be in English (matches the rest of the project).

Examples:

```java
// SYSOPS: private Dagger modules must be internal under Gradle/Kapt
@Module
internal abstract class InternalCoordinatorsModule { ... }
```

```xml
<!-- SYSOPS: renamed manifest package for BP compilation -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.android.systemui">
```

### 11.5 Commit hygiene

- Each task commit MUST include the migration log entry if one was
  produced.
- Commit messages in this repo follow the pattern:
  `<area>: <imperative summary>` (e.g. `build: pin AGP 9.2.0`,
  `docs(migration): add 问题十八`). See `git log --oneline` for
  precedent.
- Large binary additions (`libs/*.jar`) go in their **own commit** with
  the `vendor:` prefix and reference the migration log entry in the
  body (e.g. `vendor: add WindowManager-Shell.aar — see 问题二十六`).

### 11.6 What we do not record

- Trivial typo fixes.
- Dependency version bumps that just work.
- Routine file moves/refactors.
- Anything whose explanation would be longer than the fix itself.

### 11.7 Examples from the reference project (informational only)

The reference project `CarSystemUIGradle/docs/GRADLE_MIGRATION.md` has 35
entries documenting its migration. We use the **same schema** (problem →
analysis → solution → files changed → status) but a different prefix
(`SYSOPS:` instead of `JD MOD:`) and a different starting count (we
inherit the existing 6 categories of unresolved issues from the v1
attempt and continue numbering from where they leave off).

Categories of issues that are **expected to recur** in this project,
based on what the reference ran into:

1. Missing source directories in `sourceSets`.
2. Missing JAR/AAR dependencies (resolved via `tools/extract_prebuilts.sh`).
3. Kotlin Dagger visibility (`private` → `internal`).
4. `nonTransitiveRClass` and resource ID mismatches.
5. Hidden API references requiring `framework.jar` on classpath.
6. BP vs Gradle package-name collision
   (`--rename-manifest-package` trick).
7. Custom SDK Platform (`SysUISdk`) for framework-private resource IDs.
8. Lifecycle / WindowManager-Shell / WifiTrackerLib runtime crashes.
9. AOSP-only AARs not on Maven Central.
10. Platform signing for system-app install.

The migration log captures our version of each.