# SystemUI-Gradle

**[中文](README.md)** | English

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

> Note: all jar / AAR dependencies are committed, so **a fresh clone builds as-is**.
> The only prerequisites not in the repo are the SysUISdk compile platform and the
> deployment target (emulator images); each is generated once from an AOSP build.

### Requirements

| Item | Requirement |
|---|---|
| OS | Ubuntu Linux (x86_64), your user in the `kvm` group |
| Disk | ≥ 400 GiB for full reproduction (incl. AOSP); ≈ 20 GiB to build this project alone |
| RAM | ≥ 32 GiB recommended (for the full AOSP build; 16 GiB works for this project alone) |
| JDK | 17+ (measured on 21) |
| Python | 3.x + [uv](https://docs.astral.sh/uv/) (scripts always run via `uv run`) |
| Tools | adb; scrcpy optional (to view the headless emulator) |

### Steps

**1. (one-off) Fetch and build AOSP `android-17.0.0_r1`** — its outputs generate
SysUISdk and the emulator images:

```bash
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -d -c -j4
cd <aosp-root> && . build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j$(nproc)
```

**2. (one-off) Generate SysUISdk**:

```bash
uv run python tools/build_sysuisdk.py --aosp-root <aosp-root>
# outputs <sdk-root>/platforms/android-SysUISdk
```

**3. Build this project**:

```bash
git clone <this-repo> && cd SystemUI-Gradle
./gradlew :app:assembleDebug       # Debug APK → app/build/outputs/apk/debug/
./gradlew :app:assembleRelease     # R8-optimized Release APK → app/build/outputs/apk/release/
uv run pytest tools/tests/ -q      # tooling tests
```

**4. Launch the emulator and deploy**: boot an emulator from the `sdk_phone64_x86_64`
images produced in step 1
(`ANDROID_PRODUCT_OUT=<aosp-root>/out/target/product/emu64x emulator ...`; full flags in
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

Apache License 2.0, same as AOSP (the source body comes from AOSP SystemUI).
