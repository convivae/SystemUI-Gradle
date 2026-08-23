# Same-tree AOSP ARM64 emulator runtime plan

> Approved direction: use a same-checkout ARM64 userdebug emulator image instead of
> the mismatched Google API x86_64 image.

## Phase 1 — Existing-output proof

- [x] Capture the running Google AVD identity and stop it without deleting its AVD/image.
- [x] Verify zero connected emulator devices and zero emulator/QEMU processes.
- [x] Set `ANDROID_PRODUCT_OUT` to the existing `generic_arm64` output and invoke the
      AOSP emulator entrypoint with bounded startup observation.
- [x] Record whether it boots or which mandatory emulator artifacts are missing.

Result: the standard launcher rejects ARM64 guests on the x86_64 host; direct
ARM64 QEMU reaches image validation but exits because the GSI has no
`kernel-ranchu`. No guest boot occurred.

## Phase 2 — Exact product selection

- [x] Identify this branch's exact ARM64 goldfish phone product and release-config syntax.
- [x] Select `userdebug`, as explicitly requested by the user.
- [x] Compare required output set against the existing `aosp_arm64-eng` GSI output.
- [x] Obtain explicit approval at the heavy-build boundary. The user imposed a hard
      maximum of four jobs on this 32 GiB host.
- [x] Build `emu_img_zip` for `sdk_phone64_arm64 trunk_staging userdebug` with exactly
      `m -j4 emu_img_zip`, without erasing `generic_arm64` or running another build.
      Attempt 1 was a kernel-confirmed OOM under unrelated tmpfs pressure; after
      bounded removal of two byte-proven duplicate temporary images, attempt 2
      succeeded in `01:29:20` with exit `0` and produced the complete image set.

## Phase 2.5 — Official launch research

- [ ] Task 052A: cite official documentation for build, package, AVD and launch commands,
      including the documented host/guest architecture and acceleration constraints.
- [ ] Task 052B: trace the emulator launcher and QEMU source from architecture rejection
      through machine and virtio device selection; explain the observed ranchu/PCI mismatch.
- [ ] Task 052C: enumerate this checkout's launchable virtual-device products and rank
      same-tree runtime options using official source plus independently corroborating evidence.
- [ ] Architect cross-check all three reports against the installed binaries and local source,
      then select one official or source-proven launch path before changing runtime flags again.

## Phase 3 — Baseline emulator gate

- [ ] Start the same-tree ARM64 emulator with no snapshot contamination.
- [ ] Verify `ro.kernel.qemu=1`, ARM64 ABI, build type, fingerprint and boot completion.
- [ ] Verify platform/framework certificate equals the Gradle APK certificate.
- [ ] Verify baseline SystemUI PID and fatal-free stability before replacement.

## Phase 4 — Gradle APK runtime gate

- [ ] Freeze and hash the selected Gradle Debug APK.
- [ ] Deploy through the least invasive same-key system-app update path available on
      userdebug; record exact PackageManager behavior.
- [ ] Verify installed bytes, application/factory manifest-to-DEX closure, package flags,
      `usesNonSdkApi`, hidden-API policy and signature domain.
- [ ] Reboot and capture the first real fatal, if any.
- [ ] If SystemUI starts, verify PID stability for at least 60 seconds plus status bar,
      Quick Settings, lock/wake/unlock and launcher interaction.

## Stop conditions

- Any non-emulator or unknown target appears.
- Existing output proves to be GSI-only and a new AOSP product build would be required:
  record exact evidence and scope before launching the heavy build.
- A product source/config modification is required rather than a standard lunch/build.
- Runtime failure lacks enough evidence to classify one next hypothesis.
