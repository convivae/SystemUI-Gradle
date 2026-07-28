# SystemUI-Gradle 文档索引

> **目的**: 让任何 AI Agent 都能快速找到所需文档。
> **最后更新**: 2026-07-28

---

## ⭐ 必读文档 (新 AI 入口)

| 顺序 | 文档 | 说明 |
|------|------|------|
| 1 | [`docs/HANDOFF.md`](./HANDOFF.md) | 5 分钟上手纲要 + 项目概述 |
| 2 | [`../AGENTS.md`](../AGENTS.md) | ⭐ 项目规则（必读） |
| 3 | [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) | 当前状态快照（错误数、阻塞） |

---

## 📋 规则与原则

- [`../AGENTS.md`](../AGENTS.md) - 全局规则、依赖引入、问题排查流程

---

## 📊 现状与计划

- [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) - 当前错误数、分布、已尝试方案
- [`docs/PLAN.md`](./PLAN.md) - 阶段计划（Stage 1-5）
- [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) - 历史问题与演变

---

## ⚠️ 踩坑与调研

- [`docs/PITFALLS.md`](./PITFALLS.md) - 看似简单但实际不行的方案
- [`docs/architecture/`](./architecture/) - 深度调研文档
  - [`STAGE2-3-RESEARCH-LOG.md`](./architecture/STAGE2-3-RESEARCH-LOG.md) - Stage 2-3 根因分析

---

## 🐛 问题记录 (按时间)

| 日期 | 文档 |
|------|------|
| 2026-07-18 | [`docs/issues/2026-07-18-real-framework-jar-migration.md`](./issues/2026-07-18-real-framework-jar-migration.md) |
| 2026-07-22 | [`docs/issues/2026-07-22-framework-jar-replace-and-stubs.md`](./issues/2026-07-22-framework-jar-replace-and-stubs.md) |
| 2026-07-22 | [`docs/issues/2026-07-22-sdk-android-jar-merge.md`](./issues/2026-07-22-sdk-android-jar-merge.md) |
| 2026-07-22 | [`docs/issues/2026-07-22-stub-cleanup-and-deps.md`](./issues/2026-07-22-stub-cleanup-and-deps.md) |
| 2026-07-23 | [`docs/issues/2026-07-23-server-notification-flags-unresolvable.md`](./issues/2026-07-23-server-notification-flags-unresolvable.md) |
| 2026-07-28 | [`docs/issues/2026-07-28-server-flags-debug-session.md`](./issues/2026-07-28-server-flags-debug-session.md) |

---

## 🛠️ 工具脚本

- [`../tools/gen_aar_maven.py`](../tools/gen_aar_maven.py) - AAR 生成脚本（从 CarSystemUIGradle 复制）
- [`../tools/extract_prebuilts.sh`](../tools/extract_prebuilts.sh) - 预编译 jar 提取脚本

---

## 📁 项目根目录

- [`../`](../) - SystemUI-Gradle/
  - [`../build.gradle.kts`](../build.gradle.kts) - 根项目（allprojects 注入）
  - [`../settings.gradle.kts`](../settings.gradle.kts) - 模块配置
  - [`../gradle/libs.versions.toml`](../gradle/libs.versions.toml) - 版本目录
  - [`../libs/`](../libs/) - 自包含依赖

---

## 🔍 快速搜索

### "项目规则是什么？"
→ [`AGENTS.md`](../AGENTS.md) §1, §2

### "现在错误数多少？怎么分布？"
→ [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) §2, §3

### "我能加 stub 类吗？"
→ 不能。`AGENTS.md` §1.2

### "server-notification-flags 怎么修？"
→ [`docs/PITFALLS.md`](./PITFALLS.md) §2 + [`docs/issues/2026-07-28-server-flags-debug-session.md`](./issues/2026-07-28-server-flags-debug-session.md)

### "Compose Scene 怎么办？"
→ [`docs/architecture/STAGE2-3-RESEARCH-LOG.md`](./architecture/STAGE2-3-RESEARCH-LOG.md) §3

### "错误数变化历史？"
→ [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 问题十一

### "哪些方案试过失败？"
→ [`docs/PITFALLS.md`](./PITFALLS.md) 全文

### "下次该做什么？"
→ [`docs/PLAN.md`](./PLAN.md) 各阶段 + [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) §6