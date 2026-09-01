# AOSP-17 platform-aconfig JarJar closure — Soong 机制重建与 Gradle seam 设计

**日期**：2026-09-01
**任务**：task078（C5 blocker 诊断/设计；rewrite 实施明确不在范围内）
**状态**：研究完成，唯一推荐待用户裁决
**配套**：gate 工具 `tools/check_aconfig_jarjar_references.py`；issue 记录 `docs/issues/2026-09-01-c5-aconfig-jarjar-closure.md`

---

## 摘要

- AOSP 17 对 framework-owned aconfig flag 类实施自动传播 JarJar 重命名：725 条 exact `rule <source> <target>`（冻结文件 726 行，含末尾空行，SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`）把 `android.app.Flags` 等原名改写为 `com.android.internal.hidden_from_bootclasspath.*`。
- 重写发生在**每个 java 模块自己的 javac/kotlinc/turbine 输出上**（编译后、静态库合并/R8/D8/打包前），不是最终 APK 阶段。
- 秒级静态 gate（P1）已落地：Gradle Release `RESULT=FAIL`（4 critical source present / 4 target absent，exit 1），stock APK `RESULT=PASS`（exit 0）。Release 的直接死因：`android.app.Flags` 被引用但整个 program input 无定义、设备 bootclasspath 亦无原名 → `NoClassDefFoundError`。
- 三方案对比后**推荐方案 A**：AGP 9.3.1 `ScopedArtifact.CLASSES`（`useScope(ALL)`）单一 pre-R8 程序输入变换，复用 Soong 自家的 `jarjar.jar`（`external/jarjar`，Apache-2.0）与冻结规则文件做 classfile 级改写，再剥离变换产生的 hidden 定义，R8 shrinking 自然清掉失引用的原名定义。**本推荐为裁决项，未实施。**

---

## 1. 冻结证据与 gate 验证

### 1.1 规则文件（权威输入）

- 路径：`/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`
- SHA-256：`f79a08d4…5a6de97`；**726 行 = 725 条规则 + 1 行末尾空行**（task brief 与 issue 记录中的 "726 rules" 应更正为 725；gate 工具按规则条数解析为 725，不含空行）。
- 全部条目均为 exact `rule <source> <target>`；无 `zap`/`keep`/通配符。四条关键规则（行号 15/265/400/725）覆盖四个 runtime-critical source。
- 字节级同一文件（同 SHA-256）出现在 `SystemUI-core`、`SystemUI-application`、`SystemUI-application-compat-library` 的中间产物 `repackaged-jarjar/repackaging.txt` 中；`SystemUI` android_app 模块本身没有（它无自有源码，见 §2.4）。

### 1.2 gate 工具与验收输出

工具 `tools/check_aconfig_jarjar_references.py`：纯 stdlib DEX string_ids/type_ids/class_defs 读取器，区分 **referenced（type table）** 与 **defined（class defs）**，扫描 APK 内全部 `classes*.dex`；只接受 exact 规则，遇到通配符/`zap`/`keep` 显式拒绝（exit 2）。critical 集（硬编码，与冻结证据一致）：`android.app.Flags`、`android.os.Flags`、`android.view.accessibility.Flags`、`com.android.window.flags.Flags`。

```bash
uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q   # 19 passed
```

**Gradle Release（exit 1，`RESULT=FAIL`）**：4 critical source 全部 referenced、4 target 全部 absent；全规则统计 30 source-present / 0 target；defined 原名类仅 3 个：`android.os.Flags`、`android.os.FeatureFlagsImpl`、`com.android.window.flags.Flags`（即 `android.app.Flags`、`android.view.accessibility.Flags` 被引用但**未定义**）。

**stock AOSP APK（exit 0，`RESULT=PASS`）**：4 critical source 全部 absent、4 target 全部 present；全规则统计 1 source-present / 36 target-present（36 个 target 全部为 `com.android.internal.hidden_from_bootclasspath.*` 引用，0 defined）。唯一 source-present 是 defined 的 `android.app.admin.flags.FeatureFlagsImpl`（见 §2.5）。

两台 APK 规模对照：stock 3 个 dex、53358 type refs、40185 class defs；Gradle Release 2 个 dex、33856 refs、22455 defs（R8 shrinking 均已运行；stock 的 `proguard_usage.zip` 17MB 证明其 shrinking 规模）。

### 1.3 Gradle 侧根源链（直接观察）

- 3 个 defined 原名类来自 `libs/systemui-aconfig-flags.jar`（`implementation`，`SystemUI-core/build.gradle.kts:481`），该 jar 仅含 `android/os/Flags.class` 与 `com/android/window/flags/Flags.class` 等，**不含** `android/app/Flags.class`、`android/view/accessibility/Flags.class`（`unzip -l` 验证）。因此 Release 中 `android.app.Flags` 是**悬空外部引用**：program input 无定义、R8 把它当 library class 留下。
- `libs/framework.jar`（compile-only）对四个 critical 类**同时含原名与 hidden 名两份**，编译期解析全部成功——这正是"编译能过、运行炸"的原因：编译用的是原名，设备 bootclasspath 里只有 hidden 名。
- Debug 未构建（`app/build/outputs/apk/debug/` 为空，本任务禁跑 Gradle）。推断（标注为推断）：Debug 走 D8 无 shrinking，`systemui-aconfig-flags.jar` 的原名定义全部入 dex，APK 自洽，故 task075 观察到 Debug 可运行；Release 经 R8 shrinking 后出现悬空引用。Debug/Release 语义不一致是 C5 的次生症状。

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

（`removeAndroidCompatAnnotations=true` 是 AOSP fork 的定制项：剥离重命名类上的 `@UnsupportedAppUsage`，b/146418363。）

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
- **stock 1/36**：所有自有源码的引用已被 jarjar 改写为 hidden 名（36 个 target 被 reference、0 个被 define——定义在设备 framework 里）；唯一 source-present 是 **app 自带的 aconfig 静态库**：SettingsLib 静态链接 `device_policy_aconfig_flags_lib`（`SettingsLib/Android.bp:82`），该 jar 以**原名**合并进 app（静态库 jar 不经过 consumer 的重命名），因此 APK 合法携带 `android.app.admin.flags.FeatureFlagsImpl` 的原名定义，其兄弟类（Flags/FeatureFlags/FakeFeatureFlagsImpl/CustomFeatureFlags）被 R8 视为未引用而移除。settingslib 自身对该包的引用（`RestrictedLockUtilsInternal`、`RestrictedPreferenceHelper`）已被其模块级 repackaging.txt 改写为 hidden `Flags`（对 repackaged jar 的 class 常量池逐类扫描验证：重写后仅含 hidden `Flags` 字符串）。
- **由此推断的 gate 设计约束**（已体现在工具里）：不能断言"725 条 source 全部 absent"——app 自带 aconfig 库是合法原名定义来源。gate 只对四个 frozen runtime-critical source 判 FAIL，并输出全规则统计作为诊断。
- **未追溯到（标注 unknown）**：stock 中 `new FeatureFlagsImpl()` 的精确存活链。已证明：R8 program 输入（`withres/SystemUI.jar`，171MB 全量组合）中含全部 5 个原名 admin 类，但**没有任何 class 常量池引用** `android/app/admin/flags/FeatureFlagsImpl`；`proguard.flags`/`proguard_common.flags`/`proguard_kotlin.flags` 及 jar 内嵌 `META-INF/proguard/*` 均无针对 admin flags 的 keep 规则（唯一的 flags keep 是 `proguard_common.flags` 的 `-keepnames class com.android.window.flags.Flags`，keepnames 不阻止移除）。R8 为何保留该类（候选：baseline profile 钉住、R8 内部 keep 语义）未继续深挖——它不影响 gate 语义与方案对比，如实记录为 unknown。

### 2.6 可再生性（必须/禁止入库清单）

| 产物 | 来源 | 可从干净 AOSP 树再生？ | 入库策略 |
|---|---|---|---|
| 725 条规则文件 | Soong 构建期生成（intermediates） | 是：`m framework-minus-apex` 后取 `repackaged-jarjar/repackaging.txt`；其内容由 `frameworks/base/AconfigFlags.bp` 声明集 + prefix 决定 | **建议冻结副本入库**（如 `tools/data/`，附 SHA-256 校验），gate 与未来 transform 以冻结副本为准；AOSP 路径仅作对照 |
| `jarjar.jar` | AOSP 源码树 `external/jarjar`（Apache-2.0，AOSP fork）经 `m jarjar.jar` 构建 | 是 | 建议 host 工具入库（非 Android 依赖，不进 APK classpath，不违反规则 ②/③ 产物边界）；替换实现见 §4.1 备选 |
| stock APK / Gradle Release APK | 各自构建 | 是 / 是 | 只读证据，不入库 |

---

## 3. 目标语义（方案的判定标准）

未来 rewrite 落地后，Gradle Release 应达到 stock 同构：

1. 四个 critical source（推及 725 条规则的全部 source）**不被引用**，引用改写为对应 hidden target；
2. **不打包平台定义**：R8 shrinking 后 APK 不携带 `com.android.internal.hidden_from_bootclasspath.*`（那是 framework 的类）——实现上不得把改名后的平台类作为 program class 打进 APK；
3. app 自带 aconfig 库的原名定义（如未来出现 SettingsLib 式静态链接）是合法的，不得误杀；
4. Debug/Release 一致：同一变换对 D8（无 shrinking）与 R8（有 shrinking）都成立。

---

## 4. 三方案对比（P3）

### 4.1 方案 A：pre-R8 程序输入单一变换（AGP scoped artifact API）——**推荐**

**机制**：`AndroidComponentsExtension.onVariants { variant -> variant.artifacts.useScope(ScopedArtifacts.Scope.ALL).use(task).toTransform(ScopedArtifact.CLASSES, …) }`。AGP 9.3.1 `gradle-api` 源码已验证（`com/android/build/api/artifact/ScopedArtifact.kt`）：`CLASSES : ScopedArtifact(), Appendable, Transformable, Replaceable`，KDoc 明确"project + external dependencies 全量 classes、R8/dex 之前"。task 拿到全部 classes（jars + dirs），执行：

1. 合并为单一 jar（或逐 jar 处理）；
2. `java -DremoveAndroidCompatAnnotations=true -jar jarjar.jar process rules.txt in.jar out.jar`（Soong 同款工具、同款规则、同款参数）；
3. **剥离改名产物中的平台定义**：变换前断言输入不含 `com/android/internal/hidden_from_bootclasspath/**` 条目（应恒真），变换后删除全部此类条目——它们全是步骤 2 刚把 program 内 aconfig jar 原名定义改出来的"平台类副本"，删掉后引用保留、定义交还 framework；
4. 输出替换 `CLASSES`。

随后 R8（Release）/D8（Debug）消费同一变换产物：Release 下失引用的原名定义被 shrinking 自然清除（结果即 stock 形态：30→0 source 引用、hidden 引用外部解析）；Debug 下原名定义残留但 APK 自洽（与现状等价、无回归）。

**已知难点（实施前须裁决/验证）**：R8 的 library classpath（SysUISdk android.jar / framework.jar）不含 hidden 名，改写后 R8 会报 missing class。首选解法是把 AOSP `framework-minus-apex` repackaged turbine 中间 jar 作为附加 library 输入（hidden 名在其中，来源合法）；被否的替代是窄域 `-dontwarn`（ADR 0006 明令禁止用 dontwarn 掩盖，除非用户逐条裁决）。

**评价**：支持性好（AGP 官方公开 API，单点注册于 `:app`，17 个模块零改动）；正确性高（classfile 级重写即 Soong 语义，R8 shrinking 清定义与 stock 行为同构）；可再生性好（§2.6）；规则合规（改的是 Gradle 管线与构建产物，不碰 src/res，无 stub、无平台类打包、无 dontwarn）。风险：`Scope.ALL` classes 体积（Release 全量约数十 MB）的 jarjar 耗时需实测（I/O 型，Soong 对 framework 以 10 shards 分片提示单进程有开销；预估秒级~十秒级，可接受）。

### 4.2 方案 B：post-R8 DEX 改写——否决

在最终 `classes*.dex` 上重写 type 引用。否决理由：Soong jarjar 只吃 classfile，DEX 级需自研/引入 dexlib2 等重写器（string_ids 增删牵动全部 id 表、map_off、checksum、adler 校验）；签名前插入但位于一切 shrinking/merging 之后，丢失 R8 shrinking 协同（原名定义已被 R8 保留，还得再做定义清理）；multidex 边界、mapping.txt 与 debug info 均显示改名前名字，排障困难；Debug（D8）路径需复制一份实现。正确性与可维护性风险在三者中最高，收益为零。

### 4.3 方案 C：整建制复用 Soong JarJar 产物——否决（工具除外）

把 AOSP 侧已重写的 `SystemUI-core`/`SystemUI-application` 中间 jar 直接当 Gradle 依赖，或在 Gradle 里逐模块 hook compileJava/compileKotlin 输出复刻 Soong per-module 重写。前者以 prebuilt 替换源码依赖，直接违反规则 S 与 ADR 0003（源码模块是本项目根基），**红线否决**。后者（逐模块复刻）机制上最忠实于 §2.4 的 Soong 架构，但在 Gradle 里意味着 17 个模块的编译输出 hook、增量编译失效风险、模块间 jar 缓存语义重排，复杂度高而语义收益为零（方案 A 的单点变换产出与逐模块变换在最终字节上等价）。

**工具层面的复用是方案 C 的合法残余并已并入方案 A**：jarjar.jar 与冻结规则文件都来自 AOSP（§2.6），方案 A 只是换了执行 seam，不换工具与规则。

### 4.4 结论矩阵

| 维度 | A：pre-R8 scoped CLASSES | B：post-R8 DEX | C：复用 Soong 产物/逐模块 |
|---|---|---|---|
| 支持性 | 高（AGP 公开 API，单点） | 低（自研 DEX 重写） | 低（17 模块 hook）/ 红线（prebuilt） |
| 正确性 | 高（classfile 重写 + R8 协同 = stock 同构） | 低-中（id 表/签名/mapping 风险） | 高（机制同 A）/ — |
| 可再生性 | 高（AOSP 工具+规则冻结入库） | 中 | 高 |
| 规则合规 | 合规（待 R8 library 裁决项收尾） | 合规但高风险 | prebuilt 形态违规；逐模块形态合规 |
| **结论** | **推荐** | 否决 | 否决（工具复用并入 A） |

### 4.5 推荐（单一 seam，待用户裁决）

**方案 A**。理由浓缩：它是唯一同时满足 §3 全部四条目标、且实施面（一个 Gradle registration + 一个 host 工具 + 一份冻结规则）小到可以完整回滚的 seam。证据已充分，无需补充实验即可出实现 brief；唯一开放子项是 R8 missing-class 解法的选择（附加 library jar vs 窄域 dontwarn），列入 brief 的裁决点。

---

## 5. 实现brief草稿（未执行，仅供用户裁决后开新任务）

**范围**：`build-logic`（或 `:app` build.gradle.kts，用户定）新增一个 convention/registration：`useScope(ALL).toTransform(ScopedArtifact.CLASSES)` 任务；`tools/data/jarjar_rules_725.txt` 冻结规则（SHA-256 `f79a08d4…`）；`tools/jarjar/jarjar.jar` host 工具 + README（来源 `external/jarjar`、构建命令 `m jarjar.jar`、SHA-256）。

**步骤**：
1. 冻结规则文件与 host 工具入库，附校验脚本（Python，`uv run`）。
2. 变换任务：merge → jarjar process（`-DremoveAndroidCompatAnnotations=true`）→ 断言输入无 hidden 条目 → 删除全部 `com/android/internal/hidden_from_bootclasspath/**` 条目 → 替换 `CLASSES`。全 Python 或 Gradle task 内 `JavaExec` 皆可，由实施者按 ADR 0002（tools 一律 Python）与构建时序决定。
3. R8 missing-class 裁决：默认引入 AOSP repackaged framework turbine jar 作附加 library；如不可行，窄域 dontwarn 需用户逐条批准并在 issue 记录。
4. 测试：gate 翻绿（`uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/release/app-release.apk --rules tools/data/jarjar_rules_725.txt` → exit 0、RESULT=PASS、四 target present）；变换任务自身单测（fixture jar：含原名引用+原名定义，断言引用改写、定义剥离）；Debug 构建后 gate 同样 PASS（source 仍可能因无 shrinking 而 defined——需在 brief 实施时确认 gate 对 Debug 的口径：source 不被 *引用* 即达标）。
5. 红线：不改 `SystemUI-*/src/**`、res、manifest；不打包平台类；不用 `@Suppress`；不改 AGENTS/ADR；AOSP 目录只读。
6. 回滚：删除 registration + 两个入库文件即完全回滚；APK 输出回到现状（gate 复红）。

**验收**：Release gate exit 0；stock 对照仍 exit 0；`git diff --name-only` 仅含新增文件与单点 registration。

---

## 6. 本任务执行记录

- 运行：`uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q`（19 passed）、两次 gate 验收命令（Release exit 1 / stock exit 0）、AOSP 只读检索（grep/sed/unzip/python zipfile）。**未运行任何 Gradle/Soong/ADB/emulator 命令**（任务约束）。
- 所有 AOSP 引用文件均为只读；AOSP checkout 无任何写入。

## 7. 证据索引

| 事实 | 证据 |
|---|---|
| aconfig 空 target 规则生成 | `build/soong/aconfig/codegen/java_aconfig_library.go:127-135` |
| prefix 填充 | `frameworks/base/Android.bp:580-581`（module :547，defaults :472） |
| provider 传播 + repackaging.txt 落盘 | `build/soong/java/base.go:1272-1283` |
| 执行点（per-module 编译产物） | `base.go:1633,1718,1726,1795,1827,1833,3436-3441` |
| jarjar 命令 | `build/soong/java/builder.go:356-368` |
| SystemUI 侧规则字节一致 | 三处 intermediates `repackaging.txt` 同 SHA `f79a08d4…` |
| SettingsLib 静态链接 aconfig 库 | `frameworks/base/packages/SettingsLib/Android.bp:82`；重写后引用只剩 hidden `Flags`（class 常量池扫描） |
| R8 输入含 5 个原名 admin 类、无外部引用者 | `withres/SystemUI.jar` 全量扫描 |
| flags keep 规则仅有 keepnames(window.Flags) | `frameworks/base/packages/SystemUI/proguard_common.flags` |
| AGP 9.3.1 ScopedArtifact.CLASSES Transformable | `gradle-api-9.3.1-sources.jar` 内 `ScopedArtifact.kt` |
| Gradle 定义来源 | `libs/systemui-aconfig-flags.jar` 条目清单（`unzip -l`） |
