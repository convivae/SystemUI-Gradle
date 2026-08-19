# Task 013 — Package SettingsLibSettingsTheme resources

**Authority:** `redline-gated`, with explicit user pre-approval dated 2026-08-19 for the exact new AOSP SettingsTheme AAR, fixed `1.0.0` catalog alias, local Maven copy, and `:SystemUI-res` dependency described below. No other red-line change is approved.

**Reports To:** chief architect in the main herdr session.

**Plan:** `docs/superpowers/plans/2026-08-19-settingslib-settings-theme-aar.md`

**Issue/Spec:** `docs/issues/2026-08-19-settingslib-settings-theme-aar.md`

## Goal

Package the real AOSP `SettingsLibSettingsTheme` Soong target as an independent deterministic res-only AAR and make its untouched resources visible to `:SystemUI-res`, resolving the missing switch track/thumb resources without merging or rewriting raw XML.

## Allowed Paths

- `tools/package_aosp_aar.py`
- `tools/install_aar_to_maven.py`
- `tools/tests/test_package_aosp_aar.py`
- `tools/tests/test_install_aar_to_maven.py`
- `libs/aars/SettingsLibSettingsTheme.aar`
- `libs/maven/com/android/systemui/SettingsLibSettingsTheme/**`
- `gradle/libs.versions.toml` — only one new `systemui-settingslib-theme` alias at version `1.0.0`; no existing line may change
- `SystemUI-res/build.gradle.kts` — only the corresponding `api(...)` dependency and explanatory comment
- `docs/issues/2026-08-19-settingslib-settings-theme-aar.md`
- `docs/superpowers/plans/2026-08-19-settingslib-settings-theme-aar.md`
- `docs/orchestration/tasks/013-settingslib-settings-theme-aar.md`

## Forbidden Paths

- every `SystemUI-*/src/**` and `SystemUI-*/res*/**`
- every AOSP file under `/home/conv/myspace/aosp/`
- existing AAR/Maven artifacts, including `SettingsLib.aar`
- `AGENTS.md`, `docs/adr/**`, `docs/orchestration/CHARTER.md`
- `settings.gradle.kts`, `gradle.properties`, `buildSrc/**`
- module include list, dependency versions, existing catalog aliases
- stubs, suppressions, source exclusions, generated resource source files, build bypasses

## Mandatory Method

- Invoke `worker-contract`, then `systematic-debugging` and `test-driven-development`.
- Preserve the separate Soong target because `SettingsLib/res` and `SettingsTheme/res` contain 89 duplicate relative paths; never merge or overlay those raw trees.
- Package the **complete** SettingsTheme `res/**` tree byte-for-byte, not only the three currently needed drawable variants.
- RED-test registry and full resource provenance before implementation.
- Generate/install only `SettingsLibSettingsTheme`; do not rebuild unrelated artifacts.
- Commit in English; never push.

## Acceptance

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: more than 131 tests, exit 0, final `OK`.

```bash
./gradlew :app:clean :app:processDebugResources --console=plain 2>&1 | tee /tmp/task013.log
```

Expected: exit 0; output contains `BUILD SUCCESSFUL`; androidprv helper includes `unresolved=0`; `grep -cE 'settingslib_switch_(track|thumb).*not found' /tmp/task013.log` prints `0`.

Also prove:

- direct AAR `res/**` file set and bytes equal AOSP SettingsTheme `res/**` exactly;
- direct and Maven AAR SHA-256 are identical;
- no Forbidden Path changed;
- `git diff --check` has no output.

After resource acceptance passes, run `:app:assembleDebug` diagnostically and report the real APK result. A new layer is not permission to modify files outside this brief.

## Checklist

- [ ] CONTRACT printed and model verified by architect
- [ ] RED tests observed for absent config/coordinate
- [ ] complete res-only AAR config and Maven coordinate implemented
- [ ] focused tests GREEN
- [ ] artifact generated, installed, and provenance verified
- [ ] catalog alias and `:SystemUI-res` dependency added exactly
- [ ] full Python suite passes (>131)
- [ ] clean resource-link acceptance run and recorded truthfully
- [ ] APK diagnostic run only if resource link passes
- [ ] issue updated with errors/hashes/results
- [ ] `git diff --check` clean
- [ ] English commit created; no push
- [ ] terminal-final `HANDOFF:` printed
