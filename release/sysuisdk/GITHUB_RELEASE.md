# SysUISdk android-17.0.0_r1-r2

> **Local release draft — not uploaded.** Publish from another machine after applying
> the accompanying project patch. The r1 tag/assets remain unchanged.

## Fix

Preserve Android Studio sync and Android local JVM tests without replacing AOSP
method bodies with stubs. Generator **045.3** relocates the existing ten
libcore/DDMS bridge classes from `android.jar` into a real SDK optional library:

- `optional/sysui-platform-bridge.jar`
- `optional/optional.json`: `com.android.systemui.platform.bridge`, `manifest=false`
- Gradle: public `android.useLibrary("com.android.systemui.platform.bridge")`

All original **39,258 android.jar entry payloads** survive unchanged across the
two JARs. The system-module JAR and hidden AIDL are byte-identical to r1. The
37-entry AOSP bridge allowlist is unchanged; no platform classes enter the APK.

The packager now verifies every generated file against the marker inventory and
rejects modified, missing or extra files before producing a release.

## Assets

- `SysUISdk-android-17.0.0_r1-r2.zip` — **79,983,909 bytes**
- `SysUISdk-android-17.0.0_r1-r2.zip.sha256`

ZIP SHA-256:

```text
329fd0e12a19b8004180fb74f0a9a3817b2e7b3c1fc36617a8af7d535b5543ae
```

Two independent generator outputs were packaged separately and produced
byte-identical ZIPs. The archive includes LICENSE, NOTICE, README.txt and the
full `.sysuisdk-generated.json` provenance inventory. Its own checksum remains
external to avoid a self-referential archive.

## Verification

- Actual Tooling API AndroidProject models: all **13 Android modules**, 26 variant
  records; every Debug UnitTest artifact retained and mockable JAR resolved.
- Real AGP local JVM regression: **4 tests**, 0 failures/errors/skips; exact bridge
  runtime path, Java/Kotlin API access, real host-safe Chunk behavior, enum behavior
  and Android mockable behavior checked.
- SDK composition + packaging tests: **97 passed**, 3 subtests passed.
- Full Python suite: **366 passed**, 154 subtests passed, **1 pre-existing failure**
  (`SettingsLibSettingsThemeProvenance.test_res_entries_match_aosp_tree_exactly`),
  reproduced on unchanged base commit. This release does not claim an all-green suite.
- Debug and Release/R8 builds successful; fresh-daemon repeat explicitly verified
  generated SDK classpaths, optional bridge on R8 library input, not program input.
- Both APKs pass the 725-rule aconfig gate, contain zero definitions from the
  37-class bridge, and have no invented bridge uses-library manifest requirement.
- Both APKs verify with APK Signature Scheme v2.
- Debug APK SHA matches the previously published project Debug APK exactly:
  `e7277867695b85098bee5d3bba06732371ff708471d332e807e5ff08b3a45abd`.
- Release APK SHA for this validation:
  `395959de6cc2b1741244df29ff00b3a1033ff3e5053b108298721268d16281c3`.
  No claim of byte identity with the previous Release APK is made.
- No new device deployment or manual Studio UI session was performed in this run.

## Reproduce

Use the patched project source (tag this source when publishing). Install the
read-only official `android-37.0` SDK platform and build AOSP `android-17.0.0_r1`.
This remains **AOSP outputs plus Google's official SDK base**, not a pure-AOSP base.

Verified input checkout identities:

- AOSP manifest: `5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f`
- frameworks/base: `94b4c163b7dfe5ce3607f7bb8456f9573f7de57d`
- Official base source.properties: Pkg.Revision=2, API=37.0, ExtensionLevel=22
- Packaging runtime used here: uv 0.12.22, Python 3.12.7, zlib 1.2.11

The marker pins the seven exact AOSP artifact/source paths and hashes and every
base file hash; compare them when reproducing. Identical tag names alone do not
pin built artifacts or the official SDK revision. Byte-identical ZIP reproduction
also requires the same compression implementation/settings.

```bash
uv run python tools/build_sysuisdk.py \
  --aosp-root /absolute/path/to/aosp \
  --sdk-root /absolute/path/to/Android/Sdk \
  --output /absolute/path/to/staging/android-SysUISdk

uv run python tools/package_sysuisdk_release.py \
  --platform /absolute/path/to/staging/android-SysUISdk \
  --output /absolute/path/to/dist/SysUISdk-android-17.0.0_r1-r2.zip
```

For an existing generator-owned live SDK, omit `--output` and add `--replace` to
the generator. Stop Gradle daemons before switching SDK roots or replacing the
platform; AGP 9.3.1 has a static bootclasspath cache that omits the SDK root.
Do not overlay ZIP contents onto an old platform.

The fixture and headless IDE-model commands are documented in
`tools/tests/fixtures/sysuisdk_optional_bridge/README.md`. Exact local acceptance
records are in `docs/issues/2026-10-03-sdk-optional-bridge-implementation.md`.
