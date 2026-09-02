# C5 Task 093：transient input-cache control

**日期**：2026-09-02
**状态**：已完成 — `CACHE_ACTIVATED_ISOLATION_FAILURE`
**前置**：Tasks 090–092 已连续取得可观察 `PASS`。Task 092 在 production `AconfigReferenceRewriteParameters`、managed file access、一次 `FrozenAconfigInputs.load(...)`、production allowlist helper 正命中、application-only `InstrumentationScope.ALL` 和 `COPY_FRAMES` 下成功到达 class-byte no-op visitor；唯一 command exit 0，accepted/visitor sentinels 各 1。因此上述层均不是已观察 isolation failure 的充分 trigger。

## 问题

在保留 Task 092 已证明安全的 parameter/load/positive-admission/no-op-visitor 行为时，只恢复 production factory 的 **transient cache layer**——`@Transient @Volatile cachedInputs`、fast path 与 `synchronized(this)` 初始化——是否会重现 Task 084 的 literal serialization path？

该控制不调用或构造 `referenceOnlyVisitor(...)`，不改写 class bytes，不扩大 admission 到其他 caller。它只测试 production cache state/access pattern，不测试 production visitor construction。

## 单变量设计

1. 在 `/tmp/task093-c5-transient-cache-control/` 创建 production 四规则文件的逐字节副本 `task093-frozen-rules.txt`。它必须与 production 文件 `cmp` 相等，SHA-256 仍为 `ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`；allowlist 继续使用 production 166-class 文件，SHA-256 `926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`。
2. 临时新增 `TransientCacheControlFactory : AsmClassVisitorFactory<AconfigReferenceRewriteParameters>`。除 production cache layer 外，其逻辑与 Task 092 相同：
   - 唯一实例字段必须是 `@Transient @Volatile private var cachedInputs: FrozenAconfigInputs? = null`；不得增加 static/companion cache或其他状态；
   - 唯一 private accessor 必须逐语义复刻 production `inputs()`：先读 `cachedInputs` fast path；miss 时进入 `synchronized(this)` 并 second-read `cachedInputs`；仍为空时，在同一个 `FrozenAconfigInputs.load(...)` 调用表达式中精确调用 `parameters.get()` 两次（第一次取得 `rulesFile`，第二次取得 `allowlistFile`），然后 `.also { cachedInputs = it }` 写回并返回。Accessor源码中只允许这一处 `FrozenAconfigInputs.load(...)`，不得缓存或合并 `parameters.get()`；
   - 非 `android.os.CustomFeatureFlags` 立即返回 `false`，不得读取参数或cache；
   - sentinel 打印 `TASK093_CACHE_ENTERED=android.os.CustomFeatureFlags`，通过cache accessor取得4 mappings/166 allowlist，再用 `AconfigReferenceRewriteFactory.isAllowlistedClass(...)` 正命中并打印 `TASK093_CACHE_ACCEPTED=android.os.CustomFeatureFlags;mappings=4;allowlist=166`；
   - `createClassVisitor(...)` 只验证当前类、打印 `TASK093_NOOP_VISITOR_CREATED=android.os.CustomFeatureFlags` 并原样返回 `nextClassVisitor`；不得读取cache、读取parameters或调用 `referenceOnlyVisitor(...)`。
3. 临时 registration 只切换 factory，并将 `rulesFile` 指向 scratch byte-exact copy；保留 production allowlist、application-only gate、`ALL`、`COPY_FRAMES` 和 parameter interface。
4. Chief 验收 exact two-path diff、cache field/accessor、scratch identity和保存patch后，只执行一次：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --info --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task093-c5-transient-cache-control/desugar-transient-cache.log
   ```
5. 无论结果如何，恢复plugin、删除temporary factory并执行一次经过self-match审计的cleanup block。每条命令后立即保存exit code；不得重跑任何cleanup命令：
   ```bash
   set +e
   pkill -9 -f 'Gradle[D]aemon'; first_rc=$?
   printf '%s\n' "$first_rc" > /tmp/task093-c5-transient-cache-control/cleanup-gradle-daemon.exit
   pkill -9 -f 'KotlinCompile[D]aemon'; second_rc=$?
   printf '%s\n' "$second_rc" > /tmp/task093-c5-transient-cache-control/cleanup-kotlin-compile-daemon.exit
   pkill -9 -f 'kotlin-daemon-[e]mbeddable'; third_rc=$?
   printf '%s\n' "$third_rc" > /tmp/task093-c5-transient-cache-control/cleanup-kotlin-embeddable-daemon.exit
   printf 'first=%s\nsecond=%s\nthird=%s\n' "$first_rc" "$second_rc" "$third_rc"
   ```
   冻结shell文本除三个 bracketed patterns 外不得出现可被它们匹配的 daemon literal；此后只允许read-only process census。

## 判据

- `PASS`：command exit 0，精确 accepted 和 no-op visitor sentinel count 均 ≥1。结论仅为该control中的cache layer未触发known failure。
- `CACHE_ACTIVATED_ISOLATION_FAILURE`：command非0并重现 Task 084 同类 `InstrumentationContext_Decorated.__apiVersion__` → temporary factory `__instrumentationContext__` literal path；无论failure发生在cache-entered sentinel之前或之后，均记录三个sentinel counts并归此类。它只能把cache layer固定为当前最小已知激活边界；不得仅凭字段存在声称字段本身是序列化对象。
- `CACHE_LOAD_FAILURE`：cache-entered ≥1、accepted=0，且最深cause来自cache accessor/input load而非known isolation path。
- `INCONCLUSIVE`：exit 0但accepted或visitor sentinel缺失。
- `OTHER_FAILURE`：其他结果。任何非PASS均停止，不试第二变体。

## 边界与结论范围

Temporary tracked writes仅限：

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/TransientCacheControlFactory.kt`

Scratch仅限 `/tmp/task093-c5-transient-cache-control/**`。禁止修改production factory/parameters/input loader/reference rewriter、rules、allowlist、app wiring、AOSP/SDK/`libs/**`、ProGuard或SystemUI源码。禁止第二个Gradle wrapper command、full assemble、Release/R8、checker、device、Soong/Ninja、commit/push及direct `python`/`python3`。

即使 `PASS`，也只证明production-shaped transient cache layer在sentinel-scoped positive-admission/no-op-visitor control中未触发known failure；不证明 `referenceOnlyVisitor(...)`、完整166-class execution、APK、R8或runtime。PASS后下一任务才允许单独恢复production visitor construction。

## 执行结果

Task 093 从 exact pushed base `81e190e322424d8779a2d1949b355ab40427721c` 执行。Worker `task093` 位于 `w2:t3V` / `w2:p30`；session events 独立确认 `provider=joycode`、`modelId=GLM-5.3`、`thinkingLevel=high`。Chief 在唯一 Gradle command 前验收 exact two-path temporary diff：plugin/factory/patch SHA-256 分别为 `caa98714fdee0bd1567bd96d0a0573791cf859fec7b6317de0b6923ef802a550`、`617be431ff48c4b07c038b1eb3d1152b6a87d748a6e97a65214eade4c13b1411`、`75af51d80c8002d1984a113981b2bb9cb7c00f898370b35e21c50666ec58bd08`；scratch rules 与 production rules 逐字节相同。

唯一 frozen command 的 `PIPELINE_RC=1`，在 `:app:desugarDebugFileDependencies` 失败；`BUILD FAILED in 17s`，`5 actionable tasks: 3 executed, 2 up-to-date`。日志 `/tmp/task093-c5-transient-cache-control/desugar-transient-cache.log` 共 9387 行，SHA-256 为 `7f760669721065eb672c4a7ee8c07c848c45ce32c07a77c0aa7e6248c102ff31`。三个 sentinel count 均为 0，`AsmClassesTransform` cache record 为 0；这与 failure 在任何 instrumentation callback 前发生一致。

日志精确重现 Task 084 path，以下三项各出现 46 次：

```text
java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty
field InstrumentationContext_Decorated.__apiVersion__
field TransientCacheControlFactory_Decorated.__instrumentationContext__
```

因此按冻结矩阵正式归类 **`CACHE_ACTIVATED_ISOLATION_FAILURE`**。相对 Task 092 `PASS` control，加入的完整 production-shaped transient cache layer 是当前最小已知 activation boundary；本任务**没有**单独证明 `cachedInputs` 字段、instance state、`@Transient`、accessor 或 writeback 中任一项是 sole trigger，也没有执行 `referenceOnlyVisitor(...)`。

## 恢复、审计与cleanup偏差

Temporary plugin 已逐字节恢复，temporary factory 已删除；production plugin/factory/input-loader/rewriter、rules、allowlist SHA-256 分别恢复为 `f50685c37db713d10e91d5aa1851a57f0203578b02d48ee5e2af6507196feda5`、`bd92aeedd70aa677e6ee2e1c6231fa1c7dc3dca26768890950aa54a011c798cb`、`e56922137fc0573e6310063c376f84d480eb6b649aab2c42cff1e10261526f27`、`c6fbfca057d73f6d8e01c117c7886d07acb34987b301aa42536d0298fa00e7ac`、`ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`、`926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`。最终 `git status --porcelain` 为空且 `HEAD == origin/main == 81e190e3…`。Session SHA-256 为 `2f3adbc5cd2a99e65fd73090737538414a8789b437ef5ba6741c38599db86446`；独立审计确认恰好一个 `./gradlew` tool call、零 direct `python`/`python3` call。

Cleanup 与冻结文本发生过程偏差：worker 在一个 wrapper invocation 中使用了三条不同的pattern/command，shell 在第二个 exit file 后终止；`cleanup-gradle-daemon.exit=0`、`cleanup-kotlin-compile-daemon.exit=1`，第三个 `cleanup-kotlin-embeddable-daemon.exit` 从未生成。Chief 明确禁止后未补跑或重跑任何cleanup command。最终只读 census 显示无 Java/Gradle/Kotlin、Soong或Ninja进程。该偏差不改变实验分类，但必须永久保留。

## 错误数演变与待解决问题

- 本任务唯一 focused command 从 Task 092 的 exit 0 变为 exit 1，并在 artifact-transform parameter isolation 阶段重现 known literal path；这不是 APK build 结果。
- 待解决：围绕已缩小的 cache activation boundary 设计 isolation-safe production fix；在该 fix 独立验证前不恢复 full build、Release/R8 或 runtime。`referenceOnlyVisitor(...)` 尚未在production pipeline验证，但已不再是重现当前serialization failure的前置条件。
