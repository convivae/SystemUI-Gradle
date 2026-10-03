# Android Studio Sync：SysUISdk MockableJarTransform 失败

日期：2026-10-03

> 后续：用户选择保留 JVM 测试，已转向并实现真实 SDK optional bridge 方案；
> 本文保留初次诊断与当时待选方案。当前进展见
> `2026-10-03-sdk-optional-bridge-implementation.md` 与 `../CURRENT_STATE.md`。

## 背景

用户在 Studio Gradle Sync 遇到多个 Android 模块 `androidApis` 配置失败，公共失败点为
`MockableJarTransform: android-SysUISdk/android.jar`，ASM 报
`Cannot read field "outgoingEdges" because "handlerRangeBlock" is null`。
本机 AOSP 根为用户确认的 `/home/leijiabin/myspace/aosp`，已完成构建；SDK 根为
`/home/leijiabin/Android/Sdk`。已有用户修改 `gradle.properties`，必须保留。

## 操作计划（执行前）

1. 阅读项目规范、ADR 0006、SDK composition 和 Gradle 配置。
2. 建立独立于 Studio UI 的 `androidApis` / AGP transformer 精确复现，保存完整 cause chain。
3. 对照当前 AGP 实现与真实 SDK class，区分输入损坏、真实方法体兼容性和环境因素。
4. 仅在证据充分且符合规则时实施最小修复；涉及 stub、源码/资源改写、升级或架构选型时先询问用户。
5. 重跑精确复现和适用回归；记录未执行的构建/Studio 验证，不将 `help` 成功当作 Sync 成功。

## 诊断结论（2026-10-03）

**根因已复现：AGP 9.3.1 的 MockableJarGenerator 与 SysUISdk 中保留真实方法体的
libcore bridge 不兼容；不是下载损坏，也不是 13 个模块各自缺依赖。**

单入口生成器按 ADR 0006 从 `core-libart/.../javac/core-libart.jar` 复制真实 class。
对以下四个失败 class，已逐项比较本机 AOSP 与已安装 SDK 的解压 class SHA-256，全部相等：

| class | SHA-256（SDK = 本机 AOSP） |
|---|---|
| `libcore/io/IoUtils$FileReader.class` | `138b3fe7d25d23b0984220cd29c84b948c69ce32fd5e825bac09666c618077d1` |
| `libcore/io/IoUtils.class` | `7a18d836b0553ec058196616c7facab0071be1976c4a093bf8b1fa2317198d2f` |
| `libcore/util/NativeAllocationRegistry.class` | `dac078a3ebf268ab33a8f763e4ed40e65803cb3492944596abeae7acb94f2e89` |
| `org/apache/harmony/dalvik/ddmc/DdmServer.class` | `a84e6512587c8c5db746b5c97479c20b50f37f2caeca351fdc6895971264e0ff` |

### AGP 机制证据

阅读当前 Gradle 缓存中的官方 9.3.1 sources JAR（不是根据旧版实现推测）：

- `builder-9.3.1-sources.jar`：`com/android/builder/testing/MockableJarGenerator.java`
  - `fixMethodBody()` 对普通方法执行 `instructions.clear()`，改成抛异常或返回默认值；
  - 未清理 `MethodNode.tryCatchBlocks`，其 start/end/handler label 仍引用被删除的指令；
  - `rewriteClass()` 以 `COMPUTE_MAXS | COMPUTE_FRAMES` 写出，ASM 在
    `MethodWriter.computeAllFrames()` 遍历异常区间时取到 null，报用户原样异常。
- `gradle-9.3.1-sources.jar`：`internal/ide/v2/ModelBuilder.kt:1018–1019,1204–1232`
  - IDE 为 host test component 创建 JavaArtifact；无论是否有测试源码，若 component 存在，
    都会解析 `variantModel.mockableJarArtifact.files`。
- `internal/tasks/factory/BootClasspathConfigImpl.kt:175–195`：惰性创建 `androidApis`，
  使用 `artifactType=android-mockable-jar` 和 `returnDefaultValues` 属性请求 transform。

公开来源坐标：`com.android.tools.build:builder:9.3.1:sources`、
`com.android.tools.build:gradle:9.3.1:sources`、`com.android.tools.build:gradle-api:9.3.1:sources`。

### 最小输入与结构探针

仅保留 SDK 原始 `libcore/io/IoUtils.class` 的单 class JAR，调用当前 AGP 的真实
`MockableJarGenerator(false).createMockableJar()`，仍稳定重现原异常（1 秒）。
反射调用其 `modifyClass()` 仅用于 `/tmp` 诊断，没有 patch AGP 或 live SDK：

```text
BEFORE IoUtils.closeQuietly(AutoCloseable): handlers=2 detached=0
AFTER  IoUtils.closeQuietly(AutoCloseable): handlers=2 detached=2
```

IoUtils 六个带异常处理表的方法均由 detached=0 变为全部 detached。
同 JVM / 同 AGP 转换官方 `android-37.0/android.jar` 成功。
这排除了本次故障必须依赖 Studio UI、并行 sync 或损坏缓存的解释；
JDK 21 不是此异常的独立根因。

## 错误数演变 / 实际验证

所有命令串行运行；未安装依赖、未清缓存、未替换 SDK。
诊断 init scripts、从官方 sources JAR 解包的只读参考和日志均在
`/tmp/sysuisdk-sync-diagnosis/`，不进入源码模块。

| 验证 | 实际结果 |
|---|---|
| 初版 init 直接读取 `androidApis` | 首次误应用到 buildSrc，修正 scope 后发现 CLI 配置阶段尚无惰性 androidApis；不计为目标复现 |
| `./gradlew :app:createMockableJar --offline --stacktrace --console=plain` | UP-TO-DATE / BUILD SUCCESSFUL；没有实际转换，**不代表 Sync 成功** |
| `:app:diagnoseAndroidApis -I /tmp/sysuisdk-sync-diagnosis/resolve.init.gradle`，调用真实 AGP generator | SysUISdk FAIL，原样 `handlerRangeBlock/outgoingEdges` |
| 同命令加 `-Dprobe.sdkJar=.../android-37.0/android.jar` | 官方 SDK PASS |
| 同命令加 `-Dprobe.sdkJar=/tmp/sysuisdk-sync-diagnosis/libcore_io_IoUtils.class.jar` | 单 class FAIL，原样异常 |
| `:app:diagnoseMockableClasses -I .../classes.init.gradle` | libcore/DDMS 10 class 中 4 FAIL、6 PASS；范围仅这 10 个，不声称全 SDK 无其他失败 |
| `:app:diagnoseExceptionLabels -I .../labels.init.gradle` | 六个方法的异常处理 label 全部由有效变为悬空，PASS（诊断证据，不是修复） |
| APK 构建 / APK 静态门 / 设备验证 | **未运行**，本轮只调查 Sync |
| Studio 再次 Sync / Tooling API 全模型回归 | **未运行**；尚未实施修复 |

上述诊断命令统一带 `--offline --console=plain`；完整堆栈验证追加
`--stacktrace -Dorg.gradle.jvmargs='-Xmx16g -Dfile.encoding=UTF-8 -XX:-OmitStackTraceInFastThrow'`。
关闭 JVM fast-throw 优化仅为取完整堆栈（已反复抛出的 NPE 原先无 message/stack），
不是修复选项，也未写入 gradle.properties。
关键日志：`direct-stack.log`、`stock.log`、`classes.log`、`minimal.log`、`labels.log`。

## 修复候选与待用户决策

**推荐候选：通过 AGP 公开 variant API 关闭 Android 模块的本地 JVM UnitTest component。**
维持真实 SDK 原样，使 IDE 不再请求对它做 mockable 转换。这是测试能力范围调整，
不是修复 AGP transformer 本身，必须先向用户说明并确认。

- 当前 Gradle Android 模块未显式接入本地测试源码；core 中保留的 pods `src/test`
  并非已配置的 Gradle test roots。不可删除这些 AOSP 源文件。
- 只针对 Android 模块的 UnitTest；不影响 `buildSrc` JVM 测试、纯 JVM 模块测试、
  Python 工具测试或 Android instrumented/device tests。
- 应使用当前公开 API `HasHostTestsBuilder.hostTests[HostTestBuilder.UNIT_TEST_TYPE].enable`，
  不使用已废弃 `VariantBuilder.enableUnitTest`，不私接 AGP 内部 task/configuration。
- 代价：Android 模块不能再直接使用 `testDebugUnitTest` / `testReleaseUnitTest`。
- **未实施或验证该候选**。用户批准后应先通过真实 Tooling API AndroidProject 模型做
  红/绿回归，确认全部 Android 模块不再生成 UnitTest artifact；再验证生产任务仍保留。

若用户需要本地 Android JVM 单元测试，应继续调研保留该能力的上游 AGP 修复途径；
不能在没有已修复版本证据时贸然升级整个工具链。

不采用的“捷径”：
- 删除 bridge 类或替换成 public SDK：破坏已验证的 hidden API/R8 library closure。
- 手工改写 SDK 方法体、生成 stub：违反项目规则/真实字节约束。
- 仅重新运行现有 SDK 生成器：这四个类本机 AOSP 与现有 SDK 本就字节相等，不能改变根因。
- `unitTests.returnDefaultValues=true`：该分支仍清空指令且不清理异常处理表；不是结构性修复。
- 清缓存、换 JDK、改 parallel sync：单 class / 同环境官方 SDK 对照已锁定实际失败路径。

目前只修改诊断文档及 CURRENT_STATE 的维护期 blocker 记录；生产代码、用户原有
`gradle.properties` 改动、SDK、AOSP 输入均未改动。
