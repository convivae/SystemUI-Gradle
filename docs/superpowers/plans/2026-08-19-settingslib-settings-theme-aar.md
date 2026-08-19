# SettingsLibSettingsTheme AAR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the complete AOSP `SettingsLibSettingsTheme` resource target as a deterministic local-Maven AAR and wire it into `:SystemUI-res` so the two missing switch drawables resolve.

**Architecture:** Preserve the real Soong target boundary instead of merging two raw resource roots with 89 duplicate paths. Build a res-only AAR from the untouched SettingsTheme tree, install it through the existing local Maven mechanism, and declare it explicitly at the resource-owning Gradle module.

**Tech Stack:** Python 3 `unittest`/`zipfile`, deterministic AAR packaging, local Maven AAR, Gradle Kotlin DSL, AGP 9.3.1/AAPT2.

**Spec:** `docs/issues/2026-08-19-settingslib-settings-theme-aar.md`

## Global Constraints

- No edits to `SystemUI-*/src/**`, `SystemUI-*/res*/**`, or any AOSP file.
- Copy all SettingsTheme resource files byte-for-byte; do not merge, rewrite, generate, or select only the currently failing files.
- Add no stub, suppression, source exclusion, version upgrade, module, or build bypass.
- Use the fixed local coordinate `com.android.systemui:SettingsLibSettingsTheme:1.0.0`.
- The user's 2026-08-19 approval covers the new catalog alias and tracked AAR/Maven artifact, but no other catalog/version change.
- Worker commits in English and never pushes.

---

### Task 1: Add the res-only artifact test-first

**Files:**
- Modify: `tools/tests/test_package_aosp_aar.py`
- Modify: `tools/tests/test_install_aar_to_maven.py`
- Modify: `tools/package_aosp_aar.py`
- Modify: `tools/install_aar_to_maven.py`

**Interfaces:**
- Consumes: existing `CONFIGS`, `build_artifact()`, `assemble_aar()`, and `ARTIFACTS` registries.
- Produces: `CONFIGS["SettingsLibSettingsTheme"]` and `ARTIFACTS["SettingsLibSettingsTheme"]`.

- [ ] **Step 1: Write failing config and provenance tests**

Add tests asserting:

```python
cfg = paar.CONFIGS["SettingsLibSettingsTheme"]
self.assertEqual(cfg["code"], [])
self.assertIn("SettingsLib/SettingsTheme/res", str(cfg["res"]))
self.assertTrue(str(cfg["manifest"]).endswith("SettingsTheme/AndroidManifest.xml"))
self.assertIn("SettingsLibSettingsTheme/android_common/R.txt", str(cfg["rtxt"]))
self.assertEqual(cfg["output"], "libs/aars/SettingsLibSettingsTheme.aar")
```

Build the artifact into a temporary path, compare the complete `res/**` entry set to the AOSP source tree, and assert every entry's bytes equal the corresponding source file. Assert the v31 thumb/track and v34 track entries explicitly.

Add an installer test asserting:

```python
self.assertEqual(
    iam.ARTIFACTS["SettingsLibSettingsTheme"],
    {"group": "com.android.systemui", "name": "SettingsLibSettingsTheme", "version": "1.0.0"},
)
```

Update the exact `CONFIGS` set expectation to include `SettingsLibSettingsTheme`.

- [ ] **Step 2: Run RED tests**

Run:

```bash
python3 -m unittest tools.tests.test_package_aosp_aar tools.tests.test_install_aar_to_maven
```

Expected: failures caused only by missing `SettingsLibSettingsTheme` registry entries.

- [ ] **Step 3: Add the minimal deterministic config**

Add to `CONFIGS`:

```python
"SettingsLibSettingsTheme": {
    "code": [],
    "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/SettingsTheme/res"],
    "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/SettingsTheme/AndroidManifest.xml",
    "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsTheme/SettingsLibSettingsTheme/android_common/R.txt",
    "output": "libs/aars/SettingsLibSettingsTheme.aar",
},
```

Register the exact Maven coordinate in `ARTIFACTS`. Do not special-case copying or weaken duplicate-resource checks.

- [ ] **Step 4: Run focused GREEN tests**

Run the same focused unittest command. Expected: exit 0 and `OK`.

### Task 2: Generate and wire the tracked artifact

**Files:**
- Create: `libs/aars/SettingsLibSettingsTheme.aar`
- Create: `libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0/SettingsLibSettingsTheme-1.0.0.aar`
- Create: `libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0/SettingsLibSettingsTheme-1.0.0.pom`
- Modify: `gradle/libs.versions.toml`
- Modify: `SystemUI-res/build.gradle.kts`

**Interfaces:**
- Consumes: Task 1's artifact registries.
- Produces: `libs.systemui.settingslib.theme` catalog accessor and resources visible to `:SystemUI-res` consumers.

- [ ] **Step 1: Generate and install only the new artifact**

Run:

```bash
python3 tools/package_aosp_aar.py SettingsLibSettingsTheme
python3 tools/install_aar_to_maven.py SettingsLibSettingsTheme
```

Expected: one direct AAR and one local Maven AAR/POM at the paths above.

- [ ] **Step 2: Verify artifact provenance before Gradle wiring**

Use Python/zipfile to assert the AAR's `res/**` set exactly matches all files below AOSP `SettingsTheme/res`, bytes included. Run `sha256sum` and require the direct and Maven AAR hashes to be identical. Verify the three switch entries exist.

- [ ] **Step 3: Add the fixed catalog alias and resource-owner dependency**

Add exactly:

```toml
systemui-settingslib-theme = { group = "com.android.systemui", name = "SettingsLibSettingsTheme", version = "1.0.0" }
```

In `SystemUI-res/build.gradle.kts`, adjacent to the existing SettingsLib dependency, add:

```kotlin
api(libs.systemui.settingslib.theme)
```

Do not change any existing coordinate or version.

- [ ] **Step 4: Run the complete Python suite**

Run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: more than 131 tests, exit 0, final `OK`.

- [ ] **Step 5: Run clean resource-link acceptance**

Run:

```bash
./gradlew :app:clean :app:processDebugResources --console=plain 2>&1 | tee /tmp/task013.log
```

Expected: exit 0, output contains `BUILD SUCCESSFUL`, helper reports `unresolved=0`, and:

```bash
grep -cE 'settingslib_switch_(track|thumb).*not found' /tmp/task013.log
# 0
```

If a new failure layer appears after both switch errors reach zero, record the first failing task and first error group in the issue and halt rather than broadening scope.

- [ ] **Step 6: Run APK diagnostic only after Step 5 passes**

Run:

```bash
./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/task013-app.log
```

Record the real result. If an APK is produced, record its path, size, and SHA-256. If not, record only the first new failing task/error group.

- [ ] **Step 7: Update documentation and commit**

Update `docs/issues/2026-08-19-settingslib-settings-theme-aar.md` with commands, counts, hashes, and real build results. Tick every plan and brief checkbox. Run `git diff --check`, then commit in English without pushing:

```bash
git commit -m "build: package SettingsLib settings theme resources"
```
