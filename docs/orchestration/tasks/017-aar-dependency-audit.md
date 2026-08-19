# Task 017 — 全量 AAR 依赖审查（只读）

## Goal

用户指示（2026-08-19）：审查项目所有 AAR 依赖，找出
(a) 未走本地 Maven 统一管理的（直接 `files(...)` 引用）→ 迁移候选；
(b) 未使用 / 不必要的 → 删除候选。

产出**一个**审查文档：`docs/architecture/2026-08-19-aar-dependency-audit.md`，
含 per-artifact 结论表（keep / migrate-to-Maven / delete-candidate + 证据），
供用户批准后续清理动作。**本任务不删除、不修改任何被审查对象。**

## Non-goals

- 不删除/移动/修改任何 AAR、POM、构建脚本、catalog、源码、资源；
- 不运行 Gradle 构建（`./gradlew` 一律禁止；用静态分析：grep、解包、字节码检查）；
- 不评价 jar（用户问题聚焦 AAR；jar 异常仅作相邻发现记录）。

## Allowed Paths

- `docs/architecture/2026-08-19-aar-dependency-audit.md`（新建）
- `docs/issues/2026-08-19-aar-dependency-audit.md`（更新结果）
- `docs/orchestration/tasks/017-aar-dependency-audit.md`（勾选 checklist）

## Forbidden Paths

其它一切。注意：Task 015 可能正在并行修改 `tools/package_aosp_aar.py` /
`libs/aars/SettingsLib*` / `gradle/libs.versions.toml`——**不要读取 worktree 外
其它分支的中间态作为结论**；以本 worktree 的 main 基线为准，并在文档中标注
Task 015 的 7 个新 AAR 属于已批准增量。

## Inputs to Read First

1. `AGENTS.md`（§1.1/§3.2 依赖规则与 libs 清单）、`docs/orchestration/CHARTER.md`
2. `docs/issues/2026-08-19-aar-dependency-audit.md`
3. 本 worktree 全部 `**/build.gradle.kts`、`settings.gradle.kts`、`gradle/libs.versions.toml`
4. `libs/aars/`、`libs/maven/`（完整目录树 + 每个 POM）
5. `tools/package_aosp_aar.py`、`tools/install_aar_to_maven.py`、
   `tools/rebuild_settingslib_aar.py`、`tools/gen_aar_maven.py`（评估在役/废弃）
6. 消费证据：各模块源码 import / res 引用 / manifest 引用

## Required Findings

1. **全量 inventory 表**：每个 AAR 产物（含 libs/maven 孤儿坐标）：
   坐标/路径、SHA-256、大小、提供者（package_aosp_aar.py CONFIGS / install ARTIFACTS /
   无注册）、消费者（模块 + dependency 配置 + 直接 files() 还是 catalog/Maven）、
   POM 是否骨架。
2. **直接 files() 引用清单**：任何绕过 Maven 的 AAR 引用（含 `fileTree`、绝对/相对路径），
   逐条给文件+行号。
3. **使用性判定**：对每个被消费的 AAR，给出"类或资源被消费模块实际引用"的证据
   （grep/解包/字节码，至少一条）；无证据者列 delete-candidate 并说明理由与风险。
4. **冗余/重叠判定**：artifact 之间类集合或资源重叠（如 maven 里 flags artifact 与
   libs/*.jar 同名类）；历史遗留（SystemUISharedLib）；在役工具链不引用的产物。
5. **结论表 + 建议**：keep / migrate-to-Maven / delete-candidate 三分类，
   每条的回滚方式；按风险排序的清理顺序建议。
6. 标注置信度；不确定的写"未证实"，不猜测。

## Execution Hints

- 先 worker-contract skill 输出 `CONTRACT:`；
- 用 research skill 的方法（一手来源、引用出处）；
- 临时脚本/解包目录只放 /tmp；
- 文档中的每条结论必须带证据（文件:行号 或 命令输出摘要）。

## Acceptance

- `test -s docs/architecture/2026-08-19-aar-dependency-audit.md`
- `rg -n "keep|migrate|delete-candidate|files\\(" docs/architecture/2026-08-19-aar-dependency-audit.md`
  有实质命中
- `git diff --check` 干净；只改 Allowed Paths；英文 commit；**不 push**

## Report

完成后汇报：commit、逐条 checklist、issue 更新、新发现、HANDOFF 块。
