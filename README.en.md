# SystemUI-Gradle

**[中文](README.md)** | English

A standalone, self-contained Gradle build of AOSP `frameworks/base/packages/SystemUI` —
the **real SystemUI source tree** (not pruned, not stubbed), fully extracted from
Soong/Blueprint, compilable without the AOSP source tree, while staying 1:1 aligned
with AOSP sources and resources so it can flow back upstream at any time.

> **Achieved**: both the Debug and the optimized Release runtime have been validated
> on a same-tree x86_64 emulator (see the table below). Full live state:
> [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md).

---

## Status at a glance (2026-08-26)

| Dimension | Status |
|---|---|
| **Debug runtime** | ✅ **DEBUG_RUNTIME_PASS (2026-08-25)**: the Gradle-built Debug APK (sha256 `e8aad131…`, 163,896,493 B) runs on a `sdk_phone64_x86_64` emulator — SystemUI PID stable across 10×30s samples, zero FATAL/NoClassDefFoundError, StatusBar/NotificationShade/Taskbar on screen |
| **Release runtime** | ✅ **RELEASE_RUNTIME_PASS (2026-08-26)**: the optimized Release APK (R8 whole-program optimization + resource shrinking + `-dontobfuscate` matching Soong + V2 signing; current baseline sha256 `d3968fb2…`, 34,688,965 B) deployed the same way — stable PID, zero FATAL, QS expand/collapse clean |
| Toolchain | Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10 (AGP `builtInKotlin`) · KSP 2.2.10-2.0.2 · Dagger 2.59.2 · Compose 1.11.4 · material3 1.5.0-alpha18 · JDK 21 · `compileSdkPreview = "SysUISdk"` |
| Compilation | KSP 0 errors · core Kotlin 0 errors · core javac 0 errors; `:app:assembleDebug` is the hard gate for every batch of changes |
| R8 | Release missing references: **0** (burned down exactly, batch by batch, from 140) |
| Tool tests | `uv run pytest tools/tests/ -q` → **276 passed** (+102 subtests) |
| Source/res alignment | Automated alignment check: MISSING / MISPLACED / EXTRA = **0 / 0 / 0** |
| Artifact regeneration | all 104 artifacts in `libs/` (jars/AARs/POMs) are committed to git **and** deterministically regenerable by `tools/` scripts (see Quickstart step 4) |

> The success criterion is **AGP-native functional parity**: the generated SysUISdk must
> directly support the existing Debug and optimized Release builds and actually run on a
> device — not merely "look like it compiles".

## Why

AOSP's SystemUI is normally built inside the AOSP tree with Soong. That makes it hard to:

- iterate quickly with Android Studio / a Gradle build loop;
- version, branch, and code-review it independently of the platform;
- base downstream products on it without maintaining a full AOSP build environment.

This project ports SystemUI to a pure Gradle build. Every dependency it needs — hidden
APIs, aconfig flags, AOSP libraries, resources — is vendored into the repo as a **real
artifact**, so `git clone` is all you need. **The build never reaches back into the
AOSP tree.**

Sibling project using the same approach: [CarSystemUIGradle](../CarSystemUIGradle)
(Car SystemUI).

## Architecture

### Module topology (13 Gradle modules, semantically aligned with AOSP `Android.bp`)

| Module | Role (Soong target) |
|---|---|
| `:app` | `android_app "SystemUI"`: APK entry (no sources of its own; manifest, signing, packaging) |
| `:SystemUI-core` | `android_library "SystemUI-core"`: main module — `SystemUIApplication` and other entry classes, src + compose + pods |
| `:SystemUI-res` | Standalone resource namespace (res / res-keyguard / res-product), generates `com.android.systemui.res.R` |
| `:SystemUI-common` | Common + Log + shared-utils, merged |
| `:SystemUI-animation` | PlatformAnimationLib + Shader (surfaceeffects), merged (with res) |
| `:SystemUI-plugin-core` | PluginCoreLib runtime API (JVM) |
| `:SystemUI-plugin-processor` | PluginAnnotationProcessor (build-time, not packaged) |
| `:SystemUI-plugin` | SystemUIPluginLib runtime (incl. bcsmartspace) |
| `:SystemUI-unfold` | SystemUIUnfoldLib (Dagger via KSP) |
| `:SystemUI-customization` | SystemUICustomizationLib (with res) |
| `:SystemUI-shared` | SystemUISharedLib + keyguard, merged (aidl + res) |
| `:SystemUI-shared-biometrics` | biometrics (own R namespace, consumed by Settings) |
| `:SystemUI-compose` | Compose Core + Scene, merged |

`SystemUI-core/src/` mirrors AOSP `frameworks/base/packages/SystemUI/src/` path-for-path;
`SystemUI-res/res*` mirrors the corresponding AOSP resource directories 1:1
(see [AGENTS.md](AGENTS.md) §3.3).

### Dependency resolution (the no-stub rule)

AGP's official SDK strips `@hide` APIs and aconfig-generated classes, both of which
SystemUI uses heavily. This project uses **no hand-written stubs** — only three kinds of
real artifacts:

1. **Official Maven coordinates** (preferred): androidx / Compose / Dagger / protobuf and
   other third-party libraries, at the latest compatible versions
2. **Local JARs**: resource-free pure-code AOSP artifacts (framework.jar, aconfig flags
   jars, …)
3. **AARs**: AOSP libraries with resources (direct include from `libs/aars/` first;
   promoted to the local Maven repo `libs/maven/` only when a conflict is confirmed)

**SysUISdk** is this project's custom `compileSdkPreview` platform: a single-entry
generator, `tools/build_sysuisdk.py`, composes it transactionally from a read-only
official SDK platform plus built AOSP `out/` artifacts, supplying hidden API bytes,
framework-private resources (`@*android:` IDs), and @hide AIDL declarations in one shot.
Every AAR/JAR is **deterministically** packaged from AOSP Soong outputs by scripts in
`tools/` — reproducible and auditable.

## AOSP version baseline

All current validation (builds + both runtimes) is based on a snapshot of AOSP `main`:

- Snapshot file:
  [`docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml`](docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml)
  (1042 projects, exported with `repo manifest -r` from the validated tree on 2026-08-26;
  see [`docs/aosp-pinning/README.md`](docs/aosp-pinning/README.md))
- **Formal version pinning has not been executed yet**: upgrading/pinning the baseline to
  a formal AOSP release (upgrade AOSP → rebuild → rerun the full pipeline → re-validate
  the port) is planned follow-up work (Phase C, full from-zero pipeline rerun; see
  [docs/PLAN.md](docs/PLAN.md) and
  [docs/architecture/2026-08-26-regeneration-gap-closure.md](docs/architecture/2026-08-26-regeneration-gap-closure.md)).

## Reproducing from zero (Quickstart)

Seven steps end to end. Everything in `libs/` is committed to git, so **a fresh clone can
skip steps 1–4 and go straight to step 5**; steps 1–4 are needed only when regenerating
the AOSP artifacts from scratch. Each step is labeled with its current verification
status.

### Requirements (measured on the reference machine)

| Item | Requirement |
|---|---|
| OS | Ubuntu Linux (x86_64) |
| Disk | **≥400 GiB**: the AOSP tree measured 418G (including `out/` at 187G; that includes historical experiment artifacts — a clean single-product build is estimated at ~300G) |
| RAM | **≥32 GiB**: the reference machine has 30Gi RAM + 8G swap and is a tight fit (AOSP builds must use `-j4`); the emulator needs another ~4.5 GiB resident |
| KVM | required (same-tree x86_64 emulator; your user must be in the `kvm` group) |
| JDK | 17+ (project toolchain measured on JDK 21) |
| Python | Python 3 + [uv](https://docs.astral.sh/uv/) (scripts are always run via `uv run`; pip is forbidden) |
| Android tools | adb; scrcpy optional (to view the headless emulator) |

The Gradle wrapper ships 9.5.0 (distributed via the Tencent mirror), and
`settings.gradle.kts` has Tencent Cloud / Aliyun Maven mirrors built in — it works out of
the box on networks with limited access to the original registries.

### Steps

**1. Download AOSP (repo init main + snapshot checkout)** — *the snapshot itself was
exported from the tree validated on 2026-08-26; a full from-zero rerun is pending Phase C*

```bash
repo init -u https://android.googlesource.com/platform/manifest -b main
# To pin to the validated snapshot: use docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml as the manifest, then repo sync
```

**2. Build AOSP** — *verified* (the same-tree emulator and all artifact scripts consume
this build's `out/`)

```bash
cd <aosp-root> && . build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j4        # outputs include the out/target/product/emu64x/ emulator images
```

**3. Generate SysUISdk** — *verified* (Task 045: two builds from real AOSP inputs were
byte-identical, 11,382 files)

```bash
uv run python tools/build_sysuisdk.py --aosp-root <aosp-root>
# Output: <sdk-root>/platforms/android-SysUISdk; see docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md
```

**4. Generate the libs/ artifacts** (only when regenerating) — *verified* (Tasks 064/065:
all 15 previously unscripted artifacts brought into the pipeline, with a frozen sha256
ledger and `--verify-only`)

```bash
uv run python tools/package_aosp_aar.py --all          # 29 AARs → libs/aars/
uv run python tools/install_aar_to_maven.py            # install as local-Maven AARs → libs/maven/
uv run python tools/package_aconfig_jars.py --all      # aconfig flags jars (incl. the merged family)
uv run python tools/package_misc_jars.py --all         # 12 misc jars (framework.jar, …)
uv run python tools/package_compilelib_jars.py         # compilelib debug/release jars
uv run python tools/package_monet_jar.py               # monet jar
uv run python tools/package_viewcapture_motiontool_jars.py
```

**5. Gradle build** — *verified* (assembleDebug is the hard gate for every batch)

```bash
./gradlew :app:assembleDebug      # Debug APK
./gradlew :app:assembleRelease    # optimized Release APK (R8 + resource shrinking + V2 signing)
uv run pytest tools/tests/ -q     # toolchain tests (276 passed)
```

**6. Start the emulator** — *verified*; the full command and environment variables
(`ANDROID_PRODUCT_OUT` / `ANDROID_BUILD_TOP` / `ANDROID_TMP`, pre-creating the log files,
and other pitfalls) are in the runbook:
[docs/issues/2026-08-26-emulator-relaunch-runbook.md](docs/issues/2026-08-26-emulator-relaunch-runbook.md)

**7. Deploy and validate** — *verified* (dual gates passed for Debug `e8aad131…` and
Release `d3968fb2…`); the staged deployment procedure (root → disable-verity → staged
push with an on-device sha256 gate → atomic replace → clear caches → reboot, plus known
pitfalls) is in [docs/PITFALLS.md](docs/PITFALLS.md) §14.

## Documentation map

| You want… | Look at |
|---|---|
| Live state snapshot (build matrix, versions, artifacts, evidence) | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| 5-minute onboarding | [docs/HANDOFF.md](docs/HANDOFF.md) |
| Project rules (no stubs / alignment discipline / escalation) | [AGENTS.md](AGENTS.md) |
| Remaining roadmap and completion criteria | [docs/PLAN.md](docs/PLAN.md) |
| Pitfall log (incl. the device/emulator deployment procedure, §14) | [docs/PITFALLS.md](docs/PITFALLS.md) |
| Architecture decision records (ADR) | [docs/adr/](docs/adr/) |
| Deep research reports | [docs/architecture/](docs/architecture/) |
| Daily issue records | [docs/issues/](docs/issues/) |
| Documentation index and lifecycle | [docs/README.md](docs/README.md) |
| Multi-worker orchestration (herdr) | [docs/orchestration/](docs/orchestration/) |

## License

Apache License 2.0, same as AOSP (the bulk of the source comes from AOSP SystemUI).
