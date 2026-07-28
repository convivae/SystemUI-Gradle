# Stage 4 (部分): 补齐 unfold jar + androidx.window (2026-07-28)

> 承接 log jar（938→885）。本次错误数 **885 → 844 (−41)**。

## TL;DR

可折叠设备相关引用 unresolved，分两类：
- `com.android.systemui.unfold.updates.FOLD_UPDATE_*` 常量 + `FoldStateProvider` 等 →
  补 AOSP `SystemUIUnfoldLib.jar`（112 类）。
- `androidx.window.layout.FoldingFeature` / `WindowLayoutInfo` → 补 maven `androidx.window:window:1.3.0`。

−41。

## 解决方案

```bash
cp aosp/.../SystemUI/unfold/SystemUIUnfoldLib/android_common/kotlin/SystemUIUnfoldLib.jar libs/SystemUI-unfold.jar
```
`SystemUI-core/build.gradle.kts`：
```kotlin
implementation(files("${rootProject.projectDir}/libs/SystemUI-unfold.jar"))  // FOLD_UPDATE_* 等
implementation("androidx.window:window:1.3.0")                                // FoldingFeature 等
```

## 无回归

LC_ALL=C 对比：**无新增 unresolved 符号类型**。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| log jar 后 | 885 |
| + unfold jar + androidx.window | **844** |
