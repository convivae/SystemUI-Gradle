# 2026-08-20 — AOSP SystemUI Release 构建配置深度分析 + 我方 release 对齐建议（Task 028，只读研究）

> **性质**：只读研究。本文不改任何构建文件；所有"建议"均为待用户批准的提案。
> 分析对象：`/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/`（下称 AOSP）。
> 对比对象：`app/build.gradle.kts`、`SystemUI-core/build.gradle.kts`（下称"我方"）。
> 前置：`docs/issues/2026-08-20-assemble-release-verification.md`（Task 025，release 首验失败于
> `consumer-rules.pro` 悬挂引用）。

---

## a. Release 编译哪些代码

### AOSP 事实

**`android_library "SystemUI-core"`**（`Android.bp:415`）：

- `srcs`（L416-423）基线包含：
  - `src/**/*.kt`、`src/**/*.java`、`src/**/I*.aidl`
  - **`:ReleaseJavaFiles`（L429）— release 文件默认在编译集里**
  - `compose/features/src/**/*.kt`、`compose/facade/enabled/src/**/*.kt`
- `product_variables.debuggable`（L433-437）：debuggable 构建时**追加** `:DebugJavaFiles` 并**排除** `:ReleaseJavaFiles`。
- filegroup 定义（L57-71）：
  - `ReleaseJavaFiles` = `src-release/**/*.kt|*.java`（4 个文件，见下）
  - `DebugJavaFiles` = `src-debug/**/*.kt|*.java`（同名 4 个文件）

**src-release vs src-debug 的 4 组文件**（AOSP 目录实测，两目录文件集 1:1 同名）：

| 文件 | release 版语义 | debug 版差异（diff 实测） |
|---|---|---|
| `flags/FlagsFactory.kt` | 未 release 的 flag **恒为 false**（`UnreleasedFlag(teamfood = false)`），且不注册 dupe 检查 | 保留 teamfood 值 + `checkForDupesAndAdd` |
| `flags/FlagsModule.kt` | 绑定 `FeatureFlagsReleaseStartableModule` + `ServerFlagReaderModule` | 绑定 `FeatureFlagsDebugStartableModule`（本地 fake flag override，需 Context/Handler） |
| `log/DebugLogger.kt` | **空 logger**（"An empty logger for release builds."） | 完整 Log 包装：tag 自动取、懒求值、LOG_ID_MAIN |
| `util/StartBinderLoggerModule.kt` | **空 module**（仅 debug 用） | `@Binds @IntoMap @ClassKey(BinderLogger)` 注册 CoreStartable |

**compilelib**（`frameworks/libs/systemui/compilelib/Android.bp:30-45`）：

- 同一套 `product_variables.debuggable` 机制（`compilelib-{Release,Debug}JavaFiles` filegroup，L22-33）
- `src-release/.../Compile.java`：`IS_DEBUG = false`；`src-debug/...`：`IS_DEBUG = true`

**`android_app "SystemUI"`**（`Android.bp:958-986`）：`static_libs: ["SystemUI-core"]`（L965-967），无自有 srcs。

### 我方现状

- `SystemUI-core/build.gradle.kts` sourceSets：main = `src` + compose/features + facade/enabled + pods（对齐 bp 基线）；**但 main srcDirs 不含 `src-release`**；`debug` srcSet 加 `src-debug`，`release` srcSet 加 `src-release`。
- `debugImplementation`/`releaseImplementation` 分别引 `libs/compilelib-{debug,release}.jar`（两 jar 均在，实测 400 字节，仅 `Compile.class`）。

### Gap 判定：**语义等价，机制不同**

| 点 | AOSP | 我方 | 差异 |
|---|---|---|---|
| release 源码选择 | release 文件在**基线**，debuggable 时 swap | main 不含任一，按 variant srcSet 加 | 语义等价（debug=src+src-debug；release=src+src-release）；Gradle variant srcSet 是地道机制，**无需改** |
| compilelib | 同一模块 debuggable swap | 两个 prebuilt jar 按 variant 切 | 语义等价；jar 来自 `tools/package_compilelib_jars.py`（provenance 合规） |

---

## b. 哪些地方加优化（optimize）

### AOSP 事实

**`SystemUI_optimized_defaults`**（`Android.bp:927-950`，`soong_config_module_type` + `java_defaults`）：

- 变量：`ANDROID` namespace 的 bool `SYSTEMUI_OPTIMIZE_JAVA`
- **true 分支**（L938-945）：`optimize: { enabled: true, optimize: true, shrink: true, shrink_resources: true, optimized_shrink_resources: true, ignore_warnings: false, proguard_compatibility: false }`
- **默认分支**（未设变量，L946-949）：仅 `ignore_warnings: false, proguard_compatibility: false`（即**不优化**）

**变量取值**（`build/make/core/android_soong_config_vars.mk:108-109`）：

```make
# Enable SystemUI optimizations by default unless explicitly set.
SYSTEMUI_OPTIMIZE_JAVA ?= true
$(call add_soong_config_var,ANDROID,SYSTEMUI_OPTIMIZE_JAVA)
```

**关键结论：`SYSTEMUI_OPTIMIZE_JAVA` 默认 true 且不随 build variant 变化** —— 它是
make/env 级开关（`export SYSTEMUI_OPTIMIZE_JAVA=false` 可关），**eng/userdebug 构建同样开 R8**。

Soong 引擎语义（`build/soong/java/dex.go`）：

- L166-174 `effectiveOptimizeEnabled`：eng 构建 + `D8_on_eng` 才强制关；否则 `enabled` 显式值优先（SystemUI app 显式 `enabled: true`）。
- L176-178 `resourceShrinkingEnabled`：**`!ctx.Config().Eng()`** —— 资源收缩在 eng 构建被禁（代码优化仍开）。
- L180-182 `optimizeOrObfuscateEnabled`：`optimize: true` → R8 全模式（可 obfuscate，但 SystemUI 未设 `obfuscate`，见下）。

**`android_app "SystemUI"` 自身 optimize**（`Android.bp:977-979`）：

```
dxflags: ["--multi-dex"],
optimize: { proguard_flags_files: ["proguard.flags"] },
```

- `dxflags --multi-dex`：多 dex（Gradle minSdk≥21 自动，无需配置）
- proguard flags 由 `proguard.flags` 提供（见 c）

**defaults 链中与 optimize 相关的其余项**：

- `platform_app_defaults`（`frameworks/base/packages/Android.bp:25-37`）：**纯 error-prone javacflags，无任何 optimize 配置**
- `wmshell_defaults`（`frameworks/base/libs/WindowManager/Shell/Android.bp:210-216`）：`required: ["wmshell.protolog.json.gz", "wmshell.protolog.pb"]` —— 运行时 protolog 数据文件依赖，非编译优化

### 我方现状

- `app/build.gradle.kts` buildTypes debug/release 均未设 `isMinifyEnabled`（默认 **false**）
- `SystemUI-core` release 显式 `isMinifyEnabled = false`

### Gap

| 点 | AOSP | 我方 |
|---|---|---|
| R8 代码优化 | **默认开启**（SYSTEMUI_OPTIMIZE_JAVA=true，全 variant） | 关闭 |
| 资源收缩 | 非 eng 构建开启（shrink_resources + optimized） | 关闭（`shrinkResources` 未设） |

---

## c. 哪些地方加混淆（proguard/R8 规则）

### AOSP flags 文件链（均在 `frameworks/base/packages/SystemUI/` 下，我方 `app/` 已 1:1 复制，diff 实测 byte-identical）

**`proguard.flags`**（app 入口，5 行）：
1. `-include proguard_common.flags` — 引入公共规则链
2. `-keep class com.android.systemui.SystemUIInitializerImpl { *; }` — 保住 CoreStartable 反射入口
3. `-keep,allowoptimization,allowaccessmodification class com.android.systemui.dagger.DaggerReferenceGlobalRootComponent** { !synthetic *; }` — 保住 KSP 生成的 Dagger 根组件（非 synthetic 成员）

**`proguard_common.flags`**（`-include proguard_kotlin.flags` + 以下，逐条语义）：
1. `-keep class com.android.systemui.VendorServices { public void <init>(); }` — CoreStartable 反射实例化（SystemUIApplication#startAdditionalStartable）
2. WeaklyReferencedCallback 两组 `-keepnames`/`-keepclassmembers` — 弱引用回调注册的类保 init/成员，防被 shrink 掉后 weak registrar 悬挂
3. `-keep class androidx.core.app.CoreComponentFactory { void <init>(); }`
4. `-keep class com.android.wm.shell.* { void <init>(); }` + `-keepclassmembers class com.android.wm.shell.protolog.ShellProtoLogGroup { *; }` — WM-Shell
5. `-keepnames` bootclasspath 冲突类：`android.**.nano.**`、`com.android.**.nano.**`、`com.android.internal.protolog.**`、`android.hardware.common.**`、`com.android.window.flags.Flags` — 防 R8 access-modify 与 bootclasspath 冲突
6. `-allowaccessmodification` — 允许 private/protected 改 public，配合 getter/setter 内联
7. `-assumenosideeffects android.util.Log.v/isLoggable` + `Slog.v` + **`-maximumremovedandroidloglevel 2`** — strip verbose 日志（R8 私有扩展）

**`proguard_kotlin.flags`**：`-assumenosideeffects class kotlin.jvm.internal.Intrinsics { ... }` — 删 8 个 Kotlin↔Java 互操作 null/lateinit 检查（Intrinsics 检查、`!!`、lateinit 访问检查），减小体积。

**SystemUI-core（java_library 层）零 proguard 配置 — 复核确认**：
`awk` 提取 `Android.bp` L415-600 `SystemUI-core` 模块块内 `proguard|optimize|consumer` 匹配数 = **0**。
（soong `java_library`/`android_library` 默认 `Optimize.EnabledByDefault = false`，`build/soong/java/java.go:3409`；仅 app 默认 true，`app.go:1440`。）

**库级 proguard flags 如何进最终构建**（soong 语义，`build/soong/java/app.go:745-753`）：
- `export_proguard_flags_files: true` 的传递 static 依赖 → flags **无条件**汇入 app 的 R8（= Gradle `consumerProguardFiles` 语义）
- app 的**直接** static_libs（此处只有 SystemUI-core）自身的 `proguard_flags_files` 也汇入；间接依赖未 export 的不汇入

| 模块 | flags 文件 | export? | 实际进 SystemUI APK 的 R8? |
|---|---|---|---|
| `plugin/SystemUIPluginLib`（`plugin/Android.bp:37-42`） | `proguard_plugins.flags`（19 行：keep `plugins.**`、`log.core.**`、ConstraintSet 边界方法） | **是** | 是 |
| `plugin_core/PluginAnnotationLib`（L34-40） | `plugin_core/proguard.flags`（14 行：R8 full mode 注解保留 `-keepattributes RuntimeVisible*Annotation*` 等） | **是** | 是 |
| `plugin_core/PluginCoreLib`（L61-66） | 同上 `proguard.flags` | **是** | 是 |
| `shared/SystemUIFlagsLib`（`shared/Android.bp:106-108`） | `proguard_flags.flags`（1 行：`-keep class * implements com.android.systemui.flags.ParcelableFlag`） | **否** | **否**（且该模块无树内消费者，实为休眠配置；flags 类实际来自 aconfig 生成的 `com_android_systemui_flags_lib`，`aconfig/Android.bp:46`，无 proguard 配置） |
| `SystemUI-core` | 无 | — | — |

### 我方现状

- `app/proguard.flags` / `proguard_common.flags` / `proguard_kotlin.flags` 已从 AOSP 1:1 复制（三文件 diff 全部 byte-identical，来源 commit `31433963`）
- `app/build.gradle.kts` debug/release 均 `proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard.flags")` — **但 `isMinifyEnabled` 未开，规则从不生效**
- `SystemUI-plugin` / `SystemUI-shared` / `SystemUI-plugin-core` 的 build.gradle.kts **无任何 `consumerProguardFiles`**（grep 实测 0 匹配）— AOSP 侧 plugin/plugin_core 的 export flags 在我方丢失
- **已知缺陷**（Task 025 确证）：`SystemUI-core/build.gradle.kts:28` `consumerProguardFiles("consumer-rules.pro")` 引用不存在的文件 → `mergeReleaseConsumerProguardFiles` 必败；`:36` `proguardFiles(..., "proguard-rules.pro")` 同为悬挂引用（未触发）

---

## d/e. Debug-only vs Release-only 机制

### AOSP 事实

1. **`product_variables.debuggable` 触发条件**（`build/make/core/soong_config.mk:61`）：
   ```make
   $(call add_json_bool, Debuggable, $(filter userdebug eng,$(TARGET_BUILD_VARIANT)))
   ```
   即 **eng/userdebug → debuggable=true（用 src-debug）；user → false（用 src-release）**。
   （`build/soong/android/config.go:1368` `Debuggable()` 直接读该 product variable。）

2. **全 SystemUI 树唯一一处 variant 切换**：`grep -rn debuggable|product_variables --include=Android.bp` 全树仅 `Android.bp:433-437` 一处（core 的 src swap）；compilelib 在 `frameworks/libs/systemui` 同机制。

3. **compilelib IS_DEBUG 常量**：见 a 节。release 构建中 `Compile.IS_DEBUG=false` 使源码里 `if (Compile.IS_DEBUG)` 分支被 R8 常量折叠删除。

4. **其他 variant 相关机制盘点（均为平台级而非 SystemUI 模块级）**：
   - `SYSTEMUI_OPTIMIZE_JAVA`：**不随 variant 变**（b 节），是 env/make 开关
   - `RELEASE_SYSTEMUI_USE_SPEED_PROFILE`（`android_soong_config_vars.mk:113`）：baseline profile 开关，树内仅此一处赋值、无 soong 消费者（google 内部/后端消费），对模块 Gradle 配置无对应物
   - aconfig 无 per-variant 模式；flag 值由设备 `.pmac` / server control 决定，与编译 variant 无关（`FeatureFlagsReleaseStartableModule` vs Debug 的选择本身就是 src-release/src-debug 的内容）
   - `MinimizeJavaDebugInfo`（`config.go:1364-1366`）：`!Eng()` 时压缩 java debug info — 平台级 dex 细节，Gradle 侧无对应（也不需要）

### 我方现状

debug ↔ release 的全部差异 = `src-debug`/`src-release` srcSet + `compilelib-{debug,release}.jar` + KSP/AIDL 按 variant 接线。**与 AOSP 的 variant 维度语义一致**（AOSP 的 debuggable≈我方 debug，user≈我方 release）。我方额外差异：debug 用 debug keystore? 否——我方 debug 也签 platform keystore（对齐 AOSP certificate: "platform" 全 variant 签名）。

---

## f. 其他 release 相关

| 项 | AOSP（证据） | 我方 | 判定 |
|---|---|---|---|
| dexpreopt | `out/soong/.../SystemUI/dexpreopt.config`（实测存在）：`UncompressedDex: true`、`DexLocation: /system/system_ext/priv-app/SystemUI/SystemUI.apk`、boot image 依赖列表 | 无（也不应有：我们产出 sideload APK，非系统镜像 preopt） | **合理缺失** |
| dex2oat/speed profile | `RELEASE_SYSTEMUI_USE_SPEED_PROFILE`（`android_soong_config_vars.mk:113`），平台级 | 无 | 合理缺失 |
| `use_resource_processor: true` | app/core/res 均设（L969 等） | AGP aapt2 天然等价 | 对齐 |
| aapt 标志 | app 无 aaptflags（tests 模块才有 `--extra-packages`）；`:app` 另有 featureFlag 参数（我方为 WM-Shell AAR 变通，见 2026-08-13 文档） | `additionalParameters("--feature-flags", ...)` | 我方多出的**已知变通**，非 gap |
| manifest placeholder | bp 无 | 无 | 对齐 |
| 签名 | `certificate: "platform"`（L972），**不随 variant 变** | debug/release 共用 `keystore/platform.keystore` | **对齐** |
| `platform_apis: true` | L970 | compileSdkPreview=SysUISdk（隐藏 API 由自定义 SDK+framework.jar 提供） | 对齐（机制不同语义同） |
| `system_ext_specific` / `privileged` | L971-972 | 无 Gradle 对应（安装位置问题，与 APK 构建无关） | 合理缺失 |
| `required: ["privapp_whitelist_..."]` | L982-984 | 无（非 APK 内容） | 合理缺失 |
| `dxflags: ["--multi-dex"]` | L977 | minSdk≥21 自动 | 对齐 |
| kotlincflags `-Xjvm-default=all` | L975 | 顶层 `kotlin.compilerOptions` 已加 | 对齐 |

---

## Gap 总表（AOSP release 行为 vs 我方 vs 建议）

| # | 维度 | AOSP release（user 构建，SYSTEMUI_OPTIMIZE_JAVA=true 默认） | 我方现状 | 建议（待批准） |
|---|---|---|---|---|
| 1 | 编译代码集 | src + compose/features + facade/enabled + **src-release** | 同（release srcSet） | 无需改 |
| 2 | compilelib | IS_DEBUG=false jar | `compilelib-release.jar` | 无需改 |
| 3 | R8 代码优化 | **开**（optimize+shrink） | `isMinifyEnabled=false` 关 | 见建议 R1：`app/release` 设 `isMinifyEnabled=true` + `proguard-android-optimize.txt`（已引用）+ `proguard.flags`（已引用）。**分两步走**：先修悬挂引用（G1）拿到未混淆 release APK 基线，再开 R8（风险：R8 对 9000+ 类图 + KSP 生成代码的 keep 覆盖未知，AOSP flags 链是为此设计的，但 AOSP 用 R8 full mode + `-allowaccessmodification`，AGP 默认兼容模式不同） |
| 4 | 资源收缩 | 非 eng 开（shrink_resources + optimized） | 关 | 建议 R2（可选，二期）：`shrinkResources=true`；需 `res/raw/keep.xml` 类配套时回 AOSP 查证（AOSP 未用 keep.xml，靠 optimized shrink 的代码遍历；AGP 无 optimized shrink，语义有差） |
| 5 | app proguard flags | `proguard.flags`（→common→kotlin 链） | 文件已 1:1 复制且已 `proguardFiles(...)` 引用，**但 minify 关着不生效** | 随 R1 生效；无需改引用 |
| 6 | plugin/plugin_core export flags | `export_proguard_flags_files: true` → 汇入 app R8 | 丢失（模块无 consumerProguardFiles） | 建议 R3：`:SystemUI-plugin` 加 `consumerProguardFiles("proguard_plugins.flags")`（从 `plugin/Android.bp:37-42` 对应复制）；`:SystemUI-plugin-core` 加 `consumerProguardFlags` 内容 = `plugin_core/proguard.flags`。**.pro 文件来源**：AOSP 原文件复制（合规，同 proguard.flags 先例）；红线（build 文件 + 新文件），需批准 |
| 7 | SystemUIFlagsLib `-keep ParcelableFlag` | 休眠（无消费者，不进 app R8） | flags 来自 `systemui-flags.jar`（aconfig 生成，无规则） | **不加**：AOSP 自己都不汇入；保持一致 |
| 8 | core 层 proguard | **零配置**（复核确认） | `consumerProguardFiles("consumer-rules.pro")` + `proguardFiles(..., "proguard-rules.pro")` 两处悬挂引用，**AOSP 无对应物**，且 release 构建必败（Task 025） | 建议 G1（**最高优先级**）：删除 `SystemUI-core/build.gradle.kts` L28 `consumerProguardFiles("consumer-rules.pro")` 与 L31-35 release 块中 `"proguard-rules.pro"` 引用（保留 `getDefaultProguardFile` 亦可一并删——`isMinifyEnabled=false` 下本就不消费；最小 diff = 只删两处字符串）。对齐 AOSP"library 层零 proguard"。方向 2（Task 025 §8），需用户批准 |
| 9 | 日志 strip | `-maximumremovedandroidloglevel 2` 等（common 链） | 同文件已复制，待 R1 生效 | 无需改 |
| 10 | debug 变体 | AOSP eng/userdebug 同样 R8（除 eng 资源收缩）；src-debug | 我方 debug 不 minify | 保持现状：Gradle debug=开发迭代用，minify 只给 release，符合 Gradle 惯例且 AOSP 的"eng 也优化"源于性能敏感的出厂镜像，对我方目标（可安装验证 APK）无意义 |

## Release 写法具体建议（红线，全部待用户批准后才可实施）

**G1（修 release 阻塞，最小 diff）** — `SystemUI-core/build.gradle.kts`：
- 删 L28：`consumerProguardFiles("consumer-rules.pro")`
- release 块删 `"proguard-rules.pro"` 字符串（L31-35），或整个 `proguardFiles(...)`（isMinifyEnabled=false 下无消费者）

**R1（开启 R8，对齐 AOSP 主行为）** — `app/build.gradle.kts` release 块：
```kotlin
release {
    isMinifyEnabled = true          // AOSP SystemUI_optimized_defaults: optimize+shrink
    signingConfig = signingConfigs.getByName("release")
    proguardFiles(                   // 已有，无需改：proguard-android-optimize.txt + proguard.flags
        getDefaultProguardFile("proguard-android-optimize.txt"),
        "proguard.flags"
    )
}
```
前置：G1 落地 + R3 落地（否则 plugin 反射 API 会被 R8 删除）。验收：`:app:assembleRelease` 产出 APK 且
SystemUIPlugin 反射加载路径类保留（对照 `proguard_plugins.flags` keep 名单抽查 dex）。

**R2（可选二期）**：release 加 `shrinkResources = true`。

**R3（补 export flags 通道）**：`:SystemUI-plugin` / `:SystemUI-plugin-core` 增加
`consumerProguardFiles`，.pro 文件从 AOSP `plugin/proguard_plugins.flags`、`plugin_core/proguard.flags` 原样复制
（来源合规；落点遵循各模块根目录，与 `app/proguard.flags` 先例一致）。

**不建议做**：dexpreopt / speed profile / system_ext / privapp whitelist —— 镜像级概念，与独立 APK 构建无关。

---

## 证据清单（全部实测命令）

- `grep -n "DebugJavaFiles\|ReleaseJavaFiles" Android.bp` → L58/67/429/435/436/715
- `sed -n '920,986p' Android.bp`（soong_config defaults + android_app SystemUI）
- `build/make/core/android_soong_config_vars.mk:108-113`（SYSTEMUI_OPTIMIZE_JAVA / SPEED_PROFILE）
- `build/make/core/soong_config.mk:61`（Debuggable = userdebug|eng）
- `build/soong/java/dex.go:166-182`（effectiveOptimizeEnabled / resourceShrinkingEnabled）
- `build/soong/java/app.go:745-753` + `base.go:1982-1990`（static lib proguard 汇入 + export 语义）
- `build/soong/java/java.go:3409` / `app.go:1440`（library 默认不优化 / app 默认优化）
- `awk` SystemUI-core 模块块内 proguard|optimize 匹配数 = 0
- 我方三 .flags 文件与 AOSP diff = 全部 identical
- 我方 `SystemUI-plugin|shared|plugin-core` build.gradle.kts grep proguard/consumer = 0 匹配
- 我方 `SystemUI-core/src-{debug,release}/` 各 4 .kt；`libs/compilelib-{debug,release}.jar` 存在

## 构建说明

本文为只读研究，**未运行任何 Gradle 构建**（brief 允许但非必要；所有结论来自文件/grep/diff 证据）。
