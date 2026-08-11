# AAR 统一到 Maven catalog（参考项目模式）

> **修订（2026-08-12）**：本文中 “`libs/aars/` 和 `libs/maven/` 为 gitignored 中间产物” 的策略已变更——
> 用户 2026-08-12 明确要求 **`libs/`（含 jar/aars/maven）全部提交入 git**，新 clone 可直接构建，
> 无需先跑 `package_aosp_aar.py` / `install_aar_to_maven.py`。其余 catalog 统一管理机制不变。

> **背景**: 用户 2026-08-11 建议: "所有的maven格式的aar都可以使用libs.versions.toml进行统一管理,就像参考项目一样"。
> 本项目 Phase B 走 direct AAR 路径(`libs/aars/*.aar` + `files()`),build.gradle.kts 里出现 13 处
> `files("${rootProject.projectDir}/libs/aars/xxx.aar")` 重复路径,不便统一管理。

## 现状

- `libs/aars/` 6 个 AAR: `SettingsLib.aar`, `WifiTrackerLib.aar`, `WindowManager-Shell-shared.aar`,
  `WindowManager-Shell.aar`, `animationlib.aar`, `iconloader.aar`
- 13 处 `files()` 引用,分布于 6 个 module: core, res, customization, animation, compose, shared
- `settings.gradle.kts` 已有 `maven { url = uri("${rootProject.projectDir}/libs/maven") }` 配置
- 此前 Phase B Task 7 删除了 4 个旧 catalog alias(对应被污染的 Maven AAR),仓内残留 `SystemUISharedLib` 与 `flags`

## 参考项目模式(CarSystemUIGradle)

参考项目的 Maven AAR 干净(R=0, sysui=0),可复用其模式:

1. AAR 放 `libs/maven/<group>/<name>/<version>/<name>-<version>.aar`
2. 简单 POM 骨架(仅 groupId/artifactId/version/packaging,无 transitive deps)
3. `libs.versions.toml` 声明 alias: `systemui-settingslib = { group = "com.android.systemui", name = "SettingsLib", version = "1.0.0" }`
4. `build.gradle.kts` 用 `implementation(libs.systemui.settingslib)`

## 方案

1. 新增工具 `tools/install_aar_to_maven.py`: 把 `libs/aars/*.aar` 安装到 `libs/maven/` 并生成 POM
2. 在 `libs.versions.toml` 加 6 个 alias(group `com.android.systemui`,version `1.0.0`)
3. 替换所有 `files(libs/aars/xxx.aar)` 为 catalog 引用
4. 验证: `gradlew projects` + core 编译错误数不退化
5. 切换完成后,`libs/aars/` 中的 AAR 已无消费者,可删除

## 关键决策

- **groupId 统一 `com.android.systemui`**: 参考项目全部用这个(即使 WM-Shell 在 AOSP 是 frameworks 库)。简单统一。
- **version `1.0.0`**: 参考项目一致
- **POM 无 transitive deps**: 避免依赖地狱。AAR 自身不引入传递依赖,由消费方显式声明。
- **保留 direct AAR 生成工具**: `tools/package_aosp_aar.py` 继续负责生成 `libs/aars/*.aar`,新工具负责"安装到 Maven 仓"。两阶段分离。

## 与 ADR 0001 的关系

ADR 0001 的原文是: "AAR 先直接引入,确认冲突后才用 local Maven"。本项目 Phase B 已走 direct AAR 验证流程
(确认无冲突后),现在用户明确要求统一 catalog 管理,这属于用户明确指令(优先级最高)。
本质上这是"确认无冲突后,统一采用 Maven 仓模式管理"。

## 待办

- [x] 写 `tools/install_aar_to_maven.py` + 单测（8 tests PASS）
- [x] 安装 6 个 AAR 到 `libs/maven/`
- [x] 更新 `libs.versions.toml` 6 个 alias
- [x] 替换 13 处 files() 引用
- [x] 验证 `gradlew projects` + core 编译（BUILD SUCCESSFUL，错误数 234 未退化）
- [x] 删除 `libs/aars/` 目录（gitignore，git rm --cached，磁盘保留为中间产物）
- [x] 更新 AGENTS.md（§1.1、§2.3、§3.2）
- [x] 提交

## 结果

- core 编译错误数：234（与切换前一致，未退化）
- `gradlew projects` BUILD SUCCESSFUL
- 8 个单测 PASS
- 0 处残留 `files(libs/aars/...)` 引用

## 待用户决策：libs/aars/ vs libs/maven/ 的 check-in 策略

**用户决策（2026-08-11）**：
- `libs/maven/` gitignore（保持）
- `libs/aars/` gitignore（中间产物，不入版本控制）
- 项目代码只用 Maven catalog 形式引用 AAR（已实现）
- 构建前需跑工具恢复 AAR

**已执行**：
- `.gitignore` 加 `libs/aars/`
- `git rm --cached` 6 个 AAR（磁盘保留）
- `package_aosp_aar.py` 加 `--all` 选项（+2 单测）
- 验证完整工作流：清空 → `package_aosp_aar.py --all` → `install_aar_to_maven.py` → `gradlew projects` BUILD SUCCESSFUL

**构建前置步骤**（新 clone 或清空后）：
```bash
python3 tools/package_aosp_aar.py --all    # 生成 libs/aars/*.aar
python3 tools/install_aar_to_maven.py       # 安装到 libs/maven/
./gradlew :app:assembleDebug
```
