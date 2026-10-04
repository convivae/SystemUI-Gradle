# Task 025 — assembleRelease 验证 + 诊断（不修复）

## Goal

首次验证 release 变体（用户 2026-08-19 批准）。范围限定：**验证 + 诊断，不修复**。

## 步骤

1. 基线确认：`./gradlew :app:assembleDebug` 应成功（对照组）；
2. `./gradlew :app:assembleRelease`：
   - **成功** → 记录 APK 路径/大小/SHA-256，收工；
   - **失败** → 定位首个失败任务，收集完整错误，按 systematic-debugging 归组根因，
     写诊断报告；**不做任何修复尝试**；
3. `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（148 基线）。

## 已知背景（免重复调研）

- release 签名：platform.keystore 已就位（keystore/platform.keystore），debug/release 共用；
- core `isMinifyEnabled = false`，release 不跑混淆；
- release 专有输入：`SystemUI-core/src-release/`、`libs/compilelib-release.jar`；
- KSP/AIDL release 接线已配置（`kspReleaseKotlin → compileReleaseAidl`）。

## Non-goals

- 不修任何构建/源码问题；
- 不改版本、配置、依赖。

## Allowed Paths

- `docs/issues/2026-08-20-assemble-release-verification.md`（新建）
- `docs/orchestration/tasks/025-assemble-release-verification.md`（本文件勾选）

## Forbidden Paths

其它一切（纯验证 + 文档）。

## Acceptance

- issue 文档含：debug 对照结果、release 结果（成功产物信息 或 失败首任务 + 错误原文 + 根因归组）、测试基线
- 英文 commit；不 push

## Report

完成后汇报：commit、release 构建结论、（若失败）根因清单、issue 更新、HANDOFF 块。

---

## Completion Status (worker 025, 2026-08-20)

- [x] **步骤 1（基线确认）** `./gradlew :app:assembleDebug` → `BUILD SUCCESSFUL in 2m 5s`（216 actionable tasks）。控制组成立。
- [x] **步骤 2（assembleRelease）** → 失败分支。首次运行：守护进程于 `compileReleaseJavaWithJavac` 被 OOM-kill（journalctl 铁证，环境性）；清理残留 JVM 后重跑：首个失败任务 `:SystemUI-core:mergeReleaseConsumerProguardFiles`，错误 `Supplied consumer proguard configuration does not exist: .../SystemUI-core/consumer-rules.pro`。按 systematic-debugging 归组根因 = 构建配置缺陷（悬挂 `consumerProguardFiles` 引用，commit `a4bd7f94` 引入但未创建文件）。**未做任何修复尝试**。完整诊断见 `docs/issues/2026-08-20-assemble-release-verification.md`。
- [x] **步骤 3（工具测试基线）** `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 148 tests ... OK`（148 基线一致）。
- [x] **Acceptance — issue 文档** 已建于 `docs/issues/2026-08-20-assemble-release-verification.md`，含 debug 对照、release 失败首任务+错误原文+根因归组、测试基线。
- [x] **Acceptance — 英文 commit，不 push** 见本 worker commit。

### 红线/超出范围（worker 未实施）

- 修复 `consumer-rules.pro` / `proguard-rules.pro` 悬挂引用属构建配置/产物来源红线（CHARTER Part 5），且 brief 明令不改配置；3 个修复方向已记录于 issue §8，交架构师/用户裁定。
