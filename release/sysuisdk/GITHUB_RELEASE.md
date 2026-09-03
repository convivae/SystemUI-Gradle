# SysUISdk android-17.0.0_r1-r1

Prebuilt `android-SysUISdk` compile platform for SystemUI-Gradle. This r1 asset has been
acceptance-tested by the project owner and builds both project variants without an AOSP
checkout.

## Assets

Download both files into the same directory:

- `SysUISdk-android-17.0.0_r1-r1.zip`
- `SysUISdk-android-17.0.0_r1-r1.zip.sha256`

Verify the archive before extracting it:

```bash
sha256sum --check SysUISdk-android-17.0.0_r1-r1.zip.sha256
```

Expected result:

```text
SysUISdk-android-17.0.0_r1-r1.zip: OK
```

SHA-256: `ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`

## Install

Set `ANDROID_SDK_ROOT` to the SDK used by Gradle. Remove or rename an existing
`android-SysUISdk` first; do not merge two platform versions.

```bash
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
```

Then clone and build the project as documented in
[README.md](https://github.com/convivae/SystemUI-Gradle/blob/main/README.md):

```bash
./gradlew :app:assembleDebug
./gradlew :app:assembleRelease
```

## Provenance and licensing

The platform combines AOSP `android-17.0.0_r1` build outputs with a stock
`android-37.0` SDK platform base. See `NOTICE` inside the archive and
[`release/sysuisdk/NOTICE`](https://github.com/convivae/SystemUI-Gradle/blob/main/release/sysuisdk/NOTICE)
for the component and license breakdown.

The r1 tag is retained at commit `e5ca8dda`; the packaging tool and finalized release
documentation were committed immediately afterward in `928353a0`.
