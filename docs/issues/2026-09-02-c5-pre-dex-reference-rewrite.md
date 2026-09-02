# C5：最小 pre-D8/R8 平台 aconfig 引用改写设计

**日期**：2026-09-02
**状态**：Task 081 build-logic implementation 与 focused tests 已完成；等待 Chief 双轴 review，尚未运行任何 Android module build、R8 或设备验收

## 背景

Task 080 已将当前 Release APK 中四个 runtime-critical 旧平台类引用追溯到 166 个唯一引用类，覆盖：

1. `:SystemUI-core`、`:SystemUI-shared` 的项目编译类；
2. `libs/systemui-aconfig-flags.jar`、`libs/prebuilts/tracinglib-platform.jar`；
3. SettingsLib、WindowManager-Shell、WindowManager-Shell-shared 的 AAR `classes.jar`；
4. `personalcontext_ace_visualizer.aar` 的 `classes.jar`。

`libs/framework.jar` 只属于 compileOnly/library classpath，明确不属于 program input。

当前 Release APK 尚未修复，`tools/check_aconfig_jarjar_references.py` 仍应退出 1 并报告 `RESULT=FAIL`。

## 目标

在 Java/Kotlin 编译完成后、D8/R8 之前，只改写 Task 080 已证明的 166 个 program class 中下列四个类引用：

```text
android.app.Flags
  -> com.android.internal.hidden_from_bootclasspath.android.app.Flags
android.os.Flags
  -> com.android.internal.hidden_from_bootclasspath.android.os.Flags
android.view.accessibility.Flags
  -> com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags
com.android.window.flags.Flags
  -> com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags
```

不修改 AOSP SystemUI 源码，不改 JAR/AAR 交付物，不复制或打包平台类，不使用 stub、`dontwarn`、源码 import 改写或 post-R8 DEX patch。

## 推荐设计

### 单一构建 seam

新增一个仓库内 `buildSrc` Gradle plugin，并只在 `:app` 应用。插件使用 AGP 9.3.1 的公开 instrumentation API：

```text
variant.instrumentation.transformClassesWith(..., InstrumentationScope.ALL, ...)
```

AGP 9.3.1 官方 API 源码明确说明 `ALL` 在 application module 中覆盖当前项目及其 library dependencies；因此可在一个 pre-D8/R8 seam 同时看到 Task 080 已证明的 project-local、JAR 和 AAR program classes。

这不是此前被否决的“`Scope.ALL` + 原始 JarJar + 删除定义”算法：

- 只有 checked-in allowlist 中的 166 个 class identity 可进入 visitor；其余 program classes 不被 instrument；
- visitor 只改 class-file reference，必须保持 `this_class` 原值；
- 不删除任何 class，不把 source definition 改名为 hidden target；
- 四条 exact mapping 之外不做任何包级或通配改写；
- `libs/framework.jar` 既不是 runtime dependency，又不在 166-class allowlist 中。

### 两个冻结输入

1. `gradle/aosp17-critical-aconfig-reference-rules.txt`
   - 4 条 exact rule；
   - 按 source 字典序、LF、末尾换行；
   - SHA-256：`ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`；
   - 每条都必须逐字存在于完整 AOSP 规则文件（完整文件 SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`）。
2. `gradle/aosp17-critical-aconfig-reference-classes.txt`
   - Task 080 四节明细中的 166 个唯一引用类；
   - 点分 FQCN、字典序、LF、末尾换行；
   - SHA-256：`926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`。

插件必须 fail closed：文件缺失、格式错误、重复项、计数不符、SHA 不符或规则集合不是上述四项时，配置/测试失败。

### 字节码语义

实现使用 ASM 的 type remapping 能力覆盖 class 常量、字段/方法描述符、签名、annotation、method handle、invokedynamic 等 JVM 类型位置，但不得把任意 UTF-8 字符串当类引用。

对每个被允许的 class：

- 保存原始 `this_class`；
- 所有引用位置只按四条 exact rule 改写；
- 当前 class 自引用仍保持原始 identity；
- 输出 `this_class` 永远不得成为任一 hidden target。

默认使用 `FramesComputationMode.COPY_FRAMES`；本改写只替换等价 object type，不增加或删除指令，也不改变栈形状。

## 为什么选此方案

- **比逐模块 `Scope.PROJECT` 深**：一个 app-level seam 覆盖 project library、JAR、AAR，避免在多个模块重复接线。
- **比预改写/升版 AAR 深**：不制造第二套依赖产物，不改变 `libs/`，资源与 POM 不受影响。
- **比原始 JarJar 安全**：只改引用并保持 `this_class`，不会夺取设备平台类所有权。
- **比全局扫描宽改写窄**：行为边界固定为 Task 080 的 166 类 × 4 exact mappings。
- **可撤销**：移除 `:app` plugin 与 buildSrc/data 文件即可恢复现状。

## 拒绝的替代方案

1. **继续 Task 079 的 464-input broad replay**：与当前四类 runtime blocker 不成比例；保持暂停。
2. **逐模块 `Scope.PROJECT` + 预改写外部 AAR/JAR**：需要多点接线并产生/升版依赖产物，扩大修改面。
3. **无 allowlist 的 `InstrumentationScope.ALL`**：即便 mapping 很窄，也会让未证明 class 经过 visitor，不符合 Task 080 的最小边界。
4. **原始 JarJar 后删除 hidden definitions**：先错误地产生平台定义再删除，ownership 不安全，已否决。
5. **源码、DEX、ProGuard 或平台类副本 workaround**：违反既定约束或掩盖真实引用错误。

## TDD 与分阶段验收

Task 081 只实现 build logic 与 focused tests，不运行 app Debug/Release build。测试必须覆盖：

- 四条规则与 166-class allowlist 的格式、计数、SHA 与 fail-closed 行为；
- allowlisted caller 的 class reference 从 source 变 target；
- 非 allowlisted class 不进入 visitor；
- source-named class 的 `this_class` 与自引用保持原名，同时其对其他规则 source 的引用可转换；
- 任意输出均不定义 hidden target；
- 字符串常量不被误当类引用；
- descriptor/signature/annotation/instruction/handle/invokedynamic 等关键 ASM 路径。

后续任务严格串行：

1. Task 082：停止 Gradle/Kotlin daemon 后只做 Debug build 与静态检查；
2. Task 083：重新停止 daemon 后只做 Release build、R8 与 APK checker；
3. 独立 Debug 部署/重启门；
4. 独立 Release 部署/重启门。

Task 081 的 focused tests 绿色不代表 APK 或 runtime 已修复。

## 用户裁决与主机重启状态

用户于 2026-09-02 明确批准以下完整方案：

- 新增 `buildSrc` pre-D8/R8 reference-only AGP instrumentation plugin；
- `:app` 使用 `InstrumentationScope.ALL`，但以冻结 166-class allowlist 限定实际 instrument 范围；
- 只启用四条 runtime-critical exact mappings；
- Task 081 可新增 ADR 0008 记录此架构决定；
- Task 081 不运行 app build，构建与设备验收继续拆成后续串行任务。

用户同时说明主机已重启。Chief 复查后确认当前 `adb devices -l` 为空，且没有 emulator/QEMU 进程；Task 081 禁止且不需要设备操作，因此本任务开始前不重启模拟器。后续进入独立 Debug/Release runtime gate 前，再按当前 runbook 启动并核验专用 Android 17 模拟器。

## 首次 TDD worker 记录

首个 worker 从 fixed base `584ad47e01728e3b0c7905b7229d75bc3f23833e` 开始，只留下两个 Allowed Paths 内的未提交文件：

- `buildSrc/build.gradle.kts`
- `buildSrc/src/test/kotlin/com/android/systemui/build/aconfig/AconfigReferenceRewriteTest.kt`

它运行 `./gradlew -p buildSrc test --console=plain` 得到预期 RED：测试编译因 production API `AconfigReferenceRewriter` 尚不存在而失败。该 worker 随后额外运行了 brief 未授权的 `./gradlew --status`，且在 Chief 多次要求补齐十项 mandatory tests 后仍停留于设计推演，因此被停止。Chief 已终止 Gradle/Kotlin daemon；仓库中尚无 production implementation、冻结规则/allowlist、`:app` 接线、ADR 0008 或完成态证据，Android app build、R8、emulator 与 ADB 均未运行。

用户随后指定：后续创建的 worker/reviewer 统一显式使用 `joycode/GLM-5.3`、`thinking=high`；指令到达时已经运行的 worker 不需要为此调整。Task 081 replacement `task081-r3` 经 session JSON 核实符合该模型政策并完成 CONTRACT，但连续两个受限 checkpoint 仍停留于设计叙述、没有产生首个 test diff，因此 Chief 按 no-progress 规则停止该 worker并接回本任务。

## Task 081 实现与 focused TDD 证据

Chief 先将被 `.gitignore` 的 `com/android/systemui/build/aconfig/` 测试迁移到可追踪的 `com/android/systemui/aconfigrewrite/` 包路径，并补成三组 focused tests，覆盖 brief 的十项 mandatory contract。生产实现前运行：

```bash
./gradlew -p buildSrc test --console=plain
```

得到预期 RED：`:compileTestKotlin FAILED`，未解析的生产 seam 包括 `FrozenAconfigInputs`、`ReferenceOnlyClassRewriter`、`AconfigReferenceRewriteFilter` 和 `AconfigInstrumentationRegistration`。该命令没有配置或执行根工程 Android module。

随后完成：

- 两个冻结输入文件及 count/SHA/格式 fail-closed loader；
- 基于 ASM `ClassRemapper` 的 reference-only visitor，保持 `this_class` 和当前 class 自引用；
- 166-class filter 与 AGP `AsmClassVisitorFactory`；
- 仅由 `:app` 应用的 buildSrc plugin，registration 固定 `InstrumentationScope.ALL` 与 `FramesComputationMode.COPY_FRAMES`；
- ADR 0008。

同一 focused gate 的 GREEN 结果为 `BUILD SUCCESSFUL`，共 9 个 JUnit test（3 个 suite，0 failure/error）。测试逐项覆盖四规则与完整 AOSP provenance、166 allowlist、allowlisted/non-allowlisted filter、source-named class identity/self-reference、hidden definition 为零、普通字符串保持，以及 descriptor/signature/annotation/type instruction/method handle/invokedynamic remap。冻结输入复核结果：

```text
RULES=4
RULES_SHA256=ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85
ALLOWLIST_CLASSES=166
ALLOWLIST_SHA256=926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b
REFERENCE_ONLY_TESTS=PASS
HIDDEN_TARGET_DEFINITIONS=0
ANDROID_APP_BUILD=NOT_RUN
RESULT=PASS
```

Task 081 到此只达到 focused build-logic proof rung。Debug/Release APK 尚未重编，现有 Release APK checker 仍应保持旧的 `RESULT=FAIL`；Android build、R8、emulator 与 ADB 留给 review-PASS 后的独立串行任务。
