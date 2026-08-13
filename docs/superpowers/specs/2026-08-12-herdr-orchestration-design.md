# Herdr 编排工作流设计（Orchestration Design）

> **状态**：待用户 review
> **日期**：2026-08-12
> **动机**：长任务在上下文压缩后丢失强制约束（规则 P/S/C/F/R/B/H/D/I），导致跑偏。
> 用户指定本会话 pi 作为总架构师/编排者，统筹其他 herdr pane 中的 worker pi，监控其工作进度。

---

## 1. 目标与非目标

### 1.1 目标

- **防漂移**：任何参与者（worker、架构师、未来的新会话）在上下文压缩后，仅凭仓库内文件即可无损恢复全部强制约束与任务进度。
- **可监控**：架构师通过 herdr CLI 掌握每个 worker pane 的生命周期状态（working/blocked/idle/done）。
- **可追溯**：任务派发、阻塞、审查结论全部落盘，可回查。
- **不重复造轮子**：复用现有 plan/issue/CURRENT_STATE 文档纪律、superpowers 与 Matt Pocock 系列 skill。

### 1.2 非目标

- 不追求并行吞吐（并行只在任务独立时启用，默认串行）。
- 不改变现有构建/依赖/文档规则本身；本流程是规则的外化与执行载体。
- herdr 只承担生命周期管理，不作为约束或状态的存储介质。

### 1.3 已确认的关键决策

| 决策点 | 结论 |
|--------|------|
| 主要痛点 | 长任务上下文压缩后忘记强制约束（防跑偏优先于并行吞吐） |
| worker 关系 | **混合模式**：默认串行委派；任务经判定无共享状态、无顺序依赖时才开并行 herdr worktree |
| 提交权限 | **分级**：普通任务 worker 自行英文 commit；触碰红线区必须停下上报，经架构师转用户显式批准 |
| pi-subagent | 已删除，不再使用 |
| herdr 角色 | 执行器（pane/agent 生命周期 + 状态可视），不是约束/状态存储 |

---

## 2. 总体架构

### 2.1 角色与通道

```
用户
  │（下达目标、批准红线改动、批准 spec/plan）
  ▼
架构师 pi（herdr pane w2:p1，本会话）
  │  职责：拆任务、写 task brief、派发、监控、审查、合并、维护编排状态
  │  工具：herdr CLI + git + 文件协议
  ▼
worker pi（herdr pane，默认 1 个串行；任务独立时并行 worktree）
     职责：读 brief → 干活 → 自验证 → 按权限提交 → 写交接
```

三条通道，职责分离：

| 通道 | 载体 | 管什么 | 不管什么 |
|------|------|--------|----------|
| 生命周期 | herdr CLI（`agent start/prompt/wait/read`、`pane split/run/close`、`worktree create`） | 启动 worker、下发 brief 指针、监控状态 | 不传约束正文（终端是有损通道） |
| 记忆/状态 | `docs/orchestration/` 文件 | 约束、任务状态、验收标准、红线区 | 不存易变瞬时输出 |
| 产物 | 代码 diff + commit + `docs/issues/`（沿用现有纪律） | 工作成果与审查依据 | — |

### 2.2 新增目录结构

```
docs/orchestration/
├── CHARTER.md        # 编排章程：角色契约、十条强制规则、红线区、worker 契约（防漂移核心）
├── STATE.md          # 当前编排状态：活跃 pane、任务、阶段、阻塞点（架构师每步操作前重读）
├── tasks/            # 每任务一份 brief（沿用现有 plan 模板 + 权限/路径白名单字段）
│   └── NNN-<slug>.md
└── log.md            # 追加式事件日志：派发/完成/阻塞/审查结论（一行一条）
```

外加两个 pi skill（位于 `~/.pi/agent/skills/`，遵循 writing-skills 规范）：

- `orchestrator/` —— 架构师角色操作手册
- `worker-contract/` —— worker 自约束协议

### 2.3 核心设计原则

**任何一方上下文被压缩后，仅凭 `CHARTER.md + STATE.md + 当前 task brief` 三份文件即可无损恢复全部约束和进度。** herdr 状态（working/blocked/idle）只用于监控，不作为事实来源；`unknown` 状态不可信时以 `agent read` 的终端实际输出为准。

---

## 3. CHARTER.md 内容规范

CHARTER 分八个部分。Part 1–5 是约束层（改动 = 改规则 = 红线）；Part 6 是状态层（只放指针，随 STATE 更新）；Part 7–8 是行为协议。所有条文来自现有文档的浓缩，不新造规则。

### Part 1 · 项目身份与规则优先级

- 项目本质：AOSP `frameworks/base/packages/SystemUI` 移植到独立 Gradle 体系（AGP 9.3.1 + Gradle 9.5.0 + builtInKotlin 2.2.10），目标是真实编译出 SystemUI APK。
- 指令优先级逐字引用：**用户明确指令 > AGENTS.md + HANDOFF > 默认系统提示**。
- 编排推论：task brief 视为架构师转达的用户指令；brief 与 AGENTS.md 规则冲突时**规则赢，worker 必须上报而非执行**。

### Part 2 · 十条强制规则（三段式：一句话禁令 + 出处 + 违反时的正确做法）

| # | 规则 | 一句话禁令 | 出处 |
|---|------|-----------|------|
| P | 无 stub | 禁止手写 `*.java/*.kt` stub 让编译器满意；禁止伪造 res | AGENTS §1.2 |
| S | SystemUI 自有代码源码化 | `packages/SystemUI/**/Android.bp` 定义的模块一律源码依赖 | §1.5 |
| C | 不漏不多 | 代码/aidl/res 与 AOSP 逐一对齐；`check_source_alignment.py` 验证 | §1.6 |
| F | framework 只走 SDK/jar | 非 SystemUI 代码禁止源码复制；缺 API 补 SysUISdk/framework.jar | §1.7 |
| R | res 来源纯正 | res 只能来自 AOSP 源码/AAR/官方 Maven；擅改须走 ADR 0004 CONV 标记且用户授权 | §1.8 + ADR 0001/0004 |
| B | bp 语义对齐 | 模块边界/R namespace/入口类位置以 `Android.bp` 语义为准 | §1.9 + ADR 0003 |
| I | 错误数非门槛 | 错误数只是诊断信息；禁止为降错误数做结构性倒退 | §2.1 |
| D | 文档先行 | 每步先写 `docs/issues/`；构建结果如实记录，禁止暗示成功 | §2.2 |
| H | 求助用户 | §2.5 七类情形必须停下问用户 | §2.5 |
| 工具 | Python only | `tools/` 下脚本一律 Python | ADR 0002 |

### Part 3 · 依赖三层判定决策树

```
是 frameworks/base/packages/SystemUI/**/Android.bp 定义的 soong 模块？
├─ 是 → ① 源码复制成 module（规则 S）
└─ 否 → Google Maven/Maven Central 有且未被 AOSP fork？
    ├─ 是 → ③ 官方坐标（版本先查 maven-metadata.xml；PITFALLS §1.7）
    └─ 否 → ② AOSP 产物：无资源→jar；有资源→AAR 先直接引入，
             确认冲突后才进 libs/maven（ADR 0001）
```

关键机制警告：Soong `static_libs` 传递依赖不会自动进入 Gradle classpath（Task 7 的 8 组 javac 错误全部源于此）；`libs/maven/` 的 POM 是无依赖骨架。

### Part 4 · 工具链事实表

- 版本矩阵：Gradle 9.5.0 / AGP 9.3.1 / Kotlin 2.2.10（builtInKotlin 内置，无显式 kotlin-android 插件）/ KSP 2.2.10-2.0.2 / Dagger 2.59.2 / Compose 1.11.4（不可升 1.12，`ExperimentalAnimatableApi` 已移除，PITFALLS §1.6）/ material3 1.5.0-alpha18。
- builtInKotlin 三件套：`android.builtInKotlin=true`、`android.disallowKotlinSourceSets=false`、所有 Android 模块 `kotlin.srcDirs` 对齐 `java.srcDirs`（PITFALLS §1.5）。
- SysUISdk 可补丁（framework.jar 补 API、framework-res.apk 补私有资源 ID、`framework.aidl` 补 AIDL 声明，AGENTS §2.4）；framework.jar 不注入 KotlinCompile。
- KAPT 禁用（PITFALLS §1.2），注解处理一律 KSP。
- 内部 flags jar 必须排在 framework.jar 之前（PITFALLS §2.x）。

### Part 5 · 红线区清单（触发即 `REDLINE:` 上报）

1. **AOSP 镜像源码/res**：`SystemUI-*/src/**`、`SystemUI-*/res*/**`——CONV 标记场景也须用户授权（R + ADR 0004）
2. **任何 res/ 文件**的新增/修改/删除（R）
3. **规则与流程文件**：`AGENTS.md`、`docs/adr/**`、`docs/orchestration/CHARTER.md`（H.6）
4. **依赖版本矩阵**：`gradle/libs.versions.toml`、`settings.gradle.kts` 的版本与 include 列表
5. **模块边界**：模块增删、入口类（`SystemUIApplication`/`SystemUIService`）挪位置（ADR 0003）
6. **构建绕过**：`@Suppress("DEPRECATION")`、排除源码、关闭 javac/D8/KSP 校验、手写 stub（P/I/用户偏好）
7. **非 Python 脚本**进 `tools/`（ADR 0002）

worker 不确定是否触红线时**默认视为触红线**（宁可误报）。

### Part 6 · 当前项目状态快照

只放一行结论 + 指针（细节永远以 `docs/CURRENT_STATE.md` 为准）。当前快照：KSP 0 错误（2933 文件）、core Kotlin 0 错误；`:app:assembleDebug` 被 core javac 42 错误阻塞，APK 未生成（8 组根因见 `docs/issues/2026-08-12-current-progress-standards-review.md`）。已知允许偏差：1 个 src MODIFIED + 86 个 res byte-diff。

### Part 7 · Worker 契约

**启动序列**（收到任务后、写任何代码前按序执行）：
1. 读 `AGENTS.md` 全文
2. 读 `CHARTER.md`
3. 读自己的 task brief
4. 读 brief 列出的相关 issue/plan 文档
5. 输出 `CONTRACT:` 段复述：任务目标、允许动的路径、禁止动的路径、验收命令、提交权限——架构师通过 `agent read` 验证该段存在才算派发成功

**上报四件套**（缺一不可）：
1. 英文 commit（或 REDLINE 状态下的未提交 diff + 说明）
2. brief checkbox 全部勾选 + 每条验证命令的真实输出摘要（禁止虚假成功声明）
3. `docs/issues/` 当日记录更新（规则 D）
4. `HANDOFF:` 终端结尾段（做了什么/验证了什么/遗留什么），供 `agent read` 抓取

### Part 8 · 用户偏好硬条款

中文交流；commit message 英文；及时 commit + push；先 plan 再开发；增量提交；依赖尽量最新但升级前先沟通（AOSP prebuilt 版本号必须查 `maven-metadata.xml`）；不用 `@Suppress` 绕过；不确定查官方文档；参考 `CarSystemUIGradle`；给下一个 AI 留完整交接。

---

## 4. 任务生命周期协议

### 阶段 0 · 任务拆解（仅架构师）

- 调用 superpowers `writing-plans` 或 Matt `to-tickets` 拆任务；按 dispatching-parallel-agents 标准判定并行性（无共享文件、无顺序依赖才可并行）。
- 每个任务生成 `docs/orchestration/tasks/NNN-<slug>.md`，格式 = 现有 plan 模板（Global Constraints + File Map + checkbox steps）外加：

```markdown
## Authority            # self-commit | redline-gated（列出预计触碰的红线）
## Allowed Paths        # 允许修改的路径白名单
## Forbidden Paths      # 明确禁止的路径
## Acceptance           # 验收命令 + 期望输出（禁止"构建成功"这类虚词）
## Reports To           # docs/orchestration/log.md 条目格式
```

- **用户关卡**：plan/brief 拆完后给用户过目，批准后才派发。

### 阶段 1 · 派发

> 下列 herdr 命令为模板；确切参数以实现时安装的 herdr binary 为准（herdr skill 原则：binary 是语法的权威）。

```bash
# 并行任务先建隔离 worktree（串行任务跳过，用当前 checkout）
herdr worktree create ...

# 开 pane + 启动 worker pi
herdr pane split ...
herdr agent start --pane <pane_id> pi

# 下发任务（只传指针，不传约束正文）
herdr agent prompt <name-or-pane> \
  "你是 worker。立即按序阅读：(1) AGENTS.md (2) docs/orchestration/CHARTER.md \
   (3) docs/orchestration/tasks/NNN-xxx.md，然后输出 CONTRACT: 段复述你的约束，再开工。"
```

更新 `STATE.md` + `log.md`。验收点：`agent read` 抓到的输出必须含 `CONTRACT:` 段。

### 阶段 2 · 监控

```bash
herdr agent list
herdr agent wait <name> --state blocked,idle --timeout ...
herdr agent read <name>
```

- `working` → 不打扰（worker 上下文珍贵）
- `blocked` → `agent read` 看原因：REDLINE → 转述用户等批准；普通问题 → 在 brief 范围内让它按 systematic-debugging 继续，范围外升级用户
- `idle/done` → 进入审查

### 阶段 3 · 审查（合并前的硬关卡）

worker 报"完成"不等于完成。按序核查：

1. **产物核查**：commit 英文且聚焦；diff 未触碰 Forbidden Paths/红线区（触碰即打回）
2. **证据核查**：架构师**亲自重跑验收命令**，比对输出（PITFALLS §8.1 教训）
3. **文档核查**：`docs/issues/` 已更新；`git diff --check` 干净
4. **约束核查**：无新 stub、无擅改 res；涉及源码树时 `check_source_alignment.py --strict` 仍 MISSING/MISPLACED/EXTRA=0

不通过 → 问题列表 `agent prompt` 发回 worker 返工（它上下文还在，修自己的活成本最低）。

### 阶段 4 · 合并与提交

- 串行（当前 checkout）：审查通过后直接 `git push`。
- 并行（worktree）：按依赖顺序逐个 merge/cherry-pick 回主 checkout；冲突由架构师解决或退回 worker；每合并一个重跑验收命令确认无交叉破坏。
- 红线区改动：即使审查通过，先向用户展示 diff 摘要，**用户确认后才 push**。

### 阶段 5 · 收尾与状态推进

更新 `STATE.md` + `log.md`；同步维护文档（`CURRENT_STATE.md` 等）；`pane close` 释放 worker 或复用 pane 派下一个任务（压缩风险高就换新的）。

### 异常处理

| 异常 | 处理 |
|------|------|
| worker 卡死/无响应 | `agent read` 诊断 → `pane close` → 新 pane 重派（brief 还在，成本仅一次冷启动） |
| worker 反复犯同一错误 | 停止重试（PITFALLS §7.2），根因调查升级给用户 |
| 架构师自身压缩 | 重读 CHARTER + STATE + log 恢复现场 |
| herdr 状态 `unknown` | 不信状态，直接 `agent read` 看终端实际输出 |

---

## 5. Skill 接口设计

### 5.1 `orchestrator`（`~/.pi/agent/skills/orchestrator/SKILL.md`，约 150 行）

```yaml
---
name: orchestrator
description: "Orchestrate herdr worker panes for SystemUI-Gradle. Use when acting as chief architect: decomposing goals into task briefs, dispatching workers, monitoring via herdr, reviewing output, merging. Loads the orchestration charter before any action."
---
```

正文：入口检查（`HERDR_ENV=1`、编排文件存在性）→ 强制启动序列（读 CHARTER + STATE + log 尾部）→ 六阶段操作规程（checklist 化，附 herdr 命令模板）→ 并行性判定三问 → 审查 checklist → 红线升级话术模板。规则细节一律指向 CHARTER/AGENTS.md，skill 只写"何时读什么"。

### 5.2 `worker-contract`（`~/.pi/agent/skills/worker-contract/SKILL.md`，约 100 行）

```yaml
---
name: worker-contract
description: "SystemUI-Gradle herdr worker self-constraint protocol. Use when dispatched as a worker pane: mandates the reading sequence (AGENTS.md → CHARTER → task brief), CONTRACT: echo, red-line halt behavior, and the four-part completion report."
---
```

正文：启动序列（五步，未完成前不得写代码）→ CONTRACT 段模板 → commit 前对照 Allowed/Forbidden Paths → REDLINE 固定输出格式 → 完成四件套 → 调试纪律（systematic-debugging，禁止试错式乱改）。

### 5.3 与既有体系的关系

| 已有资产 | 编排流程中的角色 |
|---------|-----------------|
| superpowers `writing-plans` / Matt `to-tickets` | 阶段 0 拆任务 |
| superpowers `systematic-debugging` | worker 调试纪律 |
| superpowers `verification-before-completion` | 审查 checklist 第 2 条依据 |
| Matt `handoff` | worker 超长任务中途交接（可选） |
| `code-review` skill | 大任务合并前深度审查（可选） |
| 现有 plan/issue/CURRENT_STATE 纪律 | 全部沿用，编排文件只增不改 |

---

## 6. 演进策略

1. 先写最小可用版：两个 skill + CHARTER + STATE 骨架 + log。
2. 用一个真实任务做 pilot（建议取"Task 7 后续修复计划"的第一个子任务，如刷新 `SystemUI-tags.jar`——范围小、验收明确）。
3. 根据 pilot 暴露的问题迭代 CHARTER/skill/协议。
4. 固化后将编排流程写回 AGENTS.md 索引（该改动本身属红线区，需用户批准）。

## 7. 测试与验证

本设计是流程设计，验证方式是 pilot 任务的实际执行：

- CHARTER 有效性：worker 冷启动（新 pane、零上下文）后仅凭文件能正确复述约束（CONTRACT 段准确）。
- 审查有效性：架构师重跑验收命令能复现 worker 声明的结果。
- 恢复有效性：模拟架构师压缩后，仅凭 STATE + log 能正确回答"哪些任务在什么阶段"。
