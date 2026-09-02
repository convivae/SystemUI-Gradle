# C5 Task 094：immutable parameter snapshot control

**日期**：2026-09-02
**状态**：正式 `PASS`；temporary sources 已完整恢复，production 实现尚未迁移
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

- Task 094 唯一 Gradle command 正式 `PASS`：`PIPELINE_RC=0`，`BUILD SUCCESSFUL in 17s`，`5 actionable tasks: 2 executed, 3 up-to-date`。
- 主日志 `/tmp/task094-c5-immutable-input-snapshot/desugar-immutable-inputs.log` 共 1464 行，SHA-256 `53fbffec9cff08f3349762effca125725a8781f8a4e26f92a74a7f73e1c2f4c0`。
- 三个 sentinel 各恰好 1 次：entered、4/166 accepted、no-op visitor created；`AsmClassesTransform` records 45。`NotSerializableException`、temporary factory `__instrumentationContext__` 与 `InstrumentationContext_Decorated.__apiVersion__` marker 均为 0。
- Direct target 显示 `UP-TO-DATE`，但三个 callback sentinel 与 45 个 ASM records 直接证明 relevant factory execution；不能用 task-level status 否定该 control。
- `javap -p` 证明 temporary factory 无 declared fields；parameters 只有 `MapProperty<String, String>` 与 `SetProperty<String>` accessors。
- Session 审计确认 exactly one `./gradlew` tool call、zero Python calls，temporary writes 仅两个 allowed paths。Plugin 已从 scratch byte-exact copy 恢复，temporary factory source 已删除；最终 production/input hashes恢复，worktree clean，process census为空。

## Cleanup 与 evidence caveats

Cleanup 三条命令各执行一次，保存 exit codes `0/0/1`，未补跑或重跑。以下 caveats 不改变 `PASS`，但必须保留：

1. 初始一次未 bracket-escape 的 `pgrep -f` census 自匹配 wrapper；随后权威 census 使用 bracket-escaped/runtime-safe patterns，未错误终止任何过程。
2. `pre-run-hashes.txt` 最初因错误 test paths 含 `No such file or directory`；只清理自己的 scratch evidence，正确 test hashes 保存在 `pre-run-hashes-testfiles.txt`。
3. 普通 `git diff` 生成的 `post-mutation-diff.patch` 不包含 untracked temporary factory；其完整内容另存 `temporary-factory-copy.kt`，post-mutation status/hashes/invariants亦已保存。
4. 编译后的 temporary factory class 仍存在于 gitignored `buildSrc/build`，属于授权 Gradle run 的自然输出；tracked worktree clean，production source 已恢复。

## Bounded conclusion 与下一步

Task 094 只证明 configuration-time validated 4/166 managed values + field-free no-op factory 可通过真实 dependency-transform isolation。它不证明 production `referenceOnlyVisitor(...)`、Debug APK、Release/R8、checker 或 runtime。

下一独立 Task 095 将把该 seam 迁入 production：plugin 配置阶段一次 load，parameters 改为 managed map/set，factory 移除 cache/state 并恢复 `referenceOnlyVisitor(...)`；随后运行 focused tests 与 bounded direct-transform DEX proof。Task 095 review-PASS 前不得运行 full Debug build。Task 079 broad replay继续暂停。
