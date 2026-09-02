# C5 Task 095：production immutable-input seam 与 visitor proof

**日期**：2026-09-02
**状态**：**PASS（用户于 2026-09-02 批准校准 direct gate）**。原 frozen `0/2→2/2` 判据的实际结果仍如实保留为 `INCONCLUSIVE_DIRECT_VISITOR`（实际 1/2）；用户随后批准以“至少一个真实 allowlisted instruction-level rewrite 已落入 DEX，同时 hidden target definitions 为 0、old source definitions 保留”为本任务 corrected direct gate，并授权不重跑 Gradle、直接进入 Standards/Spec 双轴 review。该 PASS 仅关闭 production immutable-input seam + bounded real visitor proof，不声明完整 Debug/Release APK、四映射静态门或 runtime 成功。
**前置**：Task 094 正式 `PASS`。configuration-time validated 4 mappings / 166 allowlist managed values 与 field-free no-op factory 已在真实 `:app:desugarDebugFileDependencies` dependency transform 中通过 isolation；该结果尚未证明 production `referenceOnlyVisitor(...)`。

## 背景

当前 production plugin 仍把 rules/allowlist 作为两个 `RegularFileProperty` 传给 factory，production factory 仍持有 `@Transient @Volatile cachedInputs`、`synchronized(this)` 初始化和 writeback。Task 093 已证明完整 cache layer 足以在 callback 前激活 Task 084 literal serialization path；Task 094 则证明去掉 factory-owned state、改用 Gradle-managed immutable values 可以通过相同真实 transform seam。因此下一步不再拆 cache 子字段，也不引入 external weak cache，而是把 Task 094 已证边界迁入 production 并恢复 reference-only visitor。

## 设计

1. Plugin 在 application plugin 生效后、`onVariants` 之前只调用一次 `FrozenAconfigInputs.load(rulesFile, allowlistFile)`。该调用继续承担四条 exact mappings、166-class allowlist、固定 SHA/count/排序/格式校验。
2. `AconfigInstrumentationRegistration.registerForPlugin(...)` 接收已校验的 `FrozenAconfigInputs`，不再接收文件；它把 mappings/allowlist 写入 `@Input MapProperty<String, String>` 与 `@Input SetProperty<String>`。
3. Production factory 只作为 managed parameters 到 visitor 的纯 adapter：无 worker-authored instance/static/companion field、cache、thread-local、`@Transient`、`@Volatile` 或 synchronization。allowlist helper 移为 top-level pure function，避免 factory 自身生成 Kotlin `Companion` field。
4. `isInstrumentable(...)` 从 managed allowlist 判断；`createClassVisitor(...)` 把 dot-FQCN mappings 转为 internal names，并调用既有 `referenceOnlyVisitor(...)`。不修改 rewriter 语义：`this_class`、current-class self-reference 和普通字符串保持不变，hidden target definition 仍禁止打包。
5. 保持 application-only、`InstrumentationScope.ALL`、`FramesComputationMode.COPY_FRAMES`；不改 app/module wiring、rules/allowlist bytes、AOSP/SystemUI 源码、SDK、`libs/**` 或 ProGuard/R8 配置。

这是比 external weak cache 更深、更小的 production seam：配置侧负责一次性校验与 immutable snapshot，factory 只负责读取声明式 transform inputs 和构造 visitor；没有 daemon-global lifetime/keying/expiry/concurrency 语义，也没有逐 class 文件 I/O。

## 紧密反馈环

本任务只允许两个串行 Gradle wrapper invocation：

1. focused `buildSrc` tests，覆盖 frozen input、registration contract 和 reference-only visitor 语义；
2. 真实 `:app:desugarDebugFileDependencies --info --stacktrace`，验证 production factory isolation 与 visitor execution。

真实 visitor 的可观察证据来自该 direct task 的两个已证明 external-file caller inputs：

- `libs/systemui-aconfig-flags.jar`；
- `libs/prebuilts/tracinglib-platform.jar`。

Task 094 no-op 后的当前 direct-output baseline 中，`android.os.Flags` 与 `com.android.window.flags.Flags` 的两个 hidden targets 均为 `referenced 0/2, defined 0/2`。Task 095 direct transform 必须把对应 hidden targets 变为 `referenced 2/2, defined 0/2`，同时保留两个 old source definitions 为 `defined 2/2`。old source descriptor 在聚合 DEX type table 中仍会因 preserved definitions/self-references 出现，不能错误要求 source aggregate refs 为 0。其余两条 mapping 主要来自 AAR/project callers，留给下一独立 full Debug build/static gate 证明。

## 接受条件

- Production source 不再包含 file-backed parameters 或 factory cache layer；configuration-time load call site 恰好一次。
- Factory 编译 class 经 `javap -p` 无 worker-authored declared field；parameters 仅暴露 managed `MapProperty`/`SetProperty` accessors。
- 既有 9 个 focused tests 全通过；registration test 必须验证 application-only、exact production factory、`ALL`、`COPY_FRAMES` 与 exact 4/166 managed values。
- Direct task exit 0，有真实 `AsmClassesTransform` records，且 `NotSerializableException`、production factory `__instrumentationContext__` 与 `InstrumentationContext_Decorated.__apiVersion__` markers 均为 0。
- 两个 frozen external-file outputs 从 pre-run hidden target refs `0/2` 变为 post-run `2/2`；hidden target definitions `0/2`；old source definitions `2/2`。
- 禁止 full assemble、Release/R8、APK checker、device/ADB/emulator、Soong/Ninja 或 Task 079 broad replay。本任务成功只关闭 production seam + focused/direct visitor proof，不声明 APK 或 runtime 成功。

## 执行记录

### 2026-09-02 Preflight（已获 Chief 接受）

- Base：`HEAD = origin/main = 46a070193028fe5ad3228da4223c39c3de422edf`，worktree clean，无 Gradle/Kotlin/Soong/Ninja/Java 进程。
- 冻结哈希均与 Task 094 一致（FrozenAconfigInputs `e5692213…`、rewriter `c6fbfca0…`、buildSrc build `3d1b8a56…`、rules `ff79a84d…`、allowlist `926f102e…`）；rules 4 行、allowlist 166 行。
- RED DEX baseline（`uv run python` ×1，exit 0）：聚合 757 referenced types / 626 defined classes；两个 old source definitions `2/2`，hidden target refs `0/2`，hidden target defs `0/2`。

### 2026-09-02 实现（本节；未运行任何 Gradle）

按设计 1–5 完成四个允许源码路径的修改：

- `AconfigReferenceRewritePlugin.kt`：`registerForPlugin(pluginId, instrumentation, frozenInputs)` 接收已校验 snapshot；`apply` 在 `withPlugin` 内、`onVariants` 之前恰好一次 `FrozenAconfigInputs.load(...)`；参数 action 写入 managed `MapProperty`/`SetProperty`。
- `AconfigReferenceRewriteFactory.kt`：parameters 仅 `@get:Input MapProperty<String, String> mappings` + `@get:Input SetProperty<String> allowlist`；factory 类体零 property/零 companion/零 cache/零同步；`isAllowlistedClass` 移为 top-level internal pure function；`isInstrumentable` 读 managed allowlist；`createClassVisitor` 将 dot-FQCN mappings 转 internal names 并调用 `referenceOnlyVisitor(...)`。
- `AconfigInstrumentationRegistrationTest.kt`：recording doubles（JDK proxy `Instrumentation` / `MapProperty` / `SetProperty` + 本地 `RecordingParameters`）验证 application-only、exact production factory、`ALL`、`COPY_FRAMES`，以及从 repository 校验 snapshot 写入的 exact 4 mappings / 166 allowlist managed values（含 putAll/addAll 调用记录与最终 value 两个断言面）。
- `ReferenceOnlyClassRewriterTest.kt`：仅将 companion 调用改为 top-level `isAllowlistedClass(...)`，五个 visitor 语义测试原样保留。

静态证据（存 `/tmp/task095-c5-production-immutable-input-seam/implementation/`）：

- `implementation.diff`（363 行，即四个文件的完整 diff）、`git-diff-check.txt`（exit 0，无 whitespace error）。
- `static-invariants.txt`：四冻结输入哈希不变；`git status --porcelain` 仅四个允许文件。
- `structural-checks.txt`：`FrozenAconfigInputs.load(` 在 main 中恰 1 处（plugin apply）；factory 中 `RegularFileProperty`/`InputFile`/`PathSensitivity`/`cachedInputs`/`Transient`/`Volatile`/`synchronized`/`companion object` 计数全 0；`referenceOnlyVisitor` 调用已恢复；plugin 传 snapshot 无 per-variant load。

已知披露：registration test 中三处 JDK-proxy 类型转换（`as (AconfigReferenceRewriteParameters) -> Unit`、`as MapProperty<String, String>`、`as SetProperty<String>`）产生 Kotlin unchecked-cast 编译警告；这是 JDK 动态代理测试 double 的标准代价，不涉及任何 `@Suppress` 或构建检查绕过。

### 2026-09-02 Focused tests（Gradle 1/2，唯一一次 wrapper invocation）

命令：`set -o pipefail; ./gradlew -p buildSrc test --tests 'com.android.systemui.aconfigrewrite.*' --stacktrace --console=plain --max-workers=4 | tee focused-tests.log`。

- `PIPELINE_RC=0`，`BUILD SUCCESSFUL in 8s`（7 actionable：5 executed, 2 up-to-date）；`:test` 为 executed，非 UP-TO-DATE。
- 日志 `focused-tests.log`（23 行）SHA-256 `850f1e698b0fe0565fca5c921cd08c8b4003b082546685be111f949cafeffe55`。
- 发现/完成 9/9 tests（Registration 1 + FrozenAconfigInputs 3 + ReferenceOnlyClassRewriter 5），`failures=0 errors=0 skipped=0`。
- 编译告警恰 3 条，均为实现阶段已披露的 JDK-proxy unchecked cast（RegistrationTest 107/162/188 行），无其他告警。
- 编译产物静态证据（未追加任何 Gradle 调用）：`javap -p` 证明生产 factory `AconfigReferenceRewriteFactory` 声明字段数为 0（仅构造器 + `isInstrumentable` + `createClassVisitor`），无 Companion/cache 字段；top-level `isAllowlistedClass` 位于 `AconfigReferenceRewriteFactoryKt` static；`AconfigReferenceRewritePlugin` 无实例字段；`AconfigInstrumentationRegistration` 仅有 Kotlin object 预期的静态 `INSTANCE` 与 `APPLICATION_PLUGIN_ID` 常量（非 worker state，不在 field-free 不变式范围内）。证据存 `/tmp/task095-c5-production-immutable-input-seam/focused-evidence.txt`、`focused-javap.txt`。双轴 review 指出 `focused-javap.txt` 未单独收录 parameters interface；Chief 随后在不调用 Gradle 的前提下执行 `javap -p -classpath buildSrc/build/classes/kotlin/main com.android.systemui.aconfigrewrite.AconfigReferenceRewriteParameters`，确认它恰好只含 `getMappings(): MapProperty<String, String>` 与 `getAllowlist(): SetProperty<String>` 两个 managed accessor。
- **过程偏差（永久披露）**：XML 聚合首轮误用裸 `python3`（违反仅 `uv run python` 规则）；已立即用合规 `uv run python` 重算（结果相同：tests=9 failures=0 errors=0），偏差不因此抵销，永久记录在案。

### 2026-09-02 Direct transform（Gradle 2/2，串行、 Chief 授权后）

命令：`set -o pipefail; JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' ./gradlew :app:desugarDebugFileDependencies --info --stacktrace --console=plain --max-workers=4 | tee direct-transform.log`。

- `PIPELINE_RC=0`，`BUILD SUCCESSFUL in 21s`（5 actionable：3 executed, 2 up-to-date）；`:app:desugarDebugFileDependencies` 非 UP-TO-DATE（输入 transform 输出因 buildSrc 变更被移除后全量重跑）；两个 output jar mtime 均为本 run 时刻。
- 日志 `direct-transform.log` 522 行 SHA-256 `f6a1fee256de7c61eb1b7abaabdd696073a12c3934e03339617c201df8979610`。
- 真实 `AsmClassesTransform` records 45 个（含两个 gate 输入 `systemui-aconfig-flags.jar`、`tracinglib-platform.jar`）。
- 三个 serialization marker 均为 0：`NotSerializableException` 0、production factory `__instrumentationContext__` 0、`InstrumentationContext_Decorated.__apiVersion__` 0。field-free factory 在真实 worker isolation 下存活。

**Post DEX（`uv run python`，同一 bounded 两 jar 聚合）**：aggregate 758 referenced types（baseline 757，+1 恰为新 hidden target）/ 626 defined classes；

| source | src_ref | src_def | tgt_ref | tgt_def |
|---|---|---|---|---|
| android.app.Flags | F | F | F | F |
| android.os.Flags | T | T | **T** | F |
| android.view.accessibility.Flags | F | F | F | F |
| com.android.window.flags.Flags | T | T | F | F |

GATE：old source definitions **2/2** ✓；hidden target refs **1/2** ✗（要求 2/2）；hidden target defs **0/2** ✓。

**严格分类：INCONCLUSIVE_DIRECT_VISITOR。** direct command 成功（exit 0、BUILD SUCCESSFUL），但要求的 0/2→2/2 hidden-reference 变化未达成（实际 1/2）；按 frozen brief 既非 PASS 亦不以 FAILED 记录，本记录亦不授权 gate 校准或 broader success claim。

诊断（per-jar + 字节码级，均只读、仅 `uv run python`）：

- `android.os.Flags` 半项已达成：`tracinglib-platform.jar` 中 allowlisted `com.android.app.tracing.coroutines.TraceContextElement`（166 行 allowlist 的第 2 行）原 jar 有 4 条真实 `invokestatic android/os/Flags.perfettoSdkTracingV3()Z`；post DEX 该 jar 引用 hidden target、不再引用 source——production `referenceOnlyVisitor` 在真实 transform 中完成首个可用改写。
- `com.android.window.flags.Flags` 半项在 bounded 两 jar 内**不可达**：两 jar 中该类型的全部出现仅为（a）其在 `41_systemui-aconfig-flags.jar` 内的自身 definition/self-reference（`Flags` 类不在 allowlist；且 self-reference 保留是冻结的 rewriter 语义），与（b）allowlisted `com.android.window.flags.CustomFeatureFlags` 中一条**孤儿 constant-pool `Class` 条目**（`#11 = Class com/android/window/flags/Flags`，无任何 instruction 引用；`isOptimizationEnabled()` 仅 `iconst_1`，整个类为 string-based `getValue` 机制）。ASM ClassReader 不 visit 孤儿条目，无物可改写。
- 结论：RED baseline 的 `src_ref=True` 由 definition 自满足，被 gate 设计误读为“存在真实 allowlisted caller 引用”；2/2 期望对本 bounded 输出集不成立。window.flags hidden 引用需要 AAR/project caller（如后续 full Debug build/static gate）才可能出现。

Cleanup（frozen block，恰好一次，exit 立即保存）：`cleanup-1.exit=0`、`cleanup-2.exit=0`、`cleanup-3.exit=1`（kotlin-daemon-embeddable 无匹配，与 Task 094 同形）；无补跑。事后 census（bracket-safe）：全 0。
- **过程偏差（永久披露）**：final census 首次执行时 wrapper shell 自身命令行包含明文标签 `GradleDaemon`/`java` 等，被 bracket-safe pgrep 正则自匹配而打印了全为 2 的假阳性计数；未杀任何进程，改用非匹配标签重算得全 0。偏差永久记录在案。

## 用户批准的 gate 校准（2026-09-02，执行后决策）

原 frozen gate 将两个 source definitions 在 DEX type table 中产生的 `src_ref=True` 误当成两个真实 allowlisted caller 均可改写。执行后的字节码证据证明，第二个 bounded input 中的 `com.android.window.flags.Flags` 只存在 definition/self-reference 与未被 ASM visitor 访问的孤立 constant-pool `Class` 项，因此原 `2/2` 对这两个固定输出不可满足。

用户明确批准 Chief 的建议：本任务 corrected direct gate 改为同时满足以下条件：

- 至少一个真实 allowlisted instruction-level old-name reference 经 production visitor 改写为 hidden target reference；
- hidden target definitions 保持 0；
- old source definitions 保持不变；
- direct transform exit 0、真实 ASM records 存在、known serialization markers 为 0；
- focused semantic/registration tests 全绿。

现有证据满足 corrected gate：`TraceContextElement` 的四条真实 `invokestatic android/os/Flags.perfettoSdkTracingV3()Z` 已改写，hidden definitions `0/2`、old definitions `2/2`，45 个 ASM records，serialization markers 全 0，focused tests 9/9。用户同时批准不重跑 Gradle，直接进入双轴 review；完整四映射仍必须由后续 Debug APK static gate 验证。

## 双轴 review 收口（2026-09-02）

Standards 与 Spec reviewers均以固定 base `46a070193028fe5ad3228da4223c39c3de422edf`审查11路径working-tree diff；两份session均由Chief独立核验为`joycode/GLM-5.3`、`thinking=high`。两轴初审均为PASS且`BLOCKER/HIGH/MEDIUM=0`；LOW仅涉及allowlist行号误写和parameters interface `javap`捕获缺口。Chief将`TraceContextElement`位置更正为166行allowlist的第2行，并以只读`javap -p`确认parameters interface恰好只含`getMappings`/`getAllowlist`两个managed accessor。两轴focused re-review随后均返回PASS、`BLOCKER/HIGH/MEDIUM=0`，全部LOW关闭，仅保留无需行动的TRIVIAL观察。

因此Task 095正式review-PASS，但结论仍严格限于production immutable-input seam与bounded真实visitor proof；本轮没有新增Gradle调用、full Debug/Release build、APK checker、device/ADB/emulator、Soong/Ninja或Task 079 replay。下一独立任务必须fresh构建Debug APK并验证全部四条hidden mappings、hidden target definitions为0及无非法old-name caller。

## 错误数演变与待解决问题

- Task 094：direct dependency transform `PIPELINE_RC=0`，1464 行日志 SHA-256 `53fbffec9cff08f3349762effca125725a8781f8a4e26f92a74a7f73e1c2f4c0`，三个 sentinel 各 1，45 个 ASM records，known serialization markers 0。
- Task 095 direct transform：build 层全过（exit 0、45 ASM records、零 serialization markers、field-free factory 存活、真实改写首次落 DEX）。原 frozen `0/2→2/2` gate 的执行时分类仍为 **INCONCLUSIVE_DIRECT_VISITOR**（old defs 2/2，hidden refs 1/2，hidden defs 0/2）；用户随后根据已证明的 bounded-input 不可达原因，批准 corrected gate，并据此接受 Task 095 为 **PASS**、授权双轴 review。该决定不授权把 bounded proof 冒充四映射 APK/static/runtime 成功。
- Task 095 review-PASS；下一步执行独立fresh Debug build/static gate，随后按序 Release build/static、Debug runtime、Release runtime。
