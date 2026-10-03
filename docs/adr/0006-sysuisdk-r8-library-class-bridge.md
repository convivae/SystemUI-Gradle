# ADR 0006 — 通过 SysUISdk 向 AGP/R8 提供真实平台与构建期 library classes

## 状态

Accepted（2026-08-21；2026-10-03 用户批准 optional bridge 布局修订，保留真实字节与禁止 stub 的规则。验证记录见 `docs/issues/2026-10-03-sdk-optional-bridge-implementation.md`。）

## 背景

AOSP Soong 将 SystemUI 的代码收缩建立在多条 classpath channel 上：设备 bootclasspath
类、`libs`/header JAR、构建期 annotation JAR，以及 APK program inputs。AGP 9.3.1
主要把 compileSdk/SysUISdk bootclasspath 作为 R8 library input，不能直接表达 Soong 的
全部 Ch3/Ch4 library channels。

Task 040 后，fresh release R8 只剩 7 个真实 missing refs。其中 6 个属于平台或构建期
library definitions：

- `android.compat.annotation.UnsupportedAppUsage`
- `com.android.aconfig.annotations.AconfigFlagAccessor`
- `com.android.tools.r8.keepanno.annotations.UsesReflection`
- `libcore.io.IoUtils`
- `libcore.util.NativeAllocationRegistry`
- `org.apache.harmony.dalvik.ddmc.ChunkHandler`

第 7 个 `com.android.aconfig.annotations.AssumeTrueForR8` 具有 R8 flag-assumption 语义，
需要单独验证。

把这些类作为 `implementation` 会错误地将平台/构建期类打入 APK；复制 framework 源码
违反规则 F；`-dontwarn` 会隐藏可由真实定义闭合的 classpath 缺口。AGP 当前也没有公开、
稳定的 DSL 可把额外 JAR 直接声明为仅供 R8 使用的 library input。

## 决策（现行机制：单入口 + SDK optional bridge，2026-10-03）

1. SysUISdk 由单入口生成器重建：`python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp`。一次调用消费冻结的七输入 AOSP 映射（framework 聚合 JAR、framework-res.apk、core-libart、aconfig-annotations、keepanno、两个隐藏 AIDL 源），把真实 AOSP class entries 交付到 `android.jar`、SDK optional bridge JAR 与 `core-for-system-modules.jar`，使 AGP 将其作为 library classes 提供给 javac/Kotlin/R8，而不是作为 APK program classes。（D12 2026-08-29：原第八输入 unsupportedappusage.jar 随其 bridge slice 一并移除——17 framework 聚合 turbine JAR 已内嵌同名两类，framework 副本即最终字节。）
2. 精确 37 个 bridge entries（D12 后冻结清单）保持源字节不变：27 个 dalvik/aconfig/keepanno entries 留在 `android.jar`，10 个 libcore/DDMS entries 交付到 `optional/sysui-platform-bridge.jar`；`core-for-system-modules.jar` 仍保留全部 37 个。`android.jar` 与 optional JAR 的 bridge 定义必须不相交、并集完整；源字节校验、冲突拒绝、确定性输出与事务检查保留。不得用 package-prefix 推测或整包隐式注入。
3. 官方 base platform（默认 `android-37.0`）保持只读；生成在 sibling staging 目录进行，全部验证通过后以 rename 原子发布；输出目录由生成器拥有并以 marker 证明（marker 只记录 provenance，不是备份）。
4. `--replace` 只接受带有效 generator marker 的生成器自有输出；绝不替换官方 base platform。
5. `AssumeTrueForR8` 保持在 SysUISdk 之外，由 release build type 的唯一一条 exact `-dontwarn` adapter 处理（Task 044 用户批准）；必须保留真实 R8 flag-assumption 语义，不得通过 runtime packaging 或把该 annotation 打进 SDK 解决。

6. SDK `optional/optional.json` 保留 stock entries，新增 `com.android.systemui.platform.bridge`，`manifest=false`。Android 模块统一用公开 `android.useLibrary(...)` 消费；禁止 implementation 打包、普通 compileOnly 代替 R8 library channel，或私接 AGP 内部任务。
7. 不关闭 Android 本地 UnitTest，不修改 class 方法体。AGP 只对 `android.jar` 做 mockable 转换，optional bridge 按真实 class 进入测试 classpath；这并不保证 native/ART API 能在 host JVM 直接执行。SDK 元数据不声明新的设备共享库依赖，最终 APK 必须检查无对应 uses-library 条目。

## 2026-10-03 修订理由与权衡

AGP 9.3.1 MockableJarGenerator 替换真实 libcore 方法体后没有清理异常处理表，导致
Studio 的 androidApis 解析报 handlerRangeBlock/outgoingEdges NPE。只在 SDK 副本中
分离上述 10 类即可通过转换，且全部 class/resource 字节不变。官方 AGP 的
BootClasspathConfig、BaseR8Task、AndroidUnitTest 明确支持 optional SDK library 通道，
所以不需要改写 SDK 方法体，也不需要放弃本地 JVM 测试。

代价是 SDK 布局/消费配置同步升级（生成器 045.3+）、额外 JAR 与 metadata 的来源校验，
并重跑 IDE、真实 JVM 测试、Debug/Release 与 APK 边界门。旧 SDK 缺 optional library 时
应明确失败；不静默回退。全量 stubbing（PR #1）和关闭 UnitTest 均不是本项目采纳的修复。
这是交付位置变更，不放宽 AGENTS 的 P/F/R 规则或真实 library classes 合同。

## 后果

- SysUISdk 不再只是 framework API/resource 的容器，也成为 Soong→AGP 缺失 library channel
  的受控桥；每个桥接 slice 都必须可追溯到真实 AOSP artifact。
- AGP 的 compileSdk/R8 library-class 视图更接近 Soong，且不会扩大 APK program closure。
- 修改这些 AOSP artifact 版本或 class inventory 时，构建会通过 allowlist/source collision
  显式失败，需要重新审计，而不是静默吸收新类。
- Task 032 早期针对 `AconfigFlagAccessor` 的窄域 `-dontwarn` 建议被本结构性方案取代。
- 回滚方式是重新运行单入口生成器（用冻结映射的合法输入集）并以 `--replace` 替换生成器自有输出；不得手工删除 live JAR entries，也不存在 `--apply`/restore 接口。

## 历史修订记录（已被取代，仅存档）

以下 staged 流水线机制是本 ADR 的原始决策（2026-08-21 早期），已于同日随单入口生成器（Task 045）退役，仅供历史追溯，不再是现行工作流：

- 所有注入由 `tools/build_sysuisdk.py` 的显式 S0–S5 stage 完成；先构建 staging SDK，再通过
  `tools/build_sysuisdk.py --apply --source <staging>` 更新 live SDK；禁止直接 patch live SDK。
- 每个 stage 使用固定 source artifact、显式 class allowlist、来源字节校验、冲突拒绝、永久备份、
  幂等测试和 S5 staging/live 校验。
- Task 041 只处理六个普通 library-class roots（35 类，fresh R8 目标 7→1）；Task 042 单独验收
  `AssumeTrueForR8`（目标 1→0）。

随单入口落地，`tools/install_sdk.py`、`tools/patch_sdk_dalvik_annotations.py`、
`tools/patch_sdk_r8_library_classes.py` 及仓库 payload（`libs/android-merged.jar`、
`libs/framework-res.apk`）已删除；现行机制见
`docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`。

## 备选方案

1. **作为 `implementation`/program input 引入 JAR**：会把平台或构建期类打进 APK，否决。
2. **`compileOnly` JAR**：AGP 9.3.1 不保证将普通 compile classpath 作为 R8 library input，
   现有缺口已证明该路径不足，否决。
3. **精确或宽泛 `-dontwarn`**：隐藏真实可闭合的 library definitions，且不能保留完整
   annotation/signature 语义，否决。
4. **复制 framework/libcore 源码**：违反规则 F，否决。
5. **私有 AGP task wiring/reflection hack**：脆弱、难以随 AGP 升级维护；在公开 DSL 出现前不采用。
