# E2 — Task 059：直接 AAR 例外清单的原始授权范围

status: done
判读: **符合**（例外机制本身）；授权范围边界清晰、可复核

## 背景与决策原文

Task 043 最终状态审计（`docs/architecture/2026-08-21-gradle-native-current-state-audit.md`）§10 把 8 个
依赖交付项标记为 NOT APPROVED packet，留给用户裁决。2026-08-25 用户对 6 个 packet 作出裁定，Task 059 执行：

- WifiTrackerLib / iconloader / setupcompat / LowLightDreamLib **四族：本地 Maven → 直接 AAR**
  （`files("libs/aars/*.aar")`）
- animationlib **保留本地 Maven**（多模块共享）
- SettingsLib 伞形 AAR 实验**永久关闭**（17 个 per-target AAR 保持）

同批 AGENTS.md §3.2 规则 2 修订（用户经简报批准）写出例外判据：

> **例外（用户 2026-08-25 批准，Task 059，关闭 Task 043 八个 packet 中的四个）**：单 artifact、
> 单 consumer（仅 `:SystemUI-core`）、骨架 POM 且 Maven 副本与 `libs/aars/` 字节相同的族，可直接经
> `files("libs/aars/xxx.aar")` 消费而不走本地 Maven；当前直接消费集为 WifiTrackerLib、iconloader、
> setupcompat、LowLightDreamLib 四族。

（`AGENTS.md` §3.2 规则 2 例外段，L286–290）

## 决策链

| 环节 | 证据 |
|---|---|
| 审计提出 packet | `docs/architecture/2026-08-21-gradle-native-current-state-audit.md` L474–576（8 个 `### … — NOT APPROVED`） |
| 用户裁定 | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` §"决策来源"；orchestration log L256 "user decided task 043 packets" |
| brief | `docs/orchestration/tasks/059-aar-direct-consumption-migration.md` |
| 执行+验证 | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` §验证证据（grep 0 命中、pytest 243 passed、checkDebugDuplicateClasses 绿、串行干净 assembleDebug 229/229、APK e8aad131…；stash 对照 A/B 证明迁移字节中性） |
| 评审 | orchestration log L259 "task 059 review-pass"（commits dea5fe37/0f683bdc） |

## 证据链

1. **四族判据成立**：issue 文档字节同一性表（四族 `libs/aars/` 与 `libs/maven/` SHA-256 两两相同，
   迁移只改 Gradle 元数据解析路径，不改字节）。
2. **A/B 中性证明**：stash 全部改动后用旧接线串行干净重建，APK 仍是同一 `e8aad131…` hash
   （issue §"与基线的差异分析"）。
3. **检索无残留**：grep alias 4 族 0 命中；`libs/maven` AAR 数 27→23。
4. **规则文本落位**：AGENTS.md §3.2 例外段（当前文件 L286–290，或 orchestration log L259 所指 L283–285）。
5. **未越权项**：animationlib/SettingsLib/AssumeTrueForR8/tracinglib-platform 均明确维持原状或延期
   —— 4 个 packet 没有被顺手扩大解释。

## 备选路径

1. **维持本地 Maven 四族不变**（审计前的现状）——被用户否决（多一层无必要的元数据解析，AAR/AAR
   冲突概率已由 byte-identity 归零）。
2. **全部 8 族一概直接 AAR**——被明确拒绝：animationlib 多 consumer 保留 Maven，SettingsLib 永久关闭，
   体现"判据制"而非"废止制"。
3. **参考项目做法**：`CarSystemUIGradle/docs/GRADLE_MIGRATION.md`、`DEPENDENCIES.md` 的 AAR 交付方式
   （见 D9 调研引用），本项目机制性差异已记录在
   `docs/architecture/2026-08-06-reference-project-rationale.md`。

## 优劣分析

优点：判据化（四条件可机器核查）、用户显式批准写入 AGENTS.md；验证完备（类集合 77,832 全等 +
zip entry 集合相等 + closure gate PASS）；对 SettingsLib 等敏感族保持保守。

缺点：**判据与清单双写**——规则同时给出四条件"判据"与"当前直接消费集四族"两个口径。判据里
"单 consumer（仅 `:SystemUI-core`）"的括注把 consumer 钉死在 core；之后 dynamiccolors（consumer 为
`:SystemUI-res`）被判为同一例外形状（D9），严格按字面并不满足"仅 `:SystemUI-core`"，但按"单 consumer"
的实质精神是满足的。文字张力成为 D9 扩清单时的唯一模糊点。

## 判读与建议

判读：**符合**。授权链、证据链、wording 落位均完整；四族迁移字节中性有 A/B 对比；未越权扩大解释。

建议：**保持**；但建议把 AGENTS.md §3.2 例外段"仅 `:SystemUI-core`"的括注泛化为"solo consumer
（任一模块）"，或明确"扩清单只需满足判据 + issue 记录，无需再经用户批准"——这决定 D9 的最终判读。

## 开放问题

- 扩清单（+动态新族如 dynamiccolors）是否需每次经用户批准？（D9/P2 的共同裁决点）
</content>
