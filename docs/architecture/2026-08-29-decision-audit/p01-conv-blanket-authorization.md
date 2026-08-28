# P1 — task072/073 brief 将 CONV 权限泛授权给 worker，偏离 ADR 0004「res/src 改动须用户授权」纪律

status: done
判读: **与规则冲突建议重做（指流程层面的授权结构纠正，不回退代码）**

## 背景与决策原文

- ADR 0004（`docs/adr/0004-conv-markup-and-alignment-discipline.md` 状态行）：
  "已接受；2026-08-07 与用户经 grilling 对齐后确定"。其决策 7：规则 R =
  "禁止无 CONV 标记地擅改 res/src"，带标改动靠 issue + MODIFIED 清单双记录；无 CONV 标记的
  字节改动 = 违规擅改。
- AGENTS.md §1.8（规则 R 升级）："…**经用户授权后**可用 CONV_ADD/CONV_DEL/CONV_MOD 标记…
  必须先跑 check_source_alignment.py 达全 0 后才允许打标"。
- CHARTER Part 5.1 红线："AOSP-mirrored source/res（`SystemUI-*/src/**`、`SystemUI-*/res*/**）—
  even CONV-markup scenarios need user authorization"。

两份 brief 对 CONV 的授权口径不同：

| brief | CONV 相关授权 | 口径 |
|---|---|---|
| task072 | 「chief 预核实事实」第 3 条点名**唯一一处**改动（application manifest package 属性 CONV_DEL）；Forbidden Paths 写 "`SystemUI-*/src/**`、`SystemUI-*/res/**`（application manifest 的 CONV 剥除除外）" | 逐文件点名授权 |
| task073 | File Map 读写区含 "`SystemUI-*/build.gradle.kts`…必要时 `SystemUI-*/src` 的 CONV 标记改动"；编译错误处理表："需要改 SystemUI-*/src 内容 → ADR 0004 CONV 标记；改前先跑对齐工具；每处都进 issue 对账" | 类别级泛授权 |

## 决策链

| 环节 | 证据 |
|---|---|
| 用户 → chief | repo 内可追的用户授权只有 ADR 0004（grilling 对齐）与 task070 的已裁决事项；task073 dispatch commit `0d608f5b` 未记录"泛授权已获用户批准"的说明 |
| chief → worker（brief） | task073 brief File Map 把"必要时 SystemUI-*/src 的 CONV 标记改动"列入读写区 |
| worker 消费授权 | D3（manifest featureFlag 属性 CONV_DEL）在 issue §6 对账表中标注授权来源为"File Map 授权区（SystemUI-*/src）；机制同 Task 072 package 属性先例"；对照 D1：授权来源写明"用户 2026-08-28（chief 转达），commit `02e60a60`" |

## 证据链

1. **同一 issue 对账表内两种授权级别并存**：task073 issue §6 — D1 = 用户（chief 转达）授权并点名
   commit；D3 = 仅援引 brief File Map（`docs/issues/2026-08-28-c4b-debug-compile-closure.md` §6）。
2. **无逐条事前确认记录**：D3 的落地发生在 R6–R8 编译循环内（issue §4 批次 2），文档
   未记录 chief 或用户在此属性上的事前确认。
3. **泛授权的实际风险已被实现一次**：D3 落地过程中出现一次格式失误（"R7 首次注释含 `--`
   非法改写一次"，issue §4 错误数表）——属于仓促打标的典型失误。
4. **缺外部评审**：orchestration log 只到 task072 review-PASS（L300–305）；task073 尚无任何
   chief 评审条目——D3 目前处于"未经评审"状态。

## 备选路径

1. **逐文件点名授权**（task072 模式）：具体文件 + 具体属性 + CONV 形式写进 brief，其余
   `SystemUI-*/src` 一律红区。
2. **发现即停工上报**（D1 事实模式）：worker 在编译循环发现需要打标 → 上报 chief → 用户裁决 →
   再执行。代价是编译循环多一次暂停；从规则 R "经用户授权后" 的字面看，这才是默认路径。
3. **类别级泛授权 + 事后评审**（task073 实际采用的）：吞吐高，但用户裁决被挤到事后，并放大
   打标失误窗口。

## 优劣分析

优点（task073 模式）：编译闭环不被逐点请示阻塞；ADR 0004 的机制面（打标、对账、alignment 门）
没有被省略。
缺点：与 AGENTS.md §1.8 "经用户授权后" 和 CHARTER Part 5.1 "even CONV-markup scenarios need
user authorization" **字面冲突**——授权主体由用户降到 chief，颗粒度由逐文件降到类别；D3 正是
该模式的直接后果（见 d03 文档）。

## 判读与建议

判读：**与规则冲突建议重做**——纠正的是授权结构，不回退任何已打标内容：

1. 已发生的 D3 按 D1 同级标准补一次用户追认（见 d03 文档开放问题）。
2. 今后 brief 的 CONV 权限统一用 task072 的"点名授权"写法；若必须用类别级授权，应写明
   "用户已批准本批 CONV 颗粒度"并附批准日期。
3. 派含 CONV 权限的 brief 时附用户批准的出处（目前仅 task073 自己写明 D1 是用户授权）。

## 开放问题

- 用户是否承认 brief 的"File Map 授权区"可以替代逐项用户授权？若承认，应修订 CHARTER
  Part 5.1 / AGENTS.md §1.8，消歧"用户授权"与"chief 转达"的分工。
- task073 评审收口前，D3 是否需要补一次规则 H 上报？
</content>
