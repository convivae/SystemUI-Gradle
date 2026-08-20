# 文档信息架构与核心文档治理（Task 039）

> 日期：2026-08-20
> 状态：设计已获用户授权；Task 038 已合并并完成 main fresh verification，等待派发

## 背景

项目已有大量 issue、architecture audit、Superpowers plan/spec、orchestration task 和迁移日志。这些材料保留了重要决策与证据，但当前存在两个问题：

1. `CURRENT_STATE`、`HANDOFF`、`PLAN`、`AGENTS`、`CHARTER`、README 等重复保存同一批动态数字，导致“APK 未生成”“131 tests”“R8 88”等陈述长期滞留；
2. 历史快照和实时文档没有清晰生命周期，维护者不知道哪些文档应持续更新、哪些应冻结。

Task 038 已在 main 完成 fresh verification：179/179 tests、debug 成功、R8 88→81 精确差分。现在以此为基线整理信息架构，而不是继续逐文件同步相同状态。

## 已批准的治理设计

### 1. 单一完整实时状态源

`docs/CURRENT_STATE.md` 是项目**唯一完整实时状态 owner**。完整构建状态、当前 blocker、测试数、R8 余量、下一步和最近验证证据只在这里维护。

其他入口只引用或摘要：

- `README.md` / `README.en.md`：对外介绍 + 简短状态摘要；
- `docs/HANDOFF.md`：5 分钟接手流程、规则入口、当前唯一优先级；
- `docs/PLAN.md`：仅未完成路线、顺序与完成条件；
- `docs/README.md`：文档分类、生命周期与导航；
- `AGENTS.md`：强制项目规则，不保存动态构建快照；
- `docs/orchestration/CHARTER.md`：编排协议，不保存动态项目快照；
- `docs/orchestration/STATE.md`：仅保存活跃 worker/queue/编排状态，项目技术状态链接 `CURRENT_STATE`；
- `docs/PITFALLS.md`：可复用经验，不保存当前错误数；
- ADR：有效架构决策，仅在决策变化时更新或新增。

### 2. 生命周期分类

| 类别 | 文档 | 维护规则 |
|---|---|---|
| 持续维护 | `CURRENT_STATE`、`HANDOFF`、`PLAN`、双语 README、`docs/README` | 按各自 owner 的触发条件更新；不复制完整状态 |
| 规则与有效决策 | `AGENTS`、`CHARTER`、`docs/adr/**` | 只在规则、流程或决策变化时更新 |
| 追加型记录 | `docs/orchestration/log.md`、`docs/GRADLE_MIGRATION_LOG.md` | 只追加，不改写历史证据 |
| 冻结历史快照 | 已完成 issues、architecture 调研/audit、Superpowers specs/plans、orchestration tasks | 完成后原地保留；不为追随当前状态而重写 |

### 3. Audit 边界

- 已完成的 audit 是冻结历史快照，即使数字后来变化，也不回写成当前值。
- 只有文档头明确标记 `Lifecycle: Active operational audit` 且 bounded audit 尚未关闭时，才可继续更新其**审计域内 ledger**；它仍不得成为全项目状态源。
- 当前 `2026-08-20-r8-runtime-closure-audit.md` 可在 R8 closure 归零前作为 active operational audit 维护 class mapping；完整实时结论仍由 `CURRENT_STATE` owner。
- audit 关闭后改为 frozen；后续新问题建立新 issue/audit，不改写旧结论。

### 4. 保守整理与删除准则

本次不大规模移动历史文件，不按目录美观重排，也不批量给历史文件加 header。删除文档必须同时满足：

1. 内容完全重复或为无内容的生成副本；
2. 没有独立决策、证据、时间线或 handoff 价值；
3. 全仓无有效 inbound link，或链接已先迁移；
4. 删除理由与证据记录在本 issue；
5. reviewer 可独立复核。

只要存在疑问就保留。本次预期**不删除历史文档**；worker 如发现候选，仅列清单，不得自行删除。

### 5. 索引结构

`docs/README.md` 按职责导航，而不是列出所有日期文件：

1. Start here：README → HANDOFF → AGENTS → CURRENT_STATE → PLAN；
2. Live owners：五个持续维护文档及各自职责；
3. Rules and decisions：AGENTS、CHARTER、ADR；
4. Active operational records：orchestration STATE/log、仍 active 的 bounded audit；
5. Historical archives：issues、architecture、Superpowers、orchestration tasks，按目录入口 + 少量精选里程碑；
6. Tooling reference：当前有效 Python 工具。

### 6. 维护触发条件

- merge 改变 build/test/blocker/toolchain/current next step → 更新 `CURRENT_STATE`；
- 接手步骤、强规则入口或当前唯一优先级变化 → 更新 `HANDOFF`；
- 未完成路线、顺序或完成条件变化 → 更新 `PLAN`；
- 对外里程碑显著变化 → 同步双语 README 的短摘要；
- 分类、owner、ADR 或关键入口变化 → 更新 `docs/README`；
- 强制规则变化 → 更新 `AGENTS`；编排协议变化 → 更新 `CHARTER`；
- 出现可复用根因/防错经验 → 更新 `PITFALLS`；
- 编排事件/迁移里程碑 → 分别追加 orchestration log / migration log；
- frozen 文档不因当前状态变化而更新，只允许纠正明确 typo/provenance，且注明更正原因。

## Task 039 固定事实

| 项目 | 已验证事实 |
|---|---|
| Debug | `:app:assembleDebug` SUCCESS；每批硬门禁 |
| Python tests | 179/179 |
| R8 轨迹 | 140→126→119→109→106→88→81 |
| 剩余 81 | SettingsLib 74 + B1–B4 platform/build classpath 6 + `AssumeTrueForR8` 1 |
| Release R8 | 仍因真实 closure 缺失失败；非成功状态 |
| `shrinkResources` | 尚未完成有效验收 |
| Device/emulator | 尚未开始运行验证 |
| 下一顺序 | SettingsLib → B1–B4 → `AssumeTrueForR8` → release R8/shrink/sign → device |

证据：`docs/orchestration/STATE.md`、`docs/orchestration/log.md`、Task 038 issue，以及 main fresh logs `/tmp/task038-main-*`。

## 实施范围

### 核心重写

- `docs/CURRENT_STATE.md`
- `docs/HANDOFF.md`
- `docs/PLAN.md`
- `docs/README.md`

### 去重与职责校准

- `AGENTS.md`：移除动态“当前进度状态”快照，保留规则、架构约束、诊断流程、用户偏好，并链接 `CURRENT_STATE`；
- `docs/orchestration/CHARTER.md`：用 `CURRENT_STATE` 链接替代 Part 6 动态快照；
- `docs/orchestration/STATE.md`：仅保留活跃 worker、近期 queue 和 `CURRENT_STATE` 链接，移除长期技术状态复制；
- `docs/PITFALLS.md`：删除“当前错误数”式状态，只保留可复用经验；
- `docs/GRADLE_MIGRATION_LOG.md`：在顶部追加近期里程碑，历史内容不改写。

### 不在本次改写

- 双语 README 已由架构师同步为 179/81，只做只读一致性验收；
- ADR、已完成 issue/audit/spec/plan/task 不批量修改；
- orchestration log 只由架构师按事件追加；worker 不改；
- 源码、资源、Gradle、工具和二进制产物均不改。

## 验收

1. `CURRENT_STATE` 是唯一包含完整实时技术状态的文档；
2. AGENTS/CHARTER 不再包含动态构建快照；STATE 只保留编排态；
3. HANDOFF 可在 5 分钟内指向正确规则、状态、计划和当前任务；
4. PLAN 只描述未完成路线和完成条件；
5. docs/README 明确生命周期、owner、audit 边界、删除准则和维护触发条件；
6. PITFALLS 不维护当前错误数；迁移日志保留历史并追加 2026-08-19/20 摘要；
7. 历史文件不移动、不批量重写、不删除；
8. 本地 Markdown 链接检查、陈旧现状扫描、职责去重检查和 `git diff --check` 通过；
9. 不运行 Gradle，不生成构建产物。

## 错误数与状态演变

- 刷新前：核心文档仍出现 APK 未生成、131 tests、SettingsLib switch drawable blocker 等旧现状。
- 当前事实：debug 成功、179 tests、R8 81。
- 文档任务不运行构建；数字来自已完成的 main fresh verification。

## 待解决问题

- SettingsLib 74 refs 的实现方案属于下一 bounded build task，不在本任务设计。
- frozen 历史文档中出现旧数字是合法历史；只有把它误当当前入口时才需要修导航。
- 删除候选若不能满足五项准则，本次一律保留。
