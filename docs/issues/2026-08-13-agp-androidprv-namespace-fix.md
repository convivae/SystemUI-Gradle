# AGP androidprv namespace loss — build-logic repair

Date: 2026-08-13
Status: approved, implementation pending (brief 012)

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
| Brief 012 target | 0 `androidprv:` errors and `:app:processDebugResources` successful |

## Pending steps

1. Reproduce baseline and audit AGP 9.3.1 public APIs.
2. Prove one minimal build-intermediate repair.
3. Implement helper test-first and wire per variant.
4. Run clean resource-link acceptance and APK diagnostics.
