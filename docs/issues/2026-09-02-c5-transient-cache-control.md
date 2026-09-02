# C5 Task 093：transient input-cache control

**日期**：2026-09-02
**状态**：待执行
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

## 错误数演变与待解决问题

- 本任务开始前不运行编译，错误数无新变化；Task 092 focused command为exit 0，但不等同于APK build。
- 待解决：cache是否激活known path；之后仍须独立隔离`referenceOnlyVisitor(...)`，再实施/验收production fix并重跑双APK与runtime gates。
