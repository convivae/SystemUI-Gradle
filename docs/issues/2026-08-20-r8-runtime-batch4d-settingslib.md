# 2026-08-20 R8 Runtime Batch 4D — SettingsLib program/resource 闭包（81→7）

## 背景

Task 038 合并后的 main fresh R8 仍有 **81** 个真实 missing refs，其中 **74** 个属于
SettingsLib：43 个程序类和 31 个子资源 namespace `R$*`。其余 7 个是 B1–B4
platform/build classpath 6 项与 `AssumeTrueForR8` 1 项，本批不得处理。

用户于 2026-08-20 明确批准本 bounded 设计及以下坐标升级：

- `SettingsLib`：`1.0.0 → 1.0.1`
- `SettingsLibSettingsTheme`：`1.0.0 → 1.0.1`
- 10 个新增 per-target res-owning AAR：初始 `1.0.0`

本批不改变 Gradle 模块边界，不修改任何 AOSP 镜像源码或资源文件。

## 根因与 owner

### 43 个程序类

1. 主 `SettingsLib` Kotlin 产物缺失：
   `.../SettingsLib/SettingsLib/android_common/kotlin/SettingsLib.jar` 有 372 个 class entries，
   包含 40 个当前 R8 missing 的主源码类。现有主 AAR 只���并递归发现的 javac JAR。
2. `SettingsLibDeviceStateRotationLock` Kotlin 产物缺失：
   `.../DeviceStateRotationLock/SettingsLibDeviceStateRotationLock/android_common/kotlin/
   SettingsLibDeviceStateRotationLock.jar` 只有 `PosturesHelper.class`，应并入主 AAR，
   因该 target 是主 `SettingsLib` 的 direct `static_libs`。
3. `SettingsLibSettingsTheme` Kotlin 产物缺失：
   `.../SettingsTheme/SettingsLibSettingsTheme/android_common/kotlin/
   SettingsLibSettingsTheme.jar` 有 15 个 class entries，包含
   `GroupSectionDividerMixin` 和 `SettingsThemeHelper`。该代码必须归独立 Theme AAR，
   不得并入主 AAR。

当前 `libs/SettingsLib-full.jar` 是主 Kotlin 代码的临时 `compileOnly` 载体。主 AAR 补齐后，
必须删除该 JAR、`SystemUI-core/build.gradle.kts` 中对应依赖与注释，避免双来源。

### 31 个资源 namespace R 类

31 个 missing `R$*` 分属 10 个拥有真实 AOSP 资源的 Soong target：

| Soong target | AOSP 子目录 | manifest namespace | res 文件数 |
|---|---|---|---:|
| `SettingsLibMainSwitchPreference` | `MainSwitchPreference` | `com.android.settingslib.widget.mainswitch` | 22 |
| `SettingsLibAppPreference` | `AppPreference` | `com.android.settingslib.widget.preference.app` | 91 |
| `SettingsLibBannerMessagePreference` | `BannerMessagePreference` | `com.android.settingslib.widget.preference.banner` | 96 |
| `SettingsLibBarChartPreference` | `BarChartPreference` | `com.android.settingslib.widget.preference.barchart` | 6 |
| `SettingsLibButtonPreference` | `ButtonPreference` | `com.android.settingslib.widget.preference.button` | 23 |
| `SettingsLibFooterPreference` | `FooterPreference` | `com.android.settingslib.widget.preference.footer` | 91 |
| `SettingsLibIllustrationPreference` | `IllustrationPreference` | `com.android.settingslib.widget.preference.illustration` | 6 |
| `SettingsLibSliderPreference` | `SliderPreference` | `com.android.settingslib.widget.preference.slider` | 5 |
| `SettingsLibUsageProgressBarPreference` | `UsageProgressBarPreference` | `com.android.settingslib.widget.preference.usage` | 1 |
| `SettingsLibSettingsSpinner` | `SettingsSpinner` | `com.android.settingslib.widget.spinner` | 5 |

这些 target 共 346 个真实资源文件。不能把 Soong `R.jar` 或手工 R 类塞进主 AAR：这样会丢失
资源闭包并违反规则 R。正确交付方式是每个 target 一个 res-only AAR，原样携带 AOSP res、
原始 manifest 和 Soong `R.txt`，由 AGP 生成各自 R namespace。

## 已批准设计

### Program closure

- 主 `SettingsLib.aar` 在现有 780-class javac 闭包上加入主 Kotlin 372 类与
  DeviceStateRotationLock Kotlin 1 类，目标 classes.jar 为 **1153 类的精确不相交并集**。
- `SettingsLibSettingsTheme.aar` 独立加入其 Kotlin JAR，目标 classes.jar 为 **15 类**。
- 主 AAR 必须不含 `GroupSectionDividerMixin` / `SettingsThemeHelper`；Theme AAR 必须包含它们。
- 删除 `libs/SettingsLib-full.jar` 和唯一 `compileOnly` 引用。

### Resource closure

- 新增上表 10 个 res-only AAR；每个 AAR 的 `res/**` 必须与对应 AOSP 目录不漏、不多、逐字节一致。
- AAR 的 manifest 与 R.txt 使用 owning Soong target 的原始产物；classes.jar 保持空。
- 不覆盖、重命名、合并或改写任何 XML/PNG。

### Maven/POM closure

- 主 SettingsLib 和 Theme 坐标升至已批准的 `1.0.1`，删除各自旧 `1.0.0` 目录。
- 10 个新 target 使用 `com.android.systemui:<SoongTargetName>:1.0.0`。
- 主 SettingsLib POM 的资源依赖集合由 7 条扩展为 17 条，并按 AOSP 主
  `SettingsLib` `static_libs` 的过滤后顺序排列：
  ActionButtons、AdaptiveIcon、App、BannerMessage、BarChart、Button、Footer、Illustration、
  Layout、MainSwitch、ProgressBar、RestrictedLockUtils、SelectorWithWidget、SettingsSpinner、
  Slider、TwoTarget、UsageProgressBar。
- 17 个子 target 自身仍使用无 dependencies 的骨架 POM。

## 禁止事项

- 不改 `SystemUI-*/src/**`、`SystemUI-*/res*/**` 或 AOSP 源树。
- 不加 stub、keep、dontwarn、`@Suppress`、源码排除或检查绕过。
- 不用 R-only JAR，不把 Theme 类并入主 AAR，不把任何新资源合并进主 AAR。
- 不处理 B1–B4、`AssumeTrueForR8` 或其他闭包。
- 不更改除已批准 `SettingsLib`/Theme `1.0.1` 外的任何依赖版本。

## 验收标准

1. 新增测试先红后绿；全套 `tools/tests` 通过（当前基线 179，加本批新增测试）。
2. 主 AAR classes.jar = 1153 类精确并集；Theme = 15 类；两者类集零重叠。
3. 10 个新 AAR 共 346 个 res 文件，逐 target 与 AOSP res 树逐字节一致；classes.jar 为空。
4. 所有 12 个变化/新增 AAR 连续两次打包 byte-identical。
5. 本地 Maven 仅保留主 SettingsLib/Theme `1.0.1`；10 个新 target 为 `1.0.0`；主 POM
   恰有 17 条依赖边，子 POM 均无 dependencies。
6. `libs/SettingsLib-full.jar` 不存在，非历史文档中的功能引用归零。
7. `:app:checkDebugDuplicateClasses :app:assembleDebug` BUILD SUCCESSFUL（硬门禁）。
8. pre-change R8 中 74 个 `com.android.settingslib.*` missing targets 在 debug APK 中全部 defined。
9. fresh R8 **81→7 精确**：removed 恰为 pre-change 的 74 个 SettingsLib refs，added=0，
   after 中无 `com.android.settingslib.*`，B1–B4 6 项与 `AssumeTrueForR8` 保留。
10. `git diff --check` 干净；真实命令、退出码、哈希和差分追加到本文。

## 错误数演变

| 阶段 | R8 unique missing refs | 状态 |
|---|---:|---|
| Task 038 main fresh | 81 | 已验证；其中 SettingsLib 74 |
| Task 040 目标 | 7 | 验收目标；必须由 fresh R8 实测，不能预先声明成功 |

## 待解决问题

本批成功后仅剩：B1–B4 platform/build classpath 6 refs 与 `AssumeTrueForR8` 1 ref。它们必须
按后续独立批次处理，本批不得顺手修改。
