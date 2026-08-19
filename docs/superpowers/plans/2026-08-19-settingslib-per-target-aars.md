# Task 015 实施计划 — SettingsLib 资源闭包 B2（7 个 per-target res-only AAR + POM 传递依赖）

## 目标

`./gradlew :app:clean :app:processDebugResources` exit 0（BUILD SUCCESSFUL），
`not found` 资源错误归零，`settingslib_switch_*` 保持 0。

## 设计定稿（用户 2026-08-19 批准）

- 方案 B2（Task 016 调研推荐）：新增 **7 个** res-only AAR
  （SelectorWithWidgetPreference 92f、RestrictedLockUtils 87f、ActionButtonsPreference 15f、
  ProgressBar 10f、TwoTargetPreference 7f、LayoutPreference 6f、AdaptiveIcon 3f）。
- POM 传递依赖（ADR 0005）：7 个 target 经架构师核实**均为** SettingsLib 主 bp 直接
  `static_libs` → `SettingsLib` POM 携带 7 条 dependency 边，严格镜像 `Android.bp`。
- `SettingsLibSettingsTheme` / `SettingsLibColor` 现有显式接线**不动**。
- consumer 不需要新增任何 `api(...)` 行（传递获得）。

## 步骤

1. **TDD RED**：`tools/tests/test_install_aar_to_maven.py` 新增 POM `<dependencies>` 渲染测试；
   `tools/tests/test_package_aosp_aar.py` 新增 7 个 res-only CONFIG 注册测试 → 失败。
2. **实现**：
   - `tools/package_aosp_aar.py`：按 `SettingsLibSettingsTheme` 模板新增 7 个 CONFIGS
     （`code=[]`，res = AOSP target `res/`，R.txt = Soong `android_common/R.txt`）。
   - `tools/install_aar_to_maven.py`：`ARTIFACTS` 支持可选 `deps` 字段并渲染
     `<dependencies>`；注册 7 个 `com.android.systemui:<Target>:1.0.0`；
     `SettingsLib` 条目 deps = 7 个新坐标。
3. **GREEN**：焦点测试通过 → 全套 `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK。
4. **生成产物**：`python3 tools/package_aosp_aar.py --all` +
   `python3 tools/install_aar_to_maven.py`；逐 AAR 验证 res 与 AOSP byte-exact、
   direct 与 Maven AAR SHA-256 相同、SettingsLib POM 含 7 条 dependency。
5. **catalog**：`gradle/libs.versions.toml` 新增 7 个固定 `1.0.0` alias（注册表用途）。
6. **构建验证**：`:app:clean :app:processDebugResources` exit 0；
   然后 `:app:assembleDebug` 诊断并如实记录。
7. **文档**：issue 结果、ADR 0005 保持不变、CHARTER/AGENTS.md 的 POM 骨架措辞同步
   （用户已随方案 B 授权）。

## 验收

- unittest 全套 OK（>137）
- 7 个 AAR provenance byte-exact；SettingsLib POM 7 deps
- `processDebugResources` BUILD SUCCESSFUL
- 文档如实记录 assembleDebug 结果（成功 → 路径/大小/SHA-256；失败 → 首个失败任务 + 首批错误）
