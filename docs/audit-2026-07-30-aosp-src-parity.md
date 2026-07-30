# AOSP src 1:1 对齐审计报告

**生成时间**：2026-07-30 01:27 UTC+8
**脚本**：`scripts/check_aosp_src_parity.py` + `scripts/check_aosp_extras_breakdown.py` + `scripts/check_aosp_extras_sysui.py`
**扫描范围**：`SystemUI-Gradle/SystemUI-core/src{,/-debug/-release}` vs AOSP `frameworks/base/packages/SystemUI/`
**AOSP commit**：当前 worktree HEAD

---

## 1. 总体对齐情况

| 维度 | AOSP | 我们 | 差异 |
|------|------|------|------|
| `src/` 源文件 (.kt/.java/.aidl/.proto) | 4203 | **4543** | **+340** |
| `src-debug/` | 4 | 4 | 0 |
| `src-release/` | 4 | 4 | 0 |
| `res/` 文件数 | 1897 | 1897 | 0 |
| `res-keyguard/` | 212 | 212 | 0 |
| `res-product/` | 86 | 86 | 0 |
| AOSP 有我们没有的文件 | — | — | **0** ✅ |
| 跨 source-set 重叠 | — | — | 4（AOSP 既有结构，非 bug） |

---

## 2. 资源对齐 ✅

`res/` / `res-keyguard/` / `res-product/` **三个目录 1:1 完全对齐**（文件数一致）。
这意味着所有 `R.string.*` / `R.drawable.*` / `R.layout.*` 未解析错误应该都是 R 类生成问题，
**不是资源缺失**。

---

## 3. src/ 多出的 340 个文件分析

### 3.1 按顶层包分类

| 包 | 数量 | 评估 |
|----|------|------|
| `com/android/systemui/...` | **235** | ❗ AOSP 独立模块代码，错放进 SystemUI-core |
| `com/android/compose/...` | 77 | ⚠️ AOSP 独立模块（compose/scene, compose/core, compose/features） |
| `com/android/settingslib/...` | 15 | ⚠️ AOSP 独立模块 SettingsLib |
| `com/android/traceur/...` | 3 | ? |
| `platform/test/motion/...` | 3 | ⚠️ AOSP 独立模块 motion test |
| `com/android/keyguard/...` | 2 | ⚠️ AOSP frameworks/base/keyguard |
| `com/android/server/...` | 2 | ❗ **frameworks/base/services，误装** |

### 3.2 src/com/android/systemui/ 235 文件细分

| 子目录 | 数量 | AOSP 真实位置 |
|--------|------|---------------|
| `kairos/` | 42 | `frameworks/base/packages/SystemUI/utils/kairos/src/` |
| `scene/` | 43 | `compose/scene/tests/src/` (测试代码) |
| `keyguard/ui/composable/` | 25 | `compose/features/src/` |
| `communal/ui/compose/` | 18 | `compose/features/src/` |
| `biometrics/...` | 11 | 多分散 (部分应在 compose/features) |
| `util/...` | 11 | 待细查 |
| `notifications/ui/composable/` | 8 | compose/features/src |
| `bouncer/ui/composable/` | 7 | compose/features/src |
| `common/ui/compose/` | 7 | compose/features/src |
| `qs/.../compose/` | 7 | compose/features/src |
| `shade/...` | 6 | 待查 |
| `retail/...` | 5 | 待查 |
| `volume/.../composable/` | 28 | compose/features/src |
| ... | ... | ... |

---

## 4. 根因结论

**这 340 个文件都不是 SystemUI 的"自有代码被错放"**——它们的源代码在 AOSP 里**确实存在**，
只是位于 AOSP 的独立 bp 模块（java_library）中：

```
frameworks/base/packages/SystemUI/
├── src/                                ← 主 java_library "SystemUI" (4203 files)
├── utils/kairos/src/                   ← java_library "SystemUI-kairos"
├── compose/scene/src/                  ← java_library "PlatformComposeSceneTransitionLayout"
├── compose/scene/tests/                ← java_library "PlatformComposeSceneTransitionLayoutTest"
├── compose/core/src/                   ← java_library "PlatformComposeCore"
├── compose/features/src/               ← java_library "PlatformComposeFeatures"
├── plugin/                             ← java_library "PluginCore"
├── plugin_core/                        ← java_library "Plugin"
├── customization/                      ← java_library "SystemUICustomization"
├── unfold/                             ← java_library "SystemUIUnfoldLib"
├── shared/                             ← java_library "SystemUIShared"
└── accessibility/...                   ← 各独立模块
```

我们之前把 AOSP 整棵目录树的 `*.kt/*.java` 直接扫进 SystemUI-core/src/，**没有按 bp 模块拆模块**。

---

## 5. 决策选项

### 选项 A：按 AOSP bp 模块拆 Gradle 子模块（推荐，符合规则 S）

**做法**：
- 把 340 个多出文件按 AOSP bp 模块拆分到独立 Gradle 子模块：
  - `:SystemUI-kairos`（42 个 kairos 文件）
  - `:SystemUI-compose-scene`（46 个 compose/scene 主代码）
  - `:SystemUI-compose-core`（com/android/compose/ 顶层）
  - `:SystemUI-compose-features`（115 个 keyguard/communal/biometrics/.../composable）
  - `:SystemUI-compose-scene-tests`（43 个 scene 测试代码 + 其它测试）
  - `:SystemUI-settingslib`（15 个 settingslib）
  - `:SystemUI-plugin-core`（已存在）
  - `:SystemUI-unfold`（已存在）
  - `:SystemUI-shared`（已存在）
  - `:SystemUI-customization`（已存在）
  - ...
- 每个子模块 `:api` 用 `compileOnly` 暴露给 `:SystemUI-core`
- 配套新建 `settings.gradle.kts` 子模块条目、`build.gradle.kts` 各模块独立

**优点**：100% 严格 1:1 对齐 AOSP bp 结构，符合规则 S 精神
**代价**：迁移工作量较大，需要把所有 build 脚本里引用的包名重组

### 选项 B：作为 AOSP 复合兼容模式，合并到 SystemUI-core（临时方案）

**做法**：
- 保留现状，所有源码全放 `:SystemUI-core/src/`
- 在 `build.gradle.kts` 里加注释说明："本模块聚合 AOSP bp 模块 X/Y/Z 的源码"
- 按 AOSP bp 模块名注释分段（如 `// === from bp: SystemUI-kairos ===`）

**优点**：零迁移
**缺点**：违反规则 S 的"bp 1:1" 严格要求；编译粒度丧失（任何文件改动重编整个 core）

### 选项 C：精简（部分按 bp 模块拆分 + 部分合并）

混合方案：拆分 3-5 个最有价值的（kairos、compose-features、compose-scene），
其他保留 core。

---

## 6. 完整映射结果（基于 `extras-file-mapping.csv`）

通过 `scripts/map_extras_to_modules.py` 扫描 AOSP 整树索引，按文件实际路径匹配到目标 AOSP 模块：

**316 个文件**已精确映射到目标 AOSP bp 模块（见 `docs/extras-file-mapping.csv`）。
**24 个未匹配** 主要是非 SystemUI 模块代码（SettingsLib / Traceur / WindowManager-Shell / motion 测试）。

### 目标 Gradle 子模块映射（按 AOSP bp 1:1 命名）

| AOSP bp 模块 | bp 路径 | 文件数 | Gradle 子模块名 |
|-------------|---------|--------|-----------------|
| `SystemUI-core` | `.` | 162 | `:SystemUI-core` |
| `PlatformComposeSceneTransitionLayout` | `compose/scene/` | 50 | `:SystemUI-compose-scene` |
| `kairos` | `utils/kairos/` | 42 | `:SystemUI-utils-kairos` |
| `PlatformComposeCore` | `compose/core/` | 27 | `:SystemUI-compose-core` |
| `BiometricsSharedLib` | `shared/biometrics/` | 11 | `:SystemUI-shared-biometrics` |
| `api` (util/settings) | `pods/com/android/systemui/util/settings/` | 10 | `:SystemUI-pods-util-settings` |
| `SystemUI-proto` | `.` | 4 | `:SystemUI-proto` |
| `api` (dagger) | `pods/com/android/systemui/dagger/` | 3 | `:SystemUI-pods-dagger` |
| `SystemUISharedLib-Keyguard` | `shared/keyguard/` | 2 | `:SystemUI-shared-keyguard` |
| `impl` (retail) | `pods/com/android/systemui/retail/` | 1 | `:SystemUI-pods-retail-impl` |
| `api` (retail/data) | `pods/.../retail/data/` | 1 | `:SystemUI-pods-retail-data-api` |
| `impl` (retail/data) | `pods/.../retail/data/` | 1 | `:SystemUI-pods-retail-data-impl` |
| `api` (retail/domain) | `pods/.../retail/domain/` | 1 | `:SystemUI-pods-retail-domain-api` |
| `impl` (retail/domain) | `pods/.../retail/domain/` | 1 | `:SystemUI-pods-retail-domain-impl` |

### 未匹配 24 个（需建独立 Gradle 子模块）

| 文件 | AOSP 真实位置 | 应建 Gradle 子模块 |
|------|--------------|-------------------|
| `com/android/settingslib/...` (15) | `frameworks/base/packages/SettingsLib/` | `:SettingsLib` (prebuilt jar) |
| `com/android/traceur/...` (3) | `packages/apps/Traceur/` | `:Traceur` (prebuilt jar) |
| `com/android/wm/shell/dagger/HasWMComponent.kt` | `frameworks/base/libs/WindowManager/Shell/` | `WindowManager-Shell.jar` 已存在 |
| `platform/test/motion/...` (3) | `platform_testing/libraries/motion/compose/values/` | `:PlatformMotionTestValues` |
| `com/android/systemui/util/Compile.java` | AOSP `src/` 不存在 | 待查 |
| `com/android/systemui/contextualeducation/GestureType.kt` | AOSP `src/` 不存在 | 待查 |
