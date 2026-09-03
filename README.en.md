# SystemUI-Gradle

**[中文](README.md)** | English

[![SysUISdk r1 downloads](https://img.shields.io/github/downloads/convivae/SystemUI-Gradle/sysuisdk-android-17.0.0_r1-r1/total?label=SysUISdk%20r1%20downloads&logo=github)](https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1)
[![AOSP baseline](https://img.shields.io/badge/AOSP-android--17.0.0__r1-3ddc84?logo=android&logoColor=white)](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1)
[![Build verified](https://img.shields.io/badge/Debug%20%2B%20Release-verified-brightgreen)](docs/CURRENT_STATE.md)
[![Gradle 9.5.0](https://img.shields.io/badge/Gradle-9.5.0-02303a?logo=gradle&logoColor=white)](gradle/wrapper/gradle-wrapper.properties)
[![AGP 9.3.1](https://img.shields.io/badge/AGP-9.3.1-3ddc84?logo=android&logoColor=white)](gradle/libs.versions.toml)
[![Kotlin 2.2.10](https://img.shields.io/badge/Kotlin-2.2.10-7f52ff?logo=kotlin&logoColor=white)](gradle/libs.versions.toml)

A standalone, self-contained Gradle build of AOSP `frameworks/base/packages/SystemUI` —
the real, complete source of Android's **status bar, notification shade / quick settings,
lockscreen (Keyguard) and recents overview** — extracted from the Soong build system.
It builds a real SystemUI APK (not pruned, not stubbed) without the AOSP source tree,
while staying 1:1 aligned with AOSP sources and resources so changes can flow back
upstream at any time.

- **AOSP baseline**: `android-17.0.0_r1` (the first Android 17 release tag)
- **Toolchain**: Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10 (AGP builtInKotlin) · KSP ·
  Dagger · Compose · JDK 21
- **Achieved**: both the Debug APK (~200 MB) and the R8-optimized Release APK (~45 MB)
  compile cleanly and **run for real** on an Android 17 x86_64 emulator — stable across
  cold boot and full-device reboot (zero crashes; status bar, notification shade and
  wallpaper all on screen)

## What you get out of it

AOSP's SystemUI normally only builds inside a full AOSP checkout with Soong. This
project turns it into an ordinary Android Gradle project, which means you can:

- **Develop SystemUI in Android Studio**: full code indexing, navigation, refactoring
  and breakpoint debugging — iteration speed goes from "rebuild the tree" to a normal
  app build;
- **Version it independently**: branch, review and roll back SystemUI in its own git
  repository, decoupled from the platform checkout;
- **Build products on it**: customize the status bar / shade / lockscreen for a ROM or
  an industry system (automotive, tablet, IoT) by editing the real AOSP sources instead
  of maintaining patch stacks;
- **Study and teach**: SystemUI is one of the most complex Android applications
  (Dagger + Compose + a plugin system + heavy `@hide` API usage); this project makes it
  readable and hackable like a normal app;
- **Reproduce everything**: every binary dependency (jars / AARs) is committed to git,
  and each one can be **deterministically regenerated** from AOSP build outputs by the
  scripts in `tools/` — no hand-uploaded "magic files".

## How it works (overview)

The root reason SystemUI cannot leave the AOSP build is its heavy use of `@hide` APIs,
aconfig-generated flags classes and framework-private resources, none of which exist in
the standard Android SDK. This project solves that with:

1. **SysUISdk**: a custom compile platform (`compileSdkPreview = "SysUISdk"`) composed by
   the single-entry generator `tools/build_sysuisdk.py` from an official SDK platform
   plus built AOSP artifacts, supplying hidden APIs, framework-private resources and
   `@hide` AIDL declarations. It is a compile-time platform only — nothing from it is
   packaged into the APK.
2. **A three-tier dependency policy**: third-party libraries (androidx / Compose /
   Dagger / …) always come from official Maven coordinates; resource-free AOSP
   pure-code artifacts ship as local jars; AOSP libraries with resources ship as AARs.
   **There are no hand-written stubs anywhere in the repository.**
3. **17 Gradle modules**: module boundaries follow the semantics of AOSP `Android.bp`
   (see the table below); all SystemUI-owned code compiles from source, and resources
   and manifests are aligned with AOSP file-for-file.
4. **Build-time reference rewriting**: on Android 17, the Soong build renames a set of
   framework aconfig classes into a hidden package
   (`com.android.internal.hidden_from_bootclasspath.*`). During AGP bytecode
   instrumentation this project applies the same AOSP rule table (725 exact renames) as
   a **reference-only** rewrite, and ships an instruction-level static verifier,
   `tools/check_aconfig_jarjar_references.py`, that checks the final APK so the class
   names it references at runtime always match the on-device framework.

### Module map

| Module | Role (AOSP Soong target) |
|---|---|
| `:app` | APK entry: signing, packaging, manifest merger shell (`android_app "SystemUI"`) |
| `:SystemUI-core` | Main module: `SystemUIApplication` and other entry classes, src + compose + pods |
| `:SystemUI-application` | Dagger root component + the full AOSP manifest |
| `:SystemUI-res` | Resources (res / res-keyguard / res-product), generates `com.android.systemui.res.R` |
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

## Quick start

> All jar / AAR dependencies are committed, and the custom `android-SysUISdk` compile
> platform is published as a zip on
> [GitHub Releases](https://github.com/convivae/SystemUI-Gradle/releases) —
> **clone + one download is all you need to build; no AOSP checkout required.** You only
> need the AOSP 17 tree to regenerate SysUISdk / the `libs/` artifacts yourself or to
> build the deployment emulator images (see the optional branch in step 3). If Gradle
> reports `Failed to find Platform SDK with path: platforms;android-SysUISdk`, step 2
> below has not been completed, or the platform was unzipped into a different Android
> SDK root than the one Gradle uses.

### Requirements

| Item | Requirement |
|---|---|
| OS | Ubuntu Linux (x86_64); your user in the `kvm` group when running the emulator |
| Disk | ≈ 20 GiB to build this project alone; ≥ 400 GiB for full reproduction (incl. AOSP) |
| RAM | 16 GiB works for this project alone; ≥ 32 GiB recommended for the full AOSP build |
| JDK | 17+ (measured on 21) |
| Android SDK | anything recent; the official `platforms/android-37.0` is only needed as the read-only base when regenerating SysUISdk yourself |
| Python | 3.x + [uv](https://docs.astral.sh/uv/) (scripts always run via `uv run`) |
| Tools | unzip and sha256sum; adb; repo (AOSP path only) and scrcpy (viewing the headless emulator) optional |

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

### 2. Get SysUISdk (pick one)

**Option A (recommended): install the accepted r1 release**

Download the zip and matching `.sha256` file from the
[SysUISdk r1 Release](https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1),
then verify and install them from your download directory:

```bash
cd "$HOME/Downloads"  # adjust to your actual download directory
sha256sum --check SysUISdk-android-17.0.0_r1-r1.zip.sha256

(
  set -eu
  target="$ANDROID_SDK_ROOT/platforms/android-SysUISdk"
  test ! -e "$target" || {
    echo "ERROR: $target already exists; remove or rename it first." >&2
    exit 1
  }
  mkdir -p "$ANDROID_SDK_ROOT/platforms"
  unzip -q SysUISdk-android-17.0.0_r1-r1.zip 'android-SysUISdk/*' \
    -d "$ANDROID_SDK_ROOT/platforms"
  test -f "$target/android.jar"
)

cd "$PROJECT_ROOT"
```

The checksum command must print `SysUISdk-android-17.0.0_r1-r1.zip: OK`.
The fixed SHA-256 is
`ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`.
If `android-SysUISdk` already exists, remove or rename it explicitly first; do not
merge a new release into an old platform directory.

**Option B: generate it from AOSP yourself** — complete step 3 first, then run:

```bash
uv run python tools/build_sysuisdk.py \
  --aosp-root "$AOSP_ROOT" \
  --sdk-root "$ANDROID_SDK_ROOT"

# add --replace when regenerating an existing SysUISdk from newer AOSP outputs
```

### 3. (Optional) Prepare the AOSP 17 build outputs once

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

### 4. Build the APK

```bash
# Debug APK → app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:assembleDebug

# Clean app, then build the R8-optimized Release APK
# Output → app/build/outputs/apk/release/app-release.apk
./gradlew :app:clean :app:assembleRelease
```

Optional tooling verification:

```bash
uv run pytest tools/tests/ -q
uv run python tools/check_aconfig_jarjar_references.py \
  --apk app/build/outputs/apk/release/app-release.apk
```

### 5. Launch the emulator and deploy

Boot an emulator from the `sdk_phone64_x86_64` images produced in step 3
(`ANDROID_PRODUCT_OUT="$AOSP_ROOT/out/target/product/emu64x" emulator ...`; full flags in
[docs/issues/2026-08-26-emulator-relaunch-runbook.md](docs/issues/2026-08-26-emulator-relaunch-runbook.md)),
then replace the system SystemUI:

```bash
adb root && adb disable-verity && adb reboot   # after boot:
adb root && adb remount
adb push app/build/outputs/apk/debug/app-debug.apk /system_ext/priv-app/SystemUI/SystemUI.apk
adb shell pm grant com.android.systemui android.permission.BLUETOOTH_CONNECT
adb shell pm grant com.android.systemui android.permission.READ_CONTACTS
adb reboot
```

Deployment details and known traps (verification, read-only overlays after reboot,
grant resets, …) are in [docs/PITFALLS.md](docs/PITFALLS.md), device/emulator section.

## Secondary development guide

**Editing code**: SystemUI sources live in `SystemUI-core/src/` (path-for-path mirror of
AOSP `packages/SystemUI/src/`); each sub-library lives in its `SystemUI-*` module. Just
edit and build — no code generation, no intermediate layers.

**Editing resources**: resources are concentrated in `SystemUI-res/res*` (1:1 with AOSP
`res/`, `res-keyguard/`, `res-product/`). Reference them via `com.android.systemui.res.R`.

**Staying in sync with upstream**: this project deliberately avoids fork-style
rewrites — sources and resources stay file-for-file aligned with AOSP, enforced by
`tools/check_source_alignment.py --strict` (zero missing / misplaced / extra files).
Your own changes remain ordinary git history that can be rebased or cherry-picked back
into AOSP-shaped commits.

**Moving to a newer AOSP baseline**: after switching the AOSP tag, run in order —
realign sources (`check_source_alignment.py`), regenerate all jars / AARs with the
`tools/package_*.py` scripts, rebuild SysUISdk, rebuild the APKs and re-run the
deployment verification. The whole chain is scripted; no manual artifacts.

**Verification checklist** (after every change):

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
- **The deployment target must be a same-tree build**: SystemUI is a platform-signed app
  calling hidden APIs, so it must be deployed onto an AOSP build matching the baseline
  (this project verifies against same-tree emulator images); it cannot be installed on
  retail phones or the stock emulator images.
- **Release is not obfuscated**: matching AOSP behavior, Release applies R8 optimization
  and resource shrinking only — no identifier obfuscation.

## Documentation map

| Want to know | Read |
|---|---|
| Detailed build / deployment pitfalls | [docs/PITFALLS.md](docs/PITFALLS.md) |
| Architecture decision records (ADRs) | [docs/adr/](docs/adr/) |
| Deep dives (SysUISdk generation, R8 closure, aconfig renaming, …) | [docs/architecture/](docs/architecture/) |
| Live development status (internal) | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| Internal development rules | [AGENTS.md](AGENTS.md) |
| Documentation index and maintenance rules | [docs/README.md](docs/README.md) |

## License

AOSP-derived SystemUI sources and project-authored code are provided under the Apache
License 2.0. The separately published SysUISdk r1 also contains stock Android SDK base
files governed by the Android SDK License Agreement. Read
[`release/sysuisdk/NOTICE`](release/sysuisdk/NOTICE) and the
[Android SDK Terms](https://developer.android.com/studio/terms) before downloading or
using it.
