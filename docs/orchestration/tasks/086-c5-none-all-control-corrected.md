# Task 086 — Run the corrected no-op `ALL` isolation control

## Goal

用一次临时、可完全恢复且**显式传空 `instrumentationParamsConfig` lambda `{ }`**的 `InstrumentationParameters.None` no-op `InstrumentationScope.ALL` registration，完成 Task 085未触达的 isolation control。只做控制实验，不形成production实现。

## Authority

本任务是串行、临时buildSrc diff、单Gradle command、最终零tracked diff的诊断worker：

- May：读取项目、Task 084/085证据与本地AGP/Gradle cache；创建指定scratch；临时编辑两个Allowed Paths；运行下述唯一Gradle command；结束后精确恢复并终止本次daemon。
- May NOT：修改其他tracked path、production factory、规则/allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard或SystemUI源码；运行其他Gradle task、full assemble、Release/R8、checker、device、Soong/Ninja；commit/push；直接`python`/`python3`。
- Reports To：Chief。

## Allowed Paths（临时改动，必须恢复）

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpAllScopeFactory.kt`
- `/tmp/task086-c5-none-all-control-corrected/**`

## Required startup

1. 完整读取`AGENTS.md`，等待返回。
2. 再以独立调用完整读取`docs/orchestration/CHARTER.md`，等待返回。
3. 读取worker-contract、本brief、Task 086 issue、Task 085 issue、Task 084 issue和两个前序scratch summary/log摘要。
4. 输出`CONTRACT:`；Chief接受前不得创建scratch、编辑或运行命令。

## Procedure

1. 创建scratch，确认branch/HEAD、worktree clean且无Gradle/Kotlin/Soong/Ninja活动进程；否则停止。
2. 记录plugin原始SHA-256并确认no-op factory不存在。创建：
   - `internal abstract class NoOpAllScopeFactory : AsmClassVisitorFactory<InstrumentationParameters.None>`；
   - `isInstrumentable(classData: ClassData): Boolean = false`；
   - `createClassVisitor(classContext: ClassContext, nextClassVisitor: ClassVisitor) = nextClassVisitor`。
3. 仅把`AconfigInstrumentationRegistration`的factory临时切到no-op，registration必须逐字具有空lambda形态：
   ```kotlin
   instrumentation.transformClassesWith(
       NoOpAllScopeFactory::class.java,
       InstrumentationScope.ALL,
   ) { }
   ```
   application-only gate和`COPY_FRAMES`保持不变；不得省略`{ }`，不得读取rules/allowlist。
4. 保存完整临时证据到scratch，运行`git diff --check`，输出exact changed-path list，然后停止等待Chief检查。
5. Chief接受后，运行且仅运行：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task086-c5-none-all-control-corrected/desugar-none-all.log
   ```
6. 记录真实exit code，按日志分类；不得运行第二个Gradle task/control。
7. 无论结果如何，精确恢复plugin并删除临时factory；终止本次Gradle/Kotlin daemon，确认worktree clean且无残留构建进程。
8. 输出report与`HANDOFF:`；不得commit或编辑docs。

## Acceptance

- 运行前diff恰好两个Allowed Paths；production factory、四规则、166-class allowlist未改。
- 临时factory使用AGP 9.3.1 `ClassData`/`ClassContext`签名；registration显式包含空lambda `{ }`。
- 唯一command运行一次，exit code与exact result已记录。
- `CONTROL_RESULT=SAME_API_VERSION_FAILURE|PASS|OTHER_FAILURE`。
- 若为`SAME_API_VERSION_FAILURE`，literal path必须同时包含`InstrumentationContext_Decorated.__apiVersion__`与`NoOpAllScopeFactory_Decorated.__instrumentationContext__`。
- 最终tracked worktree clean；无第二task、full build、Release/device/Soong操作。

## Report format

```text
STATUS: PASS|FAIL
CONTROL_PATCH_PATHS=
LOOP_EXIT=
CONTROL_RESULT=SAME_API_VERSION_FAILURE|PASS|OTHER_FAILURE
DEEPEST_CAUSE=
FIELD_PATH=
PRODUCTION_FACTORY_UNCHANGED=YES|NO
TRACKED_WORKTREE=
FORBIDDEN_ACTIONS=NONE|...
NEXT=Chief decides supported production seam
```

End with a concise `HANDOFF:` block.
