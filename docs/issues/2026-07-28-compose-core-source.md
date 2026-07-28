# Stage 3 (部分): 补齐 PlatformComposeCore 源码 + compose androidx 依赖 (2026-07-28)

> 承接 lottie（844→809）。本次错误数 **809 → 741 (−68)**。

## TL;DR

Compose Scene/theme 框架内部大量 unresolved：`thenIf`(10)、`modifiers`(12)、`graphics`(11)、
`drawInContainer`、`rememberDrawablePainter`(5)、`windowsizeclass`(5)、`roundToPx` 等。
根因：我方移植 SystemUI 时**漏了 PlatformComposeCore 的 6 个源码目录**。补齐源码 + 2 个
androidx 依赖后 −68。

## 根因

`com.android.compose.animation.scene.*`（SceneTransitionLayout，45 文件）源码已在
`SystemUI-core/src`，但其依赖的 **PlatformComposeCore 工具目录缺失**：

| 目录 | 文件数 | 提供 |
|------|--------|------|
| `modifiers/` | 5 | `thenIf`、ConditionalModifiers、Padding、Size |
| `ui/graphics/`(+painter) | 3 | `drawInContainer`、DrawInOverlay、`rememberDrawablePainter` |
| `windowsizeclass/` | 1 | WindowSizeClass |
| `gesture/` | 2 | 手势工具 |
| `grid/` | 1 | grid 布局 |
| `runtime/` | 1 | runtime 工具 |

这些目录只依赖标准 Compose + `com.android.app.tracing.traceSection`（已在 tracinglib jar）+ 自引用。

## 解决方案（AGENTS §1：复制 AOSP 源码）

```bash
SRC=aosp/.../SystemUI/compose/core/src/com/android/compose
for d in modifiers windowsizeclass gesture grid runtime; do cp -r $SRC/$d SystemUI-core/src/com/android/compose/; done
cp $SRC/ui/graphics/*.kt         SystemUI-core/src/com/android/compose/ui/graphics/
cp $SRC/ui/graphics/painter/*.kt SystemUI-core/src/com/android/compose/ui/graphics/painter/
```

复制后 `WindowSizeClass.kt` / `CommonTile.kt` 引入两个 androidx artifact（AOSP Android.bp 同款）：
```kotlin
implementation("androidx.compose.animation:animation-graphics:1.7.5")        // AnimatedImageVector
implementation("androidx.compose.material3:material3-window-size-class:1.3.1") // WindowSizeClass
```

## 无回归

LC_ALL=C 对比 verify20(809)→verify22(741)：**无新增 unresolved 符号类型**。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| lottie 后 | 809 |
| 复制 6 个 compose core 目录 | 755 |
| + animation-graphics + material3-window-size-class | **741** |
