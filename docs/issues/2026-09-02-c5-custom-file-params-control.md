# C5 Task 087：same custom file parameters no-op `ALL` control

**日期**：2026-09-02
**状态**：已执行，`INCONCLUSIVE`（target `UP-TO-DATE`，没有artifact-transform实际执行证据）
**前置**：Task 086 的 `InstrumentationParameters.None` no-op `InstrumentationScope.ALL` control 已通过 `:app:desugarDebugFileDependencies`。这排除了“AGP 注入的 `InstrumentationContext.__apiVersion__` 对所有 `ALL` factory 都必然不可序列化”，但 Task 086 同时替换了 parameters 类型和 factory 实现，尚不能把原失败唯一归因于两项 custom file parameters。

## 问题

Production factory 与 Task 086 control 的差异有两组：

1. `AconfigReferenceRewriteParameters` 中两个配置后的 `RegularFileProperty`；
2. production factory 的 allowlist 过滤、visitor 创建和 transient cache 实现。

Task 087 保持 Task 086 的 no-op 行为，仅恢复 production 的 parameters 类型和完全相同的两个 file-property 配置，用一个 direct task 判断 custom parameter shape 是否足以重新触发 isolation failure。

## 执行结果

唯一授权命令退出 0，日志为 `/tmp/task087-c5-custom-file-params-control/desugar-custom-file-params.log`（98 行，SHA-256 `81a615421db72c4b5e82150f195827ecdff3338b6ad16788ff827779a13d4914`），但 line 94 为 `> Task :app:desugarDebugFileDependencies UP-TO-DATE`。日志没有证明 `AsmClassesTransform` 或 `NoOpFileParamsFactory` 实际执行，因此结果不能归类为 `PASS`，正式裁定为 **`INCONCLUSIVE`**。Production plugin已byte-for-byte恢复（SHA-256 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`），temporary factory已删除，worktree clean，无残留Gradle/Kotlin/Soong/Ninja进程。

Task 089第一方研究进一步确认：`--rerun-tasks`与`--no-build-cache`均没有被已查第一方资料证明可单独强制artifact transform重执行。后继Task 090改用内容/路径唯一的annotated scratch file input，并以factory sentinel + `--info`日志作为执行证据。

## 原控制设计

1. 临时新增 `NoOpFileParamsFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`；不新增字段，`isInstrumentable=false`，visitor 原样透传。
2. 临时把 app-only registration 切到该 factory；继续使用 `InstrumentationScope.ALL` 和 `FramesComputationMode.COPY_FRAMES`，并逐字保留 production 的 `rulesFile` / `allowlistFile` 配置 lambda。
3. Chief 检查 exact two-path diff 后，只运行一次 extended-info `:app:desugarDebugFileDependencies`。
4. 保存日志与临时 patch 到 `/tmp/task087-c5-custom-file-params-control/**`，随后 byte-for-byte 恢复，最终 tracked worktree clean。

## 判据

- `CUSTOM_PARAMS_FAILURE`：出现与 Task 084 相同的 `InstrumentationContext_Decorated.__apiVersion__` → `NoOpFileParamsFactory_Decorated.__instrumentationContext__` 路径。结论仅为：相同 custom parameters 的存在/配置足以让 no-op factory 进入失败序列化路径；下一步 production seam 应移除 `InstrumentationParameters` file properties，同时以可测试、可追踪方式冻结四规则和 166-class allowlist。
- `PASS`：direct task通过且有独立证据证明artifact transform/factory实际执行。原Task 087日志没有该证据，因此不得使用此分类。
- `OTHER_FAILURE`：如实记录并停止，不在本任务尝试第二变体。

## 边界

临时修改仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpFileParamsFactory.kt`
- scratch 仅限 `/tmp/task087-c5-custom-file-params-control/**`

禁止修改 production `AconfigReferenceRewriteFactory.kt`、parameters interface、四规则、166-class allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard、SystemUI 源码或其他 tracked path。禁止 full assemble、Release/R8、checker、device、Soong/Ninja、第二个 Gradle task、commit/push。
