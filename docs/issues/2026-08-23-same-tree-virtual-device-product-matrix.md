# Same-tree virtual-device product and launch matrix

> Date: 2026-08-23
> Task: 052C (research-only; no build, launch, ADB, or AVD/SDK/AOSP mutation performed)
> Status: report complete from local first-party evidence; live web corroboration blocked (host network unreachable)

## Checkout and host facts

All facts below were measured read-only on this host during this task, or taken
from retained Task 052 evidence (`docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md`).

| Fact | Value | Evidence |
|---|---|---|
| Host CPU / ISA | AMD Ryzen 5 7500F, x86_64, 12 threads, `svm` virtualization flags present | `lscpu`, `grep -cE "(vmx|svm)" /proc/cpuinfo` → 12 |
| KVM | available: `kvm_amd` module loaded, `/dev/kvm` exists (root:kvm, mode 660) | `lsmod`, `ls -la /dev/kvm` |
| vhost-vsock | available: `/dev/vhost-vsock` exists (Cuttlefish prerequisite) | `ls /dev/vhost-vsock` |
| RAM | 30 GiB total, ~21 GiB available | `free -h` |
| Disk free | **36 GiB measured** (brief stated 37–39 GiB; `df -h /` → 36G avail, 96% used) | `df -h` |
| Existing AOSP outputs | `out/target/product/emu64a` ≈ 17 GiB; `out/target/product/generic_arm64` ≈ 14 GiB | `du -sh` |
| Installed emulator | SDK Emulator **36.6.6** (build 15272510) at `/home/conv/Android/Sdk/emulator/` | `emulator -version` |
| Installed system images | only `android-37.0/google_apis/x86_64` (Google APIs, rev 6) — NOT same-tree | `system-images/.../source.properties` |
| Existing AVD | `sysui-gradle-task049-debug-20260822-120226` (Google API x86_64, stopped) | `~/.android/avd/` |
| Network | outbound HTTPS to developer.android.com / google.com **unreachable** (connect timeouts) | `curl` probes this session |
| Same-tree platform key | frozen Gradle Debug APK cert SHA-256 `c8a2e9bc...192ab8` matches this checkout's `platform.x509.pem` | Task 052 evidence |

**Key conceptual separation (required by brief):** "same-tree identity" means the
system image's framework source revision, SystemUI source, and platform signing key
all come from this AOSP checkout. That identity is **independent of guest ISA**.
`sdk_phone64_x86_64`, `sdk_phone64_arm64`, and `aosp_cf_x86_64_phone` built from
this tree all carry the same framework/source/platform-key identity; they differ
only in guest ABI and host launch mechanism. The Google API x86_64 image currently
installed does NOT have same-tree identity (Task 051/052 proved the signature mismatch).

## Product inventory

Source: `device/generic/goldfish/AndroidProducts.mk`, `device/google/cuttlefish/AndroidProducts.mk`,
product makefiles and board configs — read directly, no `lunch` run.

| Product | Lunch target | PRODUCT_DEVICE | Guest arch | Listed | Buildable here | Artifacts built | Runtime proven |
|---|---|---|---|---|---|---|---|
| `sdk_phone64_x86_64` | `sdk_phone64_x86_64 trunk_staging userdebug` | `emu64x` | x86_64 | yes (goldfish AndroidProducts.mk) | yes (board config + 6.6 kernel prebuilt present) | **no** (no `out/target/product/emu64x`) | no |
| `sdk_phone64_arm64` | `sdk_phone64_arm64 trunk_staging userdebug` | `emu64a` | arm64 | yes | yes | **yes** — full goldfish set, 17 GiB | **no** — launcher rejects; direct-QEMU probe not boot-complete |
| `aosp_arm64` | `aosp_arm64 trunk_staging eng` (built as `aosp_arm64-eng`) | `generic_arm64` | arm64 | yes | yes | yes — GSI images only, 14 GiB | no — not a launchable emulator image |
| `aosp_cf_x86_64_phone` | `aosp_cf_x86_64_phone trunk_staging userdebug` (in COMMON_LUNCH_CHOICES) | `vsoc_x86_64` | x86_64 | yes | yes (source present) | **no** | no |
| `aosp_cf_arm64_phone` | in cuttlefish AndroidProducts.mk (not in COMMON_LUNCH_CHOICES) | `vsoc_arm64` | arm64 | yes | yes (source present) | no | no |
| Other goldfish products | `sdk_phone64_x86_64_minigbm`, `sdk_phone16k_*`, `sdk_tablet_*`, `sdk_slim_*`, `sdk_phone64_*_riscv64`, `fvp` | various | x86_64/arm64/riscv64 | yes | mostly yes | no | no |

First-party detail confirming `sdk_phone64_x86_64`:

- `device/generic/goldfish/64bitonly/product/sdk_phone64_x86_64.mk`:
  `PRODUCT_NAME := sdk_phone64_x86_64`, `PRODUCT_DEVICE := emu64x`,
  `PRODUCT_MODEL := Android SDK built for x86_64`.
- `device/generic/goldfish/board/emu64x/BoardConfig.mk` lines 17–20:
  `TARGET_CPU_ABI := x86_64`, `TARGET_ARCH := x86_64` (no 2nd arch → x86_64-only).
- `board/emu64x/details.mk` includes `board/kernel/x86_64.mk` → prebuilt kernel
  `prebuilts/qemu-kernel/x86_64/6.6/kernel-6.6` **present locally** (verified).
- `board/emu64x/README.txt` (first-party): "The emu64x product ... will work with
  the IA version of the emulator" — i.e. this product is explicitly designed for
  the standard x86_64 Android Emulator.

The four status columns above are deliberately NOT collapsed: "listed" (in
AndroidProducts.mk), "buildable" (inputs present, but no build run this task),
"artifacts built" (files exist under `out/target/product/`), and "runtime proven"
(successfully booted and used) are distinct states.

## Artifact and launcher mapping

### Goldfish path (`emu_img_zip`)

`device/generic/goldfish/tasks/emu_img_zip.mk` (read in full) defines the official
same-tree emulator artifact for any `sdk_*` product: target `emu_img_zip` produces
`$(PRODUCT_OUT)/sdk-repo-linux-system-images.zip` containing, per ABI directory:

- `kernel-ranchu` (from `prebuilts/qemu-kernel/<arch>/6.6/`)
- `system-qemu.img` (as `system.img`), `ramdisk-qemu.img`, `vendor-qemu.img`
- `userdata.img`, `build.prop`, `source.properties` (from
  `PRODUCT_SDK_ADDON_SYS_IMG_SOURCE_PROP` template), `VerifiedBootParams.textproto`,
  `advancedFeatures.ini`, `kernel_cmdline.txt`, `encryptionkey.img`

This ZIP is the standard SDK **system-image** distribution layout: the official
host launch path is install-into-SDK → create AVD → `emulator` (36.6.6 installed),
which uses **KVM** hardware acceleration for an x86_64 guest on this x86_64 host.

Verified existing `emu64a` output (17 GiB total): `kernel-ranchu` (14.5 MB),
`system-qemu.img` (1.9 GB), `ramdisk-qemu.img` (2.1 MB), `vendor-qemu.img`
(99.6 MB), `userdata.img` (576 MB), `sdk-repo-linux-system-images.zip` (793 MB),
plus raw `system.img`/`super.img`/`vbmeta.img`/etc. and 3.0 GiB `obj/`.

Verified existing `generic_arm64` output (14 GiB): only `system.img`,
`ramdisk.img`, `vbmeta.img`, `pvmfw.img` — **no** `kernel-ranchu`, no `-qemu`
images, no `vendor.img`/`userdata.img`. It is a GSI, not a complete goldfish
emulator image; both launch attempts against it already failed authoritatively
(Task 052: launcher PANIC; direct QEMU exit 1, missing `kernel-ranchu`).

### Cuttlefish path

`device/google/cuttlefish` is fully present. Official prerequisites from its
`README.md` (first-party, read in full): KVM required (present here), plus host
debian packages `cuttlefish-base`/`cuttlefish-user` built from
https://github.com/google/android-cuttlefish and installed, `vhost_vsock` kernel
module (present here), user in `kvm,cvdnetwork,render` groups, and a reboot.
Launch is via `launch_cvd` from a `cvd-host_package` matched to the image build.
Current host status: **no cvd binary, no cuttlefish debian packages installed**
(`which cvd` empty); KVM and `/dev/vhost-vsock` prerequisites are satisfied.
Same-tree Cuttlefish requires building `aosp_cf_x86_64_phone` plus the host
package — both absent today.

### Standard AOSP launcher rejection (ARM64 guest on x86_64 host)

Task 052 evidence (retained, first-party observation from this checkout): the
AOSP `emulator` entrypoint exited 1 with
`PANIC: QEMU2 emulator does not support arm64 CPU architecture` for the ARM64
guest on this x86_64 host — regardless of the image being a complete goldfish
set. A direct `qemu-system-aarch64` invocation with `-machine type=virt` reached
`/init` and ADB (identity: `ro.kernel.qemu=1`, `arm64-v8a`, userdebug, local
`sdk_phone64_arm64/emu64a` fingerprint) but `sys.boot_completed` stayed empty and
zygote/system_server were unstable — a diagnostic probe, not a working runtime.

## Host/guest/acceleration matrix

| Option | Guest ISA | Build feasibility (this checkout) | Official launch path | Acceleration needed | Disk estimate | Current-host suitability |
|---|---|---|---|---|---|---|
| `sdk_phone64_x86_64` (emu64x) | x86_64 (host-native) | High — product + board config + 6.6 x86_64 kernel prebuilt all present; `emu_img_zip` target applies | SDK system-image ZIP → AVD → installed Emulator 36.6.6 | KVM (**available**) | ~15–17 GiB (emu64a analog: 17 GiB incl. 3 GiB obj + 0.8 GiB ZIP); fits in 36 GiB free | **Best** — no cross-arch issue, official launcher, same-tree identity retained |
| `aosp_cf_x86_64_phone` Cuttlefish | x86_64 (host-native) | High — source + lunch choice present | `launch_cvd` (host package + debian install + group setup) | KVM + vhost-vsock (**both available**) | guest build ~15 GiB+ plus host package; fits but tighter | Good secondary — KVM present, but host packages absent (extra privileged setup + reboot) |
| `sdk_phone64_arm64` (emu64a) | arm64 (cross-arch on x86_64 host) | **Already built** (17 GiB, complete set, ZIP passes `unzip -t`) | Standard launcher **rejects arm64 guest on x86_64 host**; no official software-emulation launch path proven | TCG-only (slow, unproven to boot-complete here) | 0 additional (built) | **Not suitable now** — runtime not proven; only diagnostic direct-QEMU reached ADB without boot completion |
| `aosp_arm64` (generic_arm64) | arm64 | Built, but GSI-only | None — no kernel-ranchu/-qemu images; both launch attempts failed authoritatively | n/a | 0 additional (built, 14 GiB) | **Rejected** — not a full device image; could only serve via GSI-on-other-device flows outside this task |
| `sdk_phone64_arm64` minigbm / 16k / riscv64 / tablet / slim / fvp | various | listed; not built | varies | varies | unknown (not estimated) | Out of scope — no advantage over ranked options |
| Installed Google API x86_64 image | x86_64 | n/a (prebuilt) | AVD + emulator | KVM | 0 | **Rejected for validation** — platform key / source revision mismatch (Task 051/052) |

## Secondary corroboration

Honest status: this host's outbound network is **unreachable** (curl to
developer.android.com and google.com timed out; IPv6 "Network is unreachable",
IPv4 connect timeout). No live third-party report could be fetched this session.
Per the brief, third-party reports are corroboration only, never authoritative;
here even the corroboration layer could not be refreshed, so the ranking rests on
**local first-party evidence only**, and the unknowns are preserved as unknowns:

1. Corroborating-but-local observation A: AOSP `emulator` launcher PANIC
   `QEMU2 emulator does not support arm64 CPU architecture` (Task 052, this
   checkout + installed SDK Emulator 36.6.6). Consistent with the official
   Android Studio documentation position that ARM64 system images are intended
   for ARM64 hosts (https://developer.android.com/studio/run/emulator — not
   fetchable this session; retained as pointer, not as verified claim).
2. Corroborating-but-local observation B: direct `qemu-system-aarch64` with
   `-machine type=virt` boots the local ARM64 kernel to `/init` and ADB under
   software emulation but not to `sys.boot_completed` — matches the widely
   reported community experience that ARM64-on-x86_64 Android emulation is
   possible at the QEMU/TCG layer but not a supported Android Emulator launch
   path (e.g. https://source.android.com/docs/setup/create/avd and
   https://developer.android.com/studio/run/emulator-requirements — pointers
   only, unverified this session).
3. Official (first-party, locally present) Cuttlefish documentation confirms
   KVM + vhost-vsock + debian host packages as prerequisites:
   `device/google/cuttlefish/README.md`, which itself points to
   https://github.com/google/android-cuttlefish (unfetched this session).

Open question preserved: whether any current emulator build accepts an arm64
guest on x86_64 via a documented TCG path — **unproven** here and explicitly
NOT relied upon by the ranking below, which prefers a host-native x86_64 guest.

## Ranked same-tree runtime options

Identity axes held constant: all top options are built from this AOSP checkout,
so framework source revision, SystemUI source, and platform key
(`platform.x509.pem`, matching the frozen Gradle Debug APK cert SHA-256
`c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`) are
same-tree regardless of guest ISA. The ranking is therefore driven by launch
mechanism, acceleration, disk headroom, and proven-ness.

**Rank 1 — PRIMARY: `sdk_phone64_x86_64` Goldfish (emu64x), userdebug, `emu_img_zip`.**
Host-native guest removes the entire cross-architecture class of failures
(launcher PANIC, PCI/ranchu machine mismatch, TCG slowness). Official launch
path fully exists locally: `emu_img_zip` produces the SDK system-image ZIP;
Emulator 36.6.6 + KVM installed. First-party README states emu64x "will work
with the IA version of the emulator". Kernel prebuilt present. Cost: one
`-j4` incremental build (~1.5 h per emu64a precedent) and ~15–17 GiB disk,
leaving ~19–21 GiB free — acceptable. Same-tree identity fully retained.

**Rank 2 — FALLBACK: `aosp_cf_x86_64_phone` Cuttlefish (vsoc_x86_64).**
Also host-native x86_64 with KVM, and Cuttlefish is an officially supported
virtual device with a source-controlled host runner in this checkout. KVM and
vhost-vsock are present. Falls behind Goldfish because: host debian packages
(cuttlefish-base/user) are not installed (requires sudo, usermod, reboot),
no cvd host package exists yet, and the disk cost is guest build + host
package on top of the existing 31 GiB of outputs.

**Rank 3 — BUILT-BUT-UNPROVEN: `sdk_phone64_arm64` (emu64a).**
Complete same-tree goldfish image set already built (17 GiB, zero additional
build cost) — its value is real. But the standard launcher categorically
rejects an arm64 guest on this x86_64 host, and the only workaround tried
(direct QEMU + `-machine type=virt`) did not reach boot completion. Keep the
artifacts; do not spend further runtime effort until/unless an official
arm64-on-x86_64 launch path is proven.

**Rank 4 — REJECTED: `aosp_arm64` (generic_arm64) GSI.**
Not a full device image (no kernel-ranchu/-qemu/vendor/userdata); both launch
attempts failed authoritatively. Not a same-tree SystemUI runtime environment.

**REJECTED: installed Google API x86_64 image.** Boots fine but fails the whole
point of same-tree validation (platform signature and source revision mismatch).

## Recommended next command and stop conditions

First-party evidence supports exactly one next command — building the rank-1
candidate (this task itself ran nothing; the command is a recommendation for the
architect/user, subject to the standing user constraints: `-j4` max, waits
bounded ≤90 s, mutations confined to `out/`):

```bash
cd /home/conv/myspace/aosp
lunch sdk_phone64_x86_64 trunk_staging userdebug
m -j4 emu_img_zip
```

Expected product output: `out/target/product/emu64x/` with `kernel-ranchu`,
`system-qemu.img`, `ramdisk-qemu.img`, `vendor-qemu.img`, `userdata.img`, and
`sdk-repo-linux-system-images.zip` (mirroring the verified emu64a layout).

What must be proven before any launch command is issued (no first-party
evidence yet for these steps on this host):

1. Disk headroom stays ≥ ~10 GiB free after the build (36 GiB now; ~15–17 GiB
   expected consumed). If free space would drop below 10 GiB, STOP and ask
   whether to retire existing outputs first.
2. The ZIP passes `unzip -t` and `source.properties` is present, before any
   SDK system-image install or AVD creation (both are mutations forbidden to
   this task and requiring fresh authorization).
3. The emulator 36.6.6 accepts the locally built x86_64 image via the standard
   launcher with KVM (first launch identity check: `ro.kernel.qemu=1`, x86_64
   ABI, userdebug, `sdk_phone64_x86_64/emu64x` fingerprint, platform
   certificate matching the frozen APK SHA-256 above).

Stop conditions: kernel-confirmed OOM (precedent: first emu64a attempt), free
disk < 10 GiB, `emu_img_zip` failing on missing inputs, or the launcher
rejecting the image — in each case halt and report rather than improvise
overrides (the `-machine type=virt` lesson: diagnostic probes are not launch
solutions).

## Sources

First-party (local, read this task unless noted):

- `device/generic/goldfish/AndroidProducts.mk` — full goldfish product list
- `device/generic/goldfish/64bitonly/product/sdk_phone64_x86_64.mk` and
  `.../sdk_phone64_arm64.mk` — PRODUCT_DEVICE/model, board inheritance
- `device/generic/goldfish/board/emu64x/BoardConfig.mk` (TARGET_ARCH x86_64),
  `board/emu64a/BoardConfig.mk` (TARGET_ARCH arm64), `board/emu64x/README.txt`
- `device/generic/goldfish/board/kernel/x86_64.mk`; `prebuilts/qemu-kernel/x86_64/6.6/kernel-6.6` (present)
- `device/generic/goldfish/tasks/emu_img_zip.mk` — official artifact/ZIP definition
- `device/google/cuttlefish/AndroidProducts.mk`, `vsoc_x86_64/phone/aosp_cf.mk`, `README.md`
- `out/target/product/emu64a/` and `out/target/product/generic_arm64/` inventories (`ls`, `du`, file sizes)
- Host probes: `lscpu`, `lsmod`, `/dev/kvm`, `/dev/vhost-vsock`, `df -h`, `free -h`, `emulator -version`, `~/.android/avd/`
- `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md` — Task 052 retained evidence (launcher PANIC, direct-QEMU probe, emu64a build result, platform cert match)

Official documentation pointers (NOT fetched this session — network unreachable;
listed for architect follow-up, claims above do not depend on them):

- https://developer.android.com/studio/run/emulator — emulator system images & host/guest ABI guidance
- https://developer.android.com/studio/run/emulator-requirements — acceleration requirements (KVM on Linux)
- https://source.android.com/docs/setup/create/avd — AOSP virtual device setup
- https://github.com/google/android-cuttlefish — Cuttlefish host tools and debian packages (cited by local README)

## Build/error evolution

- Gradle: NOT RUN (research-only task).
- AOSP build/launch/ADB/AVD/SDK mutation: NOT RUN, per brief.
- Live web research: attempted, failed (host network unreachable); unknowns preserved as unknowns.
