# Task 019 — 文档/脚本小清理（docstring + legacy .sh + AGENTS.md libs 树）

## Goal

三项已批准的小清理：
1. `tools/install_aar_to_maven.py` docstring L13–14 仍引用已删除的 `gen_aar_maven.py` → 移除该引用；
2. `scripts/check-aosp-src-parity.sh`（legacy bash，与 Python 孪生 `check_aosp_src_parity.py` 同 commit 引入）→
   先验证 `.py` 是功能超集：若是，直接删 `.sh`；若有 `.sh` 独有逻辑，先并入 `.py` 再删 `.sh`；
3. `AGENTS.md` §3.2 的 `libs/maven/` 目录树已过时 → 与实际目录同步
   （实际 16 个 artifact 目录 + `com/android/server/notification-flags/`，含 LowLightDreamLib、
   setupcompat、SettingsLibSettingsTheme、7 个 per-target AAR；树中 `[已删]`/`[旧]` 等过期注释一并修正）。

## Non-goals

- 不改任何脚本的功能逻辑（除 2 中必要的 delta 移植）；
- 不动 libs/ 产物、源码、res、catalog、构建文件；
- AGENTS.md 仅更新 §3.2 的目录树块，不改规则文字；
- 不重构。

## Allowed Paths

- `tools/install_aar_to_maven.py`（仅 docstring）
- `scripts/check-aosp-src-parity.sh`（删除）、`scripts/check_aosp_src_parity.py`（仅当有 delta 需移植时）
- `AGENTS.md`（仅 §3.2 libs 树块）
- `docs/issues/2026-08-19-small-cleanups.md`、
  `docs/orchestration/tasks/019-small-cleanups.md`（本文件勾选）

## Forbidden Paths

其它一切。注意 `docs/` 历史文档中对被删脚本的引用属于历史记录，**不改**。

## Execution Hints

1. 先 worker-contract skill 输出 `CONTRACT:`；
2. 对项 2：读两个脚本对比功能；`git grep` 确认无在役引用（docs 历史除外）；
3. 对项 3：用 `ls libs/maven/com/android/systemui/ libs/maven/com/android/server/` 取真实列表，
   逐个对照 catalog alias 补注释；
4. 跑 `python3 -m unittest discover -s tools/tests -p 'test_*.py'` 验证 OK；
5. `git diff --check` 干净；英文 commit；**不 push**。

## Acceptance

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（148 基线）
- `git grep -n "gen_aar_maven" -- ':!docs/'` 无残留
- `scripts/` 下无 `.sh` 文件
- AGENTS.md §3.2 树与实际 `libs/maven/` 一致（逐目录核对）
- issue 文档更新

## Report

完成后汇报：commit、逐条 checklist（真实输出）、.sh 删除前功能对比结论、issue 更新、新发现、HANDOFF 块。
