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
| Task 040 目标 | 7 | 验收目标 |
| Task 040 实测（fresh R8） | 7 | ✅ 2026-08-21 实测：BEFORE=81 AFTER=7 REMOVED=74 ADDED=0 |

## 待解决问题

本批成功后仅剩：B1–B4 platform/build classpath 6 refs 与 `AssumeTrueForR8` 1 ref。它们必须
按后续独立批次处理，本批不得顺手修改。

---

## 实施证据（Task 040 worker，2026-08-21 追加）

### Task 1：pre-change fresh R8 baseline

- `./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain -Dorg.gradle.workers.max=4`
  → exit **1**（`BUILD FAILED in 2m 1s`，到达 R8 missing-reference 诊断，非前置任务失败）。
- 归一化断言：`BASELINE=81 SETTINGSLIB=74 OTHER=7`；74 个 SettingsLib targets 已存
  `/tmp/task040-settingslib-before.txt`，含 `AssumeTrueForR8`。

### Task 2：program closure（TDD 先红后绿）

- RED：6 failures（main 缺 Kotlin 输入、780≠1153、Theme 0≠15）；既有 res 溯源测试保持绿。
- 输入机械验证：discovery 32 javac JAR → 780 类；MAIN_KOTLIN 372 类；DEVICE_KOTLIN 1 类
  （`PosturesHelper`）；THEME_KOTLIN 15 类；四者两两不相交、无 R 类；main 并集恰 **1153**。
- GREEN：focused 12 tests `OK`；`SettingsLib.aar` 4,797,541 bytes；
  `SettingsLibSettingsTheme.aar` 165,734 bytes；
  main 含 `RestrictedPreferenceHelperProvider`/`PosturesHelper`、不含
  `GroupSectionDividerMixin`/`SettingsThemeHelper`；main∩Theme = 0。

### Task 3：10 个 res-only AAR（TDD 先红后绿）

- 源树计数：`22,91,96,6,23,91,6,5,1,5`，总计 **346**；manifest namespace 与设计表一致。
- RED：missing config keys；GREEN：10 AAR 全部生成，346 res 文件逐字节与 AOSP 一致，
  classes.jar 全空，重复打包 byte-identical；CONFIGS 达 29 artifacts。

### Task 4：Maven wiring（TDD 先红后绿）

- RED：旧版本/7 边/缺注册；GREEN：`tools.tests.test_install_aar_to_maven` 21 tests `OK`。
- 17 条 POM 边按 AOSP bp 过滤后顺序机械验证（bp static_libs 共 44 项，SettingsLib* 35 项，
  res-owning 17 项入选）。
- 安装：main/Theme 仅存 `1.0.1`（旧 `1.0.0` 目录已删）；10 新 target `1.0.0`；
  主 POM 恰 17 `<dependency>` 边；其余 POM 骨架无 deps；Maven AAR 与 `libs/aars` byte-identical。
- `libs/SettingsLib-full.jar` 已删；`rg 'SettingsLib-full\.jar' --glob '!docs/**'` 无功能引用；
  `SystemUI-core/build.gradle.kts` 仅删 2 行（注释 + compileOnly）。

### Task 5：全套验证

1. 全套 Python 测试：`Ran 195 tests in 72.577s`，`OK`，exit 0（179 基线 + 16 新增）。
2. 12 个 AAR 两次打包 `cmp` 全部 exit 0（deterministic）。SHA-256：

   | AAR | SHA-256 |
   |---|---|
   | SettingsLib | 61b480f284ae7eefd194412cf2dde8c7ad55675f8275f32cd6654278d8a2bd04 |
   | SettingsLibSettingsTheme | 9ee3c671d80b1338b41480d886e2277910fd8c0b80ee3cbf907ebacb3f00b877 |
   | SettingsLibMainSwitchPreference | b6147933ce09c4d792cb88275a38436226a98add85ad0d539dd277e1f9a1c71f |
   | SettingsLibAppPreference | 2110852a0fee594121a8cca7e0057d421d1903e8895ead9ca6bd094c10cbbaec |
   | SettingsLibBannerMessagePreference | 7beca439ac32c2b6a3f4e8be1edf185ca65ede0ab0ada5700fea17c7a874454c |
   | SettingsLibBarChartPreference | 4624cf0e4c30921ac31f454c1e6b0bb17ce80df4d47fd6cfd61da938f194281e |
   | SettingsLibButtonPreference | 2801c41c071c9d4bb07578e4518ac89bd493e049e546f38546c61ba9c3939452 |
   | SettingsLibFooterPreference | 2a631f84d9c622775296e45b0911ee2dea49c8d318642b916ce3f7a1636f8c59 |
   | SettingsLibIllustrationPreference | 81cf4dc6cfa7fe1d66cf56ef6813a51ccd9445caf022d46e65240f9ca827e49c |
   | SettingsLibSliderPreference | 1912b297b54c95b576e4c094c62e5adadc53259650a27cecdd74d02b70f93102 |
   | SettingsLibUsageProgressBarPreference | 6ab7d889b5738b88a2ca2d5dfd134330adf60d50fe09b4be88c4f8f4ed8561b1 |
   | SettingsLibSettingsSpinner | ee3aa868adc75038564fcbf38e7405e5b0a8a6e8b34349df22408fa80821db62 |

3. 重装后 Maven 副本与最终 AAR 字节一致（`git status libs/maven libs/aars` 0 变化）。
4. Debug 硬门禁：`:app:checkDebugDuplicateClasses :app:assembleDebug` → exit **0**，
   `BUILD SUCCESSFUL in 2m 42s`（216 tasks，无 duplicate class 冲突、无资源冲突）。
5. APK defined 检查（apkanalyzer dex packages --defined-only）：`TOTAL=74 DEFINED=74 MISSING=0`。
6. Fresh R8 after：exit **1**（仅因 7 个 deferred refs；`BUILD FAILED in 2m 11s`）；
   精确差分断言输出：

   ```text
   BEFORE=81 AFTER=7 REMOVED=74 ADDED=0
   remaining refs:
     android.compat.annotation.UnsupportedAppUsage
     com.android.aconfig.annotations.AconfigFlagAccessor
     com.android.aconfig.annotations.AssumeTrueForR8
     com.android.tools.r8.keepanno.annotations.UsesReflection
     libcore.io.IoUtils
     libcore.util.NativeAllocationRegistry
     org.apache.harmony.dalvik.ddmc.ChunkHandler
   ```

   removed 恰为 pre-change 的 74 个 `com.android.settingslib.*` refs；after 中无任何
   SettingsLib ref；`AssumeTrueForR8` 保留；B1–B4 platform/build classpath 6 项保留。

### 提交记录

- `dfd5c05e` build: complete SettingsLib program AAR closure
- `c23cf137` build: add SettingsLib resource namespace AARs
- `0ecf17e0` build: deliver SettingsLib closure through Maven AARs
- （后续）docs: record SettingsLib closure evidence

worker 未 push（按 brief 要求，由 architect 审核后 push）。

## Architect main fresh 验收（2026-08-21）

固定 worker head `568114433108c34cd990909d2242b38e0037d949` 通过双轴静态审查：
Standards PASS（0 BLOCKER/HIGH/MEDIUM；经用户 H.6 授权将 AGENTS/CHARTER 的历史 7 边事实同步为 17），Spec PASS（零发现）。四个 worker commits 已分别落到 main：
`d2e1569a`、`01c7e58d`、`1aea7ace`、`f1952172`。

main 独立验收结果：

1. `python3 -m unittest discover -s tools/tests -p 'test_*.py'`：**195/195**，exit 0。
2. 12 个变化/新增 AAR 各连续重建两次，全部 byte-identical；重装本地 Maven 后 12/12 副本与 `libs/aars` byte-identical；哈希与 worker 表一致。
3. `:app:checkDebugDuplicateClasses :app:assembleDebug`：exit **0**，`BUILD SUCCESSFUL in 1m 10s`；APK SHA-256 `1335957d70e6fb92dbe6a35f773f20af20ad3744214f81422b87cc65a9957ae9`。
4. main debug APK：pre-change SettingsLib targets **74/74 defined**。
5. `:app:minifyReleaseWithR8 --rerun-tasks`：真实 exit **1**，`BUILD FAILED in 2m 17s`，仅因 7 个 deferred refs；精确差分 **BEFORE=81 AFTER=7 REMOVED=74 ADDED=0**，removed 恰为 74 个 SettingsLib refs，after 无 SettingsLib ref，`AssumeTrueForR8` 保留。
6. `git diff --check` 干净；工程硬门禁与本批全部验收标准满足。
