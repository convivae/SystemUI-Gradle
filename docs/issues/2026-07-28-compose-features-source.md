# Stage 3 大步: 补齐 compose/features + biometric + animation 源码 (2026-07-28)

> 承接 compose/core 顶层文件（741→724）。本次 **724 → 509 (−215)**，一次大跃进。
> 用户 2026-07-28 明确：为补齐真实 AOSP 源码而复制代码，即使暂时抬高错误数也允许，
> 因项目整体在前进。本步先短暂 +47 再净降 215。

## TL;DR

一次性补齐三块缺失的 AOSP 源码 + 一个 import 规范化：
1. **compose/features/src**（152 文件）：`scene.ui.composable.Scene`/`Overlay`/`QuickSettingsShade`/
   `SceneContainerTransitions` 及大量 bouncer/qs/volume/keyguard compose 界面。
2. **biometrics/shared/model**（9 文件）：`asBiometricModality`/`toSensorStrength`/`toSensorType` 等。
3. **compose/core/animation**（4 顶层文件）：`Bounceable`/`Easings`/`Emphasized`/`Expandable`。
4. **res.R → R 规范化**（39 文件）：features 文件用 `com.android.systemui.res.R`，
   我方 namespace 是 `com.android.systemui`（R 在 `com.android.systemui.R`），改 import 后
   `R` unresolved 的级联全解（705→509，−196）。

## 关键洞察：res.R 命名空间

- AOSP SystemUI 的 R 在 `com.android.systemui.res.R`（把 R 挪进 res 子包）。
- 我方 Gradle `namespace = "com.android.systemui"` → R 生成在 `com.android.systemui.R`。
- 已有 1044 文件用 `import com.android.systemui.R`（能编译），新拷入的 152 features 文件里
  39 个用 `.res.R` → `Unresolved reference 'R'` + 全部 `R.*` 级联（148 处）。
- 修复：`sed` 把这 39 文件的 `import com.android.systemui.res.R` 改为 `com.android.systemui.R`。

## 解决方案（AGENTS §1：复制 AOSP 源码）

```bash
# 1. features/src（排除已存在的 SysuiTestTag.kt）
# 2. biometrics/shared/model 9 文件
# 3. compose/core/animation：Bounceable/Easings/Expandable/ExpandableController
# 4. sed 规范化 res.R → R
```

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| compose/core 顶层后 | 724 |
| + features/src（152） | 771（暂升，符合用户前进原则） |
| + biometric（9）+ animation（4） | 705 |
| + res.R→R 规范化（39） | **509** |

## 残留新缺口（2 个符号类型，honest gaps）

- `MotionTestValues`/`motionTestValues`/`MotionTestValueKey`（BouncerContent.kt 等）：
  `platform.test.motion` 测试库，主源码里的 motion 测试挂钩，需 motion-test jar 或剥离。
- `setShowTitleItems`（SliceAndroidView.kt）：framework Slice 方法，属 framework.jar 版本差异。

## 无严重回归

vs 724 baseline：净降 215，仅新增 2 个 honest 符号类型（上面两条），其余全为已有缺口的暴露。