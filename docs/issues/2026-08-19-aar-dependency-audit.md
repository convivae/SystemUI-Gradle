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

待填。
