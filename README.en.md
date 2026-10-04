# SystemUI-Gradle

**[中文](README.md)** | English

[![AOSP baseline](https://img.shields.io/badge/AOSP-android--17.0.0__r1-3ddc84?logo=android&logoColor=white)](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1)
[![Gradle 9.5.0](https://img.shields.io/badge/Gradle-9.5.0-02303a?logo=gradle&logoColor=white)](gradle/wrapper/gradle-wrapper.properties)
[![AGP 9.3.1](https://img.shields.io/badge/AGP-9.3.1-3ddc84?logo=android&logoColor=white)](gradle/libs.versions.toml)
[![Kotlin 2.2.10](https://img.shields.io/badge/Kotlin-2.2.10-7f52ff?logo=kotlin&logoColor=white)](gradle/libs.versions.toml)

This project takes AOSP `frameworks/base/packages/SystemUI` — the real, complete source
of Android's **status bar, notification shade / quick settings, lockscreen (Keyguard)
and recents overview** — out of the Soong build system and turns it into a standalone,
self-contained Android Gradle project. It builds like a normal app from Android Studio
or the command line, produces installable Debug and Release APKs, and has been
verified to run on a same-baseline AOSP 17 emulator.

## Highlights

- **Real sources, not pruned, not stubbed**: all SystemUI-owned code compiles from
  source; resources and manifests align with AOSP file-for-file, so changes can flow
  back upstream at any time;
- **17 Gradle modules**: module boundaries follow the semantics of AOSP `Android.bp`,
  and source paths correspond one-to-one with AOSP — reading and navigation come free;
- **SysUISdk**: a custom compile platform supplying the `@hide` APIs, framework-private
  resources and hidden AIDL declarations the standard Android SDK lacks (published on
  [GitHub Releases](https://github.com/convivae/SystemUI-Gradle/releases), and
  deterministically regenerable from AOSP outputs);
- **Clean dependencies**: third-party libraries (androidx / Compose / Dagger / …)
  always come from official Maven coordinates; AOSP artifacts ship as committed jars /
  AARs, each regenerable by the scripts in `tools/` — no hand-uploaded "magic files"
  and no hand-written stubs;
- **Release support**: R8 optimization plus resource shrinking, producing the same
  kind of non-obfuscated, platform-signed APK as AOSP.

## Requirements

| Item | Requirement |
|---|---|
| OS | Verified on Linux x86_64; no native macOS/Windows validation yet; KVM access for the Linux emulator |
| JDK | 21; daemon/toolchain settings are defined in `gradle/gradle-daemon-jvm.properties` and build files |
| RAM | ~16 GiB works for this project alone (Gradle `-Xmx16g`); ≥ 30 GiB recommended when also building AOSP |
| Disk | ≈ 20 GiB to build this project alone; ≥ 400 GiB for full reproduction (incl. the AOSP tree) |
| Android SDK | anything recent; the official `platforms/android-37.0` is only needed as the read-only base when regenerating SysUISdk yourself |
| Maintenance tools (optional) | Python 3.11+ and [uv](https://docs.astral.sh/uv/), only for regeneration/verification scripts under `tools/` |
| Deployment tools (optional) | adb; repo for AOSP builds; emulator and scrcpy as needed |

> **With a compatible SysUISdk installed, ordinary APK builds need neither Python,
> uv nor an AOSP source tree.** JAR/AAR dependencies are committed, and resource repair
> uses a Kotlin Gradle task and AGP's AAPT2. Regeneration, AOSP alignment checks and
> emulator-image builds require their respective maintenance environments.
> See step 2 for the distinction between current main and the historical r1 SDK.

Commands below use Bash. On Windows use `gradlew.bat` and adapt path setup to your shell.

## Quick start

### 1. Clone the project and set paths

Replace the following values with **absolute paths** on your machine:

```bash
git clone https://github.com/convivae/SystemUI-Gradle.git
cd SystemUI-Gradle

export PROJECT_ROOT="$PWD"
export ANDROID_SDK_ROOT=/absolute/path/to/Android/Sdk
export ANDROID_HOME="$ANDROID_SDK_ROOT"
printf 'sdk.dir=%s\n' "$ANDROID_SDK_ROOT" > local.properties
```

### 2. Get SysUISdk

> **Current main requires the optional-bridge layout from generator 045.3+.** The
> published r1 SDK remains available for the historical `v1.0.0-android-17.0.0_r1`
> tag, but lacks `com.android.systemui.platform.bridge`. Until a new SDK release
> is published, use option B below for main; use `--replace` for generator-owned
> existing outputs. This fixes Studio sync without disabling local JVM tests or
> rewriting real AOSP class bytes.

**Option A (historical release tag only): install the published r1 release**

Download the zip from the
[SysUISdk r1 Release](https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1)
(a matching `.sha256` is provided for verification; fixed SHA-256
`ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`)
and extract it into `$ANDROID_SDK_ROOT/platforms/`. The installed layout:

```
$ANDROID_SDK_ROOT/
└── platforms/
    └── android-SysUISdk/      # the extracted directory, containing android.jar etc.
```

Note: if `platforms/android-SysUISdk` already exists, remove or rename it
first — do not merge a new release into an old platform directory.

**Option B: generate it from AOSP yourself** — complete step 3 first, then run:

```bash
uv run python tools/build_sysuisdk.py \
  --aosp-root "$AOSP_ROOT" \
  --sdk-root "$ANDROID_SDK_ROOT"

# add --replace when regenerating an existing SysUISdk from newer AOSP outputs
```

If Gradle reports `Failed to find Platform SDK with path: platforms;android-SysUISdk`,
step 2 has not been completed, or the platform was unzipped into a different Android
SDK root than the one Gradle uses.
If it reports `Unable to find optional library: com.android.systemui.platform.bridge`,
regenerate the old-layout SDK with the current generator; do not remove `useLibrary()`
or disable UnitTest.

Local JVM regression and headless IDE model checks are documented in
[`tools/tests/fixtures/sysuisdk_optional_bridge/README.md`](tools/tests/fixtures/sysuisdk_optional_bridge/README.md).

### 3. (Optional) Prepare the AOSP 17 build outputs

Only needed to: generate SysUISdk via option B, regenerate the `libs/` artifacts, or
build the deployment emulator images. If you took option A and don't need the
emulator, skip to step 4.

```bash
export AOSP_ROOT=/absolute/path/to/aosp
mkdir -p "$AOSP_ROOT"
cd "$AOSP_ROOT"
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -d -c -j4
. build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j"$(nproc)"
cd "$PROJECT_ROOT"
```

### 4. Build the APKs

```bash
# Debug APK → app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:assembleDebug

# Clean app, then build the R8-optimized Release APK
# Output → app/build/outputs/apk/release/app-release.apk
./gradlew :app:clean :app:assembleRelease
```

`:app:clean` deletes all app variant outputs. To retain both APKs, run
`:app:assembleDebug` again after the clean Release build.

Both variants are signed with the platform keystore committed to the repository
(`keystore/platform.keystore`, derived from the AOSP development test key) — no extra
configuration is needed to produce deployable signed APKs.

## Running on the emulator

SystemUI is a platform-signed app calling hidden APIs, so the deployment target must
be an AOSP build matching the baseline (this project verifies against self-built
`sdk_phone64_x86_64` emulator images; it cannot be installed on retail phones or the
stock emulator images).

Boot the same-baseline images from step 3 using the layout and launch options of
that AOSP product. Before replacement, back up the original APK/images and verify
platform signing, the target partition, overlay space and the recovery procedure.
Use staging, SHA checks and a same-directory atomic replacement rather than directly
overwriting the running SystemUI APK. See the
[deployment checklist](docs/PITFALLS.md#设备与模拟器部署) (Chinese).

Dated emulator runbooks describe particular image experiments, not generic launch
scripts that can be copied to the current host unchanged.

## Secondary development guide

**Editing code**: SystemUI sources live in `SystemUI-core/src/` (path-for-path mirror
of AOSP `packages/SystemUI/src/`); each sub-library lives in its `SystemUI-*` module.
Just edit and build — no code generation, no intermediate layers. Key entry points:

- `:SystemUI-core` — `SystemUIApplication` and the main application logic;
- `:SystemUI-application` — the Dagger root component and the full manifest.

**Editing resources**: resources are concentrated in `SystemUI-res/res*` (1:1 with
AOSP `res/`, `res-keyguard/`, `res-product/`), referenced from code as
`com.android.systemui.res.R`.

**Module structure**: module split and merging follow the semantics of AOSP
`Android.bp` exactly (see [ADR 0003](docs/adr/0003-app-module-aligns-aosp-bp.md)).
Module map:

| Module | Role (AOSP Soong target) |
|---|---|
| `:app` | APK entry: signing, packaging, manifest merger shell (`android_app "SystemUI"`) |
| `:SystemUI-core` | Main module: entry classes, src + compose + pods |
| `:SystemUI-application` | Dagger root component + the full AOSP manifest |
| `:SystemUI-res` | Resources (res / res-keyguard / res-product) |
| `:SystemUI-common` | Common + Log + shared-utils |
| `:SystemUI-animation` | Platform animation library (PlatformAnimationLib) |
| `:SystemUI-compose` | Compose Core + Scene |
| `:SystemUI-customization` | Customization library (wallpaper, theme picker, …) |
| `:SystemUI-clocks-common` | Clocks common library |
| `:SystemUI-shared` | shared + keyguard (AIDL + resources) |
| `:SystemUI-shared-biometrics` | Biometrics (own resource namespace) |
| `:SystemUI-plugin` / `:SystemUI-plugin-core` | Plugin runtime and API |
| `:SystemUI-plugin-processor` | Plugin annotation processor (build-time only) |
| `:SystemUI-unfold` | Foldable unfold library |
| `:SystemUI-accessibility-floatingmenu-res` | Accessibility floating-menu resources |
| `:SystemUI-utils-kairos` | kairos (SystemUI's reactive state library) |

**Staying in sync with upstream**: this project deliberately avoids fork-style
rewrites — sources and resources stay file-for-file aligned with AOSP, enforced by
`tools/check_source_alignment.py --strict` (zero missing / misplaced / extra files).
Your own changes remain ordinary git history that can be rebased or cherry-picked back
into AOSP at any time.

**Moving to a newer AOSP baseline**: after switching the tag, run in order — realign
sources (`check_source_alignment.py`), regenerate all jars / AARs with the
`tools/package_*.py` scripts, rebuild SysUISdk, rebuild the APKs and re-run the
deployment verification. The whole chain is scripted; no manual artifacts.

**Verification tools** (select for the change; run the reference-integrity gate for each built APK):

The `tools/` commands require a maintainer-configured Python/uv environment and are
not dependencies of `assembleDebug/Release`. A successful build alone does not prove
deployment or runtime behavior.

```bash
./gradlew :app:assembleDebug                                 # compile gate
uv run python tools/check_source_alignment.py --strict       # alignment gate (needs the AOSP tree)
uv run python tools/check_aconfig_jarjar_references.py \
    --apk app/build/outputs/apk/debug/app-debug.apk          # APK reference-integrity gate
uv run pytest tools/tests/ -q                                # tooling regression
```

## Known limitations

- **Dependency ceilings**: Compose must stay below 1.12 (it removed
  `ExperimentalAnimatableApi`, which AOSP uses); kotlinx-coroutines is capped at 1.10.2
  (1.11 adds an overload that breaks AOSP sources). Check
  [docs/PITFALLS.md](docs/PITFALLS.md) before upgrading dependencies.
- **Release is not obfuscated**: matching AOSP behavior, Release applies R8
  optimization and resource shrinking only — no identifier obfuscation.

## Project layout

```
SystemUI-Gradle/
├── app/                      # APK packaging entry (signing, manifest merger shell)
├── SystemUI-*/               # Source/resource modules (see the module map above)
├── libs/                     # AOSP artifact dependencies (jars / AARs / local Maven, all script-regenerated)
├── tools/                    # Python build/verification tooling (SysUISdk generation, artifact packaging, alignment checks, …)
├── keystore/                 # Platform signing keystore (AOSP development test key)
├── release/                  # SysUISdk release assets (LICENSE / NOTICE / packaging script)
├── docs/                     # Project documentation (see below)
└── gradle/                   # Wrapper and version catalog
```

## Documentation

| Want to know | Read |
|---|---|
| Detailed build / deployment pitfalls | [docs/PITFALLS.md](docs/PITFALLS.md) |
| Documentation index and navigation | [docs/README.md](docs/README.md) |
| Gradle build design and dependency boundaries | [docs/architecture/gradle-build.md](docs/architecture/gradle-build.md) |
| Architecture decision records (ADRs) | [docs/adr/](docs/adr/) |
| Deep-dive reports | [docs/architecture/](docs/architecture/) |

## License

AOSP-derived SystemUI sources (Apache License 2.0, Copyright The Android Open Source
Project) and project-authored code are provided under the Apache License 2.0. The
separately published SysUISdk zip also contains stock Android SDK base files governed
by the Android SDK License Agreement. Read
[`release/sysuisdk/NOTICE`](release/sysuisdk/NOTICE) and the
[Android SDK Terms](https://developer.android.com/studio/terms) before downloading or
using it.
