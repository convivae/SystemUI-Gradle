# Task 015 — SettingsLib 资源闭包 B2 实施（7 个 res-only AAR + POM 传递依赖）

## Goal

按用户批准的 B2 方案（Task 016 调研）实施 SettingsLib 资源闭包：
新增 **7 个 per-target res-only AAR**，通过 ADR 0005 的 POM 传递依赖接线，
使 `./gradlew :app:clean :app:processDebugResources` exit 0（BUILD SUCCESSFUL）。

## 已获用户明确预批准（2026-08-19）

1. 新增 7 个 res-only AAR（坐标 `com.android.systemui:<Target>:1.0.0`）：
   `SettingsLibSelectorWithWidgetPreference`、`SettingsLibRestrictedLockUtils`、
   `SettingsLibActionButtonsPreference`、`SettingsLibProgressBar`、
   `SettingsLibTwoTargetPreference`、`SettingsLibLayoutPreference`、`SettingsLibAdaptiveIcon`。
2. `tools/install_aar_to_maven.py` 支持 POM `<dependencies>`（仅 SettingsLib 闭包使用）；
   `SettingsLib` POM 携带上述 7 条依赖边（架构师已核实 7 者均为主 bp 直接
   `static_libs`，严格镜像 `Android.bp`）。
3. `gradle/libs.versions.toml` 新增 7 个固定 `1.0.0` alias（注册表；不升级任何版本）。
4. CHARTER Part 3 与 AGENTS.md §3.2 的"POM 骨架"事实性措辞同步（只改措辞，不改规则语义）。
5. Task 013 的 `api(libs.systemui.settingslib.theme)` 显式接线与 Color 接线**保持不变**；
   consumer 不新增依赖行。

## Non-goals

- 不改动 SettingsLib.aar / SettingsTheme.aar / Color.aar 的 AAR 字节（只重发 SettingsLib POM）；
- 不触碰 SystemUI 源码/res、AOSP 树、其他 artifact、依赖版本、模块边界；
- 不做 Task 017 的 AAR 审计/清理。

## Allowed Paths

- `tools/package_aosp_aar.py`、`tools/install_aar_to_maven.py`
- `tools/tests/test_package_aosp_aar.py`、`tools/tests/test_install_aar_to_maven.py`
- `libs/aars/SettingsLib{SelectorWithWidgetPreference,RestrictedLockUtils,ActionButtonsPreference,ProgressBar,TwoTargetPreference,LayoutPreference,AdaptiveIcon}.aar`（新生成）
- `libs/maven/com/android/systemui/SettingsLib<Target>/**`（新安装）
- `libs/maven/com/android/systemui/SettingsLib/1.0.0/SettingsLib-1.0.0.pom`（重发，加 deps）
- `gradle/libs.versions.toml`（仅新增 7 行 alias）
- `docs/issues/2026-08-19-settingslib-per-target-aars.md`、`docs/orchestration/CHARTER.md`、
  `AGENTS.md`（仅 §3.2 措辞）、`docs/orchestration/tasks/015-settingslib-per-target-aars.md`（本文件勾选）

## Execution Hints

1. 先 worker-contract skill 输出 `CONTRACT:`；
2. 用 test-driven-development skill：先写失败测试（POM deps 渲染 + 7 个 CONFIG 注册），再实现；
3. 7 个 CONFIGS 以现有 `SettingsLibSettingsTheme` 条目为模板（`code=[]`、res 源目录、
   Soong `android_common/R.txt`）；各 target 的 Soong intermediates 路径先 `ls` 核实；
4. 生成后逐 AAR 验证 provenance：`res/**` 与 AOSP 源树逐文件 byte-exact、
   direct AAR 与 Maven AAR SHA-256 相同、POM 含 7 条 dependency 且无多余；
5. 构建验证用 `./gradlew :app:clean :app:processDebugResources`，统计
   `not found` 资源错误数与 `settingslib_switch_` 命中数（应全 0）；
6. 其后运行 `:app:assembleDebug` 诊断：成功→记录 APK 路径/大小/SHA-256；
   失败→只记首个失败任务与首批错误，不扩大修复范围；
7. 更新 issue 的错误数演变表；`git diff --check` 干净；英文 commit；**不 push**。

## Acceptance

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` 全套 OK（基线 137）
- 7 个 AAR 存在且 provenance 验证通过（byte-exact + SHA-256 一致）
- `libs/maven/com/android/systemui/SettingsLib/1.0.0/SettingsLib-1.0.0.pom` 含 7 条 dependency
- `./gradlew :app:clean :app:processDebugResources` exit 0 且输出 `BUILD SUCCESSFUL`
- issue 文档如实记录 assembleDebug 诊断结果

## Report

完成后汇报：commit、逐条 checklist（含真实命令输出）、issue 更新、新发现、HANDOFF 块。
