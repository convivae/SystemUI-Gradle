# task072/073 决策审计 — 索引（audit01）

> 任务 brief: `docs/orchestration/tasks/audit01-decision-audit.md`
> 只读调研；不改任何代码。本目录是唯一输出。
> 判读三档：符合 / 可接受但需补记录 / 与规则冲突建议重做。

## Resume 速查（冷启动 5 分钟恢复）

1. **先读本文件**（本页）→ 看状态表找到下一个 `not-started`/`doing` 行 → 直接做那一项。
2. 关键背景源（只读引用源，全部已确认存在）：
   - 两篇 issue：`docs/issues/2026-08-28-c4-gradle-wiring.md`（task072）、`docs/issues/2026-08-28-c4b-debug-compile-closure.md`（task073）
   - 两份 brief：`docs/orchestration/tasks/072-c4-gradle-wiring.md`、`docs/orchestration/tasks/073-c4b-debug-compile-closure.md`
   - commit 范围：`git log --oneline 452c9f6c..HEAD`；task070 相关：`git log --grep task070 --oneline`
   - ADR：`docs/adr/`；规则：`AGENTS.md`；AOSP 树：`/home/conv/myspace/aosp`（只读）
   - 参考项目：`/home/conv/myspace/CarSystemUIGradle`（重点 `docs/GRADLE_MIGRATION.md`、`docs/DEPENDENCIES.md`）
3. **每完成一个决策文档**：
   - 更新本页对应行 status → done + 一句话预结论；
   - `git add docs/architecture/2026-08-29-decision-audit/<doc>.md docs/architecture/2026-08-29-decision-audit/index.md`（**显式路径**，禁止 `git add -A`/`git add .`）；
   - 小步英文 commit（如 `audit01: audit doc for D2 (manifest package attr strip)`）。
4. 进度跟踪：已完成 = `1/19` 中的数字见状态表 done 计数。
5. 临时 scratch 目录：`/tmp/audit01/`（命令输出留存，可删）。
6. 若遇新可疑决策 → 写入下方"发现的额外问题"节，不展开。

## 状态表

| # | 决策 | 文档 | status | 一句话预结论 | 关键证据指针 |
|---|------|------|--------|--------------|--------------|
| D1 | res-product config.xml 三变体 CONV_DEL（用户授权 commit 02e60a60） | d01-config-xml-conv-del.md | not-started | | commit 02e60a60；task073 issue §6 |
| D2 | application manifest 剥 package 属性（task072 80be3e58） | d02-manifest-package-strip.md | not-started | | commit 80be3e58；task072 brief §3；task072 issue §3.3 |
| D3 | application manifest 剥 featureFlag 属性（泛授权，未单独报 user） | d03-manifest-featureflag-strip.md | not-started | | task073 issue §4 批次2/§6；commit 内查 |
| D4 | clocks-common/floatingmenu manifest 保留 package 属性 | d04-manifest-package-keep.md | not-started | | task072 issue §3.3 对账表 |
| D5 | kairos → tier① 源码模块 :SystemUI-utils-kairos | d05-kairos-source-module.md | not-started | | commit 4ac49993；bp utils/kairos/Android.bp；AGENTS.md §3.1 旧文 |
| D6 | ace 拆双 AAR（common jar 并入 visualizer） | d06-ace-dual-aar.md | not-started | | task073 issue §3；commit e6c59677 |
| D7 | wmshell-shared AAR 并入 AIDL 闭包 19 类，2.0.0→2.0.1 | d07-wmshell-shared-aidls.md | not-started | | task073 issue §4 批次1 |
| D8 | aapt2 编译期转发 --feature-flags + systemui-aconfig-flags.txt | d08-aapt2-feature-flags.md | not-started | | task073 issue §4 批次2；commit 6e66a0ea |
| D9 | dynamiccolors 走 Task 059 直接 AAR 例外（清单 +1） | d09-dynamiccolors-direct-aar.md | not-started | | task072 issue §2/§3.4；commit 452c9f6c |
| D10 | mechanics×2 jar + SerialPortAccessDialog AAR | d10-mechanics-serial-artifacts.md | not-started | | task073 issue §3 |
| D11 | core namespace com.android.systemui → com.android.systemui.core | d11-core-namespace-rename.md | not-started | | task072 issue §3.1；commit d1352d5d |
| D12 | 生成器碰撞裁决（UnsupportedAppUsage turbine vs javac 字节）——当前挂起 | d12-sysuisdk-bridge-collision.md | not-started | | task073 issue §4 剩余阻塞 1 |
| P1 | task072/073 brief 把 CONV 权限泛授权给 worker | p01-conv-blanket-authorization.md | not-started | | 两 brief File Map/Forbidden Paths；ADR 0004 |
| P2 | chief 评审接受 worker 自判项未先报用户 | p02-chief-review-escalation.md | not-started | | review log eb135b98；规则 H |
| P3 | worker brief 外扩范围（ace 双 AAR、wmshell 2.0.1） | p03-worker-scope-drift.md | not-started | | commit e6c59677 / 38cd4c4b vs brief |
| E1 | Task 050：79 处 manifest FQCN 手工改写先例 | e01-task050-fqcn-rewrites.md | not-started | | docs/tasks/050 相关 issue；commit grep |
| E2 | Task 059：直接 AAR 例外清单原始授权范围 | e02-task059-direct-aar-exception.md | not-started | | AGENTS.md §3.2 例外段；task059 文档 |
| E3 | Task 070：5806 处 strings.xml CONV 标记授权链 | e03-task070-strings-conv.md | not-started | | task070 相关 commit/issue |
| E4 | 13-module → 16-module 拓扑演变 | e04-module-topology-evolution.md | not-started | | docs/architecture/2026-08-06-module-structure-audit.md；AGENTS.md §3.1 |

## 发现的额外问题（台账外）

（空 — 主清单调研中如发现再填）

## 总评

见 `summary.md`（最后写）。

## 完成验收笔记

- [ ] 19 决策文档 + index + summary 齐全，status 全 done
- [ ] 抽查结论可回溯证据（文件:行号 / 命令输出 / commit hash）
- [ ] 本目录外零代码改动；小步 commit 串
</content>
