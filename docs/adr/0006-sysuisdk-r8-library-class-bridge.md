# ADR 0006 — 通过 SysUISdk 向 AGP/R8 提供真实平台与构建期 library classes

## 状态

Accepted（2026-08-21，用户明确批准 Task 041/042 两阶段方案）

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

## 决策

1. 通过声明式 SysUISdk 构建流水线，把真实 AOSP class entries 注入
   `android.jar` 与 `core-for-system-modules.jar`，使 AGP 将其作为 library classes 提供给
   javac/Kotlin/R8，而不是作为 APK program classes。
2. 所有注入必须由 `tools/build_sysuisdk.py` 的显式 stage 完成；先构建 staging SDK，再通过
   `tools/build_sysuisdk.py --apply --source <staging>` 更新 live SDK。禁止直接 patch live SDK。
3. 每个 stage 使用固定 source artifact、显式 class allowlist、来源字节校验、冲突拒绝、备份、
   幂等测试和 S5 staging/live 校验。不得用 package-prefix 推断或整包隐式注入。
4. Task 041 只处理六个普通 library-class roots。为闭合真实签名/annotation graph，使用
   `IoUtils` 2 类、`NativeAllocationRegistry` 4 类、DDMS owner package 4 类、
   `UnsupportedAppUsage` 2 类、`AconfigFlagAccessor` 1 类和完整 keepanno annotation package
   22 类，共 35 类；fresh R8 目标为精确 7→1，且这 35 类不得出现在 APK defined classes 中。
5. `AssumeTrueForR8` 留给 Task 042 的独立 stage/验收，必须保留其真实 R8 annotation 语义，
   目标为精确 1→0；不得通过 runtime packaging 或 `-dontwarn` 解决。

## 后果

- SysUISdk 不再只是 framework API/resource 的容器，也成为 Soong→AGP 缺失 library channel
  的受控桥；每个桥接 slice 都必须可追溯到真实 AOSP artifact。
- AGP 的 compileSdk/R8 library-class 视图更接近 Soong，且不会扩大 APK program closure。
- 修改这些 AOSP artifact 版本或 class inventory 时，构建会通过 allowlist/source collision
  显式失败，需要重新审计，而不是静默吸收新类。
- Task 032 早期针对 `AconfigFlagAccessor` 的窄域 `-dontwarn` 建议被本结构性方案取代。
- 回滚方式是用 `build_sysuisdk.py --apply` 应用不含对应 stage 的已验证 staging SDK；不得手工
  删除 live JAR entries。

## 备选方案

1. **作为 `implementation`/program input 引入 JAR**：会把平台或构建期类打进 APK，否决。
2. **`compileOnly` JAR**：AGP 9.3.1 不保证将普通 compile classpath 作为 R8 library input，
   现有缺口已证明该路径不足，否决。
3. **精确或宽泛 `-dontwarn`**：隐藏真实可闭合的 library definitions，且不能保留完整
   annotation/signature 语义，否决。
4. **复制 framework/libcore 源码**：违反规则 F，否决。
5. **私有 AGP task wiring/reflection hack**：脆弱、难以随 AGP 升级维护；在公开 DSL 出现前不采用。
