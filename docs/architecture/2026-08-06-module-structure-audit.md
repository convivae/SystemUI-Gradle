# SystemUI 模块结构对齐 AOSP BP 全面调研

**日期**：2026-08-06
**背景**：用户质疑当前 22 个 Gradle 模块过多，怀疑有"子模块被平铺成主模块"。本调研逐个对照 AOSP `frameworks/base/packages/SystemUI/` 的 soong 模块定义，确定真实拓扑与当前偏差。

## 一、AOSP 真实模块拓扑

### 1.1 SystemUI-core 的直接 static_libs（Android.bp:446-520）

SystemUI-core（`android_library`，bp:423）直接依赖的 **SystemUI 自有模块**（按 bp 顺序）：

| soong 模块 | 源码目录 | 类型 |
|---|---|---|
| SystemUI-res | (顶层, resource only) | android_library 资源 |
| PlatformAnimationLib | animation/ | android_library |
| SystemUICommon | common/ | java_library |
| SystemUICustomizationLib | customization/ | android_library |
| SystemUILogLib | log/ | java_library |
| SystemUIPluginLib | plugin/ | java_library |
| SystemUISharedLib | shared/ | android_library |
| SystemUI-shared-utils | utils/ | java_library |
| SystemUI-statsd | shared/ (genrule) | java_library |
| SystemUI-tags | (顶层) | java_library |
| SystemUI-proto | (顶层) | java_library |
| PlatformComposeCore | compose/core/ | android_library |
| PlatformComposeSceneTransitionLayout | compose/scene/ | android_library |
| pods/dagger:api | pods/.../dagger/ | java_library |
| pods/util/settings:api | pods/.../util/settings/ | java_library |
| pods/retail:impl | pods/.../retail/ | java_library |

外加 frameworks/libs（非 SystemUI）：compilelib、com_android_systemui_flags_lib、com_android_systemui_shared_flags_lib、iconloader_base、motion_tool_lib、contextualeducationlib、monet、libmonet、animationlib。

### 1.2 传递依赖（子模块）

```
SystemUI-core
├── PlatformAnimationLib ──┬── SystemUIShaderLib (同 animation/src/, exclude 分隔)
│                          └── animationlib (frameworks/libs, 非 SystemUI)
├── SystemUICommon ──────── SystemUI-shared-utils
├── SystemUISharedLib ──────┬── BiometricsSharedLib (shared/biometrics/)
│                           ├── SystemUISharedLib-Keyguard (shared/keyguard/)
│                           ├── SystemUIUnfoldLib (unfold/)
│                           ├── PluginCoreLib (plugin_core/) → PluginAnnotationLib
│                           ├── WindowManager-Shell-shared, tracinglib, view_capture, msdl (frameworks/libs)
│                           └── com_android_systemui_shared_flags_lib (frameworks/libs)
├── pods/retail:impl ──────┬── pods/retail/data:impl → pods/retail/data:api
│                          └── pods/retail/domain:impl → pods/retail/domain:api
└── (各 pods 子模块又依赖 pods/dagger:api, pods/util/settings:api)
```

### 1.3 AOSP 中无生产引用的孤立模块

- **kairos**（utils/kairos/）：仅 `kairos-test`（java_test）引用，SystemUI-core static_libs **不含** kairos。
- **SystemUIFlagsLib**（shared/）：全 SystemUI 树无引用（`SystemUI-flag-types` 只被 FlagsLib 引用，形成死链）。

## 二、当前 Gradle 模块逐个对照

当前 `settings.gradle.kts` 含 22 个模块（含 app）。对照 AOSP：

### 2.1 与 AOSP 对齐的模块（保留）

| Gradle 模块 | AOSP soong 模块 | core 直接依赖? |
|---|---|---|
| :app | SystemUI app | - |
| :SystemUI-core | SystemUI-core | - |
| :SystemUI-shared | SystemUISharedLib | ✅ |
| :SystemUI-animation | PlatformAnimationLib | ✅ |
| :SystemUI-customization | SystemUICustomizationLib | ✅ |
| :SystemUI-plugin | SystemUIPluginLib | ✅ |
| :SystemUI-common | SystemUICommon | ✅ |
| :SystemUI-log | SystemUILogLib | ✅ |
| :SystemUI-compose-core | PlatformComposeCore | ✅ |
| :SystemUI-compose-scene | PlatformComposeSceneTransitionLayout | ✅ |
| :SystemUI-proto | SystemUI-proto | ✅ |

### 2.2 合理的"传递依赖子模块"（保留，但需修正依赖位置）

这些是 AOSP 独立 soong 模块，且部分被多个父模块引用，独立 Gradle 模块合理：

| Gradle 模块 | AOSP 模块 | AOSP 引用者 | 问题 |
|---|---|---|---|
| :SystemUI-plugin-core | PluginCoreLib | shared+customization+plugin | 当前是否被正确引用需查 |
| :SystemUI-unfold | SystemUIUnfoldLib | shared+customization | 同上 |
| :SystemUI-shared-biometrics | BiometricsSharedLib | **仅 shared** | ⚠️ 当前被 core 直接依赖（应经 shared 传递） |
| :SystemUI-shared-keyguard | SystemUISharedLib-Keyguard | **仅 shared** | ⚠️ 同上 |

### 2.3 pods 系列（namespace 子模块，5 个有效 + 2 个空壳）

AOSP pods 是一个 `soong_namespace`，下含 5 个子目录各自定义 api/impl（局部模块名）。项目处理：

| Gradle 模块 | AOSP 对应 | core 直接依赖? | 问题 |
|---|---|---|---|
| :SystemUI-pods-dagger | pods/dagger:api | ✅ | 保留 |
| :SystemUI-pods-retail | pods/retail:impl | ✅ | 保留 |
| :SystemUI-pods-data | pods/retail/data:{api+impl} | ❌ 经 retail | api/impl 合并，合理简化 |
| :SystemUI-pods-domain | pods/retail/domain:{api+impl} | ❌ 经 retail | 同上 |
| :SystemUI-pods-settings | pods/util/settings:api | ✅ | 保留 |
| SystemUI-pods-retail-data-impl/ (目录) | — | — | ❌ **脚手架空壳**，settings 未 include，引用不存在的 `:SystemUI-pods-retail-data-api` |
| SystemUI-pods-retail-domain-impl/ (目录) | — | — | ❌ **脚手架空壳**，同上 |

### 2.4 违规或多余模块

| Gradle 模块 | AOSP 对应 | 判定 |
|---|---|---|
| :SystemUI-animationlib | animationlib (**frameworks/libs/systemui**) | ❌ 非 SystemUI 自有，源码复制违反规则 F；应改 AAR |
| :SystemUI-utils-kairos | kairos (utils/kairos/) | ❌ AOSP 无生产引用；项目 core 违规依赖它（AOSP core 不依赖 kairos） |

## 三、问题诊断汇总

### 问题 A：违规源码模块（违反规则 S/F）

1. **`:SystemUI-animationlib`** — 复制 `frameworks/libs/systemui/animationlib`（包 `com.android.app.animation`），非 SystemUI 自有。应改 AAR。
2. **`:SystemUI-utils-kairos`** — AOSP kairos 仅供 `kairos-test` 用，SystemUI-core 不依赖。项目 core `implementation(project(":SystemUI-utils-kairos"))`（build.gradle.kts:111）是违规依赖。应删模块 + 删 core 依赖。
3. **`:SystemUI-core` 的 `Compile.java`** — 来自 `frameworks/libs/systemui/compilelib`，非 SystemUI 自有。应改 jar。

### 问题 B：脚手架空壳残留

- `SystemUI-pods-retail-data-impl/`、`SystemUI-pods-retail-domain-impl/`：`scaffold_aosp_modules.py` 生成物，settings 未 include，build.gradle.kts 引用不存在的 api 模块。应删目录。

### 问题 C：源码放错模块

1. **`FlowConflated.kt` / `LatestConflated.kt`** 在 `:SystemUI-common` → AOSP 在 `utils/src/`，属 `SystemUI-shared-utils`。
2. **`:SystemUI-core/src/com/android/systemui/utils/*`**（GlobalWindowManager 等）→ AOSP 在 `utils/src/`，属 `SystemUI-shared-utils`。
3. 对齐脚本报的 "pods retail 4 kt 缺失" 实为**误报**：文件已在 `:SystemUI-pods-data`/`:SystemUI-pods-domain`，脚本按空壳模块 `retail-data-impl` 找导致找不到。

### 问题 D：缺失模块（AOSP 有、项目未建）

| 应建模块 | AOSP 对应 | 现状 |
|---|---|---|
| :SystemUI-shared-utils | SystemUI-shared-utils (utils/) | 源码散落在 core/common，未成模块 |
| :SystemUI-shader | SystemUIShaderLib (animation/ surfaceeffects, 22 文件) | 完全缺失（脚本 SHADER AOSP 22/项目 0） |
| :SystemUI-res | SystemUI-res (资源) | 资源挂 core（规则 B 要求独立） |
| :SystemUI-tags | SystemUI-tags (顶层 java_library) | 当前用 jar（可接受，非源码模块） |

### 问题 E：依赖位置错误

1. **`:SystemUI-core` 直接依赖 `:SystemUI-shared-biometrics` / `:SystemUI-shared-keyguard`**（build.gradle.kts:117,119）→ AOSP 这两个是 **SystemUISharedLib 的传递依赖**，应由 `:SystemUI-shared` 依赖，core 只依赖 `:SystemUI-shared`。
2. **`:SystemUI-shared` 未依赖 biometrics/keyguard**（shared/build.gradle.kts 只有 plugin-core + unfold）→ 与 AOSP 相反。

## 四、核心结论：模块不是"太多"，而是"划分错位"

用户的直觉准确，但根因不是模块数量：

- AOSP `packages/SystemUI/` 下生产 soong 模块约 30 个（含 pods 5 个 namespace 子模块）
- 项目当前 22 个，数量并不离谱
- **真正问题是划分与 AOSP 不一致**：
  - 该建的没建（shared-utils / shader / res）
  - 不该建的建了（animationlib 违规、kairos 死模块、2 个空壳）
  - 依赖关系错（biometrics/keyguard 挂 core 不挂 shared、core 违规依赖 kairos）
  - 源码放错模块（Conflated 在 common、utils 散落 core、Compile.java 在 core）

## 五、修正方向（待用户确认优先级与合并策略）

### 第一优先：删违规与空壳（结构净化）
- 删 `:SystemUI-animationlib` 模块，改 AAR 引入 frameworks/libs animationlib
- 删 `:SystemUI-utils-kairos` 模块 + 删 core 对它的依赖
- 删 `Compile.java` 源码，compilelib 改 jar
- 删 2 个 pods 空壳目录

### 第二优先：修正依赖位置（对齐 bp 拓扑）
- `:SystemUI-shared` 增加依赖 `:SystemUI-shared-biometrics` + `:SystemUI-shared-keyguard`
- `:SystemUI-core` 移除对 biometrics/keyguard 的直接依赖（改由 shared 传递）

### 第三优先：建缺失模块 + 迁源码
- 新建 `:SystemUI-shared-utils`，迁入 utils/src 源码（含从 common 迁回的 Conflated、从 core 迁回的 utils/）
- 新建 `:SystemUI-shader`（或并入 `:SystemUI-animation`，因 AOSP 同 animation/ 目录用 exclude 分隔）
- 新建 `:SystemUI-res`（规则 B 要求）

### 合并策略选项（需用户决策）

pods 5 个模块：AOSP 是 namespace 下独立 soong 模块。可：
- **方案 P1**：保持 5 个（对齐 bp 拓扑，当前已合理合并 api/impl）
- **方案 P2**：合并为 1 个 `:SystemUI-pods`（用 sourceSet 含 5 子目录，简化但偏离 bp）

biometrics/keyguard/unfold/plugin-core：AOSP 独立 soong 模块，建议**保持独立**（源码独立目录 + 部分多引用）。

## 六、验证记录

本调研仅读取 AOSP `Android.bp` 与项目 build.gradle.kts/settings，未修改任何源码或运行编译。所有 soong 模块名、static_libs、引用关系均来自 AOSP `frameworks/base/packages/SystemUI/` 的 `Android.bp` 文件证据。

## 七、参考证据

- AOSP SystemUI-core static_libs：`Android.bp:446-520`
- AOSP SystemUISharedLib static_libs：`shared/Android.bp:54-71`
- AOSP PlatformAnimationLib exclude_srcs + ShaderLib：`animation/Android.bp:30-50`
- AOSP kairos 仅被 kairos-test 引用：`utils/kairos/Android.bp:42`
- 项目 core 违规依赖 kairos：`SystemUI-core/build.gradle.kts:111`
- 项目 core 直接依赖 biometrics/keyguard：`SystemUI-core/build.gradle.kts:117,119`
- 项目 shared 未依赖 biometrics/keyguard：`SystemUI-shared/build.gradle.kts`（仅 plugin-core/unfold）
- pods 空壳：`SystemUI-pods-retail-{data,domain}-impl/build.gradle.kts`（引用不存在的 api 模块）
