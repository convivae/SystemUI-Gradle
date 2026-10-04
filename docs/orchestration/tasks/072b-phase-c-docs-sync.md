# Task 072b — Phase C 文档同步（CURRENT_STATE / HANDOFF / PLAN / README）

## 背景

Phase C 已推进过半，但四大文档仍停留在 16 时代双 runtime 闭环的状态描述：
- C1 完成：AOSP 升级 `android-17.0.0_r1` + 全量编译成功（2h35m，frameworks/base `94b4c163b`）
- C3 完成（task070）：源码 17 重对齐，`--strict` exit 0；新基线 src 1989 files / res 577 files（MODIFIED 1 src + 86 res 为白名单/CONV）
- C2 完成（task071）：`libs/` 104 文件全删后仅凭 7 个 tools 脚本从 AOSP-17 再生（102 文件 byte-identical/drifted 四类核对）；maven 全族坐标 2.0.0；`motion_tool_lib.jar`、`settingslib-selector-flags.jar`、`settingslib-selector-flags` 族、`quickaccesswallet-flags` 族、`security-flags` 族退役；aconfig 12 族（6 族改 framework-minus-apex 聚合分片抽取）；pytest 290+ passed
- C4a 完成（task072，review-PASS）：16-module 拓扑（新增 `:SystemUI-application`/`:SystemUI-clocks-common`/`:SystemUI-accessibility-floatingmenu-res`）、catalog 23 族 2.0.0、surfaceeffects×3 jar + uilatencystats-flags + dynamiccolors AAR 新产物、`:app` 最小 manifest 壳、core namespace→`com.android.systemui.core`、`./gradlew help`/`projects` 绿
- C4b 进行中（task073，另一 worker 正在 main checkout 编译闭环 assembleDebug；**不要动它的工作文件**）
- 后续：task074（Release/R8 闭环）→ C5（17 镜像模拟器双 runtime 门，runbook `docs/issues/2026-08-26-emulator-relaunch-runbook.md`）→ C6（manifest 快照 + tag + README 版本声明；ADR 0007）

## 任务

把以下四个文档刷新到上述事实（保留各文档自身结构，只更新过时内容；如实记录"当前 assembleDebug 尚未恢复绿、C4b 进行中"——**禁止**写成构建已通过）：

1. `docs/CURRENT_STATE.md` — 唯一实时状态 owner：构建矩阵（debug/release=进行中/未跑，16 时代 APK sha 台账标注为历史）、依赖产物清单（16-module 拓扑、libs 新产物、maven 2.0.0、退役族）、验证门现状（pytest 293 passed、对齐 strict 0、gradle help 绿）、blocker、下一步
2. `docs/HANDOFF.md` — 5 分钟概要入口：Phase C 主线、当前 C4b 进行中、新 AI 必读顺序不变
3. `docs/PLAN.md` — 未完成路线：勾掉 C1/C3/C2/C4a，剩 C4b（进行中）/task074/C5/C6
4. `README.md` / `README.en.md` — 仅更新与现状直接矛盾的句子（如模块数、AOSP 版本描述）；大改版留给 C6（tag 收口时统一声明版本）——本次**轻触**

事实来源（只读，用于交叉核对）：`docs/orchestration/STATE.md`、`docs/orchestration/log.md`、`docs/issues/2026-08-27-c3-source-realignment-execution.md`、`docs/issues/2026-08-27-c2-libs-regen-17.md`、`docs/issues/2026-08-28-c4-gradle-wiring.md`、`docs/adr/0007-phase-c-clean-regen-release-tag.md`。引用数字时以这些文档为准，不确定就去读，不要编造。

## Global Constraints

- **另一 worker 正在同一 checkout 做 task073**：禁止跑任何 gradle/pytest（daemon 争用）；commit 时只 `git add` 你自己改的文件路径，**严禁 `git add -A` / `git add .`**；commit 前先 `git status` 确认没有把别人的工作文件带进来。
- 单次 commit，英文 message，不 push。
- AOSP 树只读。

## File Map

- 读写：`docs/CURRENT_STATE.md`、`docs/HANDOFF.md`、`docs/PLAN.md`、`README.md`、`README.en.md`、新建 `docs/issues/2026-08-28-phase-c-docs-sync.md`（规则 D：先写 issue 记录本次文档改动清单）
- **禁改**：`AGENTS.md`、`docs/orchestration/*`（STATE.md 归 task073 worker）、`tools/`、`libs/`、所有 `SystemUI-*/`、`gradle/`、worker task073 的一切文件

## 验收

- 四文档 + issue 更新完毕，与事实源零矛盾（数字逐项核对）。
- git 仅含本任务文件的单一 commit；`git log -1 --stat` 核对无越界文件。
- 未运行任何构建（本任务不需要）。

## 五字段

- **Authority**: self-commit；never push；发现事实源之间矛盾 → 停下报告 chief
- **Allowed Paths**: 上列读写清单 + `/tmp/072b/`
- **Forbidden Paths**: `AGENTS.md`、`docs/orchestration/**`、`tools/**`、`libs/**`、`SystemUI-*/**`、`gradle/**`、`app/**`、git push、任何 gradle/pytest 命令、`git add -A`/`git add .`
- **Acceptance**: 文档与事实源一致 + 单一干净 commit
- **Reports To**: chief（herdr agent `docsync`）

## 模型

joycode GLM-5.2（文档任务无需 5.3）。
