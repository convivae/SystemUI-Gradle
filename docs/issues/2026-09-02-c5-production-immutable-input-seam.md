# C5 Task 095：production immutable-input seam 与 visitor proof

**日期**：2026-09-02
**状态**：已设计，待从 clean pushed planning base 串行执行
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

## 错误数演变与待解决问题

- Task 094：direct dependency transform `PIPELINE_RC=0`，1464 行日志 SHA-256 `53fbffec9cff08f3349762effca125725a8781f8a4e26f92a74a7f73e1c2f4c0`，三个 sentinel 各 1，45 个 ASM records，known serialization markers 0。
- Task 095 尚未执行；production source 仍为 Task 093 已知失败 cache shape，新 Debug APK仍未产出。
- Task 095 review-PASS 后才执行独立 Debug build/static gate；随后按序 Release build/static、Debug runtime、Release runtime。
