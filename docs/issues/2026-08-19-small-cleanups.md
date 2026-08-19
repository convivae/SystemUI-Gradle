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

（Task 019 worker 执行，2026-08-19）

### 1. docstring 清理（tools/install_aar_to_maven.py）

删除了 docstring 中对已删除脚本 `gen_aar_maven.py` 的两行引用（“与 gen_aar_maven.py 的区别”
及其第一条 bullet），保留了仍然成立的描述“本工具只做文件复制 + POM 生成，不修改 AAR 字节内容”。
功能逻辑零改动。

### 2. 删除 scripts/check-aosp-src-parity.sh

**功能对比结论：`check_aosp_src_parity.py` 是功能超集，无 `.sh` 独有逻辑，直接删除。**

逐项对比：
- source set：两者均为 src/src-debug/src-release，扩展名均 .kt/.java/.aidl/.proto ✓
- 缺/多报告：两者均按 source set 输出 missing/extras，均截断前 50 条（`.py` 额外提示“and N more”）✓
- 跨 source set 误放：`.sh` 只查 src↔src-debug 一对；`.py` 查全部三对组合 ✓（超集）
- 资源目录对比：两者均对 res/res-keyguard/res-product 输出文件数对比 ✓
- AOSP 根路径覆盖：`.sh` 用 `AOSP_ROOT` 环境变量；`.py` 用 `--aosp-root` 参数（同等能力）✓
- `.py` 独有：Summary 汇总（total missing/extras/overlaps）

`git grep` 确认无在役引用（仅脚本自身注释，docs/ 历史文档不改）。

### 3. AGENTS.md §3.2 libs 树同步

与实际目录逐一对齐（脚本核对：maven 树 18/18 精确匹配，aars 树 17/17 精确匹配）：
- 删除 `[已删] WindowManager-Shell-shared.jar` 过期行；
- aars/ 补齐：LowLightDreamLib、setupcompat、SettingsLibColor、SettingsLibSettingsTheme、
  7 个 SettingsLib per-target res-only AAR；
- maven/ 补齐：com.android.systemui 下 16 个 artifact 目录（含 SettingsLibSettingsTheme、
  LowLightDreamLib、setupcompat、7 个 per-target）+ com.android.settingslib/color +
  com.android.server/notification-flags（旧树的 `com.android.server.notification/Flags/`
  错误路径已修正）；
- 每个目录对照 `gradle/libs.versions.toml` 补 catalog alias 注释；
- 规则文字未动。

### 验证

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 148 tests ... OK`（148 基线保持）
- `git grep -n "gen_aar_maven" -- ':!docs/'` → 无匹配（exit 1）
- `ls scripts/*.sh` → 无匹配（exit 2）
- `git diff --check` → 干净（exit 0）

本次未运行 Gradle 构建（纯文档/脚本注释/脚本删除改动，无构建面影响）。
