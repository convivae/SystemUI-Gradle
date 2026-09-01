# AOSP-17 platform-aconfig JarJar closure — Soong 机制重建与 Gradle seam 设计

**日期**：2026-09-01（同日复审修正：初审报告的方案 A 算法与 R8 library 论断被否决，本版为修正版）
**任务**：task078（C5 blocker 诊断/设计；rewrite 实施明确不在范围内）
**状态**：研究完成；**pre-R8 变换族保留为首选族，但具体算法证据不足**，四个有界实验（E1–E4）完成前不得实施
**配套**：gate 工具 `tools/check_aconfig_jarjar_references.py`；issue 记录 `docs/issues/2026-09-01-c5-aconfig-jarjar-closure.md`

---

## 摘要

- AOSP 17 对 framework-owned aconfig flag 类实施自动传播 JarJar 重命名：725 条 exact `rule <source> <target>`（冻结文件 726 行，含末尾空行，SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`）把 `android.app.Flags` 等原名改写为 `com.android.internal.hidden_from_bootclasspath.*`。
- 重写发生在**每个 java 模块自己的 javac/kotlinc/turbine 输出上**（编译后、静态库合并/R8/D8/打包前），不是最终 APK 阶段。
- 秒级静态 gate（P1）已落地：Gradle Release `RESULT=FAIL`（4 critical source present / 4 target absent，exit 1），stock APK `RESULT=PASS`（exit 0）。Release 的直接死因：`android.app.Flags` 被引用但整个 program input 无定义、设备 bootclasspath 亦无原名 → `NoClassDefFoundError`。
- 三方案对比后**保留方案 A 族(pre-R8 程序输入变换)为首选,但具体算法证据不足**。初审提出的"Scope.ALL 一次性 jarjar + 删除 hidden 定义"算法已被否决:它会改名并删除依赖 jar 里合法的 app 自带 aconfig 实现,与 stock `FeatureFlagsImpl` 证据矛盾。修正后的候选算法是“按 stock R8 输入清单对齐产物变体（受影响 AAR 改从 repackaged 中间产物打包）+ 逐参与模块 project 编译产物做引用改写（`:app` 无源码，不存在单点 registration；见 §4.1）+ 不做任何定义删除”，其成立性依赖四个有界实验（E1–E4），**实施前必须完成并经用户裁决**；下一张可执行 brief 只覆盖 E1–E4 实验，实现任务范围待 E1 输出后另立（§5）。

---

## 1. 冻结证据与 gate 验证

### 1.1 规则文件（权威输入）

- 路径：`/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`
- SHA-256：`f79a08d4…5a6de97`；**726 行 = 725 条规则 + 1 行末尾空行**（task brief 与 issue 记录中的 "726 rules" 应更正为 725；gate 工具按规则条数解析为 725，不含空行）。
- 全部条目均为 exact `rule <source> <target>`；无 `zap`/`keep`/通配符。四条关键规则（行号 15/265/400/725）覆盖四个 runtime-critical source。
- 字节级同一文件（同 SHA-256）出现在 `SystemUI-core`、`SystemUI-application`、`SystemUI-application-compat-library` 的中间产物 `repackaged-jarjar/repackaging.txt` 中；`SystemUI` android_app 模块本身没有（它无自有源码，见 §2.4）。

### 1.2 gate 工具与验收输出

工具 `tools/check_aconfig_jarjar_references.py`：纯 stdlib DEX string_ids/type_ids/class_defs 读取器，区分 **referenced（type table）** 与 **defined（class defs）**，扫描 APK 内全部 `classes*.dex`；只接受 exact 规则，遇到通配符/`zap`/`keep` 显式拒绝（exit 2）。gate 判定（二轮复审硬化）：(i) 四个 critical source 必须完全不被引用；(ii) 四个 critical target 必须被引用；(iii) **全规则集合（725 条）中任一 target descriptor 被 define 即 FAIL**——改名后的平台类是设备 framework 的类，打进 APK 永远不合法，gate 因此无法靠打包 hidden 定义“满足”（critical target 是该全集检查的子集）。critical 集（硬编码，与冻结证据一致）：`android.app.Flags`、`android.os.Flags`、`android.view.accessibility.Flags`、`com.android.window.flags.Flags`。

```bash
uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q   # 26 passed（初审 19 + 一轮 4 + 二轮 3：非 critical target 定义 FAIL、critical target 定义 FAIL、app 自带原名定义不误杀）
```

**Gradle Release（exit 1，`RESULT=FAIL`）**：4 critical source 全部 referenced、4 target 全部 absent；全规则统计 30 source-present / 0 target；defined 原名类仅 3 个：`android.os.Flags`、`android.os.FeatureFlagsImpl`、`com.android.window.flags.Flags`（即 `android.app.Flags`、`android.view.accessibility.Flags` 被引用但**未定义**）。

**stock AOSP APK（exit 0，`RESULT=PASS`）**：4 critical source 全部 absent、4 target 全部 present；全规则统计 1 source-present / 36 target-present（36 个 target 全部为 `com.android.internal.hidden_from_bootclasspath.*` 引用，0 defined）。唯一 source-present 是 defined 的 `android.app.admin.flags.FeatureFlagsImpl`（见 §2.5）。

两台 APK 规模对照：stock 3 个 dex、53358 type refs、40185 class defs；Gradle Release 2 个 dex、33856 refs、22455 defs（R8 shrinking 均已运行；stock 的 `proguard_usage.zip` 17MB 证明其 shrinking 规模）。

### 1.3 Gradle 侧根源链（直接观察）

- 3 个 defined 原名类来自 `libs/systemui-aconfig-flags.jar`（`implementation`，`SystemUI-core/build.gradle.kts:481`），该 jar 仅含 `android/os/Flags.class` 与 `com/android/window/flags/Flags.class` 等，**不含** `android/app/Flags.class`、`android/view/accessibility/Flags.class`（`unzip -l` 验证）。因此 Release 中 `android.app.Flags` 是**悬空外部引用**：program input 无定义、R8 把它当 library class 留下。
- `libs/framework.jar`（compile-only）对四个 critical 类**同时含原名与 hidden 名两份**，编译期解析全部成功——这正是"编译能过、运行炸"的原因：编译用的是原名，设备 bootclasspath 里只有 hidden 名。
- Debug 未构建（`app/build/outputs/apk/debug/` 为空，本任务禁跑 Gradle）。**对今天未变换 Debug 的推断**（标注为推断）：D8 无 shrinking，`systemui-aconfig-flags.jar` 的原名定义全部入 dex 且被 jar 内部引用，APK 自洽，故 task075 观察到 Debug 可运行；Release 经 R8 shrinking 后出现悬空引用。**对未来变换后 Debug 的预测**（标注为预测，未验证）：project 与重打包 AAR 的引用改写为 hidden 后，app 自带 jar 的原名定义仍在（D8 不做 shrinking 清除），而定义同样出现在 type_ids 中，“source 不被引用”的 gate 判据对残留定义一样会判 present；该状态与 stock debug 构建形态如何对齐、Debug gate 口径是什么，需在实现任务中裁决（§4.1）。注意不得声称与 jarjar 语义矛盾的结论（初审即犯此错：声称“改名+删除后原名定义残留”）——定义一旦被 jarjar 改名并剥离，原名不可能残留；残留在新候选算法中的来源是**未被改名的 app 自带 jar**。

---

## 2. Soong 机制重建（P2，全部一手源码引用）

### 2.1 规则生成：aconfig 库声明"待填空"规则

`build/soong/aconfig/codegen/java_aconfig_library.go:127-135`：每个 `java_aconfig_library` 在 `ReleaseJarjarFlagsInFramework()`（release 配置）或 declaration `Exportable` 时，对 5 个生成类各调一次 `AddJarJarRenameRule(pkg+".Flags", "")` 等——**target 为空串**。即 aconfig 库自己只声明"这些名字将来要改"，不改成什么。

### 2.2 规则填充：`framework-minus-apex` 的 prefix

`frameworks/base/Android.bp:580-581`（module 定义起于 :547，defaults 链 `framework-minus-apex-with-libs-defaults` :472）：

```
jarjar_prefix: "com.android.internal.hidden_from_bootclasspath",
jarjar_shards: "10",
```

Soong 用该 prefix 把从依赖收集来的空 target 规则**填充**为 `rule android.app.Flags com.android.internal.hidden_from_bootclasspath.android.app.Flags` 形式，并落盘为 framework 模块的 `repackaging.txt`（725 条）。

注意区分：`framework-minus-apex` 另有一套**显式** `jarjar_rules: ":framework-jarjar-rules"`（`framework-jarjar-rules.txt`，含 hidl/perfetto/aconfig-storage 通配规则），那是另一种机制，与本文的自动传播规则**无关**，不要混淆。

### 2.3 规则传播：blueprint provider + 合并语义

每个 java 模块 `compile()`（`build/soong/java/base.go:1272-1283`）调 `collectJarJarRules(ctx)`：从依赖收集（static_libs/libs 按 `RenameUseInclude` 吸收、bootclasspath 按 `RenameUseExclude` 排除），空 target 与非空 target 合并时**非空胜出**，同 source 冲突 target 不同则报错；结果经 `JarJarProvider` provider 继续向下游传播，非空文本写入本模块 `repackaged-jarjar/repackaging.txt`。

这解释了字节级同一 SHA 的传播路径：framework（provider 持有 725 条已填充规则）→ `SystemUI-core` / `SystemUI-application` / compat-library 的 `repackaging.txt` 全部 `f79a08d4…`。

### 2.4 执行点与阶段排序（关键结论）

`build/soong/java/base.go:3436-3441` `repackageFlagsIfNecessary()` → `TransformJarJar()`。调用点全部位于**各模块自己编译产物**上：turbine/header jar（:1414/:1424/:1718/:1726）、kotlinc（:1633）、javac 各 shard（:1795/:1827/:1833）。jarjar 命令本体在 `build/soong/java/builder.go:356-368`：

```
java -DremoveAndroidCompatAnnotations=true -jar jarjar.jar \
  process <rulesFile> <in> <out> <total_shards> <shard_index>
```

（`removeAndroidCompatAnnotations=true` 是 AOSP fork 的定制项：剥离重命名类上的 `@UnsupportedAppUsage`，b/146418363。分片更正：自动规则路径经 `TransformJarJar` 硬编码 **1 个 shard**（`builder.go:1156-1158`，totalShards==1 时直接单次运行）；`framework-minus-apex` 的 `jarjar_shards: "10"` 只作用于显式 `jarjar_rules` 属性的另一条路径 `jarjarIfNecessary`（`base.go:3445-3464`），**不能**作为自动规则路径开销的证据——初审误用，已更正。）

**阶段排序表**：

| 阶段 | 顺序 | 证据 |
|---|---|---|
| aconfig codegen（生成原名类 + 空 target 规则） | 1 | java_aconfig_library.go:118-135 |
| javac/kotlinc/turbine | 2 | base.go:1633,1795-1833 |
| **jarjar 重写（本模块产物）** | **3（紧随编译）** | base.go:3436-3441 |
| 静态库组合（consumer 拿到已重写的 jar） | 4 | provider 传播 + repackaged jar 即 static_lib 交付物 |
| R8/proguard | 5 | 输入为已重写 jars |
| D8 dex / APK 打包 | 6 | 常规管线 |
| `SystemUI` android_app 自身 | 无重写 | 无自有源码，无 repackaged-jarjar 中间产物 |

未证明/未知项：无（本表每一行均有一手指令或中间产物证据）。

### 2.5 "30/0 vs 1/36"与 stock `FeatureFlagsImpl` 幸存者

- **Gradle Release 30/0**：我们的管线不存在 §2.4 的第 3 阶段；编译期对原名的引用（30 个 source descriptor 被 type table 引用）原样进入 R8。R8 shrinking 后 3 个 jar 里实际存在定义的原名类被保留，`android.app.Flags` 等 2 个 jar 里没有的定义成为悬空引用。
- **stock 1/36**：所有自有源码的引用已被 jarjar 改写为 hidden 名（36 个 target 被 reference、0 个被 define——定义在设备 framework 里）；唯一 source-present 是 **app 自带的 aconfig 静态库**：SettingsLib 静态链接 `device_policy_aconfig_flags_lib`（`SettingsLib/Android.bp:82`），该 jar 以**原名**进入 R8 输入（rsp 直接证据：`device_policy_aconfig_flags_java_export` 走普通 `javac/` 变体；变体选择机制见 §2.7），因此 APK 合法携带 `android.app.admin.flags.FeatureFlagsImpl` 的原名定义，其兄弟类（Flags/FeatureFlags/FakeFeatureFlagsImpl/CustomFeatureFlags）被 R8 视为未引用而移除。settingslib 自身对该包的引用（`RestrictedLockUtilsInternal`、`RestrictedPreferenceHelper`）已被其模块级 repackaging.txt 改写为 hidden `Flags`（对 repackaged jar 的 class 常量池逐类扫描验证：重写后仅含 hidden `Flags` 字符串）。
- **由此推断的 gate 设计约束**（已体现在工具里）：不能断言“725 条 source 全部 absent”——app 自带 aconfig 库是合法原名定义来源，且这些定义同样出现在 type_ids。gate 只对四个 frozen runtime-critical source 判 FAIL，并输出全规则统计作为诊断；target 侧则硬化为全规则任一 target 被 define 即 FAIL（改名后的平台类不得进 APK）。
- **未追溯到（标注 unknown）**：stock 中 `new FeatureFlagsImpl()` 的精确存活链。已证明：R8 program 输入（`withres/SystemUI.jar`，171MB 全量组合）中含全部 5 个原名 admin 类，但**没有任何 class 常量池引用** `android/app/admin/flags/FeatureFlagsImpl`；`proguard.flags`/`proguard_common.flags`/`proguard_kotlin.flags` 及 jar 内嵌 `META-INF/proguard/*` 均无针对 admin flags 的 keep 规则（唯一的 flags keep 是 `proguard_common.flags` 的 `-keepnames class com.android.window.flags.Flags`，keepnames 不阻止移除）。R8 为何保留该类（候选：baseline profile 钉住、R8 内部 keep 语义）未继续深挖——它不影响 gate 语义与方案对比，如实记录为 unknown。

### 2.6 可再生性（必须/禁止入库清单）

| 产物 | 来源 | 可从干净 AOSP 树再生？ | 入库策略 |
|---|---|---|---|
| 725 条规则文件 | Soong 构建期生成（intermediates） | 是：`m framework-minus-apex` 后取 `repackaged-jarjar/repackaging.txt`；其内容由 `frameworks/base/AconfigFlags.bp` 声明集 + prefix 决定 | **建议冻结副本入库**（如 `tools/data/`，附 SHA-256 校验），gate 与未来 transform 以冻结副本为准；AOSP 路径仅作对照 |
| `jarjar.jar` | AOSP 源码树 `external/jarjar`（Apache-2.0，AOSP fork）经 `m jarjar.jar` 构建 | 是 | 建议 host 工具入库（非 Android 依赖，不进 APK classpath，不违反规则 ②/③ 产物边界）；使用方式见 §4.1 |
| stock APK / Gradle Release APK | 各自构建 | 是 / 是 | 只读证据，不入库 |

### 2.7 stock R8 输入的逐产物变体选择（新增证据）

`withres/SystemUI.jar.rsp`（stock R8 program 输入清单，463 个 jar）显示改名范围是**逐产物决定**的，不是对全量输入的一次性变换：

- SettingsLib、WindowManager-Shell、WindowManager-Shell-shared、SystemUIFlagsLib、`com_android_wm_shell_flags_lib`、`am_flags_lib` 等以 `repackaged-jarjar/{javac,kotlinc}` **已改名变体**进入（163/463）；
- `device_policy_aconfig_flags_java_export`、`com.android.window.flags.window-aconfig-java`、`com_android_systemui_flags_lib` 等以普通 `javac/` **原名变体**进入——原名定义与原名内部引用原样进入 R8，靠 liveness 收缩；
- 哪些产物走哪个变体的精确判定规则（模块自身规则是否已被填充、消费方式 static_libs vs libs 等）**未完全追溯**，列为 E1 实验对象。

对照我们的 `libs/`（97 个 jar/AAR 的常量池扫描，复审新增）：`SettingsLib-2.0.1.aar`、`WindowManager-Shell-2.0.0.aar`、`WindowManager-Shell-shared-2.0.1.aar`、`personalcontext_ace_visualizer.aar` 引用四个 critical **原名**且**完全不含** hidden 字符串——它们从**非 repackaged** 的 Soong 中间产物打包，与 stock 实际链接的变体**不一致**。这是 Gradle 侧引用未改写的第二大来源（第一大是 project 模块自身编译产物）。`systemui-aconfig-flags.jar` 定义 `android/os/Flags` 等原名，方向上与 stock 的普通 javac 变体一致。

---

## 3. 目标语义（方案的判定标准）

未来 rewrite 落地后，Gradle Release 应达到 stock 同构：

1. 四个 critical source **不被引用**。本 gate 仅对这四个 critical source 强制完全缺席；**不得**推广为“725 条规则的全部 source 都不被 type_ids 引用”——§2.5 已证明 app 自带 aconfig 定义（如 stock 的 `android.app.admin.flags.FeatureFlagsImpl`）合法地以原名出现在 type_ids 中，无指令级/所有权感知判据就无法区分它们与违规引用。全规则 source 统计仅作诊断输出，直到存在这样的判据为止；
2. **不打包平台定义**：APK 不得 define 725 条规则集合中的**任何** target descriptor（`com.android.internal.hidden_from_bootclasspath.*` 是设备 framework 的类，critical target 是子集）——gate 已硬化（任一 target 被 define 即 FAIL），实现上也不得把改名后的平台类作为 program class 打进 APK；
3. **所有权安全**：app 自带 aconfig 库的原名定义（如 stock 的 `android.app.admin.flags.FeatureFlagsImpl`、我们的 `systemui-aconfig-flags.jar`）是合法的，变换不得删除、改名或把它们重定向到 framework 副本；
4. Debug/Release 一致：同一变换对 D8（无 shrinking）与 R8（有 shrinking）都成立，且需明确变换后 Debug 中残留原名定义的 gate 口径（定义同样出现在 type_ids）。

---

## 4. 三方案对比（P3）

### 4.1 方案族 A：pre-R8 程序输入变换（AGP scoped artifact API 或等价 seam）——**保留为首选族；具体算法证据不足**

**可用 seam（直接观察，二轮复审更正）**：正确 API 是 `AndroidComponentsExtension.onVariants { variant -> variant.artifacts.forScope(ScopedArtifacts.Scope.PROJECT).use(task).toTransform(ScopedArtifact.CLASSES, …) }`——`Artifacts.forScope(scope): ScopedArtifacts`（`gradle-api-9.3.1-sources.jar` 内 `com/android/build/api/artifact/Artifacts.kt:136`）；`useScope` 不存在，初审 API 名有误。`Scope.PROJECT` 的 KDoc 明确“not including imported projects nor external dependencies”（`com/android/build/api/variant/ScopedArtifacts.kt:31-38`）；`ScopedArtifact.kt` 已验证 `CLASSES : ScopedArtifact(), Appendable, Transformable, Replaceable`。**关键限制**：`:app` 无自有源码，仅在 `:app` 注册 `forScope(PROJECT)` 什么都不变换，也覆盖不了 16 个 library 模块——不存在“单点 registration / 17 模块零 hook”的形态。Soong 同构的候选必须是**集中配置**（如 build-logic convention plugin）的 registration，应用到**每个参与编译的 Android 源码模块**自己的 PROJECT classes；JVM 模块（`:SystemUI-plugin-core`、`:SystemUI-utils-kairos`）的 classes 以 external jar 形态进入 app，不在任何 Android 模块的 PROJECT scope 内，需要显式盘点与另行处理（等价 plain-Java 变换或其它裁决；`:SystemUI-plugin-processor` 为 build-time only 不进 APK，不参与）；res-only 模块无 classes 不参与。该逐模块机制属于 A 族自身的执行机制，其集中配置的可行性与完整参与清单**未证明**：若 E 实验显示无法集中配置，A 族标记 unresolved。

**初审算法已废弃（复审结论）**：初审提议 `forScope(ALL)` 一次性 jarjar 后“删除全部 hidden 定义”。该算法所有权不安全：Scope.ALL 会把**依赖 jar 里的 app 自带 aconfig 定义**（如 `systemui-aconfig-flags.jar` 的 `android/os/Flags`）一并改名，整体删除随后会抹掉或重定向这些合法 app 实现，与 §2.5 stock `FeatureFlagsImpl` 证据和 §3.3 目标直接矛盾。且 AGP 侧根本不存在能区分“平台副本”与“app 自带实现”的删除判据。废弃，不得复活。

**R8 library 论断更正（复审）**：初审声称“SysUISdk android.jar / framework.jar 不含 hidden 名、需附加 turbine jar 或窄域 dontwarn”——**错误**。直接观察：`/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar` 与 `libs/framework.jar` 均同时含四个 critical 类的**原名与 hidden 名两份**（`unzip -l` 验证）。按 ADR 0006，SysUISdk android.jar 正是向 R8 提供 library classes 的入口，改写后的 hidden 引用在 library classpath 上**应当**可解析；但“实际 R8 运行中可解析”需下一任务验证（E4），不得假设。“额外 turbine jar vs dontwarn”的裁决项整体撤销；`-dontwarn` 被 brief 禁止，**不作为可选路径提出**。

**候选算法（Soong 同构，未验证）**：
1. 按 stock rsp 的逐产物变体选择对齐交付物：把需要改写的 AAR（SettingsLib、WM-Shell 等，完整清单见 E1）改从 AOSP `repackaged-jarjar/` 中间产物重打包（修 `tools/package_aosp_aar.py` 的输入选择，纯产物来源修正）；
2. 仅对 project 模块编译产物做 jarjar 引用改写（Gradle seam：集中配置到每个参与 Android 源码模块的 `forScope(Scope.PROJECT)` `ScopedArtifact.CLASSES` 变换，或等价 classfile 变换；参与清单含 JVM 模块的显式处理，见上段）；
3. **不做任何定义删除**：app 自带 aconfig jar 的原名定义与内部引用原样保留，交给 R8 liveness 收缩，与 stock 行为同构（§2.7 原名变体产物同样直接进 R8）。

**证据不足之处与必需的有界实验（不得跳过，不得声称“无需实验”）**：
- **E1（本任务已部分完成）**：逐产物变体表——扩展到 rsp 全部 463 项中所有含 aconfig 引用的产物，与我们 `libs/` 清单逐一对照，得出“哪些产物需换成 repackaged 变体”的完整清单；同时追溯 Soong 侧变体选择的精确判定规则。
- **E2**：对受影响 AAR 做 repackaged 变体的干跑替换（scratch 副本，不动 `libs/`），常量池复扫验证引用全部变 hidden、无原名 critical 引用残留。
- **E3**：对 project 模块现有编译中间产物的副本跑 Soong `jarjar.jar` + 冻结规则，验证引用覆盖完整、且 project 产物不含 725 个 source 的任何定义（若有定义则候选算法需再评估）；同时实测耗时（自动规则路径在 Soong 为单 shard，无分片开销数据可引用）。
- **E4（实际 R8 解析）**：直接**独立调用** AGP 9.3.1 自带 R8（`java -cp <gradle-cache>/builder-9.3.1.jar com.android.tools.r8.R8 …`，已实测自报 `R8 9.3.16 (build 65eb2ed…)`；**不是 Gradle task**），验证 SysUISdk android.jar 作 `--lib` 时四个 critical hidden target 的解析：scratch 合成 program artifact 引用全部四个 hidden target descriptor、不定义它们；保留 probe class；按需关闭 shrinking/minification/desugaring。gate：R8 exit 0 且无 missing-class 诊断、输出仍引用全部四个 hidden target 且不定义；可行则用官方 base SDK（`android-37.0`）android.jar 作 `--lib` 跑阴性对照（预期出现 missing-class 诊断，证明探针能捕获未解析类），不可行则说明为何不需要。
- **Debug 口径**：变换后 Debug 将保留 app 自带 jar 的原名定义（定义出现在 type_ids，source-absent 判据同样适用），是否接受该状态（stock debug 构建同形态）需用户裁决。

**评价**：支持性中-高（AGP 公开 API 常规，但需集中配置到每个参与模块，非单点；AAR 重打包常规）；正确性**未证明**（候选算法与 stock 同构的论证依赖 E1–E4）；可再生性好（§2.6）；规则合规（AAR 换 repackaged 变体仍是 AOSP 原始产物交付，不违反规则 R/②；project 侧改写只改构建产物，不碰 src/res）。

### 4.2 方案 B：post-R8 DEX 改写——否决

在最终 `classes*.dex` 上重写 type 引用。否决理由：Soong jarjar 只吃 classfile，DEX 级需自研/引入 dexlib2 等重写器（string_ids 增删牵动全部 id 表、map_off、checksum、adler 校验）；签名前插入但位于一切 shrinking/merging 之后，丢失 R8 shrinking 协同（原名定义已被 R8 保留，还得再做定义清理）；multidex 边界、mapping.txt 与 debug info 均显示改名前名字，排障困难；Debug（D8）路径需复制一份实现。正确性与可维护性风险在三者中最高，收益为零。

### 4.3 方案 C：消费 Soong 预编译的 SystemUI 代码/最终产物——否决（工具除外）

把 AOSP 侧已重写的 `SystemUI-core`/`SystemUI-application` 中间 jar 或最终产物直接当 Gradle 依赖。这以 prebuilt 替换源码模块，直接违反规则 S 与 ADR 0003（源码模块是本项目根基），**红线否决**。（更正：逐模块在 Gradle 侧复刻 Soong per-module 重写**不属于**方案 C——它是 A 族自身的执行机制，见 §4.1，其复杂度代价已在 A 内如实计入。）

**工具层面的复用是方案 C 的合法残余并已并入 A 族**：jarjar.jar 与冻结规则文件都来自 AOSP（§2.6），A 族只是换了执行 seam，不换工具与规则。

### 4.4 结论矩阵

| 维度 | A 族：pre-R8 变换（变体对齐 + 逐参与模块 PROJECT 改写） | B：post-R8 DEX | C：消费 Soong prebuilt SystemUI 产物 |
|---|---|---|---|
| 支持性 | 中-高（AGP 公开 API，需集中配置到每个参与模块；AAR 重打包） | 低（自研 DEX 重写） | 红线（prebuilt 替换源码模块） |
| 正确性 | **未证明**（算法与 stock 同构依赖 E1–E4） | 低-中（id 表/签名/mapping 风险） | 高（机制同 A 族）/ — |
| 可再生性 | 高（AOSP 工具+规则冻结入库） | 中 | 高 |
| 规则合规 | 合规（repackaged 变体仍是 AOSP 原始产物） | 合规但高风险 | **红线违规**（规则 S/ADR 0003） |
| **结论** | **保留为首选族，算法待实验** | 否决 | 否决（工具复用并入 A 族） |

### 4.5 推荐（族级，待用户裁决）

**保留 pre-R8 变换族（方案 A 族）为首选**，但**具体算法的证据不足**：初审的一次性 Scope.ALL + 删除 hidden 定义的算法已证伪（所有权不安全，§4.1）；替换后的候选算法（变体对齐 + 逐参与模块 PROJECT 改写 + 不删除）与 stock 同构的论证依赖 E1–E4 四个有界实验，**在实验完成并经用户裁决前不得进入实施，不得声称“无需补充实验”**；若集中配置的逐模块 registration 不可行，A 族本身标记 unresolved。方案 B/C 维持否决。

---

## 5. 下一任务 brief 草稿（未执行；本轮只定义 E1–E4 实验任务，实现任务范围显式 defer）

“证据不足”的诚实后果：E1–E4 完成前，实现任务的确切路径（Allowed Paths、受影响 AAR 坐标清单、registration 形态与参与模块清单）**不可知，也不得虚构**。因此下一张可执行的任务 brief 只覆盖有界实验；实现 brief 在 E1 输出完整清单后另立。

### 5.1 实验任务（E1–E4）brief

**目标**：产出实现任务所需的全部判定输入，零行为变更。

**Allowed Paths**（实验任务）：
- `docs/issues/<date>-c5-jarjar-e1-e4.md`（新，实验记录）
- `docs/architecture/<date>-c5-jarjar-e1-e4.md`（新，变体表与实验报告）
- `tools/` 下新增只读分析脚本（Python，`uv run`；不得修改 gate 语义；脚本入库）；scratch 产物（E2/E3/E4 干跑输入输出、合成 probe artifact 等）不入库，仅存 scratch 目录
- 实验任务自身的 task brief

**Forbidden Paths**（实验任务）：
- 一切 `*.gradle*`、`libs/**`、`SystemUI-*/src/**`、res、manifest、`AGENTS.md`、`docs/adr/**`、`docs/orchestration/CHARTER.md`
- `/home/conv/myspace/aosp/**` 写入（干跑只能写 scratch 副本）
- Gradle/Soong/ADB/emulator 命令。E3 用现有 Gradle 编译中间产物副本 + host `jarjar.jar`（历史产物，不新跑构建）；E4 的实际 R8 运行**不属于本条禁令**：它是直接 `java -cp builder-9.3.1.jar com.android.tools.r8.R8` 的独立调用，不是 Gradle task、不触发构建——这是终审修正消除的契约矛盾（原 §5.1 把一切实际 R8 路径判为超范围并把 E4 降级为静态类存在性检查，而静态存在性已被证实、无信息量，与 §4.1/§4.5 “候选正确性依赖 E4 实际 R8 验证”直接矛盾）。E4 全部合成 artifact 与输出仅存 scratch 目录，不入库

**实验内容与 gate**：
- **E1（变体表）**：rsp 全 463 项 × 我们 `libs/` 与 project 模块清单逐一对照（不抽样）→ 完整“需换 repackaged 变体”清单 + Soong 变体选择判定规则追溯 + participating-module/JVM 模块处理清单。gate：清单覆盖全部 463 项。
- **E2（AAR 干跑）**：受影响 AAR 的 repackaged 变体 scratch 打包 + 常量池复扫。gate：critical 原名引用归零、hidden 引用出现、**无新增 hidden 定义**（target-defined 为零）。
- **E3（project 产物干跑）**：对各参与模块现有编译中间产物副本跑 `jarjar.jar` + 冻结规则。**前置断言**：每个被变换 artifact 中 725 个 source 的 matching 定义数为零（若有定义，候选算法需再评估并按规则 H 上报）；**后置断言**：725 个 target 的定义为零（hidden 平台定义不得被引入——注意 jarjar 同时改名引用与定义，无法“变换含原名定义的 artifact 又保留该定义”，前置断言正是为此存在）。同时实测耗时。
- **E4（SysUISdk R8 解析，实际运行）**：独立调用 AGP 9.3.1 bundled R8（`builder-9.3.1.jar`，自报 `R8 9.3.16`；非 Gradle task），以 SysUISdk android.jar 作 `--lib`：scratch 合成 program artifact（保留 probe class，关闭 shrinking/minification/desugaring）引用全部四个 critical hidden target descriptor 且不定义它们。gate：R8 exit 0、无 missing-class 诊断、输出仍引用全部四个 hidden target 且不定义；阴性对照用官方 base SDK `android-37.0` android.jar 作 `--lib`（预期 missing-class 诊断；若不可行需说明为何不需要）。
- **整体 gate**：`uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q` 全绿；Release gate 仍 exit 1 `RESULT=FAIL`、stock 仍 exit 0 `RESULT=PASS`（实验零行为变更）；`git diff --check` 干净；只触及 Allowed Paths。

### 5.2 实现任务（deferred，待 E1 输出后另立 brief）

实现任务的 Allowed Paths、受影响 AAR 坐标清单、participating-module registration 清单**在此显式不列出**：它们由 E1–E4 的输出决定。E1 清单落档前，任何声称“实现路径已知”的 brief 都是虚构。

不依赖 E 输出、现在即可固定的方向性红线：
- 不删除/改名/重定向 app 自带 aconfig 定义；被变换 artifact 前置断言零 matching source 定义、后置断言零 hidden target 定义；
- 不打包平台类（gate 已硬化：任一 target 被 define 即 FAIL）；
- 禁 `-dontwarn` / `@Suppress`；不改 src/res/manifest/AGENTS/ADR；AOSP 只读；
- 变换任务单测 fixture 必须是**分离输入**：(a) PROJECT 型 artifact——含 source 引用、零 matching source 定义，被变换；(b) external/app-owned aconfig 定义 jar——**故意不变换**；组合后断言：引用全部变 hidden、external 原名定义仍在、未引入任何 hidden target 定义。不得使用“单 artifact 同时含定义又被变换”的错误形态；
- Release gate 翻绿（exit 0、RESULT=PASS、四 critical target present 且全规则 target-defined 为零）；stock 对照仍 exit 0；Debug 口径按 §4.1 裁决项执行后验证。

---

## 6. 本任务执行记录

- 初审（commit `1f5e93e8`）：`uv run pytest …`（19 passed）、两次 gate 验收（Release exit 1 / stock exit 0）、AOSP 只读检索（grep/sed/unzip/python zipfile）。**未运行任何 Gradle/Soong/ADB/emulator 命令**（任务约束）。
- 一轮修正（commit `b4e021e8`）：同 pytest 套件（23 passed）、两次 gate 复跑确认冻结输出不变、`libs/` 97 产物常量池扫描、`SystemUI.jar.rsp` 变体分析、SysUISdk android.jar / framework.jar 双形态验证。
- 二轮修正（commit `cb1223f4`，chief FAIL 复审后）：gate 硬化（任一 target defined 即 FAIL）+ 3 个新单测（26 passed）；AGP API 更正为 `forScope(Scope.PROJECT)`（一手源码验证 `Artifacts.kt:136`、`variant/ScopedArtifacts.kt:31-38`）；`:app` 无源码、单点 registration 不可行的限制写入 §4.1；§3.1 收窄为仅四 critical source 强制缺席；§5 重构为“实验任务 brief + 实现 defer”。两次 gate 复跑：Release 仍 exit 1 FAIL、stock 仍 exit 0 PASS（36 target referenced / 0 defined）。
- 终审修正（本 commit，docs-only，代码/测试零改动）：消除 E4 契约矛盾——§4.1/§4.5 要求候选正确性依赖 E4 的实际 R8 验证，但原 §5.1 禁止一切实际 R8 路径并把 E4 降级为静态类存在性检查（该事实已被 §4.1 “R8 library 论断更正”证实，无信息量）。E4 重新定义为直接独立调用 AGP 9.3.1 bundled R8（`builder-9.3.1.jar`，已实测自报 `R8 9.3.16 (build 65eb2ed…)`；非 Gradle task）的实验，含 scratch 合成 program artifact、SysUISdk `--lib`、shrink/minify/desugar 关闭、阴性对照；§4/§5/issue/brief 同步。**E1–E4 仍未在 Task 078 中运行**（本轮仅更正定义；唯一新增运行是只读的 `R8 --version` 版本核实）。
- 所有 AOSP 引用文件均为只读；AOSP checkout 无任何写入。

## 7. 证据索引

| 事实 | 证据 |
|---|---|
| aconfig 空 target 规则生成 | `build/soong/aconfig/codegen/java_aconfig_library.go:127-135` |
| prefix 填充 | `frameworks/base/Android.bp:580-581`（module :547，defaults :472） |
| provider 传播 + repackaging.txt 落盘 | `build/soong/java/base.go:1272-1283` |
| 执行点（per-module 编译产物） | `base.go:1633,1718,1726,1795,1827,1833,3436-3441` |
| jarjar 命令 | `build/soong/java/builder.go:356-368` |
| 自动规则路径单 shard，与 jarjar_shards 无关 | `builder.go:1156-1158`（TransformJarJar 硬编码 1）；`base.go:3445-3464`（jarjarIfNecessary 为显式 rules 的分片路径） |
| SystemUI 侧规则字节一致 | 三处 intermediates `repackaging.txt` 同 SHA `f79a08d4…` |
| SettingsLib 静态链接 aconfig 库 | `frameworks/base/packages/SettingsLib/Android.bp:82`；重写后引用只剩 hidden `Flags`（class 常量池扫描） |
| stock R8 输入逐产物变体选择 | `withres/SystemUI.jar.rsp`：463 项，163 走 `repackaged-jarjar/`；SettingsLib/WM-Shell 为 repackaged，device_policy export/window-aconfig/systemui_flags_lib 为普通 `javac/` |
| 我们 AAR 从非 repackaged 产物打包 | `libs/` 97 产物常量池扫描：SettingsLib-2.0.1、WM-Shell-2.0.0、WM-Shell-shared-2.0.1、personalcontext_ace_visualizer 引用 critical 原名、无 hidden 字符串 |
| SysUISdk android.jar 与 framework.jar 双形态 | 两 jar `unzip -l`：四 critical 类均含原名 + `hidden_from_bootclasspath` 两份 |
| R8 输入含 5 个原名 admin 类、无外部引用者 | `withres/SystemUI.jar` 全量扫描 |
| flags keep 规则仅有 keepnames(window.Flags) | `frameworks/base/packages/SystemUI/proguard_common.flags` |
| AGP 9.3.1 ScopedArtifact.CLASSES Transformable | `gradle-api-9.3.1-sources.jar` 内 `ScopedArtifact.kt` |
| AGP API 为 `Artifacts.forScope(scope): ScopedArtifacts`，PROJECT 不含 imported/external | 同 jar 内 `com/android/build/api/artifact/Artifacts.kt:136`、`com/android/build/api/variant/ScopedArtifacts.kt:31-38` |
| AGP 9.3.1 bundled R8 入口与版本：`builder-9.3.1.jar` 自报 `R8 9.3.16 (build 65eb2ed…)` | `java -cp ~/.gradle/caches/modules-2/files-2.1/com.android.tools.build/builder/9.3.1/9cd910fdf4b695abce90ed6a07b6dd348541fc7a/builder-9.3.1.jar com.android.tools.r8.R8 --version`（Task 078 终审修正时只读核实） |
| Gradle 定义来源 | `libs/systemui-aconfig-flags.jar` 条目清单（`unzip -l`） |
