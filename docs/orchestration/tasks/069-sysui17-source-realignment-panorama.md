# Task 069 — SystemUI-17 源码重对齐全景扫描（C3 预研，只读）

## 背景

- AOSP 树已切到 `android-17.0.0_r1`（frameworks/base `94b4c163b`，2026-05-21），全量 out/ 已构建。
- 项目源码仍对齐 2025-03-26 旧树（SDK 35 preview 时代），漂移 14 个月。
- 本任务为 **Phase C 步骤 C3（源码重对齐）的预研**：只读分析，不做任何源码/资源改动，不跑 Gradle。
- 用户已裁决（ADR 0007）：C3 先行（先保证源码不重不漏，编译错误留给 C4 Gradle 适配，不管）；模块拓扑跟随新 bp 语义做**最小必要**调整。

## Global Constraints

- 只读任务：**禁止**修改任何 `SystemUI-*/src`、`res`、`libs/`、`*.gradle.kts`；禁止跑任何 Gradle 命令；禁止 push。
- Python 一律 `uv run`（如需跑脚本）。
- 报告写 `docs/`，commit 用英文，本地 commit（不 push）。
- AOSP 根路径唯一来源：`tools/aosp_paths.py`（当前指向 /home/conv/myspace/aosp）。
- 工具是 `python3 tools/check_source_alignment.py`（默认走 aosp_paths；支持 --summary/--strict/--no-res）。

## 基准数字（chief 已独立复核，报告中的数字必须与之对得上）

`python3 tools/check_source_alignment.py --summary` 当前输出：

| 计数器 | 值 |
|---|---|
| MISSING（AOSP 有项目缺） | 1963 |
| MISPLACED（owner 错） | 20 |
| EXTRA（项目多余） | 642 |
| MODIFIED（同路径字节不同） | 2222 |
| APP | 0 |
| RES-MISS / RES-EXTRA / RES-MODIFIED | 438 / 219 / 830 |

## File Map（产出物）

- `docs/architecture/2026-08-27-sysui17-realignment-panorama.md` — 主报告
- `docs/issues/2026-08-27-sysui17-realignment-panorama.md` — 问题记录
- 允许新建上述两个文档 + 更新 `docs/orchestration/STATE.md` 的本 task 行；其余一律不动。

## 步骤（checkbox）

### S1 对齐全景分解
- [ ] 把四个源码计数器（1963/20/642/2222）按 **Gradle module（13 个）+ AOSP 一级子目录** 双维度分解成表格。
- [ ] MISSING 按新增目录聚类：识别 AOSP 17 新增的顶层/二级目录（如 application/、metrics/ 等），列出每个新目录的文件数与 bp 归属。
- [ ] EXTRA 的 642 个逐类归因：① 旧树存在、17 已删除；② 历史搬运错误；③ 其他。给出删除清单建议。
- [ ] MISPLACED 20 个逐个列出（路径 + 应属 owner）。
- [ ] res 三计数器（438/219/830）按 res/、res-keyguard/、res-product/ 分解。

### S2 Android.bp 语义 diff → 模块拓扑影响
- [ ] 通读新 `frameworks/base/packages/SystemUI/Android.bp`（含子目录 bp），对照项目现有 13-module 拓扑（见 `docs/architecture/2026-08-06-module-structure-audit.md`、ADR 0003）。
- [ ] 列出新树 bp 相对旧语义的变化：新增 soong 模块（android_app/android_library 等）、消失的模块、static_libs 依赖边重大变化。
- [ ] 给出「最小必要」Gradle 拓扑调整建议：哪些新 bp 模块应并入哪个现有 Gradle module、哪些需要新 module（预期 application/、metrics/ 等需裁决，标出建议+理由）。**只建议，不实施。**

### S3 CONV 标记存量盘点（ADR 0004）
- [ ] 统计项目内所有 CONV_ADD/CONV_DEL/CONV_MOD + BEGIN/END 块的位置与数量（src + res）。
- [ ] 对每个 CONV 标记点，比对 17 树对应文件，分类：A=17 已吸收该改动（标记可撤销，回滚为纯 AOSP 字节）；B=17 仍未吸收（标记需要保留并重新 CONV 重批）；C=对应文件在 17 中已删除（标记随之消亡）。
- [ ] 输出三类清单（文件级粒度即可，不必逐行）。

### S4 执行批次计划（C3 落地方案建议）
- [ ] 设计重对齐执行批次：建议按 module 或目录分批（每批一个 worker 任务），每批验收 = 该范围对齐计数器归零（RES 归零）。
- [ ] 评估机械化程度：纯 copy/delete 的部分可否写一个 Python 同步工具（tools/ 下，uv run）一次性完成？哪些部分必须人工（CONV 重批、misplaced 移动、拓扑变化涉及的目录搬家）？
- [ ] 给出每批的预估文件操作数、风险点（如 aidl 新增、manifest 变化 1158 行基线是否漂移、plugin API 变更波及）。
- [ ] 明确 **AndroidManifest.xml（app 模块，AOSP 完整复制基线）** 在 17 树的行数/内容漂移情况。

### S5 报告与收尾
- [ ] 主报告 + issue 文档写全（背景/操作/数字演变/待决问题）。
- [ ] 英文 commit（docs-only），本地不 push。
- [ ] 四段式完成报告（CONTRACT 回显、做了什么、证据、遗留）。

## 五字段

- **Authority**: self-commit（仅 docs/ + STATE.md 行；**不得**触碰任何源码/资源/构建文件）
- **Allowed Paths**: `docs/architecture/2026-08-27-sysui17-realignment-panorama.md`、`docs/issues/2026-08-27-sysui17-realignment-panorama.md`、`docs/orchestration/STATE.md`（本 task 行）
- **Forbidden Paths**: 一切 `SystemUI-*/`、`app/`、`libs/`、`tools/`（只读使用除外）、`*.gradle.kts`、`gradle/`、`settings.gradle.kts`、`.git push`
- **Acceptance**: `python3 tools/check_source_alignment.py --summary` 输出数字与本文基准表逐项一致（worker 复跑记录在报告中）；主报告包含 S1–S4 四个章节且 S4 有分批清单；`git diff --name-only HEAD~1` 只含 Allowed Paths。
- **Reports To**: chief（herdr agent `task069`，主会话 `w2:p1`）

## 模型

joycode GLM-5.3（用户规则：worker 仅 joycode GLM）。
