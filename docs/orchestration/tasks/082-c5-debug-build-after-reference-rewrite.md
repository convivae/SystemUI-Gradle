# Task 082 — C5 Debug build after pre-D8 aconfig rewrite

## Goal

在 Task 081 review-PASS 后首次执行真实 Android pipeline，证明 `:app:assembleDebug` 成功并产出完整 Debug APK，同时以静态证据确认四个 runtime-critical hidden targets 已被引用且 APK 未定义任何 hidden platform target。

## Authority

本任务是**只构建、只读取、零 tracked-file 写入**的串行 worker：

- May：读取项目/AOSP owner 文件；运行唯一 Gradle command；读取 Gradle 输出；在 `/tmp/task082-c5-debug-build/` 保存完整日志与只读检查结果；运行 `sha256sum`、`unzip -t`、`uv run python tools/check_aconfig_jarjar_references.py`；读取 `git status`。
- May NOT：编辑/创建/删除任何 tracked file；运行 Release/R8 task；运行其他 Gradle task；启动 emulator/ADB；运行 Soong/Ninja；修改 AOSP、SDK、`libs/**`、源码、资源、build logic、ProGuard、settings；commit/push；使用 `git add -A`/`.`；运行 direct `python`/`python3`。
- Reports To：Chief。

## Required startup

1. 完整读取 `AGENTS.md`，等待返回。
2. 再以独立调用完整读取 `docs/orchestration/CHARTER.md`，等待返回。
3. 读取本 brief 与 `docs/issues/2026-09-02-c5-debug-build-after-reference-rewrite.md`。
4. 输出 `CONTRACT:`，明确唯一 Gradle command、Allowed/Forbidden writes、失败即停、Reports To Chief。Chief 接受前不得运行命令或创建 scratch。

## Procedure

1. 创建唯一 scratch root `/tmp/task082-c5-debug-build/`。
2. 只读确认无 Gradle/Kotlin/Soong/Ninja 活动进程；若存在，停止并报告 Chief，不自行 kill。
3. 运行且仅运行：
   ```bash
   ./gradlew :app:assembleDebug --console=plain --rerun-tasks --max-workers=4 \
     2>&1 | tee /tmp/task082-c5-debug-build/assemble-debug.log
   ```
   保留真实 pipeline exit code；不得用 pipeline 掩盖失败。
4. 若构建失败，立即停止，只报告首个 actionable failure、日志路径、exit code 和 tracked status；不得修复或追加 Gradle task。
5. 若构建成功：
   - `test -f app/build/outputs/apk/debug/app-debug.apk`
   - 记录 byte size 和 SHA-256；
   - `unzip -t` 检查 ZIP 完整性；
   - 运行现有 checker（必须使用 `uv run python`）并保存输出/exit code：
     ```bash
     uv run python tools/check_aconfig_jarjar_references.py \
       --apk app/build/outputs/apk/debug/app-debug.apk \
       --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
     ```
6. 对 checker 输出只做如下判读：Debug 无 shrinking，old-name source definitions 可使 frozen Release gate exit 1；必须确认四个 critical hidden targets全部 referenced、全规则 hidden target definitions = 0。任何 critical old-name residual 若不是 APK 内 source definition/self-reference，则 FAIL；不得改 checker。
7. 读取 `git status --short --untracked-files=all`，tracked worktree 必须 clean。输出报告后等待 Chief；不得自己 commit。

## Allowed Paths

- Build outputs/Gradle state：`**/build/**`、`.gradle/**`（Gradle 自然生成）
- Scratch：`/tmp/task082-c5-debug-build/**`
- 所有 tracked repository 文件与 AOSP owner：只读

## Acceptance

- 唯一 Gradle command exit 0，日志含 `BUILD SUCCESSFUL`。
- Debug APK 存在、ZIP 完整，SHA-256/size 已报告。
- 四 hidden targets referenced 4/4；hidden target definitions 0。
- old-name residual 仅允许对应 APK-defined source classes/self-reference；否则 FAIL。
- tracked worktree clean；无 Release/R8、device、Soong/Ninja、代码或文档改动。

## Report format

```text
STATUS: PASS|FAIL
GRADLE_EXIT=
BUILD_RESULT=
APK_PATH=
APK_SIZE=
APK_SHA256=
ZIP_TEST=
CRITICAL_HIDDEN_REFERENCES=/4
HIDDEN_TARGET_DEFINITIONS=
OLD_SOURCE_RESIDUALS=<summary and whether each is defined>
CHECKER_EXIT=
TRACKED_WORKTREE=
FORBIDDEN_ACTIONS=NONE|...
NEXT=Chief records result; Release build/static gate remains separate
```

End with a concise `HANDOFF:` block.
