# Task 084 — Capture Java serialization field path

## Goal

对 Task 083 已固定的 `java.io.NotSerializableException: org.gradle.api.internal.provider.DefaultProperty` 启用 JDK extended serialization debug info，以同一 direct dependency-transform task取得第一条可验证的 factory object-graph field path。只诊断，不修改 build logic。

## Authority

本任务是**只读、单命令、零 tracked-file 写入**的串行 worker：

- May：读取项目、Task 083 scratch、Gradle/AGP cache source/classfile；创建 `/tmp/task084-c5-serialization-field-path/**`；运行下述唯一 Gradle command；使用 `javap`、`unzip -p/-l`、`rg`、`find`、`sha256sum` 等只读工具；读取 `git status`；构建结束后终止本次 Gradle/Kotlin daemons。
- May NOT：编辑/创建/删除任何 tracked file；修改 AOSP/SDK/`libs/**`/build outputs；运行其他 Gradle task；运行 `assembleDebug`、Release/R8、checker、emulator/ADB、Soong/Ninja；试改代码；commit/push；direct `python`/`python3`。
- Reports To：Chief。

## Required startup

1. 完整读取 `AGENTS.md`，等待返回。
2. 再以独立调用完整读取 `docs/orchestration/CHARTER.md`，等待返回。
3. 读取 `/home/conv/.pi/agent/skills/worker-contract/SKILL.md`、本 brief、Task 084 issue、Task 083 issue和 `/tmp/task083-c5-asm-factory-isolation/SUMMARY.md`。
4. 输出 `CONTRACT:`，明确唯一命令、失败/无 field path即停、Allowed/Forbidden writes、Reports To Chief。Chief 接受前不得运行命令或创建 scratch。

## Procedure

1. 创建唯一 scratch root `/tmp/task084-c5-serialization-field-path/`。
2. 只读确认 tracked worktree clean且无 Gradle/Kotlin/Soong/Ninja活动进程；发现任一项即停止，不自行 kill。
3. 运行且仅运行：
   ```bash
   set -o pipefail
   JAVA_TOOL_OPTIONS='-Dsun.io.serialization.extendedDebugInfo=true' \
     ./gradlew :app:desugarDebugFileDependencies \
       --stacktrace --console=plain --max-workers=4 \
       2>&1 | tee /tmp/task084-c5-serialization-field-path/desugar-extended-stacktrace.log
   ```
4. 若未重现 `AsmClassesTransform` / `AconfigReferenceRewriteFactory` isolation failure，立即停止并报告 loop不等价；不得运行第二个 task。
5. 若重现，逐字提取 deepest `NotSerializableException` message及其所有 extended field-path lines。若没有扩展路径，报告 `FIELD_PATH=UNAVAILABLE`并停止，不推断具体 owner。
6. 若取得路径，以当前 classfile与 AGP 9.3.1 local source逐段对应，并提出一个最小 buildSrc fix experiment；不得实现。
7. 终止本次 Gradle/Kotlin daemons，确认 tracked worktree clean，输出 HANDOFF。

## Acceptance

- 唯一 command的真实 exit code与 exact-failure reproduction已记录。
- `DEEPEST_CAUSE` 与 `FIELD_PATH`逐字记录；字段归属只依据 extended message，不靠猜测。
- 下一步 proposal保持四规则/166-class/reference-only/app-only `ALL` contract不变；若路径不可用，唯一后续为单独的 `InstrumentationParameters.None` no-op `ALL` control。
- tracked worktree clean；无其他 Gradle task、无build logic编辑、无Release/device/Soong操作。

## Report format

```text
STATUS: PASS|FAIL
LOOP_EXIT=
EXACT_FAILURE_REPRODUCED=YES|NO
DEEPEST_CAUSE=
FIELD_PATH=<literal path>|UNAVAILABLE
PATH_OWNERSHIP=
MINIMAL_NEXT_EXPERIMENT=
TRACKED_WORKTREE=
FORBIDDEN_ACTIONS=NONE|...
NEXT=Chief decides separate implementation/control task
```

End with a concise `HANDOFF:` block.
