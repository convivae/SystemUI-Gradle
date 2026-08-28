# SystemUI-Gradle

**[中文](README.md)** | English

A standalone, self-contained Gradle build of AOSP `frameworks/base/packages/SystemUI` —
the **real SystemUI source tree** (not pruned, not stubbed), fully extracted from
Soong/Blueprint, compilable without the AOSP source tree, while staying 1:1 aligned
with AOSP sources and resources so it can flow back upstream at any time.

> **16-era milestone (historical baseline)**: both the Debug and the optimized Release runtime
> were validated on a same-tree x86_64 emulator (2026-08-25/26). The project is now in
> **Phase C** (AOSP baseline pinned to `android-17.0.0_r1`, full pipeline clean regeneration):
> C1/C3/C2/C4a are complete, and **C4b (restoring the `assembleDebug` compile closure) is in
> progress**. Full live state: [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md).

---

## Status at a glance (2026-08-28)

| Dimension | Status |
|---|---|
| **Debug build** | ⏳ **C4b in progress**: `:app:assembleDebug` has not yet been restored to green after the AOSP-17 realignment (16-era historical baseline: DEBUG_RUNTIME_PASS 2026-08-25, APK `e8aad131…`) |
| **Release build** | not run (deferred to task074; 16-era historical baseline: RELEASE_RUNTIME_PASS 2026-08-26, APK `d3968fb2…`) |
| Toolchain | Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10 (AGP `builtInKotlin`) · KSP 2.2.10-2.0.2 · Dagger 2.59.2 · Compose 1.11.4 · material3 1.5.0-alpha18 · JDK 21 · `compileSdkPreview = "SysUISdk"` |
| Config parse | `./gradlew help` / `projects` **BUILD SUCCESSFUL** (all 16 modules recognized; C4a acceptance) |
| Tool tests | `uv run pytest tools/tests/ -q` → **293 passed** (+111 subtests) |
| Source/res alignment | automated alignment check `--strict` exit 0 (MISSING / MISPLACED / EXTRA = 0 / 0 / 0; MODIFIED 1 src + 86 res are whitelisted CONV marks) |
| Artifact regeneration | all 107 artifacts in `libs/` (jars/AARs/POMs) are committed to git **and** deterministically regenerable by `tools/` scripts from AOSP-17 (see Quickstart step 4) |

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

### Module topology (16 Gradle modules, semantically aligned with AOSP 17 `Android.bp`)

| Module | Role (Soong target) |
|---|---|
| `:app` | `android_app "SystemUI"`: APK entry (no sources of its own; minimal manifest merger shell, signing, packaging) |
| `:SystemUI-core` | `android_library "SystemUI-core"`: main module — `SystemUIApplication` and other entry classes, src + compose + pods |
| `:SystemUI-application` | `android_library "SystemUI-application"`: Dagger root component + the full 1338-line AOSP manifest (new in 17) |
| `:SystemUI-res` | Standalone resource namespace (res / res-keyguard / res-product), generates `com.android.systemui.res.R` |
| `:SystemUI-common` | Common + Log + shared-utils, merged |
| `:SystemUI-animation` | PlatformAnimationLib (with res; since 17, surfaceeffects is delivered as jars) |
| `:SystemUI-plugin-core` | PluginCoreLib runtime API (JVM) |
| `:SystemUI-plugin-processor` | PluginAnnotationProcessor (build-time, not packaged) |
| `:SystemUI-plugin` | SystemUIPluginLib runtime (incl. bcsmartspace) |
| `:SystemUI-unfold` | SystemUIUnfoldLib (Dagger via KSP) |
| `:SystemUI-customization` | SystemUICustomizationLib (with res) |
| `:SystemUI-clocks-common` | SystemUIClocks-CommonLib (with res; new in 17, consumed by customization) |
| `:SystemUI-shared` | SystemUISharedLib + keyguard, merged (aidl + res) |
| `:SystemUI-shared-biometrics` | biometrics (own R namespace, consumed by Settings) |
| `:SystemUI-compose` | Compose Core + Scene, merged |
| `:SystemUI-accessibility-floatingmenu-res` | AccessibilityFloatingMenu-res (res-only; new in 17, consumed by SystemUI-res) |

(C4b is in progress adding the `:SystemUI-utils-kairos` tier-① source module per the 17 bp;
the complete topology owner is [AGENTS.md](AGENTS.md) §3.1.)

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

The current baseline is the AOSP release tag **`android-17.0.0_r1`** (Phase C / C1, in-place
switch and full build on 2026-08-27; frameworks/base `94b4c163b`, manifest `5bc9a7ce`,
1084 projects):

- Sources/resources have been fully realigned to the 17 tree (C3, alignment gate `--strict` exit 0);
  the `libs/` artifacts have all been script-regenerated from the 17 tree (C2).
- The `main`-branch snapshot used for 16-era validation remains archived at
  [`docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml`](docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml)
  (1042 projects; see [`docs/aosp-pinning/README.md`](docs/aosp-pinning/README.md)).
- **Re-validation of the build / dual runtime on the 17 baseline and the tag closure are still in
  progress** (C4b/C5/C6; see [docs/PLAN.md](docs/PLAN.md) and
  [docs/adr/0007-phase-c-clean-regen-release-tag.md](docs/adr/0007-phase-c-clean-regen-release-tag.md));
  the formal README version declaration will be updated at C6.

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

**1. Download AOSP (repo init + tag checkout)** — *executed on `android-17.0.0_r1` (C1)*

```bash
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -d -c -j4
# 16-era validated snapshot archive: docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml
```

**2. Build AOSP** — *verified (C1: full `m` build on the 17 tree succeeded, 2h35m; the artifact scripts and the emulator images all consume this build's `out/`)*

```bash
cd <aosp-root> && . build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j4        # outputs include the out/target/product/emu64x/ emulator images
```

**3. Generate SysUISdk** — *verified (Task 045, 16-era baseline; regeneration from the 17 tree is scheduled before C5, all eight inputs verified present)*

```bash
uv run python tools/build_sysuisdk.py --aosp-root <aosp-root>
# Output: <sdk-root>/platforms/android-SysUISdk; see docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md
```

**4. Generate the libs/ artifacts** (only when regenerating) — *verified (C2: 104 deleted →
7 scripts regenerated 102 files from AOSP-17; C4a added 5 new artifacts, 107 files total, all
script-produced)*

```bash
uv run python tools/package_aosp_aar.py --all          # 30 AARs → libs/aars/
uv run python tools/install_aar_to_maven.py            # install as local-Maven AARs (23 families, all 2.0.0) → libs/maven/
uv run python tools/package_aconfig_jars.py --all      # aconfig flags jars (incl. the 12-family merge)
uv run python tools/package_misc_jars.py --all         # misc jars (framework.jar, surfaceeffects×3, …)
uv run python tools/package_compilelib_jars.py         # compilelib debug/release jars
uv run python tools/package_monet_jar.py               # monet jar
uv run python tools/package_viewcapture_motiontool_jars.py
```

**5. Gradle build** — *verified in the 16 era; on the 17 realignment the `:app:assembleDebug`
compile closure (C4b) is in progress and not yet green*

```bash
./gradlew :app:assembleDebug      # Debug APK (C4b target gate)
./gradlew :app:assembleRelease    # optimized Release APK (deferred to task074)
uv run pytest tools/tests/ -q     # toolchain tests (293 passed)
```

**6. Start the emulator** — *verified in the 16 era; relaunching the 17 image is C5*; the full
command and environment variables (`ANDROID_PRODUCT_OUT` / `ANDROID_BUILD_TOP` /
`ANDROID_TMP`, pre-creating the log files, and other pitfalls) are in the runbook:
[docs/issues/2026-08-26-emulator-relaunch-runbook.md](docs/issues/2026-08-26-emulator-relaunch-runbook.md)

**7. Deploy and validate** — *verified in the 16 era (dual gates passed for Debug `e8aad131…`
and Release `d3968fb2…`); re-validation on the 17 baseline is C5*; the staged deployment procedure (root → disable-verity → staged
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
