# AGP androidprv namespace loss — build-logic repair

Date: 2026-08-13
Status: implemented on task-012 (2026-08-19); androidprv goal met (0 errors);
new latent layer (SettingsLib AAR missing drawables) escalated as REDLINE —
see `docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md` §5

## Background

Task 011 made the SysUISdk reproducible and overlaid the current AOSP
`framework-res.apk` resources into its `android.jar`. The private framework
symbols now exist and resolve in isolated AAPT2 tests, but
`:app:processDebugResources` still reports 20 `androidprv:` errors.

Systematic debugging established the remaining root cause: AGP 9.3.1
`MergeResources` reserializes values resources and drops
`xmlns:androidprv="http://schemas.android.com/apk/prv/res/android"` because the
prefix occurs only inside `name="androidprv:..."` values. The merged XML retains
81 `androidprv:` references but no matching declaration. AAPT2 Variant C fails
without the declaration; Variants D/E succeed with it against the S4 SDK.
Full evidence is in:

- `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md` §8.2
- `docs/issues/2026-08-13-sysuisdk-reproducible-build.md` §8.4

## Approved direction

The user approved the architect's recommendation on 2026-08-13: investigate
and implement a build-logic repair without modifying AOSP mirrored resources.
The worker must first audit AGP's public artifact API. If no transformable
merged-resource artifact exists, the approved fallback is a deterministic
post-merge/pre-link recompilation of only affected values flats, using AGP's
own `SdkComponents.aapt2` provider.

## Guardrails

- No `SystemUI-*/res*` or source changes.
- No fabricated source resource.
- No version/catalog/Gradle property change.
- If a build-only repair cannot be demonstrated, stop with `REDLINE:`.
- Baseline and post-fix command output must be recorded truthfully.

## Error evolution

| Checkpoint | Result |
|---|---|
| Before S4 | 20 `androidprv:` link errors (stale table + namespace loss) |
| After S4 | 20 `androidprv:` link errors; isolated AAPT2 proves resource table fixed |
| Brief 012 baseline (2026-08-19) | `BUILD FAILED`, 20 `androidprv` hits (`/tmp/task012-before.log`) |
| After task 012 implementation | `scanned=419 patched=8 compiled=8 unresolved=0`; **0 `androidprv` errors**; link now fails only on pre-existing masked layer `drawable/settingslib_switch_{track,thumb} not found` (missing from tracked SettingsLib AAR; defined in AOSP `SettingsLib/SettingsTheme/res/drawable-v31/`) |
| `:app:assembleDebug` diagnostics | `BUILD FAILED` at the same `processDebugResources` (settingslib layer); no APK produced |

## Task 012 command evidence (2026-08-19)

```
$ ./gradlew :app:processDebugResources --console=plain   # baseline
BUILD FAILED in 18s ; grep -c androidprv -> 20

$ python3 -m unittest discover -s tools/tests -p 'test_*.py'
Ran 131 tests in 17.654s   OK      (was 116; +15 helper tests, RED-verified first)

$ ./gradlew :app:clean :app:processDebugResources --console=plain
scanned=419 patched=8 compiled=8 unresolved=0
BUILD FAILED in 5s ; grep -c androidprv -> 0
  values/values.xml:15398: drawable/settingslib_switch_track not found  (new layer)
  values/values.xml:15399: drawable/settingslib_switch_thumb not found (new layer)

$ ./gradlew :app:assembleDebug --console=plain
BUILD FAILED in 11s ; same layer; no APK
```

## Pending steps

1. ~~Reproduce baseline and audit AGP 9.3.1 public APIs.~~ (done — no public
   merged-res artifact; `SdkComponents.aapt2` public and used)
2. ~~Prove one minimal build-intermediate repair.~~ (done — see §4.1 of the
   architecture doc)
3. ~~Implement helper test-first and wire per variant.~~ (done — 15 new tests,
   131 total OK; `merge → patch → process` wired in `app/build.gradle.kts`)
4. ~~Run clean resource-link acceptance and APK diagnostics.~~ (done —
   androidprv 0 achieved; build blocked by the settingslib layer below)
5. **NEW (escalated REDLINE)**: SettingsLib AAR lacks
   `settingslib_switch_{track,thumb}` (AOSP `SettingsLib/SettingsTheme/res/drawable-v31/`)
   → re-package SettingsLib AAR to include SettingsTheme res. Outside task-012
   Allowed Paths (dependency artifact change); awaiting architect/user decision.
