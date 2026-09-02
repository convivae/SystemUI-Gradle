# C5 Task 086：corrected `InstrumentationParameters.None` no-op `ALL` control

**日期**：2026-09-02
**状态**：已完成（`PASS`；corrected no-op `ALL` control通过）
**前置**：Task 084已证明首个不可序列化对象为 `InstrumentationContext_Decorated.__apiVersion__`。Task 085本应隔离 custom parameters，但临时 registration省略了 AGP 9.3.1必需的 `instrumentationParamsConfig`，唯一 command在 buildSrc编译阶段结束为 `OTHER_FAILURE`，未触达 isolation。

## 问题

AGP 9.3.1 `Instrumentation.transformClassesWith` 即使 factory参数类型为 `InstrumentationParameters.None`，也要求第三个 configuration lambda。Task 086只纠正这一处实验搭建错误：使用显式空 lambda `{ }`，其余 control设计、执行次数与禁止项全部不变。

## 控制设计

1. 临时新增 `internal abstract class NoOpAllScopeFactory : AsmClassVisitorFactory<InstrumentationParameters.None>`，使用AGP 9.3.1 `ClassData` / `ClassContext`签名，`isInstrumentable=false`，visitor原样透传。
2. 临时把 app-only registration切到该 factory，保持 `InstrumentationScope.ALL`与`FramesComputationMode.COPY_FRAMES`，并显式传入空 configuration lambda `{ }`。
3. Chief检查exact two-path diff后，只运行一次 extended-info `:app:desugarDebugFileDependencies`。
4. 保存日志与临时patch到 `/tmp/task086-c5-none-all-control-corrected/**`，随后精确恢复，最终tracked worktree clean。

## 判据

- `SAME_API_VERSION_FAILURE`：同一 `InstrumentationContext_Decorated.__apiVersion__` → `NoOpAllScopeFactory_Decorated.__instrumentationContext__`路径失败，证明首个 blocker独立于 custom parameters。
- `PASS`：direct task通过，证明AGP注入的`apiVersion`对所有`InstrumentationParameters.None` no-op `ALL` factory并非必然失败；由于Task 086同时替换了parameters类型和factory实现，下一步仍需以相同custom file parameters + no-op factory做单变量控制。
- `OTHER_FAILURE`：如实记录并停止，不在本任务试第三个变体。

## 边界

临时修改仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpAllScopeFactory.kt`
- scratch仅限 `/tmp/task086-c5-none-all-control-corrected/**`

禁止修改 production factory、四规则、166-class allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard、SystemUI源码或任何其他tracked path。禁止full assemble、Release/R8、checker、device、Soong/Ninja、第二个Gradle task、commit/push。

## 实际结果

Replacement worker严格运行唯一授权command一次，`LOOP_EXIT=0`：

```text
> Task :app:desugarDebugFileDependencies

BUILD SUCCESSFUL in 21s
5 actionable tasks: 3 executed, 2 up-to-date
```

`CONTROL_RESULT=PASS`。完整日志 `/tmp/task086-c5-none-all-control-corrected/desugar-none-all.log` 为98行，SHA-256 `938d2248910800094776e87f9fd661b128e4d3eeafe0d003fd4b6d4e9cb0980b`；其中 `NotSerializableException=0`、`__apiVersion__=0`、`BUILD SUCCESSFUL=1`。

Chief独立确认plugin已byte-for-byte恢复到SHA-256 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`，临时factory已删除，production factory/rules/allowlist哈希未变，tracked/untracked worktree clean且无Gradle/Kotlin/Soong/Ninja残留进程。没有运行第二个Gradle task、full build、Release/R8、checker或device操作。

该结果排除“AGP注入的`InstrumentationContext.__apiVersion__`使所有`InstrumentationParameters.None` no-op `ALL` factory必然失败”，但Task 086同时改变了parameter类型和factory实现，不能单凭此结果把Task 084失败唯一归因于custom file properties。Task 087将保留相同no-op行为，仅恢复`AconfigReferenceRewriteParameters`及两个production file-property配置。
