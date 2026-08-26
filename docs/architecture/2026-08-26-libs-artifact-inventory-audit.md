# libs/ 全量产物引用图审计（Task 062，只读研究）

> **Scope**: `libs/` 下每一个 git-tracked 产物的引用图审计，为大扫除（删除孤儿文件）提供逐项证据。
> **Mode**: 只读研究 —— 禁止 Gradle 构建、禁止修改任何项目文件（仅本报告 + log + issues 可写）。
> **Date**: 2026-08-26 · **Worker**: task062 (joycode/GLM-5.3) · **Authority**: self-commit (report only, never push)

---

## 0. Executive Summary

| 指标 | 值 |
|---|---|
| git-tracked `libs/` 文件总数 | **105**（28 root jar + 1 root aar + 1 prebuilts jar + 29 aars + 23 maven aar + 23 maven pom） |
| WIRED（被 kts/toml/flags 引用） | **104** |
| ORPHAN（零引用） | **1** → `libs/lifecycle-process-2.4.0-alpha01.aar` |
| DELETE-CANDIDATE | **1**（同上，高置信） |
| UNCERTAIN | **0** |
| 官方 Maven 等价物可替换机会 | **1**（同上 orphan；若将来需要可用 `androidx.lifecycle:lifecycle-process`） |

**一句话结论**：`libs/` 基本干净，仅 `libs/lifecycle-process-2.4.0-alpha01.aar` 是确定孤儿（自首个 commit 起未被任何 build 文件引用，且已有官方 Maven 坐标）；其余 104 个产物全部被 wiring 或为合规的 Maven/源交付输入。chief 预扫的 6 个疑点中 5 个被**证伪**（无孤儿），1 个（prebuilts 仅 tracinglib）被**证实**。

---

## 1. Methodology

1. **Inventory**: `find libs -type f` 全量枚举；`git ls-files libs/` 校对 git-tracked 集（105 文件）。
2. **Hash/size**: `sha256sum` 前 8 位 + `stat -c %s` 字节，逐文件记录。
3. **Wiring grep**: 对每个产物 basename 在 `*.kts` / `*.toml` / `*.flags` 中 `grep -rn` 取 `file:line` 证据；
   另用 `grep -oE 'libs/[A-Za-z0-9_./-]+\.(jar|aar)'` 全量兜底，确认无 `fileTree`/glob 批量引入。
4. **Catalog 解析**: 读 `gradle/libs.versions.toml` 全量 alias，并 grep `libs.systemui.*` 在各 module 的实际消费，区分
   "直接消费 alias" 与 "注册表登记（经 POM 传递）"。
5. **POM 传递验证**: 读 `SettingsLib-1.0.1.pom`，确认 ADR 0005 的 17 条 per-target 依赖边。
6. **字节对齐**: 程序化比对每个 `libs/aars/*.aar` 与 `libs/maven/**.aar` 的 sha256（drift check）。
7. **Git 考古**: 对孤儿候选跑 `git log --follow`；对 task 057 合并跑 `git log --diff-filter=D --name-only`。
8. **官方 Maven 回查**（规则 §1.5）: 用阿里云 google/central 镜像 `maven-metadata.xml` 验证候选坐标；
   sanity 用 `androidx.core:core-ktx`（返回有效 XML 证明镜像对存在 artifact 服务正常）。

**只读保证**: 全程未运行任何 `./gradlew` 任务，未修改任何 `libs/`、`*.kts`、`*.toml`、`*.flags`、源码或 res。

---

## 2. libs/*.jar（根目录，28 个）

> 消费者配置缩写：`impl`=implementation, `co`=compileOnly, `dI`=debugImplementation, `rI`=releaseImplementation,
> `api`=api, `root-JC`=根 `build.gradle.kts` 的 `JavaCompile` 全工程注入。

| # | 路径 | sha8 | size | WIRED? (grep 证据) | 消费者（module:config） | 判定 | 官方 Maven 等价物 |
|---|---|---|---|---|---|---|---|
| 1 | libs/framework.jar | 0fe39d80 | 19902057 | ✅ build.gradle.kts:13; app:158; core:15,151; customization:52; animation:47; unfold:52; plugin-core:24; plugin:53; shared-biometrics:38; common:34; shared:53; compose:55; replace-sdk-jar.gradle.kts:73 | 全 12 module `co` + root-JC | KEEP | 无（AOSP @hide framework 聚合） |
| 2 | libs/framework-statsd.jar | d54489ee | 56445 | ✅ core:16,152 | :SystemUI-core `co` (+ `frameworkJars` var) | KEEP | 无 |
| 3 | libs/android.car.jar | bd5faa75 | 739278 | ✅ core:153 | :SystemUI-core `co` | KEEP | 无（AOSP car @hide） |
| 4 | libs/android_module_lib_stubs_current.jar | af3fc1f1 | 5852413 | ✅ core:155 | :SystemUI-core `co` | KEEP | 无（AOSP module lib stubs） |
| 5 | libs/keepanno-annotations.jar | 056412aa | 20827 | ✅ core:176 | :SystemUI-core `co` | KEEP | **无**（已验证：google 镜像 HTTP 404 + central 镜像 HTTP 404；AOSP `prebuilts/r8/` only —— core 注释 "Maven 上无此 artifact" 正确） |
| 6 | libs/monet.jar | 50f88d51 | 111175 | ✅ core:172; customization:61; build.gradle.kts:16 | :SystemUI-core `impl`, :SystemUI-customization `co`, root-JC internalFlags | KEEP ⚠️见§8.1 | 无（AOSP 内部） |
| 7 | libs/systemui-flags.jar | c0b7d482 | 75736 | ✅ core:173; animation:56; build.gradle.kts:15 | :SystemUI-core `impl`, :SystemUI-animation `co`, root-JC internalFlags | KEEP | 无（AOSP aconfig） |
| 8 | libs/notification-flags.jar | 0f3bfc66 | 14301 | ✅ core:205; build.gradle.kts:18 | :SystemUI-core `impl`, root-JC（classpath 前置） | KEEP | 无（AOSP aconfig） |
| 9 | libs/systemui-aconfig-flags.jar | 5b629580 | 210299 | ✅ core:251; app/proguard_gradle.flags:19(注释) | :SystemUI-core `impl` | KEEP | 无（task 057 合并 14 hidden-twin aconfig） |
| 10 | libs/device-state-flags.jar | cf8f4f09 | 8587 | ✅ core:256 | :SystemUI-core `impl` | KEEP | 无 |
| 11 | libs/launcher3-flags.jar | 5b0f57ee | 31524 | ✅ core:208 | :SystemUI-core `impl` | KEEP | 无 |
| 12 | libs/settingslib-flags.jar | 829fa4e5 | 6311 | ✅ core:180 | :SystemUI-core `co` | KEEP | 无 |
| 13 | libs/settingslib-media-flags.jar | 2f0dfc15 | 9368 | ✅ core:182 | :SystemUI-core `impl` | KEEP | 无 |
| 14 | libs/settingslib-selector-flags.jar | 7c54c1fb | 8884 | ✅ core:214 | :SystemUI-core `impl` | KEEP | 无 |
| 15 | libs/settingslib-widget-flags.jar | e08f2587 | 7944 | ✅ core:211 | :SystemUI-core `impl` | KEEP | 无 |
| 16 | libs/systemui-shared-flags.jar | f3db97ca | 11197 | ✅ core:233; animation:58; shared:66 | :SystemUI-core `impl`, :SystemUI-animation `co`, :SystemUI-shared `co` | KEEP | 无 |
| 17 | libs/wifi-flags.jar | b12ffcc9 | 15664 | ✅ core:239 | :SystemUI-core `impl` | KEEP | 无 |
| 18 | libs/wm-shell-flags.jar | 5a8a7d94 | 13314 | ✅ core:242 | :SystemUI-core `impl` | KEEP | 无 |
| 19 | libs/compilelib-debug.jar | 9d12cbdd | 400 | ✅ core:130 | :SystemUI-core `dI` | KEEP | 无（AOSP compilelib 变体，IS_DEBUG 常量） |
| 20 | libs/compilelib-release.jar | ad605e3f | 400 | ✅ core:131 | :SystemUI-core `rI` | KEEP | 无 |
| 21 | libs/SystemUI-proto.jar | 8f24c6b2 | 34526 | ✅ core:160 | :SystemUI-core `impl` | KEEP | 无（AOSP proto gen；nano runtime 已用 `libs.protobuf.javanano`） |
| 22 | libs/SystemUI-statsd.jar | 3e96c653 | 12259 | ✅ core:168 | :SystemUI-core `impl` | KEEP | 无 |
| 23 | libs/SystemUI-tags.jar | 441b05ed | 2086 | ✅ core:167 | :SystemUI-core `impl` | KEEP | 无 |
| 24 | libs/contextualeducationlib.jar | 21827c3c | 2356 | ✅ core:191 | :SystemUI-core `impl` | KEEP | 无 |
| 25 | libs/msdl.jar | ecbdfe63 | 65750 | ✅ core:135 | :SystemUI-core `impl` | KEEP | 无 |
| 26 | libs/motion_tool_lib.jar | e2f5d0a9 | 93172 | ✅ core:188 | :SystemUI-core `impl` | KEEP | 无 |
| 27 | libs/view_capture.jar | 7ed2eb14 | 93747 | ✅ core:142; shared:74 | :SystemUI-core `impl`, :SystemUI-shared `impl` | KEEP | 无 |
| 28 | libs/PlatformMotionTestingComposeValues.jar | beb021cf | 14053 | ✅ core:194 | :SystemUI-core `impl` | KEEP | 无 |

**小计**：28/28 WIRED，0 orphan。

---

## 3. libs/*.aar（根目录，1 个）—— 唯一孤儿

| 路径 | sha8 | size | WIRED? | git 引入 | 疑似被取代 | 判定 | 官方 Maven 等价物 |
|---|---|---|---|---|---|---|---|
| libs/lifecycle-process-2.4.0-alpha01.aar | fda3954f | 9478 | ❌ **0 引用**（kts/toml/flags 全 0；连 .md 也 0） | `a4bd7f94` 2026-07-18 "feat(build): update Gradle config for AGP 9.2 + Kotlin 1.9.22"（首个 commit，此后未动） | 项目已迁官方 Maven `androidxLifecycle=2.11.0`（runtime-ktx/viewmodel-ktx/service/viewmodel-compose）；catalog 无 `lifecycle-process` alias，无任何使用。此 AAR 是 AGP 9.2 + Kotlin 1.9.22 史前本地 AAR 残留 | **DELETE-CANDIDATE**（高置信） | **`androidx.lifecycle:lifecycle-process`**（Google Maven，latest 2.12.0-alpha01；已验证镜像返回有效 metadata.xml。若将来需要应走官方坐标） |

**证据**：
- `grep -rn 'lifecycle-process' .`（全文件类型，排除自身）→ 0 命中
- `git log --follow -- libs/lifecycle-process-2.4.0-alpha01.aar` → 仅 1 条（`a4bd7f94` 引入，从未修改）
- 阿里云 google 镜像 `androidx/lifecycle/lifecycle-process/maven-metadata.xml` → 有效 XML（`<latest>2.12.0-alpha01</latest>`）

---

## 4. libs/prebuilts/（1 个）

| 路径 | sha8 | size | WIRED? | 消费者 | 判定 | 官方 Maven 等价物 |
|---|---|---|---|---|---|---|
| libs/prebuilts/tracinglib-platform.jar | 90ec3be8 | 115342 | ✅ core:148; compose:61; common:38; shared:68 | :SystemUI-core `impl`, :SystemUI-compose `impl`, :SystemUI-common `co`, :SystemUI-shared `co` | KEEP | 无（chief 2026-08-26 已关闭溯源：AOSP `frameworks/libs/systemui/tracinglib/core`，module `tracinglib-platform`，纯代码无 res，jar 形态正确） |

**prebuilts 目录仅此 1 文件**，无其他残留（chief 疑点 #4 证实）。

---

## 5. libs/aars/（29 个）

分两类：**直接消费**（`files("libs/aars/xxx.aar")`，无 Maven 副本）6 个；**Maven 源输入**（`install_aar_to_maven.py` 的输入，build 经 `libs/maven/` 消费）23 个。

### 5.1 直接消费 AAR（6 个，全部 WIRED）

| 路径 | sha8 | size | WIRED? | 消费者 | task 059? | 判定 | Maven 等价物 |
|---|---|---|---|---|---|---|---|
| libs/aars/TraceurCommon.aar | e358570e | 1053643 | ✅ core:198 | :SystemUI-core `impl` | 否（一直直接） | KEEP | 无 |
| libs/aars/Traceur-res.aar | 868237f6 | 409115 | ✅ core:200 | :SystemUI-core `impl` | 否（一直直接） | KEEP | 无 |
| libs/aars/setupcompat.aar | 0a4222bf | 194066 | ✅ core:221 | :SystemUI-core `impl` | ✅ task 059 | KEEP | 无 |
| libs/aars/iconloader.aar | d6e4f27e | 137664 | ✅ core:223 | :SystemUI-core `impl` | ✅ task 059 | KEEP | 无 |
| libs/aars/LowLightDreamLib.aar | 2a7b0939 | 28914 | ✅ core:231 | :SystemUI-core `impl` | ✅ task 059 | KEEP | 无 |
| libs/aars/WifiTrackerLib.aar | d45bbca9 | 588337 | ✅ core:258 | :SystemUI-core `impl` | ✅ task 059 | KEEP | 无 |

> task 059 的 4 族（WifiTrackerLib/iconloader/setupcompat/LowLightDreamLib）已从 `libs/maven/` 退役，仅 `libs/aars/` 副本由 `files()` 直接消费 —— **无第 5 个残留文件**（chief 疑点 #2 证伪）。
> Traceur×2 不属 task 059 迁移集，但一直就是直接 AAR（从未进 Maven），合规。

### 5.2 Maven 源输入 AAR（23 个，WIRED 经 libs/maven/）

这些 AAR 是 `tools/install_aar_to_maven.py` 的输入（AGENTS.md §3.2 rule 1+5：`libs/` 全量入 git 作再生源）；build 不直接 `files()` 它们，而是经 `libs/maven/` 的 catalog alias / POM 传递消费。**全部 KEEP**（再生源，非孤儿）。**字节与 Maven 副本完全一致**（见 §6 drift check，23/23 MATCH）。

| 路径 | sha8 | size | 对应 Maven artifact | 消费方式 |
|---|---|---|---|---|
| libs/aars/animationlib.aar | 91f85a93 | 19680 | com.android.systemui:animationlib:1.0.0 | catalog `libs.systemui.animationlib`（直接） |
| libs/aars/SettingsLib.aar | 61b480f2 | 4797541 | com.android.systemui:SettingsLib:1.0.1 | catalog `libs.systemui.settingslib`（直接） |
| libs/aars/SettingsLibColor.aar | 41a8d422 | 2033 | com.android.settingslib:color:1.0.0 | catalog `libs.systemui.settingslib.color`（直接） |
| libs/aars/SettingsLibSettingsTheme.aar | 9ee3c671 | 165734 | com.android.systemui:SettingsLibSettingsTheme:1.0.1 | catalog `libs.systemui.settingslib.theme`（直接） |
| libs/aars/WindowManager-Shell.aar | 37e3e786 | 4396336 | com.android.systemui:WindowManager-Shell:1.0.1 | catalog `libs.systemui.wmshell`（直接） |
| libs/aars/WindowManager-Shell-shared.aar | 1633db41 | 222686 | com.android.systemui:WindowManager-Shell-shared:1.0.0 | catalog `libs.systemui.wmshell.shared`（直接） |
| libs/aars/SettingsLibActionButtonsPreference.aar | dd481d9f | 12524 | …:SettingsLibActionButtonsPreference:1.0.0 | POM 传递（SettingsLib POM dep） |
| libs/aars/SettingsLibAdaptiveIcon.aar | 6f2df660 | 2922 | …:SettingsLibAdaptiveIcon:1.0.0 | POM 传递 |
| libs/aars/SettingsLibAppPreference.aar | 2110852a | 67135 | …:SettingsLibAppPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibBannerMessagePreference.aar | 7beca439 | 70129 | …:SettingsLibBannerMessagePreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibBarChartPreference.aar | 4624cf0e | 5789 | …:SettingsLibBarChartPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibButtonPreference.aar | 2801c41c | 18790 | …:SettingsLibButtonPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibFooterPreference.aar | 2a631f84 | 66912 | …:SettingsLibFooterPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibIllustrationPreference.aar | 81cf4dc6 | 5197 | …:SettingsLibIllustrationPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibLayoutPreference.aar | c41e5cf3 | 6194 | …:SettingsLibLayoutPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibMainSwitchPreference.aar | b6147933 | 18525 | …:SettingsLibMainSwitchPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibProgressBar.aar | 5e8c3468 | 9794 | …:SettingsLibProgressBar:1.0.0 | POM 传递 |
| libs/aars/SettingsLibRestrictedLockUtils.aar | 6bb2ecc6 | 73913 | …:SettingsLibRestrictedLockUtils:1.0.0 | POM 传递 |
| libs/aars/SettingsLibSelectorWithWidgetPreference.aar | 87f558c6 | 67343 | …:SettingsLibSelectorWithWidgetPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibSettingsSpinner.aar | ee3aa868 | 4572 | …:SettingsLibSettingsSpinner:1.0.0 | POM 传递 |
| libs/aars/SettingsLibSliderPreference.aar | 1912b297 | 5536 | …:SettingsLibSliderPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibTwoTargetPreference.aar | 7c5fbc43 | 7809 | …:SettingsLibTwoTargetPreference:1.0.0 | POM 传递 |
| libs/aars/SettingsLibUsageProgressBarPreference.aar | 6ab7d889 | 2117 | …:SettingsLibUsageProgressBarPreference:1.0.0 | POM 传递 |

> 17 个 POM 传递子目标在 `libs.versions.toml` 注册了 catalog alias（Task 015/040 标注 "经 SettingsLib POM 传递依赖获得，未被 build 文件直接引用（仅作注册表登记）"），并出现在 `SettingsLib-1.0.1.pom` 的 `<dependencies>` 中（17 条，ADR 0005）。删除任一会破坏 SettingsLib 资源闭包解析。

---

## 6. libs/maven/（23 个 artifact = 23 AAR + 23 POM）

每个 artifact = 1 AAR + 1 POM。消费方式分两类。

### 6.1 直接 catalog 消费（6 个 artifact）

| Maven artifact (group:art:ver) | AAR sha8 | POM sha8 | catalog alias | 消费者（module:config） |
|---|---|---|---|---|
| com.android.systemui:animationlib:1.0.0 | 91f85a93 | f8f4d625 | `libs.systemui.animationlib` | customization:63 `api`; animation:54 `api`; compose:60 `impl` |
| com.android.systemui:SettingsLib:1.0.1 | 61b480f2 | 5c408a12 | `libs.systemui.settingslib` | core:217 `impl`; res:37 `api` |
| com.android.systemui:WindowManager-Shell:1.0.1 | 37e3e786 | 889b8438 | `libs.systemui.wmshell` | core:224 `impl`; animation:50 `co`; shared:63 `co` |
| com.android.systemui:WindowManager-Shell-shared:1.0.0 | 1633db41 | 5da0fd94 | `libs.systemui.wmshell.shared` | core:228 `impl`; animation:51 `co`; shared:64 `co` |
| com.android.settingslib:color:1.0.0 | 41a8d422 | da554d21 | `libs.systemui.settingslib.color` | core:262 `impl` |
| com.android.systemui:SettingsLibSettingsTheme:1.0.1 | 9ee3c671 | adcf5424 | `libs.systemui.settingslib.theme` | res:40 `api` |

### 6.2 POM 传递消费（17 个 artifact，ADR 0005）

均作为 `SettingsLib-1.0.1.pom` 的 `<dependency>` 被传递拉入（资源闭包）；catalog 有 alias 但 build 文件不直接 `libs.xxx` 引用。

`SettingsLibActionButtonsPreference / AdaptiveIcon / AppPreference / BannerMessagePreference / BarChartPreference / ButtonPreference / FooterPreference / IllustrationPreference / LayoutPreference / MainSwitchPreference / ProgressBar / RestrictedLockUtils / SelectorWithWidgetPreference / SettingsSpinner / SliderPreference / TwoTargetPreference / UsageProgressBarPreference`（全部 1.0.0）

**POM 验证**：`SettingsLib-1.0.1.pom` 含 17 条 `<dependency>`，与 ADR 0005 "17 条机械镜像 Android.bp static_libs 的 per-target 依赖边" 完全一致。

### 6.3 字节对齐（drift check）

程序化比对 23 个 Maven AAR 与对应 `libs/aars/` 源：**23/23 sha256 完全一致，零 drift**。
（脚本对 `WindowManager-Shell` 与 `SettingsLibColor` 因 artifactId 命名差异产生过假阳性 ——
`WM-Shell` 的 glob 误匹配到 `-shared` 变体、`SettingsLibColor` 的 Maven artifactId 是 `color`；
两者经原始 sha256 列表人工复核均确认 MATCH：37e3e786↔37e3e786、1633db41↔1633db41、41a8d422↔41a8d422。）

**Maven artifact 判定**：23/23 KEEP，0 orphan。task 059 的 4 族已确认从 `libs/maven/` 删除（chief 疑点 #3 证实：现存 animationlib/SettingsLib 族/WM-Shell，4 族已删）。

---

## 7. Chief 预扫 6 疑点核查结果

| # | 疑点 | 结论 | 证据 |
|---|---|---|---|
| 1 | 11 个分散 flags jar（device-state/launcher3/notification/settingslib×4/systemui-flags/systemui-shared-flags/wifi/wm-shell）task 057 合并后是否全孤儿？ | **证伪** | 11 个**全部仍 WIRED**（core 各 impl/co 行，见 §2 #10-18）。task 057（`e69b9bc7`）合并的是**另一组** 14 个 "framework exportable-aconfig hidden-twin" jar（window/smartspace/android-os/biometrics/content-pm/device-state-feature/net-platform/permission/provider/security/service-controls/service-notification/usb/quickaccesswallet），这 14 个源 jar 已 `git rm`（`git log --diff-filter=D` 证实），不在当前 libs/ 中。现存的 11 个是 per-target flags，与 task 057 合并集**无交集**。 |
| 2 | libs/aars/ 有没有 task 059 四族之外的残留文件？ | **证伪** | 29 个 aar 全部有归属：6 直接消费（4 task 059 族 + Traceur×2 一直直接）+ 23 Maven 源输入。无第 5 个残留。 |
| 3 | libs/maven/ 现存哪些 artifact 树、是否仍被引用？ | **证实** | 23 artifact：6 直接 catalog 消费 + 17 POM 传递（ADR 0005）。task 059 四族（WifiTrackerLib/iconloader/setupcompat/LowLightDreamLib）已从 maven 删除。无孤儿 maven artifact。 |
| 4 | libs/prebuilts/ 除 tracinglib-platform.jar 外还有什么？ | **证实** | 仅 `tracinglib-platform.jar` 1 文件，无其他。 |
| 5 | android_module_lib_stubs_current.jar、SystemUI-tags.jar 引用状态？ | **WIRED** | 前者 core:155 `co`；后者 core:167 `impl`。均 KEEP。 |
| 6 | compilelib-debug/release.jar wiring？ | **WIRED** | debug: core:130 `dI`；release: core:131 `rI`。均 KEEP（AGENTS.md §3.1 compilelib→debug/release JAR，400B 含 IS_DEBUG 常量）。 |

---

## 8. DELETE-CANDIDATE 清单（按置信度排序）

| 风险 | 路径 | 判定 | 删除理由 | 删除后验证命令 |
|---|---|---|---|---|
| 🟢 低 | `libs/lifecycle-process-2.4.0-alpha01.aar` | DELETE-CANDIDATE（高置信） | 全仓零引用（kts/toml/flags/.md 均 0）；自首个 commit `a4bd7f94`(2026-07-18) 引入后从未被任何 build wiring 使用；项目已用官方 Maven `androidx.lifecycle:*` 坐标族（`androidxLifecycle=2.11.0`），此本地 AAR 是 AGP 9.2+Kotlin 1.9.22 史前残留。删除对构建零影响。 | 删除后跑 `./gradlew :app:assembleDebug`（应与基线 `e8aad131` 字节一致 —— **本任务未执行，留待 chief 批准后由执行者验证**）。删除前可再跑 `grep -rn 'lifecycle-process' --include='*.kts' --include='*.toml' --include='*.flags' .` 确认仍 0 命中。 |

> **唯一删除候选**。删除属 red-line（`libs/**`，CHARTER Part 5 未显式列 libs/，但 AGENTS.md §3.2 rule 1 "libs/ 全部提交入 git" 暗示 libs/ 变更需谨慎）—— 建议 chief 在批准大扫除时一并授权，或派独立 task 执行删除+构建验证。本 task 不执行删除（只读授权）。

---

## 9. 官方 Maven 等价物替换机会清单

| 本地产物 | 官方坐标 | 镜像验证 | 建议 |
|---|---|---|---|
| `libs/lifecycle-process-2.4.0-alpha01.aar` | `androidx.lifecycle:lifecycle-process`（Google Maven，latest 2.12.0-alpha01） | ✅ 阿里云 google 镜像返回有效 `maven-metadata.xml` | **无需替换，直接删除**（产物未被引用）。若将来 SystemUI 源码需要 `ProcessLifecycleOwner`，应走官方坐标 `implementation("androidx.lifecycle:lifecycle-process:2.11.0")`（对齐项目 `androidxLifecycle` pin），不要用本地 AAR。 |
| `libs/keepanno-annotations.jar` | （无） | ❌ google HTTP 404 + central HTTP 404 | **保留**。core 注释 "Maven 上无此 artifact" 经验证正确；AOSP `prebuilts/r8/keepanno-annotations.jar` 是唯一来源。 |
| SettingsLib 族 / animationlib / WM-Shell / iconloader / setupcompat / LowLightDreamLib / WifiTrackerLib / Traceur×2 / tracinglib | （无） | ❌ `com.android.settingslib:settingslib` 镜像 404（已抽样验证） | **全部保留**。均为 AOSP fork / @hide / aconfig 产物，无公网等价物（tier②，规则 §1.5）。 |
| `libs/framework.jar` / `framework-statsd.jar` / `android.car.jar` / `android_module_lib_stubs_current.jar` | （无） | N/A（AOSP @hide 聚合） | **保留**（tier②，规则 F）。 |
| 14 个 aconfig flags jar（systemui-flags / notification-flags / device-state / launcher3 / settingslib×4 / systemui-shared / wifi / wm-shell / systemui-aconfig-flags） | （无） | N/A（AOSP aconfig 生成） | **保留**（tier②）。 |

> **既有官方坐标已落地的先例**（非本次发现，仅记录对照）：`protobuf-javanano`（task 027）、`protobuf-javalite`（task 035）、`zxing-core`（task 027）已由本地 jar 迁至官方 Maven 坐标，本地 jar 已退役。本次审计未发现新的"本地 jar 有官方等价物却未迁移"的 case（除 orphan lifecycle-process 外）。

---

## 10. 旁观察（非删除候选，供 chief 知悉）

### 10.1 monet.jar 的 tier① 合规疑问（OUT OF SCOPE）

AGENTS.md §1.5 tier① 清单将 **`monet`** 列为 SystemUI 自有代码（"shared、animation、customization、log、common、unfold、kairos、compose/core、compose/scene、plugin、**monet**"），规则 S 要求**源码复制做源码依赖**。但当前 `libs/monet.jar` 是 jar 形态（core:172 `impl` + customization:61 `co` + root-JC）。

- 这**不是孤儿**（WIRED，删除会破坏构建），故本审计判 KEEP。
- 这**不是官方 Maven 等价物问题**（monet 是 AOSP 内部，无公网坐标）。
- 这是一个潜在的**规则 S（源码化）合规 gap**，但属于"产物形态是否正确"而非"是否应删除"的问题，**超出本次孤儿审计范围**。
- 建议：chief 单独派 task 评估 monet 是否应源码化（参考 `docs/architecture/2026-07-29-systemui-module-source-vs-jar.md`）。

### 10.2 gradle/replace-sdk-jar.gradle.kts 是未接线遗留脚本

- 该脚本**未被任何 `settings.gradle.kts` / `build.gradle.kts` `apply(from=...)`**（`grep -rn 'replace-sdk-jar'` 除文件自身外 0 命中）。
- 它引用 `libs/platform/android.jar`（`createMergedJar` 任务输出），但 **`libs/platform/` 目录不存在、git 未跟踪**（非提交产物，不入本审计清单）。
- 该脚本是早期"动态替换 SDK android.jar"实验的遗留，现已被 SysUISdk 单入口生成器（`tools/build_sysuisdk.py`，ADR 0006）取代。
- **不在 `libs/` 产物审计范围内**，但作为"未接线遗留"提请 chief 知悉，可在后续大扫除中考虑删除该脚本（属 `gradle/` 目录，非 `libs/`，需独立授权）。

### 10.3 libs/systemui-aidl.jar 已删除（历史注释）

`SystemUI-core/build.gradle.kts:349` 注释提及 `libs/systemui-aidl.jar`（"已删…AIDL 是 SystemUI 自有代码，规则 S 要求源码编译"）。该文件**不存在于 libs/**（`find` 无命中），仅为历史注释。非孤儿（文件已不存在），无需处理。注释保留作为决策记录。

---

## 11. 附录 A：全量 sha256+size 清单（105 文件）

见 §2-§6 各表 "sha8" + "size" 列（已逐文件记录）。完整 8 位前缀 sha256 由 `sha256sum` 生成，可由以下命令复现：

```bash
find libs -type f \( -name "*.jar" -o -name "*.aar" -o -name "*.pom" \) | sort | \
  while read f; do printf '%s\t%s\t%s\n' "$(sha256sum "$f" | cut -c1-8)" "$(stat -c %s "$f")" "$f"; done
```

## 12. 附录 B：复现命令

```bash
# 全量 wiring grep（每产物 token）
for tok in framework.jar systemui-flags.jar monet.jar ...; do
  grep -rn --include="*.kts" --include="*.toml" --include="*.flags" -- "$tok" . | grep -v '/.gradle/'
done

# catalog alias 实际消费
grep -rn --include="*.kts" 'libs\.systemui' . | grep -v '/.gradle/'

# aars ↔ maven 字节对齐
for aar in libs/aars/*.aar; do
  base=$(basename "$aar" .aar)
  maven=$(find libs/maven -name "${base}-*.aar" | head -1)
  [ -n "$maven" ] && diff <(sha256sum "$aar") <(sha256sum "$maven")  # 注意 WM-Shell/Color 命名假阳性
done

# 官方 Maven 等价物回查
curl -sS "https://maven.aliyun.com/repository/google/<group-path>/<artifact>/maven-metadata.xml"
```

---

**审计完成**。唯一可执行清理动作：删除 `libs/lifecycle-process-2.4.0-alpha01.aar`（需 chief 授权 + 构建验证）。其余 104 产物全部合规保留。
