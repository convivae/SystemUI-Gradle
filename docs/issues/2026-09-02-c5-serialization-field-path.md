# C5 Task 084：扩展 Java serialization field-path 诊断

**日期**：2026-09-02
**状态**：PASS（read-only diagnosis；字段路径已取得，下一步 Task 085 no-op `ALL` control）
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

## 执行结果

唯一命令于 `main@dfde271802fa23836701375b70cc49fde83a038e` 运行一次，`LOOP_EXIT=1`，`BUILD FAILED in 5s`，`5 actionable tasks: 1 executed, 4 up-to-date`。日志 `/tmp/task084-c5-serialization-field-path/desugar-extended-stacktrace.log` 共 8051 行，SHA-256 为 `dc9cac2bbc2a6745d800f8eb80b762cecb1d0860010fc3fca37b8334fd209a88`；46 个 deepest-cause chain均为同一异常和同一扩展路径：

```text
java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty
- field (class "com.android.build.api.instrumentation.InstrumentationContext_Decorated", name: "__apiVersion__", type: "interface org.gradle.api.provider.Property")
- object (class "com.android.build.api.instrumentation.InstrumentationContext_Decorated", property 'instrumentationContext')
- field (class "com.android.systemui.aconfigrewrite.AconfigReferenceRewriteFactory_Decorated", name: "__instrumentationContext__", type: "interface com.android.build.api.instrumentation.InstrumentationContext")
- root object (class "com.android.systemui.aconfigrewrite.AconfigReferenceRewriteFactory_Decorated", com.android.systemui.aconfigrewrite.AconfigReferenceRewriteFactory_Decorated@7c90afd3)
```

Chief 独立核验了行数、SHA、46 个 `DefaultProperty`/`__apiVersion__`/`__instrumentationContext__`路径实例、outer `:app:desugarDebugFileDependencies` failure、日志尾部构建结果与 AGP 9.3.1 source。`AsmClassVisitorFactoryEntry.configure()` 无条件执行 `visitorFactory.instrumentationContext.apiVersion.setDisallowChanges(apiVersion)`，而 `AsmClassesTransform.Parameters.visitorsList` ��接持有 dependency-scope factory instances。因此第一项被证明不可序列化的对象属于 AGP runtime-generated `InstrumentationContext_Decorated.__apiVersion__`，经 factory decorator 的 `__instrumentationContext__` 可达；它不是自定义 `AconfigReferenceRewriteParameters`，也不是已为 transient 的 `cachedInputs`。

这里仍保留一条推断边界：该路径证明 `__apiVersion__` 是**第一处**失败；不能由此证明后续 `__parameters__` 一定可序列化，也不能在尚未运行 control 前宣称所有 `ALL` factory必然失败。最小下一步是单独 Task 085：临时注册 `InstrumentationParameters.None` 的 no-op `InstrumentationScope.ALL` factory，运行同一 direct task一次并恢复临时 diff。若仍在同一 `__apiVersion__` 路径失败，则把 blocker裁定为通用 AGP 9.3.1/Gradle 9.5.0 `ALL` factory isolation incompatibility；若通过，才继续调查 custom parameters shape。

Worker未修改 tracked files，未运行第二个 build task、assemble、Release/R8、checker、device或Soong；本次 daemon已停止，最终 worktree clean。完整摘要见 `/tmp/task084-c5-serialization-field-path/SUMMARY.md`。
