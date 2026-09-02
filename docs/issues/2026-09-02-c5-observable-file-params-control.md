# C5 Task 090：可观察的 custom file-parameters artifact-transform control

**日期**：2026-09-02
**状态**：待执行
**前置**：Task 087 的 field-free no-op factory + production `AconfigReferenceRewriteParameters` 命令退出 0，但 `:app:desugarDebugFileDependencies` 为 `UP-TO-DATE`，因此没有证明 `AsmClassesTransform` 或 factory 实际执行，正式结论为 `INCONCLUSIVE`。Task 088 未找到升级是 targeted fix 的第一方证据；Task 089 建议先通过改变 annotated transform input 并留下执行标记，完成最小可观察控制。

## 问题

在保持 production parameter **类型与两个 file-property 槽位**、application-only `InstrumentationScope.ALL`、`COPY_FRAMES` 和 field-free no-op visitor 不变的前提下，能否通过一个语义无害但指纹唯一的临时 `@InputFile` 值，强制相关 artifact transform 失去既有缓存命中，并证明 factory 确实执行或在 isolation 阶段失败？

## 控制设计

1. 临时新增 `NoOpFileParamsFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`，无实例字段，visitor仍为 no-op。
2. `isInstrumentable` 对每个类仍返回 `false`；仅当 AGP 向 factory 提供已知 runtime-JAR sentinel `android.os.CustomFeatureFlags` 时向标准输出打印唯一标记 `TASK090_FACTORY_EXECUTED=android.os.CustomFeatureFlags`。该标记只证明 transform action 调用了 factory，不改变 class bytes。
3. 在 `/tmp/task090-c5-observable-file-params-control/probe-rules.txt` 创建 production 四规则的副本并追加一行仅供本 no-op control 使用的固定 probe 文本。临时 registration仍配置同一个 `AconfigReferenceRewriteParameters` 的 `rulesFile` 与 `allowlistFile`：前者指向 probe 文件，后者保持 production allowlist。由于 factory不读取参数，probe 内容不会进入任何 class 语义；其唯一目的为改变已声明 `@InputFile` 的内容/路径指纹。
4. 只运行一次 direct task，并使用 `--info` 与 JDK extended serialization info：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task090-c5-observable-file-params-control/desugar-observable-file-params.log
   ```
5. 无论结果如何，恢复 plugin byte-for-byte、删除 temporary factory、停止本次 Gradle/Kotlin daemons，并证明 worktree clean。不得运行第二个 Gradle command。

## 判据

- `CUSTOM_PARAMS_FAILURE`：日志出现 Task 084 同类 literal path，且路径经过 `NoOpFileParamsFactory_Decorated.__instrumentationContext__` 到 `InstrumentationContext_Decorated.__apiVersion__`。这证明该次 non-`None` file-parameter no-op transform 在 isolation 时失败；不泛化到所有 non-`None` parameter 类型。
- `PASS`：command exit 0，且日志至少出现一次精确 sentinel `TASK090_FACTORY_EXECUTED=android.os.CustomFeatureFlags`。即使 task最终显示 `UP-TO-DATE`，sentinel也证明相关 artifact transform action实际调用了 factory。
- `INCONCLUSIVE`：command exit 0但 sentinel 为0；不得把 `BUILD SUCCESSFUL`或task级 `UP-TO-DATE`当成parameter通过。
- `OTHER_FAILURE`：任何其他失败；记录最深 cause并停止。

## 边界

临时写入仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpFileParamsFactory.kt`
- `/tmp/task090-c5-observable-file-params-control/**`

禁止修改 production `AconfigReferenceRewriteFactory.kt`、`AconfigReferenceRewriteParameters`、四规则、166-class allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard、SystemUI源码或任何其他tracked path。禁止 full assemble、Release/R8、checker、device、Soong/Ninja、第二个 Gradle command、commit/push。

## 后续决策

- `CUSTOM_PARAMS_FAILURE`：设计不携带 managed file parameters 的最小 production seam，同时保持四规则/166 allowlist可测试且可追踪；先写新 task，不在本控制中实现。
- `PASS`：继续只隔离 production factory 的 filter/cache/visitor行为；不扩大mapping或scope。
- `INCONCLUSIVE`/`OTHER_FAILURE`：只围绕新证据定义下一项控制，不选择production seam。
