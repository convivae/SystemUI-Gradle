# Core Documentation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目六个核心文档刷新到 Task 038 合并后的真实基线，使新访问者和下一个 Agent 不再被“APK 未生成”等旧状态误导。

**Architecture:** 先从权威状态、R8 closure audit 和最近任务证据建立一份统一事实表，再由该事实表依次重写当前状态、交接和路线图，最后更新索引、踩坑与历史日志。文档只描述已经验证的事实；历史内容保留为明确标记的历史，不与当前状态混写。

**Tech Stack:** Markdown、Git、Python 3（仅用于静态链接/一致性检查）、Unix 文本工具；禁止 Gradle 构建。

**Spec:** `docs/issues/2026-08-20-core-documentation-refresh.md`

## Global Constraints

- 基线必须包含 Task 038 架构师主分支 fresh verification，关键数字为 debug 成功、179 tests、R8 missing refs 81。
- release R8 仍失败；`shrinkResources`、release 签名最终验收和设备验证均未完成。
- 后续顺序固定为 SettingsLib 74 → B1–B4 platform/build classpath 6 → `AssumeTrueForR8` 1 → release/shrink/sign/device。
- 仅允许修改六个目标文档和 Task 039 issue；禁止修改 `AGENTS.md`、`docs/orchestration/CHARTER.md`、ADR、源码、资源、Gradle 配置与二进制产物。
- 不运行 Gradle；不伪造测试或构建结果；所有命令与数字必须能追溯到已合并 issue/STATE/log。
- 历史迁移日志不得删除；只在顶部追加当前里程碑。

---

### Task 1: 建立统一事实表并审计陈旧陈述

**Files:**
- Read: `docs/orchestration/STATE.md`
- Read: `docs/orchestration/log.md`
- Read: `docs/architecture/2026-08-20-r8-runtime-closure-audit.md`
- Read: `docs/issues/2026-08-20-release-r8-alignment-decisions.md`
- Read: `docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md`
- Read: `docs/issues/2026-08-20-device-emulator-validation-plan.md`
- Modify: `docs/issues/2026-08-20-core-documentation-refresh.md`

**Interfaces:**
- Consumes: Task 038 merged main and architect verification evidence.
- Produces: issue 文档中的“最终事实表”，供后续五个任务逐字复用。

- [ ] **Step 1: 确认固定事实**

记录以下项目：toolchain、13 modules、KSP/Kotlin/javac 状态、debug APK、tests、R8 140→81 轨迹、81 的构成、当前 next step、尚未完成的 release/device 工作。

- [ ] **Step 2: 审计六个目标文档**

运行：

```bash
rg -n 'APK 尚未生成|APK 未生成|131/131|60 个|8 个 AAR|42 个 javac|SettingsLib AAR 缺|119|109|106|88 个 R8|错误数从 2000' \
  docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md docs/README.md \
  docs/PITFALLS.md docs/GRADLE_MIGRATION_LOG.md
```

将每个命中标为“需要删除/改成历史/仍有效”。

- [ ] **Step 3: 在 issue 中追加最终事实表与审计清单**

事实表至少包含：

```text
debug=:app:assembleDebug SUCCESS
python_tests=179/179
r8_missing=81
r8_path=140→126→119→109→106→88→81
remaining=SettingsLib 74 + platform/build classpath 6 + AssumeTrueForR8 1
release_r8=BLOCKED
resource_shrink=NOT COMPLETED
device_validation=NOT STARTED
```

- [ ] **Step 4: 提交事实表**

```bash
git add docs/issues/2026-08-20-core-documentation-refresh.md
git commit -m "docs: establish current project facts for documentation refresh"
```

---

### Task 2: 重写当前状态和路线图

**Files:**
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/PLAN.md`

**Interfaces:**
- Consumes: Task 1 最终事实表。
- Produces: 当前状态权威快照和从 81 refs 到设备验证的可执行路线图。

- [ ] **Step 1: 重写 `CURRENT_STATE.md`**

保留并更新以下结构：TL;DR、已完成里程碑、当前构建状态、toolchain、13-module topology、依赖治理、当前 blocker、下一步、验证命令、历史诊断摘要。删除“APK 未生成”和 SettingsLib switch drawable blocker 等失效现状。

- [ ] **Step 2: 重写 `PLAN.md`**

将顶部失效的 2026-07/08 阶段计划替换为：已完成基础迁移、debug APK、release baseline、R8 Batch 1–4C；当前 SettingsLib 74；后续 B1–B4、annotation、release R8/shrink/sign、device validation。历史计划可保留为简短附录或链接，不得继续显示为当前操作步骤。

- [ ] **Step 3: 交叉检查关键数字**

```bash
rg -n '179|140.*81|SettingsLib.*74|AssumeTrueForR8|assembleDebug|shrinkResources' \
  docs/CURRENT_STATE.md docs/PLAN.md
```

Expected: 两文档当前状态一致；无 release 成功误报。

- [ ] **Step 4: 提交状态和计划**

```bash
git add docs/CURRENT_STATE.md docs/PLAN.md
git commit -m "docs: refresh current state and release roadmap"
```

---

### Task 3: 重写 5 分钟交接与文档索引

**Files:**
- Modify: `docs/HANDOFF.md`
- Modify: `docs/README.md`

**Interfaces:**
- Consumes: Task 2 的当前状态和路线图。
- Produces: 新 Agent 的最短正确入口与可导航文档索引。

- [ ] **Step 1: 重写 `HANDOFF.md`**

包含：项目目标、必读顺序、规则摘要、当前 179/81 状态、构建串行纪律、正确验证命令、当前唯一优先级、禁止方案、关键路径。删除要求新 Agent 先跑全量构建的默认动作，避免与单构建者纪律冲突。

- [ ] **Step 2: 刷新 `docs/README.md`**

更新里程碑、ADR 0005、近期 2026-08-19/20 architecture/issues、orchestration 入口和工具列表；测试数改为 179。对大量历史 issue 用目录链接和精选表替代陈旧的“近期”列表。

- [ ] **Step 3: 验证相对链接存在**

运行一个只读 Python 检查：

```bash
python3 - <<'PY'
from pathlib import Path
import re
for doc in [Path('docs/HANDOFF.md'), Path('docs/README.md')]:
    for target in re.findall(r'\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)', doc.read_text()):
        if '://' in target:
            continue
        path = (doc.parent / target).resolve()
        assert path.exists(), f'{doc}: missing {target}'
print('markdown links: OK')
PY
```

Expected: `markdown links: OK`。

- [ ] **Step 4: 提交交接和索引**

```bash
git add docs/HANDOFF.md docs/README.md
git commit -m "docs: update handoff and documentation index"
```

---

### Task 4: 增量更新踩坑与迁移日志

**Files:**
- Modify: `docs/PITFALLS.md`
- Modify: `docs/GRADLE_MIGRATION_LOG.md`

**Interfaces:**
- Consumes: Task 1 事实表和 Tasks 031–038 的已验证经验。
- Produces: 不丢历史的近期经验与里程碑摘要。

- [ ] **Step 1: 更新 `PITFALLS.md`**

最小增量记录：SysUISdk 只能经声明式 pipeline；AAR `static_libs` 不会自动成为 Gradle 闭包；本地 AAR 内容变化必须升坐标；R8 missing refs 不得 `-dontwarn` 掩盖；debug 每批硬门禁；全系统 Gradle 构建串行。只修正会误导当前执行的旧句，不删除经典历史根因记录。

- [ ] **Step 2: 更新 `GRADLE_MIGRATION_LOG.md`**

在 2026-08-12 条目之前追加一个 2026-08-19/20 汇总，包含首个 debug APK、release baseline、R8 140→81、Batch 1–4C、179 tests 和尚未完成项。明确这是里程碑摘要，详细证据链接到 issue/audit。

- [ ] **Step 3: 检查历史与当前标签**

```bash
rg -n '140.*81|179/179|static_libs|dontwarn|串行|历史' \
  docs/PITFALLS.md docs/GRADLE_MIGRATION_LOG.md
```

Expected: 新经验可定位；旧失败记录仍存在且不会被误当现状。

- [ ] **Step 4: 提交踩坑和日志**

```bash
git add docs/PITFALLS.md docs/GRADLE_MIGRATION_LOG.md
git commit -m "docs: capture current R8 and artifact migration lessons"
```

---

### Task 5: 全局一致性验收与交接

**Files:**
- Modify: `docs/issues/2026-08-20-core-documentation-refresh.md`
- Verify: all six target documents

**Interfaces:**
- Consumes: Tasks 1–4 文档。
- Produces: 可审查提交、真实验证记录和 HANDOFF。

- [ ] **Step 1: 陈旧现状清零**

```bash
rg -n 'APK 尚未生成|APK 未生成|131/131|60 个|8 个 AAR|42 个 javac 错误|SettingsLib AAR 缺两个|当前.*106|当前.*88' \
  docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md docs/README.md || true
```

Expected: 0 个未标注为“历史”的误导性当前状态。若保留历史数字，句子必须明确写“历史”。

- [ ] **Step 2: 当前数字一致性检查**

```bash
for f in docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md docs/README.md; do
  grep -q '179' "$f" || { echo "missing 179: $f"; exit 1; }
  grep -q '81' "$f" || { echo "missing 81: $f"; exit 1; }
done
```

Expected: exit 0。

- [ ] **Step 3: 链接、差异和范围检查**

运行 Task 3 的链接检查，并执行：

```bash
git diff --check
git status --short
git diff --name-only HEAD~4..HEAD
```

Expected: diff-check clean；只有 issue + 六个授权文档发生变化；无 Gradle/build 产物。

- [ ] **Step 4: 更新 issue 验证结果并提交**

```bash
git add docs/issues/2026-08-20-core-documentation-refresh.md
git commit -m "docs: finalize core documentation refresh evidence"
```

- [ ] **Step 5: 输出 HANDOFF**

报告每个提交、修改文件、链接检查、陈旧短语检查、`git diff --check`，并明确“未运行 Gradle（按任务边界）”。worker 只 commit，不 push。
