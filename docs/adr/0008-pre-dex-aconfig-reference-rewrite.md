# ADR 0008 — 在 app 级 pre-D8/R8 seam 做最小 aconfig 引用改写

日期：2026-09-02
状态：已批准（用户批准 Task 081 exact brief）

## 背景

AOSP 17 的 Soong 构建会根据 framework JarJar 规则，将部分 platform aconfig 类引用从公开源码名改为设备运行时实际提供的 `com.android.internal.hidden_from_bootclasspath.*` 名称。独立 Gradle 构建缺少该步骤，因此 Release DEX 仍引用四个旧名，并在 Android 17 设备上触发 `NoClassDefFoundError`。

Task 080 通过 class 常量池 `CONSTANT_Class` 与 `this_class` 语义，证明当前 blocker 仅涉及四条 exact mapping 和 166 个 program class identity。来源覆盖项目 library 输出、runtime JAR 及 AAR `classes.jar`；compileOnly `libs/framework.jar` 明确不属于 program input。

## 决策

1. 在仓库内 `buildSrc` 提供单一 Gradle plugin，只由 `:app` 应用。插件使用 AGP 9.3.1 公开 instrumentation API，在 application variant 上以 `InstrumentationScope.ALL` 注册 visitor，并使用 `FramesComputationMode.COPY_FRAMES`。
2. `ALL` 只负责覆盖 app 的项目 library 与 runtime JAR/AAR program inputs；factory 的 `isInstrumentable` 再以冻结的 166-class allowlist 限定实际处理范围。
3. 只启用以下四条来自 AOSP `repackaged-jarjar/repackaging.txt` 的 exact mapping：
   - `android.app.Flags` → `com.android.internal.hidden_from_bootclasspath.android.app.Flags`
   - `android.os.Flags` → `com.android.internal.hidden_from_bootclasspath.android.os.Flags`
   - `android.view.accessibility.Flags` → `com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags`
   - `com.android.window.flags.Flags` → `com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags`
4. 改写是 reference-only：保持输入 `this_class`，保持当前 class 的自引用，不删除 class，也不产生任何 hidden target definition。ASM type remapper 只处理 JVM 类型位置，不替换普通字符串常量。
5. 两个 checked-in 输入均 fail closed：四规则文件必须为 4 行且 SHA-256 为 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`；allowlist 必须为 166 行且 SHA-256 为 `926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`。缺失、CRLF、无末尾换行、格式错误、重复、排序/count/SHA/set 漂移均终止构建。
6. 完整 AOSP provenance owner 是 `frameworks/base/framework` 的生成规则文件，完整 SHA-256 为 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`；focused tests 逐行核对四条冻结规则确实存在于该 owner。

## 后果

- Debug 与 Release 将在 D8/R8 前获得同一组确定性引用转换，且不修改 AOSP SystemUI 源码、JAR/AAR 交付物、SDK、ProGuard 或最终 DEX。
- app-level `ALL` 是覆盖所有已证明 program input 类别所需的单一 seam；allowlist 防止未经 Task 080 证明的 class 进入 visitor。
- `libs/framework.jar` 仍只承担 compile/library classpath 职责，不会被转换或打包。
- 本任务的 focused build-logic tests 只证明 loader、visitor、filter 和 registration contract，不代表 APK 已重建或 runtime blocker 已关闭；Debug、Release 和设备重启验收分别由后续任务完成。
- 回滚只需从 `:app` 移除 plugin，并删除对应 `buildSrc` 与冻结输入文件。

## 被拒绝的替代方案

- 修改 SystemUI 源码 import：破坏 AOSP 源码对齐。
- 复制或打包 hidden platform class：会错误取得平台类 ownership，且违反 no-stub/framework 边界。
- 预改写并升版所有 JAR/AAR：制造第二套依赖产物和多点维护面。
- 无 allowlist 的全局 `ALL` visitor：处理范围超过已证明的 166 个 class。
- raw JarJar 后删除定义、`dontwarn`、class deletion 或 post-R8 DEX patch：掩盖或制造 ownership 问题，且偏离正确的 pre-D8/R8 seam。
- 恢复 Task 079 的 464-input/725-rule broad replay：对当前四类 runtime blocker 过宽，继续保持暂停。
