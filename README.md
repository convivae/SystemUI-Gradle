# SystemUI-Gradle

A standalone, self-contained Gradle build of the Android SystemUI source tree — designed to compile independently of the AOSP build system while remaining compatible with it.

> **Status:** active development — see [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) for the live snapshot.
> As of 2026-08-19, debug/release KSP, core Kotlin, and core javac pass with
> **0 errors**. Feature-flag linking, reproducible SysUISdk/framework resources,
> and AGP's dropped `androidprv` namespace are fixed. `:app:assembleDebug` is now
> blocked at `:app:processDebugResources` because the tracked SettingsLib AAR lacks
> two AOSP SettingsTheme switch drawables, so no APK is produced yet. See the
> [androidprv issue record](docs/issues/2026-08-13-agp-androidprv-namespace-fix.md).

---

## Why

AOSP's SystemUI is normally built inside the AOSP source tree using Blueprint (`Android.bp`) and Soong. While this works well for AOSP itself, it makes the module hard to:

- modify and iterate on with Android Studio / a fast Gradle build loop;
- use as a library or standalone project outside the full AOSP checkout;
- version, branch, or code-review independently of the platform.

This project extracts SystemUI from AOSP, ports it to a pure Gradle build (Gradle 9.5 + AGP 9.3.1 +
Kotlin 2.2.10 via AGP `builtInKotlin`), and packages every dependency it needs so that the project
compiles without ever reaching back into the AOSP tree.

A reference implementation that informed many of the choices here is [`CarSystemUIGradle`](../CarSystemUIGradle) (commit `c0ae96b`) — a sibling project that did the same thing for the Car SystemUI.

---

## Goals

1. **Build independently.** No symlinks to the AOSP tree. Every needed `.class`, `.jar`, `.aar`, and resource lives inside this repo.
2. **Stay BP-compatible.** The source tree is kept close enough to AOSP that the same files still compile under Blueprint, so the project can be dropped back into AOSP without rewriting imports or layout.
3. **No stubs.** Hidden AOSP APIs are provided by real prebuilt JARs/AARs copied out of AOSP outputs, never by hand-written `*.java` stub classes.
4. **No private resource files.** Every resource under `res/` came from AOSP source, a checked-in AAR, or a checked-in JAR — never a one-off XML/PNG created locally to make the build pass.
5. **Use modern Gradle.** Kotlin DSL (`build.gradle.kts`), version catalog (`gradle/libs.versions.toml`), Gradle 9.5, AGP 9.3.1 with `builtInKotlin=true`.

---

## High-level architecture

```
SystemUI-Gradle/
├── app/                         # APK entry point (no sources; depends on :SystemUI-core)
├── SystemUI-core/               # Main module: src + compose + pods + entry classes
├── SystemUI-res/                # Standalone resource namespace (res/res-keyguard/res-product)
├── SystemUI-common/             # Common + Log + utils (JVM)
├── SystemUI-animation/          # PlatformAnimation + Shader
├── SystemUI-plugin-core/        # Plugin runtime API (JVM)
├── SystemUI-plugin-processor/   # Plugin annotation processor (build-time)
├── SystemUI-plugin/             # PluginLib runtime (incl. bcsmartspace)
├── SystemUI-unfold/             # Unfold (KSP Dagger)
├── SystemUI-customization/      # Customization (with res)
├── SystemUI-shared/             # Shared + keyguard
├── SystemUI-shared-biometrics/  # Biometrics (own R namespace)
├── SystemUI-compose/            # Compose Core + Scene
├── libs/                        # All prebuilt jars/aars + local Maven repo (committed to git)
│   ├── framework.jar            # AOSP framework (provides hidden APIs)
│   ├── monet.jar                # Monet color engine
│   ├── systemui-flags.jar       # aconfig-generated SystemUI flags (+ other flag jars)
│   ├── aars/                    # 8 AOSP-produced AARs (animationlib, SettingsLib, WM-Shell, ...)
│   ├── maven/                   # Local Maven repo (AAR + POM) consumed via version catalog
│   └── prebuilts/               # Legacy prebuilt jars (being cleaned up)
├── tools/                       # Python helper scripts (AAR packaging, SDK install, ...)
├── docs/                        # CURRENT_STATE.md, PLAN.md, PITFALLS.md, issues/, adr/
├── gradle/libs.versions.toml    # Single source of truth for versions/deps
├── settings.gradle.kts
└── build.gradle.kts             # Root build + framework.jar injection
```

The AOSP sources under `SystemUI-core/src/` mirror the original layout of
`frameworks/base/packages/SystemUI/src/` (see `AGENTS.md` for the full mapping).
Resources owned by `:SystemUI-res` under `SystemUI-res/res/`,
`SystemUI-res/res-keyguard/`, and `SystemUI-res/res-product/` are tracked copies of the
corresponding AOSP resource directories.

---

## How the build finds AOSP-internal code

AGP compiles against a public SDK, which strips out `@hide` APIs and aconfig-generated
flags. SystemUI uses a lot of both, so we layer extra jars on top of the SDK via three
mechanisms:

1. **`framework.jar`** — AOSP's full prebuilt framework (with `@hide` APIs intact).
   Injected into every project's compile classpath by the `allprojects {}` block in the
   root `build.gradle.kts`. For some classes (e.g. `UserHandle.getIdentifier()`) we
   additionally need to take precedence over `android.jar`; for those we merged the
   conflicting classes into the SDK's `android.jar` itself (`libs/android-merged.jar` →
   `SysUISdk/android.jar`).
2. **aconfig-flag jars** — `com.android.systemui.Flags` and friends are generated by aconfig at
   AOSP build time. We extract the `.class` files from the AOSP intermediates and package them as
   small standalone jars (see `libs/systemui-flags.jar` and the other `*-flags.jar` files).
3. **Local Maven AARs** — SystemUI-adjacent prebuilt artifacts (`SettingsLib`, `iconloader`,
   `WindowManager-Shell`, `WifiTrackerLib`, `animationlib`, …) are produced by AOSP and consumed
   here as AARs from `libs/maven/`, referenced through the version catalog. They are generated by
   `tools/package_aosp_aar.py` and installed by `tools/install_aar_to_maven.py`.

Every mechanism in this list is a real prebuilt, not a stub.

---

## Building

### Prerequisites

- Linux x86_64 (the project is developed on Linux; macOS may work but is untested)
- JDK 21 (Gradle daemon JVM in `gradle/gradle-daemon-jvm.properties`)
- Android SDK at `$ANDROID_SDK_ROOT` (defaults to `~/Android/Sdk`)
- A `SysUISdk` platform installed under `$ANDROID_SDK_ROOT/platforms/android-SysUISdk`
  with both `android.jar` and `core-for-system-modules.jar` — see
  `tools/install_sdk.py`
- AOSP source tree at `/home/conv/myspace/aosp` (only needed if you regenerate the
  prebuilt jars/AARs)

### Configure

```bash
# 1. Create local.properties pointing at your SDK
echo "sdk.dir=$ANDROID_SDK_ROOT" > local.properties

# 2. (Optional) Regenerate AARs from your local AOSP build outputs.
#    libs/ (jars, aars/, maven/) is committed to git, so a fresh clone builds
#    without this step; run it only when AOSP artifacts need regenerating.
python3 tools/package_aosp_aar.py --all    # generate libs/aars/*.aar
python3 tools/install_aar_to_maven.py       # install to libs/maven/ + POM
```

### Build SystemUI-core

```bash
./gradlew :SystemUI-core:compileDebugKotlin
```

### Assemble a debug APK

```bash
./gradlew :app:assembleDebug
```

### Other useful tasks

```bash
./gradlew :SystemUI-core:clean
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks
./gradlew :SystemUI-core:dependencies --configuration debugCompileClasspath
./gradlew :SystemUI-core:tasks --all
```

---

## Project conventions

- **No stubs.** Hidden APIs come from real prebuilt jars/AARs, never from hand-written
  `*.java` stub classes.
- **No private resources.** Every resource was copied from AOSP source, lives inside an
  AAR, or lives inside a Maven artifact.
- **Source mirrors AOSP layout.** `SystemUI-core/src/<path>` corresponds to
  `aosp/frameworks/base/packages/SystemUI/src/<path>`. Don't reshuffle directories.
- **One commit per logical change.** Push promptly. Update `docs/` in the same commit.
- **Error counts are diagnostic only.** They never gate commits or rollbacks; what matters is
  forward progress toward a correct, maintainable, buildable project (see `AGENTS.md` rule I).

The full list of constraints and conventions lives in [`AGENTS.md`](AGENTS.md).

---

## Where to look

| You want to… | Look at |
|---|---|
| Understand the current roadmap and milestones | [`docs/PLAN.md`](docs/PLAN.md) |
| See how the error count has evolved over time | [`docs/GRADLE_MIGRATION_LOG.md`](docs/GRADLE_MIGRATION_LOG.md) |
| Read about a specific build problem and its fix | [`docs/issues/`](docs/issues/) (one file per day/topic) |
| Understand project rules and constraints | [`AGENTS.md`](AGENTS.md) |
| Regenerate AARs from AOSP outputs | [`tools/package_aosp_aar.py`](tools/package_aosp_aar.py) + [`tools/install_aar_to_maven.py`](tools/install_aar_to_maven.py) |
| Find where a hidden API lives | check `libs/framework.jar` first, then `docs/issues/` |

---

## Known issues

As of 2026-08-12 the verified blockers are tracked in
[`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) and the
[standards review](docs/issues/2026-08-12-current-progress-standards-review.md):

- **Final APK assembly is blocked at core Java compilation.** The previous blockers have been
  fixed: `jsr305` is now declared; WM-Shell AAR class overlap is zero; shared SettingsLib/SystemUI
  flags use the correct compile/runtime forms; release KSP is wired to release AIDL; AGP 9.3.1 is
  verified. Task 7 then exposed eight real dependency/artifact gaps: `NeverCompile`, setupcompat,
  Wi-Fi/WM-Shell aconfig flags, zxing, missing Dagger factories from `:SystemUI-shared`, a stale
  `SystemUI-tags.jar`, and an `androidx.media` version constraint.
- **No APK is produced yet.** The next work is a standards-compliant follow-up plan that supplies
  the real AOSP JARs/AARs or Maven constraints and reruns `:app:assembleDebug`.
- **Non-blocking warnings remain.** Room schema export is unconfigured, Kotlin 2.3 warns about
  future data-class copy visibility, and manifest merging reports duplicate permissions. These are
  deferred follow-ups, not current build blockers.

Historical blockers that are **solved**: KSP + Dagger binding resolution (Dagger 2.59.2 enables
`useBindingGraphFix` by default), the Compose inline-metadata failure (gone since Compose 1.11.4 +
AGP `builtInKotlin`), and the server-notification-flags resolution issue (a source stub was
shadowing the jar — see `docs/PITFALLS.md` §2.4).

---

## Reference projects

- [`CarSystemUIGradle`](../CarSystemUIGradle) — sibling project, same approach applied to
  Car SystemUI. Particularly informative for AAR-generation patterns; key commit is
  `c0ae96b`.
- [AOSP SystemUI](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/packages/SystemUI/)
  — the upstream source.

---

## License

The code in this repository is licensed under the Apache License, Version 2.0, the same
as AOSP itself. See individual file headers for details.
