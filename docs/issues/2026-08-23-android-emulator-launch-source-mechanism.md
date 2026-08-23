# Android Emulator ARM64 launch source mechanism

**Date:** 2026-08-23
**Task:** 052B
**Scope:** source research only; no emulator/device was launched, stopped, reset, or modified during this task
**Result:** the launcher rejection, generated `ranchu`/PCI conflict, 35.3.8-to-36.6.6 sound-device delta, and trailing `-machine type=virt` behavior are source-explained. Exact source revisions for the two released binaries remain unknown.

## Executive conclusion

Three independent layers must not be conflated:

1. **Launcher policy:** the x86-64 `emulator` launcher rejects an ARM64 guest before selecting a backend. In the inspected first-party source, the `arm64 -> aarch64` backend mapping is compiled only under `__aarch64__`; an x86-64 launcher therefore reaches `APANIC("QEMU2 emulator does not support %s CPU architecture", avdArch)`. This is the source mechanism behind the retained `QEMU2 emulator does not support arm64 CPU architecture` result. It does **not** establish that the bundled QEMU backend lacks AArch64 emulation.
2. **QEMU machine/device capability:** when the x86-64-hosted `qemu-system-aarch64-headless` backend is invoked directly, Android Emulator glue selects `-machine type=ranchu`, yet enabled image features independently add PCI-only devices. The `ranchu` board creates virtio-MMIO transports, whereas the generated argv includes PCI sound, input, serial, Wi-Fi, and vsock devices. The first incompatible PCI device reached by each retained run produces `PCI bus not available`.
3. **Acceleration availability:** `/dev/kvm` permission failure only determines whether KVM can be used. It neither causes the launcher architecture rejection nor proves that TCG cannot emulate AArch64. The retained `type=virt` run reaches the ARM64 kernel with KVM unavailable.

The official source-controlled local-image route is `acloud` invoking the top-level `emulator` launcher, not invoking the target-specific QEMU backend directly. For this ARM64 product, the inspected launcher/backend source describes the coherent first-party pairing as an AArch64-host emulator package: its launcher admits `arm64`, selects `qemu-system-aarch64`, and its backend generator chooses `type=virt`, whose board creates a GPEX PCIe host. On the present x86-64 host, direct backend invocation is a diagnostic bypass of launcher policy, not evidence of a supported launcher/guest pairing.

## Observed binaries, AVD, and argv

### Immutable first-party source snapshot

The primary Emulator/QEMU source is the AOSP mirror commit
[`ae9d18d2b6261179fbd57fffec720a04f7bfb053`](https://github.com/aosp-mirror/platform_external_qemu/commit/ae9d18d2b6261179fbd57fffec720a04f7bfb053), whose commit subject is `Bump Emulator to 35.6.3 Canary` (2025-03-27). It was inspected read-only at `/tmp/task052-external-qemu-src`; missing partial-clone blobs were read by immutable Git object ID, without hydrating or changing that checkout.

Important limitation: this snapshot is later than retained Emulator 35.3.8 and earlier than retained Emulator 36.6.6. It proves the mechanism present in a nearby first-party revision and matches the retained argv, but this task did not establish the exact release-source commit for either binary. Findings below explicitly distinguish retained behavior from source-proven mechanism.

Relevant immutable files:

- [`android/emulator/main-emulator.cpp`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android/emulator/main-emulator.cpp)
  (blob `b9aa22a54b75b72e5e876910db2b132c47e9095f`)
- [`android-qemu2-glue/main.cpp`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp)
  (blob `ce784d98404839425c58a29efd7f4d727ea66388`)
- [`hw/arm/ranchu.c`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/hw/arm/ranchu.c)
  (blob `20c9fa28aa5f479163f4a194d4ea79aa0c539bed`)
- [`hw/arm/virt.c`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/hw/arm/virt.c)
  (blob `274896c9352e72bd76dfeac2f8c2f3bf1dd7602a`)
- [`vl.c`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/vl.c)
  (blob `18e6033ec15cba0f1666882848b5d6176861a936`)
- [`util/qemu-config.c`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/util/qemu-config.c)
  (blob `20f7d1429d8f66ed3da749f608fe0696f650bcb6`)
- [`util/qemu-option.c`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/util/qemu-option.c)
  (blob `fcd3a3fcec61bb13f9d634f5ee58928dfe25f182`)

The first-party local launch/packaging sources were read from the AOSP checkout at these exact revisions:

- `platform/tools/acloud` revision `bd9f513c1db8fe0caccf2384bcdd8570a8c51029`:
  `/home/conv/myspace/aosp/tools/acloud/create/goldfish_local_image_local_instance.py`
- `device/generic/goldfish` revision `3ce87694caeb4a330280bb1284d9ad050fe28263`:
  `/home/conv/myspace/aosp/device/generic/goldfish/tasks/emu_img_zip.mk` and
  `/home/conv/myspace/aosp/device/generic/goldfish/64bitonly/product/sdk_phone64_arm64.mk`

### Retained runtime evidence

No run was performed for this report. The first two retained logs are closed
files, so their SHA-256 values cover the complete files. The third log belongs
to an append-only live diagnostic run; its whole-file length and hash can
continue changing. To make the cited startup evidence reproducible without
mutating or stopping that run, this report hashes only the raw byte stream
produced by `head -n 782 emulator-sdk36-virt.log`, ending at the last cited
startup line:

| Evidence | SHA-256 scope | Relevant lines |
|---|---|---|
| `.../logs/emulator-isolated-avd.log` | complete file: `21302020ec98b68742963342e6ae4dbbca60c97010c2d4d8444344933fd676c1` | 273-390 argv; 391 version; 393 KVM; 430 failure |
| `.../logs/emulator-sdk36.log` | complete file: `52a8503d53cfcf415e279149d7e786fe1455d05a6e62035f8b88f452f36fd27c` | 576-693 argv; 694 version; 696 KVM; 734 failure |
| `.../logs/emulator-sdk36-virt.log` | bounded prefix, lines 1-782: `f14e4f87b6980f3432c93dc11fa7090f2e0960596c0d87d171b6075c643a6926` | 575-694 argv; 695 version; 697 KVM; 777-782 kernel/machine |

The bounded prefix hash was computed twice while the file contained 26,951
lines; both reads produced the same value. Content after line 782 is excluded
from this report's evidence identity. No whole-file hash is asserted for the
live log.

All paths above are under `/home/conv/myspace/task052-aosp-arm64-runtime/`.
The retained AVD says `abi.type=arm64-v8a` and `hw.cpu.arch=arm64`
(`avd/task052-arm64.avd/config.ini:2,13`). Its image is API 35 ARM64
(`image/source.properties:5,9`). `image/advancedFeatures.ini:9,12,22-23,30`
enables `VirtioWifi`, `VirtioInput`, `VirtconsoleLogcat`, `VirtioVsockPipe`, and
`VirtioSndCard`. Audio input/output are disabled in config, but that does not
mean no emulated sound controller is generated.

The two top-level launchers and both ARM64 target backends are x86-64 host ELF
executables:

| Retained package | Top-level launcher | ARM64 target backend |
|---|---|---|
| Emulator 35.3.8.0, build 12560773 | `/home/conv/myspace/aosp/prebuilts/android-emulator/linux-x86_64/emulator` | `/home/conv/myspace/aosp/prebuilts/android-emulator/linux-x86_64/qemu/linux-x86_64/qemu-system-aarch64-headless` |
| Emulator 36.6.6.0, build 15272510 | `/home/conv/Android/Sdk/emulator/emulator` | `/home/conv/Android/Sdk/emulator/qemu/linux-x86_64/qemu-system-aarch64-headless` |

The launcher hashes were:

- AOSP prebuilt 35.3.8 launcher: `b6728c9c59eceaea49b9a6dea130353d5be394c907f1bd49bb7e188d540edeae`
- installed SDK 36.6.6 launcher: `32752e297a6763857b3bac932847bee331ffec3a31b7ffe87c3915ed5079eb63`

## Source path: invocation to final ARM64 QEMU argv

### 1. The official local-image wrapper calls the top-level launcher

`goldfish_local_image_local_instance.py:14-36` states that build-environment
launches use the prebuilt emulator from `ANDROID_EMULATOR_PREBUILTS`; outside a
build environment it accepts unpacked SDK emulator and system-image
repositories. Lines 175-203 find the top-level `emulator` binary and start it.
Lines 519-539 set `ANDROID_PRODUCT_OUT`/`ANDROID_BUILD_TOP` and construct the
launcher command with `-verbose`, `-show-kernel`, and `-read-only`.

This agrees with `tools/acloud/README.md:47-73`, which identifies
`acloud create --local-instance --local-image` as the local-instance/local-image
entry point. The product/packaging side is also explicit:

- `sdk_phone64_arm64.mk:28-38` inherits the ARM64 emulator board and names the
  product `sdk_phone64_arm64`, device `emu64a`.
- `emu_img_zip.mk:11-26,39-69` packages `kernel-ranchu`, system, ramdisk,
  vendor, userdata, feature, source-property, and verified-boot inputs into the
  emulator system-image ZIP.

**Fact:** the source-controlled wrapper invokes `emulator`, not
`qemu-system-aarch64-headless` directly.

**Interpretation:** the retained direct-backend runs bypassed a launcher policy
boundary and are suitable for diagnosis, but they are not the official launch
path demonstrated by this source.

## Launcher architecture gate

### 2. The launcher discovers the guest architecture

In [`main-emulator.cpp:944-963`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android/emulator/main-emulator.cpp#L944-L963),
the launcher gets the architecture either from the selected AVD or, in build
environment mode, from `ANDROID_PRODUCT_OUT`. Lines 986-993 supply a host-based
default only when discovery failed.

The AVD route has an additional explicit policy check at
[`main-emulator.cpp:1043-1065`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android/emulator/main-emulator.cpp#L1043-L1065):
an x86-64 build rejects an ARM64 AVD at API >= 28 with the more specific
`not supported ... on x86_64 host` panic. The retained generic panic came from
the later backend-selection gate, consistent with the earlier build-environment
attempt having an `ANDROID_PRODUCT_OUT` but no named AVD.

### 3. The x86-64 launcher has no ARM64 backend mapping

[`main-emulator.cpp:1248-1271`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android/emulator/main-emulator.cpp#L1248-L1271)
defines the Android-to-QEMU target mapping:

- only an AArch64-host build (`__aarch64__`) includes
  `{"arm64", "aarch64", "aarch64"}`;
- an x86-64-host build (`__x86_64__`) includes x86 and x86_64 mappings.

[`main-emulator.cpp:1273-1319`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android/emulator/main-emulator.cpp#L1273-L1319)
then:

1. derives the host package directory (`linux-aarch64` on AArch64, otherwise
   `linux-x86_64` for a 64-bit launcher);
2. calls `getQemuArch(avdArch, ...)`;
3. emits `QEMU2 emulator does not support %s CPU architecture` when the mapping
   is absent; and
4. otherwise forms `qemu-system-<qemuArch>[-headless]`.

Lines 1070-1098 call that selector and require the resulting executable to
exist. Lines 1107-1117 replace `argv[0]` with the selected backend and establish
its bundled-library path. Finally,
[`main-emulator.cpp:1141-1165`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android/emulator/main-emulator.cpp#L1141-L1165)
logs the forwarded backend parameters and `safe_execv()`s the backend.

**Source-proven conclusion:** the message is a compile-time host/guest policy
decision in the launcher. It occurs before the ARM64 QEMU backend is executed.
It is not a QEMU target-capability probe and not a KVM probe.

## Backend and accelerator selection

### 4. The backend turns Android configuration into QEMU argv

The target-specific backend is still a host executable. For a `TARGET_ARM64`
build, [`android-qemu2-glue/main.cpp:210-240`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp#L210-L240)
defines:

- Android architecture `arm64`;
- QEMU architecture `aarch64`;
- `cortex-a57` when the host is not AArch64;
- `virtio-blk-device` and `virtio-net-device` (MMIO transport models).

After processing AVD/image/hardware/feature inputs, lines 3514-3527 write
`hardware-qemu.ini`, print each final QEMU argument under `-verbose`, and print
the concatenated argv. That is the source of the retained `QEMU options list`.

## Machine selection

### Host-conditional machine selection

For non-x86 guests, [`main.cpp:2664-2688`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp#L2664-L2688)
selects the machine by **host build architecture**:

- AArch64 host: `-machine type=virt`, then optionally `-enable-hvf` or
  `-enable-kvm` if the separate acceleration check succeeds;
- other hosts, including this x86-64 host: `-machine type=ranchu`.

Thus guest ABI, board type, and accelerator are separate decisions. In
particular, `-accel off` or lack of `/dev/kvm` does not select `ranchu`; the host
compile branch does.

### `ranchu` supplies virtio-MMIO, not a PCI root bus

[`hw/arm/ranchu.c:435-467`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/hw/arm/ranchu.c#L435-L467)
creates a fixed set of `virtio-mmio` transports and corresponding
`virtio,mmio` device-tree nodes. Lines 525-583 initialize the board devices and
call that MMIO creation routine; lines 588-596 register the `ranchu` machine.
There is no PCI host construction in that board initialization. The retained
backend diagnostics are the direct capability result: the board reports
`PCI bus not available` when a PCI model is instantiated.

By contrast, [`hw/arm/virt.c:1056-1169`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/hw/arm/virt.c#L1056-L1169)
creates a GPEX host, maps ECAM/MMIO/PIO windows, obtains its `PCIBus`, and emits
a `pci-host-ecam-generic` DT node. Lines 1499-1502 invoke `create_pcie()` during
`virt` board initialization. This is why the same PCI argv can be instantiated
under effective `type=virt` but not under `type=ranchu`.

## Virtio transport/device selection

### Feature-driven branches still add PCI models

Machine selection does not constrain all later device selection:

- [`main.cpp:827-862`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp#L827-L862):
  enabled `VirtioInput` adds PCI mouse/tablet/multitouch models and
  `virtio-keyboard-pci`.
- [`main.cpp:2898-2925`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp#L2898-L2925):
  the virtconsole path adds `virtio-serial-pci`.
- [`main.cpp:3052-3121`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp#L3052-L3121):
  input is initialized, `VirtioWifi` adds `virtio-wifi-pci`, and
  `VirtioVsockPipe` adds `virtio-vsock-pci`.
- [`main.cpp:1394-1425`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/main.cpp#L1394-L1425):
  `VirtioSndCard` selects `virtio-snd-pci`; otherwise API >= 26 (or x86)
  selects `hda`. Disabling audio input/output merely appends
  `input=off,output=off`; it does not omit the controller.

The retained image enables these Virtio features. Therefore the observed argv
is a generator inconsistency on this host path: ARM64 target defaults produce
MMIO storage/network, while independent enabled-feature branches produce PCI
serial/input/Wi-Fi/vsock/sound devices for a `ranchu` board without a PCI bus.

## Why the observed command fails

### Retained 35.3.8 versus 36.6.6 argv

The relevant retained argv is nearly identical through machine, storage,
network, serial, input, Wi-Fi, and vsock construction:

| Concern | Emulator 35.3.8 (`emulator-isolated-avd.log`) | Emulator 36.6.6 (`emulator-sdk36.log`) |
|---|---|---|
| Backend | x86-64 `qemu-system-aarch64-headless` | x86-64 `qemu-system-aarch64-headless` |
| CPU/machine | `-cpu cortex-a57 -machine type=ranchu` | same |
| ARM storage/network | `virtio-blk-device`, `virtio-net-device` | same |
| PCI devices | serial, 11 multitouch devices, keyboard, Wi-Fi, vsock | same |
| Sound | `-soundhw hda:input=off,output=off` | `-soundhw virtio-snd-pci:input=off,output=off` |
| First terminal error | `PCI bus not available for hda` | `PCI bus not available for virtio-snd-pci` |

Retained evidence locations:

- 35.3.8: argv at lines 273-390, version/build `35.3.8.0 (12560773)`
  at line 391, and failure at line 430.
- 36.6.6: argv at lines 576-693, version/build `36.6.6.0 (15272510)`
  at line 694, and failure at line 734.

**Fact:** the immediate visible delta is HDA to virtio-snd PCI; both are invalid
on the selected `ranchu` board, so both terminate at sound-device creation.
Other PCI devices occur earlier in the displayed argv, but QEMU's realization
order must not be inferred solely from textual argv order.

**Source-supported interpretation:** the current source's
`buildSoundhwParam()` exactly describes the 36.6.6 choice when
`VirtioSndCard=on`, and its fallback describes the 35.3.8 HDA value for API 35
when that feature is ineffective/off.

**Unknown:** without the exact 35.3.8 and 36.6.6 source tags/config snapshots,
this report cannot say whether the sound delta came from feature availability,
feature-default evolution, parser behavior, or a source change. It also cannot
prove that every generator branch shown above is byte-for-byte identical in
both released binaries.

## Effect of a trailing duplicate `-machine type=virt`

The retained 36.6.6 override argv contains both:

```text
argv[14]  = "-machine"
argv[15]  = "type=ranchu"
...
argv[112] = "-machine"
argv[113] = "type=virt"
```

This is not ambiguous in the inspected QEMU option implementation:

1. [`util/qemu-config.c:153-161`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/util/qemu-config.c#L153-L161)
   declares the `machine` option list with `merge_lists = true` and `type` as a
   string option.
2. [`vl.c:4190-4197`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/vl.c#L4190-L4197)
   parses every `-M`/`-machine` occurrence into that list.
3. [`util/qemu-option.c:609-643`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/util/qemu-option.c#L609-L643)
   returns the existing anonymous option object when a list merges; lines
   818-852 parse the new text into that object.
4. [`util/qemu-option.c:493-528`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/util/qemu-option.c#L493-L528)
   appends ordinary parsed values to the option tail. Lines 230-240 search that
   tail in reverse, so lookup returns the last same-named value; lines 264-280
   show `qemu_opt_get()` using that reverse lookup.
5. [`vl.c:3033-3048`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/vl.c#L3033-L3048)
   selects the machine from `qemu_opt_get(opts, "type")`.

**Conclusion:** in this source, the trailing `type=virt` is the effective
machine type. It does not erase the earlier token from the printed argv; both
values are retained in the merged option structure, but reverse lookup makes
the last `type` win for machine selection.

The live diagnostic run's bounded startup prefix corroborates this source path
rather than merely suppressing an error: it gets past the prior
`virtio-snd-pci` PCI-bus failure and starts the ARM64 kernel
(`emulator-sdk36-virt.log:688-697,777-782`). This does not prove a healthy
Android userspace; later output from that append-only run is outside the bounded
evidence used here and outside this mechanism report.

### Why the kernel still prints `Machine model: linux,ranchu`

That string does **not** mean the first `type=ranchu` won. The selected `virt`
board itself writes the root device-tree compatible string
`linux,ranchu` in
[`hw/arm/virt.c:230-244`](https://github.com/aosp-mirror/platform_external_qemu/blob/ae9d18d2b6261179fbd57fffec720a04f7bfb053/hw/arm/virt.c#L230-L244).
Linux prints that DT identity as its machine model. Machine-class selection and
guest-visible DT compatibility naming are different concepts.

## Evidence table and first-party sources

The classifications below are tied to the immutable first-party source links
and retained evidence hashes listed above.

### Classification matrix

| Statement | Classification | Basis |
|---|---|---|
| The retained image is API 35 ARM64 (`arm64-v8a`). | Observed fact | AVD/image property files |
| Both retained backends are x86-64 host executables targeting AArch64 guests. | Observed fact | ELF inspection and argv[0] |
| The generic ARM64 rejection occurs in the launcher before backend exec. | Source-proven fact | `main-emulator.cpp:1248-1319`, `1141-1165` |
| The rejection proves QEMU cannot emulate AArch64. | False inference | The target backend exists and the retained `virt` run starts ARM64 Linux |
| x86-64-host ARM target generation chooses `ranchu`; AArch64-host generation chooses `virt`. | Source-proven fact | `main.cpp:2664-2688` |
| `ranchu` has virtio-MMIO transports and cannot host the requested PCI devices. | Source plus observed capability | `ranchu.c:435-467,525-596`; exact backend errors |
| Enabled features add PCI devices without being gated on the selected machine. | Source-proven fact | input/serial/Wi-Fi/vsock/sound branches cited above |
| KVM unavailability caused the launcher panic. | False inference | launcher gate precedes backend acceleration handling |
| The trailing `type=virt` is effective. | Source-proven and observed | merged-option/reverse-lookup chain; kernel starts |
| `Machine model: linux,ranchu` means QEMU selected the `ranchu` class. | False inference | `virt.c:230-244` emits that exact DT compatible string |
| 36.6.6 changed sound because of one identified upstream commit. | Unknown | exact release source mapping was not established |
| Direct x86-64-host ARM64 backend execution is an officially supported launcher path. | Not established; treat as diagnostic bypass | official wrapper invokes launcher; launcher rejects this pairing |

## Source-proven next probe (not executed)

Use the already packaged `sdk_phone64_arm64` image with a matching **Linux
AArch64 Emulator package on an AArch64 host**, through the first-party
`acloud create --local-instance --local-image` path. Do not append a manual
`-qemu -machine ...` override and do not deploy the Gradle APK during this probe.

Expected, source-predicted argv delta from the retained x86-64-host run:

```text
backend package: qemu/linux-x86_64/qemu-system-aarch64[-headless]
              -> qemu/linux-aarch64/qemu-system-aarch64[-headless]

machine:         -machine type=ranchu
              -> -machine type=virt
```

The PCI feature devices should remain, while the `virt` board supplies their
GPEX PCIe host. `-enable-kvm` is expected only if the independent AArch64-host
acceleration check succeeds; KVM availability is not an acceptance condition
for validating the launcher/machine decision.

**Stop condition:** capture the verbose `QEMU options list` and stop the probe
as soon as it shows the AArch64 backend path and a single generated
`-machine type=virt`, plus either (a) the first kernel line with no preceding
`PCI bus not available` error or (b) the first backend error. Do not continue
into ADB, SystemUI replacement, or general userspace diagnosis in that probe.

This is narrower than further x86-64 direct-backend flag experiments: it tests
the exact host branch and official launcher path identified by source, while
changing only the host/package side of the machine-selection decision.

## Open unknowns

1. Exact external/qemu source commits used to build Emulator 35.3.8 build
   12560773 and Emulator 36.6.6 build 15272510 were not mapped.
2. Consequently, the exact commit/default responsible for the HDA to
   virtio-snd transition is not assigned here.
3. The source documents the intended AArch64-host branch, but no Linux AArch64
   emulator package or AArch64 host was inspected or run in this task.
4. The bounded `type=virt` startup prefix demonstrates machine/device
   compatibility and kernel entry, not Android boot health; later output from
   the still-live append-only run requires a separate investigation.
5. Direct backend help returned `unknown option: -machine`; the Android backend
   has a launcher/glue option layer rather than stock-QEMU help behavior. This
   does not override the retained final argv or the parser source above.

## Commands and mutation statement

Research used only read-only file inspection, Git object/API reads, ELF/version
queries, and source searches. No emulator, QEMU guest, ADB command, AVD
operation, build, package mutation, SDK/AOSP/image patch, Gradle, Soong, Ninja,
`m`, or `lunch` was run. The only repository write is this report.

Build/error evolution: **not applicable; no build was run.** The retained
failures remained 35.3.8 `PCI bus not available for hda`, 36.6.6
`PCI bus not available for virtio-snd-pci`, while the already-retained trailing
`-machine type=virt` run passed that initialization boundary and reached the
kernel. No new runtime evidence was created.
