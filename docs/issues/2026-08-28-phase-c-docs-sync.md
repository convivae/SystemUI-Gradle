# Task 072b — Phase C 文档同步（CURRENT_STATE / HANDOFF / PLAN / README）

**日期**：2026-08-28
**任务**：`docs/orchestration/tasks/072b-phase-c-docs-sync.md`
**性质**：纯文档刷新，无代码/构建改动。**本任务未运行任何构建（gradle/pytest 均禁跑：另一 worker task073 正在同一 checkout 做 C4b 编译闭环，避免 daemon 争用）。**

## 背景

Phase C 已推进过半，但四大文档仍停留在 16 时代（AOSP main 快照）双 runtime 闭环的状态描述。
本次把四文档刷新到 Phase C 事实，如实记录 **C4b（`:app:assembleDebug` 编译闭环）进行中、
17 重对齐后构建尚未恢复绿**——不写成构建已通过。

## 事实核对表（逐项与事实源核对）

| 事实 | 数值/结论 | 来源 |
|---|---|---|
| AOSP 基线 | `android-17.0.0_r1`，manifest `5bc9a7ce`，frameworks/base `94b4c163b`，1084 projects | log.md 2026-08-27 Phase C 条目；ADR 0007 |
| C1 全量构建 | `m -j16`（GOMEMLIMIT=24GiB + 32G swap）2h35m；soong_build 分析 OOM 根因（26G 单进程） | log.md 2026-08-27 |
| C3（task070） | `--strict` exit 0；MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；MODIFIED 1（CONV_MOD 白名单 kt）+ RES-MODIFIED 86（CONV_DEL 白名单 res-product）；5806 处非 default 变体重标（tv/tablet/device/desktop）；9 commits 已 push | `docs/issues/2026-08-27-c3-source-realignment-execution.md` |
| C2（task071） | libs/ 104 文件全删 → 7 脚本再生 102 文件（全部脚本产出，无手工）；漂移 9 identical / 47 drifted / 48 gone / 46 new；maven 全族 2.0.0（23 族）；退役 `motion_tool_lib.jar`、`settingslib-selector-flags.jar`；aconfig family 14→12（合并 jar 60 类；security/quickaccesswallet/selector-flags 上游删除）；6 族改 framework-minus-apex 聚合分片抽取 | `docs/issues/2026-08-27-c2-libs-regen-17.md` |
| C4a（task072） | 16-module 拓扑（新增 `:SystemUI-application`/`:SystemUI-clocks-common`/`:SystemUI-accessibility-floatingmenu-res`）；catalog 23 族 2.0.0 + jsr330；core −motion_tool_lib −settingslib-selector-flags +surfaceeffects×3 +uilatencystats-flags；SystemUI-res +floatingmenu +wmshell +dynamiccolors（直接 AAR）；core namespace→`com.android.systemui.core`；`:app` 最小 manifest 壳；`./gradlew help`+`projects` BUILD SUCCESSFUL；`--strict` exit 0；pytest 293 passed（+111 subtests） | `docs/issues/2026-08-28-c4-gradle-wiring.md`；log.md 2026-08-28 评审收口条目 |
| C4b（task073） | 进行中：目标 `:app:assembleDebug` BUILD SUCCESSFUL；P0 `:SystemUI-utils-kairos` 源码模块已提交（commit `4ac49993`）；预期错误面见 task072 issue §6 | `docs/orchestration/tasks/073-c4b-debug-compile-closure.md`；git log |
| 16 时代历史 APK 台账 | Debug `e8aad131…`（163,896,493 B，2026-08-25）；Release `d3968fb2…`（34,688,965 B，2026-08-26）——均为 AOSP main 快照（16 时代）产物，Phase C 后属历史 | log.md task058/065 条目 |
| 当前 libs/ 实测 | 30 根 jar + 30 aar + 23 maven AAR + 23 POM + 1 prebuilts = 107 文件（C2 102 + C4a 新 5） | `find libs -type f` 实测 107（本次只读核对） |
| 模块实测 | settings.gradle.kts 当前 17 个 include（C4a 16 + task073 P0 已加 `:SystemUI-utils-kairos`） | `grep include settings.gradle.kts`（只读） |
| SysUISdk 现状 | live `android-SysUISdk` 仍为 16 时代产物（android.jar 2026-08-21 生成）；AOSP-17 八输入已验存，重建排在 C5 前 | task071 brief §「build_sysuisdk.py 不在本任务」；SDK 目录 mtime 实测 |
| 模拟器现状 | 当前无 QEMU/emulator 进程在跑（`pgrep -af qemu\|emulator` 无输出）；C5 将按 runbook 重拉 17 镜像 | 本次只读实测；`docs/issues/2026-08-26-emulator-relaunch-runbook.md` |
| 后续路线 | C4b（进行中）→ task074（Release/R8 闭环）→ C5（17 镜像模拟器双 runtime 门）→ C6（manifest 快照 + tag + README 版本声明，ADR 0007） | task072b brief；ADR 0007 |

## 本次文档改动清单

| 文档 | 改动 |
|---|---|
| `docs/CURRENT_STATE.md` | 头部 Last verified/摘要、TL;DR、里程碑表追加 Phase C 四行、构建验证矩阵重写为 17 现状、模块拓扑 13→16（+kairos 进行中标注）、依赖产物清单重写（107 文件/2.0.0/退役族）、Release closure 标注 16 时代历史、Next ordered work 重排为 Phase C 余项、验证证据段区分当前/历史 |
| `docs/HANDOFF.md` | 头部摘要、§1 第 5 条优先级改 Phase C、§1.1 标注 16 时代回顾、§2 libs 说明加 C4b 注记 |
| `docs/PLAN.md` | 当前路线重排：C1/C3/C2/C4a 勾掉，剩 C4b（进行中）/task074/C5/C6；已完成工作段落同步 |
| `README.md` / `README.en.md` | 轻触：状态速览表（16 时代 runtime 标注历史 + 当前 Phase C 进行中）、模块拓扑 13→16、AOSP 基线段（已固定 `android-17.0.0_r1`，tag 收口归 C6）、Quickstart 状态标注（2/3/5/7 步区分 16 时代已验证与 17 重验进行中）、pytest/产物计数更新 |

## 错误数演变

不适用（纯文档任务，无构建）。

## 验收

- [x] 四文档 + 本 issue 更新完毕，数字逐项与事实源核对（见上表）
- [x] git 仅含本任务文件的单一 commit，`git log -1 --stat` 核对无越界文件
- [x] 未运行任何构建（本任务不需要；gradle/pytest 被禁）

## 待解决问题

- 无。发现的所有事实矛盾均已消除；STATE.md/log.md 归 task073 与 architect，本任务未触碰。
