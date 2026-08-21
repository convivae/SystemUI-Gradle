# ADR 0006 — 通过 SysUISdk 向 AGP/R8 提供真实平台与构建期 library classes

## 状态

Accepted（2026-08-21，用户明确批准 Task 041/042 两阶段方案；同日机制修订为单入口生成器，见“决策”与“历史修订记录”）

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

## 决策（现行机制，2026-08-21 修订为单入口）

1. SysUISdk 由单入口生成器重建：`python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp`。一次调用消费冻结的八输入 AOSP 映射（framework 聚合 JAR、framework-res.apk、core-libart、unsupportedappusage、aconfig-annotations、keepanno、两个隐藏 AIDL 源），把真实 AOSP class entries 注入 `android.jar` 与 `core-for-system-modules.jar`，使 AGP 将其作为 library classes 提供给 javac/Kotlin/R8，而不是作为 APK program classes。
2. 精确 39 个 bridge entries（Task 041 冻结的 35 个 library-class entries + 4 个 dalvik 优化 annotation entries）同时进入两个 SDK target JAR；源字节校验、冲突拒绝、确定性输出与幂等测试内置于生成器。不得用 package-prefix 推测或整包隐式注入。
3. 官方 base platform（默认 `android-37.0`）保持只读；生成在 sibling staging 目录进行，全部验证通过后以 rename 原子发布；输出目录由生成器拥有并以 marker 证明（marker 只记录 provenance，不是备份）。
4. `--replace` 只接受带有效 generator marker 的生成器自有输出；绝不替换官方 base platform。
5. `AssumeTrueForR8` 保持在 SysUISdk 之外，由 release build type 的唯一一条 exact `-dontwarn` adapter 处理（Task 044 用户批准）；必须保留真实 R8 flag-assumption 语义，不得通过 runtime packaging 或把该 annotation 打进 SDK 解决。

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
