# Task 085 — Isolate `ALL` factory infrastructure with a no-op control

## Goal

用一次临时、可完全恢复的 `InstrumentationParameters.None` no-op `InstrumentationScope.ALL` registration，判定 Task 084 的 `InstrumentationContext_Decorated.__apiVersion__` serialization failure是否独立于项目自定义 parameters。只做控制实验，不形成 production实现。

## Authority

本任务是**串行、临时 buildSrc diff、单 Gradle command、最终零 tracked diff**的诊断 worker：

- May：读取项目、Task 084 scratch与本地 AGP/Gradle cache；创建 `/tmp/task085-c5-none-all-control/**`；临时编辑下列两个 Allowed Paths；使用只读 shell工具；运行下述唯一 Gradle command；结束后精确恢复临时改动并终止本次 daemon。
- May NOT：修改其他 tracked path；修改 production `AconfigReferenceRewriteFactory.kt`、规则/allowlist、`:app` wiring、AOSP/SDK/`libs/**`、ProGuard或SystemUI源码；运行其他 Gradle task；运行 full assemble、Release/R8、checker、emulator/ADB、Soong/Ninja；commit/push；直接 `python`/`python3`。
- Reports To：Chief。

## Allowed Paths（临时改动，必须恢复）

- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/AconfigReferenceRewritePlugin.kt`
- `buildSrc/src/main/kotlin/com/android/systemui/aconfigrewrite/NoOpAllScopeFactory.kt`
- `/tmp/task085-c5-none-all-control/**`

## Required startup

1. 完整读取 `AGENTS.md`，等待返回。
2. 再以独立调用完整读取 `docs/orchestration/CHARTER.md`，等待返回。
3. 读取 `/home/conv/.pi/agent/skills/worker-contract/SKILL.md`、本 brief、Task 085 issue、Task 084 issue和 `/tmp/task084-c5-serialization-field-path/SUMMARY.md`。
4. 输出 `CONTRACT:`，明确临时 diff、唯一 command、恢复义务、Allowed/Forbidden paths和 Reports To Chief。Chief接受前不得创建 scratch、编辑或运行命令。

## Procedure

1. 创建 `/tmp/task085-c5-none-all-control/`，确认 branch/HEAD、tracked worktree clean且无 Gradle/Kotlin/Soong/Ninja活动进程；否则停止，不自行 kill。
2. 记录 Allowed Paths原始 SHA-256。创建一个最小 `NoOpAllScopeFactory : AsmClassVisitorFactory<InstrumentationParameters.None>`：`isInstrumentable`恒为 `false`，`createClassVisitor`原样返回 `nextClassVisitor`。
3. 仅把 `AconfigInstrumentationRegistration` 中 `transformClassesWith` 的 factory临时切到 no-op control，保持 application-only、`InstrumentationScope.ALL`、`FramesComputationMode.COPY_FRAMES`不变；不读取 rules/allowlist，不改 production factory。
4. 保存 `git diff --binary` 到 `/tmp/task085-c5-none-all-control/control.patch`，运行 `git diff --check`，输出 exact changed-path list，然后停止等待 Chief检查临时 diff。
5. Chief接受后，运行且仅运行：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task085-c5-none-all-control/desugar-none-all.log
   ```
6. 记录真实 exit code。若失败，逐字提取 outer failure、deepest cause与所有 extended field-path lines；若通过，也如实记录。不得运行第二个 Gradle task或第二个 control变体。
7. 无论结果如何，精确恢复 plugin文件并删除临时 no-op文件；不得恢复其他路径。终止本次 Gradle/Kotlin daemon，确认 tracked worktree clean且无残留匹配进程。
8. 输出 report与 `HANDOFF:`；不得 commit。

## Acceptance

- 运行前临时 diff恰好两个 Allowed Paths；production factory、四规则、166-class allowlist均未改。
- 唯一 command运行一次，exit code和 exact result已记录。
- `CONTROL_RESULT=SAME_API_VERSION_FAILURE|PASS|OTHER_FAILURE`，只按日志判定。
- 若为 `SAME_API_VERSION_FAILURE`，literal path必须同时包含 `InstrumentationContext_Decorated.__apiVersion__` 与 no-op factory decorator的 `__instrumentationContext__`，且不得再归因 custom parameters。
- 最终 tracked worktree clean；无第二 task、full build、Release/device/Soong操作。

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
