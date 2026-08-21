# SystemUI-Gradle

**[中文](README.md)** | English

A standalone, self-contained Gradle build of AOSP `frameworks/base/packages/SystemUI` —
the real SystemUI source tree, fully extracted from Soong/Blueprint, compilable without
the AOSP source tree, while staying 1:1 aligned with AOSP sources and resources so it
can flow back upstream at any time.

> **Status:** active development. Both the debug and the optimized release APK build;
> on-device runtime validation has not been performed yet.
> Live snapshot: [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md).

---

## Why

AOSP's SystemUI is normally built inside the AOSP tree with Soong. That makes it hard to:

- iterate quickly with Android Studio / a Gradle build loop;
- version, branch, and code-review it independently of the platform;
- base downstream products on it without maintaining a full AOSP build environment.

This project ports SystemUI to a pure Gradle build (Gradle 9.5 + AGP 9.3.1 + Kotlin
2.2.10). Every dependency it needs — hidden APIs, aconfig flags, AOSP libraries,
resources — is vendored into the repo as a real artifact, so `git clone` is all you
need. **The build never reaches back into the AOSP tree.**

Sibling project using the same approach: [CarSystemUIGradle](../CarSystemUIGradle)
(Car SystemUI).

## Status at a glance (2026-08-21)

| Dimension | Status |
|---|---|
| Toolchain | Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10 (AGP `builtInKotlin`) · KSP 2.2.10-2.0.2 · Dagger 2.59.2 · Compose 1.11.4 |
| Custom SDK | SysUISdk reproducible with a single command (`python3 tools/build_sysuisdk.py --aosp-root <aosp>`; transactional generation incl. hidden APIs, framework-private resources, @hide AIDL declarations) |
| Compilation | KSP 0 errors · core Kotlin 0 errors · core javac 0 errors |
| Unit tests | **220/220 passing** |
| **Debug APK** | ✅ `:app:assembleDebug` succeeds (hard gate for every batch of changes) |
| Release APK | ✅ optimized release build succeeds (R8 whole-program optimization + resource shrinking + V2 signing); R8 missing references: **0** |
| Device validation | ⏳ not yet performed (emulator/device plan on file) |

## What's been done

- **13 Gradle modules** whose boundaries semantically follow AOSP `Android.bp`;
  all SystemUI-owned code is source-built (never jarred), while non-SystemUI AOSP
  artifacts are consumed only as jars/AARs (no copying framework sources)
- **Source/resources aligned 1:1 with AOSP** (nothing missing, nothing extra),
  with automated alignment checks; any unavoidable source edit is recorded with
  traceable markup comments — auditable and reversible
- **Single-command SysUISdk generator**: builds `android-SysUISdk` transactionally
  from a read-only official SDK platform plus built AOSP outputs; hidden APIs,
  framework-private resources, and @hide AIDL declarations all come from real AOSP
  inputs — no hand-edited SDK
- **Full dependency governance**: AOSP libraries are deterministically packaged into 29
  AARs by `tools/package_aosp_aar.py`, served through a local Maven repo + version
  catalog; third-party libraries use official Maven coordinates at the latest compatible
  versions; all of `libs/` is committed to git
- **Release aligned with AOSP**: Soong behavior is the baseline — zero ProGuard in core,
  unified R8 + shrinkResources in the app
- **R8 runtime-closure audit and burn-down**: 140 missing references cleared exactly,
  batch by batch, down to **0**, with all platform/build-time bridge classes kept out of
  the APK

## What's in progress

- **On-device runtime validation**: the optimized release APK builds, is signed, and passes
  integrity checks, but has not yet been installed and exercised on a compatible emulator
  or device (a green build is not a runtime validation; plan:
  `docs/issues/2026-08-20-device-emulator-validation-plan.md`)
- Ongoing alignment of sources/resources with the AOSP upstream, plus read-only inventory
  and cleanup assessment of legacy artifacts

## Module layout

```
SystemUI-Gradle/
├── app/                        # APK entry point (no sources; manifest, signing, packaging)
├── SystemUI-core/              # Main module: SystemUIApplication, src + compose + pods
├── SystemUI-res/               # Standalone resource namespace (res / res-keyguard / res-product)
├── SystemUI-common/            # Common + Log + shared-utils
├── SystemUI-animation/         # PlatformAnimation + Shader (surfaceeffects)
├── SystemUI-plugin-core/       # Plugin runtime API (JVM)
├── SystemUI-plugin-processor/  # Plugin annotation processor (build-time)
├── SystemUI-plugin/            # PluginLib runtime (incl. bcsmartspace)
├── SystemUI-unfold/            # Unfold (Dagger via KSP)
├── SystemUI-customization/     # Customization (with res)
├── SystemUI-shared/            # Shared + keyguard (aidl + res)
├── SystemUI-shared-biometrics/ # Biometrics (own R namespace)
├── SystemUI-compose/           # Compose Core + Scene
├── libs/                       # All prebuilt artifacts, committed to git
│   ├── framework.jar           # AOSP framework (with @hide APIs)
│   ├── *-flags.jar             # aconfig-generated flags classes
│   ├── aars/                   # 29 AOSP-produced AARs (SettingsLib, WM-Shell, iconloader…)
│   └── maven/                  # Local Maven repo (AAR + POM, consumed via catalog)
├── tools/                      # Python tooling (AAR packaging, SDK build, alignment checks…)
└── docs/                       # State, plans, pitfalls, issue records, ADRs
```

`SystemUI-core/src/` mirrors AOSP `frameworks/base/packages/SystemUI/src/` path-for-path;
`SystemUI-res/res*` mirrors the corresponding AOSP resource directories 1:1
(see `AGENTS.md` §3.3).

## How dependencies are resolved (the no-stub rule)

AGP's official SDK strips `@hide` APIs and aconfig-generated classes, both of which
SystemUI uses heavily. This project uses **no hand-written stubs** — only three kinds of
real artifacts:

1. **Official Maven coordinates** (preferred): androidx / Compose / Dagger / protobuf and
   other third-party libraries, at the latest compatible versions
2. **Local JARs**: resource-free pure-code AOSP artifacts (framework.jar, aconfig flags
   jars, …)
3. **AARs**: AOSP libraries with resources (direct include first; promoted to the local
   Maven repo only when a conflict is confirmed)

Every AAR/JAR is **deterministically** packaged from AOSP Soong outputs by scripts in
`tools/` — reproducible and auditable.

## Building

### Prerequisites

- Linux x86_64 · JDK 21
- Android SDK with the **SysUISdk** platform installed
  (`platforms/android-SysUISdk`, produced by
  `python3 tools/build_sysuisdk.py --aosp-root <aosp>`)
- A local AOSP tree is needed only to regenerate the SysUISdk platform or other AOSP
  artifacts (and it must have been built once — the generator only consumes `out/` outputs)

### Common commands

```bash
./gradlew :app:assembleDebug            # Build the debug APK (current hard gate)
./gradlew :SystemUI-core:compileDebugKotlin
python3 -m unittest discover -s tools/tests   # Toolchain tests (220)
```

All of `libs/` is committed to git — **a fresh clone builds out of the box**.

## Documentation map

| You want… | Look at |
|---|---|
| Live state snapshot | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| Project rules (no stubs / alignment discipline / escalation) | [AGENTS.md](AGENTS.md) |
| Phase plan | [docs/PLAN.md](docs/PLAN.md) |
| Pitfall log | [docs/PITFALLS.md](docs/PITFALLS.md) |
| Architecture decision records | [docs/adr/](docs/adr/) |
| Daily issue / research records | [docs/issues/](docs/issues/) · [docs/architecture/](docs/architecture/) |

## License

Apache License 2.0, same as AOSP.
