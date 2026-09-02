# C5 Task 085：`InstrumentationParameters.None` no-op `ALL` control

**日期**：2026-09-02
**状态**：已结束（`OTHER_FAILURE`；控制未触达 isolation）
**前置**：Task 084 证明首个不可序列化对象为 AGP runtime-generated `InstrumentationContext_Decorated.__apiVersion__`，经 `AconfigReferenceRewriteFactory_Decorated.__instrumentationContext__` 可达。尚未证明该失败对所有 `InstrumentationScope.ALL` factory都成立，也未证明 custom parameters是否存在后续独立问题。

## 问题

当前 production factory同时具有 AGP无条件注入的 `instrumentationContext.apiVersion` 和项目自定义 `AconfigReferenceRewriteParameters`。Task 084 的 extended path只证明前者先失败。若直接修改 production实现，仍会把 AGP/Gradle通用 isolation incompatibility与项目参数形状混在一起。

## 最小控制实验

在一次受控临时 diff中：

1. 新增一个不读取任何输入、`isInstrumentable=false`、visitor原样透传的 `AsmClassVisitorFactory<InstrumentationParameters.None>`。
2. 仅把 `AconfigInstrumentationRegistration` 的 app-only `InstrumentationScope.ALL` registration临时切到该 no-op factory；保留 `COPY_FRAMES`，不改 production rewrite factory、四规则或166-class allowlist。
3. Chief在运行前检查临时 diff。
4. 只运行一次带 extended serialization info的 `:app:desugarDebugFileDependencies` direct task。
5. 保存日志与临时 patch到 `/tmp/task085-c5-none-all-control/**`，随后精确恢复临时改动，最终 tracked worktree必须 clean。

## 判据

- 若仍以同一 `InstrumentationContext_Decorated.__apiVersion__` → factory `__instrumentationContext__`路径失败：control证明 blocker不依赖 custom parameters，归类为当前 AGP 9.3.1 + Gradle 9.5.0 dependency-scope `ALL` factory isolation incompatibility；下一步查官方兼容性/上游修复或选择不依赖该 raw-factory serialization路径的受支持 pre-D8/R8 seam。
- 若 direct task通过：说明 custom parameter shape参与失败；下一步再单独最小化 parameters。
- 若出现第三种 failure：如实记录，停止；不得在同一任务试第二个变体。

## 边界

允许临时修改且必须恢复的文件仅为：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpAllScopeFactory.kt`（临时新文件）

禁止修改 production `AconfigReferenceRewriteFactory.kt`、规则/allowlist、app wiring、源码、`libs/**`、AOSP、SDK、ProGuard或任何文档。禁止 full Debug、Release/R8、checker、device、Soong/Ninja、第二个 Gradle task、commit/push。Python若确有需要只能 `uv run`，但本实验不需要 Python。

## 实际结果

唯一授权 command 运行一次，`LOOP_EXIT=1`，5 秒后在 `:buildSrc:compileKotlin` 失败；未进入 `:app:desugarDebugFileDependencies`：

```text
e: file:///home/conv/myspace/SystemUI-Gradle/buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt:23:13 No value passed for parameter 'instrumentationParamsConfig'.
BUILD FAILED in 5s
3 actionable tasks: 1 executed, 2 up-to-date
```

`CONTROL_RESULT=OTHER_FAILURE`。日志中 `NotSerializableException=0`、`__apiVersion__=0`、`:app:desugarDebugFileDependencies=0`，因此本任务没有回答 custom parameters是否相关。原因是临时 registration把 custom配置 lambda整体删除，但 AGP 9.3.1 `transformClassesWith` 即使使用 `InstrumentationParameters.None` 也要求显式传入空 `instrumentationParamsConfig` lambda。

完整日志为 `/tmp/task085-c5-none-all-control/desugar-none-all.log`：220 行，SHA-256 `12b365f83d0015840b3869a46c33c1b4195125cca199844768d552c9661730b0`。临时 plugin已恢复至 SHA-256 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`，临时 factory已删除，最终 worktree clean且无 Gradle/Kotlin/Soong/Ninja残留进程。按单任务边界没有运行第二个 control；corrected空-lambda实验转交 Task 086。
