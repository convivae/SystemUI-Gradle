# SystemUI-Gradle 文档索引与生命周期 (docs/README.md)

> **Owner**: 本文件定义文档分类、生命周期、owner、维护触发与导航。
> **实时技术状态唯一见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)**；本文件不复制构建数字。
> **最后更新**: 2026-08-20（Task 039 文档治理）

---

## Start here（新 AI 阅读顺序）

1. [`docs/HANDOFF.md`](./HANDOFF.md) — 5 分钟接手流程与红线速查
2. [`../AGENTS.md`](../AGENTS.md) — 全部强制项目规则（必读）
3. [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) — 唯一完整实时技术状态
4. [`docs/PLAN.md`](./PLAN.md) — 未完成路线与完成条件
5. （编排参与者加读）[`docs/orchestration/CHARTER.md`](./orchestration/CHARTER.md) → [`docs/orchestration/STATE.md`](./orchestration/STATE.md) → [`docs/orchestration/log.md`](./orchestration/log.md) 尾部

## Live owners（持续维护文档）

| 文档 | 职责 | 更新触发 |
|------|------|---------|
| [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) | **唯一完整实时技术状态**（构建矩阵、版本、依赖产物、blocker、下一步、验证证据） | merge 改变 build/test/blocker/toolchain/当前下一步 |
| [`docs/HANDOFF.md`](./HANDOFF.md) | 5 分钟接手流程、规则入口、当前唯一优先级 | 接手步骤、规则入口或唯一优先级变化 |
| [`docs/PLAN.md`](./PLAN.md) | 仅未完成路线、顺序与完成条件 | 路线、顺序或完成条件变化 |
| [`README.md`](../README.md) / [`README.en.md`](../README.en.md) | 对外介绍 + 简短状态摘要（双语） | 对外里程碑显著变化 |
| `docs/README.md`（本文件） | 文档生命周期、owner、导航 | 分类、owner、ADR 或关键入口变化 |

## Rules and decisions（规则与有效决策）

- [`../AGENTS.md`](../AGENTS.md) — 强制规则 P/S/C/F/R/B/H/D/I、依赖三层策略、SysUISdk 规则、诊断流程、用户偏好。**不保存动态进度**；实时状态见 CURRENT_STATE。
- [`docs/orchestration/CHARTER.md`](./orchestration/CHARTER.md) — herdr 编排协议（十规则、依赖决策树、串行构建、红线、worker contract）。不保存动态项目快照。
- [`docs/adr/`](./adr/) — ADR 0001–0005：res 处理优先级 / Python-only 工具 / bp 语义对齐 / CONV 标记 / SettingsLib POM 传递依赖。仅在决策变化时更新或新增。

## Append-only records（追加型记录）

- [`docs/orchestration/log.md`](./orchestration/log.md) — 编排事件流水（只由架构师按事件追加）。
- [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) — 迁移里程碑与错误数历史（只追加，不改写旧条目）。

## Active operational records（活跃运营记录）

- [`docs/orchestration/STATE.md`](./orchestration/STATE.md) — 仅活跃 worker / queue / 编排 transition；技术状态链接 CURRENT_STATE。
- **Active operational audit 定义**：文档头明确标记 `Lifecycle: Active operational audit` 且 bounded audit 尚未关闭的审计文档，可继续更新其**审计域内 ledger**，但不得成为全项目状态源。当前唯一实例：[`docs/architecture/2026-08-20-r8-runtime-closure-audit.md`](./architecture/2026-08-20-r8-runtime-closure-audit.md)（R8 closure 归零前维护 class mapping）。audit 关闭后改 frozen；新问题建新 issue/audit，不改写旧结论。

## Historical archives（冻结历史归档）

完成后原地保留，**不因当前状态变化而重写**；旧数字是合法历史快照。只允许纠正明确 typo/provenance 且注明原因。

| 目录 | 内容 | 精选里程碑 |
|------|------|-----------|
| [`docs/issues/`](./issues/) | 每日问题/任务记录 | 2026-08-19 SettingsLib per-target AARs、2026-08-20 R8 Batch 1–4C 系列、2026-08-20 官方 Maven 审计 |
| [`docs/architecture/`](./architecture/) | 深度调研与 audit | 2026-08-06 module-structure-audit、2026-08-13 sysuisdk-reproducible-build |
| [`docs/superpowers/`](./superpowers/) | specs 与 plans | 按任务配套 |
| [`docs/orchestration/tasks/`](./orchestration/tasks/) | 已派发任务 brief | Task 031 R8 closure audit、Task 038 Traceur |
| [`docs/audit-2026-07-30-aosp-src-parity.md`](./audit-2026-07-30-aosp-src-parity.md) / [`docs/mapping-2026-07-30-aosp-bp-to-gradle.md`](./mapping-2026-07-30-aosp-bp-to-gradle.md) | 早期对齐审计与 bp 映射 | — |
| [`docs/PITFALLS.md`](./PITFALLS.md) | 可复用踩坑经验（**不维护当前错误数**，实时状态见 CURRENT_STATE） | — |

## 删除准则（五项须同时满足，本次未删除任何文档）

1. 内容完全重复或为无内容的生成副本；
2. 没有独立决策、证据、时间线或 handoff 价值；
3. 全仓无有效 inbound link，或链接已先迁移；
4. 删除理由与证据记录在对应 issue；
5. reviewer 可独立复核。

**有疑问即保留。** 移动/重排历史文件同样不在常规维护范围内。

## 维护触发条件表

| 事件 | 更新对象 |
|------|---------|
| merge 改变 build/test/blocker/toolchain/当前下一步 | CURRENT_STATE |
| 接手步骤、规则入口、当前唯一优先级变化 | HANDOFF |
| 未完成路线、顺序、完成条件变化 | PLAN |
| 对外里程碑显著变化 | 双语 README 短摘要 |
| 分类、owner、ADR、关键入口变化 | docs/README |
| 强制规则变化 | AGENTS |
| 编排协议变化 | CHARTER |
| 可复用根因/防错经验 | PITFALLS |
| 编排事件 / 迁移里程碑 | orchestration log / migration log（追加） |
| frozen 文档 | 不更新（仅 typo/provenance 更正并注明） |

## Tooling reference（当前有效 Python 工具，ADR 0002）

| 工具 | 用途 |
|------|------|
| [`../tools/build_sysuisdk.py`](../tools/build_sysuisdk.py) | 从 tracked inputs 从零重建 SysUISdk（`--apply` 落盘） |
| [`../tools/package_aosp_aar.py`](../tools/package_aosp_aar.py) | 从 AOSP Soong 产物打包确定性 AAR 到 `libs/aars/` |
| [`../tools/install_aar_to_maven.py`](../tools/install_aar_to_maven.py) | 安装 AAR 到 `libs/maven/` 本地 Maven 仓（AAR + POM 骨架） |
| [`../tools/package_aconfig_jars.py`](../tools/package_aconfig_jars.py) | 从 AOSP javac 产物打包完整 aconfig runtime JAR |
| [`../tools/package_compilelib_jars.py`](../tools/package_compilelib_jars.py) | 打包 compilelib debug/release JAR |
| [`../tools/package_monet_jar.py`](../tools/package_monet_jar.py) / [`../tools/package_viewcapture_motiontool_jars.py`](../tools/package_viewcapture_motiontool_jars.py) | 确定性 clean JAR（monet / view-capture / motion-tool） |
| [`../tools/check_source_alignment.py`](../tools/check_source_alignment.py) | AOSP src/AIDL/res 对齐校验（规则 C） |
| [`../tools/install_sdk.py`](../tools/install_sdk.py) | 校验 + 补 SysUISdk framework.aidl |
| [`../tools/patch_androidprv_merged_resources.py`](../tools/patch_androidprv_merged_resources.py) | AGP `androidprv` namespace 丢失修复 |
| [`../tools/markup_product_variants.py`](../tools/markup_product_variants.py) | res-product `product=` 变体 CONV 标记 |

单元测试：`python3 -m unittest discover -s tools/tests -p 'test_*.py'`（当前通过数见 CURRENT_STATE）。

## 快速搜索

- "项目规则是什么？" → [`AGENTS.md`](../AGENTS.md) §1–§2
- "现在构建状态如何？" → [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)
- "下次该做什么？" → [`docs/PLAN.md`](./PLAN.md)
- "为什么不能用 Kotlin 2.3.x / Compose 1.12？" → [`docs/PITFALLS.md`](./PITFALLS.md) §1.1/§1.6
- "builtInKotlin 下 KSP/AIDL 怎么配？" → [`docs/PITFALLS.md`](./PITFALLS.md) §1.5
- "我能加 stub 吗？" → 不能，`AGENTS.md` §1.2（规则 P）
- "错误数变化历史？" → [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md)
- "哪些方案试过失败？" → [`docs/PITFALLS.md`](./PITFALLS.md) 全文
