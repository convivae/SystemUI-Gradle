# Task 083 — Diagnose AGP ASM factory isolation

## Goal

以 direct `:app:desugarDebugFileDependencies` feedback loop 重现 Task 082 的 exact transform-isolation failure，取得完整 deepest serialization cause，并以 AGP/Gradle primary source和当前 classfile证据裁定最小修复方向。只诊断，不修改 build logic。

## Authority

本任务是**只读、单命令、零 tracked-file 写入**的串行 worker：

- May：读取项目、Gradle/AGP cache sources与classfiles；创建 `/tmp/task083-c5-asm-factory-isolation/**`；运行唯一 Gradle command；使用 `javap`、`unzip -p/-l`、`rg`、`find`、`sha256sum` 等只读工具；读取 `git status`；构建结束后终止本次 Gradle/Kotlin daemons。
- May NOT：编辑/创建/删除任何 tracked file；修改 AOSP/SDK/`libs/**`/build outputs；运行其他 Gradle task；运行 `assembleDebug`、Release/R8、checker、emulator/ADB、Soong/Ninja；试改代码；commit/push；direct `python`/`python3`。
- Reports To：Chief。

## Required startup

1. 完整读取 `AGENTS.md`，等待返回。
2. 再以独立调用完整读取 `docs/orchestration/CHARTER.md`，等待返回。
3. 读取 `/home/conv/.pi/agent/skills/worker-contract/SKILL.md`、本 brief、`docs/issues/2026-09-02-c5-asm-factory-isolation.md` 与 Task 082 issue。
4. 输出 `CONTRACT:`，明确唯一 Gradle command、失败/不等价即停、Allowed/Forbidden writes、Reports To Chief。Chief 接受前不得运行命令或创建 scratch。

## Procedure

1. 创建唯一 scratch root `/tmp/task083-c5-asm-factory-isolation/`。
2. 只读确认 tracked worktree clean且无 Gradle/Kotlin/Soong/Ninja活动进程；发现任一项即停止，不自行 kill。
3. 运行且仅运行：
   ```bash
   set -o pipefail
   ./gradlew :app:desugarDebugFileDependencies \
     --stacktrace --console=plain --max-workers=4 \
     2>&1 | tee /tmp/task083-c5-asm-factory-isolation/desugar-stacktrace.log
   ```
4. 若没有重现 Task 082 的 `AsmClassesTransform` / `AconfigReferenceRewriteFactory` isolation failure，立即停止并报告不等价，不运行第二个 task。
5. 若重现，提取完整 exception chain（至少包含每层 exception type/message直到 deepest cause）并保存只读摘要到 scratch。
6. 使用只读证据检查：
   - 当前 `AconfigReferenceRewriteFactory` source 与 `javap -p -v` field/interface flags；
   - AGP 9.3.1 `AsmClassVisitorFactory` API source；
   - deepest cause涉及的 Gradle/AGP serializer/transform source（仅本机 cache中可用部分）。
7. 对 issue 的 H1–H4 分别给出 supported/rejected/undetermined及证据。提出一个最小 fix proposal与正确 regression gate proposal；不得实现。
8. 终止本次 Gradle/Kotlin daemons，确认 tracked worktree clean，输出 HANDOFF。

## Acceptance

- 唯一 direct task重现 exact Task 082 failure，且真实 exit code已记录；否则诚实报告 loop不等价。
- 报告 deepest exception type/message和第一项真正不可序列化/不可隔离对象；不把外层 wrapper当根因。
- H1–H4逐项裁定并引用本地 primary source/classfile证据。
- 下一步 proposal保持四规则/166-class/reference-only/app-only `ALL` seam不变，只触及必要 build logic与focused regression gate。
- tracked worktree clean；无其他 Gradle task、无build logic编辑、无Release/device/Soong操作。

## Report format

```text
STATUS: PASS|FAIL
LOOP_COMMAND=
LOOP_EXIT=
EXACT_FAILURE_REPRODUCED=YES|NO
DEEPEST_CAUSE_TYPE=
DEEPEST_CAUSE_MESSAGE=
FIRST_NON_ISOLATABLE_OBJECT=
H1=
H2=
H3=
H4=
MINIMAL_FIX_PROPOSAL=
REGRESSION_GATE_PROPOSAL=
TRACKED_WORKTREE=
FORBIDDEN_ACTIONS=NONE|...
NEXT=Chief decides separate implementation task
```

End with a concise `HANDOFF:` block.
