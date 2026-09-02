# C5 Task 091：可观察的 frozen-input load control

**日期**：2026-09-02
**状态**：已执行，`PASS`（managed property access 与一次 production `FrozenAconfigInputs.load(...)` 在可观察 factory execution 中完成；temporary diff 已完整恢复）
**前置**：Task 090 已以一次真实 factory sentinel 将 production `AconfigReferenceRewriteParameters`（两个 file-property 槽位）+ field-free no-op + application-only `InstrumentationScope.ALL` + `COPY_FRAMES` 控制归类为 `PASS`。因此已观察的 production isolation failure 不能归因于该 parameter shape 本身；下一变量必须限制在 production factory implementation 内部。

## 问题

在保持 Task 090 的 parameter type、scope、frames mode、field-free/no-cache 结构和 class-byte no-op 不变时，临时 factory 是否能对已知 runtime-JAR sentinel `android.os.CustomFeatureFlags` **实际读取两个 managed file properties并成功执行一次 `FrozenAconfigInputs.load(...)`**，随后仍返回 `false`？

该控制只恢复 production input access/validation 这一层，不恢复 production allowlist filter 的正命中、不调用 `createClassVisitor`、不引入 `cachedInputs`，也不构造 `referenceOnlyVisitor`。

## 排序假设与预测

1. **H1：production failure 在 file-property getter / `FrozenAconfigInputs.load(...)` 层恢复。** 若 factory 已进入但 load 未完成，日志会有 `TASK091_LOAD_ENTERED` 而没有 `TASK091_INPUTS_LOADED`，并出现对应最深 cause。若 literal serialization failure 在 `LOAD_ENTERED=0` 时发生，只能证明这个 implementation/class-shape control 在 isolation 前失败，不能声称 load body 已执行或是直接原因。
2. **H2：input access/load 层安全，trigger 在后续 filter/cache/visitor。** 唯一命令 exit 0，且 `TASK091_INPUTS_LOADED=android.os.CustomFeatureFlags;mappings=4;allowlist=166` 至少出现一次。
3. **H3：artifact transform 未实际执行或出现不同失败。** Exit 0但 loaded sentinel为0则为 `INCONCLUSIVE`；其他失败为 `OTHER_FAILURE`，均停止而不试第二变体。

## 控制设计

1. 在 `/tmp/task091-c5-frozen-input-load-control/` 创建 production四规则文件的**逐字节副本**，文件名固定为 `task091-frozen-rules.txt`。副本必须保持 production SHA-256 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`，不得追加probe文本；唯一作用是以新路径改变已声明 `@InputFile` 值，同时让 production SHA/count校验成功。Allowlist继续指向production文件。
2. 临时新增 `FrozenInputLoadControlFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`，不得有实例字段或cache。对非sentinel类立即返回 `false`；对 `android.os.CustomFeatureFlags` 依次打印 `TASK091_LOAD_ENTERED=android.os.CustomFeatureFlags`、读取两个 parameter files、调用 `FrozenAconfigInputs.load(...)`，验证 mappings=4与allowlist=166，再打印精确 loaded sentinel并返回 `false`。
3. `createClassVisitor` 只返回 `nextClassVisitor`；因为 `isInstrumentable` 始终返回 `false`，正常情况下不应被调用。不得调用 production filter或`referenceOnlyVisitor`。
4. 临时 registration只切换factory并把`rulesFile`指向scratch byte-exact copy；保留production allowlist、application-only gate、`InstrumentationScope.ALL`、`COPY_FRAMES`及parameter interface。
5. Chief检查exact two-path diff、scratch hashes与保存patch后，只运行一次：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task091-c5-frozen-input-load-control/desugar-frozen-input-load.log
   ```
6. 无论结果如何，恢复plugin byte-for-byte、删除temporary factory，并直接执行三个强制cleanup命令：
   ```bash
   pkill -9 -f 'Gradle[D]aemon'
   pkill -9 -f 'KotlinCompile[D]aemon'
   pkill -9 -f 'kotlin-daemon-[e]mbeddable'
   ```
   证明worktree clean且无Gradle/Kotlin/Soong/Ninja残留进程。不得自行替换或增加cleanup pattern。

## 判据

- `PASS`：command exit 0，精确 `TASK091_INPUTS_LOADED=android.os.CustomFeatureFlags;mappings=4;allowlist=166` count ≥1。Task-level `UP-TO-DATE`不否定该sentinel；sentinel本身证明factory中的production load path已执行完成。
- `SAME_ISOLATION_FAILURE`：出现Task 084同类 `InstrumentationContext_Decorated.__apiVersion__` → `FrozenInputLoadControlFactory_Decorated.__instrumentationContext__` literal path。必须同时报告entered/loaded counts；若entered=0，不得归因于load body。
- `INPUT_LOAD_FAILURE`：entered≥1、loaded=0，且最深cause来自parameter取值或`FrozenAconfigInputs.load(...)`。
- `INCONCLUSIVE`：exit 0但loaded sentinel为0。
- `OTHER_FAILURE`：任何其他失败。所有非PASS分支均停止，由Chief另立下一任务。

## 边界与结论范围

临时tracked写入仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/FrozenInputLoadControlFactory.kt`

scratch仅限 `/tmp/task091-c5-frozen-input-load-control/**`。禁止修改production `AconfigReferenceRewriteFactory.kt`、`AconfigReferenceRewriteParameters`、`FrozenAconfigInputs.kt`、`ReferenceOnlyClassRewriter.kt`、四规则、166-class allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard、SystemUI源码或其他tracked path。禁止第二个Gradle command、full assemble、Release/R8、checker、device、Soong/Ninja、commit/push、direct `python`/`python3`。

即使 `PASS`，也只证明一次可观察的 managed file access + frozen input validation；不证明production cache/filter/visitor、APK、Release或runtime。PASS后的下一独立任务才允许恢复一个后续implementation layer。

## 实际结果

唯一授权的 Gradle wrapper invocation 按冻结命令执行，pipeline exit `0`。完整日志 `/tmp/task091-c5-frozen-input-load-control/desugar-frozen-input-load.log` 共 1463 行，SHA-256 `de243bd45b8b56995562cf17ba6a9ddb96451d91303d3202370b8e7fadbb8eb5`。精确 sentinels 各出现一次：

```text
TASK091_LOAD_ENTERED=android.os.CustomFeatureFlags
TASK091_INPUTS_LOADED=android.os.CustomFeatureFlags;mappings=4;allowlist=166
```

entered 位于 line 1450，loaded 位于 line 1453。日志另有 45 条 `Caching disabled for AsmClassesTransform:`，direct target 最终报告 `:app:desugarDebugFileDependencies UP-TO-DATE`，但 loaded sentinel 已直接证明 relevant factory invocation 完成了 production load path，因此按预先冻结矩阵正式归类 **`PASS`**。构建摘要为 `BUILD SUCCESSFUL in 17s`、`5 actionable tasks: 2 executed, 3 up-to-date`；未出现 `NotSerializableException`、`__instrumentationContext__` 或 `__apiVersion__` failure path。

Scratch rules 与 production rules 逐字节相等，SHA-256 均为 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`。Pre-run temporary evidence hashes为：plugin `826412bba0c0cfe2779137bc5e464885bfb45f04ea10804cb67c2c89ea376149`，factory `ba85019411adfacb0bccf0a51ae92160cc6b8ae7139333387b1bd975e0372e2a`，saved patch `316b0b1eb46bc01a22aca916730b4fb76f38a7a461498621d9e11505711e8c48`。Session审计确认仅有一次`./gradlew` tool call，未发现direct `python`/`python3`。

恢复后worktree clean，temporary factory absent，production plugin/factory/input-loader/reference-rewriter/rules/allowlist SHA-256分别恢复为 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`、`bd92aeedd70aa677e6ee2e1c6231fa1c7dc3dca26768890950aa54a011c798cb`、`e56922137fc0573e6310063c376f84d480eb6b649aab2c42cff1e10261526f27`、`c6fbfca057d73f6d8e01c117c7886d07acb34987b301aa42536d0298fa00e7ac`、`ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`、`926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`。最终read-only process census为空。

过程偏差必须永久保留：`pkill -9 -f 'Gradle[D]aemon'` 被执行两次，而不是合同要求的一次；另外两个强制pattern各执行一次。由于首轮命令输出丢失，三个mandated cleanup exit codes均未保存。重复cleanup与exit-code缺失不改变entered/loaded/build证据和`PASS`分类，但本任务不得声称cleanup procedure完全合规。Task 092已把三条命令冻结在单个shell block中，并要求每条执行后立即把exit code写入scratch；即使输出丢失也禁止重跑。

## 结论范围与下一步

Task 091只证明：在Task 090已经证明可执行的custom parameter/scope/no-op结构下，managed property getters与一次production `FrozenAconfigInputs.load(...)`不是已观察failure的充分trigger。它不证明positive admission、transient cache、reference-only visitor、APK、R8或runtime。

下一独立Task 092只把allowlisted sentinel从`false`改为production helper的positive admission，并让AGP进入class-byte no-op visitor；仍无cache且不构造`referenceOnlyVisitor(...)`。若positive admission激活Task 084 literal isolation path，只能把最小已知激活边界固定在“至少一个类被接纳并进入下游transform”，不能把membership运算本身误称为serialization root cause。
