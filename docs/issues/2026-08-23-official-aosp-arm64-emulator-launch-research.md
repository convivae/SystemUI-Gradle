# Official AOSP ARM64 Emulator launch research (Task 052A)

> Date: 2026-08-23
> Status: research-only, no emulator/device/AVD/AOSP/SDK mutation performed
> Authority: `self-commit` (Task 052A brief); reports to Task 052 architect
> Retained official sources reused: `/tmp/emu_rn.txt` (release notes), `/tmp/emu_cmd.txt` (command-line docs)

This report is scoped strictly to Task 052A: it establishes the **officially
documented** build, packaging, AVD/image-installation, and launch path for an
AOSP ARM64 phone image, with explicit evidence for host/guest architecture and
acceleration constraints. It does **not** prescribe undocumented flags and does
not launch or mutate any emulator/device. It complements (does not duplicate)
Task 052B (launcher/QEMU source tracing) and Task 052C (launchable-product
enumeration).

---

## 1. Question and current local facts

**Question.** On this **x86_64 Linux host**, is launching an **ARM64 Android
guest** through the official Android Emulator launcher a supported path, and
what does official documentation say about building/packaging/AVD-installing an
AOSP ARM64 phone image and about host/guest acceleration?

Terminology kept distinct throughout (brief Global Constraints):

- **Guest image/kernel** = the Android system image + `kernel-ranchu` produced
  by the AOSP goldfish product (`sdk_phone64_arm64` → device `emu64a`).
- **Host Emulator/QEMU binary** = the `emulator` launcher and the
  `qemu-system-<arch>` engines shipped with the Android SDK Emulator package.

**Local facts recorded in the Task 052 issue** (`docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md`),
re-read for this report:

- Host is **x86_64**. The standard AOSP `emulator` launcher, pointed at the
  existing `generic_arm64` (`aosp_arm64-eng`) GSI output, exited `1` with
  `PANIC: QEMU2 emulator does not support arm64 CPU architecture` — i.e. the
  launcher explicitly rejects an ARM64 guest on the x86_64 host.
- Directly invoking SDK Emulator 36.6.6's ARM64 QEMU binary passed the
  architecture check but exited `1` because the GSI output has no
  `kernel-ranchu`; its diagnostic found no usable fallback kernel in the SDK
  system-image directories.
- Both Emulator **35.3.8** (AOSP prebuilt) and **36.6.6** (installed SDK) generated
  PCI virtio devices for the ARM `ranchu` machine, which has no PCI bus in that
  execution path.
- Adding only a trailing `-machine type=virt` override let the locally built
  ARM64 kernel reach `/init` and ADB; the target reported `ro.kernel.qemu=1`,
  `arm64-v8a`, `userdebug`, and the expected local `sdk_phone64_arm64/emu64a`
  fingerprint. That override is recorded as a **diagnostic probe only**: `sys.boot_completed`
  remained empty, `system_server` was absent, and zygote was in a SIGABRT
  restart loop. No Gradle APK was deployed.
- The approved same-tree build was run exactly as bounded:
  `lunch sdk_phone64_arm64 trunk_staging userdebug` then `m -j4 emu_img_zip`,
  which succeeded (exit `0`) and produced the complete `emu64a`
  kernel/system/vendor/ramdisk/userdata set plus a ZIP that passes `unzip -t`.
- Existing `out/target/product/generic_arm64` (`aosp_arm64-eng`) is an ARM64
  GSI/system product, **not** a complete goldfish emulator phone image: it has
  `system.img`, `ramdisk.img`, `vbmeta.img`, a built `SystemUI.apk`, but no
  emulator kernel, `vendor.img`, `userdata.img`, or complete goldfish device
  image set.

These local facts motivate the official-documentation questions below; they are
**observations**, not official support statements.

---

## 2. Official build and packaging commands

The authoritative definition of the ARM64 goldfish phone product and its
emulator-image packaging target lives in the AOSP source tree itself (a primary
source), read-only for this report.

**Product definition — `sdk_phone64_arm64` (device `emu64a`).**
Local path: `/home/conv/myspace/aosp/device/generic/goldfish/64bitonly/product/sdk_phone64_arm64.mk`
quoted head:

```
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
...
$(call inherit-product, device/generic/goldfish/board/emu64a/details.mk)
$(call inherit-product, device/generic/goldfish/product/phone.mk)

PRODUCT_BRAND := Android
PRODUCT_NAME := sdk_phone64_arm64
PRODUCT_DEVICE := emu64a
PRODUCT_MODEL := Android SDK built for arm64
```

It is registered in the goldfish product list. Local path:
`/home/conv/myspace/aosp/device/generic/goldfish/AndroidProducts.mk`:

```
PRODUCT_MAKEFILES := \
    ...
    $(LOCAL_DIR)/64bitonly/product/sdk_phone64_arm64.mk \
    $(LOCAL_DIR)/64bitonly/product/sdk_phone64_arm64_minigbm.mk \
    ...
```

So the **official lunch target** for an ARM64 goldfish phone on this branch is
`sdk_phone64_arm64` (device `emu64a`). This matches the command actually run in
the Task 052 issue (`lunch sdk_phone64_arm64 trunk_staging userdebug`).
`trunk_staging` is the branch/release config and `userdebug` is the build type;
both are standard AOSP `lunch` syntax.

**Packaging target — `emu_img_zip`.** Local path:
`/home/conv/myspace/aosp/device/generic/goldfish/tasks/emu_img_zip.mk`.
Its header and the make target verbatim:

```
# Rules to generate a zip file that contains google emulator images
# and other files for distribution

ifneq ($(filter sdk_% gcar_%, $(TARGET_PRODUCT)),)
...
ifeq ($(TARGET_ARCH), x86)
# a 32bit guest on a 64bit kernel
EMULATOR_KERNEL_DIST_NAME := kernel-ranchu-64
else
EMULATOR_KERNEL_DIST_NAME := kernel-ranchu
endif # x86
...
INSTALLED_QEMU_SYSTEMIMAGE := $(PRODUCT_OUT)/system-qemu.img
INSTALLED_QEMU_RAMDISKIMAGE := $(PRODUCT_OUT)/ramdisk-qemu.img
INSTALLED_QEMU_VENDORIMAGE := $(PRODUCT_OUT)/vendor-qemu.img
PRODUCT_OUT_DATA_FILES := $(PRODUCT_OUT)/userdata.img # also builds $(PRODUCT_OUT)/data
...
.PHONY: emu_img_zip
emu_img_zip: $(INTERNAL_EMULATOR_PACKAGE_TARGET)
...
INTERNAL_EMULATOR_PACKAGE_TARGET := $(PRODUCT_OUT)/sdk-repo-linux-system-images.zip
```

The target is gated on `TARGET_PRODUCT` matching `sdk_%` or `gcar_%`, so it only
applies to SDK/goldfish emulator products (including `sdk_phone64_arm64`). For
an ARM64 guest (`TARGET_ARCH != x86`) it requires `kernel-ranchu` (not
`kernel-ranchu-64`) plus `system-qemu.img`, `ramdisk-qemu.img`,
`vendor-qemu.img`, and `userdata.img`, and emits
`sdk-repo-linux-system-images.zip`. This is the **officially defined packaging
target**; it is exactly the command run in the Task 052 issue (`m -j4 emu_img_zip`)
and exactly the artifact set the issue confirms was produced.

**AOSP prebuilt Emulator 35.3.8.** Local path:
`/home/conv/myspace/aosp/prebuilts/android-emulator/linux-x86_64/source.properties`
→ `Pkg.Revision=35.3.8`, `Pkg.BuildId=12560773`, `Pkg.Desc=Android Emulator`.
This is the Emulator package prebuilt checked into AOSP, used by the AOSP
`emulator` launcher entrypoint.

**Installed SDK Emulator 36.6.6.** Local path:
`/home/conv/Android/Sdk/emulator/source.properties` → `Pkg.Revision=36.6.6`,
`Pkg.BuildId=15272510`, `Pkg.Desc=Android Emulator`. Its guest-emulation engines
live under `/home/conv/Android/Sdk/emulator/qemu/linux-x86_64/`, including
`qemu-system-aarch64`, `qemu-system-aarch64-headless`, `qemu-system-armel(-headless)`,
`qemu-system-i386(-headless)`, and `qemu-system-x86_64(-headless)`. The directory
name `linux-x86_64` is the **host** architecture; the binaries inside are
guest-architecture emulation engines.

> Note (not a build command): the only **host-side** ARM64 build instruction in
> official Emulator documentation is the 30.0.26 release-note "Emulator for
> ARM64 hosts" cross-compile recipe (see §4/§5). That builds the **emulator
> binary** for an ARM64 host; it is not a guest-image build command.

---

## 3. Official AVD/image installation and launch commands

From the retained command-line documentation (`/tmp/emu_cmd.txt`, fetched from
`kb://android/studio/run/emulator-commandline`, canonical URL
https://developer.android.com/studio/run/emulator-commandline):

**Start the emulator (AVD-based):**

```
emulator -avd avd_name [ {-option [value]} … ]
emulator @avd_name [ {-option [value]} … ]
emulator -list-avds
```

**AVD system directory** (where the emulator reads the goldfish image set):

> "macOS and Linux - `~/Library/Android/sdk/system-images/android-apiLevel/variant/arch/`"
> ... `arch` "is the target CPU architecture. For example, `x86`."
> The emulator reads `kernel-qemu` or `kernel-ranchu`, `ramdisk.img`,
> `system.img`, `userdata.img` from the system directory; `-kernel` overrides
> the kernel and "If you don't specify this option, the default is `kernel-ranchu`."
> "`kernel-ranchu` is based on the QEMU emulator."

**AVD data directory:** `~/.android/avd/name.avd/` (`-datadir` overrides);
`userdata-qemu.img` is the writable data partition (`-data`), `cache.img`
(`-cache`), `sdcard.img` (`-sdcard`).

**Install an app on a running AVD:** build/package the APK, start the emulator,
then install with `adb` (the doc treats the emulator as a device for `adb`).
Uninstall as on a physical device; `-wipe-data` resets to factory defaults.

**Locally built images — SDK AVD installation (unknown).** The command-line
guide documents the `emulator -avd <name>` launch surface and the SDK
system-image directory layout (`~/Library/Android/sdk/system-images/android-apiLevel/variant/arch/`,
above), but it does **not** document a canonical manual installation command for
the locally generated `sdk-repo-linux-system-images.zip` produced by `emu_img_zip`
(§2). This research did **not** find an official, first-party manual installation
procedure for that locally generated ZIP; the generic directory layout above is
therefore **not** presented as a proven installation procedure. This is recorded
as an explicit unknown (§7). The Task 052 issue shows this host's only installed
system-image tree is `android-37.0`; no `arm64` arch tree is installed, consistent
with the launcher rejecting an ARM64 guest here.

**Locally built images — AOSP source-controlled Goldfish local-image runner.**
AOSP ships a source-controlled runner for a locally built image on a local
instance: `acloud`. Local path: `/home/conv/myspace/aosp/tools/acloud/README.md`
(§"create", lines ~45-73) documents the four `acloud create` use cases and
states: "Create is the main entry point in creating an AVD, supporting both
remote instance (running on a virtual machine in the cloud) and local instance
(running on your local host) use cases. You also have the option to use a
locally built image or an image from the Android Build servers." The
local-instance + locally-built-image case is documented as:

> `$ acloud create --local-instance --local-image`

The AVD type is selectable. Local path:
`/home/conv/myspace/aosp/tools/acloud/create/create_args.py` (lines ~580-588)
defines the `--avd-type` argument with `choices=[constants.TYPE_GCE,
constants.TYPE_CF, constants.TYPE_GF, constants.TYPE_CHEEPS, constants.TYPE_FVP,
constants.TYPE_TRUSTY]`; `constants.TYPE_GF = "goldfish"` is defined in
`/home/conv/myspace/aosp/tools/acloud/internal/constants.py` (line 44). So the
exact official same-checkout local Goldfish entry, after `lunch`/build
environment setup, is:

> `acloud create --local-instance --local-image --avd-type goldfish`

(This report does **not** run it — forbidden by the brief.) When the
`--local-image` path is omitted, acloud resolves it from the build environment.
Local path: `/home/conv/myspace/aosp/tools/acloud/create/avd_spec.py`,
`_GetLocalImagePath` (lines ~532-555): "If the value is empty, this method
returns ANDROID_PRODUCT_OUT in build environment" — i.e. an omitted
`--local-image` resolves to `$ANDROID_PRODUCT_OUT`.

The launch still goes through the **top-level `emulator` launcher**. Local
path: `/home/conv/myspace/aosp/tools/acloud/create/goldfish_local_image_local_instance.py`,
`_StartEmulatorProcess` (lines ~499-544). It copies the host environment, sets
`ANDROID_PRODUCT_OUT` to the image dir, `ANDROID_TMP` to the working dir, and
`ANDROID_BUILD_TOP` (if unset) to the image dir, then builds the command:

```
[<emulator_path>, "-verbose", "-show-kernel", "-read-only",
 "-ports", "<console_port>,<adb_port>",
 "-logcat-output", <logcat_path>, "-stdouterr-file", <stdouterr_path>]
```

and runs `subprocess.Popen(emulator_cmd, ..., env=emulator_env, ...)`. The
binary name is `_EMULATOR_BIN_NAME = "emulator"` (line 59), i.e. the same
top-level `emulator` launcher the AOSP prebuilt/SDK ship (§2). The class
docstring (lines 19-21) confirms it "runs the emulator in build environment"
using "the prebuilt emulator in ANDROID_EMULATOR_PREBUILTS."

**Reconciliation with 052B.** Because `acloud ... --avd-type goldfish` invokes
the **same top-level `emulator` launcher** (not a separate ARM64-guest engine),
it does **not** bypass the x86_64-host→ARM64 target mapping rejection that 052B
traces. On this x86_64 host, the launcher still PANICs on an ARM64 guest (§4.3);
acloud is the official local-image *entry*, but the underlying launch is subject
to the same host/guest-architecture and acceleration constraints documented in
§4. In other words: acloud makes the local Goldfish image *launchable by the
official runner*; it does not make an ARM64 guest *supported on an x86_64 host*.

> Scope note: this report cites the *documented* AVD/launch surface and the
> AOSP source-controlled runner only. It does not create, delete, or start any
> AVD or run `acloud` (forbidden by the brief).

---

## 4. Host/guest architecture and acceleration support

This is the decisive section. Two independent official sources converge.

### 4.1 The only "ARM64 hosts" statement means ARM64 host + ARM64 image + KVM

From the retained release notes (`/tmp/emu_rn.txt`, fetched from
`kb://android/studio/releases/emulator`, canonical URL
https://developer.android.com/studio/releases/emulator), under
**30.0.26 (August 16, 2020) — "Emulator for ARM64 hosts"**:

> "Linux emulator source code now supports cross compilation from x86_64 to
> arm64 hosts, enabling running arm64 system images with KVM virtualization.
> Currently, only `-gpu swiftshader_indirect` (Swiftshader arm64 host rendering)
> is supported, but a compatible set of host GPU libEGL/libGLESv2 libraries may
> also be used by replacing lib64/gles_swiftshader with them and then relaunching
> with `-gpu swiftshader_indirect`. Snapshots may also not be working (add
> `-no-snapshot` to the command line)."

Three points are explicit in this primary source:

1. It is a **cross-compilation of the emulator binary** ("from x86_64 to arm64
   hosts") — i.e. produce an emulator that *runs on an ARM64 host*. It is not a
   statement about running an ARM64 guest on an x86_64 host.
2. The release-note text describes the supported execution mode as **"running
   arm64 system images with KVM virtualization"** on that ARM64 host. (Inference,
   not stated by the release note: KVM virtualization of an ARM64 guest requires
   an AArch64 host CPU, so this x86_64 host is not covered by that statement.)
3. It mentions only `-gpu swiftshader_indirect` and `-no-snapshot`; it does
   **not** mention TCG, cross-architecture ARM64-guest-on-x86_64, or any
   `-machine`/`-accel` flag enabling that combination.

Therefore the release-note "ARM64 hosts" support = **AArch64 host + ARM64 image
+ KVM**, not ARM64 guest on x86_64 host.

### 4.2 Command-line docs: acceleration is for x86/x86_64 images only

From the retained command-line docs (`/tmp/emu_cmd.txt`, canonical URL
https://developer.android.com/studio/run/emulator-commandline), System options:

> **`-accel mode`** — "Accelerated emulation works for x86 and x86_64 system
> images only. On Linux, it relies on KVM. On Windows and Mac, it relies on an
> Intel CPU and Intel HAXM driver. This option is ignored if you're not
> emulating an x86 or x86_64 device." Valid modes: `auto`, `off`, `on`.
>
> **`-no-accel`** — "Disables emulator VM acceleration when using an x86 or
> x86_64 system image. It's useful for debugging only and is the same as
> specifying `-accel off`."
>
> **`-accel-check`** — "Checks whether a required hypervisor for emulator VM
> acceleration is installed (HAXM or KVM)."

So the documented accelerated path and the documented `-no-accel` debugging
path are both scoped to **x86 / x86_64 system images**. The docs do not describe
any `-accel`/`-no-accel` mode for an ARM64 guest, and `-accel` is explicitly
"ignored if you're not emulating an x86 or x86_64 device."

The docs also name the engine selection:

> **`-engine engine`** — `auto` (default), `classic` (older QEMU 1, deprecated),
> `qemu2` (newer QEMU 2).

and the kernel (`kernel-ranchu`, based on QEMU). Nothing in the command-line
docs describes a supported `emulator` launcher invocation that boots an ARM64
guest on an x86_64 host.

### 4.3 Local confirmation: x86_64 launcher rejects arm64 guest

Recorded in the Task 052 issue (§1): the standard AOSP `emulator` launcher on
this x86_64 host, pointed at ARM64 output, exited `1` with
`PANIC: QEMU2 emulator does not support arm64 CPU architecture`. This is the
behaviour consistent with §4.1/§4.2: the launcher does not offer an
officially-supported ARM64-guest-on-x86_64 path.

### 4.4 Direct QEMU and `-machine type=virt` are diagnostic only

The Task 052 issue records that directly invoking SDK Emulator 36.6.6's
`qemu-system-aarch64-headless` (`/home/conv/Android/Sdk/emulator/qemu/linux-x86_64/qemu-system-aarch64-headless`,
§2) passed the architecture check but exited `1` for want of `kernel-ranchu` in
the GSI; and that a trailing `-machine type=virt` override let the locally
built ARM64 kernel reach `/init` and ADB but did **not** complete boot
(`sys.boot_completed` empty, zygote SIGABRT loop). Neither direct QEMU invocation
nor `-machine type=virt` is described by the command-line docs as a supported
Android Emulator launch solution (the docs' launch surface is `emulator -avd ...`
plus its documented options; `-qemu` is flagged as "quite advanced and should be
used only by developers who are very familiar with QEMU and Android emulation").
They remain **diagnostic probes**, not official launch paths.

---

## 5. Emulator-version evidence (35.3.8 and 36.6.6)

Per the brief, the release notes were checked for ARM64-guest,
cross-architecture, TCG, ranchu, or virtio-device restrictions/fixes relevant
to Emulator **35.3.8** and **36.6.6**.

**Installed/prebuilt versions confirmed locally:**

- 35.3.8 — `/home/conv/myspace/aosp/prebuilts/android-emulator/linux-x86_64/source.properties`
  → `Pkg.Revision=35.3.8`, `Pkg.BuildId=12560773`.
- 36.6.6 — `/home/conv/Android/Sdk/emulator/source.properties`
  → `Pkg.Revision=36.6.6`, `Pkg.BuildId=15272510`.

**Release-note survey** (`/tmp/emu_rn.txt`, https://developer.android.com/studio/releases/emulator):

- The **only** "ARM64 hosts" release-note entry is **30.0.26 (August 16, 2020)**
  (§4.1). It is about cross-compiling the emulator for an ARM64 host and running
  arm64 images with KVM on that host. It is not about an ARM64 guest on an
  x86_64 host and does not name TCG or cross-architecture guest emulation.
- The **35.3.x** stable line (closest entry **35.3.11 Stable, Jan 9, 2025**)
  contains no ARM64-guest / cross-architecture / TCG / ranchu / virtio entry
  relevant to launching an ARM64 guest on x86_64. (35.6.11's
  "libndk_translation.so aborts ... in Arm64AesEncode" corroborates that ARM
  ABIs on x86/x86_64 images are served by **NDK translation**, not full ARM
  emulation — a guest-ABI convenience, not a launch path for an ARM64 system
  image.)
- The **36.6.x** line (up to **36.6.11 Stable, Jun 2, 2026**) likewise contains
  no ARM64-guest-on-x86_64 entry. 36.2.11 (Oct 9, 2025) removed HAXM and points
  to AEHD; 36.4.9 (Feb 10, 2026) added `-gpu software`; 36.5.10 (Apr 2, 2026)
  added multi-device networking (the release-note heading is "Test Multi-Device
  Interactions with Android Emulator"); 36.6.11 raised API-37 minimum RAM to 4 GB and
  added the "environment" camera mode. None reintroduces ARM64-guest-on-x86_64
  launcher support, TCG-based ARM64 guest, or an ARM-ranchu PCI/virtio fix.
- Older cross-arch context: 30.0.0 (Feb 19, 2020) "Android 11 system images" —
  x86 and x86_64 images "include ... ARMv7 and ARM64 ABIs" via the ARM-binary
  translation support, explicitly "not ... full ARM emulation." 29.0.11 (May 29,
  2019) added a headless build for 32-bit x86 guests and noted 64-bit-engine
  selection for 32-bit x86 guests. Both concern x86-family guests, not ARM64
  guests on x86_64.

**Conclusion of the version survey:** through 36.6.11 there is **no**
release-note statement that the `emulator` launcher supports an ARM64 guest on
an x86_64 host, and no TCG/cross-arch/ranchu/virtio fix that changes the §4
verdict. The single ARM64-host support statement (30.0.26) requires an ARM64
host CPU + KVM.

---

## 6. Supported-command matrix

"`x86_64-host/ARM64-guest supported?`" answers whether the **official Android
Emulator launcher** (`emulator -avd ...`) supports that combination on this host,
per §4. "Owning source" is the primary document/path that defines the command.

| Command | Owning source (URL/path) | Prerequisites | Expected artifact/device | x86_64-host/ARM64-guest supported? |
|---|---|---|---|---|
| `lunch sdk_phone64_arm64 trunk_staging userdebug` | AOSP build system; product def `/home/conv/myspace/aosp/device/generic/goldfish/64bitonly/product/sdk_phone64_arm64.mk` and `/home/conv/myspace/aosp/device/generic/goldfish/AndroidProducts.mk` | AOSP checkout, `build/envsetup.sh` sourced | Selects ARM64 goldfish phone product `sdk_phone64_arm64` (device `emu64a`), build type `userdebug` | N/A (build-time; produces an ARM64 guest image set, not a launch) |
| `m -j4 emu_img_zip` | `/home/conv/myspace/aosp/device/generic/goldfish/tasks/emu_img_zip.mk` (`.PHONY: emu_img_zip`; the `-j4` is this project's host safety limit per Task 052, not part of the upstream make target) | `sdk_%`/`gcar_%` TARGET_PRODUCT; goldfish product built | `sdk-repo-linux-system-images.zip` containing `kernel-ranchu`, `system-qemu.img`, `ramdisk-qemu.img`, `vendor-qemu.img`, `userdata.img` under `<TARGET_CPU_ABI>/` | N/A (packaging; produces the ARM64 guest image ZIP) |
| `emulator -avd <name>` | https://developer.android.com/studio/run/emulator-commandline ("Start the emulator") | An AVD whose system-image `arch` matches a supported guest; a host-supported accelerator for x86/x86_64 | A booted AVD | **No** for ARM64 guest on this x86_64 host — launcher PANICs `QEMU2 emulator does not support arm64 CPU architecture` (Task 052 issue) |
| `emulator -avd <name> -accel auto\|on\|off` | https://developer.android.com/studio/run/emulator-commandline (`-accel`) | "x86 and x86_64 system images only"; Linux KVM / Intel HAXM (HAXM removed in 36.2.11 → AEHD) | Accelerated x86/x86_64 AVD | **No** for ARM64 guest — `-accel` "is ignored if you're not emulating an x86 or x86_64 device" |
| `emulator -avd <name> -no-accel` | https://developer.android.com/studio/run/emulator-commandline (`-no-accel`) | x86/x86_64 system image; debugging only | x86/x86_64 AVD without acceleration | **No** for ARM64 guest — scoped to x86/x86_64 images |
| `emulator -avd <name> -engine auto\|classic\|qemu2` | https://developer.android.com/studio/run/emulator-commandline (`-engine`) | A supported AVD | Selects QEMU1 (deprecated)/QEMU2 engine | **No** for ARM64 guest on x86_64 (engine choice does not lift the arch rejection) |
| `emulator -accel-check` | https://developer.android.com/studio/run/emulator-commandline (`-accel-check`) | Host hypervisor present | Reports HAXM/KVM availability | **No** for ARM64 guest (it checks x86/x86_64 acceleration prerequisites) |
| `acloud create --local-instance --local-image --avd-type goldfish` | `/home/conv/myspace/aosp/tools/acloud/README.md` (§"create"); `create_args.py` `--avd-type`; `avd_spec.py` `_GetLocalImagePath`; `goldfish_local_image_local_instance.py` `_StartEmulatorProcess` | AOSP build env (`lunch` done, `$ANDROID_PRODUCT_OUT` set); locally built goldfish image set | A local Goldfish instance launched via the top-level `emulator` launcher (`-verbose -show-kernel -read-only -ports ...`) | **No** for ARM64 guest on this x86_64 host — acloud invokes the same top-level `emulator` launcher (§3), so the §4.3 PANIC still applies; it does not bypass 052B's x86_64-host→ARM64 target mapping rejection |
| Direct `qemu-system-aarch64-headless ...` (SDK 36.6.6) | QEMU; binary at `/home/conv/Android/Sdk/emulator/qemu/linux-x86_64/qemu-system-aarch64-headless`; not a documented `emulator` launcher option | `kernel-ranchu` + goldfish image set | (diagnostic) kernel reaches `/init`, ADB online | **Not an official Android Emulator launch path** — diagnostic only; exited `1` on GSI for missing `kernel-ranchu` (Task 052 issue) |
| Trailing `-machine type=virt` override | Not documented as a launch solution in https://developer.android.com/studio/run/emulator-commandline (`-qemu` flagged "quite advanced") | A bootable ARM64 kernel + image set | (diagnostic) kernel reaches `/init`, ADB online but boot incomplete | **Not an official launch solution** — diagnostic only; `sys.boot_completed` empty, zygote SIGABRT loop (Task 052 issue) |

---

## 7. Recommendation, confidence, and unresolved questions

**Recommendation (bounded).** Treat an ARM64 guest on this x86_64 host as **not
an officially supported Android Emulator launcher path**. Official documentation
supports ARM64 only as **AArch64 host + ARM64 image + KVM** (release notes
30.0.26) and scopes the `emulator` launcher's acceleration (`-accel`/`-no-accel`)
to **x86/x86_64** images (command-line docs). The local x86_64 launcher's
`PANIC: QEMU2 emulator does not support arm64 CPU architecture` is consistent
with that. Direct `qemu-system-aarch64-headless` and a trailing
`-machine type=virt` are **diagnostic probes only** — they reached `/init` and
ADB but never completed boot, and neither is documented as a launch solution.

Do **not** pursue an ARM64-guest-on-x86_64 launch through the `emulator` launcher
as if it were a supported path; do **not** rely on `-machine type=virt` or other
undocumented `-qemu` overrides as a production launch mechanism (the brief
forbids prescribing undocumented flags, and the command-line docs flag `-qemu` as
"quite advanced ... very familiar with QEMU and Android emulation"). For a
same-tree ARM64 runtime, the officially-supported route per release notes 30.0.26
requires an **AArch64 host** (with KVM), which this host is not. Alternative
same-tree virtual-device products and the launcher/QEMU source mechanism for the
ranchu/PCI mismatch are explicitly out of scope here and are owned by Task 052B
and Task 052C.

**Confidence.**

- **High** that the `emulator` launcher does not officially support an ARM64
  guest on an x86_64 host: two independent primary sources (release notes 30.0.26;
  command-line docs `-accel`/`-no-accel`) plus the local PANIC all agree.
- **High** that `lunch sdk_phone64_arm64 trunk_staging userdebug` + `m -j4 emu_img_zip`
  (upstream make target `emu_img_zip`; `-j4` is this project's host safety limit)
  is the officially-defined ARM64 goldfish phone build/package path, from the
  AOSP source `AndroidProducts.mk`, `sdk_phone64_arm64.mk`, and
  `emu_img_zip.mk`.
- **Medium** that no later Emulator version (through 36.6.11) silently added
  ARM64-guest-on-x86_64 support: the release notes contain no such entry, but
  absence of a release-note line is not a positive proof of non-existence.
- **Low** (not claimed) about why the `-machine type=virt` probe reached `/init`
  but failed to complete boot — that is a Task 052B/052C source-tracing question,
  out of scope for this report.

**Unresolved questions (handed to 052B/052C, not answered here).**

- Why do Emulator 35.3.8 and 36.6.6 generate PCI virtio devices for the ARM
  `ranchu` machine, and which official machine/device configuration is expected
  for an ARM64 goldfish image? (052B)
- What is the launcher's architecture-rejection source path from `emulator` to
  the `QEMU2 emulator does not support arm64 CPU architecture` PANIC, and is it a
  policy gate or an acceleration limitation? (052B)
- Which launchable virtual-device products does this checkout expose, and is an
  x86_64 goldfish build, Cuttlefish, or another product the lowest-risk
  same-tree runtime target on this host? (052C)
- This research found the AOSP source-controlled `acloud` local-image runner
  (`acloud create --local-instance --local-image --avd-type goldfish`, §3) as
  the official same-checkout launch entry, but confirmed it invokes the
  top-level `emulator` launcher and so does not bypass the §4.3 rejection. It
  did **not** find a canonical official manual installation command for the
  locally generated `sdk-repo-linux-system-images.zip` into the SDK
  `system-images/` tree; that SDK-side installation procedure remains an open
  question (not needed if `acloud` is used, since `acloud` consumes
  `$ANDROID_PRODUCT_OUT` directly).

---

## 8. Primary sources (full URLs/paths)

Official (retained) documentation, fetched via `android docs fetch` into
`/tmp/emu_rn.txt` and `/tmp/emu_cmd.txt`:

- Emulator release notes — https://developer.android.com/studio/releases/emulator
  (kb://android/studio/releases/emulator) → `/tmp/emu_rn.txt`. Decisive quote in
  §4.1 under "30.0.26 (August 16, 2020) — Emulator for ARM64 hosts".
- Use Android Emulator on the Command Line —
  https://developer.android.com/studio/run/emulator-commandline
  (kb://android/studio/run/emulator-commandline) → `/tmp/emu_cmd.txt`. Decisive
  quotes in §4.2 (`-accel`, `-no-accel`, `-accel-check`, `-engine`, `-kernel`).
- Configure hardware acceleration for the Android Emulator —
  https://developer.android.com/studio/run/emulator-acceleration (referenced by
  the `-accel` / `-no-accel` entries in `/tmp/emu_cmd.txt`).
- Run apps on the Android Emulator —
  https://developer.android.com/studio/run/emulator (referenced in
  `/tmp/emu_cmd.txt` "Start the emulator").
- Emulator download archive — https://developer.android.com/studio/emulator_archive
  (referenced in `/tmp/emu_rn.txt`).

Local AOSP source (read-only primary sources for build/package):

- `/home/conv/myspace/aosp/device/generic/goldfish/AndroidProducts.mk` —
  registers `sdk_phone64_arm64.mk` (§2).
- `/home/conv/myspace/aosp/device/generic/goldfish/64bitonly/product/sdk_phone64_arm64.mk`
  — `PRODUCT_NAME := sdk_phone64_arm64`, `PRODUCT_DEVICE := emu64a`,
  `PRODUCT_MODEL := Android SDK built for arm64` (§2).
- `/home/conv/myspace/aosp/device/generic/goldfish/tasks/emu_img_zip.mk` —
  `.PHONY: emu_img_zip`, `EMULATOR_KERNEL_DIST_NAME := kernel-ranchu`,
  `sdk-repo-linux-system-images.zip` (§2).
- `/home/conv/myspace/aosp/prebuilts/android-emulator/linux-x86_64/source.properties`
  — Emulator **35.3.8**, `Pkg.BuildId=12560773` (§2, §5).
- `/home/conv/Android/Sdk/emulator/source.properties` — Emulator **36.6.6**,
  `Pkg.BuildId=15272510` (§2, §5).
- `/home/conv/Android/Sdk/emulator/qemu/linux-x86_64/qemu-system-aarch64-headless`
  — the ARM64-guest QEMU engine invoked directly in the Task 052 diagnostic
  (§2, §4.4).
- `/home/conv/myspace/aosp/tools/acloud/README.md` — `acloud create` use cases,
  incl. `acloud create --local-instance --local-image` (§3).
- `/home/conv/myspace/aosp/tools/acloud/create/create_args.py` — `--avd-type`
  argument with `goldfish` (`constants.TYPE_GF`) choice (§3).
- `/home/conv/myspace/aosp/tools/acloud/internal/constants.py` —
  `TYPE_GF = "goldfish"` (§3).
- `/home/conv/myspace/aosp/tools/acloud/create/avd_spec.py` — `_GetLocalImagePath`
  resolves an omitted `--local-image` to `$ANDROID_PRODUCT_OUT` (§3).
- `/home/conv/myspace/aosp/tools/acloud/create/goldfish_local_image_local_instance.py`
  — `_StartEmulatorProcess` sets `ANDROID_PRODUCT_OUT`/`ANDROID_TMP`/
  `ANDROID_BUILD_TOP` and invokes the top-level `emulator` launcher with
  `-verbose -show-kernel -read-only -ports ...` (§3).

Project issue/plan (Task 052 context, the brief's referenced documents):

- `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md` — local
  host/guest failure observations (PANIC, direct-QEMU exit, `-machine type=virt`
  diagnostic, `emu_img_zip` build success) cited in §1/§4.3/§4.4.
- `docs/superpowers/plans/2026-08-22-same-tree-arm64-emulator-runtime.md` —
  Phase 2.5 scopes this Task 052A alongside 052B and 052C.

> No AI answer, search-result snippet, or unsourced forum post is cited as
> evidence. Every decisive claim above is tied to one of the URLs/paths listed
> here with quoted text or line context.
