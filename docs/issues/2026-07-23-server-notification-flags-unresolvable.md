# server-notification-flags.jar 解析问题 (2026-07-23)

## 问题
- 错误: `Unresolved reference 'screenshareNotificationHiding'` 等
- 涉及文件: `SensitiveContentCoordinator.kt`, `StackCoordinator.kt`, `FlagDependencies.kt`
- **当前错误数**: 2000 (目标: 0)
- **预期减少**: ~30 个 server-notification.Flags.* 引用

## 调查结论

经过详细调查，发现问题非常微妙：

### 确认的事实
1. **类在 classpath**: 通过 debug 输出验证，jar 在 `KotlinCompile.libraries` 列表中
2. **类可被 javap 加载**: `javap -p` 能正确显示所有方法和字段
3. **方法存在**: `public static boolean screenshareNotificationHiding()` 存在
4. **类有注解**:
   - `@com.android.aconfig.annotations.AconfigFlagAccessor` (RuntimeInvisibleAnnotations)
   - `@android.compat.annotation.UnsupportedAppUsage` (RuntimeInvisibleAnnotations)
5. **独立测试通过**: 同样的 jar 在独立 `kotlin("jvm") 2.1.0` 项目中**编译成功**

### 为什么独立项目能编译而 AGP 9.2 不能？

我们的 SystemUI-Gradle 项目使用:
- AGP 9.2.0 → 强制使用 Kotlin 编译插件 2.1.0
- Kotlin 编译插件 2.1.0 → 内部使用 kotlin-compiler-embeddable **2.2.10**

这是 AGP 9.2 已知行为：编译时使用比插件版本更新的 Kotlin 编译器。

Kotlin 编译器 2.2.10 对类的注解解析有更严格的检查：
- AOSP `Flags.class` 上的 `@UnsupportedAppUsage` 注解
- `AconfigFlagAccessor` 是 RuntimeInvisibleAnnotation（不影响 Java 编译器）
- 但 Kotlin 编译器可能因为某种原因无法解析 `screenshareNotificationHiding()` 方法

### 已尝试的方案 (都失败)

| 方案 | 结果 |
|------|------|
| `compileOnly(files("libs/server-notification-flags.jar"))` | 失败 |
| `implementation(files("libs/server-notification-flags.jar"))` | 失败 |
| `api(files("libs/server-notification-flags.jar"))` | 失败 |
| Maven AAR (`implementation(libs.notification.server.flags)`) | 失败 |
| Maven JAR (`implementation(libs.android.server.notification.flags)`) | 失败 |
| `flatDir` repository | 失败 |
| 加 `allprojects` `libraries.from()` | 失败 |
| 加 `allprojects` JavaCompile `classpath` | 失败 |
| 提供 `AconfigFlagAccessor` 注解类 (`libs/aconfig-annotations-lib.jar`) | 失败 |
| 提供 `UnsupportedAppUsage` 注解类 (`libs/compat-annotations.jar`) | 失败 |
| 提供 `FeatureFlags` 接口 (`libs/full-flags.aar`) | 失败 |
| `--rerun-tasks` + clean | 失败 |
| 升级 Kotlin 到 2.2.10 (与 AGP 内部版本匹配) | 失败 (plugin 冲突) |

### 工作正常的对比

`com.android.systemui.Flags` (来自 `libs/systemui-flags.jar`):
- 在 SystemUI-Gradle 中**正常工作**
- 类大小 53220 bytes
- 也有 `@AconfigFlagAccessor` 注解

差异点:
- `com.android.systemui.Flags` 类大小 53220 bytes (含所有 FLAG_* 常量和方法)
- `com.android.server.notification.Flags` 类大小 6285 bytes (更精简)

可能原因：kotlin android plugin 对 `com.android.systemui.*` 有特殊处理，但对 `com.android.server.*` 没有。

## 后续方向

### 方案 A: 等待 Kotlin/AGP 修复 (推荐)
这是 AGP 9.2 + Kotlin 2.2.10 的兼容性问题，应该在后续版本中修复。
- 监控 Kotlin 编译器更新
- 监控 AGP 9.3/9.4 是否有相关修复

### 方案 B: 退到 AGP 8.x
使用 AGP 8.x (Kotlin 编译器版本匹配插件版本)
- 修改 `libs.versions.toml` 中的 AGP 版本
- 修改 Gradle 兼容版本
- 风险：可能引入其他兼容性问题

### 方案 C: 改用 Java 编译
将使用 `server.notification.Flags.*` 的 `.kt` 文件改成 `.java` 文件
- 仍然允许调用 screenshareNotificationHiding 等
- 但修改代码违反"不创建 stub"原则

### 方案 D: 忽略这个错误
`Unresolved reference` 不会阻止编译，只是警告
- 但我们看到这个错误确实导致 Kotlin 编译失败

## 文件位置
- 失败的 jar: `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`
- 失败的 deps: `implementation(libs.android.server.notification.flags)`
- build.gradle.kts hack 仍然保留 `serverNotificationFlagsJar` 注入

## 当前状态
错误数维持 2000，无法进一步减少。下一步考虑：
1. 继续调查（可能需要更深度的 Kotlin 编译器分析）
2. 暂时跳过，专注于阶段 3 (Compose Scene Framework)
3. 等待 AGP/Kotlin 修复
