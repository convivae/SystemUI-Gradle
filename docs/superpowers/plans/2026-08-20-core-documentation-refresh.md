# Documentation Information Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目文档整理为“一个完整实时状态源 + 明确生命周期 + 历史原地冻结”的保守信息架构，并清除核心入口中的过期动态状态。

**Architecture:** `docs/CURRENT_STATE.md` 独占完整实时技术状态；其他入口只拥有各自职责并链接该状态。规则文档删除动态快照，orchestration STATE 只保留编排态，历史 issue/audit/plan/task 原地冻结且本次不移动、不删除。

**Tech Stack:** Markdown、Git、Python 3 只读链接检查、ripgrep；禁止 Gradle 和构建产物生成。

**Spec:** `docs/issues/2026-08-20-core-documentation-refresh.md`

## Global Constraints

- 固定事实：debug SUCCESS；Python tests 179/179；R8 140→126→119→109→106→88→81。
- 剩余 81 = SettingsLib 74 + B1–B4 platform/build classpath 6 + `AssumeTrueForR8` 1。
- release R8 仍失败；`shrinkResources` 与 device/emulator runtime validation 均未完成。
- 后续顺序：SettingsLib → B1–B4 → `AssumeTrueForR8` → release R8/shrink/sign → device。
- `docs/CURRENT_STATE.md` 是唯一完整实时技术状态 owner。
- 不移动、不批量改写、不删除 frozen 历史文件；发现删除候选只记录，不删除。
- 不修改 ADR、已完成 issue/audit/spec/plan/task、源码、资源、Gradle、工具或二进制产物。
- 不运行 Gradle；worker 只 commit，不 push。
- `AGENTS.md`、`CHARTER.md`、`STATE.md` 的修改仅限本计划明确列出的文档职责去重，用户已授权该范围。

---

### Task 1: 固定事实与文档生命周期审计

**Files:**
- Modify: `docs/issues/2026-08-20-core-documentation-refresh.md`
- Read: `README.md`
- Read: `README.en.md`
- Read: `docs/orchestration/log.md`
- Read: `docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md`

**Interfaces:**
- Consumes: Task 038 merged-main fresh verification at commit `2545bdc9` or later.
- Produces: issue 末尾的执行审计表，后续任务只从该表和 spec 固定事实取值。

- [ ] **Step 1: 验证工作基线**

Run:

```bash
git merge-base --is-ancestor 2545bdc9 HEAD
git status --short
grep -q '179/179' docs/orchestration/STATE.md
grep -q '81' docs/orchestration/STATE.md
```

Expected: 四条命令 exit 0；worktree 初始 clean。若不满足，输出 `REDLINE: Task 039 baseline mismatch` 并停止。

- [ ] **Step 2: 扫描核心入口的陈旧动态状态**

Run:

```bash
rg -n 'APK 尚未生成|APK 未生成|131/131|131 个|8 个 AAR|42 个 javac|SettingsLib AAR 缺|当前.*106|当前.*88|worker-reported|verification pending' \
  AGENTS.md docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md docs/README.md \
  docs/PITFALLS.md docs/orchestration/CHARTER.md docs/orchestration/STATE.md || true
```

Expected: 命中作为 Task 2–4 的 RED 基线；不要修改 frozen 历史目录来消除命中。

- [ ] **Step 3: 在 issue 追加执行审计表**

追加一个 `## 执行审计（worker）` 章节，逐项记录：

```text
baseline_commit=2545bdc9-or-later
current_owner=docs/CURRENT_STATE.md
stale_current_entries=<按文件列出 Step 2 命中>
frozen_directories=docs/issues, docs/architecture, docs/superpowers, docs/orchestration/tasks
move_candidates=none
delete_candidates=none（若发现则列路径与未满足的删除准则，仍不删除）
gradle=NOT RUN
```

- [ ] **Step 4: 提交审计基线**

```bash
git add docs/issues/2026-08-20-core-documentation-refresh.md
git commit -m "docs: audit documentation ownership and stale state"
```

Expected: English commit；仅 issue 被提交。

---

### Task 2: 建立唯一实时状态、5 分钟交接和未完成路线

**Files:**
- Rewrite: `docs/CURRENT_STATE.md`
- Rewrite: `docs/HANDOFF.md`
- Rewrite: `docs/PLAN.md`

**Interfaces:**
- Consumes: Task 1 审计表和 spec 固定事实。
- Produces: 唯一完整技术状态、最短接手入口、仅含未完成事项的路线图。

- [ ] **Step 1: 重写 `CURRENT_STATE.md` 为唯一完整实时状态**

使用以下固定结构：

```markdown
# Current State
> Owner / Last verified / Update triggers
## TL;DR
## Verified milestones
## Current build and verification matrix
## Toolchain and module topology
## Dependency and artifact state
## Release closure blocker (81 breakdown)
## Next ordered work
## Verification commands and evidence
## Historical pointers
```

必须写明 179/179、debug SUCCESS、81 构成、release/shrink/device 未完成；历史错误轨迹只给简短链接，不重放完整旧阶段。

- [ ] **Step 2: 重写 `HANDOFF.md` 为 5 分钟接手流程**

固定顺序：

1. 读 `AGENTS.md`；
2. 若做编排再读 `CHARTER.md`、`STATE.md`、log tail；
3. 读 `CURRENT_STATE.md` 获取全部实时状态；
4. 读 `PLAN.md` 获取未完成路线；
5. 当前唯一工程优先级为 SettingsLib 74 refs；
6. 列出禁止 stub/res 伪造/宽泛 dontwarn/并发 Gradle 等红线；
7. 不要求新 Agent 默认先跑重型全量构建。

HANDOFF 只保留一句 179/81 摘要并链接 CURRENT_STATE，不复制完整矩阵。

- [ ] **Step 3: 重写 `PLAN.md` 为未完成路线**

只保留以下有序阶段与完成条件：

```text
1. SettingsLib 74 program/resource closure
2. B1–B4 platform/build classpath 6
3. AssumeTrueForR8 build-time annotation 1
4. release R8 reaches zero missing refs
5. shrinkResources + signing/package verification
6. compatible emulator/device install and runtime validation
```

已完成事项只放一段链接到 CURRENT_STATE/历史任务，不保留旧 checklist 作为当前计划。

- [ ] **Step 4: 运行职责与数字检查**

```bash
grep -q '179' docs/CURRENT_STATE.md
grep -q '81' docs/CURRENT_STATE.md
grep -q 'SettingsLib.*74' docs/CURRENT_STATE.md
grep -q 'SettingsLib.*74' docs/PLAN.md
rg -n 'APK 尚未生成|APK 未生成|131/131|SettingsLib AAR 缺两个|当前.*88' \
  docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md && exit 1 || true
```

Expected: exit 0；HANDOFF/PLAN 不出现完整 build matrix 的复制。

- [ ] **Step 5: 提交实时 owner 文档**

```bash
git add docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md
git commit -m "docs: establish single live state and focused roadmap"
```

---

### Task 3: 建立索引、生命周期和规则文档去重

**Files:**
- Rewrite: `docs/README.md`
- Modify: `AGENTS.md`
- Modify: `docs/orchestration/CHARTER.md`
- Rewrite: `docs/orchestration/STATE.md`

**Interfaces:**
- Consumes: Task 2 的三个 owner 文档。
- Produces: 文档信息架构导航；不含动态技术快照的规则文档；只含编排态的 STATE。

- [ ] **Step 1: 重写 `docs/README.md` 信息架构索引**

必须包含：

- Start here 阅读顺序；
- live owners 及各自 owner/update trigger；
- rules and decisions；
- append-only records；
- active operational audit 定义与当前 R8 audit 链接；
- frozen archive 目录入口；
- 五项删除准则与“有疑问即保留”；
- 维护触发条件表；
- 当前有效 Python 工具的精选索引。

不得列出全部日期文档或复制 CURRENT_STATE 的完整数字。

- [ ] **Step 2: 从 `AGENTS.md` 移除动态当前状态**

- 删除整个 `## 四、当前进度状态`（含 4.1–4.5 动态表）；
- 在文件开头/文档位置处加入“实时状态唯一见 `docs/CURRENT_STATE.md`”；
- 保留规则 P/S/C/F/R/B/H/D/I、依赖策略、SysUISdk 规则、诊断流程、命令、用户偏好和版本历史；
- 修正因删节导致的章节编号/交叉引用，但不改变规则含义。

- [ ] **Step 3: 从 `CHARTER.md` 移除动态项目快照**

将 `Part 6 · Current Project State Snapshot` 替换为不含数字的 owner 声明：

```markdown
## Part 6 · Live State Ownership

The sole complete live technical state is `docs/CURRENT_STATE.md`.
`docs/orchestration/STATE.md` owns only active workers, queue, and orchestration transitions.
Workers must read both when the task brief requires orchestration context.
```

其他 contract、red-line、串行构建规则保持原意。

- [ ] **Step 4: 将 `STATE.md` 收窄为编排态**

固定结构：

```markdown
# Orchestration State
> technical state link / reread rule
## Active Workers
## Queue
## Recent Orchestration Transitions
## Last Updated
```

当前 Active Workers 为 Task 039 自身；Queue 写文档 review/merge 后启动 SettingsLib bounded task。不要复制 179/81 详情，只链接 CURRENT_STATE；近期 transitions 最多保留 Tasks 038/039 的编排事实。

- [ ] **Step 5: 静态检查规则未丢失且动态快照已移除**

```bash
for token in '规则 P' '规则 S' '规则 C' '规则 F' '规则 R' '规则 B' '规则 H' '规则 D'; do
  grep -q "$token" AGENTS.md || { echo "missing $token"; exit 1; }
done
! grep -q '^## 四、当前进度状态' AGENTS.md
! rg -n '131/131|APK not produced|106 missing|88 missing' docs/orchestration/CHARTER.md
rg -n 'CURRENT_STATE.md' AGENTS.md docs/orchestration/CHARTER.md docs/orchestration/STATE.md
```

Expected: exit 0。

- [ ] **Step 6: 提交信息架构和规则去重**

```bash
git add docs/README.md AGENTS.md docs/orchestration/CHARTER.md docs/orchestration/STATE.md
git commit -m "docs: separate live state from rules and archives"
```

---

### Task 4: 收敛 PITFALLS 并追加迁移里程碑

**Files:**
- Modify: `docs/PITFALLS.md`
- Modify: `docs/GRADLE_MIGRATION_LOG.md`

**Interfaces:**
- Consumes: spec 的生命周期规则和 Tasks 031–038 已验证经验。
- Produces: 不维护当前数字的可复用经验；保留历史正文的追加型迁移日志。

- [ ] **Step 1: 校准 `PITFALLS.md` 职责**

在顶部声明：只保存可复用根因/防错经验，实时状态见 CURRENT_STATE。保留并确保可定位：

- SysUISdk 只能经 `tools/build_sysuisdk.py --apply`；
- Soong `static_libs` 必须进入 program/packaging closure；
- 本地 AAR 内容变化必须升坐标；
- 真实 R8 missing refs 不得用宽泛 keep/`-dontwarn` 掩盖；
- debug 每批硬门禁；
- 全系统只允许一个 Gradle build。

删除或改成明确“历史案例”的当前错误数/当前 blocker 句，不删除仍有复用价值的失败根因。

- [ ] **Step 2: 在迁移日志顶部追加 2026-08-19/20 里程碑**

在旧日志正文之前追加一个新章节，内容严格为：首个 debug APK、release baseline、R8 140→81、Batch 1–4C、179 tests、剩余工作。明确这是追加摘要，详细证据链接 issue/audit；旧条目不改写、不重排。

- [ ] **Step 3: 检查经验与追加纪律**

```bash
rg -n 'build_sysuisdk.py --apply|static_libs|dontwarn|一个 Gradle|single Gradle|硬门禁' docs/PITFALLS.md
rg -n '140.*81|179' docs/GRADLE_MIGRATION_LOG.md
rg -n '当前.*(106|88)|131/131|APK 尚未生成' docs/PITFALLS.md && exit 1 || true
```

Expected: exit 0。

- [ ] **Step 4: 提交经验与日志**

```bash
git add docs/PITFALLS.md docs/GRADLE_MIGRATION_LOG.md
git commit -m "docs: preserve reusable lessons and append migration milestones"
```

---

### Task 5: 全局静态验收与完成证据

**Files:**
- Modify: `docs/issues/2026-08-20-core-documentation-refresh.md`
- Verify: all Task 039 modified files plus `README.md` and `README.en.md`

**Interfaces:**
- Consumes: Tasks 1–4 commits.
- Produces: 可供双轴 reviewer 审查的静态证据和 worker HANDOFF。

- [ ] **Step 1: 检查本地 Markdown 链接**

```bash
python3 - <<'PY'
from pathlib import Path
import re
files = [
    Path('README.md'), Path('README.en.md'), Path('AGENTS.md'),
    Path('docs/CURRENT_STATE.md'), Path('docs/HANDOFF.md'), Path('docs/PLAN.md'),
    Path('docs/README.md'), Path('docs/PITFALLS.md'),
    Path('docs/orchestration/CHARTER.md'), Path('docs/orchestration/STATE.md'),
]
for doc in files:
    text = doc.read_text(encoding='utf-8')
    for raw in re.findall(r'\[[^]]+\]\(([^)]+)\)', text):
        target = raw.split('#', 1)[0]
        if not target or '://' in target or target.startswith('mailto:'):
            continue
        path = (doc.parent / target).resolve()
        assert path.exists(), f'{doc}: missing link {raw}'
print('markdown links: OK')
PY
```

Expected: `markdown links: OK`。

- [ ] **Step 2: 检查当前状态去重和 frozen 历史保护**

```bash
rg -n 'APK 尚未生成|APK 未生成|131/131|131 个|SettingsLib AAR 缺两个|当前.*106|当前.*88' \
  AGENTS.md docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md docs/README.md \
  docs/PITFALLS.md docs/orchestration/CHARTER.md docs/orchestration/STATE.md && exit 1 || true

git diff --diff-filter=D --name-only 2545bdc9...HEAD | grep -q . && exit 1 || true
```

Expected: exit 0；历史目录没有删除文件。frozen 文档中的历史数字不纳入扫描。

- [ ] **Step 3: 检查范围、格式和未生成产物**

```bash
git diff --check 2545bdc9...HEAD
git diff --name-only 2545bdc9...HEAD | LC_ALL=C sort
```

Expected: 只出现以下路径：

```text
AGENTS.md
docs/CURRENT_STATE.md
docs/GRADLE_MIGRATION_LOG.md
docs/HANDOFF.md
docs/PITFALLS.md
docs/PLAN.md
docs/README.md
docs/issues/2026-08-20-core-documentation-refresh.md
docs/orchestration/CHARTER.md
docs/orchestration/STATE.md
```

- [ ] **Step 4: 在 issue 追加真实完成证据**

记录每个 commit、链接检查结果、陈旧状态扫描结果、无删除结果、`git diff --check`、修改路径和 `Gradle: NOT RUN (task boundary)`。

- [ ] **Step 5: 提交完成证据**

```bash
git add docs/issues/2026-08-20-core-documentation-refresh.md
git commit -m "docs: record documentation governance verification"
```

- [ ] **Step 6: 输出 HANDOFF**

HANDOFF 必须包含：Summary、Commits、Static verification、Files changed、Frozen-history/deletion result、Build statement。worker 不 push。

## Self-Review

- Spec coverage: single owner、四类生命周期、audit 边界、删除准则、索引、维护触发、AGENTS/CHARTER/STATE 去重、历史冻结均有对应 task。
- Placeholder scan: 无 TBD/TODO/“稍后补充”；每个验收命令和 expected result 已明确。
- Interface consistency: Task 1 固定事实 → Task 2 owner docs → Task 3 governance/index → Task 4 experience/log → Task 5 static gate。
