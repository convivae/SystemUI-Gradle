# AOSP bp 模块 → Gradle 子模块映射方案（v2）

> **注记（2026-08-26，Task 063）**：本文引用的 `scripts/` 目录（含 `propose_aosp_to_gradle_mapping.py` 等 14 个脚本）
> 与 `docs/extras-file-mapping.csv` 已于 2026-08-26 经用户批准删除（scripts 时代一次性脚本，已被
> `tools/check_source_alignment.py` + 规则 S 源码模块取代）。历史内容保留原样。

**扫描**：`scripts/propose_aosp_to_gradle_mapping.py`
**总计**：40 个 java/android library

---

## 关键发现：AOSP 是混合模型

**AOSP SystemUI 是一个 `android_library`** —— 它**不是一个** java_library，**包含多个 java_library 静态依赖**。
我们的 Gradle 等价是 `:app` 是一个 android app，依赖多个 java library 子模块。

`SystemUI-core` 是 AOSP 主 android_library，包含：
- 自己的 `src/`
- 通过 `static_libs` 链接多个 java_library：
  - `SystemUI-proto`, `SystemUI-tags`, `SystemUI-shared-utils`, `SystemUILogLib`,
    `SystemUIPluginLib`, `SystemUICommon`, `kairos`, `SystemUIFlagsLib`, `SystemUI-statsd`
- 多个 android_library（仅编译时）：
  - `PlatformComposeCore`, `PlatformComposeSceneTransitionLayout`, `PlatformComposeSceneTransitionLayoutTestsUtils`,
    `SystemUIShaderLib`, `SystemUISharedLib`, `SystemUICommon`, `SystemUIUnfoldLib`, ...
- `SystemUI-proto` 用 `proto.type: "nano"`

---

## 最终映射方案（按 AOSP bp 1:1）

| # | AOSP bp 模块 | bp 路径 | Gradle 子模块 | 类型 |
|---|-------------|---------|-------------|------|
| 1 | `SystemUI-core` | `frameworks/base/packages/SystemUI/` | `:app` | android app |
| 2 | `SystemUI-proto` | 同上 | `:SystemUI-proto` | java library |
| 3 | `SystemUI-tags` | 同上 | `:SystemUI-tags` | java library |
| 4 | `SystemUI-shared-utils` | `utils/` | `:SystemUI-utils` | java library |
| 5 | `kairos` | `utils/kairos/` | `:SystemUI-utils-kairos` | java library |
| 6 | `SystemUI-statsd` | `shared/` | `:SystemUI-shared` | java library |
| 7 | `SystemUI-flag-types` | `shared/` | `:SystemUI-shared` | java library |
| 8 | `SystemUIFlagsLib` | `shared/` | `:SystemUI-shared` | java library |
| 9 | `SystemUISharedLib` | `shared/` | `:SystemUI-shared` | android library |
| 10 | `SystemUISharedLib-Keyguard` | `shared/keyguard/` | `:SystemUI-shared-keyguard` | android library |
| 11 | `BiometricsSharedLib` | `shared/biometrics/` | `:SystemUI-shared-biometrics` | android library |
| 12 | `SystemUIPluginLib` | `plugin/` | `:SystemUI-plugin` | java library |
| 13 | `PluginCoreLib` | `plugin_core/` | `:SystemUI-plugin-core` | java library |
| 14 | `PluginAnnotationLib` | `plugin_core/` | `:SystemUI-plugin-core` | java library |
| 15 | `PluginAnnotationProcessorLib` | `plugin_core/` | `:SystemUI-plugin-core` (注：processor 是 build-time annotation processor) | java library |
| 16 | `SystemUILogLib` | `log/` | `:SystemUI-log` | java library |
| 17 | `SystemUICommon` | `common/` | `:SystemUI-common` | java library |
| 18 | `SystemUICustomizationLib` | `customization/` | `:SystemUI-customization` | android library |
| 19 | `SystemUICustomizationTestUtils` | `customization/tests/utils/` | `:SystemUI-customization` (testFixtures) | java library |
| 20 | `PlatformComposeCore` | `compose/core/` | `:SystemUI-compose-core` | android library |
| 21 | `PlatformComposeSceneTransitionLayout` | `compose/scene/` | `:SystemUI-compose-scene` | android library |
| 22 | `PlatformComposeSceneTransitionLayoutTestsUtils` | `compose/scene/tests/utils/` | `:SystemUI-compose-scene` (testFixtures) | android library |
| 23 | `PlatformAnimationLib` | `animation/` | `:SystemUI-animation` | android library |
| 24 | `PlatformAnimationLib-core` | `animation/lib/` | `:SystemUI-animation` | java library |
| 25 | `PlatformAnimationLib-server` | `animation/lib/` | `:SystemUI-animation` | java library |
| 26 | `SystemUIShaderLib` | `animation/` | `:SystemUI-animation` | android library |
| 27 | `SystemUIUnfoldLib` | `unfold/` | `:SystemUI-unfold` | android library |
| 28 | `kairos` (test) | `utils/kairos/tests/...` | (testing) | - |
| 29 | `RoboTestLibraries` | top | (testing) | - |
| 30 | `SystemUI-tests-concurrency` | top | (testing) | - |
| 31 | `kosmos` | top | (testing) | - |

---

## Pods（`pods/com/android/systemui/...`）

AOSP SystemUI 还有若干 pod 模块（java_library），按 bp name 都是 `api` 或 `impl`：

| bp 路径 | 内容 | Gradle 子模块 |
|---------|------|---------------|
| `pods/com/android/systemui/dagger/` | `@Module` / `@Provides` 接口集合 | `:SystemUI-pods-dagger` |
| `pods/com/android/systemui/retail/` | impl | `:SystemUI-pods-retail` |
| `pods/com/android/systemui/retail/data/` | api + impl | `:SystemUI-pods-retail-data` |
| `pods/com/android/systemui/retail/domain/` | api + impl | `:SystemUI-pods-retail-domain` |
| `pods/com/android/systemui/util/settings/` | api | `:SystemUI-pods-util-settings` |

**重要**：bp name 都是 `api` / `impl`，多个模块同名——Gradle 子模块不能同名，必须按 bp 路径加前缀。

---

## 关于 `:SystemUI-core` 当前状态

**当前 SystemUI-core/src/ 实际包含**：
- AOSP `SystemUI-core` 自己的 src/（主模块）
- 错装的 340 个多出文件（来自 27 个独立 bp 模块）

**拆分动作**：把这 340 个文件**物理移走**到对应新模块的 src/，按 AOSP 路径 1:1。

**每个新模块的 src/ 路径**：按 AOSP srcs glob 反推目录：
- 例 `animation/lib/Android.bp` 的 `PlatformAnimationLib-core` srcs: `src/com/android/systemui/animation/*.java` → 我们 `SystemUI-animation/src/main/java/com/android/systemui/animation/`

---

## 行动分步

1. **不要拆 SystemUI-core 自身的 src/**（主模块内容，已对齐 4203=AOSP 文件数）
2. **创建 13-15 个新 Gradle 子模块**，每个对应一个独立 bp 模块
3. **物理搬运 340 个文件**到对应模块的 src/main/java 下
4. **每个新模块加 build.gradle.kts**（模板：compileOnly framework + 内部依赖）
5. **SystemUI-core 改用 implementation(project(":xxx")) 引用新模块**

---

## 估算工作量

- 13 个新子模块 × 平均 20 个文件 = 260 个文件搬运
- 13 个新 build.gradle.kts
- settings.gradle.kts 加 13 行 include
- 验证编译（每个子模块单独 compile + :app 全链编译）

预计 2-3 轮迭代修复编译错误。

---

## 不拆的特殊情况

- **`SystemUI-tests-concurrency`**、**`RoboTestLibraries`**、**`kosmos`** —— 这些是 AOSP testing utilities，
  在我们 Gradle 里**先不拆**（`:app` 不需要测试代码），独立放到 `:app:test-fixtures` 或类似
- **`PluginAnnotationProcessorLib`** —— annotation processor，应放到 `kapt` 配置或 `javacPlugin`

---

## 下一步动作

1. 先详细映射所有 340 个文件到目标子模块（脚本生成 CSV）
2. 用户 review 映射表
3. 按 review 结果执行物理搬运 + 新模块创建

按规则 S，本方案严格按 AOSP bp 1:1，**不会自己命名模块**。
