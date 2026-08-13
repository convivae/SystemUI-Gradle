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
Stage S4 (overlay the current AOSP `framework-res.apk` resources onto
`android.jar`, to fix `androidprv:` private-resource linking) was added in task
011 (2026-08-13); see §8. S4 is opt-in (`--stages s0,s1,s2,s3,s4`); the
strict 7/7 pre-S4 reproducibility proof (default `--stages s0,s1,s2,s3` +
`--verify`) is unchanged.

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

### 2.4 S1 — `android-merged.jar` wholesale copy (RESOLVED 2026-08-13)

> **Update 2026-08-13 (task 010b):** the S1 source gap documented in the
> original audit is **resolved**. The user decided to re-track the recovered
> `libs/android-merged.jar` as the declared S1 source. `--verify` now reaches
> 7/7 PASS (§6). The historical `libs/framework.jar`-based audit is retained
> below as `§2.4.1` for provenance; the current semantics are in `§2.4.2`.

#### 2.4.1 Historical audit (original gap, 2026-08-13)

The 2026-07-22 manual merge (`docs/issues/2026-07-22-sdk-android-jar-merge.md`)
originally used the semantics: **framework.jar is master; android.jar fills the
gaps** (`merged = framework_all ∪ android_only`, framework bytes win the
intersection, repackaged with `jar cf`). `libs/framework.jar` is byte-identical
to AOSP `frameworks/base/framework/android_common/turbine-combined/framework.jar`
(25918 entries — core framework, **no** apex modules).

The original merge *product* was `libs/android-merged.jar` (commit `5836ec4`,
44846603 B, SHA-256
`67ceccc5cd9d610189d45596481b1f8fefe557c8b41a2820d9d74df536770d79`) — the
actual S1 source of truth. It was **deleted in commit `683ef39a`**
("chore(Phase A): 清理死依赖"), so the first pipeline run (task 010) had only
`libs/framework.jar` available and reported:

```
live entries  = 37524
framework.jar ∪ orig = 25918 + 14826 − 4490(intersection) = 36254
live                 = 36254 + 1266(truly orphaned) + 4(S3-reproducible) + MANIFEST.MF
```

The 1266 "orphaned" entries (full-bytecode device-framework inner classes:
bluetooth/nfc/uwb/`com.android.internal`/SystemUI-relevant — e.g.
`ActivityManager$ISystemBarListenerImpl`, `ActivityMetricsLaunchObserver`,
`BluetoothA2dp$OptionalCodecsPreferenceStatus`,
`BLASTBufferQueue$TransactionCompleteCallback`) existed in no tracked jar and
no AOSP build-tree jar (scanned 57 `framework*.jar` javac variants: 0 covered by
CRC). They were, however, present in the deleted `libs/android-merged.jar`.

#### 2.4.2 Current semantics (task 010b, 2026-08-13)

**S1 source = `libs/android-merged.jar`** (re-tracked). Empirical audit of the
recovered blob against the live `android.jar`:

```
merged entries (incl dirs) = 38892
live   entries (incl dirs) = 38896
live - merged              = 4   (exactly the S3 dalvik classes)
merged - live              = 0   (nothing to drop)
live ∩ merged              = 38892
CRC diffs on intersection  = 0
merged res/ entries        = 8451  (== live res/ count; merged carries
                                   resources.arsc + res/ verbatim)
```

`android-merged.jar` is a **strict superset** of the live `android.jar` minus
the 4 S3 dalvik classes, with **0 CRC mismatches** on the 38892-entry
intersection and **0 extra entries**. It already carries `resources.arsc` +
`res/` (8451 entries, matching live), so the base jar is **not** consulted for
gaps.

**New S1 = copy `android-merged.jar` wholesale as `android.jar`** (MANIFEST.MF
pinned to the audited live bytes for JDK-determinism; directory entries dropped
— consistent with `_jar_inventory`/`_rewrite_manifest_entry`, and the live SDK's
inventory-level verify ignores directories). No base merge. S3 then adds the 4
dalvik classes → 37520 + 4 = 37524 = live.

#### 2.4.3 Provenance chain for `libs/android-merged.jar`

```
libs/android-merged.jar
  ← recovered from git history (blob at commit 5836ec44, 2026-08-13)
  ← originally committed 2026-07-22 (commit 5836ec4) as the merge product of
     the on-device/AOSP framework jar ∪ the base android.jar (the 2026-07-22
     manual SDK build; see docs/issues/2026-07-22-sdk-android-jar-merge.md)
  ← deleted 2026-07-29 in commit 683ef39a ("chore(Phase A): 清理死依赖")
  ← re-tracked 2026-08-13 (task 010b, user decision) as the declared S1 source
  ← SHA-256 67ceccc5cd9d610189d45596481b1f8fefe557c8b41a2820d9d74df536770d79
     (architect-verified; covers 100% of the 2638 missing entries from the
     task-010 verify DIFF)
```

`libs/framework.jar` remains in the tree (it is the AOSP core-framework
turbine-combined stubs and is still referenced by `build.gradle.kts` for
bootclasspath/classpath injection per AGENTS.md §2.4), but it is **no longer the
S1 source**. The CLI option `--merged-jar` (default `libs/android-merged.jar`)
governs S1.

### 2.5 MANIFEST.MF detail

- live `android.jar` MANIFEST.MF: `Manifest-Version: 1.0\r\nCreated-By: 25.0.2 (Oracle Corporation)\r\n\r\n` (CRLF; JDK `jar cf`, 2026-07-22).
- live `core-for-system-modules.jar` MANIFEST.MF: `Manifest-Version: 1.0\nCreated-By: soong_zip\n\n` (LF; original soong_zip, preserved by `jar uf` during S3).

S1 (Python `zipfile` wholesale copy of `android-merged.jar`) writes the
android.jar manifest to the exact live bytes; S3 (`jar uf`) preserves it, and a
defensive post-S3 manifest re-normalization (`_rewrite_manifest_entry`)
guarantees the CRC matches regardless of the local JDK version.
`core-for-system-modules.jar` keeps `soong_zip` because it is only ever `jar uf`'d.

### 2.6 `package.xml` rewrite (S0)

Base → live differs in exactly 4 fields (`localPackage path`, `api-level`,
`codename`, `display-name`). S0 rewrites them for the staging name
(`platforms;android-SysUISdk-staging`, api-level 37, codename SysUISdk).
Verify checks **presence/shape**, not byte-equality, for `package.xml`.

## 3. Provenance table (live SDK file → stage → source)

| live SDK file | produced by | source artifact | reproducible? |
|---------------|-------------|-----------------|---------------|
| `android.jar` | S1 + S3 + S4 | S1: `libs/android-merged.jar` wholesale copy (MANIFEST.MF pinned; carries the stale May-27 `resources.arsc`+`res/`); S3: AOSP `core-libart.jar` (4 dalvik classes); S4 (opt-in): overlay `libs/framework-res.apk` `resources.arsc`+`res/` | **yes** pre-S4 (7/7 PASS, §6); post-S4 use `--verify --expect-s4-delta` |
| `core-for-system-modules.jar` | S3 | base `core-for-system-modules.jar` + 4 dalvik classes from AOSP `core-libart.jar` | **yes** |
| `framework.aidl` | S2 | base `framework.aidl` + 2 decls from `tools/install_sdk.py` | **yes** |
| `package.xml` | S0 | base `package.xml`, 4 fields rewritten for staging name | **yes** (shape) |
| `build.prop` | S0 | base `build.prop` (copied verbatim; base == live) | **yes** |
| `data/`, `optional/` | S0 | base subtrees (copied verbatim; base == live) | **yes** |
| `android.jar.orig`, `android.jar.bak-preres`, `core-for-system-modules.jar.orig`, `framework.aidl.bak-preaidl` | S1/S4/S3/S2 | created on first mutation (== pre-stage base) | **yes** (parity) |

AOSP build-output sources (not tracked in git, sourced from the local AOSP tree):
- `core-libart.jar` (S3): `/home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar`
- base platform `android-37.0`: `~/Android/Sdk/platforms/android-37.0` (stock SDK install)

Tracked in git:
- `libs/android-merged.jar` (S1 source, task 010b 2026-08-13): SHA-256
  `67ceccc5cd9d610189d45596481b1f8fefe557c8b41a2820d9d74df536770d79`; recovered
  from git history blob at commit `5836ec44` (originally committed `5836ec4`,
  deleted `683ef39a`, re-tracked `2026-08-13`). See §2.4.3.
- `libs/framework-res.apk` (S4 source, task 011 2026-08-13): SHA-256
  `7e76ce7d9de50d47a47396d36f4d0fd10a9d15048b6aef498d7ad434b018bef7`,
  36 079 832 B; copied from the canonical AOSP Soong product
  `frameworks/base/core/res/framework-res/android_common/framework-res.apk`.
  Regeneration: `cp <that path> libs/framework-res.apk` (requires a built AOSP
  tree; the tracked copy makes the SDK rebuildable without `out/`).

## 4. The pipeline (`tools/build_sysuisdk.py`)

```
S0  copy base platform (android-37.0) → --target; skip *.orig/*.bak-preaidl;
    rewrite package.xml for the staging name; build.prop/data/optional verbatim.
S1  copy libs/android-merged.jar wholesale as android.jar via stdlib zipfile
    (merged is a strict superset of live-minus-4-dalvik; carries resources.arsc
    + res/ verbatim; MANIFEST.MF pinned to the audited live bytes; directory
    entries dropped). Creates android.jar.orig on first run.
S2  patch framework.aidl (reuses tools/install_sdk.py patch_framework_aidl).
    Creates framework.aidl.bak-preaidl on first run.
S3  inject dalvik.annotation.optimization classes into both jars (reuses
    tools/patch_sdk_dalvik_annotations.py patch_target; source: core-libart.jar).
    Creates core-for-system-modules.jar.orig on first run; normalizes android.jar
    MANIFEST.MF to the audited live bytes after jar uf.
S4  (opt-in, --stages s0,s1,s2,s3,s4) overlay the current AOSP framework-res.apk
    resources.arsc + res/** onto android.jar, replacing S1's stale May-27
    snapshot — fixes the framework-table half of the androidprv: linking gap
    (AGENTS.md §2.4 point 2). Strips resources.arsc + res/** from android.jar,
    adds the same from libs/framework-res.apk (non-resource entries incl. the
    pinned MANIFEST.MF preserved; the apk's AndroidManifest.xml/META-INF/assets
    are NOT carried over). Creates android.jar.bak-preres on first run.
    Deterministic, idempotent. NOTE: S4 alone does NOT clear androidprv: build
    errors — see §8.2 (Factor 2: AGP merger drops xmlns:androidprv).
S5  --verify: entry inventories (names+CRC) for the two jars; byte-equality for
    framework.aidl and build.prop; presence/shape for package.xml; file-set
    equality for data/ and optional/. Per-file PASS/DIFF report; exit non-zero
    on any DIFF. --expect-s4-delta: after a build with s4, android.jar non-
    resource entries stay strict (must match live) while its resource entries
    (resources.arsc + res/**) are reported as the expected S4 delta (not gating);
    the other 6 files remain strict. The pre-S4 strict 7/7 check is unchanged.
--apply (pre-approved 2026-08-13): sync staging artifacts (android.jar,
    core-for-system-modules.jar, framework.aidl) onto the live SDK with
    timestamped per-file backups (<name>.bak-<ts>); skips identical files; never
    touches package.xml/source.properties/sdk.properties (identity files).
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
# 1. Clone the repo (libs/ is committed, including libs/android-merged.jar and
#    libs/framework-res.apk; no AOSP build needed for S0–S2; S3 needs
#    core-libart.jar, an AOSP build output — if the AOSP tree is not present
#    locally, point --core-libart-jar at a copy).
# 2a. Build the staging SDK reproducing the CURRENT live SDK exactly
#     (pre-S4 reproducibility proof — default stages):
python3 tools/build_sysuisdk.py --clean \
  --target ~/Android/Sdk/platforms/android-SysUISdk-staging
python3 tools/build_sysuisdk.py --verify \
  --target ~/Android/Sdk/platforms/android-SysUISdk-staging   # 7/7 PASS, exit 0
# 2b. Build the FIXED staging SDK (with the framework-res overlay, S4):
python3 tools/build_sysuisdk.py --clean --stages s0,s1,s2,s3,s4 \
  --target ~/Android/Sdk/platforms/android-SysUISdk-staging
python3 tools/build_sysuisdk.py --verify --expect-s4-delta \
  --target ~/Android/Sdk/platforms/android-SysUISdk-staging
    # android.jar non-resource strict PASS + resource delta (expected); exit 0
# 3. To use staging as the compile SDK, rename it to android-SysUISdk, OR sync
#    a built staging onto the live SDK with timestamped backups (pre-approved):
python3 tools/build_sysuisdk.py --apply \
  --source ~/Android/Sdk/platforms/android-SysUISdk-staging
```

Tests (never touch the real SDK):

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'   # 116 tests, OK
```

## 6. Verify result (2026-08-13 run, task 010b) — the reproducibility proof

```
$ python3 tools/build_sysuisdk.py --clean --target .../android-SysUISdk-staging
S0: copying base platform android-37.0 -> android-SysUISdk-staging
S1: copied android-merged.jar wholesale (37520 entries) as android.jar
S2: appended 2 decls to framework.aidl
S3: android.jar +4 dalvik; core-for-system-modules.jar +4 dalvik

$ python3 tools/build_sysuisdk.py --verify --target .../android-SysUISdk-staging
S5: android.jar:                  PASS  (staging=37524 live=37524 missing=0 extra=0 crc_diff=0)
S5: core-for-system-modules.jar:  PASS  (staging=1789  live=1789  missing=0 extra=0 crc_diff=0)
S5: framework.aidl:               PASS  (staging=136009B live=136009B)
S5: build.prop:                   PASS  (staging=4360B live=4360B)
S5: package.xml:                  PASS  (path=platforms;android-SysUISdk-staging api-level=37 codename=SysUISdk)
S5: data/:                        PASS  (staging=11204 live=11204 missing=0 extra=0)
S5: optional/:                    PASS  (staging=16    live=16    missing=0 extra=0)
S5: ALL PASS — staging is inventory-equivalent to the live SDK.
exit code: 0
```

**7 of 7 compared files PASS; `--verify` exits 0.** The staging SDK is
inventory-equivalent to the live SDK: every reproducible entry (name + CRC)
matches across `android.jar` (37524 entries, 0 missing, 0 extra, 0 CRC diff),
`core-for-system-modules.jar`, `framework.aidl`, `build.prop`, `package.xml`,
`data/`, and `optional/`. The SysUISdk is now fully reproducible from scratch
from tracked artifacts (`libs/android-merged.jar` + base `android-37.0` + AOSP
`core-libart.jar` + the scripted S2/S3 patches).

### 6.1 Historical: the task-010 DIFF (resolved)

The first pipeline run (task 010, commit `a9d3c472`) used `libs/framework.jar`
as the S1 source and reported `android.jar DIFF (staging=36258 live=37524
missing=1266 extra=0 crc_diff=0)` — 6/7 PASS. The 1266 missing entries were the
"orphaned" device-framework inner classes whose source (`libs/android-merged.jar`)
had been deleted in `683ef39a`. Task 010b re-tracked that blob (§2.4.3); the
DIFF is now gone. This subsection is retained for provenance only.

### 6.2 Post-S4 verify (task 011, 2026-08-13) — `--expect-s4-delta`

A staging build WITH s4 intentionally diverges from the live SDK in
`android.jar`'s resource entries (the whole point of S4 is to replace the
stale May-27 resources with the current AOSP framework-res). Plain `--verify`
therefore reports `android.jar DIFF` after s4. `--verify --expect-s4-delta`
splits the android.jar comparison: non-resource entries stay strict (must
match live names+CRC) while resource entries (`resources.arsc` + `res/**`) are
reported as the expected delta. The 2026-08-13 run:

```
S5: android.jar: PASS (non-resource strict)  (staging_nr=29159 live_nr=29159 missing=0 extra=0 crc_diff=0)
     resource delta (resources.arsc + res/**): staging=8203 live=8365 missing=230 extra=68 crc_diff=1039
S5: core-for-system-modules.jar: PASS  ... 6 other files PASS ...
S5: ALL PASS (non-resource strict)   exit 0
```

The pre-S4 strict proof (`--stages s0,s1,s2,s3` + `--verify`) remains 7/7 PASS,
exit 0 — the strict check is **not** weakened.

## 7. S1 source decision — RESOLVED (2026-08-13)

The redline-gated escalation from task 010 is **resolved by user decision
(2026-08-13)**: option 1 (re-track the merge source) was chosen. The recovered
`libs/android-merged.jar` (blob from git history `5836ec44`, SHA-256
`67ceccc5…770d79`, architect-verified to cover 100% of the 2638 missing entries)
is committed under `libs/` as the declared S1 source. S1 now copies it wholesale
(§2.4.2); `--verify` exits 0 with 7/7 PASS (§6). No further action needed on
this item. (Options 2 and 3 from the original escalation are moot.)

## 8. S4 (framework-res overlay) — implemented (task 011, 2026-08-13)

### 8.1 What S4 does

Stage S4 (`stage_s4` + `_overlay_framework_res` in `tools/build_sysuisdk.py`)
strips the existing `resources.arsc` + `res/**` from staging `android.jar` (the
stale May-27 snapshot carried by `libs/android-merged.jar`, S1) and adds
`resources.arsc` + `res/**` from `libs/framework-res.apk` (the current AOSP
Soong product of `frameworks/base/core/res`). Non-resource entries (classes,
the pinned `META-INF/MANIFEST.MF`) are preserved; the apk's `AndroidManifest.xml`,
`META-INF/*`, `assets/` are NOT carried over. Deterministic (per-entry CRC via
`_copy_zipinfo`), idempotent, `.bak-preres` backup on first mutation. See
`docs/issues/2026-08-13-sysuisdk-reproducible-build.md` §8 for the full audit.

### 8.2 The androidprv: gap has TWO independent factors (S4 fixes only one)

The brief hypothesized a single root cause ("stale May-27 resources.arsc
missing the androidprv symbols"). Systematic debugging found **two independent
factors**, confirmed by minimal `aapt2 link` tests against the live/staging jar:

**Factor 1 — stale framework resource TABLE (S4 fixes this).** The stale
`android.jar` `resources.arsc` lacked the attr *entries* (the symbols exist in
the string pool but not as resolvable `<attr>` entries). The attrs are defined
in AOSP `frameworks/base/core/res/res/values/attrs.xml` (e.g.
`attrs.xml:1298 <attr name="materialColorSurfaceContainerHighest" format="color"/>`)
and compiled into `framework-res.apk` with valid IDs
(`materialColorSurfaceContainerHighest` = `0x011200d7`). Proof: with
`xmlns:androidprv` declared, `aapt2 link` against the STALE backup jar fails
`resource android:attr/materialColorSurfaceContainerHighest not found`; against
the OVERLAID (fresh) jar it SUCCEEDS. **S4 is necessary and sufficient for
this half.**

**Factor 2 — AGP `MergeResources` DROPS `xmlns:androidprv` (NOT addressed by
S4; out of scope for task 011).** Source `SystemUI-res/res/values/colors.xml`
declares `xmlns:androidprv="http://schemas.android.com/apk/prv/res/android"`
on `<resources>` (164 SystemUI res files use `androidprv:`, only inside
*values*, never as XML attribute prefixes). AGP's merger emits a merged
`values.xml` whose root declares only `xmlns:android`, `xmlns:ns1` (tools),
`xmlns:xliff` — `xmlns:androidprv` is dropped (0 occurrences of `prv/res/android`
in the merged file despite 81 `androidprv:` references). AAPT2's
`ExtractPackageFromNamespace` (aapt2 `xml/XmlUtil.cpp`) maps the *URI*
`http://schemas.android.com/apk/prv/res/android` → package `android`, private;
without the declaration the `androidprv:` prefix in a value is unresolved →
`resource androidprv:attr/X not found`. Proof (overlaid jar):
```
Variant C (androidprv: WITHOUT xmlns:androidprv): link exit 1
   resC/values/colors.xml:3: error: resource androidprv:attr/materialColorSurfaceContainerHighest not found.
Variant D (androidprv: WITH xmlns:androidprv):    link exit 0  (SUCCESS)
Variant E (ALL 11 failing symbols, WITH declaration, overlaid jar): link exit 0
```
Variant C reproduces the full-build error byte-for-byte; Variant E proves
**overlay + declaration together resolve every failing symbol**. The merger
strips the declaration because the prefix is only used inside attribute
*values* (XML serializers drop namespace declarations they consider "unused").
CarSystemUIGradle (which also uses `androidprv:` in 9 files) has no special
merger config and no built intermediates — it has not solved this either.

### 8.3 Verdict & escalation

- S4 (overlay) is **correct, necessary, tested (116 OK), and applied to live**
  (pre-approved). It fixes Factor 1. Live `android.jar` hash `9c4deb78…` →
  `f72b92e4…`; timestamped backups on the live SDK.
- Task-011 Step-5 acceptance (**0 androidprv errors**) is **NOT met** — Factor 2
  is the sole remaining blocker for `:app:processDebugResources` (20 errors,
  all `androidprv:...not found`). Fixing Factor 2 requires build/merger
  configuration (`build.gradle.kts` / `gradle.properties` — CHARTER Part 5.4)
  or res changes (rule R — Part 5.1/5.2), both **outside task 011's Allowed
  Paths**. **Escalated as REDLINE** — the worker did not attempt it.
- `:app:assembleDebug` (Step 6 diagnostics) fails at the same
  `:app:processDebugResources`; no APK produced.
