# Task 013 — SettingsLibSettingsTheme AAR 资源闭包

## 背景

Task 012 已将 AGP `androidprv` namespace 错误从 20 降至 0。当前
`:app:processDebugResources` 首个失败层为：

```text
resource drawable/settingslib_switch_track not found
resource drawable/settingslib_switch_thumb not found
```

两个资源来自 AOSP：

- `frameworks/base/packages/SettingsLib/SettingsTheme/res/drawable-v31/settingslib_switch_track.xml`
- `frameworks/base/packages/SettingsLib/SettingsTheme/res/drawable-v31/settingslib_switch_thumb.xml`
- `settingslib_switch_track` 另有 `drawable-v34` 变体

`SettingsLibSettingsTheme` 是真实 Soong `android_library`，定义于
`SettingsLib/SettingsTheme/Android.bp`。多个 SettingsLib 子模块通过
`static_libs` 消费它；SystemUI 自有 `res/values/styles.xml` 也引用上述 drawable。

## 根因与方案

当前 `libs/aars/SettingsLib.aar` 只打包 `SettingsLib/res`。不能把
`SettingsTheme/res` 直接作为第二个 raw resource root 合并进同一 AAR：两棵树有
89 个同相对路径 XML（主要是 values locale 文件），现有严格打包器会正确拒绝；
覆盖或自行合并 XML 会破坏原始 AOSP 资源字节和规则 R。

采用与 Soong target 一致的独立 res-only AAR：

- artifact：`SettingsLibSettingsTheme`
- group/name/version：`com.android.systemui:SettingsLibSettingsTheme:1.0.0`
- raw res：完整复制 `SettingsLib/SettingsTheme/res`，不修改字节
- manifest：原始 `SettingsTheme/AndroidManifest.xml`
- R.txt：Soong `SettingsLibSettingsTheme/android_common/R.txt`
- consumer：`:SystemUI-res` 使用 catalog alias 显式 `api(...)`

这是 tier ② AOSP 含资源产物；不存在对应的未 fork 公网 Maven 产物。沿用已确认存在资源依赖冲突后的本地 Maven AAR 交付机制，不引入新版本。

## 用户授权

用户于 2026-08-19 明确批准继续重新打包 SettingsLib/SettingsTheme 资源。该授权覆盖：

- 新增上述 AOSP AAR 和本地 Maven AAR/POM；
- 在 version catalog 新增固定 `1.0.0` alias（不升级任何版本）；
- 在 `SystemUI-res/build.gradle.kts` 增加资源依赖；
- 不授权修改任何 `SystemUI-*/res*/**` 或 AOSP 源文件。

## 实施步骤

1. TDD：先为 config、完整文件集、字节一致性、Maven 注册写失败测试。
2. 在 `tools/package_aosp_aar.py` 注册 res-only `SettingsLibSettingsTheme`。
3. 在 `tools/install_aar_to_maven.py` 注册固定本地坐标。
4. 生成并提交 direct AAR 与 local Maven AAR/POM。
5. 新增 catalog alias，并从 `:SystemUI-res` 显式接入。
6. 运行全部 Python tests、artifact provenance 校验及 clean resource link。
7. 若 resource link 通过，运行 `:app:assembleDebug`；若暴露新层，只记录首个失败任务和首批错误，不扩大 Task 013 范围。

## 验收

- Python tests 全部 `OK`，数量大于 131。
- AAR 中 `res/**` 文件集与 AOSP SettingsTheme `res/**` 完全一致，逐文件字节一致。
- direct AAR 和 local Maven AAR SHA-256 相同。
- `:app:processDebugResources` 不再报告两个 `settingslib_switch_*` 缺失；目标为命令 exit 0 且输出含 `BUILD SUCCESSFUL`。
- 没有修改任何 `SystemUI-*/src/**`、`SystemUI-*/res*/**`、AOSP 文件、版本号或模块边界。

## 实施结果（2026-08-19 执行）

### TDD 波次（tools）

1. RED：先在 `tools/tests/test_package_aosp_aar.py` 新增
   `test_settingslib_settings_theme_config_paths` + `TestSettingsLibSettingsThemeProvenance`
   （4 个用例：完整 res 集合/字节比对、switch drawable 三项、无代码 entry、重建字节一致），
   并把 CONFIGS 集合断言更新为 10 个；在 `tools/tests/test_install_aar_to_maven.py` 新增
   `ArtifactRegistryTest.test_settingslib_settings_theme_coordinate`。
   焦点运行结果：7 个失败/错误，全部为缺少 `SettingsLibSettingsTheme` 注册项，无无关失败。
2. GREEN：`tools/package_aosp_aar.py` CONFIGS 新增 res-only 配置（code=[]），
   `tools/install_aar_to_maven.py` ARTIFACTS 新增固定坐标
   `com.android.systemui:SettingsLibSettingsTheme:1.0.0`。
   `python3 -m unittest tools.tests.test_package_aosp_aar tools.tests.test_install_aar_to_maven`
   → Ran 39 tests, OK。

### 生成与安装

```
python3 tools/package_aosp_aar.py SettingsLibSettingsTheme
  → libs/aars/SettingsLibSettingsTheme.aar (142016 bytes)
python3 tools/install_aar_to_maven.py SettingsLibSettingsTheme
  → libs/maven/com/android/systemui/SettingsLibSettingsTheme/1.0.0/{SettingsLibSettingsTheme-1.0.0.aar,.pom}
```

### 溯源验证（Python/zipfile 实测）

- AAR `res/**` 共 174 个文件，集合与 AOSP `SettingsLib/SettingsTheme/res/**` 完全一致，逐文件字节相同；
- `res/drawable-v31/settingslib_switch_track.xml`、`res/drawable-v31/settingslib_switch_thumb.xml`、
  `res/drawable-v34/settingslib_switch_track.xml` 三项均在；
- direct AAR 与 Maven AAR SHA-256 相同：
  `0cb09355bd3757a3990fb514bbdc0838104bc4a399fa0f5ef6f890e3cf3f1a43`。

### 接线

- `gradle/libs.versions.toml` 仅新增一行：
  `systemui-settingslib-theme = { group = "com.android.systemui", name = "SettingsLibSettingsTheme", version = "1.0.0" }`
- `SystemUI-res/build.gradle.kts` 在既有 SettingsLib 依赖旁新增 `api(libs.systemui.settingslib.theme)` + 注释，
  未改任何既有行。

### Python 全量测试

`python3 -m unittest discover -s tools/tests -p 'test_*.py'` → **Ran 137 tests, OK**（>131）。

### 资源链接验收（真实结果）

```
./gradlew :app:clean :app:processDebugResources --console=plain 2>&1 | tee /tmp/task013.log
→ BUILD FAILED in 15s（exit 非 0）
```

- `grep -cE 'settingslib_switch_(track|thumb).*not found' /tmp/task013.log` → **0**
  （两个 switch drawable 缺失错误全部消失，本任务核心目标达成）。
- 但浮出新失败层（首失败任务 `:app:processDebugResources`，共 5 条 AAPT error / 3 类资源）：

  | 缺失资源 | 引用处 | AOSP 归属 |
  |---|---|---|
  | `interpolator/progress_indeterminate_horizontal_rect2_translatex_copy` | SystemUI-res `anim/progress_indeterminate_horizontal_rect.xml` | `SettingsLib/ProgressBar/res` |
  | `style/SettingsLibActionButton` | SystemUI-res `layout/audio_sharing_dialog.xml`（98/114 行） | `SettingsLib/ActionButtonsPreference/res` |
  | `layout/preference_two_target_divider` | SettingsLib AAR `layout-v33/preference_access_point.xml`、`preference_checkable_two_target.xml` | `SettingsLib/TwoTargetPreference/res` |

  根因与 SettingsTheme 同构：合并版 `SettingsLib.aar` 只打包主 target 的 `SettingsLib/res`，
  而其它 static_libs 子模块（ProgressBar / ActionButtonsPreference / TwoTargetPreference）
  的 res 同样未打包，被引用时即报 not found。

- 按计划 Step 5 约定：switch 错误归零后出现新层 → 只记录首失败任务与首批错误组，不扩大 Task 013 范围。
- 资源链接未通过 → 按验收条件**不运行** `:app:assembleDebug`（APK 诊断仅在链接通过后允许）。

### 合规检查

- 改动路径全部在 brief Allowed Paths 内；未触碰任何 Forbidden Path（SystemUI-*/src、res*、AOSP 文件、既有 artifact、版本矩阵等）。
- `git diff --check` 无输出。

## 错误数演变

| 检查点 | 结果 |
|---|---|
| Task 012 后 | androidprv 0；SettingsLib switch drawable 缺失 2 类 |
| Task 013 后 | switch drawable 缺失 0（grep=0）；新层：5 条 AAPT error / 3 类缺失资源（ProgressBar / ActionButtonsPreference / TwoTargetPreference 子模块 res 未打包），`:app:processDebugResources` 失败 |

## 待解决问题

- 下一层（非 Task 013 范围）：架构师合并后审计 `SettingsLib` 的直接 `static_libs`，发现不是只有当前报错的 3 个 target，而是 **29 个**直接子 target 拥有 `resource_dirs`。只补 `ProgressBar`、`ActionButtonsPreference`、`TwoTargetPreference` 可以继续推进链接，但不能证明已复制 SettingsLib 的完整 Soong 资源闭包，且未被 XML 直接引用的资源可能直到运行时才暴露。
- 推荐另立 Task 014：先形成完整 resource-owner/依赖闭包清单，再决定使用“每个真实 Soong target 一个 res-only AAR + SettingsLib POM 传递依赖”还是显式 consumer 依赖；这属于本地 Maven 依赖语义的架构决策，需用户批准后实施。不得把存在重复相对路径的 raw res 静默合并进单一 AAR。
- 当前已确认的三个首层 target 分别有 10、15、7 个原始资源文件；它们仍应包含在 Task 014 闭包中。
- Task 013 完成后按真实 `:app:assembleDebug` 输出决定下一层；本次资源链接未通过，APK 未生成。
