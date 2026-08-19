# 2026-08-19 — 全量 AAR 依赖审查（Task 017）

## 背景

用户 2026-08-19 指示：审查项目所有 AAR 依赖——
1. 未走 Maven 统一管理的（直接 `files(...)` 引用）应迁移；
2. 没有实际使用 / 不必要的应删除（删除动作需用户批准后另行执行）。

## 现状线索（架构师已知，待 worker 核实）

- `libs/aars/`：animationlib、WifiTrackerLib、iconloader、SettingsLib、
  WindowManager-Shell、WindowManager-Shell-shared、SettingsLibSettingsTheme（+Task 015 将新增 7 个）
- `libs/maven/`：上述对应坐标 + 遗留 `SystemUISharedLib`（AGENTS.md §3.2 标注"待清理"）+
  flags 类 artifact（`com.android.systemui.flags:flags`、`com.android.server.notification:Flags`）
- AGENTS.md §3.2 声称"build.gradle.kts 中不再直接 files(libs/aars/xxx.aar)"，需逐模块核实
- `tools/rebuild_settingslib_aar.py` 是历史脚本，需评估是否仍被使用/应废弃

## 调研问题

1. 全量清单：所有 AAR 产物（libs/aars、libs/maven）与所有 AAR 消费点
   （各模块 build.gradle.kts、catalog alias、POM deps）；
2. 每个 AAR：谁消费（模块 + 配置 api/implementation/compileOnly）、是否 Maven 管理、
   是否实际被引用（类/资源被消费模块使用）、是否冗余（与其他 artifact 重叠）；
3. 结论表：keep / migrate-to-Maven / delete-candidate（附证据）；
4. 迁移与删除的影响面与回滚方式。

## 约束

只读审查；输出仅 `docs/architecture/2026-08-19-aar-dependency-audit.md` + 本 issue；
不删除/修改任何文件；不运行 Gradle 构建（可用 `gradlew dependencies` 类只读命令需架构师批准——
默认禁止，用静态分析）。

## 结果

审查完成，产出 `docs/architecture/2026-08-19-aar-dependency-audit.md`
（17.2KB）。基线 worktree `task-017-audit` @ commit `de0f2151`；未运行任何
Gradle；仅改 3 个 Allowed Path 文件（architecture doc 新建、本 issue 更新、
brief checklist 勾选）。

### 关键结论

- **(a) 迁移候选 = 0**：零直接 `files("*.aar")` 绕过 Maven 的引用；
  AGENTS.md §3.2 主张核实为真。全部 AAR 经 catalog + 本地 Maven 消费
  （§3 列出每个 alias 的 模块:行号:配置）。
- **(b) 删除候选**：
  1. `com.android.systemui:SystemUISharedLib`（maven 孤儿 AAR：无源 AAR、
     无消费、AGENTS.md §3.2 标"[旧] 遗留，待清理"、fat jar 1105 类与
     WM-Shell(177)/animationlib(5) 类重叠、规则 S 下已被 `:SystemUI-shared`
     源码取代）。删前需 `:app:assembleDebug` 验证无遗漏类。
  2. `com.android.systemui.flags:flags`（相邻 jar：catalog alias
     `android-systemui-flags` 无消费者；与 `libs/systemui-flags.jar` SHA 完全
     相同 = 内容重复；实际消费走顶层 jar。涉版本矩阵红线 #4，需用户决策
     删哪边）。
  3. 废弃脚本 `tools/gen_aar_maven.py`（文件头自警"失败实验"；
     AGENTS.md §1.4 标废弃）、`tools/rebuild_settingslib_aar.py`
     （2026-07-30 一次性补丁、硬编码非 worktree 路径、功能被
     CONFIGS["SettingsLib"] 取代、不解决当前阻塞点）、`tools/clean_aar_maven.py`
     （仅服务 gen_aar_maven 产物，随其废弃）。
- **keep（10 个被消费 AAR）**：全部有 ≥1 条实际引用证据——
  animationlib 149 文件、SettingsLib 289、WM-Shell 75、iconloader 8、
  WifiTrackerLib 9、LowLightDreamLib 4、setupcompat 3、SettingsLibColor 1
  （SideFpsOverlayViewModel.kt）、SettingsLibSettingsTheme 17 res（settingslib_switch）、
  WM-Shell-shared 11（PhysicsAnimator/ShellTransitions）。
- **重叠验证**：WM-Shell 主 vs shared 类集交集 = 0（AGENTS.md §4.2 主张为真）；
  SettingsLib-full.jar vs SettingsLib AAR = 0 重叠（互补，非删除依据，
  core:198 注释"0 重叠"为真）。
- **POM 全骨架**：11 个 maven AAR 的 POM 均无 `<dependencies>`（印证
  CHARTER Part 3 "POMs are dependency-free skeletons"）。

### 待用户决策（CHARTER Part 5 红线，需 architect 转呈）

1. 删 SystemUISharedLib（含删前 `:app:assembleDebug` 验证方案）。
2. flags 重复 jar：删 maven 坐标 + alias，还是删顶层 `libs/systemui-flags.jar`
   改走 Maven？（红线 #4 版本矩阵 + 依赖策略）
3. 废弃脚本三连删（`gen_aar_maven.py` / `rebuild_settingslib_aar.py` /
   `clean_aar_maven.py`）？
4. SettingsLib AAR 缺 `SettingsTheme/res/drawable-v31/settingslib_switch_{track,thumb}`
   （AGENTS.md §4.2 已记录，与本次审查正交；确认 SettingsLibSettingsTheme AAR
   是这些 drawable 的正确归属，待 Task 015/重新打包补齐）。

详见 `docs/architecture/2026-08-19-aar-dependency-audit.md` §6 结论表 + §7 待决策。
