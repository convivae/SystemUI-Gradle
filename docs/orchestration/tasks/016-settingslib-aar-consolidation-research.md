# Task 016 — SettingsLib AAR 数量整合调研（只读）

## Goal

Task 014 的结论是"33 个 res target → 30 个新 per-target AAR"。用户认可方案 B
（POM 传递依赖，ADR 0005），但**认为 30 个 AAR 过多**，要求先调研：
在严格遵守规则 R（资源 byte-exact、不改写不丢弃）的前提下，有哪些把 AAR 数量
降到 30 以下的具体方案，各自的数量、合规性、运行期风险、回滚成本。

产出**一个**结论文档：
`docs/architecture/2026-08-19-settingslib-aar-consolidation-research.md`，
供用户选择实施粒度。

## Non-goals

- 不修改任何代码、构建脚本、资源、依赖版本、AOSP 文件；
- 不实施任何方案；不运行 Gradle 构建；
- 不推翻 ADR 0005（POM 传递依赖是既定决策，本调研只研究 AAR 粒度/数量）。

## Allowed Paths

- `docs/architecture/2026-08-19-settingslib-aar-consolidation-research.md`（新建）
- `docs/issues/2026-08-19-settingslib-aar-consolidation-research.md`（更新结果）
- `docs/orchestration/tasks/016-settingslib-aar-consolidation-research.md`（勾选 checklist）

临时分析脚本只放 /tmp，不入仓库。

## Forbidden Paths

其它一切（源码、res、构建脚本、tools/、libs/、AOSP 树、参考项目树）。

## Inputs to Read First

1. `AGENTS.md`、`docs/orchestration/CHARTER.md`
2. `docs/architecture/2026-08-19-settingslib-resource-closure-research.md`（Task 014 结论，
   含 33 target 闭包审计、101 组重复路径、R 类 getstatic 实证——**复用其数据，抽查验证即可，不要从零重做**）
3. `docs/issues/2026-08-19-settingslib-aar-consolidation-research.md`（调研问题清单）
4. `docs/adr/0005-local-maven-transitive-poms.md`
5. AOSP：`frameworks/base/packages/SettingsLib/**/Android.bp`、`AndroidManifest.xml`
6. 本项目：`SystemUI-res/res/**`（资源引用源）、`SystemUI-core/src/**` 与
   `SystemUI-shared/**/src/**` 中对 `com.android.settingslib` 的 import/引用、
   `libs/aars/SettingsLib.aar`、`tools/package_aosp_aar.py`
7. 参考项目：`/home/conv/myspace/CarSystemUIGradle`（塌缩 namespace 的实际运行史）
8. AGP/AAPT2 官方文档或源码（R 类生成、AAR namespace、资源合并顺序）——优先一手来源

## Required Findings

### Q1 最小无冲突分组（定量）

把 33 个 res-owning target 分成**最少组**，使每组内部重复相对路径数为 0
（组 = 一个合并 AAR 的 res 树，文件全部 byte-exact、不改写不丢弃）。

- 给出确切组数 k、每组 target 清单、每组文件数；
- 说明算法（精确求解或 greedy + 完整性验证），并在文档附录给出可复算的清单；
- 变体单独评估：若允许"同名 values XML 内资源条目不相交时合并文件"
  （资源条目 byte-exact 但文件被合成），k 能降到多少？明确标注这是**灰区**
  （文件级合成需扩展打包器，规则 R 解释需用户裁定），不作为默认推荐。

### Q2 R namespace 塌缩的运行期实证（决定合组的代价）

合并 AAR 只有一个 manifest package → AGP 只生成一个 R namespace。
Task 014 已证子模块字节码以 `getstatic` 引用**子包** R（如
`com.android.settingslib.widget.preference.twotarget.R$id`）。

- 从 SystemUI 源码实证：SystemUI（core/shared/res）实际 import / 实例化 /
  在布局中引用了哪些 `com.android.settingslib.*` 类？这些类各引用哪个子包 R？
- 结论形式：一张"塌缩后确定会炸 / 可能炸 / 不会炸"的类清单（含证据行号）；
- 评估参考项目的证据强度：Car SystemUI 塌缩运行未炸（除 WifiTrackerLib），
  其 SettingsLib 使用面与本项目的差异是什么？

### Q3 可达性最小集（定量）

从 `SystemUI-res/res/**`、`SystemUI-compose*`、`SystemUI-core/src`、`AndroidManifest`
出发，静态解析资源引用闭包（`@type/name`、`R.type.name`、布局 class 标签、
代码 inflation），回答：链接 + 运行**实际需要**哪些子 target 的资源？

- 给出确切 target 清单与数量 m；
- 明确列出静态分析覆盖不到的引用通道（反射、动态 inflation、resource 名拼接），
  评估漏判风险与暴露方式（链接期报错 vs 运行期崩溃）。

### Q4 AGP/AAPT2 机制（一手来源）

- AAR 是否严格单 namespace（一个 manifest package 一个 R 类）？
- app link 时 library R 类如何获得 final ID（R.txt 驱动？符号必须在该 AAR 自己的
  res/ 里，还是全局资源池里有即可）？
- "R.txt-only AAR"（无 res、只有 manifest + R.txt）能否为对应 namespace 生成正确 R？
  ——若官方文档/AGP 源码无法证实，明确标注"未证实"，不得猜测；
- 多 AAR 资源合并的优先级/覆盖语义（官方文档）。

### Q5 综合方案与推荐

给出 2–3 个 **<30 个新 AAR** 的具体方案，每个含：新 AAR 数量、分组/子集清单、
规则 R/B 合规性、运行期风险（引用 Q2）、回滚成本、与 ADR 0005 POM 传递的接线方式。
至少评估以下形状（可增补）：

- **B1**：Q1 最小无冲突分组（k 个合并 AAR），namespace 塌缩风险按 Q2 结论标注；
- **B2**：Q3 可达性最小集（m 个 per-target AAR），闭包外 target 暂不出 AAR，
  新层暴露时按同模式增补；
- **B3**：混合——少量 res 合并 AAR + 必要的 R-only namespace AAR（取决于 Q4 是否证实）。

最后给**一个**推荐，并说明它如何回应用户"30 太多"的关切。

## Execution Hints

- 先用 worker-contract skill 输出 `CONTRACT:`；
- 用 research skill 的方法（一手来源、引用出处、结论落盘到指定文件）；
- 用 systematic-debugging skill 的方法核对每条链路；
- 分组/引用分析脚本放 /tmp，文档中给出关键清单与计数，使架构师可复算；
- Q2 的 SystemUI 侧证据必须带文件路径与行号。

## Acceptance

- `test -s docs/architecture/2026-08-19-settingslib-aar-consolidation-research.md`
- `rg -n "Q1|Q2|Q3|Q4|Q5|Recommendation|byte-exact|namespace" docs/architecture/2026-08-19-settingslib-aar-consolidation-research.md`
  有实质性命中
- `git diff --check` 干净；只改 Allowed Paths；英文 commit；**不 push**

## Report

完成后汇报：commit、逐条 checklist、issue 更新、新发现、HANDOFF 块。
