# Same-tree AOSP ARM64 emulator runtime validation

> Date: 2026-08-22
> Status: Task 052 ARM64 build/probe and Tasks 052A/B/C research complete; ARM64 direct-QEMU `virt` remains diagnostic-only, and the selected next runtime candidate is host-native `sdk_phone64_x86_64` (not yet built)

## Background

Task 051 proved that the frozen Gradle Debug APK reaches
`SystemUIApplication.<init>()`, but the Google API x86_64 image denies
`Trace.registerWithPerfetto()` because the APK is neither signed by that image's
platform key nor packaged with Soong's `usesNonSdkApi` manifest contract. The
Google image also uses a different SystemUI source/runtime revision.

The user selected solution family B: validate against a userdebug virtual-device image
built from the same AOSP checkout that supplies this project's framework artifacts and
SysUISdk inputs. The initial ARM64 Goldfish product was built to test that path, but the
same-tree requirement does not require a particular guest ISA; framework revision and
platform-key identity are independent of guest architecture.

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
in a SIGABRT restart loop. The Gradle APK has not been deployed. Tasks 052A/B/C
have now established the official command, launcher source mechanism, and supported
product/host matrix; their synthesis is recorded below.

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

The checkout has the required ARM64 6.6 kernel prebuilt, and the complete ARM64 product
was built successfully as recorded above. The later source review supersedes the earlier
idea of continuing with direct ARM64 QEMU/TCG: on this x86_64 host, the top-level
Android Emulator launcher deliberately rejects the ARM64 guest, while direct
`qemu-system-aarch64-headless -machine type=virt` does not reproduce the Goldfish board
contract and cannot produce a healthy Android baseline. No further direct-QEMU flag
experiments are planned.

## Official-launch and product-matrix synthesis (Tasks 052A/B/C)

The three independent, read-only reports converge on one bounded conclusion:

1. **ARM64 build/package is supported.** The branch exposes
   `sdk_phone64_arm64 trunk_staging userdebug`; `m -j4 emu_img_zip` produced a valid
   system-image ZIP and complete `emu64a` artifacts.
2. **Official ARM64 runtime is not supported on this x86_64 host.** The x86_64-built
   top-level launcher has no ARM64 result in `getQemuArch()` and terminates with
   `QEMU2 emulator does not support arm64 CPU architecture`. AOSP's source-controlled
   `acloud create --local-instance --local-image --avd-type goldfish` path still invokes
   that same top-level launcher, so it does not bypass the gate.
3. **Backend capability is not product support.** The bundled AArch64 QEMU binary can
   translate the guest under TCG, but the ARM ranchu path uses virtio-MMIO while generated
   devices still include PCI-dependent sound/input/serial/Wi-Fi/vsock. Replacing ranchu
   with generic `virt` only proves kernel/init reachability; the unstable zygote and absent
   boot completion show it is not a valid Goldfish runtime.
4. **Same-tree identity is ISA-independent.** A host-native x86_64 image built from this
   checkout still uses the same framework revision and platform certificate. The primary
   next candidate is therefore `sdk_phone64_x86_64 trunk_staging userdebug` through the
   standard Goldfish path. `aosp_cf_x86_64_phone` is a fallback only after all Cuttlefish
   package/group/KVM prerequisites are satisfied.
5. **The GSI remains rejected.** Existing `aosp_arm64-eng` output lacks the complete
   kernel/vendor/userdata Goldfish set and is not a standalone emulator product.

Evidence:

- `docs/issues/2026-08-23-official-aosp-arm64-emulator-launch-research.md`
- `docs/issues/2026-08-23-android-emulator-launch-source-mechanism.md`
- `docs/issues/2026-08-23-same-tree-virtual-device-product-matrix.md`

Fixed-base Standards/Spec review is complete for all three reports. Task 052B passed both
axes before merge. Revised 052A passed both axes; revised 052C cleared all
BLOCKER/HIGH/MEDIUM findings, leaving only non-causal LOW wording notes. Main fresh static
acceptance reports `TASK052A_REPORT=PASS`, `TASK052B_REPORT=PASS`, and
`TASK052C_REPORT=PASS`. No Gradle, Soong, Ninja, `m`, `lunch`, emulator launch/stop, or
device mutation was performed by Tasks 052A/B/C.

## Next runtime phase

1. Cleanly stop the still-running diagnostic `task052-arm64` QEMU guest and prove no
   Emulator/QEMU process or ADB target remains; this recovers about 3.4 GiB RSS and ports
   5556/5557.
2. Recheck memory and disk before the build. The latest read-only check showed 29 GiB free
   on `/`; the expected additional x86_64 output is about 15–17 GiB, leaving a narrow
   12–14 GiB margin. Stop if free space falls below 10 GiB; do not delete existing AOSP
   outputs without a separate evidence-backed decision. Keep the hard build limit at `-j4`
   and do not run Gradle or another Soong/Ninja build concurrently.
3. Build the primary host-native candidate with exactly:
   `lunch sdk_phone64_x86_64 trunk_staging userdebug` followed by
   `m -j4 emu_img_zip`.
4. Before launch, prove effective KVM access in the exact launcher process/session. The
   group database already contains `conv` in `kvm`, but the current long-lived shell does
   not; a fresh session or the separately proven bounded
   `sudo -n -u conv -g kvm ...` execution may be used only with an explicit access check.
5. Launch only through a first-party standard Goldfish path. Establish
   `sys.boot_completed=1`, stable `system_server`, and stable stock SystemUI before any
   frozen Gradle APK deployment.
6. Only after that baseline, deploy the frozen Debug APK and run certificate/hash,
   PackageManager hidden-API policy, fatal/ANR/watchdog, 60-second PID stability, status
   bar, Quick Settings, lock/wake/unlock, and launcher interaction gates.

## Acceptance

Environment acceptance requires all of:

- no unrelated emulator/QEMU process or ADB target exists during the selected runtime;
- target reports `ro.kernel.qemu=1`, the selected x86_64 ABI, and an AOSP same-tree
  fingerprint;
- target build is `sdk_phone64_x86_64` userdebug;
- target `framework-res.apk` certificate matches the frozen Gradle Debug APK;
- baseline `sys.boot_completed=1`, `system_server`, and stock SystemUI remain stable before
  replacement;
- after replacement, the installed APK hash equals the frozen artifact and runtime
  evidence distinguishes APK defects from image/environment defects;
- the final Debug gate requires a stable SystemUI PID for at least 60 seconds plus status
  bar, Quick Settings, lock/wake/unlock, and launcher interaction without fatal, ANR,
  watchdog, or crash loop.

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
- Tasks 052A/B/C: read-only first-party documentation/source/product review complete;
  ARM64-on-x86_64 top-level launcher rejection is deliberate, acloud local Goldfish still
  uses that launcher, and the direct `virt` probe is not a supported runtime.
- Selected next candidate: `sdk_phone64_x86_64 trunk_staging userdebug`; not yet built or
  launched. Cuttlefish x86_64 remains a prerequisite-gated fallback.
- Latest host check before closure: ARM64 diagnostic guest still running at PID 1727011
  (~3.4 GiB RSS, ports 5556/5557, ADB `emulator-5556`); `/` has 29 GiB free. It must be
  stopped and quiescence proven before another build/launch.

## Resolved research questions and remaining execution question

Resolved:

- The branch's official ARM64 Goldfish build/package path is proven, but its official
  runtime requires a compatible ARM64 host/acceleration environment; the x86_64 launcher
  rejects this host/guest pair before backend launch.
- The rejection is launcher architecture policy, not proof that the AArch64 QEMU backend
  lacks TCG translation capability.
- The PCI/MMIO mismatch explains why direct backend invocation failed, and generic
  `-machine type=virt` is not a supported Goldfish substitute.
- `sdk_phone64_x86_64` is the lowest-risk same-tree runtime on this host; Cuttlefish
  x86_64 is the fallback after host prerequisites are satisfied.

Remaining execution question: whether the host-native Goldfish product reaches a stable
same-tree baseline and, after that baseline is proven, whether the frozen Gradle Debug APK
passes the full runtime acceptance gates. No conclusion is recorded until those two phases
are actually run.
