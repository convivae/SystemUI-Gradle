# Same-tree AOSP ARM64 emulator runtime validation

> Date: 2026-08-22
> Status: local ARM64 userdebug `emu_img_zip` build succeeded; direct-QEMU baseline reaches ADB but is not boot-complete, so official launch research is in progress

## Background

Task 051 proved that the frozen Gradle Debug APK reaches
`SystemUIApplication.<init>()`, but the Google API x86_64 image denies
`Trace.registerWithPerfetto()` because the APK is neither signed by that image's
platform key nor packaged with Soong's `usesNonSdkApi` manifest contract. The
Google image also uses a different SystemUI source/runtime revision.

The user selected solution family B: validate against an ARM64 userdebug Android
Emulator image built from the same AOSP checkout that supplies this project's
framework artifacts and SysUISdk inputs. x86_64 is not required.

## Safety and authority

- Only emulator targets may be used. Physical devices are forbidden.
- Stop the currently running dedicated Google AVD before starting the AOSP emulator.
- Preserve the Google AVD and corrected SDK image; stopping is not deletion.
- Reuse existing AOSP outputs first. Do not start a full rebuild until inventory
  proves that the prior output is not a bootable emulator product and the required
  target is identified.
- AOSP build/output mutations are confined to `/home/conv/myspace/aosp/out/`
  and use the existing checkout. The user explicitly approved compiling the selected
  device product and imposed a hard maximum of `-j4`; no build command may exceed four
  jobs.
- Repository product source, resources, Gradle configuration, SDK and frozen APK
  are unchanged in the environment bring-up phase.
- All waits/polls are bounded to at most 90 seconds.

## Inventory result

The only existing product directory is `out/target/product/generic_arm64`.
Its recorded build config is `aosp_arm64-eng`, and shell history confirms the
previous lunch command was `lunch aosp_arm64`. It contains `system.img`,
`ramdisk.img`, `vbmeta.img`, and a built `SystemUI.apk`, but no emulator kernel,
`vendor.img`, `userdata.img`, or complete goldfish device image set. This is an
ARM64 GSI/system product, not yet proven to be a standalone Android Emulator
phone image.

The frozen Gradle Debug APK certificate SHA-256 is
`c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`, exactly
matching this AOSP checkout's default `platform.x509.pem`. A same-tree emulator
therefore removes the Google platform-signature mismatch.

## Local ARM64 product build result

The approved command was run exactly as bounded:

```bash
lunch sdk_phone64_arm64 trunk_staging userdebug
m -j4 emu_img_zip
```

The first attempt was killed by a kernel-confirmed `soong_build` OOM while a
separate 9 GiB `/tmp` image workspace consumed tmpfs and nearly all swap. After
proving its two largest files byte-identical to persistent Task 050 images and
deleting only those duplicates, the same `-j4` command succeeded without a new
OOM in `01:29:20` (exit `0`). It produced and hashed the complete `emu64a`
kernel/system/vendor/ramdisk/userdata set and a ZIP that passes `unzip -t`.

## Current direct-QEMU probe

The standard launcher and direct AOSP-prebuilt Emulator 35.3.8 both generated
PCI audio devices for ARM `ranchu`, which has no PCI bus in that execution
path. A manually isolated AVD fixed the earlier false SD-card inference but did
not remove the PCI mismatch. Directly invoking SDK Emulator 36.6.6's ARM64
QEMU binary showed the same mismatch. Adding only a trailing
`-machine type=virt` override allowed the locally built ARM64 kernel to reach
`/init` and ADB; the target reports `ro.kernel.qemu=1`, `arm64-v8a`,
`userdebug`, and the expected local `sdk_phone64_arm64/emu64a` fingerprint.

That override is only a diagnostic probe, not an accepted launch solution.
`sys.boot_completed` remains empty, `system_server` is absent, and zygote is
in a SIGABRT restart loop. The Gradle APK has not been deployed. Before another
runtime hypothesis, three parallel read-only investigations will establish the
official command, launcher source mechanism, and actually supported product /
host matrix.

## Existing-output launch result

The dedicated Google AVD was stopped cleanly. Its final recorded identity was
`sysui-gradle-task049-debug-20260822-120226`, x86_64, API 37, and
`ro.kernel.qemu=1`. Afterwards ADB reported no devices and no emulator/QEMU
process remained.

Two bounded launch probes were then run against the existing
`out/target/product/generic_arm64` output:

1. The standard AOSP `emulator` launcher exited `1` with
   `PANIC: QEMU2 emulator does not support arm64 CPU architecture`. The host is
   x86_64, and this launcher explicitly rejects an ARM64 guest on that host.
2. The packaged `qemu-system-aarch64-headless` binary was invoked directly with
   software acceleration disabled. It passed the architecture check but exited
   `1` because the GSI output has no `kernel-ranchu`; its diagnostic also found
   no usable fallback kernel in the SDK system-image directories.

This proves the existing output cannot be opened directly as a complete Android
Emulator. The exact standard product accepted by this branch is
`sdk_phone64_arm64 trunk_staging userdebug`, whose product output is
`out/target/product/emu64a`. A dry lunch succeeds, but that output currently
contains only the tiny configuration files produced by lunch and no images.
The goldfish product's `emu_img_zip` target explicitly requires
`kernel-ranchu`, `system-qemu.img`, `ramdisk-qemu.img`, `vendor-qemu.img`, and
`userdata.img`.

The checkout has the required ARM64 6.6 kernel prebuilt. A real product build is
therefore the next technical step, followed by direct ARM64 QEMU/TCG because the
standard x86_64-host launcher will still reject the guest architecture. This is
a heavy build boundary, not an already-built emulator launch.

## Steps

1. Record current Google AVD identity, stop it cleanly, and verify no emulator remains.
2. Attempt the existing `aosp_arm64-eng` output through the AOSP emulator entrypoint
   only far enough to obtain an authoritative success/failure classification.
3. If it cannot launch, identify the exact goldfish ARM64 phone userdebug lunch target
   and missing artifacts. Do not misclassify the GSI as a bootable emulator image.
4. If an existing bootable product is found, launch it with software ARM64 emulation,
   wait in <=90-second intervals, and capture boot identity.
5. Once booted, verify AOSP fingerprint, `arm64-v8a`, userdebug/eng build type,
   `ro.kernel.qemu=1`, platform certificate, original SystemUI health, and root/remount
   capability.
6. Only after a healthy baseline, deploy the frozen Gradle Debug APK and verify APK
   SHA-256, certificate, PackageManager metadata, hidden-API policy, first fatal, PID
   stability and UI interaction.

## Acceptance

Environment acceptance requires all of:

- no Google API emulator process remains while the AOSP target runs;
- target reports `ro.kernel.qemu=1`, ARM64 ABI, and an AOSP same-tree fingerprint;
- target build is userdebug (preferred) or explicitly documented eng fallback;
- target `framework-res.apk` certificate matches the frozen Gradle Debug APK;
- baseline SystemUI is stable before replacement;
- after replacement, the installed APK hash equals the frozen artifact and runtime
  evidence distinguishes APK defects from image/environment defects.

## Build/error evolution

- Gradle: NOT RUN.
- Existing AOSP output: `aosp_arm64-eng`; both the standard launcher and direct
  ARM64 QEMU probe failed before guest boot because this is not a complete
  goldfish emulator output.
- Standard launcher result: exit `1`, cross-architecture ARM64 guest rejected on
  the x86_64 host.
- Direct QEMU result: exit `1`, missing `kernel-ranchu` in the GSI output.
- Exact target selection: `lunch sdk_phone64_arm64 trunk_staging userdebug`
  succeeds; `out/target/product/emu64a` images have not been built.
- AOSP rebuild: second attempt using exactly `m -j4 emu_img_zip` succeeded in
  `01:29:20` with exit `0`; all required `emu64a` artifacts and the system-image
  ZIP were generated and hashed. The first attempt's kernel-confirmed OOM and
  bounded duplicate-file cleanup are retained in Task 052 evidence.
- Direct runtime probe: local kernel reaches `/init`, ADB is online with the
  expected ARM64 userdebug identity, but `sys.boot_completed` is empty and
  zygote/system_server are not stable. No Gradle APK deployment has occurred.

## Open questions

- Which official AOSP documentation and source-controlled scripts define the
  supported host/guest combinations for ARM64 goldfish images.
- Whether the standard launcher's x86_64-host/ARM64-guest rejection is a product
  policy, an acceleration limitation, or bypassable through a documented software
  emulation path.
- Why both Emulator 35.3.8 and 36.6.6 generated PCI virtio devices for the ARM
  `ranchu` machine, and which official machine/device configuration is expected.
- Which same-tree product is the lowest-risk runtime target on this x86_64 host:
  ARM64 goldfish under TCG, an x86_64 goldfish build, Cuttlefish, or another
  officially supported virtual-device product.
