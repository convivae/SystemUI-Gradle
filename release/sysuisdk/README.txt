SysUISdk r2 — optional platform bridge
=====================================

Release tag: sysuisdk-android-17.0.0_r1-r2
Project: https://github.com/convivae/SystemUI-Gradle
Generator: tools/build_sysuisdk.py, version 045.3

r2 fixes AGP MockableJarTransform / Android Studio sync without stubbing real
AOSP method bodies or disabling Android local JVM tests. The existing 10-class
libcore/DDMS slice is moved byte-for-byte from android.jar into
optional/sysui-platform-bridge.jar. The other 27 bridge entries stay in
android.jar; all 37 remain in core-for-system-modules.jar.

The matching Gradle project uses the public API:
    android { useLibrary("com.android.systemui.platform.bridge") }
The optional library declares manifest=false: it is not an APK program library
or an invented shared library required on the device.

Installation
------------
1. Download SysUISdk-android-17.0.0_r1-r2.zip and its .zip.sha256 sidecar.
2. In the download directory run:
       sha256sum --check SysUISdk-android-17.0.0_r1-r2.zip.sha256
3. Stop Gradle daemons (./gradlew --stop) and close ongoing Studio syncs/builds.
4. Extract only android-SysUISdk/ under your SDK's platforms/ directory.
   Do not overlay it onto an old platform. For an existing installation, either
   regenerate transactionally with --replace (see below), or move the old
   platform outside platforms/ before extracting the complete new directory.
5. Make local.properties sdk.dir point to that SDK root, then sync again.

Reproduction (no hand-patched SDK required)
------------------------------------------
Checkout the release tag of SystemUI-Gradle. Build AOSP android-17.0.0_r1 as
documented in the project README. Install the official Android SDK platform
android-37.0, which is the read-only base (this is not a pure-AOSP SDK base).
Using absolute paths, from the project root:

    uv run python tools/build_sysuisdk.py \
      --aosp-root /path/to/aosp \
      --sdk-root /path/to/Android/Sdk \
      --output /path/to/staging/android-SysUISdk

    uv run python tools/package_sysuisdk_release.py \
      --platform /path/to/staging/android-SysUISdk \
      --name SysUISdk-android-17.0.0_r1-r2 \
      --output /path/to/dist/SysUISdk-android-17.0.0_r1-r2.zip

For an existing generator-owned live platform, omit --output and add --replace
to the generator command. It validates a sibling staging directory before
publishing; it never rewrites the official android-37.0 base in place.

The marker android-SysUISdk/.sysuisdk-generated.json records the exact seven
AOSP input paths/hashes, base-platform file hashes and output file hashes.
Compare these inputs when reproducing the release: the AOSP tag alone does not
guarantee identical build outputs or an identical revision of Google's base SDK.
With identical inputs, both platform generation and release ZIP packaging are
deterministic. The packager rejects files that differ from the marker inventory.
The ZIP's own checksum is external in .zip.sha256 (not embedded recursively).

Verification and limitations
----------------------------
The repo includes a real AGP/JUnit regression fixture and a Tooling API model
gate at tools/tests/fixtures/sysuisdk_optional_bridge/. Release verification
also covers Debug/Release builds, aconfig DEX gates, no packaged bridge classes,
and no new bridge uses-library entry. See the release notes for exact results.
Local JVM testing still does not emulate ART/native platform behavior.

LICENSE and NOTICE describe the AOSP and official SDK component provenance.
