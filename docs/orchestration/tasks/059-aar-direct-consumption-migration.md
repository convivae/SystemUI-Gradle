# Task 059 — 4 single-consumer AAR families: local Maven → direct AAR (user decision 2026-08-25)

## Context

Task 043 audit (`docs/architecture/2026-08-21-gradle-native-current-state-audit.md` §10)
produced 8 NOT APPROVED packets. The user has now decided on 4 of them:

| Packet | Decision |
|---|---|
| WifiTrackerLib local-Maven delivery | **Migrate to direct AAR** |
| iconloader local-Maven delivery | **Migrate to direct AAR** |
| setupcompat local-Maven delivery | **Migrate to direct AAR** |
| LowLightDreamLib local-Maven delivery | **Migrate to direct AAR** |
| animationlib local-Maven delivery | **KEEP local Maven** (multi-module sharing; catalog alias is the standard Gradle mechanism) — close packet as "kept by design" |
| SettingsLib family delivery (umbrella AAR experiment) | **PERMANENTLY CLOSED** — 17 per-target AARs stay; experiment will not be run |
| AssumeTrueForR8 | stays NOT APPROVED (Release phase) |
| tracinglib-platform.jar | deferred to Release phase (user decision) |

The 4 migrating families are all single-artifact, single-consumer (`:SystemUI-core`
only), skeleton-POM, byte-identical between `libs/maven/...` and `libs/aars/`.
Migration changes only Gradle metadata resolution, not bytes.

## Work items

### 1. AGENTS.md §3.2 rule 2 amendment

Current rule 2 ends with: "在 `libs.versions.toml` 声明 catalog alias 统一管理；
build.gradle.kts 中不得直接 `files("libs/aars/xxx.aar")`。"

Amend to carve out the user-approved exception: single-artifact, single-consumer
families may be consumed directly from `libs/aars/` via `files(...)`; the local-Maven
path remains for multi-consumer families and any family with demonstrated
resource/dependency conflicts. List the four migrated families as the current
direct-consumption set. Note this was user-approved 2026-08-25 (Task 059, closing
4 of the Task 043 packets).

### 2. Wiring migration (SystemUI-core/build.gradle.kts)

- setupcompat (line ~221): `implementation(libs.systemui.setupcompat)` →
  `implementation(files("${rootProject.projectDir}/libs/aars/setupcompat.aar"))`
- iconloader (line ~222): `implementation(libs.systemui.iconloader)` →
  `implementation(files("${rootProject.projectDir}/libs/aars/iconloader.aar"))`
- WifiTrackerLib (line ~247): `implementation(libs.systemui.wifitrackerlib)` →
  `implementation(files("${rootProject.projectDir}/libs/aars/WifiTrackerLib.aar"))`
- LowLightDreamLib (line ~230): `implementation(libs.systemui.lowlight.dream.lib)` →
  `implementation(files("${rootProject.projectDir}/libs/aars/LowLightDreamLib.aar"))`

Update the adjacent Chinese comments to say "直接 AAR（libs/aars/，单 consumer 族，task 059）"
instead of "经本地 Maven 交付". Do NOT touch animationlib / SettingsLib / wmshell / other
catalog aliases.

### 3. Catalog + Maven retirement

- Remove 4 aliases from `gradle/libs.versions.toml`:
  `systemui-wifitrackerlib` (154), `systemui-iconloader` (158),
  `systemui-lowlight-dream-lib` (159), `systemui-setupcompat` (183).
- `git rm -r` the 4 local Maven trees:
  `libs/maven/com/android/systemui/WifiTrackerLib/`,
  `libs/maven/com/android/systemui/iconloader/`,
  `libs/maven/com/android/systemui/setupcompat/`,
  `libs/maven/com/android/systemui/LowLightDreamLib/`.
- Keep `libs/aars/*.aar` sources untouched (they are now the direct inputs).
- `tools/install_aar_to_maven.py` + tests: these four remain valid installs in general;
  do not modify the tool. Only the catalog/wiring changes.

### 4. Task 043 packet closure documentation

In `docs/architecture/2026-08-21-gradle-native-current-state-audit.md` §10, annotate
each of the 6 resolved packets (the 4 migrations + animationlib keep + SettingsLib
permanent close) with a short `> RESOLVED 2026-08-25 (task 059, user decision): ...`
line. Leave AssumeTrueForR8 and tracinglib-platform packets unchanged except adding
`> DEFERRED to Release phase (user decision 2026-08-25, task 059)` to the tracinglib
packet.

### 5. Verification (must pass)

1. `./gradlew :app:checkDebugDuplicateClasses` — green.
2. `./gradlew :app:assembleDebug` — green; record new APK sha256 and compare with
   baseline `b827df78a9f1e62061a7ea337e57e75861c168e8d665b0823e99af08ef088779`.
   Byte-identical is expected (same bytes through a different resolution path); if NOT
   identical, diff the APK (unzip + compare res/dex/manifest entries) and explain why —
   resource-link order changes are acceptable if content sets are identical, but must be
   evidenced.
3. `uv run pytest tools/tests/ -q` — green (no test changes expected).
4. `grep -rn "libs.systemui.wifitrackerlib\|libs.systemui.iconloader\|libs.systemui.setupcompat\|libs.systemui.lowlight" --include="*.kts" --include="*.toml"` → zero hits.
5. Confirm device state untouched (no redeploy needed if APK identical; if APK differs,
   redeploy to emulator-5554 using the task054 staging procedure and confirm PID stable
   3 min, zero NCDFE).

### 6. Docs & commits

- Report: `docs/issues/2026-08-25-aar-direct-consumption-migration.md` (rules D/I).
- Sync `docs/CURRENT_STATE.md` (dependency state: 4 families now direct AAR; 6 of 8
  task-043 packets resolved) + `docs/orchestration/STATE.md` + `log.md`.
- Commits (English, local, do NOT push):
  1. `refactor(deps): migrate 4 single-consumer AAR families to direct consumption (task 059)`
     (AGENTS.md amendment + wiring + catalog + maven retirement + audit annotations)
  2. `docs: task 059 orchestration state` (if STATE/log changes warrant a separate commit)

## Constraints

- Do NOT touch: `libs/aars/*.aar` bytes, `tools/install_aar_to_maven.py`, animationlib /
  SettingsLib / wmshell / other aliases, AOSP tree, emulator beyond verification.
- Python via `uv run` only.
- If `checkDebugDuplicateClasses` or resource linking fails, STOP and report —
  do not invent workarounds.

## Reports to

Chief (this pane). When done: `TASK059_REPORT=...` summary. If blocked: stop and message.
