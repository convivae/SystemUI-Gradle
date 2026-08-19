# Task 015 — SettingsLib per-target res-only AAR 闭包（POM 传递依赖）

> **状态（2026-08-19 实施完成）**：用户采纳 Task 016 推荐的 **B2（可达性驱动最小集）**：
> 在既有 main/Color/SettingsTheme 三个 AAR 基础上新增 **7 个** per-target res-only AAR
> （对比原 30-AAR 上限基线降 77%），经 ADR 0005 POM 传递依赖接线。
> 实施结果见文末「实施结果（2026-08-19 执行）」；`:app:processDebugResources` 与
> `:app:assembleDebug` 均 BUILD SUCCESSFUL，首个 APK 已产出。

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

## 实施结果（2026-08-19 执行，B2 方案）

### TDD 波次（tools）

1. RED：`tools/tests/test_install_aar_to_maven.py` 新增 4 个用例（7 坐标注册、SettingsLib
   POM 7 条 deps、闭包成员无 deps、`install_aar` deps 参数渲染 `<dependencies>` +
   `install_all` 透传 + 骨架 POM 无 `<dependencies>`）；
   `tools/tests/test_package_aosp_aar.py` 新增 `test_settingslib_closure_seven_target_configs`
   + `TestSettingsLibPerTargetProvenance`（4 用例：res 逐字节溯源/keystone 资源/res-only/
   重建字节一致）并把 CONFIGS 集合断言更新为 17。
   焦点运行：11 个失败/错误，全部为缺少注册/deps 支持，无无关失败。
2. GREEN：`tools/package_aosp_aar.py` CONFIGS 新增 7 个 res-only 配置（code=[]，
   res/manifest 取各自 AOSP 子目录，rtxt 取 Soong `android_common/R.txt`）；
   `tools/install_aar_to_maven.py` ARTIFACTS 新增 7 坐标 + SettingsLib `deps` 字段，
   POM 模板支持可选 `<dependencies>` 渲染。
   `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → **Ran 148 tests, OK**
   （基线 137 + 11 新增）。

### 生成与安装

```
python3 tools/package_aosp_aar.py SettingsLib<Target>   # 逐个打包 7 个
python3 tools/install_aar_to_maven.py SettingsLib SettingsLib<Target>...  # 重发 SettingsLib POM + 安装 7 个
```

产物（libs/aars/ + libs/maven/ 双份）：

| Target | res 文件数 | AAR 字节 |
|---|---|---|
| SettingsLibSelectorWithWidgetPreference | 92 | 67343 |
| SettingsLibRestrictedLockUtils | 87 | 73913 |
| SettingsLibActionButtonsPreference | 15 | 12524 |
| SettingsLibProgressBar | 10 | 9794 |
| SettingsLibTwoTargetPreference | 7 | 7809 |
| SettingsLibLayoutPreference | 6 | 6194 |
| SettingsLibAdaptiveIcon | 3 | 2922 |

文件数与 Task 016 调研结论逐一吻合（92/87/15/10/7/6/3）。

### 溯源验证（Python/zipfile + hashlib 实测）

- 7 个 AAR `res/**` 与 AOSP 对应子目录逐文件 byte-exact、文件集完全一致；
- 7 组 direct AAR 与 Maven AAR SHA-256 相同；
- `SettingsLib-1.0.0.pom` 含恰好 7 条 `<dependency>`（按 bp static_libs 顺序），无多余；
- 7 个新 POM 均为骨架（无 `<dependencies>`）；AAR 字节未改（SettingsLib.aar 仅重发 POM）。

### 接线

- `gradle/libs.versions.toml` 仅新增 7 行固定 `1.0.0` alias（注册表登记，未被 build 文件引用）；
- consumer 未新增依赖行：Task 013 的 `api(libs.systemui.settingslib.theme)` 与 Color 接线保持不变。

### 资源链接验收（真实结果）

```
./gradlew :app:clean :app:processDebugResources --console=plain
→ BUILD SUCCESSFUL in 25s（exit 0）
```

- `grep -c 'not found'` → **0**；`grep -c 'settingslib_switch_'` → **0**。

### APK 诊断（assembleDebug，真实结果）

```
./gradlew :app:assembleDebug --console=plain
→ BUILD SUCCESSFUL in 2m 46s（exit 0）
```

- **首个 SystemUI APK 产出**：`app/build/outputs/apk/debug/app-debug.apk`
- 大小：158,775,460 bytes（约 151.5 MB）
- SHA-256：`35c7e3f6881328a4e26c1ea3ddf6ae8f844ef5e1599f082ae1b70a87c0336e86`
- javac 阶段仅 2 条 warning（SystemApi$Client 注解类缺失的 known warning + dep-ann），无 error。

### 文档同步

- CHARTER Part 3：「POM 是 dependency-free 骨架」→「默认骨架；SettingsLib 闭包例外（ADR 0005，7 条边）」；
- AGENTS.md §3.2：同步同一事实性措辞（不改规则语义）。

### 合规检查

- 改动路径全部在 brief Allowed Paths 内；未触碰 SystemUI-*/src、res*、AOSP 树、
  既有 AAR 字节、依赖版本、模块边界、consumer build 文件；
- `git diff --check` 干净。

## 错误数演变

| 检查点 | 结果 |
|---|---|
| Task 013 后 | switch 0；3 组子模块资源缺失（5 条 AAPT error） |
| Task 015 后（B2） | `:app:processDebugResources` BUILD SUCCESSFUL（not found 0 / switch 0）；`:app:assembleDebug` BUILD SUCCESSFUL，首个 APK 产出 |

## 待解决问题

- Task 017（AAR 依赖审计）：闭包外引用（WifiTrackerLibRes/iconloader/setupdesign）与其它 artifact 的接线审计，不在本任务范围；
- 首个 APK 未经设备安装/运行验证（smali 完整性、R 类运行期引用等），后续需要真机/模拟器诊断；
- Deferred Follow-ups 不变（Room schema 导出、Kotlin 2.3 data-class copy、manifest 重复权限、
  评估移除 `android.disallowKotlinSourceSets=false`）。
