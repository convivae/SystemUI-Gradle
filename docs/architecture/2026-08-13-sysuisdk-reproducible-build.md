# SysUISdk Reproducible Build Pipeline (2026-08-13)

> Architecture spec + audit record for the reproducible SysUISdk build pipeline.
> Worker brief: `docs/orchestration/tasks/010-sysuisdk-reproducible-pipeline.md`.
> Day log: `docs/issues/2026-08-13-sysuisdk-reproducible-build.md`.
> Authority: redline-gated (staging-only; user pre-approval 2026-08-13).

## 1. Goal

Make the SysUISdk platform **reproducible from scratch** — a single Python
orchestrator (`tools/build_sysuisdk.py`) rebuilds the SDK into a **staging**
directory from tracked artifacts and verifies inventory-level equivalence with
the live SDK. The live SDK (`~/Android/Sdk/platforms/android-SysUISdk`) is never
written to, renamed, or deleted; the orchestrator hard-fails if `--target`
resolves to it.

User requirement (2026-08-13): *"SysUISDK 的构建必须是可以复现的……即使删除了你
还是能构建出来"*. The pipeline + docs are the deliverable; the staging diff is
the proof.

This brief covers stages S0–S3 + S5 (reproduce the CURRENT live SDK exactly).
The framework-res stage (S4, `androidprv:` private resource IDs) lands in the
next brief — do not add it here.

## 2. Audit findings

### 2.1 Base platform

`~/Android/Sdk/platforms/android-37.0/` is the true pristine base. Verified
byte-for-byte (entry names + CRC) against the live SDK's pristine backups:

| file | base (`android-37.0`) | live pristine backup | result |
|------|----------------------|----------------------|--------|
| `android.jar` | 15152 entries | `android.jar.orig` (15152) | identical (0 CRC diffs) |
| `core-for-system-modules.jar` | 1894 entries | `core-for-system-modules.jar.orig` (1894) | identical |
| `framework.aidl` | 135915 B | `framework.aidl.bak-preaidl` | identical (`diff` clean) |
| `build.prop` | 4360 B | live `build.prop` | identical |
| `data/`, `optional/` | — | live | identical file sets |
| `package.xml` | — | live | differs (S0 rewrites 4 fields) |
| `source.properties` | — | live | differs (mirrors package.xml fields) |
| `sdk.properties` | — | live | identical |

(`android-37.0` carries its own leftover `android.jar.orig`; S0 skips all
`*.orig` / `*.bak-preaidl` files so each stage creates its own backup of the
freshly-copied base, matching the live SDK's backup pattern.)

### 2.2 S2 — `framework.aidl` (scripted, reproducible)

`install_sdk.py` appends exactly two declarations:

```
interface android.os.IRemoteCallback;
parcelable com.android.internal.util.ScreenshotRequest;
```

Source of truth: `tools/install_sdk.py` (`HIDDEN_IFACES`, `HIDDEN_PARCELABLES`).

### 2.3 S3 — dalvik annotations (scripted, reproducible)

`patch_sdk_dalvik_annotations.py` injects 4 classes (from AOSP `core-libart.jar`)
into both `android.jar` and `core-for-system-modules.jar`:

```
dalvik/annotation/optimization/{NeverCompile,NeverInline,DeadReferenceSafe,ReachabilitySensitive}.class
```

`core-for-system-modules.jar`: 1785 → 1789 entries (+4, 0 overwritten, all
CRC-match `core-libart.jar`). `CriticalNative`/`FastNative` were already in the
base.

### 2.4 S1 — `framework.jar` merge (PARTIALLY reproducible — GAP)

The 2026-07-22 manual merge (`docs/issues/2026-07-22-sdk-android-jar-merge.md`)
used the semantics: **framework.jar is master; android.jar fills the gaps**
(`merged = framework_all ∪ android_only`, framework bytes win the intersection,
repackaged with `jar cf`). `libs/framework.jar` is byte-identical to AOSP
`frameworks/base/framework/android_common/turbine-combined/framework.jar`
(25918 entries — core framework, **no** apex modules).

Audit arithmetic on the live `android.jar`:

```
live entries  = 37524
orig entries  = 14826
ADDED         = 22698    (in live, not in orig)
OVERWRITTEN   = 4441     (same name, diff CRC)
REMOVED       = 0

framework.jar ∪ orig = 25918 + 14826 − 4490(intersection) = 36254
live                 = 36254 + 1270(orphaned) − 4(S3 dalvik in the 1270)
                     = 36254 + 1266(truly orphaned) + 4(S3-reproducible) + MANIFEST.MF
                     = 37524
```

Of the 1270 ADDED entries absent from `libs/framework.jar`, **1266 have no
tracked source and no AOSP build-tree source** (scanned 57 `framework*.jar` javac
variants: 0 covered by CRC); the remaining 4 are the S3 dalvik classes
(reproducible via `core-libart.jar`). Buckets of the 1266: `com/android/*` 268,
`android/bluetooth` 226, `android/hardware` 138, `android/net` 137, `android/app`
100, `android/media` 74, `android/view` 58, `android/nfc` 53, `android/uwb` 24,
… — full-bytecode device-framework inner classes (e.g.
`ActivityManager$ISystemBarListenerImpl`, `ActivityMetricsLaunchObserver`,
`IInterceptor`, `BluetoothA2dp$OptionalCodecsPreferenceStatus`,
`BLASTBufferQueue$TransactionCompleteCallback`).

**Provenance of the gap:** the original merge product
`libs/android-merged.jar` (commit `5836ec4`, 44846603 B) — which was the actual
S1 source of truth — was **deleted in commit `683ef39a`** ("chore(Phase A):
清理死依赖"). It is no longer tracked. The 1 overwritten CRC mismatch is
`META-INF/MANIFEST.MF` (jar-tool artifact; see §2.5).

### 2.5 MANIFEST.MF detail

- live `android.jar` MANIFEST.MF: `Manifest-Version: 1.0\r\nCreated-By: 25.0.2 (Oracle Corporation)\r\n\r\n` (CRLF; JDK `jar cf`, 2026-07-22).
- live `core-for-system-modules.jar` MANIFEST.MF: `Manifest-Version: 1.0\nCreated-By: soong_zip\n\n` (LF; original soong_zip, preserved by `jar uf` during S3).

S1 (Python `zipfile` merge) writes the android.jar manifest to the exact live
bytes; S3 (`jar uf`) preserves it, and a defensive post-S3 manifest
re-normalization (`_rewrite_manifest_entry`) guarantees the CRC matches
regardless of the local JDK version. `core-for-system-modules.jar` keeps
`soong_zip` because it is only ever `jar uf`'d.

### 2.6 `package.xml` rewrite (S0)

Base → live differs in exactly 4 fields (`localPackage path`, `api-level`,
`codename`, `display-name`). S0 rewrites them for the staging name
(`platforms;android-SysUISdk-staging`, api-level 37, codename SysUISdk).
Verify checks **presence/shape**, not byte-equality, for `package.xml`.

## 3. Provenance table (live SDK file → stage → source)

| live SDK file | produced by | source artifact | reproducible? |
|---------------|-------------|-----------------|---------------|
| `android.jar` | S1 + S3 | S1: `libs/framework.jar` (master) ∪ base `android.jar`; S3: AOSP `core-libart.jar` (4 dalvik classes); MANIFEST.MF pinned | **NO** — 1266 entries orphaned (deleted `libs/android-merged.jar`, commit `683ef39a`) |
| `core-for-system-modules.jar` | S3 | base `core-for-system-modules.jar` + 4 dalvik classes from AOSP `core-libart.jar` | **yes** |
| `framework.aidl` | S2 | base `framework.aidl` + 2 decls from `tools/install_sdk.py` | **yes** |
| `package.xml` | S0 | base `package.xml`, 4 fields rewritten for staging name | **yes** (shape) |
| `build.prop` | S0 | base `build.prop` (copied verbatim; base == live) | **yes** |
| `data/`, `optional/` | S0 | base subtrees (copied verbatim; base == live) | **yes** |
| `android.jar.orig`, `core-for-system-modules.jar.orig`, `framework.aidl.bak-preaidl` | S1/S3/S2 | created on first mutation (== pre-stage base) | **yes** (parity) |

AOSP build-output sources (not tracked in git, sourced from the local AOSP tree):
- `core-libart.jar` (S3): `/home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar`
- base platform `android-37.0`: `~/Android/Sdk/platforms/android-37.0` (stock SDK install)

## 4. The pipeline (`tools/build_sysuisdk.py`)

```
S0  copy base platform (android-37.0) → --target; skip *.orig/*.bak-preaidl;
    rewrite package.xml for the staging name; build.prop/data/optional verbatim.
S1  merge libs/framework.jar (master) into android.jar via stdlib zipfile
    (framework bytes win the intersection; base fills the gaps; MANIFEST.MF
    pinned to the audited live bytes). Creates android.jar.orig on first run.
S2  patch framework.aidl (reuses tools/install_sdk.py patch_framework_aidl).
    Creates framework.aidl.bak-preaidl on first run.
S3  inject dalvik.annotation.optimization classes into both jars (reuses
    tools/patch_sdk_dalvik_annotations.py patch_target; source: core-libart.jar).
    Creates core-for-system-modules.jar.orig on first run; normalizes android.jar
    MANIFEST.MF to the audited live bytes after jar uf.
S5  --verify: entry inventories (names+CRC) for the two jars; byte-equality for
    framework.aidl and build.prop; presence/shape for package.xml; file-set
    equality for data/ and optional/. Per-file PASS/DIFF report; exit non-zero
    on any DIFF.
```

All stages idempotent. Live-SDK hard-fail guard on `--target`. Stdlib-only
(except S3's `jar uf`, which requires a JDK on PATH — confirmed `jar 25.0.2`).

### Light adaptation of existing tools (CLI behavior unchanged)

- `tools/install_sdk.py`: extracted `patch_framework_aidl(aidl_path)` (importable
  by the orchestrator); `main()` CLI unchanged (targets the live SDK via
  `ANDROID_HOME`).
- `tools/patch_sdk_dalvik_annotations.py`: already importable (`patch_target`);
  no change required.

## 5. Fresh-machine usage

```bash
# 1. Clone the repo (libs/ is committed; no AOSP build needed for S0–S3 except
#    the core-libart.jar source for S3, which is an AOSP build output — if the
#    AOSP tree is not present locally, point --core-libart-jar at a copy).
# 2. Build the staging SDK:
python3 tools/build_sysuisdk.py --clean \
  --target ~/Android/Sdk/platforms/android-SysUISdk-staging
# 3. Verify against the live SDK (proof of reproducibility):
python3 tools/build_sysuisdk.py --verify \
  --target ~/Android/Sdk/platforms/android-SysUISdk-staging
# 4. (After the S1 source gap is resolved — see §6 — verify exits 0.)
#    To use staging as the compile SDK, rename it to android-SysUISdk.
```

Tests (never touch the real SDK):

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'   # 103 tests, OK
```

## 6. Verify result (2026-08-13 run) — the reproducibility proof

```
$ python3 tools/build_sysuisdk.py --clean --target .../android-SysUISdk-staging
S0: copying base platform android-37.0 -> android-SysUISdk-staging
S1: merged framework.jar (master, 25918 entries) + base-only (10336) = 36254 entries
S3: android.jar +4 dalvik; core-for-system-modules.jar +4 dalvik

$ python3 tools/build_sysuisdk.py --verify --target .../android-SysUISdk-staging
S5: android.jar:                  DIFF  (staging=36258 live=37524 missing=1266 extra=0 crc_diff=0)
S5: core-for-system-modules.jar:  PASS  (staging=1789  live=1789  missing=0    extra=0 crc_diff=0)
S5: framework.aidl:               PASS  (staging=136009B live=136009B)
S5: build.prop:                   PASS  (staging=4360B live=4360B)
S5: package.xml:                  PASS  (path=platforms;android-SysUISdk-staging api-level=37 codename=SysUISdk)
S5: data/:                        PASS  (staging=11204 live=11204 missing=0 extra=0)
S5: optional/:                    PASS  (staging=16    live=16    missing=0 extra=0)
S5: DIFF in 1 file(s): android.jar
exit code: 1
```

**6 of 7 compared files PASS.** The single DIFF is `android.jar`, missing
exactly **1266 entries** with **0 CRC mismatches** — i.e. the merge semantics are
correct and every reproducible entry matches; the gap is purely the 1266
orphaned entries whose source (`libs/android-merged.jar`) was deleted in
`683ef39a` and is not recoverable from any tracked or AOSP-build-tree jar.

### 6.1 Why `--verify` cannot exit 0 with `libs/framework.jar` as the S1 source

`libs/framework.jar` (25918 entries, the AOSP core-framework turbine-combined
stubs) reproduces 25869 of the 27139 merge deltas (21428 added + 4441
overwritten = 25869, +49 no-op = 25918). The remaining 1266 entries are
full-bytecode device-framework inner classes (bluetooth/nfc/uwb/`com.android.
internal`/SystemUI-relevant) present in the live `android.jar` but in **no
tracked jar and no AOSP build-tree jar**. No stage-semantics change can conjure
them; resolving the DIFF requires a decision on S1's source (§7).

## 7. Escalation (redline-gated) — S1 source decision needed

The brief's acceptance (`--verify` exit 0) cannot be met with `libs/framework.jar`
as the S1 source. Resolving it touches `libs/` (forbidden path for this worker)
and/or a brief-spec / dependency decision (CHARTER Part 5.4, rule H.5). Options
for the user:

1. **Re-track the merge source.** Re-extract the full on-device/combined
   framework jar (the source that produced the deleted `libs/android-merged.jar`)
   and commit it under `libs/` as the S1 source (replacing or supplementing
   `libs/framework.jar`). Then S1 reproduces all 37524 entries and verify exits 0.
   Cost: a larger tracked jar (~44 MB); requires identifying the exact 2026-07-22
   source (device `framework.jar` or an AOSP `framework-minus-apex` combined
   variant — note the AOSP `combined/framework.jar` scanned here did NOT contain
   the 1266, so the source is likely a device extraction).
2. **Accept the documented delta.** Keep `libs/framework.jar` as the S1 source,
   document the 1266 orphaned entries as a known historical artifact, and relax
   `--verify` to "PASS with documented exceptions" (exit 0 when the only DIFF is
   the known orphaned set). The pipeline stays honest about what it reproduces
   (97% of `android.jar` + everything else).
3. **Recover the original source from history/device.** Archaeology on the
   2026-07-22 merge (commit `5836ec4`) to identify what `framework.jar` was
   actually merged, then re-track it.

The pipeline, tests, audit, and honest verify report are delivered regardless;
this section is the decision the user must make for full reproducibility.

## 8. S4 (framework-res) — next brief

The `androidprv:` framework private-resource gap (AGENTS.md §2.4 point 2;
`docs/issues/2026-08-12-current-progress-standards-review.md`) is **not** part of
this brief. S4 will merge `framework-res.apk`'s `resources.arsc` + `res/` into
the SysUISdk `android.jar` and is tracked separately.
