# C5 Task 092：positive allowlist admission control

**日期**：2026-09-02
**状态**：待执行
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
