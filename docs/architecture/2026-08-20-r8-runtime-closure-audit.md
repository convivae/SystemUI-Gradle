# 2026-08-20 — R8 运行时依赖闭包逐类审计（Task 031，report-only）

> **性质**：只读审计报告。本文不改任何构建文件/依赖/产物；所有修复均为待批准建议。
> 输入：Task 030 的 `app/build/outputs/mapping/release/missing_rules.txt`（140 条，架构师存于
> `/tmp/task030-missing_rules.txt`，实测 140 rules / 140 个唯一 class）。
> 证据基线：AOSP 源码树 `Android.bp`（行号实测）、本项目 `libs/` 产物 `unzip -l` class-set 实测、
> 公网 Maven metadata（curl 实测）。构建：未运行（只读审计，不需要）。

---

## 1. 总数校验（Acceptance #1）

分类脚本对 140 个 missing class 逐条唯一归属：

| 类别 | 数量 | 定义 |
|---|---|---|
| A（真实 APK runtime 闭包缺失） | **135** | AOSP 将这些类作为 APK 的 program/runtime 闭包供给（static_libs 打包闭包；R8 优化后未必每个类都存活于最终 dex）；我方 runtime classpath 缺失 |
| B（bootclasspath / 构建期 / R8-library classpath，非 runtime） | **5** | libcore（bootclasspath）、构建期 CLASS-retention 注解库、或仅存在于 R8 library classpath（keepanno） |
| **合计 / 未分类** | **140 / 0** | A+B=140，无 UNCLASSIFIED |

组级分布：A1=2 A2=2 A3=76 A4=18 A5=2 A6=7 A7=7 A8=9（motiontool 4 + viewcapture 5）
A10=6 A11=4 A12=2（wifi 1 + wmshell 1）；B1=1 B2=2 B3=1 B4=1。
140 行逐类归属表见[附录](#附录-140-个-missing-class-逐类归属)。

## 2. B 类（5 个，非 runtime 闭包，不需要 dex 进 APK）

| # | Class | 宿主 | 证据 | 判定 |
|---|---|---|---|---|
| B1 | `android.compat.annotation.UnsupportedAppUsage` | **构建期 CLASS-retention 注解库（非 device-provided）** | 源码 `tools/platform-compat/java/android/compat/annotation/UnsupportedAppUsage.java`，`@Retention(CLASS)`（实测 L60）；引用点 219 处全部来自 class 文件常量池（annotation 引用），非运行时调用。**Task 032 证实**：AOSP 经 Ch4 传递 header jar 把该注解暴露给 R8；Soong `libs:` 不将其打包，且 framework.jar/android.jar 中均不存在该类 | 构建期注解：无需运行时提供者/解析；供给目标是 R8 classpath（Ch4 机制，Task 032 逐类方案） |
| B2 | `libcore.io.IoUtils`、`libcore.util.NativeAllocationRegistry` | libcore（bootclasspath） | 两类均在 `libs/android_module_lib_stubs_current.jar`（compileOnly，实测 unzip -l）；AOSP 不把它们 dex 进 SystemUI APK | device-provided |
| B3 | `com.android.aconfig.annotations.AconfigFlagAccessor` | 构建期注解 | 源码 `frameworks/libs/modules-utils/java/com/android/aconfig/annotations/AconfigFlagAccessor.java` L37 `@Retention(RetentionPolicy.CLASS)`；由 aconfig 生成代码引用 | build-time only |
| B4 | `com.android.tools.r8.keepanno.annotations.UsesReflection` | **R8 library classpath（非 runtime）** | SystemUI `Android.bp` 将 `keepanno-annotations` 放在 **`libs:`** 而非 `static_libs`（实测 L516-518）→ AOSP **不 dex 进 APK**，仅供编译期与 R8 读取。我方源码（`SystemUIAppComponentFactoryBase.kt`、`LockscreenFragment.java`、`TunerFragment.java`）引用该注解，R8 解析引用时报警 | 编译期 + R8 library classpath；**禁止**改普通 implementation（会把注解 jar dex 进 APK，违背 AOSP 语义） |

**B1–B3 处理原则（遵从用户政策，不由本审计预设方案）**：这 4 个 missing class/rule
（B1×1 + B2×2 + B3×1）**全部移交 Task 032 的逐类处置计划**，本审计与实施批次均不对其预设
dontwarn。用户政策明确：B1/B2 **不允许 dontwarn**，优先结构性 classpath/SysUISdk 方案
（如补全 R8 可见的 stub/SDK 产物）；仅 B3（AconfigFlagAccessor）在无受支持的桥梁时**才可能**
以恰好 1 条与 missing_rules.txt 对应行一字不差的 `-dontwarn` 兑底。**不得**因此放松任何 A 类修复。

**B4 处理方向（另案调查，不在本审计断言）**：保守决策是不 casually dontwarn——但
“suppress 警告后 R8 必然读不到 keepanno、keep 语义必然丢失”这一具体行为**未被证实**，本文
不以事实口吻断言语义丢失。它是一个**待验证的开放风险**：dontwarn 是否影响 R8 对 keepanno
注解的消费/keep 语义，必须在 Batch 6 对照 R8 输出与被保留的反射目标实测，不能未经 R8
源码/实验就断言。候选机制（release-only 的 program/library 输入，如把注解 jar 喂给 R8 的
classpath 而不进 dex）同样待调查验证。Task 032 维持其原有 scope（B1–B3 四个 platform 类），
B4 不并入 Task 032。

## 3. A 类组级总表（Acceptance #2 骨架）

| # | 缺失（数量） | owning Soong module（bp 证据） | 通向 SystemUI 的 edge | 资源 | 形态判定 | 我方现状 scope | 产物实测 | 根因 |
|---|---|---|---|---|---|---|---|---|
| A1 | `systemui.FeatureFlags{,Impl}`（2） | `com_android_systemui_flags_lib`（`aconfig/Android.bp:46`） | SystemUI-core `static_libs` L458 | 无 | jar | implementation `libs/systemui-flags.jar` | 仅 `Flags.class`（1 类） | header jar 未换 javac 全量 jar |
| A2 | `server.notification.FeatureFlags{,Impl}`（2） | `notification_flags_lib`（`services/core/.../notification/Android.bp:6`） | SystemUI-core L506 | 无 | jar（本地 Maven） | implementation `libs.android.server.notification.flags` | 仅 `Flags.class` | 同 A1，2026-07-23 旧批次 |
| A3 | SettingsLib 76 类（43 代码 + 31 子命名空间 `R$*` + 2 aconfig flags） | 主模块（`SettingsLib/Android.bp:11` 主 target；L71-80 为主 src/resources 声明）+ 三个代码所属子 target：`SettingsLib/DeviceStateRotationLock/Android.bp`、`SettingsLib/SettingsTheme/Android.bp`、及各 per-target 资源子模块（见 §5.1 逐类 owner） | SystemUI-core L457 | 有 | AAR（已用本地 Maven） | implementation `libs.systemui.settingslib` + compileOnly `SettingsLib-full.jar` | AAR 780 类 vs full.jar 372 类，交集 **0** | AAR 打包漏主 src、漏 DeviceStateRotationLock/SettingsTheme 代码、漏子命名空间 R、漏 2 个 aconfig lib |
| A4 | WM-Shell proto 18 类（lite 15 + nano 3） | `WindowManager-Shell-lite-proto`（`Shell/Android.bp:148`）、`WindowManager-Shell-proto`（L138） | WM-Shell `static_libs` L188-189 → SystemUI-core L448 | 无 | AAR（并入 WM-Shell） | implementation `libs.systemui.wmshell` | AAR 1848 类：`desktopmode/persistence/` proto 消息 0、`education/data/` 0、`nano/` 0、`protobuf/` 0 | proto javac 产物未合并进 AAR |
| A5 | `protobuf.GeneratedMessageLite{,$Builder}`（2） | soong `libprotobuf-java-lite`（lite proto 运行时） | A4/`motion_tool_proto`/`view_capture_proto` 的 static_libs | 无 | **官方 Maven**（tier③） | 无 | 无任何干净产物（仅 view_capture.jar 污染携带） | 缺运行时依赖声明 |
| A6 | `systemui.monet.*` 4 + `libmonet.*` 3（7） | `monet`（`frameworks/libs/systemui/monet/Android.bp:22`）、`libmonet`（`external/libmonet`） | SystemUI-core L494-495 | 无 | jar | **compileOnly** `libs/monet.jar`（L161） | jar 共 83 类 = monet+libmonet 56（`systemui.monet` 9 + `libmonet` 47）+ 27 个 error_prone_annotations 类（源自 `external/libmonet/Android.bp` 的 `static_libs: ["error_prone_annotations"]`，属 AOSP static 闭包，非污染）；7 个缺失类全在内 | scope 错误（AOSP static_libs=APK 打包闭包） |
| A7 | `traceur.*` 7（含 `traceur.res.R$*` 2） | `TraceurCommon`（`packages/apps/Traceur/Android.bp:28`）、`Traceur-res`（L41，`android_library` + `resource_dirs:["res"]`，实测 res 下 105 个资源文件；static_libs 含 androidx.leanback ×2 + legacy-preference-v14） | SystemUI-core L502-503 | **有（Traceur-res 105 个 res 文件）** | **AAR（含 res，保留 namespace）**——规则 R/F：res 必须随 AAR 走，不允许 runtime-only R.jar 顶替 | **compileOnly** `TraceurCommon.jar` + `traceur-res-R.jar`（L181-182，仅 R 类、无资源文件，不能闭包运行时资源） | TraceurCommon.jar 纯净（仅 `com/android/traceur`）；但其 static_libs 含 `perfetto_config_java_protos` + androidx.appcompat/legacy-support-v4（未随 jar 携带，见 §3.1） | 产物形态错（应为 AAR）+ scope 错误 |
| A8a | `motiontool.*` 4 | `motion_tool_lib`（`frameworks/libs/systemui/motiontoollib/Android.bp:40`） | SystemUI-core L504 | 无 | jar | **compileOnly** `motion_tool_lib.jar`（L173） | jar 恰含 8 个 `com/android/app` 类（4 缺失全在内），无污染；但 static_libs 含 `view_capture` + `motion_tool_proto` → 闭包依赖 viewcapture/protobuf（见 §3.1） | scope 错误（且翻转必须在 viewcapture/protobuf 就位之后） |
| A8b | `viewcapture.*` 5 | `view_capture`（`frameworks/libs/systemui/viewcapturelib/Android.bp:34`）、`view_capture_proto`（L21） | SystemUISharedLib `static_libs`（`shared/Android.bp:73` `:view_capture`）；另被 motion_tool_lib static 依赖 | 无 | jar | **compileOnly** `view_capture.jar`（core L136 + shared L70） | 含全部缺失类，但为 FAT jar（androidx/kotlin/kotlinx/protobuf-lite 全量混入） | scope 错误 + 产物污染（需先重打包再翻转） |
| A10 | `msdl.*` 6 | `msdl`（`frameworks/libs/systemui/msdllib/Android.bp:21`） | SystemUISharedLib `static_libs` `:msdl`（`shared/Android.bp:72`） | 无 | jar | **compileOnly** `libs/msdl.jar`（core L135） | jar 纯净（46 个 `com/google/android/msdl` 类，6 缺失全在内） | scope 错误 |
| A11 | launcher3 4（`Flags` + 3 icons Kotlin 类） | `iconloader_base`（`iconloaderlib/Android.bp`）、`com_android_launcher3_flags_lib`（`Launcher3/aconfig/Android.bp:28`，iconloader_base static_libs） | SystemUI-core L491（另 WM-Shell bp L185 同源） | iconloader 自带 res | AAR + jar | implementation `libs.systemui.iconloader` | AAR 59 类**全为 Java 产物**，Kotlin 类 0、`launcher3/Flags` 0（全 libs 实测无此 flags） | AAR 选错 soong 产物（漏 kotlin 合并）；flags jar 缺失 |
| A12 | `wifi.flags.Flags` 1 + `wm.shell.Flags` 1 | `wifi_aconfig_flags_lib`（`WifiTrackerLib/Android.bp:28` static）、`com_android_wm_shell_flags_lib`（`Shell/aconfig/Android.bp:11`，WM-Shell static L186） | WifiTrackerLib → core L447；WM-Shell → core L448 | 无 | jar | **compileOnly** `wifi-flags.jar`（L212）/ `wm-shell-flags.jar`（L215） | 两 jar 各含**完整的 5 类生成 runtime 集**：`CustomFeatureFlags`、`FakeFeatureFlagsImpl`、`FeatureFlags`、`FeatureFlagsImpl`、`Flags`——缺失类 `Flags` 均在（实测 unzip -l 逐类列出）；AAR 内无重复（实测 0） | scope 错误 |

注：A3 的 76 = 非 R 代码类 43（`volume.*` 17、`bluetooth` 3、其余 23）+ 子命名空间 `R$*` 31
+ aconfig flags 2（`widget.flags.Flags`、`selectorwithwidgetpreference.flags.Flags`）。

> keepanno `UsesReflection` 原误归 A9，已改判 B4（SystemUI bp `libs:` 非 static_libs，实测
> L516-518），见 §2。**类计数口径**：本文所有 AAR/jar 类数统一为可复现方法
> `unzip -l <classes.jar> | grep -c '\.class$'`（不含 META-INF/versions、无 module-info 情况下
> 与总条目一致）。

### 3.1 传递 static 闭包审计（超出 missing_rules 命名类，实施必须覆盖）

R8 missing_rules 只列出当前 shrink 触及的类；翻转 scope 后 R8 会触达更深的闭包，**新 missing
类不是可接受的计划内遗漏**。以下三条链已在 AOSP bp 实测：

1. **TraceurCommon**（`Traceur/Android.bp:28-38`）：`static_libs = [androidx.appcompat_appcompat,
   androidx.legacy_legacy-support-v4, perfetto_config_java_protos]`。前两个由官方 Maven
   androidx 坐标覆盖（tier③）；`perfetto_config_java_protos` 无任何本地产物——翻转后可能新报
   perfetto config 类缺失，需在 Batch 4 一并打包/声明。
2. **motion_tool_lib → view_capture + motion_tool_proto**（`motiontoollib/Android.bp:40-55`）：
   `motion_tool_proto`（同文件 L21-35）`static_libs = [libprotobuf-java-lite, view_capture_proto]`，
   且 include viewcapturelib 的 proto 目录 → motiontool 的 4 个缺失类中的 proto 消息类由
   `motion_tool_proto` 生成，闭包还含 `view_capture_proto`（`viewcapturelib/Android.bp:21-33`）
   与 protobuf-lite runtime。**因此 motiontool 不得早于 viewcapture/protobuf 就位**（Batch 3 内
   有序：javalite + view_capture 先、motion_tool 后）。
3. **Traceur-res**（`Traceur/Android.bp:41-52`）：`static_libs = [androidx.leanback_leanback,
   androidx.leanback_leanback-preference, androidx.legacy_legacy-preference-v14]` ——
   资源型 AndroidX 依赖，走官方 Maven 坐标（tier③），AAR 重打包时验证资源合并无冲突。

### 3.2 每组 修复→批次 / 重复类风险 / 清理项 映射

| 组 | 修复→批次 | 重复类风险 | 清理项 |
|---|---|---|---|
| A1/A2 | Batch 2（aconfig javac 全量 jar） | A2 重产后与旧本地 Maven jar 同类 → 迁移直引时删旧目录 | A2 本地 Maven jar/POM/alias 全套移除（§7 Batch 2） |
| A3 | Batch 4（主 SettingsLib AAR：主 src javac+kotlin + DeviceStateRotationLock javac + 31 子命名空间 R；SettingsTheme 2 类由 SettingsLibSettingsTheme AAR **自身**补回 javac+kotlin，不并入主 AAR；2 flags 以独立 runtime jar 在 Batch 2） | 主 src 与 `SettingsLib-full.jar` 双来源 → 同批删 full.jar；主 AAR 不得含 SettingsTheme 两类（防双产物重复类）；7 条 POM 边不动 | `SettingsLib-full.jar` 退役；`git grep` 归零 |
| A4 | Batch 4（AAR 并入 lite-proto + proto javac） | launcher3 flags 双入（WM-Shell bp L185 同源）→ flags 只由独立 jar 供给，禁止并入 AAR | 无 |
| A5 | Batch 3（官方 `protobuf-javalite:3.21.12`） | 与 view_capture.jar 内嵌 lite runtime 重复 → 同批换干净重打包 jar | 旧 FAT view_capture.jar 替换 |
| A6 | Batch 1（scope 翻转） | errorprone 27 类为 libmonet static 闭包（AOSP 同样作为 APK 打包闭包供给，R8 可按需 shrink），无其他产物重复（实测）→ **保留，不剥离** | 无 |
| A7 | Batch 4C（Task 038，已完成：Traceur 双 AAR 直接引入——TraceurCommon 640 类含 perfetto_config_java_protos 625 ∪ traceur 15；Traceur-res 105 res + namespace；fresh R8 实测 88→81，removed 恰为 7 个 traceur 目标、added=0；原计划归 Batch 4，实际拆为 4C 提前落地） | res 与 SystemUI-res 合并冲突：实测无冲突（processDebugResources 通过）；perfetto proto 闭包已补齐（Batch 3 javalite 4.35.1 底座） | `traceur-res-R.jar` + `TraceurCommon.jar` 均已退役 |
| A8 | Batch 3（有序：javalite+view_capture → motion_tool） | FAT jar 内 androidx/kotlinx 与官方坐标重复 → 必须先重打包再翻转 | 旧 FAT jar 替换；core+shared 两处同改 |
| A10 | Batch 1（scope 翻转） | 无（jar 纯净，46 类全 msdl） | 无 |
| A11 | Batch 2（flags jar）+ Batch 4（AAR javac+kotlin 合并） | 与 WM-Shell 侧同源 flags → 同 A4 约束 | 无 |
| A12 | Batch 1（scope 翻转） | 无（AAR 内无重复，实测 0） | 无 |

## 4. 官方 Maven 判定（Acceptance #3，全部 curl 实测 2026-08-20）

| 候选 | 判定 | 证据 |
|---|---|---|
| `com.google.protobuf:protobuf-javalite` | **tier③ 可用，版本建议 3.21.12** | AOSP 侧 `external/protobuf/java/lite/pom.xml` `<version>3.21.12</version>`（上游 pin 版）；Maven Central `maven-metadata.xml` latest 4.36.0-RC2，`3.21.12/protobuf-javalite-3.21.12.jar` 实测存在（HTTP 200 目录页列出）。生成代码与 runtime 同版本最稳妥，建议钉 3.21.12 而非 latest |
| keepanno-annotations | **tier② 本地 jar；compileOnly scope 本身与 AOSP `libs:` 语义一致（AOSP 不 dex）**，错在 AGP R8 看不到它（visibility 问题，非 scope 问题；处置见 §2 B4/Batch 6） | Maven Central search `q=keepanno` numFound=0；Google Maven `com/android/tools/keepanno-annotations` 404。上游只随 `prebuilts/r8/keepanno-annotations.jar`（java_import）分发 |
| msdl / libmonet / monet | **tier② 本地 jar（产物形态正确，仅 scope 需翻转为 implementation）** | Maven Central search `a:msdl`、`libmonet` numFound=0；均为 AOSP 树内库（`frameworks/libs/systemui/msdllib`、`external/libmonet` 等） |
| Traceur | **tier② 但形态是含 105 个 res 的 AAR（非 jar、非纯 scope 问题）**，见 §3 A7/Batch 4 | AOSP 树内 `packages/apps/Traceur`，无公网坐标 |
| `com.google.android.material` 等 androidx/material | 不在本次 missing 集 | 无需动作 |

## 5. 三个不完整 AAR 的 class-set 证据（Acceptance #4）

### 5.1 SettingsLib.aar（780 类）vs 应有闭包

- **43 个非 R 代码类的精确 owner 拆分（实测源码定位）**：
  - **40 个主 src**（`SettingsLib/Android.bp:73-77` `srcs: ["src/**/*.java","src/**/*.kt",
  "src/**/I*.aidl"]`；抽查：`src/com/android/settingslib/wifi/WifiUtils.kt`、
  `qrcode/QrCodeGenerator.kt`、`fuelgauge/Estimate.kt`、`volume/data/repository/*`、
  `RestrictedPreferenceHelperProvider.kt` 等，全部在 `libs/SettingsLib-full.jar` 372 类内）。
  full.jar（纯主 src 产物）与 AAR 780 类**交集为 0**（`comm -12` 实测）→ AAR 打包时把主 src
  javac/kotlin 产物整个落下了；full.jar 只以 compileOnly 顶编译期（core L191）。
  - **`devicestate.PosturesHelper` 1 个**：属 `SettingsLib/DeviceStateRotationLock/src` 子模块
  （`DeviceStateRotationLock/Android.bp`），**不在主 src，也不在现有任何产物**（AAR/full.jar
  均 0 命中）。
  - **`GroupSectionDividerMixin` + `SettingsThemeHelper` 2 个**：属 `SettingsLib/SettingsTheme/src`
  子模块 Kotlin（`SettingsTheme/Android.bp`）；现有 `SettingsLibSettingsTheme.aar`（本地 Maven）
  **只有资源、classes.jar 为空**（实测），代码缺失。**归宿是 SettingsLibSettingsTheme AAR 自身**
  （独立资源 owner 的 Soong target；现有 Gradle 图由 `SystemUI-res` 经
  `api(libs.systemui.settingslib.theme)` 消费，`SystemUI-res/build.gradle.kts:40`），**不并入主
  SettingsLib AAR**，避免同类双产物。
  → 即：**不要把 43 个都当主 src，也不要认为子模块代码已全在 AAR，更不要把 SettingsTheme
  代码合进主 AAR**。
- **子命名空间 R 缺失（31 个）**：AAR 已含子模块代码（`BannerMessagePreference`/`MainSwitchBar`/
  `SettingsSpinnerPreference` 等 9 类实测在 AAR），但其引用的 `com.android.settingslib.widget.
  {mainswitch,spinner}.R$*`、`widget.preference.{app,banner,barchart,button,footer,illustration,
  slider,usage}.R$*` 在**任何产物中都不存在**（全 libs 扫描实测 0 命中）。Soong 下这些 R 由各
  per-target `android_library`（如 `SettingsLibMainSwitchPreference`，`MainSwitchPreference/
  Android.bp`，`use_resource_processor: true`）生成；合并 AAR 需把各子模块 R jar 一并合入。
- **aconfig flags 缺失（2 个）**：`settingslib_illustrationpreference_flags_lib`（`IllustrationPreference/
  Android.bp:46`，package `com.android.settingslib.widget.flags`）与
  `settingslib_selectorwithwidgetpreference_flags_lib`（`SelectorWithWidgetPreference/Android.bp:45`）
  是 SettingsLib 子模块的 static_libs；两个 Flags 类全 libs 无产物。
- **资源 owner/冲突**：AAR 已是本地 Maven 形态（ADR 0005 的 7 条 POM 边维持不变）；重打包只需
  动 classes.jar 合并，res 闭包不变 → 无新资源冲突面。

### 5.2 WindowManager-Shell.aar（1848 类）缺 proto 生成类

- 缺失 18 类的 owner：`WindowManager-Shell-lite-proto`（`Shell/Android.bp:148-158`，
  `desktopmode/{education/data/proto,persistence}/*.proto`，type lite）生成
  `desktopmode.persistence.{Desktop,DesktopTask,DesktopRepositoryState,DesktopPersistentRepositories}*`
  与 `education.data.WindowingEducationProto*`；`WindowManager-Shell-proto`（L138-144，type nano）
  生成 `wm.shell.nano.{HandlerMapping,Transition,WmShellTransitionTraceProto}`。
- 两者都是 WM-Shell `static_libs`（L188-189）→ AOSP 将其纳入 APK 打包闭包；WM-Shell 自身 Kotlin 代码
  （`DesktopUserRepositories.kt`、`AppHandleEducationController.kt` 等，实测在 AAR 内）直接引用
  这些 proto 类。AAR 内 4 项 grep 全 0（见 §3 A4 行）→ `package_aosp_aar.py` 当时只取了
  WM-Shell 主模块 javac/kotlin，未并 proto 子模块产物。
- nano 运行时已由官方 `protobuf-javanano:3.1.0`（core L218）覆盖；lite 运行时即 A5。

### 5.3 iconloader.aar（59 类）缺 Kotlin 与 launcher3 flags

- AOSP `iconloaderlib/Android.bp`（iconloader_base）：`srcs: ["src/**/*.java","src/**/*.kt"]`；
  实测 `src/com/android/launcher3/icons/ThemedBitmap.kt`（内声明 `IconThemeController`）、
  `mono/ThemedIconDrawable.kt` 均在源码树。AAR 59 类全为 Java 产物（3 个缺失 Kotlin 类 0 命中）。
- `com_android_launcher3_flags_lib`（`Launcher3/aconfig/Android.bp:28`）是 iconloader_base 的
  static_libs；`launcher3/Flags` 在全部 libs 产物中 0 命中。
- 修复需把 soong 的 **javac+kotlin 合并产物**（先例：WM-Shell-shared 已是 javac+kotlin 合并）作为
  classes.jar 重打包，并新增 launcher3 flags aconfig jar。注意该 flags lib 同时被 WM-Shell
  static_libs（bp L185）消费——A4 重打包时不可重复合入，由独立 jar 统一供给。

## 6. compileOnly 逐项判定（Acceptance #5，禁止一刀切 implementation）

| compileOnly 项 | 判定 | 依据 |
|---|---|---|
| framework.jar / framework-statsd.jar / android.car.jar / android_module_lib_stubs_current.jar | **保持 compileOnly**（B2 相关） | bootclasspath，device-provided |
| settingslib-flags.jar | **保持 compileOnly** | AOSP `SettingsLib/Android.bp:67-69` 注释明示 "This flag library has been added in frameworks jar"（`libs:` 非 static） |
| msdl.jar / monet.jar / wifi-flags.jar / wm-shell-flags.jar | **AOSP 为 static runtime → 应改 implementation**（Batch 1） | static_libs edge 见 §3 对应行；四 jar 产物纯净（实测） |
| view_capture.jar（core+shared） | **应改 implementation（Batch 3）**，但改 scope 前必须先用 soong javac 产物重打包去 FAT 污染 | 否则与官方 androidx/kotlinx 依赖 D8 重复类冲突（§3.1 链 2） |
| motion_tool_lib.jar | **应改 implementation（Batch 3，后置于 view_capture/protobuf）** | static_libs 依赖 view_capture + motion_tool_proto → view_capture_proto + protobuf-lite（§3.1），先翻转会新报 missing |
| TraceurCommon.jar / traceur-res-R.jar | **应整体换成 Traceur AAR（Batch 4）**，不是简单 scope 翻转 | Traceur-res 是带 105 个 res 的 `android_library`（规则 R/F：AAR 才能闭包资源）；TraceurCommon 闭包还缺 perfetto proto 与 AndroidX static（§3.1 链 1/3）；直接 AAR 优先，确认冲突才入本地 Maven |
| keepanno-annotations.jar | **保持 compileOnly，另案解决 R8 classpath（B4）** | AOSP `libs:` 非 static_libs → 不 dex；需要 release-only R8 classpath 方案（§2 B4，待调查断言） |
| SettingsLib-full.jar | **临时保留 compileOnly，A3 修复后退役** | 它是主 src 的唯一现有载体；AAR 补齐后同 class 双来源 → 必须删除（先例：server-notification-flags 源码 stub 遮蔽 jar 事故，docs/issues/2026-07-28） |

## 7. 实施批次（Acceptance #6，依赖序；每批均为独立可验收 PR 粒度）

> 闭包纪律：每批验收后重跑 R8，新 missing 类按 §5 诊断流程归类处理；**翻转后出现的新 missing
> 不是可接受的计划内遗漏**（§3.1 三条链即为此前置审计）。keepanno（B4）不在任何批次内改
> scope，另案处理（§2）。

### Batch 1 — 纯 scope 翻转（4 行，零重打包；A6+A10+A12 = 15 类解锁）
- 改动：`SystemUI-core/build.gradle.kts` 中 msdl（L135）、monet（L161）、wifi-flags（L212）、
  wm-shell-flags（L215）compileOnly → implementation。
- allowed_paths：`SystemUI-core/build.gradle.kts`、`docs/issues/` 记录。
- 验收：147 tests OK；`assembleDebug` dex 抽查（`com.android.systemui.monet.ColorScheme`、
  `com.google.android.msdl.domain.MSDLPlayer`）；missing_rules 140 → 125。
- 清理项：无（monet 的 errorprone 27 类属 AOSP static 闭包，保留不剥离，见 §3.2 A6）。

### Batch 2 — aconfig javac 全量 jar + notification-flags 直引迁移（A1+A2+A11-flags+A3-flags = 7 类解锁）
- 改动：`tools/package_aconfig_jars.py` 重产 A1 `systemui-flags.jar`；**A2 从本地 Maven jar 迁移为
  直引 `libs/notification-flags.jar`**——删除 `libs/maven/com/android/server/notification-flags/`
  目录（JAR+POM）、`libs.versions.toml` alias、settings/catalog 引用及 AGENTS §3.2 文档行，
  改用 `implementation(files("libs/notification-flags.jar"))`（**禁止**对 JAR 使用
  install_aar_to_maven.py——该工具只服务于 AAR）；新增 launcher3-flags、settingslib-widget-flags、
  settingslib-selector-flags 三个直引 jar。
- allowed_paths：`tools/package_aconfig_jars.py`、`libs/systemui-flags.jar`、`libs/notification-flags.jar`
  （新）、上述三个新 flags jar、`libs.versions.toml`、`settings.gradle.kts`、
  `SystemUI-core/build.gradle.kts`、删除的 `libs/maven/com/android/server/` 目录、`docs/`。
- 验收：各 jar unzip -l 含 `FeatureFlagsImpl`/`FakeFeatureFlagsImpl`（对齐 08-12
  systemui-shared-flags 先例）；147 tests；missing_rules 125 → 118。
- 清理项：catalog alias 与文档中 notification-flags Maven 行同步删除；`git grep notification-flags`
  仅剩直引与新 jar。

### Batch 3 — 官方 protobuf-javalite + view_capture 干净重打包 + motion_tool（有序；A5+A8 = 11 类解锁）
- 改动（**批内有序**）：
  1. `gradle/libs.versions.toml` 新增 `com.google.protobuf:protobuf-javalite:3.21.12`（A5，implementation）；
  2. `view_capture.jar` 用 soong javac 产物重打包（仅 `com/android/app/viewcapture/**` +
     `view_capture_proto` 生成类，去除 androidx/kotlin/kotlinx/protobuf-lite 混入），core+shared 两处
     compileOnly → implementation（A8b）；
  3. `motion_tool_lib.jar` 重打包为 `motiontool/**` + `motion_tool_proto` 生成类（其 proto 引用
     viewcapturelib proto 目录，见 §3.1 链 2），compileOnly → implementation（A8a）——**必须在 1/2 之后**。
- allowed_paths：`libs.versions.toml`、`tools/package_aosp_aar.py`（或新打包脚本）、
  `libs/view_capture.jar`、`libs/motion_tool_lib.jar`、`SystemUI-core/build.gradle.kts`、
  `SystemUI-shared/build.gradle.kts`、`docs/`。
- 验收：`assembleDebug` 无 D8 重复类（`:app:checkDebugDuplicateClasses`）；dex 抽查
  `com.android.app.viewcapture.ViewCapture`、`com.android.app.motiontool.MotionToolManager`；
  missing_rules 118 → 107。
- 清理项：旧 FAT view_capture.jar 替换后确认 shared 模块编译不回归。

### Batch 4 — 五个产物的 AAR 闭包重打包（A7+A3 剩余 74+A4+A11 Kotlin 3 = 102 类解锁，风险最高）
- 改动：`tools/package_aosp_aar.py` 扩展合并逻辑——
  1. **Traceur AAR（新产物）**：TraceurCommon（含 perfetto_config_java_protos 闭包，§3.1 链 1）+
     Traceur-res 的 105 个 res 与 namespace；**直接 AAR 引入优先**，确认资源/依赖冲突后才经
     install_aar_to_maven.py 入本地 Maven（ADR 0001 纪律）；
  2. **主 SettingsLib AAR**：主 src javac+kotlin（40 缺失类）+ DeviceStateRotationLock javac
     （`PosturesHelper`，无资源 static 子模块）+ 31 个子命名空间 R jar；**不得并入 SettingsTheme
     代码**（见步 3；验收含主 AAR 无 `GroupSectionDividerMixin`/`SettingsThemeHelper` 的重复类
     检查）。Batch 2 的两个 settingslib flags jar 是 AOSP static runtime 依赖，以**独立 runtime
     implementation jar** 供给而非并入任何 AAR，与本批互不阻塞；
  3. **SettingsLibSettingsTheme AAR（独立资源 owner，不并入主 AAR）**：在其自身产物内补回
     SettingsTheme javac+kotlin（`GroupSectionDividerMixin`/`SettingsThemeHelper`，修复空
     classes.jar），资源保持字节级不变；它是独立 Soong target，现有 Gradle 图由
     `SystemUI-res` 经 `api(libs.systemui.settingslib.theme)` 消费——坐标不变则消费方**零配置
     改动**；
  4. WM-Shell AAR：并入 lite-proto 与 proto 两个 javac jar（launcher3 flags 不得并入，§3.2 A4）；
  5. iconloader AAR：javac+kotlin 合并（先例 WM-Shell-shared）。
  版本号递增避免缓存；`install_aar_to_maven.py` 仅对既有本地 Maven 居住的 SettingsLib/
  SettingsLibSettingsTheme/WM-Shell/iconloader 重装。
- allowed_paths：`tools/package_aosp_aar.py`、`tools/install_aar_to_maven.py`、`tools/tests/`、
  `libs/aars/`（含 `SettingsLibSettingsTheme.aar`）、`libs/maven/`（含
  `com/android/systemui/SettingsLibSettingsTheme/`）、`SystemUI-core/build.gradle.kts`、
  `SystemUI-res/build.gradle.kts`（**仅当确需配置变更时**；理想情况下坐标不变、零配置改动）、
  `docs/`。
- 验收：重打包后 unzip -l 抽查 §5 代表类全部在位；**主 SettingsLib AAR 不得含
  `GroupSectionDividerMixin`/`SettingsThemeHelper`（防双产物重复类）**；Traceur AAR res 与
  SystemUI-res 合并通过
  `:app:processDebugResources`；`checkDebugDuplicateClasses` 通过；147 tests；
  missing_rules 107 → 5（仅 B1/B2×2/B3/B4）。
- 清理项：`traceur-res-R.jar` 退役；`SettingsLib-full.jar` 删除（dup 预防）并 `git grep` 归零。

### Batch 5 — B1–B3 四个 platform 类：移交 Task 032 逐类处置（不在本批次表内预设方案）
- 范围与约束见 §2：B1/B2 禁 dontwarn，优先结构性 classpath/SysUISdk；仅 B3 可能在无受支持
  桥梁时以恰好 1 条逐字 `-dontwarn` 兑底。本审计不预设结论；A 批次全部完成后预期剩余
  missing_rules = 5（B1/B2×2/B3/B4），此后走向由 Task 032 计划与 Batch 6 调查共同决定。
- allowed_paths：归 Task 032 计划另行定义。
- 验收（A 批次终态）：missing_rules 107 → 5；`mapping/usage/seeds` 产出（对齐 2026-08-20
  决策记录第 8 条验收）。**不得**声称 140 → 0：那需要 Task 032 处置与 B4 方案全部落地。

### Batch 6 — B4 keepanno R8 classpath 方案（调查驱动，不改 runtime scope）
- 调查 release-only 把 keepanno jar 喂给 R8 而不进 dex 的机制（§2 B4 候选），产出可行性结论后
  再立实施批。
- allowed_paths：调查文档 `docs/issues/`；实施批另批。

### Batch 7 — 清理与对账
- `docs/GRADLE_MIGRATION_LOG`、AGENTS §3.2 libs 图、`libs.versions.toml` 注释同步；
  未混淆 release APK（Task 029 基线）重产对比 dex 类数。

### 全局不变量（每批通用）
- 禁止：stub、res 生成/改写、自创 keep/dontwarn（唯一可能例外：B3 经 Task 032 逐字批准的
  恰好 1 条）、源码排除、
  `@Suppress` 绕过（worker-contract Never Do 全文适用）。
- 每批 allowed paths 仅限上列文件 + docs 记录；批次间不合并提交。

## 8. 尚未确认项（诚实清单）

1. **Soong 中间产物定位**：A3 的 31 个子命名空间 R jar、A4 的两个 proto javac jar、A11 的
   kotlin 合并产物、Traceur/perfetto proto 闭包，具体位于 `out/soong/.intermediates/` 的路径需在
   Batch 3/4 实施时以 `module-info.json` 实测定位（本审计只确认了"应合入什么"，未逐个取证中间
   路径——report-only 边界内无法验证 out 树新鲜度）。
2. **missing_rules 剩余计数推导**（140→125→118→107→5→0，B4 单列）为闭包推算，各批实际值以
   构建产物为准；翻转后新出现的 missing class 按 §5.1 诊断流程归类，不得顺手 dontwarn，
   也不得视为计划内可接受遗漏（§3.1/§7 纪律）。
3. **B4 keepanno release-R8 classpath 机制**未调查（Batch 6 立项），本文不断言任何候选可行。
4. **Task 029 未混淆基线 APK 同样缺 A 类全部 135 类**（运行期 NoClassDefFoundError 风险，见
   Task 030 REDLINE 记录）——本报告批次同时修复该基线，无需单独方案。

## 9. 构建说明

本任务为只读审计，**未运行任何 Gradle 构建**；所有结论来自 AOSP 源码/`Android.bp` grep、
libs 产物 `unzip -l`/`comm` class-set 对比、公网 Maven curl 证据（均在文中标注）。

---

## 附录 140 个 missing class 逐类归属

（由 `/tmp/task030-missing_rules.txt` 机械分类生成；分组定义见 §1/§3。下表共 140 个数据行。）

| Missing class（含嵌套类，`$` 原样） | 归属 |
|---|---|
| `com.android.systemui.FeatureFlags` | A1 |
| `com.android.systemui.FeatureFlagsImpl` | A1 |
| `com.google.android.msdl.data.model.MSDLToken` | A10 |
| `com.google.android.msdl.domain.InteractionProperties` | A10 |
| `com.google.android.msdl.domain.InteractionProperties$DynamicVibrationScale` | A10 |
| `com.google.android.msdl.domain.MSDLPlayer` | A10 |
| `com.google.android.msdl.domain.MSDLPlayer$Companion` | A10 |
| `com.google.android.msdl.logging.MSDLEvent` | A10 |
| `com.android.launcher3.Flags` | A11 |
| `com.android.launcher3.icons.IconThemeController` | A11 |
| `com.android.launcher3.icons.ThemedBitmap` | A11 |
| `com.android.launcher3.icons.mono.ThemedIconDrawable` | A11 |
| `com.android.wifi.flags.Flags` | A12 |
| `com.android.wm.shell.Flags` | A12 |
| `com.android.server.notification.FeatureFlags` | A2 |
| `com.android.server.notification.FeatureFlagsImpl` | A2 |
| `com.android.settingslib.RestrictedPreferenceHelperProvider` | A3 |
| `com.android.settingslib.bluetooth.LocalBluetoothLeBroadcastAssistantCallbackExtKt` | A3 |
| `com.android.settingslib.bluetooth.LocalBluetoothLeBroadcastCallbackExtKt` | A3 |
| `com.android.settingslib.bluetooth.LocalBluetoothLeBroadcastMetadata` | A3 |
| `com.android.settingslib.core.instrumentation.SettingsJankMonitor` | A3 |
| `com.android.settingslib.devicestate.PosturesHelper` | A3 |
| `com.android.settingslib.fuelgauge.Estimate` | A3 |
| `com.android.settingslib.graph.ThemedBatteryDrawable` | A3 |
| `com.android.settingslib.media.data.repository.SpatializerRepository` | A3 |
| `com.android.settingslib.media.data.repository.SpatializerRepositoryImpl` | A3 |
| `com.android.settingslib.media.domain.interactor.SpatializerInteractor` | A3 |
| `com.android.settingslib.mobile.MobileIconCarrierIdOverrides` | A3 |
| `com.android.settingslib.mobile.MobileIconCarrierIdOverridesImpl` | A3 |
| `com.android.settingslib.notification.data.repository.ZenModeRepository` | A3 |
| `com.android.settingslib.notification.data.repository.ZenModeRepository$DefaultImpls` | A3 |
| `com.android.settingslib.notification.data.repository.ZenModeRepositoryImpl` | A3 |
| `com.android.settingslib.notification.domain.interactor.NotificationsSoundPolicyInteractor` | A3 |
| `com.android.settingslib.qrcode.QrCodeGenerator` | A3 |
| `com.android.settingslib.satellite.SatelliteDialogUtils` | A3 |
| `com.android.settingslib.volume.data.repository.AudioRepository` | A3 |
| `com.android.settingslib.volume.data.repository.AudioRepositoryImpl` | A3 |
| `com.android.settingslib.volume.data.repository.AudioSharingRepository` | A3 |
| `com.android.settingslib.volume.data.repository.AudioSharingRepositoryEmptyImpl` | A3 |
| `com.android.settingslib.volume.data.repository.AudioSharingRepositoryImpl` | A3 |
| `com.android.settingslib.volume.data.repository.AudioSystemRepository` | A3 |
| `com.android.settingslib.volume.data.repository.AudioSystemRepositoryImpl` | A3 |
| `com.android.settingslib.volume.data.repository.LocalMediaRepository` | A3 |
| `com.android.settingslib.volume.data.repository.LocalMediaRepositoryImpl` | A3 |
| `com.android.settingslib.volume.data.repository.MediaControllerRepository` | A3 |
| `com.android.settingslib.volume.data.repository.MediaControllerRepositoryImpl` | A3 |
| `com.android.settingslib.volume.domain.interactor.AudioModeInteractor` | A3 |
| `com.android.settingslib.volume.domain.interactor.AudioVolumeInteractor` | A3 |
| `com.android.settingslib.volume.shared.AudioLogger` | A3 |
| `com.android.settingslib.volume.shared.AudioManagerEventsReceiver` | A3 |
| `com.android.settingslib.volume.shared.AudioManagerEventsReceiverImpl` | A3 |
| `com.android.settingslib.volume.shared.AudioSharingLogger` | A3 |
| `com.android.settingslib.volume.shared.model.AudioStream` | A3 |
| `com.android.settingslib.volume.shared.model.AudioStreamModel` | A3 |
| `com.android.settingslib.volume.shared.model.RingerMode` | A3 |
| `com.android.settingslib.widget.GroupSectionDividerMixin` | A3 |
| `com.android.settingslib.widget.SettingsThemeHelper` | A3 |
| `com.android.settingslib.widget.flags.Flags` | A3 |
| `com.android.settingslib.widget.mainswitch.R$id` | A3 |
| `com.android.settingslib.widget.mainswitch.R$layout` | A3 |
| `com.android.settingslib.widget.preference.app.R$id` | A3 |
| `com.android.settingslib.widget.preference.app.R$layout` | A3 |
| `com.android.settingslib.widget.preference.banner.R$color` | A3 |
| `com.android.settingslib.widget.preference.banner.R$drawable` | A3 |
| `com.android.settingslib.widget.preference.banner.R$id` | A3 |
| `com.android.settingslib.widget.preference.banner.R$layout` | A3 |
| `com.android.settingslib.widget.preference.banner.R$styleable` | A3 |
| `com.android.settingslib.widget.preference.barchart.R$dimen` | A3 |
| `com.android.settingslib.widget.preference.barchart.R$id` | A3 |
| `com.android.settingslib.widget.preference.barchart.R$layout` | A3 |
| `com.android.settingslib.widget.preference.button.R$id` | A3 |
| `com.android.settingslib.widget.preference.button.R$layout` | A3 |
| `com.android.settingslib.widget.preference.button.R$styleable` | A3 |
| `com.android.settingslib.widget.preference.footer.R$drawable` | A3 |
| `com.android.settingslib.widget.preference.footer.R$id` | A3 |
| `com.android.settingslib.widget.preference.footer.R$layout` | A3 |
| `com.android.settingslib.widget.preference.illustration.R$dimen` | A3 |
| `com.android.settingslib.widget.preference.illustration.R$id` | A3 |
| `com.android.settingslib.widget.preference.illustration.R$layout` | A3 |
| `com.android.settingslib.widget.preference.illustration.R$styleable` | A3 |
| `com.android.settingslib.widget.preference.slider.R$color` | A3 |
| `com.android.settingslib.widget.preference.slider.R$dimen` | A3 |
| `com.android.settingslib.widget.preference.slider.R$id` | A3 |
| `com.android.settingslib.widget.preference.slider.R$layout` | A3 |
| `com.android.settingslib.widget.preference.slider.R$styleable` | A3 |
| `com.android.settingslib.widget.preference.usage.R$id` | A3 |
| `com.android.settingslib.widget.preference.usage.R$layout` | A3 |
| `com.android.settingslib.widget.selectorwithwidgetpreference.flags.Flags` | A3 |
| `com.android.settingslib.widget.spinner.R$id` | A3 |
| `com.android.settingslib.widget.spinner.R$layout` | A3 |
| `com.android.settingslib.wifi.WifiUtils` | A3 |
| `com.android.settingslib.wifi.WifiUtils$InternetIconInjector` | A3 |
| `com.android.wm.shell.desktopmode.education.data.WindowingEducationProto` | A4 |
| `com.android.wm.shell.desktopmode.education.data.WindowingEducationProto$AppHandleEducation` | A4 |
| `com.android.wm.shell.desktopmode.education.data.WindowingEducationProto$AppHandleEducation$Builder` | A4 |
| `com.android.wm.shell.desktopmode.education.data.WindowingEducationProto$AppToWebEducation` | A4 |
| `com.android.wm.shell.desktopmode.education.data.WindowingEducationProto$AppToWebEducation$Builder` | A4 |
| `com.android.wm.shell.desktopmode.education.data.WindowingEducationProto$Builder` | A4 |
| `com.android.wm.shell.desktopmode.persistence.Desktop` | A4 |
| `com.android.wm.shell.desktopmode.persistence.Desktop$Builder` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopPersistentRepositories` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopPersistentRepositories$Builder` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopRepositoryState` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopRepositoryState$Builder` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopTask` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopTask$Builder` | A4 |
| `com.android.wm.shell.desktopmode.persistence.DesktopTaskState` | A4 |
| `com.android.wm.shell.nano.HandlerMapping` | A4 |
| `com.android.wm.shell.nano.Transition` | A4 |
| `com.android.wm.shell.nano.WmShellTransitionTraceProto` | A4 |
| `com.google.protobuf.GeneratedMessageLite` | A5 |
| `com.google.protobuf.GeneratedMessageLite$Builder` | A5 |
| `com.android.systemui.monet.ColorScheme` | A6 |
| `com.android.systemui.monet.DynamicColors` | A6 |
| `com.android.systemui.monet.Style` | A6 |
| `com.android.systemui.monet.TonalPalette` | A6 |
| `com.google.ux.material.libmonet.dynamiccolor.DynamicColor` | A6 |
| `com.google.ux.material.libmonet.dynamiccolor.DynamicScheme` | A6 |
| `com.google.ux.material.libmonet.dynamiccolor.MaterialDynamicColors` | A6 |
| `com.android.traceur.FileSender` | A7 |
| `com.android.traceur.PresetTraceConfigs` | A7 |
| `com.android.traceur.PresetTraceConfigs$TraceOptions` | A7 |
| `com.android.traceur.TraceConfig` | A7 |
| `com.android.traceur.TraceConfig$Builder` | A7 |
| `com.android.traceur.res.R$array` | A7 |
| `com.android.traceur.res.R$string` | A7 |
| `com.android.app.motiontool.DdmHandleMotionTool` | A8 |
| `com.android.app.motiontool.DdmHandleMotionTool$Companion` | A8 |
| `com.android.app.motiontool.MotionToolManager` | A8 |
| `com.android.app.motiontool.MotionToolManager$Companion` | A8 |
| `com.android.app.viewcapture.LooperExecutor` | A8 |
| `com.android.app.viewcapture.ViewCapture` | A8 |
| `com.android.app.viewcapture.ViewCaptureAwareWindowManager` | A8 |
| `com.android.app.viewcapture.ViewCaptureAwareWindowManager$Factory` | A8 |
| `com.android.app.viewcapture.ViewCaptureFactory` | A8 |
| `android.compat.annotation.UnsupportedAppUsage` | B1 |
| `libcore.io.IoUtils` | B2 |
| `libcore.util.NativeAllocationRegistry` | B2 |
| `com.android.aconfig.annotations.AconfigFlagAccessor` | B3 |
| `com.android.tools.r8.keepanno.annotations.UsesReflection` | B4 |
