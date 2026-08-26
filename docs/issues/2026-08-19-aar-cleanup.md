# 2026-08-19 — AAR/依赖清理（Task 018，执行 Task 017 审查结论）

## 背景

Task 017 审查（`docs/architecture/2026-08-19-aar-dependency-audit.md`）结论：
所有 AAR 已走本地 Maven，0 条直接 `files()` AAR 引用；10 个在消费 AAR 全部有引用证据。
删除候选经用户 2026-08-19 逐项批准。

## 用户决策（2026-08-19，明确批准）

1. **批准删除** `libs/maven/com/android/systemui/SystemUISharedLib/`（孤儿 AAR）——
   删除前需构建验证（编译类覆盖不受影响）；
2. **删 Maven 侧 flags jar**：删除 `libs/maven/com/android/systemui/flags/` +
   catalog alias `android-systemui-flags`——**Maven 仓只放 AAR**，
   `libs/systemui-flags.jar` 顶层 jar 保留不变；
3. **批准删除** 3 个废弃脚本：`tools/gen_aar_maven.py`、
   `tools/rebuild_settingslib_aar.py`、`tools/clean_aar_maven.py`；
4. 确认 SettingsTheme AAR 是 switch drawable 正确归属（Task 013/015 已覆盖，无动作）。

## 同步更新

- `gradle/libs.versions.toml`：删 `systemui-sharedlib` 与 `android-systemui-flags` 两行 alias；
- `AGENTS.md` §3.2 libs 清单：移除 SystemUISharedLib "[旧] 遗留，待清理" 行与
  maven flags 目录描述；`tools/` 表格移除 3 个废弃脚本条目；
- 本 issue 记录结果。

## 验收

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（如有引用被删脚本的测试需一并清理并说明）；
- `./gradlew :SystemUI-core:compileDebugKotlin :SystemUI-core:compileDebugJavaWithJavac`
  0 错误（验证 SystemUISharedLib 未独占任何编译所需类）；
- `git grep -n "sharedlib\|android-systemui-flags\|systemui.flags:flags\|gen_aar_maven\|rebuild_settingslib_aar\|clean_aar_maven" -- ':!docs/'`
  无残留引用（docs 历史记录除外）。

## 结果

执行日期：2026-08-19（worker 018）。

### 删除项

- `libs/maven/com/android/systemui/SystemUISharedLib/`（AAR+POM，孤儿坐标，无任何 build 引用）
- `libs/maven/com/android/systemui/flags/flags/1.0.0/`（jar+POM；`libs/systemui-flags.jar` 顶层 jar 保留不动）
- `tools/gen_aar_maven.py`、`tools/rebuild_settingslib_aar.py`、`tools/clean_aar_maven.py`
- `gradle/libs.versions.toml`：删 `systemui-sharedlib`、`android-systemui-flags` 两行 alias
  （连带删除悬空的重复段落头 `# Local Maven AARs (SystemUI modules)`；`androidx-lifecycle-service` 本属公网坐标，原分组即误置）

### 文档同步

- `AGENTS.md` §3.2 maven 树：删 SystemUISharedLib 行与 `com.android.systemui.flags/` 子树，`animationlib` 改为末枝 `└──`
- `AGENTS.md` §1.4：删 `gen_aar_maven.py` 废弃描述（对应条目同步）
- `AGENTS.md` §7 tools 表：3 个脚本本就不在表中，无需改动
- ~~`tools/install_aar_maven.py` docstring 删与 gen_aar_maven.py 的对比段~~：**已回退**（架构师 2026-08-19 范围纠正：该文件不在 Allowed Paths）；残留引用作为发现上报，见下

### 发现（超出 brief 范围，仅上报不处理）

- `tools/install_aar_to_maven.py` docstring（L13–14）仍提及已删的 `gen_aar_maven.py`（
  “与 gen_aar_maven.py 的区别：gen_aar_maven.py 把 R.jar 错误合并进 classes.jar（已废弃的失败实验）”）。
  导致验收 grep 在该文件残留 2 行匹配。建议下个 brief 授权后清理。
- 根目录存在 `scripts/extract_prebuilts.sh`（.sh，违反 ADR 0002 的历史遗留）与 `scripts/scaffold_aosp_modules.py`，均在 brief 范围外，仅报告不处理。
  （注记 2026-08-26 Task 063：两者及整个 `scripts/` 目录已经用户批准删除。）

### 验证（真实输出）

| 检查 | 删除前基线 | 删除后 | 结论 |
|------|-----------|--------|------|
| `python3 -m unittest discover -s tools/tests -p 'test_*.py'` | Ran 148 tests / OK | Ran 148 tests / OK | 无回归（无测试引用被删脚本，tools/tests/ 未改） |
| `./gradlew :SystemUI-core:compileDebugKotlin :SystemUI-core:compileDebugJavaWithJavac` | BUILD SUCCESSFUL（0 错误） | BUILD SUCCESSFUL in 47s（0 错误） | SystemUISharedLib Maven AAR 未独占任何编译所需类 |
| issue grep `git grep -n "sharedlib\|android-systemui-flags\|systemui.flags:flags\|gen_aar_maven\|rebuild_settingslib_aar\|clean_aar_maven" -- ':!docs/'` | — | 仅余 `tools/install_aar_to_maven.py` L13–14 docstring 提及已删脚本（范围纠正后回退未改，见“发现”） | 其余无残留 |
| brief grep `git grep -n "SystemUISharedLib\|systemui-sharedlib\|..." -- ':!docs/' ':!libs/maven/com/android/server'` | — | 仅余 AOSP Soong 源码模块名 `SystemUISharedLib`（Android.bp / :SystemUI-shared build 文件 / check_source_alignment / scaffold 脚本），均指源码模块而非已删 Maven 产物，须保留（规则 S/B） | 无残留 |
| `git diff --check`（含 --cached） | — | 干净 | — |

### 备注

- 本次未运行 `:app:assembleDebug`（不在验收范围；SettingsLib switch drawable 阻塞另行跟踪）。
