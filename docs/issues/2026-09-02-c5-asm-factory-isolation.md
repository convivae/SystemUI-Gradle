# C5 Task 083：AGP ASM factory isolation 根因诊断

**日期**：2026-09-02
**状态**：诊断完成（2026-09-02）；direct loop 5 秒内精确重现，deepest cause 为 `java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty`。该日志仍未给出该 `DefaultProperty` 在 runtime-generated factory decorator 中的字段路径，下一步为单命令 extended-serialization-path 诊断（Task 084）。
**前置**：Task 082 已以真实 `:app:assembleDebug` pipeline 稳定触发 `:app:desugarDebugFileDependencies` failure；完整非 stacktrace 日志位于 `/tmp/task082-c5-debug-build/assemble-debug.log`。

## 背景

Task 081 的 9 个 focused tests 与双轴 review 只验证 loader、visitor、filter 和 registration contract。Task 082 证明 AGP 9.3.1 在 `InstrumentationScope.ALL` dependency transform 参数隔离时无法序列化 `AconfigReferenceRewriteFactory`。当前日志没有 `--stacktrace`，因此不能从外层消息直接断言缺少 `Serializable`：`AsmClassVisitorFactory` 接口本身继承 `java.io.Serializable`，且 `javap -v` 已确认当前 `cachedInputs` field 为 `ACC_TRANSIENT`。

本任务只诊断，不修改 build logic，不重跑完整 `assembleDebug`。它要把反馈循环缩短到 direct `:app:desugarDebugFileDependencies`，取得 deepest cause，并用 AGP/Gradle API 与当前 classfile/source 证据裁定下一步最小修复。

## Tight feedback loop

唯一 Gradle command：

```bash
./gradlew :app:desugarDebugFileDependencies \
  --stacktrace --console=plain --max-workers=4 \
  2>&1 | tee /tmp/task083-c5-asm-factory-isolation/desugar-stacktrace.log
```

必须使用 `set -o pipefail` 记录真实 exit。由于 Task 082 已生成前置 outputs，该 direct task 应在数秒级到几十秒内重现 exact `AsmClassesTransform` isolation failure；若出现不同 failure，任务立即停止并报告 feedback loop 不等价。

## Ranked hypotheses

1. **H1 — factory instance 的自有 mutable cache 破坏 Gradle transform isolation**：即使 JVM field 标记为 `transient`，Gradle 9.5 的 managed-value/isolation serializer 仍可能拒绝或遍历 factory runtime state。预测：deepest cause 指向 `FrozenAconfigInputs`、factory field/property或 unsupported bean state；移除 factory instance cache、改为参数驱动的无状态创建会消失。
2. **H2 — custom `InstrumentationParameters` visibility/managed type 不满足 isolation contract**：`AconfigReferenceRewriteParameters` 为 buildSrc internal custom interface，两个 `RegularFileProperty` 在 AGP transform snapshot 中可能无法跨 classloader/managed isolation。预测：deepest cause 指向 generated parameters/decorated type、property或 class accessibility，而不是 cache。
3. **H3 — AGP API dependency/classloader duplication**：`buildSrc` 对 `gradle-api`/AGP API 的 dependency scope 使 factory interface/runtime class identity 在 transform isolation 时不一致。预测：deepest cause 为 classloader/class-not-found/cannot deserialize class，而非 ordinary non-serializable field。
4. **H4 — Kotlin-generated companion/metadata or serialVersion shape**：factory 的 Kotlin-generated class shape触发 serializer limitation。预测：deepest cause直接指向 companion/metadata/constructor or class descriptor；这是最低优先级，因为 AGP 文档允许普通 JVM implementation且 companion为 static。

## 执行结果

Worker `task083-isolation` 在独立 tab `w2:t3A` / pane `w2:p3F` 中使用已独立核实的 `joycode/GLM-5.3`、`thinking=high`，严格完成 AGENTS → CHARTER → brief/issue → CONTRACT startup。clean/no-process preflight 后只运行一次授权的 direct task：

```text
./gradlew :app:desugarDebugFileDependencies --stacktrace --console=plain --max-workers=4
BUILD FAILED in 5s
5 actionable tasks: 1 executed, 4 up-to-date
LOOP_EXIT=1
```

该 loop 精确重现 Task 082 的 `AsmClassesTransform` / `AconfigReferenceRewriteFactory` failure。完整日志为 `/tmp/task083-c5-asm-factory-isolation/desugar-stacktrace.log`（7866 行，SHA-256 `c02a5795667b058ff803a1bd683c92c28ac65ce661d5ff1dfe0628799c1a9dcb`），scratch 摘要为 `/tmp/task083-c5-asm-factory-isolation/SUMMARY.md`。47 个 dependency artifact cause block 均收敛到同一 exception chain：

```text
TaskExecutionException: Execution failed for task ':app:desugarDebugFileDependencies'
└─ VariantTransformConfigurationException: Could not isolate parameters ... AsmClassesTransform
   └─ IsolationException: Could not isolate value ... of type AsmClassesTransform.Parameters
      └─ ValueSnapshottingException: Could not serialize value of type AconfigReferenceRewriteFactory
         └─ java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty
```

第一项已证明不可序列化的对象是 `org.gradle.api.internal.provider.DefaultProperty`。当前 `AconfigReferenceRewriteFactory.class` 仅有 static `Companion` 与 `ACC_TRANSIENT` 的 `cachedInputs`；AGP 9.3.1 source则证明 dependency transform 的 `visitorsList` 直接持有 factory，且 runtime decorator 会向 factory 注入 `parameters: Property<...>` 与 `instrumentationContext.apiVersion: Property<Int>`。现有 stacktrace没有 field path，因此不能诚实断言失败对象究竟属于哪一项 injected property。

H1（自有 cache）被拒绝：cache 是 transient，且 isolation 发生在 visitor 执行前。H2（managed/injected property shape）方向上获得支持，但具体为 custom parameters 还是 instrumentation context 仍未确定。H3（classloader duplication）和 H4（Kotlin companion/metadata）均不受当前 exception chain 支持：没有 classloading failure，companion又是 static。Worker完成后只执行 daemon stop，确认无 Gradle/Kotlin残留且 tracked worktree clean；未运行第二个 task，未修改 build logic、APK、AOSP、SDK或 `libs/**`。

Chief 不接受把 `internal`→`public` 作为当前最小修复：`javap` 已显示 factory JVM class本身为 `public abstract`，该改动无法解释当前 Java serialization object graph。下一步先以 JDK `sun.io.serialization.extendedDebugInfo=true` 对同一 direct task做一次只读重现，要求 `NotSerializableException` 输出真实字段路径；仍无字段路径时再执行独立的 `InstrumentationParameters.None` no-op `ALL` control。任何 production fix继续后置。

## 操作与验收

1. 顺序读取项目规则与 Task 083 brief，输出 CONTRACT；确认 tracked worktree clean、无 Gradle/Kotlin/Soong/Ninja 活动。
2. 只运行上面的 direct Gradle command，一次；不得运行 `assembleDebug`、Release/R8或其他 Gradle task。
3. 保存完整 stacktrace，报告 exception chain 最深 20 层（type + message），明确第一项真正不可序列化/不可隔离对象。
4. 只读检查当前 factory classfile flags、AGP `AsmClassVisitorFactory` API source和相关 Gradle serializer source（若本机 source cache可用）；逐项裁定 H1–H4。
5. 给出一个最小 fix proposal与一个正确 regression gate proposal，但不得编辑 tracked 文件。
6. 终止本次 Gradle/Kotlin daemons；tracked worktree保持 clean。

## 禁止

- 不修改任何 tracked file、AOSP、SDK、`libs/**` 或 build outputs；不 commit/push。
- 不运行完整 Debug build、Release/R8、checker、emulator/ADB、Soong/Ninja。
- 不试改代码、不添加 `Serializable` 猜测、不删除 cache、不运行第二个 Gradle task。
- 不恢复 Task 079，不扩大四规则/166-class rewrite contract。

## 完成条件

- [x] direct feedback loop 精确重现 Task 082 failure，真实 exit 1。
- [x] deepest cause 固定为 `java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty`，未再把外层 wrapper 当根因。
- [x] H1–H4 已逐项裁定；无法从当前日志证明的 decorator field ownership 明确保留为 undetermined。
- [x] 本任务零 tracked 写入，未运行第二个 Gradle task或任何 Release/device/Soong 操作。
- [ ] 取得 `DefaultProperty` 的 Java serialization field path（转交 Task 084）。
- [ ] 根据 field path另立最小 implementation/regression task；本任务不实现。
