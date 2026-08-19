# 2026-08-20 — Release R8 / resource shrink AOSP 对齐决策

## 背景

Task 025 证明 `:app:assembleRelease` 被 `SystemUI-core/consumer-rules.pro` 悬挂引用阻塞。
Task 028 深度核对 AOSP Android.bp / Soong：AOSP 默认
`SYSTEMUI_OPTIMIZE_JAVA=true`，最终 app 开启 R8 optimize+shrink，非 eng 构建同时收缩资源；
SystemUI-core library 层零 ProGuard，plugin/plugin_core 通过 export flags 汇入 app。

## 用户批准（2026-08-20）

1. **G1**：完整删除 SystemUI-core 的 `consumerProguardFiles("consumer-rules.pro")` 和
   release `proguardFiles(..., "proguard-rules.pro")` 配置；core 与 AOSP 一样零 ProGuard。
2. **R3**：恢复 AOSP export flags 语义：
   - Android library `:SystemUI-plugin` 使用 `consumerProguardFiles`；
   - JVM library `:SystemUI-plugin-core` 无 AGP consumer DSL，AOSP 原始 flags 由 app
     `proguardFiles` 直接接入（规则文件仍归 module 所有；不为通道强改模块类型）。
3. **R1**：app release 开启 R8：`isMinifyEnabled=true`。
4. 保留官方 `proguard-android-optimize.txt`，叠加 byte-exact AOSP `proguard.flags` 链。
5. 不显式设置 `android.enableR8.fullMode`，采用 AGP 9.3.1 默认行为；如发现实证差异再单独决策。
6. **R2**：不推迟，R8 落地时同时设置 `shrinkResources=true`。
7. 不补 AOSP 自己未 export 的 SystemUIFlagsLib ParcelableFlag keep 规则。
8. 验收：release APK、platform 签名、关键类/dex、plugin rules 汇入、mapping/usage/seeds、147 tests。
9. 诊断边界：只可接入 AOSP 原始规则；禁止发明宽泛 keep、关闭 R8/检查或排除源码。
10. 批次：Task 029（G1+R3+未混淆 release 基线）→ Task 030（R1+R2 优化 release）。

## 依据

完整证据与 gap 表：`docs/architecture/2026-08-20-aosp-release-config-analysis.md`。

## 实施记录（Task 029：G1 + R3 + 未混淆 release 基线，2026-08-20）

### 改动

1. **G1**（`SystemUI-core/build.gradle.kts`）：删除 `consumerProguardFiles("consumer-rules.pro")`
   与整个 `buildTypes.release` 块（含悬挂 `proguard-rules.pro` 引用）；core 现与 AOSP
   android_library 层一致——零 ProGuard 配置。未创建空 .pro 文件。
2. **R3 :SystemUI-plugin**（Android library）：byte-exact 复制 AOSP
   `plugin/proguard_plugins.flags`（19 行）到模块根，`defaultConfig` 添加
   `consumerProguardFiles("proguard_plugins.flags")`（对应 bp
   `export_proguard_flags_files: true` + `proguard_flags_files`）。
3. **R3 :SystemUI-plugin-core**（JVM library）：byte-exact 复制 AOSP
   `plugin_core/proguard.flags` 到模块根；JVM 模块保持边界，不改 module plugin，由
   `app/build.gradle.kts` debug/release 两处 `proguardFiles(...)` 直接追加
   `rootProject.file("SystemUI-plugin-core/proguard.flags")` 接入最终 app。
4. app 的 `isMinifyEnabled`/`shrinkResources` 未动（默认 false），本基线用于隔离验证
   G1/R3；R1+R2 属 Task 030。

### 验收结果（真实命令输出）

- `diff -q` 两个 flags 文件 vs AOSP 原文件 → identical（BYTE_EXACT_OK）
- `git grep 'consumer-rules.pro\|proguard-rules.pro' -- SystemUI-core` → 无匹配（NO_DANGLING_REFS）
- `./gradlew :SystemUI-plugin:bundleReleaseAar :app:assembleRelease` →
  **BUILD SUCCESSFUL in 3m 47s**（383 actionable tasks: 11 executed, 372 up-to-date）
  - 首次运行时 Gradle daemon 被 OOM kill（-Xmx16g + Kotlin daemon 8.7GB RSS 超出内存）；
    以 `-Dorg.gradle.workers.max=4` 重跑成功（仅命令行参数，未改 gradle.properties）
- `python3 -m unittest discover -s tools/tests` → **Ran 147 tests / OK**
- `git diff --check` → 干净（DIFF_CHECK_OK）

### Release APK 基线信息（R8 未开启）

| 项 | 值 |
|---|---|
| 路径 | `app/build/outputs/apk/release/app-release.apk` |
| 大小 | 126,642,058 bytes（约 120.8 MiB） |
| SHA-256 | `0b16d484f0aa91162d7ba3641402f09412bbafa0f16578419137699216a6aca1` |
| dex | 8 个 classes*.dex（未混淆） |
| mapping | **未生成**（`outputs/mapping/release/` 不存在，R8 关闭，符合预期） |
| 签名 | V2，platform 测试证书（CN=Android，SHA-256 `c8a2e9bc…92ab8`） |

### 额外验证

- 解包 `SystemUI-plugin-release.aar`，其中 `proguard.txt` 与 AOSP
  `proguard_plugins.flags` diff → identical（consumer 规则成功打包进 AAR）。

### 待解决

- ~~Task 030：R1+R2~~ → 已实施，见下方实施记录（**REDLINE 阻塞**）。

---

## 实施记录（Task 030：R1 + R2，2026-08-20，REDLINE 阻塞）

### 改动

1. `app/build.gradle.kts` release 块：`isMinifyEnabled = true` + `isShrinkResources = true`
   （用户已批准 R1+R2；未显式设置 `android.enableR8.fullMode`；未加任何自创规则；
   debug 块未动）。
2. 首次写入 `shrinkResources = true` 报 Kotlin DSL `Unresolved reference`：
   经 javap 核对 AGP 9.3.1 `gradle-api` 的 `com.android.build.api.dsl.BuildType`，
   属性名为 `isShrinkResources`（Groovy 名无 `is` 前缀），已修正。

### 构建/验证结果（真实命令输出）

- `./gradlew :app:assembleRelease -Dorg.gradle.workers.max=4` →
  **BUILD FAILED，`Task :app:minifyReleaseWithR8 FAILED`**
  （372 actionable tasks: 4 executed, 368 up-to-date；约 1m21s）。
  首次运行还叠加了环境 OOM：kernel `oom-kill` 杀掉 Gradle daemon
  （R8 阶段 RSS 峰值 17.4GB + 闲置 Kotlin daemon 8.2GB，总内存 30GB 不够）；
  `./gradlew --stop` 后重跑内存足够，失败稳定复现为下述 R8 错误。
- 失败原文（两行 ERROR）：
  ```
  ERROR: Missing classes detected while running R8. Please add the missing classes
    or apply additional keep rules that are generated in
    <root>/app/build/outputs/mapping/release/missing_rules.txt.
  ERROR: R8: Missing class android.compat.annotation.UnsupportedAppUsage
    (referenced from: ... Flags.notificationMinimalism() and 219 other contexts)
  ```
- `app/build/outputs/mapping/release/missing_rules.txt`：**140 条 `-dontwarn` 建议**。
  APK/mapping/usage/seeds 均**未产出**（R8 在 shrink 前失败）。

### 根因分类（140 个 missing class，逐项核对 AOSP `Android.bp`）

**A 类：AOSP 把这些类编进 SystemUI APK（SystemUI-core static_libs），我们的依赖闭包缺失
（编译期能过是因为 compileOnly jar 提供符号；运行期/unminified 基线 APK 里本来就缺类，
R8 只是把它变成硬错误）**：

| # | 缺失内容 | AOSP 依据 | 我方现状 |
|---|---|---|---|
| A1 | `com.android.systemui.FeatureFlags` / `FeatureFlagsImpl`（2 类，被 185+ 处引用） | `com_android_systemui_flags_lib`（SystemUI-core static_libs，bp L459）生成 | `libs/systemui-flags.jar` 陈旧（2026-07-23，仅 `Flags.class`）；AOSP javac jar 还含 `CustomFeatureFlags`、`FakeFeatureFlagsImpl`。同批 `systemui-shared-flags.jar` 已于 08-12 换全量 javac JAR，此 jar 漏换 |
| A2 | `com.android.server.notification.FeatureFlags(Impl)` | `notification_flags_lib`（bp L505） | `libs/maven/.../notification-flags` jar 实测仅含 `Flags.class`（2026-07-23 旧打包批次，与 A1 同批） |
| A3 | SettingsLib ~70 类（`wifi.WifiUtils`、`qrcode.QrCodeGenerator`、`graph.ThemedBatteryDrawable`、`devicestate.PosturesHelper`、volume/bluetooth/fuelgauge/notification.data/media.data 各 repository、mainswitch/spinner/各 per-target `R$*` 等） | `SettingsLib`（bp L457）主 src 含这些文件（实测 `SettingsLib/src/com/android/settingslib/wifi/WifiUtils.kt` 等） | `libs/aars/SettingsLib.aar` 仅 781 类，不含主 src 这批类；我方 compileOnly `libs/SettingsLib-full.jar` 里反而全有（实测含 `WifiUtils.class` 等）——AAR 打包时选错了产物/未合并主 src |
| A4 | `com.android.wm.shell.desktopmode.persistence.{Desktop,DesktopTask,DesktopRepositoryState,DesktopPersistentRepositories…}` + `desktopmode.education.data.WindowingEducationProto*` + `com.android.wm.shell.nano.*` | `WindowManager-Shell-lite-proto`（lite proto，WM-Shell bp L189 static_libs）与 `WindowManager-Shell-proto`（nano proto，SystemUI-proto 的 libs） | `libs/aars/WindowManager-Shell.aar`（1848 类）不含任何 proto 生成类；`SystemUI-proto.jar` 的 nano 闭包也未随包 |
| A5 | `com.google.protobuf.GeneratedMessageLite($Builder)` | A4 lite proto 的 soong protobuf-lite 运行时 | 无对应运行时依赖 |
| A6 | `com.android.systemui.monet.*` + `com.google.ux.material.libmonet.*` | `monet`、`libmonet`（bp L494-495 static_libs） | `monet.jar` 为 **compileOnly**（SystemUI-core L161）；libmonet 无运行时依赖 |
| A7 | `com.android.traceur.*`（TraceConfig/PresetTraceConfigs/FileSender/res.R） | `TraceurCommon` + `Traceur-res`（bp L502-503 **static_libs**） | 两者均为 compileOnly jar（L181-182） |
| A8 | `com.android.app.motiontool.*`、`com.android.app.viewcapture.*` | `motion_tool_lib`（bp L504 static_libs）；viewcapturelib 在 WM-Shell 闭包内 | `motion_tool_lib.jar` compileOnly（L173）；viewcapture 类不在任何运行时闭包 |
| A9 | `com.android.tools.r8.keepanno.annotations.UsesReflection` | `keepanno-annotations`（bp L512 **static_libs**，注解保留在 class 内供 R8 消费） | `keepanno-annotations.jar` compileOnly（L165） |
| A10 | `com.google.android.msdl.*`（6 类） | msdllib（frameworks/libs/systemui/msdllib，经某 static 链进入 APK） | `msdl.jar` compileOnly（L135） |
| A11 | `com.android.launcher3.Flags` + `launcher3.icons.{IconThemeController,ThemedBitmap,mono.ThemedIconDrawable}` | iconloaderlib srcs（`IconThemeController` 声明在 `ThemedBitmap.kt`；其 static_libs 含 `com_android_launcher3_flags_lib`） | `libs/aars/iconloader.aar` 60 类全部为 Java 源产物，**Kotlin 类一个未含**（与 A1/A2 同模式：打包选了不全的 soong 产物）；launcher3 flags 无运行时 |
| A12 | `com.android.wifi.flags.Flags`、`com.android.wm.shell.Flags` | WifiTrackerLib / WM-Shell aconfig 闭包 | `wifi-flags.jar`/`wm-shell-flags.jar` compileOnly（L212/215） |

**B 类：真 bootclasspath/framework 提供（compileOnly 语义正确；AOSP 不报是因为 soong
把全量 classpath 喂给 R8，我方 AGP 只喂 runtime classpath）**：

| # | 缺失内容 | 来源 |
|---|---|---|
| B1 | `android.compat.annotation.UnsupportedAppUsage`（219 引用点） | framework.jar（bootclasspath，设备 framework 提供） |
| B2 | `libcore.io.IoUtils`、`libcore.util.NativeAllocationRegistry` | libcore（bootclasspath） |
| B3 | `com.android.aconfig.annotations.AconfigFlagAccessor` | aconfig 注解（构建期消费） |

### 为何 AOSP 不需要 dontwarn（核对结果）

- 我方 5 个 flags 文件 + AOSP 原始 `proguard.flags`/`proguard_common.flags`/
  `proguard_kotlin.flags`/`proguard_plugins.flags`/`plugin_core/proguard.flags`
  **均无任何 `-dontwarn`**（grep 实测 0 匹配，双方一致）。
- AOSP 不报缺失：soong R8 输入含完整编译 classpath；我方 AGP R8 只看 runtime
  classpath，于是 compileOnly/漏包类全部显形。

### REDLINE（worker 停止点，brief 步骤 5）

完成本任务需要以下之一，均越出 brief 授权边界：

1. **修 A 类**：重新打包/补齐 `libs/` 下的陈旧 jar 与 AAR 闭包、或将若干
   compileOnly 改为 implementation（依赖/产物变更，非 Allowed Paths，CHARTER Part 5.4）。
   注：A 类不仅是 R8 阻塞——**Task 029 未混淆基线 APK 本身已缺这些类，运行期会
   NoClassDefFoundError**（如 `FeatureFlags` 185+ 引用点），建议架构师优先处理。
2. **接 AGP 生成的 `missing_rules.txt`（140 条 `-dontwarn`）**：AGP 标准补救，但属
   “自创 dontwarn”，brief 明文禁止；且会把 A 类真实缺口掩埋成运行期风险。
3. **B 类少量 `-dontwarn`**（约 3 条，bootclasspath 注解/工具类）：语义正确但同样需
   用户批准才能写入。

worker 未做任何上述变更；`app/build.gradle.kts` 的 R1+R2 改动保留为未提交 diff，
等待架构师决策。
