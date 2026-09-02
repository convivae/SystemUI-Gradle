# C5 Task 084：扩展 Java serialization field-path 诊断

**日期**：2026-09-02
**状态**：待执行
**前置**：Task 083 已用 direct `:app:desugarDebugFileDependencies --stacktrace` 在 5 秒内精确重现 Task 082 failure，deepest cause 为 `java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty`，但普通 stacktrace 未指出该对象在 runtime-generated factory decorator 中的字段路径。

## 背景

Task 083 已排除 `cachedInputs` 作为直接原因：当前 classfile 中该字段为 `ACC_TRANSIENT`，而失败发生在 transform parameter isolation、visitor 执行之前。AGP 9.3.1 source证明 `AsmClassesTransform.Parameters.visitorsList` 持有 factory instance，`AsmClassVisitorFactoryEntry.configure()` 会向 runtime-generated factory decorator 注入 `parameters` 与 `instrumentationContext.apiVersion` 两组 Gradle `Property`。普通 `NotSerializableException` 只显示 `DefaultProperty` 类型，不能区分具体 field ownership。

JDK Java serialization 支持 `sun.io.serialization.extendedDebugInfo=true`，可在 `NotSerializableException` 中附加对象图 field path。本任务用该诊断开关重跑同一 direct task一次；只取证，不改代码。

## 唯一命令

```bash
set -o pipefail
JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
  ./gradlew :app:desugarDebugFileDependencies \
    --stacktrace --console=plain --max-workers=4 \
    2>&1 | tee /tmp/task084-c5-serialization-field-path/desugar-extended-stacktrace.log
```

必须记录真实 exit code。若没有重现同一 `AsmClassesTransform` / `AconfigReferenceRewriteFactory` isolation failure，立即停止；不得运行第二个 Gradle task。若 deepest message 仍无 field path，也如实记录该机制在当前 Gradle daemon路径上未提供更多信息，不得猜测 ownership。

## 验收

- 记录完整 deepest `NotSerializableException` message，包括所有 extended field-path 行；若没有则明确 `FIELD_PATH=UNAVAILABLE`。
- 将 field path 与当前 factory classfile、AGP 9.3.1 `AsmClassVisitorFactoryEntry` / `InstrumentationContext` source逐段对应，区分 direct evidence 与 inference。
- 给出唯一下一步：若 field path已定位，提出最小 buildSrc fix experiment；若未定位，提出 `InstrumentationParameters.None` no-op `ALL` control。均不得在本任务实现。
- 零 tracked写入；无第二个 Gradle task、assemble、Release/R8、checker、device、Soong/Ninja。
- 结束后终止本次 Gradle/Kotlin daemons并确认 worktree clean。
