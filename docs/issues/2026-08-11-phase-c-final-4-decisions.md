# 2026-08-11 Phase C 收尾：4 项版本/依赖决策落地

> **修订（2026-08-12）**：本文落地的版本（material 1.13.0-alpha08、material3 1.4.0-alpha09、
> Room 2.7.0-beta01、Dagger 2.55 + 手动 `useBindingGraphFix`）已在 2026-08-12 的**全依赖升级**中被超越：
> Dagger → 2.59.2（useBindingGraphFix 默认启用，手动 arg 已移除）、material3 → 1.5.0-alpha18、
> Room → 2.8.4、Compose → 1.11.4，并迁移到 AGP `builtInKotlin=true`。
> 详见 `docs/issues/2026-08-12-deps-upgrade-builtin-kotlin.md`。本文保留作为决策过程的历史记录。

## 背景

core Kotlin 编译剩余 8 个错误（commit `44f6b03c` 后）。用户对 4 个问题做出决策：

1. **问题 A（material-design-x）**：用户选择"接受本地 jar"。但调查发现 Google Maven 实际有
   `1.13.0-alpha08`，且与 AOSP `material-design-x` prebuilt **字节完全一致**（1985863 bytes）。
   按规则③（标准第三方库优先官方 Maven 坐标），改用 Maven 坐标而非本地 jar。
2. **问题 B（Room）**：用户选择"一起升级" Room runtime + compiler。
3. **问题 C（SettingsLib res）**：用户选择"现在做" SettingsLibColor 资源合并。
4. **问题 D（KSP Dagger）**：用户选择"现在配置" KSP 跑 Dagger。

## 剩余 8 个错误明细

| # | 错误 | 文件 | 根因 | 解决方案 |
|---|------|------|------|---------|
| 1-2 | `DaggerReferenceGlobalRootComponent` | SystemUIInitializerImpl.kt:20,28 | KSP 未跑 Dagger | 配置 KSP + dagger-compiler |
| 3 | `color` (settingslib_color_blue400) | SideFpsOverlayViewModel.kt:194 | SettingsLibColor 资源缺失 | 打 SettingsLibColor AAR |
| 4 | `setShowTitleItems` | SliceAndroidView.kt:49 | slice 1.0.0 缺方法 | 升级 slice → 1.1.0-alpha02 |
| 5 | `dropAllTables` | CommunalDatabase.kt:70 | Room 2.6.1 无此参数 | 升级 Room → 2.7.0-beta01 |
| 6 | `shape` (IconButton) | EditModeButton.kt:48 | material3 1.3.1 无 shape | 升级 material3 → 1.4.0-alpha09 |
| 7-8 | `trackIconActiveColor/End` | VolumeDialogSliderViewBinder.kt:52,72 | Material 1.12.0 缺方法 | 升级 material → 1.13.0-alpha08 |

## 操作步骤

### Task 1: material 1.12.0 → 1.13.0-alpha08（Maven 坐标）

**调查结论**：
- Google Maven 有 `com.google.android.material:material:1.13.0-alpha08`
- AOSP `material-design-x` 仓库的 `classes.jar`（1985863 bytes）与 Maven 版本**字节完全一致**
- `trackIconActiveColor`/`trackIconActiveEnd` 在 1.13.0-alpha08 的 Slider 类中确认存在
- 按规则③，标准第三方库优先使用官方 Maven 坐标，不复制本地 jar

**改动**：`SystemUI-core/build.gradle.kts` 中 `com.google.android.material:material:1.12.0` → `1.13.0-alpha08`

### Task 2: slice 1.0.0 → 1.1.0-alpha02

**调查结论**：
- AOSP 用 `androidx.slice_slice-view` 1.1.0-alpha02（prebuilts/sdk/current/androidx/m2repository）
- AOSP jar 确认有 `setShowTitleItems(boolean)` 方法
- 项目当前用 1.0.0

**改动**：`gradle/libs.versions.toml` 中 `androidxSlice = "1.0.0"` → `"1.1.0-alpha02"`

### Task 3: Room 2.6.1 → 2.7.0-beta01 + KSP compiler

**调查结论**：
- AOSP 用 Room 2.7.0-beta01（prebuilts/sdk/current/androidx/m2repository）
- `fallbackToDestructiveMigration(dropAllTables = true)` 在 Room 2.7+ 才有
- AOSP bp 用 `plugins: ["androidx.room_room-compiler-plugin"]`（Soong annotation processor）
- Gradle 对应：`ksp("androidx.room:room-compiler:2.7.0-beta01")`

**改动**：
- `SystemUI-core/build.gradle.kts`：加 `id("com.google.devtools.ksp")` 插件
- room-runtime/room-ktx 2.6.1 → 2.7.0-beta01
- 加 `ksp("androidx.room:room-compiler:2.7.0-beta01")`

### Task 4: material3 1.3.1 → 1.4.0-alpha09

**调查结论**：
- AOSP 用 material3 1.4.0-alpha09（prebuilts/sdk/current/androidx/m2repository）
- 1.3.1 的普通 `IconButton` 无 `shape` 参数；1.4.0-alpha09 添加了

**改动**：`SystemUI-core/build.gradle.kts` 中 material3 和 material3-window-size-class 1.3.1 → 1.4.0-alpha09

### Task 5: SettingsLibColor AAR（问题 C）

**调查结论**：
- `SettingsLibColor` 是独立 `android_library`（`SettingsLib/Color/Android.bp`），无 srcs，只有 `res/values/colors.xml`
- package `com.android.settingslib.color`，47 个 color 资源
- 不在 SettingsLib 主 target 的 static_libs 列表中
- 被 SettingsLibIllustrationPreference 依赖（SettingsLib → IllustrationPreference → Color）
- SystemUI 源码仅 1 处引用：`SideFpsOverlayViewModel.kt:194` → `com.android.settingslib.color.R.color.settingslib_color_blue400`

**方案**：按 Soong 语义，SettingsLibColor 是独立 android_library，打独立 AAR（res-only，无 code）。

**改动**：
- `tools/package_aosp_aar.py`：CONFIGS 新增 SettingsLibColor（code=[], res=Color/res, manifest=Color/AndroidManifest.xml）
- `tools/install_aar_to_maven.py`：ARTIFACTS 新增 SettingsLibColor
- `gradle/libs.versions.toml`：新增 systemui-settingslib-color alias
- `SystemUI-core/build.gradle.kts`：加 `implementation(libs.systemui.settingslib.color)`
- `tools/tests/test_package_aosp_aar.py`：CONFIGS 断言 7→8 artifacts

### Task 6: KSP 跑 Dagger（问题 D）

**调查结论**：
- `DaggerReferenceGlobalRootComponent` 是 Dagger 生成类，需 KSP 运行
- 项目 catalog dagger = 2.51.1，但 unfold 注释指出"2.51.1 + KSP2 有 'unexpected jvm signature V' bug"
- unfold 用 2.57.2（implementation 不透传）
- 2.56+ 引入 `Lazy<T : Any>` 边界，会让 core 的无界 `Lazy<T>` 报错
- 折中：用 2.55（2.51.1 与 2.56 之间，可能有 KSP2 修复但无 Lazy 边界）

**改动**：
- `gradle/libs.versions.toml`：dagger 2.51.1 → 2.55
- `SystemUI-core/build.gradle.kts`：加 `ksp(libs.dagger.compiler)`

**KSP2 subcomponent 绑定问题（已解决）**：

配置 KSP + Dagger 2.55 后，KSP 运行但报 **120 个 MissingBinding 错误**（子组件绑定无法从根组件解析）。
Dagger 自己确认绑定存在（"is provided in the following other components: ReferenceSysUIComponent"），
但 KSP2 processor 无法跨 subcomponent 边界正确解析。

**根因**：Dagger 2.55 引入了绑定图重写（`LegacyBindingGraphFactory` → 新实现），修复了
"missing multibindings"和"nonsensical error messages"等问题。但该修复在 2.55 默认 disabled，
2.58+ 默认启用。KSP2 的 subcomponent 绑定解析问题正是这些"subtle bugs"之一。

**解法**：两个配置缺一不可：

1. `ksp { arg("dagger.useBindingGraphFix", "ENABLED") }` — 启用 Dagger 2.55 绑定图重写
   参考：https://dagger.dev/dev-guide/compiler-options#useBindingGraphFix
2. `ksp.incremental=false`（gradle.properties）— 避免 KSP2 FIR 解析非确定性崩溃
   参考：https://github.com/google/ksp/issues/2542

**验证结果**：
- 120 个 MissingBinding 错误 → 0
- `DaggerReferenceGlobalRootComponent.java` 成功生成
- KSP 任务 BUILD SUCCESSFUL

**版本兼容性记录**：
- Dagger 2.55：runtime + processor 均可用（与 AOSP `external/dagger2` 的 DAGGER_TAG="2.55" 一致）
- Dagger 2.56/2.57.2 processor：触发 KSP2 内部崩溃（FIR 解析 bug）
- Dagger 2.56+ runtime：引入 `Lazy<T : Any>` 边界，core 228 处无界 `Lazy<T>` 会报错
- `ksp.incremental=false` 解决了崩溃的非确定性（但不影响绑定错误）

**后续问题**：KSP 通过后，Kotlin 编译遇到 Compose inline 问题（`Couldn't inline method call: Box$default`）。
这是 AGENTS.md §2.4 已记录的已知问题（framework.jar 污染 KotlinCompile Compose inline metadata），
与本次改动无关。

## 错误数演变

```
708 → 657 → 335 → 234 → 170 → 37 → 8（44f6b03c）→ KSP 通过后 Compose inline 问题
```

KSP + Dagger 已通过（0 个 KSP 错误，`DaggerReferenceGlobalRootComponent` 已生成）。
当前阻塞：Compose inline 问题（`Couldn't inline method call: Box$default`），为已知问题（AGENTS.md §2.4）。

## 验证结果

- [x] 6 个 Task 全部改动完成
- [x] `python3 tools/package_aosp_aar.py --all` 生成 8 个 AAR（含 SettingsLibColor）
- [x] `python3 tools/install_aar_to_maven.py` 安装 8 个 AAR
- [x] `python3 -m unittest discover -s tools/tests -p 'test_*.py'` 57 tests OK
- [x] `./gradlew :SystemUI-core:kspDebugKotlin` BUILD SUCCESSFUL（0 个 KSP 错误）
- [x] `DaggerReferenceGlobalRootComponent.java` 成功生成
- [ ] `./gradlew :SystemUI-core:compileDebugKotlin` — 被 Compose inline 问题阻塞（已知问题）
