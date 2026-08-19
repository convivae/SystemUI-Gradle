# Task 015 — SettingsLib per-target res-only AAR 闭包（POM 传递依赖）

> **状态（2026-08-19 更新）**：用户认可方案 B（POM 传递依赖，ADR 0005），
> 但认为 30 个新 AAR 数量过多，要求先派发 Task 016 调研"合规降数量"的选项
> （无冲突分组 / 可达性最小集 / R namespace 运行期实证 / AGP 机制）。
> 本文档中的 30-AAR 清单为上限基线，实施数量待 Task 016 结论与用户再决策。

## 背景

Task 014 调研（`docs/architecture/2026-08-19-settingslib-resource-closure-research.md`）结论：

- SettingsLib 完整资源闭包 = 33 个 res-owning Soong target / 1512 文件 / 101 组同相对路径；
- 主 target res 已在 `SettingsLib.aar`；`SettingsLibSettingsTheme`、`SettingsLibColor` 已有独立 AAR；
- 需新增 **30 个** res-only AAR；
- 单一合并 AAR 违反规则 R（参考项目实证）；Soong 无可复用合并产物；
- per-target AAR 还顺带修复子模块 R 类运行期悬空引用（merged classes.jar 的 `getstatic` 子包 R）。

用户 2026-08-19 明确选择 **方案 B：per-target AAR + POM 传递依赖**，AAR 统一由本地 Maven 管理
（ADR 0005）。

## 用户授权范围（2026-08-19）

- 30 个新 res-only AAR + 对应本地 Maven AAR/POM；
- `install_aar_to_maven.py` 支持 POM `<dependencies>`（仅 SettingsLib 闭包）；
- `gradle/libs.versions.toml` 新增 30 个固定 `1.0.0` alias（注册表；不升级任何版本）；
- `SystemUI-res/build.gradle.kts` 移除 Task 013 的显式 theme `api(...)`（改传递获得）；
- CHARTER Part 3 与 AGENTS.md §3.2 的"POM 骨架"事实性措辞同步；
- 新增 ADR 0005。

## 目标

`./gradlew :app:clean :app:processDebugResources` exit 0（BUILD SUCCESSFUL），
所有 `not found` 资源错误归零，`settingslib_switch_*` 保持 0。

## 关键设计

1. POM 依赖边机械镜像 `Android.bp static_libs`：
   - `SettingsLib` POM deps = 30 个直接子 target；
   - 子 target POM deps = 其 bp 中的 SettingsLib* static_libs（典型为 `SettingsLibSettingsTheme`；
     `SettingsLibIllustrationPreference` 另有 `SettingsLibColor`）；
   - 非 SettingsLib 依赖（WifiTrackerLibRes/iconloader/setupdesign）不进 POM（另行审计）。
2. 每个 AAR：`res/**` 与 AOSP 逐文件 byte-exact + 原始 `AndroidManifest.xml` + Soong `R.txt`，
   `code=[]`，版本 `1.0.0`。
3. target 清单必须重新从 Android.bp 用 brace-aware 解析导出（含默认 resource_dirs 情形），
   并与调研文档 §4.2 的 33/30 数字对账；任何差异停下报告。
4. consumer 只保留 `api(libs.systemui.settingslib)`。

## 验收

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（>137）；
- 每个新 AAR：res 集合/字节与 AOSP 源树一致；direct 与 Maven AAR SHA-256 相同；
- SettingsLib POM 含 30 条 dependency；子 POM 边与 bp 一致；
- `:app:clean :app:processDebugResources` exit 0 且 `BUILD SUCCESSFUL`；
  `not found` 资源错误计数为 0；
- 其后运行 `:app:assembleDebug` 诊断并如实记录（成功则记录 APK 路径/大小/SHA-256；
  失败则只记录首个失败任务与首批错误，不扩大范围）。

## 错误数演变

| 检查点 | 结果 |
|---|---|
| Task 013 后 | switch 0；3 组子模块资源缺失（5 条 AAPT error） |
| Task 015 后 | 待执行 |
