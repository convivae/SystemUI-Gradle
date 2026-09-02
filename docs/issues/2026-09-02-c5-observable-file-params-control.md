# C5 Task 090：可观察的 custom file-parameters artifact-transform control

**日期**：2026-09-02
**状态**：已执行，`PASS`（factory sentinel 已证明相关 `AsmClassesTransform` wave 实际调用临时 factory）
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

## 实际结果

唯一授权的 Gradle wrapper 调用按计划执行，pipeline exit `0`。完整日志为 `/tmp/task090-c5-observable-file-params-control/desugar-observable-file-params.log`，共 398 行，SHA-256 `762d53cb40bd3f3d81f79444444daa8aeee7c47efbaf6b9ef59fb1ff8da4352f`。精确 sentinel 在 line 386 出现 1 次：

```text
TASK090_FACTORY_EXECUTED=android.os.CustomFeatureFlags
```

日志另有 45 条 `Caching disabled for AsmClassesTransform:`。虽然 direct target 在 line 297/391 最终报告 `:app:desugarDebugFileDependencies UP-TO-DATE`，sentinel 已直接证明相关 artifact-transform wave 实际调用 factory，因此按预先冻结的判据正式归类为 **`PASS`**，而不是 Task 087 式 `INCONCLUSIVE`。构建摘要为 `BUILD SUCCESSFUL in 8s`、`5 actionable tasks: 2 executed, 3 up-to-date`；`NotSerializableException`、`__instrumentationContext__`、`__apiVersion__` 均为 0。

本次临时证据哈希：plugin `86b1c07369a89de57ee413f500f88b9bfc112092080e258cd1b65a51814f62d3`，temporary factory `7b19fde9a8f61bc5197b0caae0066b3b49e582bcac13a64b32acf78825135d62`，probe `767822847a13ee226bb0595ee19cf0af76a9525b802ea3a9651f548b26c86d87`，保存 patch `9416e1cbe5d7879b514b792e1e7a5f62f6ed9cd7f4e87bb8d637a2b6c2e871b0`。session 审计确认仅有一次 `./gradlew` tool call，未发现 direct `python`/`python3`。

恢复后 production plugin/factory/rules/allowlist SHA-256 分别为 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`、`bd92aeedd70aa677e6ee2e1c6231fa1c7dc3dca26768890950aa54a011c798cb`、`ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`、`926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`；temporary factory absent，worktree clean，scratch evidence 保留，无 Gradle/Kotlin/Soong/Ninja 残留进程。

过程偏差如实保留：worker 首轮 cleanup 使用了三条非 brief 指定的 process patterns。Chief 随即要求并取得三个强制 bracket-pattern cleanup 命令的独立结果；三者均 exit 1，表示纠正检查时已无匹配进程。该偏差不改变控制结论，但后继任务必须直接使用强制命令，不能自行替换。

## 结论范围

Task 090 只证明：在 production `AconfigReferenceRewriteParameters` 类型、两个 file-property 槽位、application-only `InstrumentationScope.ALL`、`COPY_FRAMES` 下，field-free no-op factory 能在可观察的 artifact-transform execution 中通过 isolation；因此已观察的 production failure 不能归因于这两个 file-property 参数形状本身。它不证明 production filter、input loading/cache、reference-only visitor、Debug APK、Release/R8 或 runtime。

后继 Task 091 继续保持 scope、parameter shape 与 no-op bytes 不变，只恢复一次可观察的 `FrozenAconfigInputs.load(...)`，以逐层隔离 production factory implementation。

## 后续决策

`PASS` 分支已选择：后继只隔离 production factory 的 input/filter/cache/visitor 行为，不扩大 mapping、allowlist 或 instrumentation scope。Task 091已将第一层冻结为sentinel-scoped managed file access + `FrozenAconfigInputs.load(...)`；其他历史分支未发生，不授权移除managed file parameters或改用其他production seam。
