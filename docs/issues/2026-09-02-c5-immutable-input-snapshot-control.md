# C5 Task 094：immutable parameter snapshot control

**日期**：2026-09-02
**状态**：已设计，待从 clean pushed planning base 串行执行
**前置**：Task 093 已闭合为 `CACHE_ACTIVATED_ISOLATION_FAILURE`。相对 Task 092，完整 production-shaped transient cache layer 足以在任何 factory callback 前激活 Task 084 literal path；但没有单独证明字段、instance state、`@Transient`、accessor 或 writeback 是 sole trigger。

## 问题与反馈环

下一步不再继续拆 cache layer 的内部字段，而是验证一个可直接落地的 isolation-safe seam：在 plugin 配置阶段只调用一次 `FrozenAconfigInputs.load(...)`，将已校验、规范化的四条 mapping 与 166-class allowlist 写入 Gradle-managed `MapProperty<String, String>` 和 `SetProperty<String>` transform inputs；factory 保持零实例字段，并只读取这些 immutable parameter values。

反馈环仍是唯一 direct artifact-transform command：

```bash
set -o pipefail
JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
  ./gradlew :app:desugarDebugFileDependencies \
    --info --stacktrace --console=plain --max-workers=4 \
    2>&1 | tee /tmp/task094-c5-immutable-input-snapshot/desugar-immutable-inputs.log
```

该 command 只验证 dependency `AsmClassesTransform` 能否完成 isolation 并到达 sentinel-scoped class-byte no-op visitor；不是 full Debug build，也不证明 production `referenceOnlyVisitor(...)`、APK、R8 或 runtime。

## 排名假设与设计选择

1. **H1（首选）— Gradle-managed immutable parameter snapshot**：若失败由 decorated factory 上的 instance cache layer 激活，则把规范化输入放入 managed parameter values、保持 factory field-free，应恢复 Task 092 类似的可观察成功。该 seam 无逐类文件 I/O，也没有 daemon-global mutable cache；参数值本身是 transform inputs。
2. **H2 — factory 外部 weak cache**：static/外部 cache 不会从 factory 字段图可达，理论上可能通过 isolation，但引入 daemon 生命周期、identity key、失效与并发语义，优先级低于 H1。
3. **H3 — 完全无 cache、每次 callback 重新 load 文件**：Tasks 091/092 已证明 sentinel-scoped load 可执行，但 production `isInstrumentable` 会面对全部 class，重复 I/O/哈希/解析不是可接受的首选实现。
4. **H4 — `ScopedArtifacts` 替代 seam**：Task 089 只证明 pre-R8；Debug pre-D8 coverage 未证明，当前不采用。

Task 094 只检验 H1 的 isolation 属性，不实现 production visitor。H1 若失败，停止并根据 literal path 分类；不得在同一任务切换到 H2/H3/H4。

## 单变量 control

1. 临时新增 `ImmutableInputsControlParameters : InstrumentationParameters`，只包含：
   - `@get:Input val mappings: MapProperty<String, String>`；
   - `@get:Input val allowlist: SetProperty<String>`。
2. 临时新增 field-free `ImmutableInputsControlFactory`：factory class body 不得声明任何 instance/static/companion cache 或其他 state。
3. Plugin 在 registration 前对 production rules/allowlist 调用一次且仅一次 `FrozenAconfigInputs.load(...)`，确认 4 mappings / 166 allowlist，再把结果设置到两个 managed properties。不得把 `File`、`FrozenAconfigInputs` 或 cache object 保存到 factory。
4. `isInstrumentable` 对所有非 `android.os.CustomFeatureFlags` 立即返回 `false`。对 sentinel：
   - 打印 `TASK094_VALUES_ENTERED=android.os.CustomFeatureFlags`；
   - 读取两个 managed values，验证 4/166；
   - 调用 production `AconfigReferenceRewriteFactory.isAllowlistedClass(...)` 并要求 true；
   - 打印 `TASK094_VALUES_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166`；返回 true。
5. `createClassVisitor` 只核对 sentinel，打印 `TASK094_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags`，原样返回 `nextClassVisitor`。不得调用或构造 `referenceOnlyVisitor(...)`。
6. 保留 application-only gate、`InstrumentationScope.ALL`、`COPY_FRAMES` 和 production rules/allowlist bytes；只临时切换 factory/parameter wiring。

Temporary tracked writes 仅允许：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/ImmutableInputsControlFactory.kt`

Scratch 仅允许 `/tmp/task094-c5-immutable-input-snapshot/**`。禁止修改 production factory/input loader/reference rewriter、rules、allowlist、app wiring、AOSP/SDK/`libs/**`、ProGuard 或 SystemUI 源码；禁止第二个 Gradle wrapper command、full assemble、Release/R8、checker、device、Soong/Ninja、commit/push 和 direct `python`/`python3`。

## 判据

- `PASS`：command exit 0，entered/accepted/no-op visitor sentinel 均至少 1，且 log 有 `AsmClassesTransform` execution records、known serialization markers 为 0。结论仅为 immutable managed-value/field-free control 在真实 dependency transform 中 isolation-safe。
- `IMMUTABLE_VALUES_ISOLATION_FAILURE`：command 非 0，并重现 `InstrumentationContext_Decorated.__apiVersion__` → temporary factory `__instrumentationContext__` literal path。
- `CONFIGURATION_LOAD_FAILURE`：在 transform callback 前由单次 `FrozenAconfigInputs.load(...)` 或 managed-value wiring 失败，且不是 known isolation path。
- `INCONCLUSIVE`：exit 0 但 accepted/visitor sentinel 或 ASM execution evidence 缺失。
- `OTHER_FAILURE`：其他结果。任何非 PASS 均停止，不试第二 seam。

## Cleanup 与恢复

无论结果如何，plugin 必须逐字节恢复，temporary factory 必须删除。Cleanup 只允许以下一个 shell invocation；pattern 在运行时由分片拼接，整个 wrapper command line 不含三个可匹配 literal，输出名也保持中性。每个 command 后立即保存 exit code，不得补跑或重跑：

```bash
set +e
first_pattern='Gradle'; first_pattern="${first_pattern}Daemon"
second_pattern='Kotlin'; second_pattern="${second_pattern}CompileDaemon"
third_pattern='kotlin-daemon-'; third_pattern="${third_pattern}embeddable"
pkill -9 -f "$first_pattern"; first_rc=$?
printf '%s\n' "$first_rc" > /tmp/task094-c5-immutable-input-snapshot/cleanup-1.exit
pkill -9 -f "$second_pattern"; second_rc=$?
printf '%s\n' "$second_rc" > /tmp/task094-c5-immutable-input-snapshot/cleanup-2.exit
pkill -9 -f "$third_pattern"; third_rc=$?
printf '%s\n' "$third_rc" > /tmp/task094-c5-immutable-input-snapshot/cleanup-3.exit
printf 'one=%s\ntwo=%s\nthree=%s\n' "$first_rc" "$second_rc" "$third_rc"
```

随后只做 read-only process census、production hashes、temporary-factory absence 和 clean worktree 验证。

## 错误数演变与待解决问题

- 本任务尚未执行；当前真实 production pipeline 仍在 Task 093 所证 isolation path 阻塞，新 Debug APK 尚未产出。
- 若 Task 094 `PASS`，下一独立 implementation task 才允许将 production factory 迁移到 immutable managed-value seam、补 focused tests，并在另一个明确 gate 中恢复 `referenceOnlyVisitor(...)`。
- 若非 PASS，保留唯一 log/field path 后停止，由 Chief 重新排序 H2/H3；不恢复 Task 079 broad replay。
