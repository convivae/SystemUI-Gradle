# Task 108 — C6 release closure (version metadata + static gates + manifest snapshot + release tag)

## Context

Dual-variant runtime verification (Tasks 103/104) is CLOSED and documented in
`docs/architecture/2026-09-06-fresh-instance-dual-variant-validation.md`.
Those validated APKs (Debug `e61d5485…` / Release `6d1d4254…`) carried the AGP
defaults `versionCode=-1` / `versionName=""`. This task adds proper version
metadata and ships the formal project release tag. Emulator is OFF — runtime
re-verification is NOT in scope; only build + static gates.

## Scope

1. Version declaration in `app/build.gradle.kts` defaultConfig:
   `versionCode = 37`, `versionName = "17"` — mirroring AOSP (SystemUI's
   version follows the platform: `ro.build.version.sdk=37` / platform 17,
   confirmed from `out/target/product/emu64x/system/build.prop` of this same
   tree; baseline `android-17.0.0_r1`), with a provenance comment.
2. Rebuild both variants (`:app:assembleDebug`; `:app:clean :app:assembleRelease`),
   stop Gradle daemons afterwards.
3. Static gate on the Release APK:
   `uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/release/app-release.apk` (must PASS).
4. Verify version landed in `output-metadata.json` (expect 37 / "17").
5. Manifest snapshots into `docs/release-manifest/` (debug/release
   `AndroidManifest.xml` from `packaged_manifests` intermediates) + README
   with APK SHA-256s and provenance; explicitly state that the new SHAs differ
   from the previously validated APKs only because of the version metadata change.
6. Local annotated tag `v1.0.0-android-17.0.0_r1` on the final commit
   (first formal release; AOSP SystemUI android-17.0.0_r1 as standalone Gradle
   build; dual-variant runtime verified on same-tree emulator; versionName 17 /
   versionCode 37). NO push, NO GitHub Release (Chief handles publication).
7. ADR 0007 closure note (date, tag, what remains open).
8. Docs sync: CURRENT_STATE / PLAN / HANDOFF / orchestration STATE + log.

## Boundaries

- No push. No GitHub Release creation. No emulator/ADB work.
- Local commits split sensibly; tag created on the last commit.

## Result

**C6_RELEASE_CLOSURE_PASS** — all scope items executed:

| Item | Result |
|---|---|
| Version declaration | ✅ `versionCode = 37`, `versionName = "17"` + provenance comment in `app/build.gradle.kts` |
| Provenance | ✅ same-tree `out/target/product/emu64x/system/build.prop`: `ro.build.version.sdk=37`, `ro.build.version.release=17` |
| Debug build | ✅ `:app:assembleDebug` BUILD SUCCESSFUL; APK `e7277867695b85098bee5d3bba06732371ff708471d332e807e5ff08b3a45abd` |
| Release build | ✅ `:app:clean :app:assembleRelease` BUILD SUCCESSFUL; APK `48ade522827b2e9450b800b47b38253d74577eec828f85058bcee8c33104f913`; daemons stopped |
| Static gate (Release) | ✅ `RESULT=PASS` — 2 DEX, 22,454 classes, 3,384,058 refs, 0 old-owner violations, 0 hidden-target definitions |
| Version landed | ✅ `output-metadata.json`: `versionCode: 37`, `versionName: "17"`; aapt badging confirms `versionCode='37' versionName='17'` on both APKs |
| Manifest snapshots | ✅ `docs/release-manifest/{debug,release}-AndroidManifest.xml` (1281/1280 lines) + README with SHAs and provenance |
| Release tag | ✅ annotated local tag `v1.0.0-android-17.0.0_r1`, NOT pushed |
| ADR 0007 | ✅ closure note appended |
| Docs sync | ✅ CURRENT_STATE / PLAN / HANDOFF / STATE.md / log.md updated |

Process note: `:app:clean` before `assembleRelease` wiped the debug APK and its
packaged-manifest intermediate; a post-release `:app:assembleDebug` re-run
restored the debug outputs (release APK SHA verified unchanged before and after).

New APK SHAs differ from the runtime-validated `e61d5485…`/`6d1d4254…` solely
because of the version metadata (previously AGP defaults); runtime behavior is
inherited from the 2026-09-06 dual-variant validation. Emulator was OFF; no
runtime re-verification was performed.
