# C5 Task 087：same custom file parameters no-op `ALL` control

**日期**：2026-09-02
**状态**：待执行
**前置**：Task 086 的 `InstrumentationParameters.None` no-op `InstrumentationScope.ALL` control 已通过 `:app:desugarDebugFileDependencies`。这排除了“AGP 注入的 `InstrumentationContext.__apiVersion__` 对所有 `ALL` factory 都必然不可序列化”，但 Task 086 同时替换了 parameters 类型和 factory 实现，尚不能把原失败唯一归因于两项 custom file parameters。

## 问题

Production factory 与 Task 086 control 的差异有两组：

1. `AconfigReferenceRewriteParameters` 中两个配置后的 `RegularFileProperty`；
2. production factory 的 allowlist 过滤、visitor 创建和 transient cache 实现。

Task 087 保持 Task 086 的 no-op 行为，仅恢复 production 的 parameters 类型和完全相同的两个 file-property 配置，用一个 direct task 判断 custom parameter shape 是否足以重新触发 isolation failure。

## 控制设计

1. 临时新增 `NoOpFileParamsFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`；不新增字段，`isInstrumentable=false`，visitor 原样透传。
2. 临时把 app-only registration 切到该 factory；继续使用 `InstrumentationScope.ALL` 和 `FramesComputationMode.COPY_FRAMES`，并逐字保留 production 的 `rulesFile` / `allowlistFile` 配置 lambda。
3. Chief 检查 exact two-path diff 后，只运行一次 extended-info `:app:desugarDebugFileDependencies`。
4. 保存日志与临时 patch 到 `/tmp/task087-c5-custom-file-params-control/**`，随后 byte-for-byte 恢复，最终 tracked worktree clean。

## 判据

- `CUSTOM_PARAMS_FAILURE`：出现与 Task 084 相同的 `InstrumentationContext_Decorated.__apiVersion__` → `NoOpFileParamsFactory_Decorated.__instrumentationContext__` 路径。结论仅为：相同 custom parameters 的存在/配置足以让 no-op factory 进入失败序列化路径；下一步 production seam 应移除 `InstrumentationParameters` file properties，同时以可测试、可追踪方式冻结四规则和 166-class allowlist。
- `PASS`：direct task 通过。结论仅为：两个 file properties 本身不足以触发失败；下一步隔离 production factory 的 filter/cache/visitor 行为。
- `OTHER_FAILURE`：如实记录并停止，不在本任务尝试第二变体。

## 边界

临时修改仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpFileParamsFactory.kt`
- scratch 仅限 `/tmp/task087-c5-custom-file-params-control/**`

禁止修改 production `AconfigReferenceRewriteFactory.kt`、parameters interface、四规则、166-class allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard、SystemUI 源码或其他 tracked path。禁止 full assemble、Release/R8、checker、device、Soong/Ninja、第二个 Gradle task、commit/push。
