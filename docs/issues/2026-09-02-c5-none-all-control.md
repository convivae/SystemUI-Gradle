# C5 Task 085：`InstrumentationParameters.None` no-op `ALL` control

**日期**：2026-09-02
**状态**：待执行
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
