# Task 063 — 执行已批准的 17 项删除 + 验证基线不变（2026-08-26）

## 背景

Task 062（libs/ 产物盘点审计，`docs/architecture/2026-08-26-libs-artifact-inventory-audit.md`）
及其 chief 扩展（tools/+scripts/ 审计，`docs/architecture/2026-08-26-tools-scripts-inventory-audit.md`）
共识别出 16 个零引用 DELETE-CANDIDATE（含 `libs/lifecycle-process-2.4.0-alpha01.aar`、
`scripts/` 全部 14 个 .py、`tools/extract_prebuilts.sh`、`gradle/replace-sdk-jar.gradle.kts`）。
用户 2026-08-26 **全部批准**（brief：`docs/orchestration/tasks/063-approved-deletion-execution.md`，
清单 verbatim）。`docs/extras-file-mapping.csv` 为 scripts/ 时代的配套 CSV，一并删除。

`tools/fix_r_imports_to_res.py` 为 UNCERTAIN，**不在**删除范围，不得触碰。

## 操作步骤

1. 预检：18 个目标全部存在；wiring 零引用（grep 全部 *.kts/*.toml/*.gradle/*.properties/*.flags
   及 AGENTS.md → 0 匹配，与 Task 062 审计一致）；worktree 干净（仅 2 个未跟踪 brief 文档）。
2. 删除 18 个文件（`scripts/` 目录整目录移除，含 `__pycache__`）。
3. 对 6 个历史文档加"已删除"注记（只加注记，不改写历史内容）：
   - `docs/audit-2026-07-30-aosp-src-parity.md`
   - `docs/mapping-2026-07-30-aosp-bp-to-gradle.md`
   - `docs/issues/2026-07-30-phase-d-modules-compile.md`
   - `docs/orchestration/tasks/019-small-cleanups.md`
   - `docs/issues/2026-08-19-aar-cleanup.md`
   - `docs/adr/0002-tools-scripts-only-python.md`（extract_prebuilts.sh 示例引用处；
     brief 用户批准清单明示授权，仅加注记不改写决策内容）
   - AGENTS.md：预扫 + 复核均为 0 处 scripts/ 引用，无需改动
4. 验证门（顺序）：对齐门 → pytest 门 → 停 daemon 后构建门（APK sha256 必须与基线一致）。
5. 两个 commit：(a) 删除 18 文件；(b) 文档注记。本地 commit，不 push。

## 验证记录（真实输出，2026-08-26）

| 门 | 命令 | 实际结果 | 结论 |
|----|------|---------|------|
| 对齐门 | `uv run python tools/check_source_alignment.py` | MISSING=0 / MISPLACED=0 / EXTRA=0 / APP=0 / RES-MISS=0 / RES-EXTRA=0；MODIFIED=1、RES-MODIFIED=86（预存诊断，strict 不卡，与删除无关） | ✅ 达标 |
| pytest 门 | `uv run pytest tools/tests/ -q` | 2 failed, 241 passed, 52 subtests passed | ⚠️ 见下 |
| 构建门 | 停 daemon（`./gradlew --stop` + pkill kotlin-daemon）后 `./gradlew :app:assembleDebug --console=plain --max-workers=4` | BUILD SUCCESSFUL in 14s（216 tasks，全部 UP-TO-DATE —— 删除的 18 个文件均非任何构建任务输入，零影响） | ✅ 达标 |
| 强验证 | `sha256sum app/build/outputs/apk/debug/app-debug.apk` | `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427`，与基线完全一致 | ✅ 字节一致 |
| git 复核 | `git status --short` | 18 D + 6 M + 3 ??（日记录 + 2 个 chief brief） | ✅ 无多余改动 |

### pytest 门 2 个失败的归因（预存，非本 task 造成）

`tools/tests/test_gradle_r8_adapter_rules.py` 的 2 个失败
（`test_adapter_has_exactly_one_exact_active_rule`、`test_adapter_has_no_wildcard_keep_or_keep_or_assume_rules`）
为**预存失败**：task 061 commit `a5246203`（keep identity-distinct CoreStartables）与 task 060
commit `fd8c8d8e`/`356b2958` 向 `app/proguard_gradle.flags` 追加了 `-dontobfuscate` 和 3 条
`-keep` 规则，但未同步更新该测试的期望值。取证方法：`git stash` 后在 HEAD 重跑同一测试文件，
同样 2 failed 4 passed —— 与本 task 删除零相关（非 ImportError 幽灵测试）。已上报 chief，建议单独派 task 修测试期望。

## 待解决问题

- `test_gradle_r8_adapter_rules.py` 预存 2 失败（上述归因），需 chief 派 task 同步测试期望与 `app/proguard_gradle.flags` 实际规则集。
