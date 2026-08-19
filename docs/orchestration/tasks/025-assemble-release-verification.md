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
