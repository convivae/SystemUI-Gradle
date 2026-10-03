# PR #1：保留 Android JVM 测试的 SysUISdk 方案评估

日期：2026-10-03。状态：**方案评估历史记录；后续实现与验收见
`../issues/2026-10-03-sdk-optional-bridge-implementation.md`。没有合并 PR #1。**

## 结论

可以尝试通过调整 SDK 的 classpath 交付边界保留 JVM 测试，不必把真实方法体全部改成 stub。
推荐先验证 **SDK optional library 分离真实 libcore/DDMS bridge** 的方案：原始 class 字节不变，
只让不含这 10 类的 android.jar 进入 AGP mockable 转换。

本机有界实验已通过：从 SDK 临时副本分离这 10 类后，其余 android.jar 在当前 AGP 9.3.1
的 `returnDefaultValues=false/true` 两种配置下均转换成功；原 39,258 ZIP entries 的内容
在两个输出 JAR 中逐条验证相同。**这不是完整 SDK / Studio / JVM 测试 / R8 成功的声明。**

PR #1 的根因分析正确，但目前的全量方法体 stubbing 实现有规范冲突和技术阻塞，不建议直接合入。
上一轮“优先关闭 UnitTest”的建议不再作为当前首选；用户明确希望保留该能力。

## 1. 审阅对象和证据边界

- PR：https://github.com/convivae/SystemUI-Gradle/pull/1 ，状态 open。
- head：`4ee80743bd77f9be87e36a00670fc9310eb6a705`。
- base：`35def1f4f110824a9fe4f8c3f3d6a38b5c29ba17`（也是本地 HEAD）。
- API 中 PR body：`fix android studio sync error`；规格补充取其新增 issue 文档与本轮用户需求。
- issue comments、inline review comments、reviews API 均返回空数组。
- 下载 diff SHA-256：`c32b57cb531fd605b6606f480b71e6da825085988ee661985abf08444c92b192`。
- 固定 head 的生成器原文 SHA-256：`43b8c7db4cb13c82359327fcb353cfc5095cd6d225c5a60cc8f240b1d459e6a3`。
- PR 原代码/测试未在本机执行；以下 findings 基于固定源码、JVM 规范和本机原 SDK 的只读检查。
  PR 中的“已成功”属于作者报告，不当作本机端到端证明。
- 当前工具无后台 agent / 独立 reviewer 接口，本报告为主 agent 单人审阅，按两轴分列。

## 2. Standards：规范符合性

### S1 — 未获例外授权的 SDK 全量 stub 化违反现行规则

PR 在 `compose_android_jar()` 对包括 stock、framework overlay 和 bridge 在内的所有真实 class
调用 `stub_class_method_bodies()`；不是只清理不合法输入，更不是保留真实方法体。
这与 AGENTS 规则 P（禁止 stub）及 ADR 0006 的真实 AOSP bridge 字节合同冲突。

SDK API stub 与伪造业务实现的目的不同，技术上可以讨论，但不能通过更换名称假定已合规。
若选择该路线，需用户明确批准 SDK 范围例外，修订 ADR 和相应验证合同。

### S2 — 报告的 live JAR 修补路径不符合生成器事务与来源规则

PR issue 声称离线改写 live `android.jar` 并留下 `android.jar.pre-stub-bak`。
这不是单入口生成器完整的 staging→validation→marker→publish 流程。
修改已生成 JAR 而不重新生成 provenance inventory 会使来源记录与实际输出不一致；
backup 也不符合 generated platform 的无备份检查。不能以手工修补结果替代完整生成验证。

## 3. Spec：是否真正保留可用测试和可再生 SDK

### F1 — 完整 SDK 生成自相矛盾（阻塞）

固定 PR [生成器](https://github.com/chenpeigen2/SystemUI-Gradle/blob/4ee80743bd77f9be87e36a00670fc9310eb6a705/tools/build_sysuisdk.py#L718-L724)
先改写 bridge 方法体，但 `_validate_platform()`
[仍比较原始字节](https://github.com/chenpeigen2/SystemUI-Gradle/blob/4ee80743bd77f9be87e36a00670fc9310eb6a705/tools/build_sysuisdk.py#L820-L834)。
真实 IoUtils 等具有方法体，改写后必然不等于 `load_bridge()` 的输入，不能通过该门禁。
这是静态可证明的合同冲突；本机没有执行 PR 全量生成。

PR 修改组合测试夹具为“无方法体的最小 class”，这些夹具经过 stubbing 不变，
因而测试不能覆盖真实 bridge 在完整生成路径上的这一矛盾。

### F2 — MethodHandle 常量池长度读错（阻塞）

[PR L560–563](https://github.com/chenpeigen2/SystemUI-Gradle/blob/4ee80743bd77f9be87e36a00670fc9310eb6a705/tools/build_sysuisdk.py#L560-L563)
在已读过 tag 后，对 tag 15 再执行 `off += 4`；实际剩余结构仅
`u1 reference_kind + u2 reference_index`，应该是 3 字节。
参见 [JVMS §4.4.8](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html#jvms-4.4.8)。
因此含 CONSTANT_MethodHandle 的合法 class 会被错误解析。PR 所谓“独立”测试解析器
复制了相同 `off += 4`，不能作为这个边界的独立判据。

### F3 — 全量抹除 enum 方法破坏测试执行

PR 对包括 `<clinit>`、`values()`、`valueOf()` 在内的有 Code 方法一律替换为 throw。
AGP `MockableJarGenerator` 明确保留 enum 的 `<clinit>/values/valueOf/$values`，不会再次修复。
所以“AGP 转换输出了 JAR”并不能保证 enum 可用；可能到类初始化才抛异常。

本机原 SDK `javap` 确认 `com.android.tools.r8.keepanno.annotations.KeepItemKind` 是有真实
`<clinit>/values/valueOf` 实现的 bridge enum，此风险不是仅针对想象中的输入。
不是声称所有平台 enum 当前都可执行：如部分 framework turbine header 原本无 Code，
其完整测试运行能力也需要另行验证。

### F4 — 构造器首条 invokespecial 不等于 super 调用

[PR `_first_invokespecial_end`](https://github.com/chenpeigen2/SystemUI-Gradle/blob/4ee80743bd77f9be87e36a00670fc9310eb6a705/tools/build_sysuisdk.py#L430-L438)
不识别 receiver 身份。合法构造器可先 `new Foo()` 求值父构造器参数，首条 invokespecial
是 `Foo.<init>` 而非 `this/super` 初始化；也可在父调用前包含条件分支。
截断前缀并删 StackMapTable 不保证合法。尤其随后 AGP 再截断首条 invokespecial 并追加
RETURN，可能在 uninitializedThis 状态返回或留下跳向已删除位置的分支。
应以成熟字节码库和真实 JVM verifier 验证，不能用“找到第一个 0xb7”替代语义分析。

### F5 — “零编译信息损失”声明过强

普通 Java 外部调用通常只依赖 API；Kotlin inline 的实现会被编译器读入并内联，
不能一概断言 javac/kotlinc 只读签名。参考 [Kotlin inline functions](https://kotlinlang.org/docs/inline-functions.html)。
PR 把所有有 Code 的类纳入，而不审计 inline bodies / metadata / 编译时处理器加载行为。
这属于通用风险，**未实证当前 SDK 某 Kotlin inline 消费点已被它破坏**。
根构建文件还明确不向 KotlinCompile 注入 `libs/framework.jar`，因此它不能成为普遍的补救保证。

另：PR 中 SystemUI-common SDK 路径修复是独立问题，应单独处理；不要据此认为 androidApis
故障已解。其手写 local.properties 解析/“与 AGP 同序”的描述也不构成本轮 SDK 方案依据。

## 4. 推荐候选：真实 SDK optional library，而非修改 class 方法体

### 4.1 结构

```text
android-SysUISdk/
  android.jar                       # 原内容减去 libcore/DDMS 10-class slice
  core-for-system-modules.jar        # 原 bridge 先保持不动，验证重复 library 定义处理
  optional/
    optional.json                   # 保留已有 entries，追加 SDK 编译桥；manifest=false
    sysui-platform-bridge.jar        # 10 个 AOSP 原始 class，逐字节不变
```

消费 Android 模块使用公开 `android.useLibrary("<bridge-name>")` 加入编译 bootclasspath。
不能简单改成 `implementation`（会把平台类打进 APK）；也不能普通 `compileOnly` 后
想当然认为 R8 一定读取。纯 JVM 模块若确需这 10 类，须明确引入相同真实 JAR，不能依赖
AGP 的 useLibrary 自动传播到 JVM 插件。

### 4.2 当前版本官方实现提供的依据

以下均来自本机缓存的当前官方 sources JAR：

- `gradle-9.3.1-sources.jar / SdkParsingUtils.kt:96–107`：SDK platform 从
  `optional/optional.json` 读取 optional libraries；additionalLibraries 只适用于 SDK addon，
  不应混用概念。
- `sdklib-32.3.1-sources.jar / PlatformTarget.java:149–180`：optional entry 含
  `name/jar/manifest`，`manifest` 传入 `OptionalLibraryImpl`。
- `gradle-api-9.3.1-sources.jar / CommonExtension.kt:414–457`：公开 `useLibrary` DSL，
  用于 SDK 提供的 optional platform libraries。
- `BootClasspathConfigImpl.kt:103–127`：已请求的 optional library 进入 filtered bootclasspath，
  由 `BootClasspathBuilder` 选择；`fullBootClasspath` 则包含所有 optional libraries。
- `BaseR8Task.kt:285–294`：R8 library bootclasspath 来自 `global.fullBootClasspath`；
  Java9+ 另加 `core-for-system-modules.jar`。这与普通 compileOnly JAR 路径不同。
- `AndroidUnitTest.java:477–484,497–525`：本地测试 runtime 加入已请求 optional libraries，
  然后才放 mockable Android JAR；optional library 不被 MockableJarTransform 改写。
- `BootClasspathConfigImpl.kt:175–195`：mockable 解析仍只针对 `androidJarProvider`。

这些源码证明存在合适接缝，但不代替在本项目执行真实编译/R8/测试的验收。

SDK 的 metadata 应设置 `manifest=false`；未来需要检查最终 APK 不出现不存在的
`<uses-library>`。仅用 `useLibrary(name, false)` 不等于保证完全不产生 manifest entry。

### 4.3 已完成实验

命令（仅临时 init probe，不是生产工具）：

```text
./gradlew :app:diagnoseSplitSdk \
  -I /tmp/sysuisdk-sync-diagnosis/split.init.gradle \
  --offline --stacktrace --console=plain \
  -Dorg.gradle.jvmargs='-Xmx16g -Dfile.encoding=UTF-8 -XX:-OmitStackTraceInFastThrow'
```

实际输出：

```text
SPLIT_BYTE_IDENTITY_PASS entries=39258 moved=10
SPLIT_MOCKABLE_PASS returnDefaultValues=false
SPLIT_MOCKABLE_PASS returnDefaultValues=true
BUILD SUCCESSFUL in 16s
```

10-class slice 是生成器既有 allowlist 中的：IoUtils{,$FileReader}、
NativeAllocationRegistry{,$CleanerRunner,$CleanerThunk,$Metrics}、
DDMS Chunk/ChunkHandler/DdmServer/DdmVmInternal。不是按任意 package-prefix 猜测扩包。
所有条目的解压 bytes 在两份 JAR 中逐一核对；ZIP 容器字节不要求相同。
原始 SDK/AOSP 只读，输出仅 `/tmp/sysuisdk-sync-diagnosis/split-probe/`，没有生成新 platform
metadata，没有把该 JAR 配入生产构建。日志：`/tmp/sysuisdk-sync-diagnosis/split.log`。

## 5. 代价、限制及验收

### 推荐方案的代价：中等，主要在接线和验收，不在字节码转换

- 修改单入口生成器的 artifact 布局、optional metadata 合并、冲突/漂移 fail-closed、
  原始字节 union 验证、marker/tool version 及发布流程；base SDK 保持只读。
- 修改 ADR 0006 的 bridge 交付位置与验证合同，但**不要求放宽禁止 stub / 保留真实字节原则**。
  这是架构边界调整，需要用户认可后再实施。
- 统一 Android 模块的 useLibrary 接线；核查 JVM 模块和 Java module image 路径。
- 发布新 SDK 版本；旧 SDK 缺 optional bridge 时应明确失败，不能静默 fallback。
- 验证：两次 SDK 再生确定性、完整 IDE Tooling model/Studio Sync、真实本地 JVM 测试
  （非 NO-SOURCE/UP-TO-DATE）、Debug 编译、Release/R8 与 library 输入列表、双 APK 静态门、
  bridge 不打包及 manifest 无新 uses-library、必要时同树设备冒烟。
- 未执行这些完整 gate，不能说已经修好。

### 本地 JVM 测试能力的边界

Android 官方说明 mockable library 让测试可以引用/模拟 Android API，并不是 Android 运行时：
[Local tests / Mockable Android library](https://developer.android.com/training/testing/local-tests#mockable-library)。
分离的真实 libcore/DDMS 类也不是 host JVM 可完整执行的 ART 实现；native 方法、隐藏平台依赖、
class init 等仍可能失败，需要测试隔离。它们保留 final/native 标志，不会得到 AGP 自动去 final
的待遇，特定 mocking 方式须单独验证。Robolectric 对 API37/SystemUI hidden API 的支持不能
靠本次改 SDK 自动获得；需要真实系统行为的测试仍应走设备。

### 其他方案比较

| 路线 | 保留真实 class 字节 | JVM 测试 | 主要代价 |
|---|---|---|---|
| SDK optional bridge（推荐先验证） | 是 | 保留 AGP test component；仍需实测执行 | SDK 布局 + useLibrary + ADR 接线/发布变更；中等 |
| SDK 窄范围方法体标准化 | 否 | 可保留，但要维护 constructor/enum/inline 语义边界 | 需明确 SDK-only stub 例外授权、成熟工具、独立 ABI/JVM/端到端门禁；中高 |
| PR 当前全量方法体 stubbing | 否 | 转换成功不等于可执行 | 已有生成合同、解析器和 enum 阻塞；不建议直接使用 |
| 修复上游 AGP converter | 是（SDK 不改） | 可保留 | 上游修复/发行等待；自行 fork AGP 需版本维护和新依赖来源审批 |
| 双 SDK（编译真实 + 测试专用） | 编译侧可保留 | 取决于 wiring | AGP 无简单第二个 compileSdk 开关；避免私有 wiring，成本更高 |
| 关闭 UnitTest component | 是 | 不保留 Android 本地测试 | 改动小，但不满足本轮用户优先目标 |

不能仅在原 class 中删除异常表而保留指令：会改变真实语义及 verifier 数据，同样违反原字节合同。
也没有证据表明换官方 SDK 底座就能解决，因为触发类来自后续真实 bridge。
本机 core-libart 已有输出目录未见可直接替换的 turbine artifact；即使使用官方 header JAR，
header 可被编译器读取也不等于能在 JVM 执行，必须验证 mockable 输出。

## 6. 下一步建议

请用户批准 **只对隔离 SDK 副本做 optional bridge 方案的端到端验证**，通过后再落生成器、
ADR 与消费接线；不先合 PR，不先改 live SDK，不关闭本地 UnitTest。
若 optional bridge 不能满足真实测试/编译/R8 gate，再带具体失败证据讨论 SDK-only stub 例外
或上游 AGP 修复，而不是先放宽项目核心规则。

本轮运行：只读 javap / 官方源码与 PR 调研 / 上述临时 split + generator probe。
本轮未运行：PR Python 测试、PR 全量 SDK 再生、Studio/Tooling model、APK 构建、R8、真实 JVM
单元测试与设备验证。当前环境 PATH 未提供 uv，未为执行 PR 擅自安装或用系统 Python 绕过规则。
