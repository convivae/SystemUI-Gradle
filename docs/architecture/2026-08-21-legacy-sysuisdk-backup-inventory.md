# Legacy Live SysUISdk Backup Inventory (Task 047)

**Date:** 2026-08-21
**Status:** Completed (read-only audit; recommendations advisory; `DELETED=0`)
**Spec:** `docs/issues/2026-08-21-legacy-sysuisdk-backup-inventory.md`
**Plan:** `docs/superpowers/plans/2026-08-21-legacy-sysuisdk-backup-inventory.md`

## 1. Goal and scope

Byte-level, reproducible inventory and per-file retention recommendation for the nine
historical backup files under the legacy live platform
`/home/conv/Android/Sdk/platforms/android-SysUISdk`. The audit is strictly read-only
against the Android SDK and AOSP trees; evidence and the canonical comparison SDK were
written only beneath `/tmp/task047-*`. No deletion was executed; irreversible deletion
requires separate explicit user approval.

## 2. Method and evidence

- Fixed-name Python manifest (`/tmp/task047-inspect.py`, no glob, no newest-file
  selector) recorded size, nanosecond mtime, SHA-256, type, ZIP CRC test, entry count,
  duplicate-name list, and manifest presence for exactly the nine frozen names.
  Outputs: `/tmp/task047-before.json`, `/tmp/task047-after.json` (identical).
- Canonical current SDK generated **outside** the live platform (Task 045 single-entry
  generator) into `/tmp/task047-generated/android-SysUISdk`; exit 0; marker
  `.sysuisdk-generated.json` present.
- Per-entry comparison (`/tmp/task047-compare.py`, evidence
  `/tmp/task047-comparison.json`): entry-name sets plus **per-entry bytes** for every
  JAR pair (backup vs stock / live-primary / canonical), and line-level diff for the
  AIDL backup. Entry counts below that feed comparisons are non-directory entries
  unless stated otherwise.

## 3. Before-manifest (machine-generated, 2026-08-22 UTC+8)

```text
BACKUPS=9
HASHED=9
MISSING=0
EXTRA_BACKUP_LIKE=none
```

| File | Size (B) | mtime (local) | SHA-256 | Type | ZIP test | Entries (total) | Dup names | MANIFEST.MF |
|---|---:|---|---|---|---|---:|---:|---|
| `android.jar.orig` | 42,966,877 | 2026-05-27T14:47:12.246 | `06893f4a316277dfe8c8fe42d4a25552b4e84be474d8c7ea7d34b6ddc26e2ad6` | zip/jar | OK | 15,152 | 0 | yes |
| `android.jar.bak-20260813-210816` | 44,848,587 | 2026-08-13T17:50:20.697 | `9c4deb7814d73935cbf1c54736dc2692a77fadda4dd352af403ee5edafadb09f` | zip/jar | OK | 38,896 | 0 | yes |
| `android.jar.bak-20260821-011116` | 56,970,625 | 2026-08-13T21:08:16.771 | `f72b92e4a2c6ba658152ff442d78bacb3c556c997451607245c09571e4df1350` | zip/jar | OK | 37,362 | 0 | yes |
| `android.jar.bak-20260821-013303` | 57,008,807 | 2026-08-21T01:10:31.714 | `fc7eaf46fd45aa7fd9f63551b131deebe215906a954c69e8bdd773b19b97126f` | zip/jar | OK | 37,397 | 0 | yes |
| `core-for-system-modules.jar.orig` | 1,521,715 | 2026-05-27T14:47:12.249 | `c88b1568be819fbf03dd4ab97b36a6729d305581efbe456b6ebe15d72d61c0f7` | zip/jar | OK | 1,894 | 0 | yes |
| `core-for-system-modules.jar.bak-20260813-210816` | 1,516,011 | 2026-08-13T17:50:20.854 | `b097eb9879726a9c949ff7df506fdfb34a368a693eddfadc73b49fcda2bdfe04` | zip/jar | OK | 1,898 | 0 | yes |
| `core-for-system-modules.jar.bak-20260821-011116` | 1,516,011 | 2026-08-13T21:08:12.519 | `a10e8e6c28ae1469a3f4575c70528e9dae90b8968f1611b4357e33047f38726a` | zip/jar | OK | 1,898 | 0 | yes |
| `core-for-system-modules.jar.bak-20260821-013303` | 1,513,413 | 2026-08-21T01:10:27.591 | `a211c6ded3d29894ae5ae4c2fc6a0af84a6804feb81433098523ec8a9c1da357` | zip/jar | OK | 1,824 | 0 | yes |
| `framework.aidl.bak-preaidl` | 135,915 | 2026-07-29T15:46:30.317 | `8ffac8df720edb18b695f9e5d804fcc9eccc748d31d6cfacf8d50ed8689237ed` | aidl text | n/a | n/a | n/a | n/a |

All eight JAR backups pass full ZIP CRC validation (`testzip` clean) and contain zero
duplicate entry names. No additional `.bak-*`/`.orig` files exist in the live platform.

## 4. Comparison targets

Canonical generation command (run from the repository root, exactly as briefed):

```bash
python3 tools/build_sysuisdk.py \
  --aosp-root /home/conv/myspace/aosp \
  --sdk-root /home/conv/Android/Sdk \
  --base-platform /home/conv/Android/Sdk/platforms/android-37.0 \
  --output /tmp/task047-generated/android-SysUISdk
```

Output: `SysUISdk composed: ... base platform : android-37.0 (11382 files); AOSP
inputs: 8 (exact frozen map); bridge entries: 39 in both target jars; generated: 11381
files`, exit 0. Marker `.sysuisdk-generated.json` exists.

| Primary | Role | Path | SHA-256 |
|---|---|---|---|
| `android.jar` | stock | `android-37.0/android.jar` | `06893f4a316277dfe8c8fe42d4a25552b4e84be474d8c7ea7d34b6ddc26e2ad6` |
| `android.jar` | live-primary | `android-SysUISdk/android.jar` | `652fd3d4a719724b89fe3c8c8122c4f021ec3692307e3130cf8850c89b157e8e` |
| `android.jar` | canonical | `/tmp/task047-generated/.../android.jar` | `c01a910ac61b7b9a6a45271c7237a7264a5c0ab02cfd83c165f31ae39d78791d` |
| `core-for-system-modules.jar` | stock | `android-37.0/core-for-system-modules.jar` | `c88b1568be819fbf03dd4ab97b36a6729d305581efbe456b6ebe15d72d61c0f7` |
| `core-for-system-modules.jar` | live-primary | `android-SysUISdk/core-for-system-modules.jar` | `330e0818407410ddeb2eb7c9b57c5a3309942b82127b05eaef1f078be5c48af3` |
| `core-for-system-modules.jar` | canonical | `/tmp/task047-generated/.../core-for-system-modules.jar` | `e7bc0115d4e276245ac2ef40789cc7d03033f5419613a1c31999e45129a69c5d` |
| `framework.aidl` | stock | `android-37.0/framework.aidl` | `8ffac8df720edb18b695f9e5d804fcc9eccc748d31d6cfacf8d50ed8689237ed` |
| `framework.aidl` | live-primary | `android-SysUISdk/framework.aidl` | `d0497fdc8ce140a04e7c64ec3fee6aa2b6836a9e47cba021e16be1c80464962e` |
| `framework.aidl` | canonical | `/tmp/task047-generated/.../framework.aidl` | `d0497fdc8ce140a04e7c64ec3fee6aa2b6836a9e47cba021e16be1c80464962e` |

The three canonical hashes equal the values recorded at Task 045 main-fresh acceptance
(`c01a910a…`, `e7bc0115…`, `d0497fdc…`), confirming deterministic reproduction from the
frozen AOSP inputs.

## 5. Per-entry comparison findings

### 5.1 `android.jar` family

Non-directory entry counts: stock 14,826; live 37,397; canonical 36,131;
`bak-20260813-210816` 37,524; `bak-20260821-011116` 37,362; `bak-20260821-013303` 37,397.

- `android.jar.orig` **is byte-identical to stock** `android-37.0/android.jar`
  (same SHA-256; 14,826/14,826 entries, 0 changed).
- `android.jar.bak-20260813-210816`: unique content. vs live-primary: 230 entries only
  in the backup (an older `res/**` framework-resource state — e.g.
  `res/color-night-v8/shade_panel_*`, `res/color/accessibility_*`,
  `res/color/btn_material_*_watch.xml`, `res/android.mime.types`), 103 entries only in
  live (bridge classes + newer resource variants), and **1,039 entries with different
  bytes**. vs canonical: 1,496 backup-only, 103 canonical-only. This is the pre-2026-08-21
  legacy patch state; its content exists nowhere else in the audited set.
- `android.jar.bak-20260821-011116`: content is a **strict subset of the live primary**
  — 0 backup-only entries, 0 changed entries; live = backup + exactly the 35 Task 041
  bridge entries (keepanno ×22, ddmc ×4, libcore ×6, UnsupportedAppUsage ×2,
  AconfigFlagAccessor ×1), all of which are byte-reproducible from the frozen AOSP inputs.
- `android.jar.bak-20260821-013303`: **content-identical to the live primary** — entry
  name set equal (37,397/37,397) and every entry byte equal; only ZIP archive metadata
  (ordering/timestamps/compression) differs, which is why the file SHA-256 differs.
- live-primary vs canonical: canonical content is a **strict subset of live** — all
  36,131 canonical entries exist in live with equal bytes except
  `META-INF/MANIFEST.MF`; live additionally carries **1,266 legacy entries** absent
  from canonical (top groups: `com/android/internal` 250, `android/bluetooth` 203,
  `android/hardware/tv` 89, `android/net/lowpan` 54, `android/content/pm` 52,
  `android/net` 50, `android/nfc` 49, …), a legacy-pipeline surface the current frozen
  generator map does not emit. Task 045 already proved functional parity (Debug/R8/
  Release all pass) despite this difference, so no action is implied here — but it means
  the live `android.jar` content is **not** byte- or content-reproducible from immutable
  inputs by the current generator.

### 5.2 `core-for-system-modules.jar` family

Non-directory entry counts: stock 1,785; live 1,824; canonical 1,824;
`bak-20260813-210816` and `bak-20260821-011116` 1,789 each; `bak-20260821-013303` 1,824.

- `core-for-system-modules.jar.orig` **is byte-identical to stock**.
- `bak-20260813-210816` and `bak-20260821-011116` carry **identical content to each
  other** (their differing SHA-256s are archive-metadata only): content = stock +
  exactly 4 entries — the dalvik optimization annotations
  `dalvik/annotation/optimization/{DeadReferenceSafe,NeverCompile,NeverInline,
  ReachabilitySensitive}.class` — each byte-equal to its counterpart in live and in
  canonical. Live/canonical = stock + the full 39-entry bridge (these 4 + the same 35
  Task 041 entries listed above). All content is recoverable from immutable inputs
  (stock base + frozen AOSP bridge jars).
- `bak-20260821-013303`: **content-identical to both the live primary and the canonical
  output** (entry sets equal to each; every entry byte equal). The canonical file itself
  is byte-reproducible by re-running the generator, so this content is fully recoverable.

### 5.3 `framework.aidl` family

- `framework.aidl.bak-preaidl` **is byte-identical to stock** `framework.aidl`
  (1,707 lines).
- live-primary `framework.aidl` is **byte-identical to the canonical output**
  (`d0497fdc…`): 1,709 lines, differing from stock only by the two source-derived
  declarations `interface android.os.IRemoteCallback;` and
  `parcelable com.android.internal.util.ScreenshotRequest;`. Fully reproducible.

## 6. Classification and recommendations

Category semantics (per plan Task 3): `byte-identical/redundant` = no unique information
content — every entry byte is duplicated by a retained source (immutable stock base,
canonical generator output, or the live primary); `unique historical snapshot` = content
exists nowhere else in the audited/immutable set; `malformed/unknown` = none found.

| # | File | Category | Recommendation | Reclaimed bytes if deleted |
|---|---|---|---|---:|
| 1 | `android.jar.orig` | byte-identical/redundant (== immutable stock) | **candidate-delete** | 42,966,877 |
| 2 | `android.jar.bak-20260813-210816` | unique historical snapshot (230 live-absent entries + 1,039 changed entries) | **retain** | 0 |
| 3 | `android.jar.bak-20260821-011116` | byte-identical/redundant (content = strict subset of live primary and of retained row 4) | **candidate-delete** (caveat A) | 56,970,625 |
| 4 | `android.jar.bak-20260821-013303` | byte-identical/redundant (content == live primary, entry-for-entry, byte-for-byte) | **candidate-delete** (caveat A) | 57,008,807 |
| 5 | `core-for-system-modules.jar.orig` | byte-identical/redundant (== immutable stock) | **candidate-delete** | 1,521,715 |
| 6 | `core-for-system-modules.jar.bak-20260813-210816` | byte-identical/redundant (content = stock + 4 AOSP bridge entries, all bytes equal) | **candidate-delete** | 1,516,011 |
| 7 | `core-for-system-modules.jar.bak-20260821-011116` | byte-identical/redundant (same content as row 6; metadata-only difference) | **candidate-delete** | 1,516,011 |
| 8 | `core-for-system-modules.jar.bak-20260821-013303` | byte-identical/redundant (content == live == canonical; canonical byte-reproducible) | **candidate-delete** | 1,513,413 |
| 9 | `framework.aidl.bak-preaidl` | byte-identical/redundant (== immutable stock) | **candidate-delete** | 135,915 |

**Caveat A (rows 3–4):** their content is duplicated only by the **live primary**
`android.jar`, which is legacy/unmarked (see §7) and whose 1,266 legacy entries are not
reproducible from immutable stock/AOSP inputs via the current frozen generator map. The
candidate-delete recommendation rests on the live primary remaining in place; any later
mutation/replacement of the live platform is itself an explicit, separately approved
action at which point legacy-content preservation can be reconsidered. If the user
prefers a frozen copy of the legacy live `android.jar` content to exist outside the
live platform, retain row 4 (row 3 is then still redundant, being a strict subset).

### Candidate-delete summary (advisory; nothing deleted)

```text
DELETED=0
CANDIDATE_DELETE=8 files, 163,149,374 bytes (~155.5 MiB)
RETAIN=1 file (android.jar.bak-20260813-210816, 44,848,587 bytes)
```

Exact candidate list: `android.jar.orig`, `android.jar.bak-20260821-011116`,
`android.jar.bak-20260821-013303`, `core-for-system-modules.jar.orig`,
`core-for-system-modules.jar.bak-20260813-210816`,
`core-for-system-modules.jar.bak-20260821-011116`,
`core-for-system-modules.jar.bak-20260821-013303`, `framework.aidl.bak-preaidl`.

## 7. Limitations and observations

- **Archive metadata vs content:** three backups (android `011116`/`013303` pair-wise
  content duplicates, and the two content-equal core `210816`/`011116` backups) are not
  byte-identical to their duplication targets — ZIP entry ordering, timestamps, and
  compression differ. Matching entry names alone was never treated as equivalence;
  every "equal" claim above compares per-entry bytes.
- **Live platform ownership:** the live `android-SysUISdk` contains no
  `.sysuisdk-generated.json` marker → **legacy/unmarked**, not generator-owned. Its
  `framework.aidl` is byte-identical to canonical and its
  `core-for-system-modules.jar` content-identical to canonical, but its `android.jar`
  content is a strict superset of canonical (1,266 legacy entries), so the live platform
  as a whole is not reproducible by the current generator.
- **Timeline note (mtimes vs backup-name timestamps):** backup names encode creation
  time while preserved mtimes encode the source's last-write time (e.g.
  `bak-20260821-011116` files carry 2026-08-13 21:08 mtimes; `bak-20260821-013303`
  files carry 01:10:2x mtimes that predate the live primaries' 01:32:0x mtimes). This is
  consistent with an mtime-preserving copy from a staged apply, but the exact legacy
  mechanics cannot be reconstructed from filesystem evidence alone; no claim is made.
- An `android-SysUISdk-staging` directory exists under `platforms/`; it is outside the
  frozen nine-file scope and was not inspected or touched.
- The audit itself cannot mutate the audited trees (hash/ZIP reads only); the
  before/after manifest equality in §8 provides the machine-checked proof.

## 8. No-mutation proof and repository scope

After-manifest regenerated with the identical script:

```text
BACKUPS=9
HASHED=9
MISSING=0
BACKUP_SET_UNCHANGED=true
```

`/tmp/task047-before.json` and `/tmp/task047-after.json` are byte-identical after JSON
normalization — all nine sizes, nanosecond mtimes, and SHA-256 values unchanged.
Stock `android-37.0` hashes equal the Task 045 recorded values (`06893f4a…`
android.jar), confirming the base platform was not modified. No Gradle task was run.

## 9. Verification log (actual commands and results)

```text
$ python3 /tmp/task047-inspect.py /tmp/task047-before.json
BACKUPS=9
HASHED=9
MISSING=0

$ python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp \
    --sdk-root /home/conv/Android/Sdk \
    --base-platform /home/conv/Android/Sdk/platforms/android-37.0 \
    --output /tmp/task047-generated/android-SysUISdk
SysUISdk composed: /tmp/task047-generated/android-SysUISdk
  base platform : android-37.0 (11382 files)
  AOSP inputs   : 8 (exact frozen map)
  bridge entries: 39 in both target jars
  generated     : 11381 files
(exit 0; marker present)

$ python3 /tmp/task047-inspect.py /tmp/task047-after.json
BACKUPS=9
HASHED=9
MISSING=0

$ python3 (normalized comparison of before/after manifests)
BACKUP_SET_UNCHANGED=true
BACKUPS=9
```
