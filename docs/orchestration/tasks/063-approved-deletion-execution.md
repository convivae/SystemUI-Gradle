# Task 063 — 执行已批准的 17 项删除 + 验证基线不变

## Authority（用户 2026-08-26 全部批准）

- 删除以下 **18 个文件**（17 项批准清单 + scripts 时代的 CSV）：
  1. `libs/lifecycle-process-2.4.0-alpha01.aar`
  2-15. `scripts/` 目录下全部 14 个 .py（`check_aosp_src_parity.py`、`check_aosp_extras_breakdown.py`、`check_aosp_extras_sysui.py`、`check_extras_in_jars.py`、`map_extras_to_modules.py`、`move_extras_to_modules.py`、`propose_aosp_to_gradle_mapping.py`、`recover_aosp_files.py`、`recover_compose_files.py`、`rollback_moves.py`、`scaffold_aosp_modules.py`、`scan_aosp_bp_modules.py`、`strip_extras_already_in_jars.py`、`strip_extras_stubs.py`）——空目录一并移除
  16. `tools/extract_prebuilts.sh`
  17. `gradle/replace-sdk-jar.gradle.kts`
  18. `docs/extras-file-mapping.csv`
- 修改以下历史文档，加"已删除"注记（**只加注记，不改写历史内容**）：
  - `docs/audit-2026-07-30-aosp-src-parity.md`
  - `docs/mapping-2026-07-30-aosp-bp-to-gradle.md`
  - `docs/issues/2026-07-30-phase-d-modules-compile.md`
  - `docs/orchestration/tasks/` 中 task 019 相关 brief（若引用了 scripts/）
  - `docs/issues/2026-08-19-aar-cleanup.md`（scaffold_aosp_modules 引用处）
  - `docs/adr/0002-tools-scripts-only-python.md`（extract_prebuilts.sh 示例引用处）
  - AGENTS.md 若有 scripts/ 路径引用则同步（预扫为 0，复核即可）
- Forbidden：以上清单之外的任何文件；**不得动 tools/fix_r_imports_to_res.py**（UNCERTAIN，保留复判）；不得动任何 wiring/build 文件（删除的文件均零引用，无需改 wiring——若发现删某文件必须改 wiring 才能编译，**停止并报告**，那说明审计有误）

## Acceptance（验证门，顺序执行）

1. **删除后对齐门**：`uv run python tools/check_source_alignment.py`（预期 MISSING/MISPLACED/EXTRA 全 0，与删除无关）
2. **pytest 门**：`uv run pytest tools/tests/ -q`（预期全绿；若删出 ImportError 说明有幽灵测试，报告）
3. **构建门**：先停闲置 Kotlin/AS daemon（内存纪律），然后 `./gradlew :app:assembleDebug --console=plain --max-workers=4`
   - 预期 BUILD SUCCESSFUL
   - **强验证**：`sha256sum app/build/outputs/apk/debug/app-debug.apk` 与基线 `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427` **完全一致**（删除的都是零引用文件，APK 不应变化一个字节）
   - 若 sha 不一致：**停止并报告**，diff 取证（不推测原因）
4. `git status --short` 复核：改动 = 删除 18 + 修改 ≤7 个 doc 注记，无其他

## Reports To

chief（main pane）。完成后四段式报告。commit 分两个：
(a) `chore: remove 17 approved unused artifacts/scripts + legacy extras CSV (task 062 audit, user-approved)`；
(b) `docs: annotate historical references to removed scripts`。
英文 message，本地 commit，不 push（chief 统一 push）。

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
