# Task 069：SystemUI-17 源码再对齐全景调研（只读）

- 日期：2026-08-27
- 结论与完整分析：`docs/architecture/2026-08-27-sysui17-realignment-panorama.md`（本文只记录过程与问题清单）

## 背景

Phase C（ADR 0007 干净重生成）的 C3 步骤（源码树再对齐到 `android-17.0.0_r1`）开工前，需要一份只读漂移全景：确认规模、归因漂移性质、盘点 bp 结构变化与 CONV 存量、产出批量执行计划与决策点。**本任务不改任何源码/res/Gradle，不跑构建。**

## 执行步骤

1. 读取任务简报与 baseline 计数，运行 `tools/check_source_alignment.py` 提取结构化数据（`/tmp/task069/alignment.json`，临时不入库）——8 项计数与 chief baseline **逐项一致**（MISSING 1963 / MISPLACED 20 / EXTRA 642 / MODIFIED 2222 / APP 0 / RES-MISS 438 / RES-EXTRA 219 / RES-MODIFIED 830）。
2. 用 AOSP git 历史（旧基线 `f0354eeb` 2025-03-26 vs 17 HEAD `94b4c163b7`）对 EXTRA 642 逐文件归因、对 MODIFIED 2222 抽样 150 个做 vintage 字节比对。
3. diff 新旧 `Android.bp`（含子目录 35+ bp），盘点 17 生产 source root 全量 6133 文件与生产图外目录。
4. grep 全库 CONV 标记存量并分类（ADR 0004 class A/B/C）。
5. 汇总成 S4 执行矩阵与 7 个决策点。

## 关键发现（问题清单）

| # | 问题 | 影响 |
|---|---|---|
| 1 | MODIFIED 2222 中 1557 个比 2025-03-26 声称基线更老（最老 2020-10）；EXTRA 642 中 131 个在旧基线前已被 AOSP 删除 | 现有拷贝是多 vintage 拼盘；但抽样 150/150 字节匹配 AOSP 历史 → C3 可机械覆盖 |
| 2 | 17 新增 6 个生产 source root（application/src、log/core/src、plugin_core/annotations/src、shared/flag/*、clocks/common），共 40 个文件在现对齐工具映射之外 | C3 前必须先扩映射，否则"计数归零"验收会漏 |
| 3 | pods 269 个 MISSING 中 50 个是 test/testFixtures/multivalentTests（生产图外） | 照单全收会把测试文件拷进生产树；需改映射排除并重算 baseline（真实缺失 219） |
| 4 | SystemUIShaderLib 移除，surfaceeffects 迁至 `frameworks/libs/systemui/surfaceeffects/` 三库（28 kt） | :SystemUI-animation 的 24 个 EXTRA 即此；需打 AAR 接入 |
| 5 | SystemUI-res static_libs 新增 AccessibilityFloatingMenu-res 等 5 项 | accessibilitymenu 的 res 在生产资源闭包，必须引入 AAR |
| 6 | `res/flag(...)/` 15 个 AAPT2 flag 限定目录文件 + res-product 3 个 fr-rCA 语法变体 | AGP 消费能力未验证，C3 风险点 |
| 7 | 2237 个 CONV_DEL（86 个 res-product strings.xml）+ 2 个 CONV_MOD 全部 class B（17 未吸收，还新增 product="desktop"） | C3 覆盖后须整批重标，不可沿用 |
| 8 | :app manifest 1157 行 vs AOSP 1338 行；proguard_common.flags 50 vs 72 行 | C3 一并替换/更新 |

## 未运行构建

本任务为只读调研，**未运行任何 Gradle 构建**（任务约束）。

## 下一步（移交 chief）

1. 用户对 §5 七个决策点拍板（架构文档）。
2. 先扩 `check_source_alignment.py` 映射（新根 + pods 排 test），重跑并冻结新 baseline。
3. 按 S4 矩阵派发 C3 批量执行（顺序：删 EXTRA → 移 MISPLACED → 拷 MISSING → 覆 MODIFIED → CONV 重标 → manifest/proguard → 重跑对齐工具验收归零）。
