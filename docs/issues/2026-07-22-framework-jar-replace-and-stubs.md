# 2026-07-22: 替换 framework.jar + Stub 内部 API 解决问题

## 背景

SystemUI-core 编译错误数从 commit `47fe845` 的 5,494 个降到
`aad1084` 的 5,296 个，但仍有大量 unresolved reference 集中在：

```
60 getString           ← Context.getString 正常，但被 R.string 不存在污染
37 it                  ← 类型推断级联失败
29 data                ← 类型推断级联失败
28 color               ← R.color.X (internal) 不存在
27 Flags               ← AOSP Flags 未声明
26 compose             ← Scene 框架 API 不全
26 ColorScheme         ← Material ColorScheme 不全
25 composable
23 flags
15 onBackInvokedDispatcher  ← ViewRootImpl.getOnBackInvokedDispatcher() 缺失
14 communalSceneKtfRefactor ← Flag
14 CommunalHubState        ← Scene 状态
13 materialColorOnSurface  ← internal.R.attr 缺失
```

## 问题一：materialColorOnSurface 等内部 attr 缺失

### 错误信息

```
e: file:///.../BiometricCustomizedViewBinder.kt:298:73 Unresolved reference 'materialColorOnSurface'.
```

### 根本原因

`materialColorOnSurface` 等 Material You attr 定义在
`frameworks/base/core/res/res/values/attrs.xml`，但只发布到
`com.android.internal.R$attr`。我们使用的 `libs/framework.jar` 是简化版本：

| 项目 | internal.R$attr 条目数 | 关键 attr |
|------|-------------------------|-----------|
| 旧 `libs/framework.jar` | 1547 | ❌ 缺 materialColorOnSurface |
| AOSP `framework.jar` (turbine-combined) | 1732 | ✅ 含 materialColorOnSurface |
| AOSP `framework.jar` (dex/framework.jar) | 1732 | ✅ 含 materialColorOnSurface |

旧 jar 来自更早 AOSP 版本，被人工裁剪过。

### 解决方案

替换 `libs/framework.jar` 为 AOSP 完整编译产物：

```bash
cp aosp/out/soong/.intermediates/frameworks/base/framework/android_common/turbine-combined/framework.jar \
   libs/framework.jar
```

### 验证

- `unzip -p libs/framework.jar com/android/internal/R\$attr.class | javap -p` 输出 1732 行
- `grep materialColorOnSurface` 命中

## 问题二：onBackInvokedDispatcher 扩展属性未生效

### 错误信息

```
e: file:///.../BackActionInteractor.kt:80:77 Unresolved reference 'onBackInvokedDispatcher'.
```

代码：
```kotlin
private val onBackInvokedDispatcher: WindowOnBackInvokedDispatcher?
notificationShadeWindowController.windowRootView?.viewRootImpl?.onBackInvokedDispatcher
```

### 根本原因

1. `ViewRootImpl.getOnBackInvokedDispatcher()` 是 `@hide` API
2. 我们创建的扩展属性 `WindowExt.kt`：
   ```kotlin
   val ViewRootImpl.onBackInvokedDispatcher: WindowOnBackInvokedDispatcher?
       get() = try {
           this::class.java.getMethod("getOnBackInvokedDispatcher").invoke(this) ...
   ```
3. 反射调用方式 — 但 Kotlin 编译器可能在编译期就检查类型
4. 且 `windowRootView?.viewRootImpl` 这种链式访问，编译器可能无法解析扩展属性

### 临时方案

复制 AOSP `WindowOnBackInvokedDispatcher.java` 到 `SystemUI-core/src/android/window/`
让代码先编译通过。后续需要用更结构化的方式扩展。

### 待办

- 替换反射为编译期扩展（用 `@hide` 注解 + compileOnly jar）
- 真正接入需要 framework.jar 中的 ViewRootImpl.getOnBackInvokedDispatcher()

## 问题三：缺少的 @hide 内部 API stub

### 新增的 stub 文件

| Stub 文件 | 来自 AOSP 路径 | 用途 |
|-----------|-----------------|------|
| `com/android/internal/jank/Cuj.java` | `frameworks/base/core/java/com/android/internal/jank/Cuj.java` | JankStats Cuj 枚举 |
| `android/hardware/biometrics/BiometricRequestConstants.java` | 同名 AOSP 文件 | Biometric 错误原因 |
| `android/hardware/biometrics/AuthenticateOptions.java` | 同名 | Biometric 选项 |
| `android/hardware/face/FaceAuthenticateOptions.java` | 同名 | Face 选项 |
| `android/hardware/input/InputGestureData.java` | 同名 | 键盘快捷键 |
| `android/window/WindowOnBackInvokedDispatcher.java` | `frameworks/base/core/java/android/window/WindowOnBackInvokedDispatcher.java` | Back 调度 |
| `com/android/internal/statusbar/LetterboxDetails.java` | `frameworks/base/core/java/com/android/internal/statusbar/LetterboxDetails.java` | Letterbox 元数据 |
| `android/media/projection/StopReason.kt` | AIDL 转 Kotlin | MediaProjection 停止原因 |
| `com/android/internal/annotations/Keep.java` | `frameworks/libs/modules-utils/java/com/android/internal/annotations/Keep.java` | @Keep 注解 |
| `android/appwidget/AppWidgetHost.java` | `frameworks/base/core/java/android/appwidget/AppWidgetHost.java` | AppWidget 宿主（含 Listener 接口） |

### AIDL 类的处理

`LetterboxDetails` 等 AIDL 文件 (`.aidl`) 被自动生成的 `*.java` 不能直接复制：
- AIDL 编译生成的 java 文件很长且包含很多生成器特殊代码
- 直接拷贝 `*.java`（如 `LetterboxDetails.java`）通常可以工作，因为它是
  AIDL 编译产物之一
- 但 `StopReason.aidl` → `StopReason.java` 路径不同，是 `aidl` 后端 → AIDL 编译器 → java
- 我们用 Kotlin stub 替代以避免维护负担

## 错误数演变

| Commit | 描述 | 错误数 |
|--------|------|--------|
| `47fe845` | 合并 framework.jar 到 SysUISdk/android.jar | 5,494 |
| `aad1084` | 添加 Stub 类 | 5,296 |
| `702679e` | 替换 framework.jar + Keep stub | **4,675** |

## 剩余错误分类（top 25）

```
60 getString           ← 多个文件用 `context.getString(R.string.X)` 但 X 不存在
37 it                  ← 类型推断级联
29 data                ← 同上
28 color               ← R.color.X (internal) 仍缺
26 compose             ← Scene 框架
26 ColorScheme
16 T                   ← 泛型推断级联
15 quickaffordance     ← Scene 数据模型
15 onBackInvokedDispatcher  ← 扩展属性未生效
15 domain              ← Dagger domain module
15 Preferences
14 communalSceneKtfRefactor ← Flag 未声明
14 CommunalHubState
13 screenshareNotificationHiding ← Flag
13 of                  ← 类型推断
13 materialColorOnSurface ← 仍 13 个 (framework.jar 替换后仍缺)
13 Slider
12 modifiers
11 preferences
11 monet               ← Monet color engine API
11 graphics
11 fasterUnlockTransition  ← Flag
11 Style
11 MediaTransferSenderState
```

## 待办

1. **Flags 声明**：手写 `Flags.kt` stub 声明 `communalSceneKtfRefactor`、
   `screenshareNotificationHiding`、`fasterUnlockTransition` 等
2. **Material ColorScheme**：检查 `androidx.compose.material3.ColorScheme` 引用
3. **Monet**：复制 AOSP Monet 类（`frameworks/base/graphics/java/android/graphics/Monet`）
4. **onBackInvokedDispatcher 扩展**：改用编译期方案替代反射
5. **Scene 框架**：补全 `SceneTransitionLayout` 等 compose scene 内部 API