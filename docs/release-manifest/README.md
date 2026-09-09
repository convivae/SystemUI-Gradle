# Release manifest snapshots (v1.0.0-android-17.0.0_r1)

Binary packaged manifests of the tagged release APKs, snapshotted for
traceability of what the manifest merger + APK packager actually produced.

| File | Variant | APK SHA-256 |
|------|---------|-------------|
| `debug-AndroidManifest.xml` | Debug | `e7277867695b85098bee5d3bba06732371ff708471d332e807e5ff08b3a45abd` |
| `release-AndroidManifest.xml` | Release | `48ade522827b2e9450b800b47b38253d74577eec828f85058bcee8c33104f913` |

Both APKs carry `versionCode=37` / `versionName="17"` (AOSP platform provenance:
`ro.build.version.sdk=37`, platform 17, baseline `android-17.0.0_r1`).

**Note:** these SHAs differ from the previously runtime-validated APKs
(Debug `e61d5485…` / Release `6d1d4254…` in
`docs/architecture/2026-09-06-fresh-instance-dual-variant-validation.md`)
because this release adds the version metadata that those builds left at the
AGP defaults (`versionCode=-1` / `versionName=""`). No other source change.

## Provenance

Source commit: the `v1.0.0-android-17.0.0_r1` tag.

Generation path (AGP build intermediates):

```
app/build/intermediates/packaged_manifests/debug/processDebugManifestForPackage/AndroidManifest.xml
app/build/intermediates/packaged_manifests/release/processReleaseManifestForPackage/AndroidManifest.xml
```

Commands: `./gradlew :app:assembleDebug` and
`./gradlew :app:clean :app:assembleRelease` (plus an `:app:assembleDebug`
re-run after the clean to restore the debug outputs).
