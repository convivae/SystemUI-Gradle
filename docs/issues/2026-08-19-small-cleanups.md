# 2026-08-19 — 小清理（Task 019）

## 背景

Task 018 收尾时发现三项小尾巴，用户 2026-08-19 指示先做：

1. `tools/install_aar_to_maven.py` docstring L13–14 引用已删除的 `gen_aar_maven.py`
   （018 曾试图改，因越界被 architect 拦下，现正式授权）；
2. `scripts/check-aosp-src-parity.sh` 是 legacy bash，与 Python 孪生
   `check_aosp_src_parity.py` 同 commit（0c6be974）引入，无在役引用
   （注：018 worker 报告的 `extract_prebuilts.sh` 实际已不存在，属过时信息）；
3. `AGENTS.md` §3.2 `libs/maven/` 目录树过时：缺 LowLightDreamLib、setupcompat、
   SettingsLibSettingsTheme、7 个 per-target SettingsLib AAR 等。

## 决策

- `.sh` 处置：若 `.py` 孪生是功能超集 → 删 `.sh`；否则并入后删（ADR 0002 精神）；
- AGENTS.md 只同步目录树块，不动规则文字。

## 结果

待填。
