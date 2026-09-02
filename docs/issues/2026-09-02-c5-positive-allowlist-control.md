# C5 Task 092：positive allowlist admission control

**日期**：2026-09-02
**状态**：已执行，`PASS`（positive allowlist admission与class-byte no-op visitor均可观察完成；temporary diff已完整恢复）
**前置**：Task 091 已取得可观察 `PASS`。在 production `AconfigReferenceRewriteParameters`、两个 managed file slots、application-only `InstrumentationScope.ALL`、`COPY_FRAMES`、field-free/no-cache 且所有类均被拒绝的控制中，`android.os.CustomFeatureFlags` 已完成一次 production `FrozenAconfigInputs.load(...)`；entered/loaded sentinel 各 1，唯一 command exit 0。因此 managed property access 与 frozen-input validation 不是已观察 isolation failure 的充分触发条件。

## 问题

在完全保留 Task 091 已证明安全的参数读取与 frozen-input load 层时，若只把已知且确实位于 166-class allowlist 的 `android.os.CustomFeatureFlags` 从 negative admission 改为使用 production `AconfigReferenceRewriteFactory.isAllowlistedClass(...)` 的 **positive admission**，AGP 能否继续调用一个 class-byte no-op 的 `createClassVisitor(...)`，还是会在 positive admission 触发下游 transform/factory isolation 时重现 Task 084 literal serialization path？

该控制不恢复 `cachedInputs`，不构造 `referenceOnlyVisitor(...)`，不改写任何 class bytes。Positive admission 后 AGP 调用 no-op `createClassVisitor(...)` 是本 rung 的必要可观察结果，不属于 production visitor construction。

## 排序假设与预测

1. **H1：positive admission 激活下游 factory isolation 并重现既有 failure。** 日志先出现 filter entered/accepted，随后在 no-op visitor sentinel 前出现 Task 084 同类 `InstrumentationContext_Decorated.__apiVersion__` → temporary factory `__instrumentationContext__` path。这只证明“至少一个类被接纳”是激活该下游失败路径的最小已知条件，不得声称 set-membership 运算本身不可序列化。
2. **H2：positive filter/admission 层安全。** 唯一 command exit 0，且 accepted 与 no-op visitor sentinel 均至少出现一次；trigger继续位于后续 transient cache或production `referenceOnlyVisitor(...)` construction。
3. **H3：filter/load自身出现不同失败或transform不可观察。** Entered后未accepted且最深cause位于load/filter为`FILTER_FAILURE`；exit 0但缺accepted或visitor sentinel为`INCONCLUSIVE`；其他失败为`OTHER_FAILURE`。

## 控制设计

1. 在 `/tmp/task092-c5-positive-allowlist-control/` 创建 production四规则文件的逐字节副本 `task092-frozen-rules.txt`。必须与production文件 `cmp`相等且SHA-256仍为 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`；allowlist继续指向production 166-class文件（SHA-256 `926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`）。
2. 临时新增 field-free/no-cache `PositiveAllowlistControlFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`：
   - 非 `android.os.CustomFeatureFlags` 立即返回 `false`，不读取参数；
   - sentinel类先打印 `TASK092_FILTER_ENTERED=android.os.CustomFeatureFlags`；
   - 对该 invocation 调用一次 `FrozenAconfigInputs.load(...)`，要求 mappings=4、allowlist=166；
   - 调用 production `AconfigReferenceRewriteFactory.isAllowlistedClass(classData.className, inputs.allowlist)`，要求结果为true；
   - 打印 `TASK092_FILTER_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166`，然后返回true；
   - `createClassVisitor(...)` 只读取 `classContext.currentClassData.className` 以确认仍为sentinel，打印 `TASK092_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags`，原样返回 `nextClassVisitor`；不得读取参数、调用`referenceOnlyVisitor(...)`或改变class bytes。
3. 临时 registration仅切换factory并把`rulesFile`指向scratch byte-exact copy；保留production allowlist、application-only gate、`InstrumentationScope.ALL`、`COPY_FRAMES`与parameter interface。
4. Chief检查exact two-path tracked diff、scratch byte equality/hashes与保存patch后，只运行一次：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task092-c5-positive-allowlist-control/desugar-positive-allowlist.log
   ```
5. 无论结果如何，恢复plugin byte-for-byte、删除temporary factory。三个cleanup命令必须在一个预先冻结的shell block中各执行一次，立即保存各自exit code；即使输出丢失也禁止重跑：
   ```bash
   set +e
   pkill -9 -f 'Gradle[D]aemon'; gradle_daemon_rc=$?
   printf '%s\n' "$gradle_daemon_rc" > /tmp/task092-c5-positive-allowlist-control/cleanup-gradle-daemon.exit
   pkill -9 -f 'KotlinCompile[D]aemon'; kotlin_compile_daemon_rc=$?
   printf '%s\n' "$kotlin_compile_daemon_rc" > /tmp/task092-c5-positive-allowlist-control/cleanup-kotlin-compile-daemon.exit
   pkill -9 -f 'kotlin-daemon-[e]mbeddable'; kotlin_embeddable_daemon_rc=$?
   printf '%s\n' "$kotlin_embeddable_daemon_rc" > /tmp/task092-c5-positive-allowlist-control/cleanup-kotlin-embeddable-daemon.exit
   printf 'GradleDaemon=%s\nKotlinCompileDaemon=%s\nKotlinDaemonEmbeddable=%s\n' \
     "$gradle_daemon_rc" "$kotlin_compile_daemon_rc" "$kotlin_embeddable_daemon_rc"
   ```
   此后只允许read-only `pgrep`/`ps` process census，不得再运行任何`pkill`。

## 判据

- `PASS`：command exit 0，精确 accepted sentinel count ≥1，且精确 no-op visitor sentinel count ≥1。Task-level `UP-TO-DATE`不否定直接factory证据。
- `ADMISSION_ACTIVATED_ISOLATION_FAILURE`：accepted≥1、no-op visitor=0，并出现Task 084同类 `InstrumentationContext_Decorated.__apiVersion__` → `PositiveAllowlistControlFactory_Decorated.__instrumentationContext__` literal path。结论仅为positive admission激活下游isolation failure。
- `FILTER_FAILURE`：entered≥1、accepted=0，且最深cause位于managed input load、size checks或production allowlist helper。
- `INCONCLUSIVE`：exit 0但accepted=0或no-op visitor=0。
- `OTHER_FAILURE`：任何其他失败。所有非PASS分支均停止，由Chief另立下一任务。

## 边界与结论范围

临时tracked写入仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/PositiveAllowlistControlFactory.kt`

scratch仅限 `/tmp/task092-c5-positive-allowlist-control/**`。禁止修改production `AconfigReferenceRewriteFactory.kt`、`AconfigReferenceRewriteParameters`、`FrozenAconfigInputs.kt`、`ReferenceOnlyClassRewriter.kt`、四规则、166-class allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard、SystemUI源码或其他tracked path。禁止第二个Gradle command、full assemble、Release/R8、checker、device、Soong/Ninja、commit/push、direct `python`/`python3`。

即使 `PASS`，也只证明一次positive allowlist admission能到达class-byte no-op visitor；不证明production transient cache、reference-only visitor、APK、Release或runtime。PASS后的下一独立任务才允许恢复 transient cache；若出现`ADMISSION_ACTIVATED_ISOLATION_FAILURE`，下一任务必须围绕该最小激活边界设计production修复，不得继续叠加cache或visitor。

## 实际结果

唯一授权的Gradle wrapper invocation按冻结命令准确执行一次，pipeline exit `0`。完整日志 `/tmp/task092-c5-positive-allowlist-control/desugar-positive-allowlist.log` 共1467行，SHA-256 `8379c3573a201891a7a13d48784dccd0862cc958076cbb729442c6b7c968d4a5`；构建摘要为 `BUILD SUCCESSFUL in 17s`、`5 actionable tasks: 2 executed, 3 up-to-date`。精确sentinels均出现一次：

```text
TASK092_FILTER_ENTERED=android.os.CustomFeatureFlags
TASK092_FILTER_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166
TASK092_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags
```

日志有45条 `Caching disabled for AsmClassesTransform:`，且 `NotSerializableException`、`__instrumentationContext__`、`__apiVersion__` counts均为0。Target-level `UP-TO-DATE`不否定accepted/visitor direct evidence；按预先冻结矩阵正式分类 **`PASS`**。

Scratch rules与production rules逐字节相等，SHA-256均为 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`；production allowlist中`android.os.CustomFeatureFlags`精确出现一次。Temporary evidence hashes为：saved patch `c164e30df62a56944cf97276c039e7e2a8217bf6a20872142fbba75957a195ca`、factory copy `0752a3b7b7e2a689c10162b27e074da435dedf0cb3ad05716c7e147d13cee1ac`、temporary plugin `9fc3497068c258c16a81368e393ec74e42d7a6d8f9b28bfbd36e27c09654f3a3`。Session审计确认worker为`joycode/GLM-5.3`、`thinking=high`，且仅执行一次Gradle wrapper command。

恢复后worktree clean，`PositiveAllowlistControlFactory.kt`不存在，production plugin/factory/input-loader/reference-rewriter/rules/allowlist SHA-256分别为 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`、`bd92aeedd70aa677e6ee2e1c6231fa1c7dc3dca26768890950aa54a011c798cb`、`e56922137fc0573e6310063c376f84d480eb6b649aab2c42cff1e10261526f27`、`c6fbfca057d73f6d8e01c117c7886d07acb34987b301aa42536d0298fa00e7ac`、`ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`、`926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`。最终read-only process census为空。

## 过程偏差

Cleanup与scratch纪律有两项必须永久保留的偏差，但均发生在实验日志已完成之后，不改变`PASS`分类：

1. 冻结cleanup shell中的首个 `pkill -9 -f 'Gradle[D]aemon'` 会匹配wrapper完整command line后部未括号化的同名literal，导致shell self-kill。首个command只执行一次并清除了Gradle daemon，但exit code未保存，`cleanup-gradle-daemon.exit`不存在；同一shell中的commands 2/3因此未执行。Chief确认后只补执行原先未运行的commands 2/3，各一次且未重跑首个command；保存结果为`cleanup-kotlin-compile-daemon.exit=0`、`cleanup-kotlin-embeddable-daemon.exit=1`。
2. Worker曾在授权scratch root外短暂创建 `/tmp/task092-code-only.kts`，随后删除；终态不存在。

后续cleanup block必须避免在shell command line其他位置出现可被目标regex匹配的literal；输出丢失或shell中断时不得重跑已执行的cleanup命令。

## 结论范围与下一步

Task 092只证明：在Tasks 090/091已证明安全的parameter/load层上，production helper positive allowlist admission与class-byte no-op visitor creation也不是已观察failure的充分trigger。它不证明transient cache、`referenceOnlyVisitor(...)`、完整166-class execution、APK、R8或runtime，也不能把cache fields、caller count或production visitor断言为root cause。

下一独立Task 093只恢复production-shaped transient cache layer，保持sentinel positive admission和class-byte no-op visitor，不调用 `referenceOnlyVisitor(...)`。若Task 093 `PASS`，后续再以独立rung恢复production visitor construction；若重现known path，则围绕cache最小边界设计production fix。
