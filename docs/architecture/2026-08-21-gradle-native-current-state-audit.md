# Gradle-native Current-State Architecture Audit

## 1. Method, baseline, and evidence boundary

- Dispatch checkout: `67fe3284f3b058c40b963c58eff931d83c0e85d7` (worktree `/home/conv/myspace/SystemUI-Gradle-wt-043`),
  clean at start. Fixed ancestry gate `git merge-base --is-ancestor 72970b84 HEAD` exited 0.
- AOSP tree: `/home/conv/myspace/aosp`; reference project: `/home/conv/myspace/CarSystemUIGradle` (comparison only,
  not normative). Audit date 2026-08-21.
- Baseline artifact counts verified: 29 `libs/aars/*.aar`, 27 `libs/maven/**/*.aar`, 28 root `libs/*.jar`,
  1 `libs/prebuilts/**/*.jar`.
- Non-goals: no Git history consultation, no implementation, no rollback, no Gradle/build/AGP/SDK/packaging
  command, no rule/policy-file modification. Every substantive claim below cites a present `path:line`, an exact
  artifact path plus inventory fact, or a recorded read-only command output.
- `Git history consulted: NO`. `Gradle: NOT RUN (read-only audit boundary)`.
- Deliverable per approved spec §11.1: a keep / simplify / consolidate / candidate rollback / needs experiment /
  needs history/context ledger. No recommendation in this report is approved for implementation.

## 2. Current Gradle module seams

13 modules are included by `settings.gradle.kts:25-37` (`include(":app")` … `include(":SystemUI-compose")`).
AOSP semantic owners are defined in `frameworks/base/packages/SystemUI/Android.bp` (`android_library
"SystemUI-res"` at bp:404-422, `android_library "SystemUI-core"` at bp:423-553, `android_app "SystemUI"` at
bp:958-985) and per-subdir `Android.bp` files (`common/Android.bp:26 "SystemUICommon"`, `log/Android.bp:26
"SystemUILogLib"`, `animation/Android.bp:27 "PlatformAnimationLib"`, `plugin/Android.bp:26
"SystemUIPluginLib"`, `plugin_core/Android.bp:48 "PluginCoreLib"`, `customization/Android.bp:26
"SystemUICustomizationLib"`, `shared/Android.bp:44 "SystemUISharedLib"`, `unfold/Android.bp:26
"SystemUIUnfoldLib"`, `compose/core/Android.bp:26 "PlatformComposeCore"`, `compose/scene/Android.bp:33
"PlatformComposeSceneTransitionLayout"`). All 13 modules are `keep` (deep-module test below).

| Module | Namespace / seam evidence | Deep-module analysis (interface / hidden complexity / leverage / deletion test) | Recommendation |
|---|---|---|---|
| `:app` | `app/build.gradle.kts:32` `namespace = "com.android.systemui.app"`; APK producer, mirrors bp `android_app "SystemUI"` (static_libs `SystemUI-core` only, dependencies block `app/build.gradle.kts:120-136`) | Interface: manifest+signing+R8 config. Hides: platform keystore, androidprv merged-resource repair task (app/build.gradle.kts:74-117), aapt2 feature-flag. Deletion test: merging into `:SystemUI-core` would destroy the bp app/library seam (ADR 0003) | keep |
| `:SystemUI-core` | `SystemUI-core/build.gradle.kts:23` `namespace = "com.android.systemui"`; java/kotlin srcDirs `src`, `src-debug`, `src-release` (lines 41-68), aidl `src` (line 56); mirrors bp `SystemUI-core` glob `src/**/*.kt|java`, `src/**/I*.aidl` (bp:425-434) | Interface: single `implementation(project(...))` edge consumed by `:app`. Hides: entry classes, pods, KSP Dagger/Room (lines 2-5). Deletion test: entry classes must stay here per AGENTS.md §1.9 (bp glob) | keep |
| `:SystemUI-res` | `SystemUI-res/build.gradle.kts:8` `namespace = "com.android.systemui.res"`; `res.srcDirs("res-product","res-keyguard","res")` (line 18) mirrors bp `SystemUI-res` resource_dirs (bp:404-412) | Interface: one R namespace (`com.android.systemui.res.R`) used by 959 source files (build.gradle.kts:2 comment). Leverage: one module owns all SystemUI res. Deletion test: folding res into core breaks the independent namespace required by explicit imports | keep |
| `:SystemUI-common` | `SystemUI-common/build.gradle.kts:3` `org.jetbrains.kotlin.jvm`; merges Common+Log+shared-utils per ADR 0003 | Interface: JVM annotations/utilities, `api(libs.kotlinx.coroutines.core)` (line 41). Deletion test: merging into core would push JVM-only code under AGP variant machinery for no gain | keep |
| `:SystemUI-animation` | `SystemUI-animation/build.gradle.kts:6` `namespace = "com.android.systemui.animation"`; res srcDirs (line 18); merges PlatformAnimationLib+Shader | Interface: animation API + own res. Deletion test: project-module consumers are `:SystemUI-core` (`SystemUI-core/build.gradle.kts:122`), `:SystemUI-customization` (`:55`), `:SystemUI-plugin` (`:60`), `:SystemUI-shared` (`:57`), `:SystemUI-compose` (`:58`), which rely on its `api(libs.systemui.animationlib)` (line 54) edge | keep |
| `:SystemUI-plugin-core` | `SystemUI-plugin-core/build.gradle.kts:4` JVM; mirrors bp `plugin_core/Android.bp:48` (JVM target) | Interface: plugin annotation API consumed at compile time; also exports `proguard.flags` consumed by `:app` (app/build.gradle.kts:56,67). Deletion test: separating JVM runtime API from the Android plugin lib is a real toolchain seam (ADR 0003) | keep |
| `:SystemUI-plugin-processor` | `SystemUI-plugin-processor/build.gradle.kts:27` `implementation(project(":SystemUI-plugin-core"))`; build-time annotation processor | Interface: processor only; does not enter the APK runtime graph (ADR 0003). Deletion test: inlining into plugin-core would force the processor onto the runtime classpath | keep |
| `:SystemUI-plugin` | `SystemUI-plugin/build.gradle.kts:10` `namespace = "com.android.systemui.plugin"`; srcDirs `src`, `bcsmartspace/src` (lines 23-24); `consumerProguardFiles("proguard_plugins.flags")` (line 18) mirrors bp `export_proguard_flags_files` | Interface: plugin runtime lib + exported consumer R8 rules. Deletion test: bcsmartspace source ownership and the consumer-rule export both anchor this seam | keep |
| `:SystemUI-unfold` | `SystemUI-unfold/build.gradle.kts:7` `namespace = "com.android.systemui.unfold"`; aidl srcDirs (line 19); `ksp(libs.dagger.compiler)` (line 60) | Interface: unfold progress API. Hidden: own KSP/Dagger graph. Deletion test: merging would entangle a small independent Dagger component into core's | keep |
| `:SystemUI-customization` | `SystemUI-customization/build.gradle.kts:6` `namespace = "com.android.systemui.customization"`; res+aidl srcDirs (lines 18-19) | Interface: customization API with res. Deletion test: independent res owner and external consumers (bp `SystemUICustomizationLib`) | keep |
| `:SystemUI-shared` | `SystemUI-shared/build.gradle.kts:7` `namespace = "com.android.systemui.shared"`; srcDirs `src`, `keyguard/src` (lines 17-20); KSP Dagger (line 81) | Interface: shared+keyguard AIDL/API surface consumed across modules. Deletion test: largest AIDL owner; merging into core would break the shared-library seam Settings also consumes | keep |
| `:SystemUI-shared-biometrics` | `SystemUI-shared-biometrics/build.gradle.kts:7` `namespace = "com.android.systemui.shared.biometrics"`; own res (line 18) | Interface: independent R namespace consumed externally by Settings (module header comment lines 1-2). Deletion test: namespace isolation for an external consumer is a demonstrated constraint | keep |
| `:SystemUI-compose` | `SystemUI-compose/build.gradle.kts:9` `namespace = "com.android.compose"`; srcDirs `core/src`, `scene/src` (lines 18-19); Compose compiler plugin | Interface: PlatformComposeCore+Scene merged (ADR 0003). Deletion test: distinct Compose toolchain needs (compiler plugin, Compose deps) justify the seam | keep |

Topology-level row: the 13-module set itself matches the approved spec §5.1 ("retained unless a later
separately approved review finds a concrete problem"); no current-state seam problem is demonstrated — **keep**.

## 3. Complete local artifact inventory

All counts verified against the fixed baseline: 29 source AARs, 27 local Maven AARs, 28 root JARs, 1 prebuilt JAR.
SHA column is the full 64-hex SHA-256 digest; sizes in bytes; classes = `.class` entries in the AAR
`classes.jar` (or JAR); res = resource-file entries; POM deps = `<dependency>` elements in the installed POM.
Facts collected read-only with `zipinfo`/`unzip -l`/`sha256sum` into `/tmp/task043-inventory/`.

### 3.1 Source AARs (`libs/aars/`) — 29

| Path | Family | Size | SHA-256 | Classes | Res files | Manifest | Delivery role |
|---|---|---|---|---|---|---|---|
| `libs/aars/LowLightDreamLib.aar` | LowLightDreamLib | 28914 | `2a7b0939611434b6c3cbeab7739307363692997ec13a71ce24d3a9a717f7c0f8` | 24 | 1 | yes | source AAR |
| `libs/aars/SettingsLib.aar` | SettingsLib | 4797541 | `61b480f284ae7eefd194412cf2dde8c7ad55675f8275f32cd6654278d8a2bd04` | 1153 | 365 | yes | source AAR |
| `libs/aars/SettingsLibActionButtonsPreference.aar` | SettingsLib | 12524 | `dd481d9f07039cf161f52809a6e7ea5a87acd72e4c67ab96aa4476866379266b` | 0 | 15 | yes | source AAR |
| `libs/aars/SettingsLibAdaptiveIcon.aar` | SettingsLib | 2922 | `6f2df660d20d5cc642dce2200faa5ddb85e0076c920365ec74aa46f659af2eb6` | 0 | 3 | yes | source AAR |
| `libs/aars/SettingsLibAppPreference.aar` | SettingsLib | 67135 | `2110852a0fee594121a8cca7e0057d421d1903e8895ead9ca6bd094c10cbbaec` | 0 | 91 | yes | source AAR |
| `libs/aars/SettingsLibBannerMessagePreference.aar` | SettingsLib | 70129 | `7beca439ac32c2b6a3f4e8be1edf185ca65ede0ab0ada5700fea17c7a874454c` | 0 | 96 | yes | source AAR |
| `libs/aars/SettingsLibBarChartPreference.aar` | SettingsLib | 5789 | `4624cf0e4c30921ac31f454c1e6b0bb17ce80df4d47fd6cfd61da938f194281e` | 0 | 6 | yes | source AAR |
| `libs/aars/SettingsLibButtonPreference.aar` | SettingsLib | 18790 | `2801c41c071c9d4bb07578e4518ac89bd493e049e546f38546c61ba9c3939452` | 0 | 23 | yes | source AAR |
| `libs/aars/SettingsLibColor.aar` | SettingsLib | 2033 | `41a8d422ea3e78837378c7b5f2f4ba7e4814983dd2f273eac3861d3dd6f2bd16` | 0 | 1 | yes | source AAR |
| `libs/aars/SettingsLibFooterPreference.aar` | SettingsLib | 66912 | `2a631f84d9c622775296e45b0911ee2dea49c8d318642b916ce3f7a1636f8c59` | 0 | 91 | yes | source AAR |
| `libs/aars/SettingsLibIllustrationPreference.aar` | SettingsLib | 5197 | `81cf4dc6cfa7fe1d66cf56ef6813a51ccd9445caf022d46e65240f9ca827e49c` | 0 | 6 | yes | source AAR |
| `libs/aars/SettingsLibLayoutPreference.aar` | SettingsLib | 6194 | `c41e5cf3cdc1a0a7e47adbfaeb1bc8b1344f303c2d9830cfbcb524f54d292e0e` | 0 | 6 | yes | source AAR |
| `libs/aars/SettingsLibMainSwitchPreference.aar` | SettingsLib | 18525 | `b6147933ce09c4d792cb88275a38436226a98add85ad0d539dd277e1f9a1c71f` | 0 | 22 | yes | source AAR |
| `libs/aars/SettingsLibProgressBar.aar` | SettingsLib | 9794 | `5e8c34680904939b1e2b213fd9a7e0bd2ca1633cc07d385bb30046c08b5823ab` | 0 | 10 | yes | source AAR |
| `libs/aars/SettingsLibRestrictedLockUtils.aar` | SettingsLib | 73913 | `6bb2ecc6495d7778260a71614b77c5e1f6bc049f29ac49aba76d9fc255196197` | 0 | 87 | yes | source AAR |
| `libs/aars/SettingsLibSelectorWithWidgetPreference.aar` | SettingsLib | 67343 | `87f558c6bf87a1191df5f453bb1f15e1ce8148c7db036cf98c61ba5b0f18682b` | 0 | 92 | yes | source AAR |
| `libs/aars/SettingsLibSettingsSpinner.aar` | SettingsLib | 4572 | `ee3aa868adc75038564fcbf38e7405e5b0a8a6e8b34349df22408fa80821db62` | 0 | 5 | yes | source AAR |
| `libs/aars/SettingsLibSettingsTheme.aar` | SettingsLib | 165734 | `9ee3c671d80b1338b41480d886e2277910fd8c0b80ee3cbf907ebacb3f00b877` | 15 | 174 | yes | source AAR |
| `libs/aars/SettingsLibSliderPreference.aar` | SettingsLib | 5536 | `1912b297b54c95b576e4c094c62e5adadc53259650a27cecdd74d02b70f93102` | 0 | 5 | yes | source AAR |
| `libs/aars/SettingsLibTwoTargetPreference.aar` | SettingsLib | 7809 | `7c5fbc437674055d00ec06c2fb20e24953a8939be09dac0c71b5887c0044ec77` | 0 | 7 | yes | source AAR |
| `libs/aars/SettingsLibUsageProgressBarPreference.aar` | SettingsLib | 2117 | `6ab7d889b5738b88a2ca2d5dfd134330adf60d50fe09b4be88c4f8f4ed8561b1` | 0 | 1 | yes | source AAR |
| `libs/aars/Traceur-res.aar` | Traceur | 409115 | `868237f6757f73719a6718b7551c966ae4e2e7b2caa53133b24e0e01554e40dd` | 0 | 105 | yes | source AAR |
| `libs/aars/TraceurCommon.aar` | Traceur | 1053643 | `e358570e907ee8c33f12e4c9a36fa741d923454d0ab872e125c0436bd02be2dd` | 640 | 0 | yes | source AAR |
| `libs/aars/WifiTrackerLib.aar` | WifiTrackerLib | 588337 | `d45bbca98feb45f552aa14fa31d819b2c85b1148c7d3cc530423212dabee99fb` | 63 | 173 | yes | source AAR |
| `libs/aars/WindowManager-Shell-shared.aar` | WM-Shell | 222686 | `1633db41becca4216a345c3caa8fe25dadbda23ce2e1901e09a8aaa8cdd48774` | 152 | 2 | yes | source AAR |
| `libs/aars/WindowManager-Shell.aar` | WM-Shell | 4396336 | `37e3e78625d8ae61f7cd3259b17346df36d997156e161f477d06f61ba1fec763` | 1888 | 378 | yes | source AAR |
| `libs/aars/animationlib.aar` | animationlib | 19680 | `91f85a93f174c1907a4af1d7afab66253314a45b09b750a4a84d7215eeb610ab` | 13 | 7 | yes | source AAR |
| `libs/aars/iconloader.aar` | iconloader | 137664 | `d6e4f27e4b752620b9207fd804db1f5f3dad3225998375ed36d13346d3da6d8b` | 75 | 11 | yes | source AAR |
| `libs/aars/setupcompat.aar` | setupcompat | 194066 | `0a4222bf22f81636e6f1b51b119df08486a71b560c7ff875bcca1c546a13c95a` | 126 | 12 | yes | source AAR |

Every source AAR is byte-identical (same SHA) to its installed local Maven copy where one exists — the Maven
set is a delivery duplicate of `libs/aars/`, plus `color` (SettingsLibColor under group `com.android.settingslib`).
TraceurCommon + Traceur-res are the only source AARs consumed **directly** as files
(`SystemUI-core/build.gradle.kts:198-200`), consistent with AGENTS.md §3.2 rule 2 (no direct `files("libs/aars/...")`
for Maven-delivered families).

### 3.2 Local Maven AARs (`libs/maven/`) — 27

| Path | Family | Size | SHA-256 | Classes | Res files | POM deps | Delivery role |
|---|---|---|---|---|---|---|---|
| `libs/maven/com/android/settingslib/color/1.0.0/color-1.0.0.aar` | color | 2033 | `41a8d422ea3e78837378c7b5f2f4ba7e4814983dd2f273eac3861d3dd6f2bd16` | 0 | 1 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/LowLightDreamLib/1.0.0/LowLightDreamLib-1.0.0.aar` | LowLightDreamLib | 28914 | `2a7b0939611434b6c3cbeab7739307363692997ec13a71ce24d3a9a717f7c0f8` | 24 | 1 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLib/1.0.1/SettingsLib-1.0.1.aar` | SettingsLib | 4797541 | `61b480f284ae7eefd194412cf2dde8c7ad55675f8275f32cd6654278d8a2bd04` | 1153 | 365 | 17 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibActionButtonsPreference/1.0.0/SettingsLibActionButtonsPreference-1.0.0.aar` | SettingsLib | 12524 | `dd481d9f07039cf161f52809a6e7ea5a87acd72e4c67ab96aa4476866379266b` | 0 | 15 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibAdaptiveIcon/1.0.0/SettingsLibAdaptiveIcon-1.0.0.aar` | SettingsLib | 2922 | `6f2df660d20d5cc642dce2200faa5ddb85e0076c920365ec74aa46f659af2eb6` | 0 | 3 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibAppPreference/1.0.0/SettingsLibAppPreference-1.0.0.aar` | SettingsLib | 67135 | `2110852a0fee594121a8cca7e0057d421d1903e8895ead9ca6bd094c10cbbaec` | 0 | 91 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibBannerMessagePreference/1.0.0/SettingsLibBannerMessagePreference-1.0.0.aar` | SettingsLib | 70129 | `7beca439ac32c2b6a3f4e8be1edf185ca65ede0ab0ada5700fea17c7a874454c` | 0 | 96 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibBarChartPreference/1.0.0/SettingsLibBarChartPreference-1.0.0.aar` | SettingsLib | 5789 | `4624cf0e4c30921ac31f454c1e6b0bb17ce80df4d47fd6cfd61da938f194281e` | 0 | 6 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibButtonPreference/1.0.0/SettingsLibButtonPreference-1.0.0.aar` | SettingsLib | 18790 | `2801c41c071c9d4bb07578e4518ac89bd493e049e546f38546c61ba9c3939452` | 0 | 23 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibFooterPreference/1.0.0/SettingsLibFooterPreference-1.0.0.aar` | SettingsLib | 66912 | `2a631f84d9c622775296e45b0911ee2dea49c8d318642b916ce3f7a1636f8c59` | 0 | 91 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibIllustrationPreference/1.0.0/SettingsLibIllustrationPreference-1.0.0.aar` | SettingsLib | 5197 | `81cf4dc6cfa7fe1d66cf56ef6813a51ccd9445caf022d46e65240f9ca827e49c` | 0 | 6 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibLayoutPreference/1.0.0/SettingsLibLayoutPreference-1.0.0.aar` | SettingsLib | 6194 | `c41e5cf3cdc1a0a7e47adbfaeb1bc8b1344f303c2d9830cfbcb524f54d292e0e` | 0 | 6 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibMainSwitchPreference/1.0.0/SettingsLibMainSwitchPreference-1.0.0.aar` | SettingsLib | 18525 | `b6147933ce09c4d792cb88275a38436226a98add85ad0d539dd277e1f9a1c71f` | 0 | 22 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibProgressBar/1.0.0/SettingsLibProgressBar-1.0.0.aar` | SettingsLib | 9794 | `5e8c34680904939b1e2b213fd9a7e0bd2ca1633cc07d385bb30046c08b5823ab` | 0 | 10 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibRestrictedLockUtils/1.0.0/SettingsLibRestrictedLockUtils-1.0.0.aar` | SettingsLib | 73913 | `6bb2ecc6495d7778260a71614b77c5e1f6bc049f29ac49aba76d9fc255196197` | 0 | 87 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibSelectorWithWidgetPreference/1.0.0/SettingsLibSelectorWithWidgetPreference-1.0.0.aar` | SettingsLib | 67343 | `87f558c6bf87a1191df5f453bb1f15e1ce8148c7db036cf98c61ba5b0f18682b` | 0 | 92 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibSettingsSpinner/1.0.0/SettingsLibSettingsSpinner-1.0.0.aar` | SettingsLib | 4572 | `ee3aa868adc75038564fcbf38e7405e5b0a8a6e8b34349df22408fa80821db62` | 0 | 5 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.1/SettingsLibSettingsTheme-1.0.1.aar` | SettingsLib | 165734 | `9ee3c671d80b1338b41480d886e2277910fd8c0b80ee3cbf907ebacb3f00b877` | 15 | 174 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibSliderPreference/1.0.0/SettingsLibSliderPreference-1.0.0.aar` | SettingsLib | 5536 | `1912b297b54c95b576e4c094c62e5adadc53259650a27cecdd74d02b70f93102` | 0 | 5 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibTwoTargetPreference/1.0.0/SettingsLibTwoTargetPreference-1.0.0.aar` | SettingsLib | 7809 | `7c5fbc437674055d00ec06c2fb20e24953a8939be09dac0c71b5887c0044ec77` | 0 | 7 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/SettingsLibUsageProgressBarPreference/1.0.0/SettingsLibUsageProgressBarPreference-1.0.0.aar` | SettingsLib | 2117 | `6ab7d889b5738b88a2ca2d5dfd134330adf60d50fe09b4be88c4f8f4ed8561b1` | 0 | 1 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/WifiTrackerLib/1.0.0/WifiTrackerLib-1.0.0.aar` | WifiTrackerLib | 588337 | `d45bbca98feb45f552aa14fa31d819b2c85b1148c7d3cc530423212dabee99fb` | 63 | 173 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/WindowManager-Shell-shared/1.0.0/WindowManager-Shell-shared-1.0.0.aar` | WM-Shell | 222686 | `1633db41becca4216a345c3caa8fe25dadbda23ce2e1901e09a8aaa8cdd48774` | 152 | 2 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/WindowManager-Shell/1.0.1/WindowManager-Shell-1.0.1.aar` | WM-Shell | 4396336 | `37e3e78625d8ae61f7cd3259b17346df36d997156e161f477d06f61ba1fec763` | 1888 | 378 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/animationlib/1.0.0/animationlib-1.0.0.aar` | animationlib | 19680 | `91f85a93f174c1907a4af1d7afab66253314a45b09b750a4a84d7215eeb610ab` | 13 | 7 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/iconloader/1.0.1/iconloader-1.0.1.aar` | iconloader | 137664 | `d6e4f27e4b752620b9207fd804db1f5f3dad3225998375ed36d13346d3da6d8b` | 75 | 11 | 0 | local Maven AAR |
| `libs/maven/com/android/systemui/setupcompat/1.0.0/setupcompat-1.0.0.aar` | setupcompat | 194066 | `0a4222bf22f81636e6f1b51b119df08486a71b560c7ff875bcca1c546a13c95a` | 126 | 12 | 0 | local Maven AAR |

### 3.3 Root JARs (`libs/`) — 28

| Path | Family/role group | Size | SHA-256 | Classes | Delivery role |
|---|---|---|---|---|---|
| `libs/PlatformMotionTestingComposeValues.jar` | view-capture/motion | 14053 | `beb021cfba4d335a05b77ccbaf18a7f935154f04bd1196531d78e4edaafba59e` | 9 | program JAR |
| `libs/SystemUI-proto.jar` | SystemUI proto | 34526 | `8f24c6b2544aa86227a311d68946329e3afa2569e60eca3eecda0d0cc91a6ea3` | 15 | program JAR |
| `libs/SystemUI-statsd.jar` | SystemUI statsd | 12259 | `3e96c65367070d15f2fa568de2cf4fba64626e87075e7e8fd2af7165518072bf` | 1 | program JAR |
| `libs/SystemUI-tags.jar` | SystemUI tags | 2086 | `441b05edc1fd304b879ee83097ad05f1c7d5f5b59f5431832ce44720792387aa` | 1 | program JAR |
| `libs/android-merged.jar` | SysUISdk | 44846603 | `67ceccc5cd9d610189d45596481b1f8fefe557c8b41a2820d9d74df536770d79` | 29131 | platform input (SysUISdk S1 source) |
| `libs/android.car.jar` | framework/platform | 739278 | `bd5faa75542bf93d9dc9c989ce09a9510261e1e72188396a4c7abf30ae3bea62` | 678 | compile/library JAR |
| `libs/android_module_lib_stubs_current.jar` | framework/platform | 5852413 | `af3fc1f18a9cbedebf01900deb9721e9339ab2fb51c3b42d3c8d052a223d13d7` | 6489 | compile/library JAR |
| `libs/compilelib-debug.jar` | compilelib | 400 | `9d12cbddf01e352485197646dcb794676738ee3ed1faf5d9490175cf920afbd3` | 1 | program JAR (debug) |
| `libs/compilelib-release.jar` | compilelib | 400 | `ad605e3fc7bb80f563497983392fc193368d88c1042bdda22e28004df73ca022` | 1 | program JAR (release) |
| `libs/contextualeducationlib.jar` | module API | 2356 | `21827c3c18dd1f8087eaac1bbecaa339fcb9679818a7d10dff169b6b1bc61385` | 1 | program JAR |
| `libs/device-state-flags.jar` | aconfig flags (device state) | 8587 | `cf8f4f0981c4033c41e9436e9b78767cdc8f0e3bacde4cdf1c7eeb44a57abd2d` | 5 | program JAR (aconfig runtime) |
| `libs/framework-statsd.jar` | framework/platform | 56445 | `d54489eea0289da14cbac81f803990f5505fe39a62303783f227c69b39daf80c` | 39 | compile/library JAR |
| `libs/framework.jar` | framework/platform | 19902057 | `0fe39d800f34f6c7b17e5c936571bc29367e1329c8af9c6ab47e894beb05be26` | 25914 | platform input (compileOnly bootclasspath) |
| `libs/keepanno-annotations.jar` | annotations (R8 keepanno) | 20827 | `056412aa7731b573f06940c792db082859ad49e464be08f464a4bba52fd856c5` | 22 | compile/library JAR |
| `libs/launcher3-flags.jar` | aconfig flags (launcher3) | 31524 | `5b0f57ee46ca0a41e20a6db8727d6a3f143bb6fb92adcf3234f706142a6a06eb` | 5 | program JAR (aconfig runtime) |
| `libs/monet.jar` | monet | 111175 | `50f88d5137d2164fe23412d38d4b5d079b16c84652ef953b6bede7276808ce60` | 56 | program JAR |
| `libs/motion_tool_lib.jar` | view-capture/motion | 93172 | `e2f5d0a96f43e535e8ead5096ea31f93c9f991504a19cf077d303142c50bbf72` | 65 | program JAR |
| `libs/msdl.jar` | module API | 65750 | `ecbdfe63b8c65ea094110931d93e600d69880d56362928b3ad6ce6c36872468e` | 46 | program JAR |
| `libs/notification-flags.jar` | aconfig flags (notification) | 14301 | `0f3bfc6623d3b7b89ea5da099458d285b266b63773e514284cd9d614d329a423` | 5 | program JAR (aconfig runtime) |
| `libs/settingslib-flags.jar` | aconfig flags (settingslib) | 6311 | `829fa4e5e694a136448200bb438b2005b14ba66b06836f686d83ef640e89a171` | 5 | program JAR (aconfig runtime) |
| `libs/settingslib-media-flags.jar` | aconfig flags (settingslib media) | 9368 | `2f0dfc1524c9558a795a1c05f382e2953982340576fab19a3f2ae7a94d2d4708` | 5 | program JAR (aconfig runtime) |
| `libs/settingslib-selector-flags.jar` | aconfig flags (settingslib selector) | 8884 | `7c54c1fb16af63791a03a0969ada802438bdc1724ce8e2a8dbb84ed41b7de145` | 5 | program JAR (aconfig runtime) |
| `libs/settingslib-widget-flags.jar` | aconfig flags (settingslib widget) | 7944 | `e08f258773e4b52c99f4216d5ceb96c19df96aee5be34453dc6ee49a958d657e` | 5 | program JAR (aconfig runtime) |
| `libs/systemui-flags.jar` | aconfig flags (systemui) | 75736 | `c0b7d4825c93f49125d1b1d91f4beb73a933999bac072a8f5b4c06b9ca5ff9f6` | 5 | program JAR (aconfig runtime) |
| `libs/systemui-shared-flags.jar` | aconfig flags (systemui shared) | 11197 | `f3db97cae224e6d044021e10b5a81076fc0eb83cec33c27fb2b00a059cf64dc9` | 5 | program JAR (aconfig runtime) |
| `libs/view_capture.jar` | view-capture/motion | 93747 | `7ed2eb141ec1d491a5c9b0f205eb2649862b6a6e5595150b92e6d7e25ed5d315` | 56 | program JAR |
| `libs/wifi-flags.jar` | aconfig flags (wifi) | 15664 | `b12ffcc9589c261f8cc68cfbacfcc22936171159f9d0b41ca61ccc6b4b32b1f1` | 5 | program JAR (aconfig runtime) |
| `libs/wm-shell-flags.jar` | aconfig flags (wm shell) | 13314 | `5a8a7d946b42bc5ccfc025d3d3cd33e2d25f58194288c1d0a5c4236d0e7ad3e0` | 5 | program JAR (aconfig runtime) |

### 3.4 Prebuilt JARs (`libs/prebuilts/`) — 1

| Path | Family | Size | SHA-256 | Classes | Delivery role |
|---|---|---|---|---|---|
| `libs/prebuilts/tracinglib-platform.jar` | tracinglib (perfetto closure) | 115342 | `90ec3be83e8af0bc9167046533be67b43fff69f0bb09ca747e7b82ddb83409d4` | 64 | compile/library JAR |

### 3.5 Consumer map and orphans

Consumers established by static search of all `*.gradle.kts` + `gradle/libs.versions.toml`:

- Local Maven AAR aliases → `:SystemUI-core` (`libs.systemui.settingslib` line 217, `setupcompat` 221,
  `iconloader` 222, `wmshell` 223, `wmshell.shared` 227, `lowlight.dream.lib` 230, `wifitrackerlib` 247,
  `settingslib.color` 251), `:SystemUI-res` (`settingslib` line 37, `settingslib.theme` 40),
  `:SystemUI-customization` (`animationlib` line 63), `:SystemUI-animation` (`animationlib` line 54; `wmshell`/`wmshell.shared`
  compileOnly lines 50-51), `:SystemUI-compose` (`animationlib` line 60), `:SystemUI-shared` (`wmshell`/`wmshell.shared`
  compileOnly lines 63-64). The 17 SettingsLib per-target res AARs are reached transitively via the SettingsLib POM
  (ADR 0005) — no direct alias consumers, which is their designed delivery role.
- Direct-file AAR consumers: TraceurCommon + Traceur-res (`SystemUI-core/build.gradle.kts:198-200`).
- Root JAR consumers: recorded in §4.4 (all 28 mapped; none unconsumed). `libs/android-merged.jar` is consumed
  only by `tools/build_sysuisdk.py` S1 (a build input, not a Gradle dependency) — expected, not an orphan.
- Unconsumed-currently: **none** across all four inventories.

## 4. Artifact-family seam analysis

### 4.1 SettingsLib family (20 local Maven AARs, 20 source AARs)

Present structure: one umbrella code artifact `SettingsLib` 1.0.1 (1153 classes, 365 res files, POM with 17
per-target dependency edges — `libs/maven/com/android/systemui/SettingsLib/1.0.1/SettingsLib-1.0.1.pom`, ADR 0005),
one owning-Kotlin artifact `SettingsLibSettingsTheme` 1.0.1 (15 classes + 174 res), one group-id outlier
`com.android.settingslib:color` 1.0.0 (res-only, 1 file), and 17 res-only per-target AARs (0 classes each,
1–96 res files). Consumers: `:SystemUI-core` (implementation) and `:SystemUI-res` (api, lines 37/40).

- Current split constraint evidence: the 17 res AARs exist to give each SettingsLib Soong res target its own
  `R.txt`/manifest so AGP resource merging resolves per-target symbols without duplicate-resource conflicts
  (ADR 0005; Task 040 achieved exact R8 81→7). Whether this constraint is **currently demonstrable** versus an
  artifact of the per-target delivery choice cannot be distinguished without an experiment — present evidence
  (no conflict reproduction at a coarser seam) is absent, so per spec §5.4 this is an audit priority, not a
  rollback list.
- Shallow-seam observation: class-set intersection between umbrella and per-target artifacts is empty by
  construction (per-target AARs are res-only), so the split is purely a resource-ownership device, not a code seam.
- Coarsest plausible future seam per spec §5.4: one umbrella SettingsLib AAR (or smallest stable set with real
  resource namespaces). Exact experiment required (future, NOT APPROVED): rebuild the family as a single AAR
  (or few), run `:app:checkDebugDuplicateClasses` + `:app:assembleDebug` + `:app:minifyReleaseWithR8`, verify
  resource link succeeds and R8 missing refs do not regress, then device install/launch.
- The 17 POM edges mechanically mirror AOSP `SettingsLib/Android.bp` `static_libs`; under a coarse umbrella
  these edges would vanish (complexity moves behind the packaging recipe, passing the spec §6 deletion test).

Recommendation: **consolidate** (NOT APPROVED — see packet §10.1); the res-namespace constraint must be
reproduced or refuted by the experiment before any change.

### 4.2 WM-Shell family (2 artifacts)

`WindowManager-Shell` 1.0.1 (1888 classes incl. proto closure, 378 res) + `WindowManager-Shell-shared` 1.0.0
(152 classes, 2 res). Consumers: `:SystemUI-core` implementation (lines 223/227); `:SystemUI-animation` and
`:SystemUI-shared` compileOnly (animation 50-51, shared 63-64). Owners: `frameworks/base/libs/WindowManager/Shell/`
(main) and `.../Shell/shared/` (own `Android.bp` + manifest + res dir, `tools/package_aosp_aar.py` lines 99-131).
Current split has a real manifest/res-owner boundary (separate upstream Android.bp targets with distinct
manifests and R.txt inputs). Spec §5.4 says "keep a stable main/shared split only if merging causes a proven
conflict" — no conflict reproduction exists for either direction; merging is a future experiment, and the split
is not currently harmful (two artifacts, deep boundary). Recommendation: **keep**, with a merge experiment listed
only as a candidate simplification if the user wants fewer coordinates (needs experiment, folded into §12 order).

### 4.3 Traceur family (2 direct AARs)

`TraceurCommon.aar` (640 classes, 0 res) + `Traceur-res.aar` (0 classes, 105 res, namespace
`com.android.traceur.res` per `SystemUI-core/build.gradle.kts:199` comment). Owner: `packages/apps/Traceur`
(`Android.bp` exists at that path). Current split: code vs res with an independent R namespace — this is a
demonstrated namespace device (R class regenerated by AGP from R.txt), matching spec's "separate resource/code
artifact only if AGP namespace or ownership requires it". One coherent artifact could not express two
namespaces. Recommendation: **keep**.

### 4.4 Remaining AAR families

| Family | Artifacts | Current seam verdict vs one-family default | Local Maven justified? | Recommendation |
|---|---|---|---|---|
| WifiTrackerLib | 1 AAR (63 cls, 173 res), alias `systemui-wifitrackerlib` (`:SystemUI-core` line 247); owner `frameworks/opt/net/wifi/libs/WifiTrackerLib` | Already one-family | Unproven: no POM deps, single consumer, no cited transitive/resource-resolution need beyond uniformity | **candidate rollback** (direct AAR) pending experiment — NOT APPROVED |
| iconloader | 1 AAR (75 cls, 11 res), alias line 222; owner `frameworks/libs/systemui/iconloaderlib` | Already one-family | Unproven (same test: skeleton POM, one consumer) | **candidate rollback** — NOT APPROVED |
| animationlib | 1 AAR (13 cls, 7 res); direct catalog aliases in `:SystemUI-customization:63`, `:SystemUI-animation:54`, `:SystemUI-compose:60`; `:SystemUI-core` consumes it transitively via `implementation(project(":SystemUI-animation"))` (`SystemUI-core/build.gradle.kts:122`); owner `frameworks/libs/systemui/animationlib/Android.bp` | Already one-family; multi-module consumers all via catalog | Unproven: multiple `api()` consumers exist, but direct AAR files would work identically | **needs experiment** — NOT APPROVED |
| setupcompat | 1 AAR (126 cls, 12 res), alias line 221; owner `external/setupcompat/Android.bp` | Already one-family | Unproven | **candidate rollback** — NOT APPROVED |
| LowLightDreamLib | 1 AAR (24 cls, 1 res), alias line 230; owner `frameworks/base/libs/dream/lowlight` | Already one-family | Unproven | **candidate rollback** — NOT APPROVED |

Note on direct-AAR migration for these single-artifact families: since every Maven AAR is byte-identical to its
`libs/aars/` source, direct `files(...aar)` consumption changes only Gradle metadata resolution, not bytes.
None has consumer rules (`consumer_rules.pro` absent in all 29 source AARs — §7.2). The catalog currently
forbids direct `libs/aars/` references (AGENTS.md §3.2 rule 2), so any migration is a policy + wiring change
requiring explicit user approval per family.

### 4.5 JAR families by role

| Group | JARs | Findings |
|---|---|---|
| framework/platform inputs | `framework.jar` (25914 cls; compileOnly across app/core/animation/common/compose/customization/plugin/plugin-core/shared/shared-biometrics/unfold + root `build.gradle.kts:12-48` JavaCompile injection), `android-merged.jar` (29131 cls; SysUISdk S1 source only), `android.car.jar`, `framework-statsd.jar`, `android_module_lib_stubs_current.jar` (all compileOnly, core) | No duplicates among themselves; each has a distinct compile role. `android-merged.jar` overlaps `framework.jar` semantically (merged SDK master) but serves the SDK pipeline, not module compilation — refresh coupling is deliberate. Provider status: all five are manually maintained platform snapshots with no producing tool (`build_sysuisdk.py`/`install_sdk.py`/`patch_sdk_dalvik_annotations.py` reference them as inputs only) |
| compilelib | `compilelib-debug.jar` / `compilelib-release.jar` (1 class each; `debugImplementation`/`releaseImplementation` core lines 130-131; tool-registered outputs of `package_compilelib_jars.py`) | Two tiny variant artifacts mirror AOSP `frameworks/libs/systemui:compilelib` debug/release outputs; variant split is the real seam |
| aconfig generated runtime (11 jars) | systemui, systemui-shared, notification, settingslib, settingslib-media, settingslib-selector, settingslib-widget, launcher3, wifi, wm-shell, device-state — all 5-class `Flags` families, all `implementation` in core except settingslib-flags (compileOnly line 180) | Coherent per-owner granularity; class ordering constraint vs framework.jar stubs handled in root `build.gradle.kts:26-35`. No duplicate delivery; refresh fragmentation is inherent to aconfig per-container generation. Provider status: 8 of the 11 jars are registered outputs of `tools/package_aconfig_jars.py` (registry keys systemui-shared/wifi/wm-shell/systemui/notification/launcher3/settingslib-widget/settingslib-selector); `settingslib-flags.jar`, `settingslib-media-flags.jar`, `device-state-flags.jar` are manually maintained with no producing tool |
| tracing/view-capture/motion | `view_capture.jar`, `motion_tool_lib.jar` (tool-registered outputs of `package_viewcapture_motiontool_jars.py`), `PlatformMotionTestingComposeValues.jar` (manually maintained, no producing tool) — all core/shared implementation | Deterministic packaging tool owns two of the three; the Compose-values jar has no registered refresh path |
| monet | `monet.jar` (56 cls; core implementation, customization compileOnly, root build injection) | AOSP owner `frameworks/libs/systemui/monet`; tool-registered output of `package_monet_jar.py`; single artifact, deep seam — keep |
| annotations | `keepanno-annotations.jar` (22 R8 keepanno classes; core compileOnly line 175-176) | Compile-only optimizer-facing; manually maintained (consumed as input by `build_sysuisdk.py` S3b but produced by no project tool); also feeds SysUISdk S3b — see §6 |
| proto/statsd/tags | `SystemUI-proto.jar`, `SystemUI-statsd.jar`, `SystemUI-tags.jar` (core implementation) | First-class Soong products of the SystemUI bp (bp:38-56); manually maintained with no producing tool; keep |
| module API / other | `msdl.jar`, `contextualeducationlib.jar` (core implementation) | Single-purpose AOSP products; manually maintained with no producing tool; keep |
| prebuilts | `tracinglib-platform.jar` (64 cls; `implementation` in `:SystemUI-compose:61`, compileOnly in `:SystemUI-common:38` and `:SystemUI-shared:68`) | Sole `libs/prebuilts/` resident; manually maintained with no producing tool; CURRENT_STATE notes it as historical legacy for gradual cleanup; no duplicate class source identified among current consumers — **needs history/context** to confirm original purpose before any retirement decision |

Root-JAR provider summary (28 jars): **13 tool-registered** (`compilelib-debug`/`compilelib-release` via
`package_compilelib_jars.py`; 8 aconfig jars via `package_aconfig_jars.py` registry; `monet.jar` via
`package_monet_jar.py`; `view_capture.jar`/`motion_tool_lib.jar` via `package_viewcapture_motiontool_jars.py`)
and **15 manually maintained** with no producing tool (`framework.jar`, `android-merged.jar`, `android.car.jar`,
`framework-statsd.jar`, `android_module_lib_stubs_current.jar`, `keepanno-annotations.jar`,
`SystemUI-proto.jar`, `SystemUI-statsd.jar`, `SystemUI-tags.jar`, `msdl.jar`, `contextualeducationlib.jar`,
`settingslib-flags.jar`, `settingslib-media-flags.jar`, `device-state-flags.jar`,
`PlatformMotionTestingComposeValues.jar`). Manually maintained status changes no §9 recommendation; it only
marks which refreshes lack a registered deterministic recipe.

## 5. Delivery and refresh mechanisms

### 5.1 Packaging / rebuild / install tools and family map

`find tools -maxdepth 1 -type f (name 'package*.py' -o name 'install_aar_to_maven.py')` yields (plus
`build_sysuisdk.py` covered in §6):

| Tool | Families produced | Input source | Determinism / allowlist interface | Tests |
|---|---|---|---|---|
| `tools/package_aosp_aar.py` | All 29 `libs/aars/` AARs: SettingsLib closure (20 targets), WM-Shell ×2, WifiTrackerLib, iconloader, animationlib, LowLightDreamLib, setupcompat, Traceur ×2 (recipes at lines 55-430+) | AOSP Soong `javac` jars + source `res/` + manifests + R.txt | Deterministic packaging; per-target code/res/manifest/rtxt recipe table | `tools/tests/test_package_aosp_aar.py` |
| `tools/install_aar_to_maven.py` | All 27 `libs/maven/` coordinates (install table lines 64-95; SettingsLib 1.0.1 with 17 POM deps, SettingsLibSettingsTheme 1.0.1, iconloader 1.0.1, WM-Shell 1.0.1) | `libs/aars/*.aar` bytes (copy-only, never rewritten) | Skeleton POMs; sole exception SettingsLib closure deps (ADR 0005) | `tools/tests/test_install_aar_to_maven.py` |
| `tools/package_compilelib_jars.py` | `compilelib-debug.jar`, `compilelib-release.jar` | AOSP compilelib javac outputs | Deterministic | `test_package_compilelib_jars.py` |
| `tools/package_aconfig_jars.py` | The 8 registered aconfig flags jars (systemui, systemui-shared, notification, launcher3, wifi, wm-shell, settingslib-widget, settingslib-selector); the other 3 root aconfig jars (settingslib, settingslib-media, device-state) are manually maintained — see §4.5 | AOSP javac products | Deterministic; explicit registry keys | `test_package_aconfig_jars.py` |
| `tools/package_monet_jar.py` | `monet.jar` (56 classes) | Two Soong javac outputs | Deterministic | `test_package_monet_jar.py` |
| `tools/package_viewcapture_motiontool_jars.py` | `view_capture.jar`, `motion_tool_lib.jar` (the related `PlatformMotionTestingComposeValues.jar` is manually maintained) | AOSP javac outputs | Deterministic | `test_package_viewcapture_motiontool_jars.py` |

### 5.2 Depth and refresh locality

A normal upstream refresh of one family currently touches: the `package_aosp_aar.py` recipe (family-local),
`install_aar_to_maven.py` install entry (family-local), the version bump in `libs.versions.toml` (catalog),
and the AAR bytes in both `libs/aars/` and `libs/maven/`. The two-step AAR→Maven pipeline is a deliberate
separation (packaging vs delivery) rather than a shallow pass-through: install never rewrites bytes and owns
POM/version policy (ADR 0001/0005). Deletion test: collapsing install into packaging would couple version
policy to byte packaging; collapsing packaging into install would lose the deterministic recipe table — the
seam is useful. However, for single-artifact families with skeleton POMs (§4.4) the entire Maven stage adds a
coordinate, a version, a catalog alias, and a duplicate byte copy without a demonstrated Gradle metadata need —
that stage is shallow **for those families only**.

### 5.3 Local-Maven justification per family

| Family | Cited current POM metadata / resource-resolution requirement | Verdict |
|---|---|---|
| SettingsLib (umbrella + 17 res + theme + color) | 17 POM edges deliver the per-target res closure onto the compile classpath automatically (ADR 0005); multi-AAR resource merging across 19 artifacts is exactly the case local Maven exists for | Justified (pending the §10.1 consolidation experiment outcome) |
| WM-Shell / WM-Shell-shared | Skeleton POMs; consumers could reference direct AARs; no transitive edges | Unproven — needs experiment |
| WifiTrackerLib, iconloader, setupcompat, LowLightDreamLib | Skeleton POMs, single consumer each | Unproven — candidate rollback |
| animationlib | Skeleton POM, multi-consumer but all internal catalog aliases | Unproven — needs experiment |
| Traceur | Not in Maven (direct AAR) — already direct | n/a (keep) |

`catalog uniformity` alone is not justification (spec §6.3); every `Unproven` row above is recorded as a
NOT APPROVED packet or ledger row requiring a later build/resource experiment before migration.

## 6. SysUISdk adapter analysis

`tools/build_sysuisdk.py` documents stages S0–S4 build + S5 verify (file docstring lines 3-38,
`ALL_STAGES = ("s0","s1","s2","s3","s3b","s4")` line 109; `DEFAULT_STAGES = "s0,s1,s2,s3,s3b"` line 113,
S4 opt-in). Live SDK verified read-only at
`/home/conv/Android/Sdk/platforms/android-SysUISdk/`.

| Stage | Interface / input | Output mutation (staging) | Platform/runtime purpose | Verification | Refresh coupling |
|---|---|---|---|---|---|
| S0 | base platform `android-37.0` copy | staging dir + `package.xml` rewrite (`stage_s0` def at line 196; `_rewrite_package_xml` helper at line 171) | provide a patchable SDK target | `test_build_sysuisdk.py` | per SDK base upgrade |
| S1 | `libs/android-merged.jar` (29131 classes) | wholesale `android.jar` copy (`stage_s1` def at line 273; `_copy_merged_master` helper at line 232) | hidden framework API compilation surface | inventory equality vs live | per framework.jar regeneration |
| S2 | `tools/install_sdk.py` | `framework.aidl` hidden iface/parcelable appends (`stage_s2` def at line 287) | framework @hide AIDL declarations (rule F) | idempotent append report | per new hidden interface |
| S3 | core-libart javac jar | 4 `dalvik.annotation.optimization` classes into both jars (`stage_s3` def at line 327; `_rewrite_manifest_entry` helper at line 304) | dalvik optimization annotations for R8/d8 | `test_patch_sdk_dalvik_annotations.py` | per platform upgrade |
| S3b | core-libart + unsupportedappusage + aconfig-annotations + keepanno javac jars | exactly 35 allowlisted library classes into `android.jar` and `core-for-system-modules.jar` (`stage_s3b` def at line 350) | real platform library classes AGP/R8 needs at build time but the public SDK lacks (ADR 0006) | `test_patch_sdk_r8_library_classes.py`; Task 041 verified 35/35 source-identical, APK 0/35 packaged | per keepanno/platform refresh |
| S4 | AOSP `framework-res.apk` | `resources.arsc` + `res/**` overlay onto `android.jar` (`stage_s4` def at line 456; `_overlay_framework_res` helper at line 415) | `@*android:` private resource IDs (AGENTS §2.4 point 2) | opt-in; CURRENT_STATE records S5 ALL PASS | per framework-res regeneration |
| S5 | `--verify` | none (read-only compare) | staging vs live equivalence gate | name→CRC inventories for the two jars | after any apply |

Live-SDK spot check (read-only `unzip -l`): `IoUtils` ×2 entries, `NativeAllocationRegistry` ×4,
`UnsupportedAppUsage` ×2, `AconfigFlagAccessor` ×1, keepanno `KeepEdge` ×1 present in **both**
`android.jar` and `core-for-system-modules.jar` — consistent with the Task 041 main-fresh record
(CURRENT_STATE “Verification commands and evidence”).

S3b category classification (Task 041 closed; audited, not reopened):

| Category | Classification | Rationale / loss-if-removed |
|---|---|---|
| `libcore/io/IoUtils` (+inner) | platform-required | real platform classes referenced by SystemUI code; removal reopens R8 missing refs (was B-group) |
| `libcore/util/NativeAllocationRegistry` (+inners) | platform-required | same; runtime-owned native allocation registry |
| DDMS-related core-libart slices | platform-required (via S3/S3b allowlist) | optimizer-visible platform annotations/classes |
| `android/compat/annotation/UnsupportedAppUsage` (+Container) | platform-required | framework stability annotation read at build time |
| `com/android/aconfig/annotations/AconfigFlagAccessor` | platform-required (live jar contains it) | aconfig runtime accessor contract |
| keepanno 22-class package | optimizer-only | consumed by R8 keep-annotation processing and core compileOnly (line 175); removal would drop keep-annotation support and reopen build refs — but it is optimizer-facing, not platform-runtime API |
| `AssumeTrueForR8` | optimizer-only — deliberately NOT bridged by S3b | the single remaining R8 missing ref; see §7.3 |

All S3b injected slices prove target availability through source-byte-identical entries from real AOSP
javac outputs (ADR 0006 requires this), so none is `obsolete` on current evidence.

## 7. AGP/R8 rule and optimizer-closure analysis

### 7.1 Project rule files and wiring

Release inputs (app/build.gradle.kts:61-70): AGP `proguard-android-optimize.txt` + `app/proguard.flags` +
`SystemUI-plugin-core/proguard.flags`; debug additionally the same set (lines 49-58).
`app/proguard.flags:1` includes `proguard_common.flags`; `proguard_common.flags:1` includes
`proguard_kotlin.flags`. `SystemUI-plugin/proguard_plugins.flags` is wired as consumer rules via
`SystemUI-plugin/build.gradle.kts:18` (`consumerProguardFiles`), mirroring bp `export_proguard_flags_files`.
No `missing_rules.txt` exists in the current worktree.

| File | Rule blocks (line counts 72/7/37/14/19) | Current evidence basis | Recommendation |
|---|---|---|---|
| `app/proguard_common.flags` | VendorServices reflective keep (upstream b/373579455 cleanup note), WeaklyReferencedCallback keepnames/keepclassmembers, CoreComponentFactory, wm-shell keep | Reflection/dynamic instantiation semantics documented inline; plugin/callback contracts are spec §7.2-justified categories | keep |
| `app/proguard.flags` | SystemUIInitializerImpl keep-all; DaggerReferenceGlobalRootComponent keep | Reflection-instantiated initializer + Dagger generated root — generated-code contract | keep |
| `app/proguard_kotlin.flags` | Intrinsics assumenosideeffects (null-check stripping) | Size optimization on Kotlin/Java interop; behavioral choice, not AOSP parity — keep while Kotlin adoption grows (upstream b/199941987 centralization note) | keep |
| `SystemUI-plugin-core/proguard.flags` | keepattributes RuntimeVisible*Annotation*, keep plugin annotation interfaces/ctors | plugin entry-point + annotation-retention contract (R8 full mode), wired via app proguardFiles (bp export semantics) | keep |
| `SystemUI-plugin/proguard_plugins.flags` | keep plugins.** and log.core.** (dynamic plugin APK boundary); ConstraintSet members | Dynamic class loading by external plugin APKs — spec §7.2 category 1/4 | keep |

All five rule files are byte-exact AOSP copies whose current blocks each cite a spec-§7.2 justification
category (reflection, plugin entry points, generated code, consumer rules). None is present "only because Soong
exports it" — on current evidence. Future flag-folding additions (AssumeTrue/FalseForR8 rules) would be new,
policy-gated inclusions, not part of these files today.

### 7.2 AAR consumer rules

`zipinfo` inspection of all 29 source AARs: **none contains `consumer-rules.pro` or `proguard.txt`**
(consumer_rules=False for every row in §3.1). Therefore no AAR consumer-rule surface exists today; the only
consumer-rule wiring in the project is `:SystemUI-plugin`'s own `consumerProguardFiles` (§7.1). No copied or
unproven AAR rules to classify — this area is clean.

### 7.3 `AssumeTrueForR8` — remaining release blocker (1 missing ref)

Current primary-source facts:

- Definition: `frameworks/libs/modules-utils/java/com/android/aconfig/annotations/AssumeTrueForR8.java` —
  `@Retention(CLASS) @Target(METHOD)`, i.e. a **build/optimizer-only annotation** (not runtime-retained).
- Users (read-only jar scan, `unzip -p libs/*.jar | grep`): the annotation is *referenced* by 11 aconfig flags
  jars + `framework.jar` + `android-merged.jar` — the generated `Flags`/`FeatureFlagsImpl` classes annotate
  flag methods with it. The class itself is defined in none of our artifacts (unzip -l shows 0 entries in
  framework.jar/android-merged.jar/keepanno/android_module_lib_stubs and only `AconfigFlagAccessor` in the live
  SDK android.jar).
- AOSP supplies optimizer semantics via `frameworks/libs/modules-utils/java/aconfig_proguard.flags`
  (`-assumevalues`/`-assumenosideeffects` on `@AssumeTrueForR8 boolean *(...) return true` etc.).
- The rejected Task 042 proposal (S3c stage + byte-exact whole-file import) remains frozen; not an option here.

Comparison matrix (no mechanism selected — decision is the user's):

| # | Treatment class | Runtime correctness | Optimization | Maintenance cost | APK-packaging risk | Future verification |
|---|---|---|---|---|---|---|
| 1 | Compile/optimizer annotation artifact (supply `AssumeTrueForR8` class only, e.g. S3b-style bridge or small jar) | none — CLASS retention, never runtime | enables the `-assumevalues` folding only if rules are also imported | one more injected slice or jar to refresh | must stay unpackaged (Task 041 proved 0/35 packaged is achievable) | fresh R8 + APK dex scan for the class |
| 2 | Narrow `-dontwarn com.android.aconfig.annotations.AssumeTrueForR8` | none (warning suppression only) | flag folding stays absent | lowest | none if scope is this one FQN | fresh R8 exit 0 + runtime smoke |
| 3 | Platform/SysUISdk library-class treatment (extend S3b allowlist with the 413-byte class) | none | folding only with rules | small (allowlist entry) | 0-packaging must be re-verified | same as 1 + S5 |
| 4 | Selectively import AOSP assumption semantics (translate the two `-assumevalues` blocks into a Gradle-appropriate rule file, plus the annotation) | none (fold constant booleans — behavior-preserving per AOSP design) | flag folding present, closer to AOSP release behavior | medium: a new rule file + annotation supply must stay in sync | folded flags change dead-code reachability — needs release runtime validation | fresh R8, diff of removed-code report, device flows |
| 5 | Leave folding absent; only silence/resolve the ref | none | none | low | lowest | R8 exit 0 + install/launch |

All five preserve runtime correctness in principle (the annotation is CLASS-retained and the assumption is
only sound for read-only flags); they differ in optimization fidelity and maintenance. Per brief, recommendation
is **needs experiment** (plus **needs history/context** for why AOSP chose whole-file export) — NOT APPROVED.

## 8. Current reference-project comparison

`/home/conv/myspace/CarSystemUIGradle` current files only (comparison, not normative; its AOSP revision is
older — minSdk 32 — and it is a car SystemUI fork).

| Mechanism | CarSystemUIGradle (current) | This project (current) | Transferable lesson |
|---|---|---|---|
| Module topology | 7 modules: `:app`, `:SystemUI-core`, `:SystemUI-shared`, `:SystemUI-plugin`, `:SystemUI-plugin-core`, `:SystemUI-animation`, `:SystemUI-monet` (`settings.gradle.kts:26-46`) | 13 modules incl. `:SystemUI-res` namespace split, unfold/customization/compose/biometrics/common/processor | Reference confirms coarse module merging works, but its topology is a different (older, car) source closure; not transferable |
| SettingsLib delivery | **one** local Maven AAR `com.android.systemui:SettingsLib:1.0.0` (`gradle/libs.versions.toml:95`, 9 AARs total in `libs/maven/`) | 20 Maven AARs (umbrella + 17 res + theme + color) | The reference already operates SettingsLib as a single umbrella Maven AAR — direct evidence that a one-artifact SettingsLib seam is viable in a Gradle build (its resource closure is smaller; experiment still required here) |
| WM-Shell | compileOnly **JAR** `libs/WindowManager-Shell.jar` (`SystemUI-core/build.gradle.kts:93`) | full AAR (code+res) implementation | Reference's jar form loses res; not applicable given our wm-shell res needs |
| iconloader / WifiTrackerLib | single local Maven AARs each (lines 96, 99) | same single-family seam, plus 6 more families | coarse per-family Maven granularity matches |
| Release optimization | `isMinifyEnabled = false` both build types (`app/build.gradle.kts:53-61`, comment cites runtime crashes under R8) | `isMinifyEnabled = true` + `isShrinkResources = true` + 5 rule files | Reference sidestepped R8 entirely — no transferable optimizer practice; validates that our R8 program is beyond reference scope |
| SysUISdk | android.jar merge approach documented in its GRADLE_MIGRATION docs (problems 24-26) | formalized S0-S5 pipeline with tests | our pipeline is the deepened version of the same idea |

Maintainability mechanisms that transfer: single-umbrella SettingsLib, per-family Maven coordinates, and the
framework.jar compileOnly pattern. Mechanisms that do not: its mirror repositories, minSdk-32 closure, no-R8
release, and jar-form WM-Shell.

## 9. Decision ledger

Columns per plan Task 9 Step 1. Modules are summarized (full evidence in §2); artifact rows use family
granularity per brief. Recommendation values are exactly the six allowed categories.

| Item | Present role | Current constraint solved | Maintenance cost | Design classification | Recommendation | Confidence | Evidence needed |
|---|---|---|---|---|---|---|---|
| `:app` | APK producer | bp app/library seam, signing, R8 config | low | bp-aligned module | keep | high | none |
| `:SystemUI-core` | main source module | entry classes + pods + KSP | low | bp-aligned module | keep | high | none |
| `:SystemUI-res` | resource namespace module | independent `com.android.systemui.res.R` | low | bp-aligned module | keep | high | none |
| `:SystemUI-common` | Common+Log+utils JVM module | JVM-only seam | low | bp-aligned module | keep | high | none |
| `:SystemUI-animation` | animation lib module | res owner + animationlib api edge | low | bp-aligned module | keep | high | none |
| `:SystemUI-plugin-core` | plugin annotation API + exported rules | JVM/toolchain seam | low | bp-aligned module | keep | high | none |
| `:SystemUI-plugin-processor` | build-time processor | keeps processor off runtime classpath | low | bp-aligned module | keep | high | none |
| `:SystemUI-plugin` | plugin runtime lib | bcsmartspace source + consumer rules | low | bp-aligned module | keep | high | none |
| `:SystemUI-unfold` | unfold module | own Dagger/KSP graph + aidl | low | bp-aligned module | keep | high | none |
| `:SystemUI-customization` | customization module | res+aidl owner | low | bp-aligned module | keep | high | none |
| `:SystemUI-shared` | shared/keyguard API | largest aidl owner | low | bp-aligned module | keep | high | none |
| `:SystemUI-shared-biometrics` | biometrics module | external-consumer R namespace | low | bp-aligned module | keep | high | none |
| `:SystemUI-compose` | Compose core+scene | Compose toolchain seam | low | bp-aligned module | keep | high | none |
| 13-module topology | overall shape | spec §5.1 retention clause | low | architecture | keep | high | none |
| SettingsLib family (20 Maven AARs + 20 source AARs) | Settings code+res closure | per-target res symbol resolution via 17 POM edges (ADR 0005) | high: 40 artifacts, 20 coordinates, 17 edges, recipe entries | artifact family | consolidate | medium | umbrella merge experiment: duplicate-classes, resource link, R8 81-ref non-regression, device launch |
| WM-Shell (2 AARs) | shell code+res | upstream main/shared manifest+R boundary | low | artifact family | keep | high | optional merge experiment only if user wants fewer coordinates |
| Traceur (2 direct AARs) | tracer code + res | independent res namespace | low | artifact family | keep | high | none |
| WifiTrackerLib | wifi UI classes+res | delivery | Maven stage unproven | delivery | candidate rollback | medium | direct-AAR experiment (dup classes, resource link, debug+release) |
| iconloader | icon loader lib | delivery | Maven stage unproven | delivery | candidate rollback | medium | same |
| setupcompat | setup wizard compat | delivery | Maven stage unproven | delivery | candidate rollback | medium | same |
| LowLightDreamLib | low-light dream lib | delivery | Maven stage unproven | delivery | candidate rollback | medium | same |
| animationlib | framework animation helpers | delivery (multi-consumer) | Maven stage unproven | delivery | needs experiment | medium | direct-AAR across 4 consumer modules |
| Direct-AAR↔local-Maven policy (AGENTS §3.2) | delivery pipeline | ADR 0001 staged-introduction discipline | low | policy (unchanged by this audit) | keep | high | per-family experiments above feed future policy review |
| package_aosp_aar.py | 29 AAR recipes | deterministic family packaging | medium (recipe table scales with targets) | refresh mechanism | keep | high | family recipe consolidation only alongside §10.1 |
| install_aar_to_maven.py | Maven delivery + POM policy | ADR 0001/0005 install | low | refresh mechanism | keep | high | none |
| compilelib/aconfig/monet/viewcapture packaging tools | jar families (13 of 28 root jars; the other 15 are manually maintained — §4.5) | deterministic refresh | low | refresh mechanism | keep | high | none |
| SysUISdk S0-S4 pipeline + S5 | platform adapter | hidden APIs, aidl, private res, dalvik ann, 35 library classes | medium | platform adapter | keep | high | none (Task 041 verified) |
| SysUISdk S3b keepanno slice | optimizer-facing keep annotations | R8 keep-annotation processing + core compile | low | optimizer-only | keep | medium | confirm no future public Maven keepanno coordinate is preferred (rule: official > local) |
| `libs/prebuilts/tracinglib-platform.jar` | tracing classes (implementation in compose, compileOnly in common/shared) | unknown original purpose on current evidence | low | legacy prebuilt | needs history/context | low | targeted history of why platform variant was required |
| `app/proguard_common.flags` / `proguard.flags` / `proguard_kotlin.flags` | release keep rules | reflection/plugin/generated-code contracts | low | optimizer rules | keep | high | none |
| `SystemUI-plugin-core/proguard.flags` | exported plugin rules | plugin annotation retention | low | optimizer rules | keep | high | none |
| `SystemUI-plugin/proguard_plugins.flags` | consumer rules | dynamic plugin APK boundary | low | optimizer rules | keep | high | none |
| AAR consumer rules (absent) | none today | n/a | none | optimizer rules | keep | high | none |
| `AssumeTrueForR8` treatment | none chosen | single remaining R8 missing ref | blocker | optimizer-only annotation | needs experiment | medium (+ needs history/context for AOSP export rationale) | 5-way comparison §7.3; fresh R8 + APK scan + runtime smoke per choice |

Totals: **keep 26** · **simplify 0** · **consolidate 1** · **candidate rollback 4** ·
**needs experiment 2** · **needs history/context 1** (34 ledger data rows; a Task 043 revision-time ad-hoc static verification
command machine-parses §9 row-by-row and asserts these counts; see §13).

## 10. User approval packets

### SettingsLib family delivery — NOT APPROVED
> RESOLVED 2026-08-25 (task 059, user decision): PERMANENTLY CLOSED — the 17 per-target AARs stay;
> the umbrella AAR experiment will not be run.
- Why it exists now: umbrella code AAR (1153 classes) + 17 per-target res-only AARs + SettingsTheme + color,
 delivered via local Maven with 17 mechanical POM edges (ADR 0005), produced by Task 040 to close R8 refs 81→7.
- Current primary-source evidence: §3.1/§3.2 inventories; `SettingsLib-1.0.1.pom` (17 dependencies);
  consumers `SystemUI-core/build.gradle.kts:217`, `SystemUI-res/build.gradle.kts:37,40`; ADR 0005.
- Constraint/guarantee it provides: each SettingsLib Soong res target resolves its own symbols without
  duplicate-resource conflicts; R8 closure currently exact (1 ref left, none SettingsLib).
- Maintenance cost: 40 AARs, 20 coordinates, 17 POM edges, ~40 recipe/install entries per refresh.
- Proposed disposition or experiment: rebuild the family at the coarsest viable seam (one umbrella AAR or the
  smallest namespace-stable set); validate with `:app:checkDebugDuplicateClasses`, `:app:assembleDebug`,
  `:app:minifyReleaseWithR8` (no new missing refs), then install/launch.
- What could be lost: per-target R.txt symbol precision; a resource merge conflict may surface that motivated
  the split (unproven on current evidence); R8 input parity as a diagnostic.
- Exact future static/build/runtime validation: AAR inventory determinism (packaging tool), duplicate-class
  check, debug+release builds, R8 removed-code report diff, device status-bar/notification/QS smoke.
- History needed later (if any): targeted history of whether a direct conflict was actually reproduced before
  the per-target split (Task 040 era), to bound the experiment.

### WifiTrackerLib local-Maven delivery — NOT APPROVED
> RESOLVED 2026-08-25 (task 059, user decision): migrated to direct AAR consumption from `libs/aars/WifiTrackerLib.aar`
> (`:SystemUI-core` wiring switched to `files(...)`; catalog alias and `libs/maven/.../WifiTrackerLib/` tree retired).
- Why it exists now: single-family AAR installed to `com.android.systemui:WifiTrackerLib:1.0.0`.
- Current primary-source evidence: §3.2 row (skeleton POM, 0 deps); sole consumer
  `SystemUI-core/build.gradle.kts:247`; byte-identical to `libs/aars/WifiTrackerLib.aar`.
- Constraint/guarantee it provides: none beyond direct AAR on current evidence.
- Maintenance cost: one coordinate + alias + duplicate byte copy.
- Proposed disposition or experiment: migrate to direct AAR; verify duplicate classes, resource link,
  debug/release builds.
- What could be lost: catalog uniformity (explicitly not justification); AGENTS §3.2 policy exception would be
  needed (policy change requires user approval).
- Exact future validation: same gates as every batch (`:app:assembleDebug` hard gate) + release R8.
- History needed later: none.

### iconloader local-Maven delivery — NOT APPROVED
> RESOLVED 2026-08-25 (task 059, user decision): migrated to direct AAR consumption from `libs/aars/iconloader.aar`
> (1.0.1 bytes unchanged; catalog alias and `libs/maven/.../iconloader/` tree retired).
- Same structure as WifiTrackerLib (sole consumer `SystemUI-core/build.gradle.kts:222`; skeleton POM;
  byte-identical 1.0.1 AAR). Same experiment, same losses (none known beyond uniformity), same validation.
- History needed later: why 1.0.0→1.0.1 was bumped (content change) — only if the seam is actually migrated.

### setupcompat local-Maven delivery — NOT APPROVED
> RESOLVED 2026-08-25 (task 059, user decision): migrated to direct AAR consumption from `libs/aars/setupcompat.aar`
> (catalog alias and `libs/maven/.../setupcompat/` tree retired).
- Sole consumer `SystemUI-core/build.gradle.kts:221`; skeleton POM; single upstream owner
  `external/setupcompat`. Same experiment/validation as WifiTrackerLib.
- History needed later: none.

### LowLightDreamLib local-Maven delivery — NOT APPROVED
> RESOLVED 2026-08-25 (task 059, user decision): migrated to direct AAR consumption from `libs/aars/LowLightDreamLib.aar`
> (catalog alias and `libs/maven/.../LowLightDreamLib/` tree retired).
- Sole consumer `SystemUI-core/build.gradle.kts:230`; skeleton POM; owner `frameworks/base/libs/dream/lowlight`.
  Same experiment/validation.
- History needed later: none.

### animationlib local-Maven delivery — NOT APPROVED
> RESOLVED 2026-08-25 (task 059, user decision): KEPT local Maven by design — multi-module sharing across 3 modules;
> catalog alias is the standard Gradle mechanism. Packet closed as "kept by design".
- Why it exists now: single-family AAR consumed via direct catalog aliases in 3 modules
  (`:SystemUI-customization:63`, `:SystemUI-animation:54`, `:SystemUI-compose:60`) and transitively by
  `:SystemUI-core` through `project(":SystemUI-animation")` (`SystemUI-core/build.gradle.kts:122`).
- Current primary-source evidence: §3.2 row (skeleton POM, 0 deps).
- Constraint/guarantee it provides: catalog-based sharing only; direct AAR would serve identically on current
  evidence.
- Maintenance cost: one coordinate + alias + duplicate copy.
- Proposed disposition or experiment: direct-AAR migration at the 3 alias wiring sites in one change
  (core is covered transitively through `:SystemUI-animation`); standard gates.
- What could be lost: uniformity; nothing technical identified.
- Exact future validation: duplicate-class check, debug+release, no new R8 refs.
- History needed later: none.

### AssumeTrueForR8 treatment mechanism — NOT APPROVED
- Why it exists now: `:app:minifyReleaseWithR8` fails on this single missing CLASS-retained annotation class
  referenced by the 11 aconfig flags jars (§7.3 facts).
- Current primary-source evidence: `frameworks/libs/modules-utils/java/.../AssumeTrueForR8.java`;
  jar reference scan; `aconfig_proguard.flags` upstream semantics; live SDK contains only
  `AconfigFlagAccessor`.
- Constraint/guarantee it provides: none today — it is the blocker.
- Maintenance cost: depends on chosen treatment (§7.3 matrix, 5 options).
- Proposed disposition or experiment: user selects a treatment class after reviewing §7.3; then a bounded
  implementation task with its own plan.
- What could be lost: option 4 (selective assumption import) folds flags and changes dead-code reachability —
  needs release runtime validation; option 2/5 leave folding absent.
- Exact future validation: fresh R8 exit 0 (or documented residual), APK dex scan (annotation must not be
  packaged if bridged), device install/launch + key flows.
- History needed later: why AOSP exports the whole `aconfig_proguard.flags` byte-exact (Task 042 finding)
  — only to inform, not to revive, the rejected proposal.

### libs/prebuilts/tracinglib-platform.jar — NOT APPROVED
> DEFERRED to Release phase (user decision 2026-08-25, task 059)
- Why it exists now: unknown on current evidence; CURRENT_STATE calls it historical legacy for gradual cleanup.
- Current primary-source evidence: `implementation` in `:SystemUI-compose:61`, compileOnly in `:SystemUI-common:38`
  and `:SystemUI-shared:68`; 64 classes; sole `libs/prebuilts/` resident; no producing tool (§4.5).
- Constraint/guarantee it provides: tracing classes at compile time (common/shared) and on the compose runtime
  classpath (implementation).
- Maintenance cost: low but it is the only prebuilt outside the standard delivery rules.
- Proposed disposition or experiment: targeted history lookup (user-approved) of its introduction; then either
  retire (if SysUISdk/aar covers the classes) or migrate into `libs/` root under a packaging tool.
- What could be lost: possibly platform-specific tracing stubs needed at compile time.
- Exact future validation: compile of the three consumers + standard gates after any change.
- History needed later: yes — this packet's core request.

## 11. Unknowns, confidence, and evidence gaps

1. **SettingsLib res-conflict motivation (high impact)** — current files cannot show whether the 17-way
   res split was forced by a reproduced conflict or chosen for Soong-target parity. Needs narrowly scoped history
   (Task 040 era) or a direct umbrella experiment. All §10.1 conclusions are medium confidence until then.
2. **Direct-AAR equivalence for single families (medium impact)** — byte-identity is proven (§3), but Gradle
   metadata/resource-merging differences between `files(*.aar)` and Maven coordinates were not exercised (no
   build allowed). Confidence: medium; the experiments in §10.2-10.6 are cheap and bounded.
3. **AssumeTrueForR8 runtime reachability (medium impact)** — whether any folded-flag path actually changes
   observable behavior under option 4 requires release build + runtime comparison; not determinable statically.
4. **tracinglib-platform.jar origin (low impact)** — no current evidence; history packet filed.
5. **Consumer-rule coverage inside Maven AAR bytes** — verified absent in all 29 source AARs; Maven copies are
   byte-identical so the conclusion transfers; residual risk ~zero.
6. **Reference project's older AOSP revision** — limits transferability of its one-AAR SettingsLib evidence to
   an existence proof, not proof for our revision's larger resource closure.

## 12. Recommended decision sequence

Risk-isolated discussion order (no implementation authorization; per plan Task 9 Step 3):

1. `AssumeTrueForR8` treatment choice (§7.3) — unblocks release R8; smallest blast radius; decides release
   optimization posture early.
2. Optimizer rules audit follow-ups (none currently non-keep; revisit only if new rules are proposed with
   treatment 1/4 above).
3. Delivery adapters: the four candidate-rollback single families (WifiTrackerLib, iconloader, setupcompat,
   LowLightDreamLib) — one family per approved task, each with the standard static+build gates.
4. animationlib direct-AAR experiment (multi-consumer; slightly wider than 3).
5. WM-Shell optional merge experiment (only if the user wants fewer coordinates; currently keep).
6. SettingsLib family consolidation experiment (§10.1) — highest value and highest risk; benefits from the
   learnings and confidence of steps 3-4.
7. SysUISdk stage set (all keep today; no decision needed unless §6 classifications change).
8. Module seams (all keep; no decision needed).
9. tracinglib-platform.jar history lookup + disposition.
10. Device/runtime closure milestones once release R8 is green (spec §9.2).

## 13. Verification record

Self-review against the approved spec (plan Task 10 Step 3):

- Spec §11.1 audit areas: modules (§2), artifact inventory (§3), families (§4), packaging/rebuild seams (§5),
  SysUISdk stages/categories (§6), release rules + remaining annotation (§7), reference comparison (§8) — covered.
- No recommendation is presented as approved: every non-`keep` item has a `### … — NOT APPROVED` packet (§10).
- No historical cause is asserted: SettingsLib motivation, tracinglib origin, and AOSP export rationale are
  explicitly marked unknown / needs history/context (§11).
- SettingsLib is treated as an audit priority with a concrete experiment, not an automatic rollback (§4.1, §10.1).
- Runtime and build validation appear only as future gates inside packets; no result is claimed.
- No byte/configuration parity is used as an acceptance criterion anywhere.
- No Gradle, AGP, package/rebuild/install, SDK apply, or history command was run during this audit. The only
  commands executed were read-only inspection (`rg`/`grep`/`find`/`unzip -l`/`unzip -p`/`sha256sum` via the
  earlier evidence sessions), Python writing only under `/tmp/task043-*`, the fixed ancestry check,
  `git rev-parse HEAD`, `git status --short`, and the static acceptance gates below.

Static acceptance gates (plan Task 10) — actual outputs recorded at commit time in the completion report:
- Completeness gate: `AUDIT_STRUCTURE_PASS modules=13 source_aars=29 maven_aars=27 root_jars=28 prebuilt_jars=1 rules=5`.
- Ledger parse: in addition, a Task 043 revision-time ad-hoc/static verification command (not the persisted
  plan Task 10 gate, which was not modified) machine-parses §9 table data rows (rows starting/ending with `|`,
  excluding header and separator) and asserts row count and recommendation counts exactly — 34 rows: keep=26,
  simplify=0, consolidate=1, candidate rollback=4, needs experiment=2, needs history/context=1 — against the
  Totals line, so any stale total fails the check. It also asserts exactly 8 `### … — NOT APPROVED` packets.
- Scope gate: `SCOPE_PASS` limited to the two allowed documentation paths.
- Placeholder scan: `CONTENT_SCAN_PASS`; `git diff --check` clean.

`Gradle: NOT RUN (read-only audit boundary)`. `Git history consulted: NO`.

Revision record (fixed-range review, same session): corrected §3.2 class counts for the nine code-bearing
Maven AARs (verified by nested-`classes.jar` `.class` count); replaced all 85 truncated 16-hex digests with
full 64-hex SHA-256 values (58 unique digests — Maven copies byte-identical to source AARs); corrected the
`settings.gradle.kts` include span to lines 25-37, the root `build.gradle.kts` injection block end to line 48
(ordering block 26-35), and the SysUISdk stage citations to actual function definition lines
(s0=196, s1=273, s2=287, s3=327, s3b=350, s4=456); corrected `tracinglib-platform.jar` consumers
(implementation in `:SystemUI-compose:61`; compileOnly only in `:SystemUI-common:38`/`:SystemUI-shared:68`);
added root-JAR provider/registration status (13 tool-registered vs 15 manually maintained, incl. the finding
that only 8 of 11 aconfig jars are registered and `PlatformMotionTestingComposeValues.jar` has no producer);
corrected the SettingsLib recipe count to 20 targets. No recommendation changed. All verification was
read-only; no Gradle run, no history consultation.

Second revision (post-review fresh verification): corrected the §9 ledger totals — the table has exactly
34 data rows with parsed recommendation counts keep=26 / simplify=0 / consolidate=1 / candidate rollback=4 /
needs experiment=2 / needs history/context=1 (previously overstated in both the report Totals line and the
issue execution record); a Task 043 revision-time ad-hoc/static verification command now machine-parses §9
rows and counts so a stale total cannot pass (the persisted plan Task 10 gate was not modified); fixed the
§4.4/§10.6 animationlib
consumer wiring (direct aliases in `:SystemUI-customization:63`/`:SystemUI-animation:54`/`:SystemUI-compose:60`;
`:SystemUI-core` consumes it transitively via `project(":SystemUI-animation")` at `SystemUI-core/build.gradle.kts:122`).
Recommendations and all 8 NOT APPROVED packets unchanged.
