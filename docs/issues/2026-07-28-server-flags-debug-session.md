# Stage 2: server-notification-flags.jar 调试 session (2026-07-28)

> 上一阶段: `docs/issues/2026-07-23-server-notification-flags-unresolvable.md`
> 本次 session: 2026-07-28

## TL;DR

**结论**: `notification-flags-1.0.0.jar` 实际**已经在 Kotlin 编译器 classpath 中**（`./gradlew --debug` 验证），但是 Kotlin 2.2.10 编译器仍报 `Unresolved reference 'screenshareNotificationHiding'`。我的修改未减少错误数（仍 2000）。问题不在 classpath 注入，而在 Kotlin 编译器后端对类的处理。

下个 AI Agent 必须重新分析，可能需要：
- 换 kotlin 编译器版本
- 提取其他相关类（`FeatureFlags` 接口）
- 用 K2JVMCompiler 手工调用并加 `-Xverbose` 看真实日志

---

## 1. 起点

继承自 `2026-07-23-server-notification-flags-unresolvable.md`，已知：
- 错误: `Unresolved reference 'screenshareNotificationHiding'` × 13 + `FlagDependencies.kt` 6 个
- 之前怀疑: AGP 9 + Kotlin 2.2.10 不兼容
- 之前尝试: 升级 Kotlin 失败

## 2. 本次 session 关键发现

### 2.1 `libs/server-notification-flags.jar` 是空 jar

```bash
$ unzip -l libs/server-notification-flags.jar
# 完全空！0 文件！
```

正确 jar 在 `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`：
```
Length      Date    Time    Name
      6285  2026-07-23 22:23   com/android/server/notification/Flags.class
```

`Flags.class` 用 javap 验证完整：
```java
public final class com.android.server.notification.Flags {
  public static boolean screenshareNotificationHiding();
  public static boolean politeNotifications();
  public static boolean crossAppPoliteNotifications();
  public static boolean vibrateWhileUnlocked();
  // ... 28 个 boolean 方法
}
```

### 2.2 `build.gradle.kts` 已有 hack 注入

```kotlin
// build.gradle.kts (root)
val serverNotificationFlagsJar = file("${rootProject.projectDir}/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar")
tasks.withType<JavaCompile>().configureEach {
    classpath = files(serverNotificationFlagsJar) + classpath
}
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    if (serverNotificationFlagsJar.exists()) {
        libraries.from(serverNotificationFlagsJar)
    }
}
```

但 `SystemUI-core/build.gradle.kts` 没显式声明。所以我加了一行：

```kotlin
// SystemUI-core/build.gradle.kts (新加)
implementation(libs.android.server.notification.flags)
```

这个 alias 已在 `libs.versions.toml`:
```toml
android-server-notification-flags = { group = "com.android.server", name = "notification-flags", version = "1.0.0" }
```

### 2.3 classpath 实际验证

跑了 `./gradlew :SystemUI-core:compileDebugKotlin --debug | grep -oE "[-]classpath [^ ]+"`，**jar 确实在 classpath 里**：

```
-classpath /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar:
/home/conv/myspace/SystemUI-Gradle/libs/framework.jar:
/home/conv/myspace/SystemUI-Gradle/libs/systemui-flags.jar:
/home/conv/myspace/SystemUI-Gradle/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar:
... 其余 androidx/compose jars
```

`GradleCompilerRunnerWithWorkers` 调用 `K2JVMCompiler` 时，jar 已经被 prep'd 到 classpath。

### 2.4 手动 kotlinc 测试

```bash
KC=/home/conv/.gradle/caches/modules-2/files-2.1/org.jetbrains.kotlin/kotlin-compiler-embeddable/2.2.10/.../kotlin-compiler-embeddable-2.2.10.jar
KS=/home/conv/.gradle/caches/modules-2/files-2.1/org.jetbrains.kotlin/kotlin-stdlib/2.2.10/.../kotlin-stdlib-2.2.10.jar
KR=/home/conv/.gradle/caches/modules-2/files-2.1/org.jetbrains.kotlin/kotlin-reflect/2.2.10/.../kotlin-reflect-2.2.10.jar
KX=/home/conv/.gradle/wrapper/dists/gradle-9.5.0-bin/.../lib/kotlinx-coroutines-core-jvm-1.10.2.jar

java -cp "$KC:$KS:$KR:$KX" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
  -cp "/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar:/home/conv/myspace/SystemUI-Gradle/libs/framework.jar:$1:$KS:$KR" \
  -d /tmp/out -jvm-target 21 -no-stdlib -no-reflect \
  SensitiveContentCoordinator.kt
```

**结果**: 仍报 `unresolved reference 'Flags'`。但注意这次只给 `framework.jar + android.jar + notification-flags.jar + kotlin-stdlib`。**没有 systemui-flags.jar**。

注意 FlagDependencies.kt 报错:
```
error: unresolved reference 'Flags'.
import com.android.server.notification.Flags.screenshareNotificationHiding
```

**正确** —— Flags 完全没找到。但 SensitiveContentCoordinator.kt 在 AGP 编译时**有**同样错误，说明：
- AGP 编译时 classpath 完全相同
- 错误完全相同

但报错不是 'Flags' 类找不到，而是 `screenshareNotificationHiding` 方法找不到？让我重看：

#### 实际错误（不是 'Flags' 类缺失）

来自 `/tmp/build.log`:
```
e: SensitiveContentCoordinator.kt:25:46 Unresolved reference 'screenshareNotificationHiding'.
e: SensitiveContentCoordinator.kt:98:24 Unresolved reference 'screenshareNotificationHiding'.
```

**奇怪**: 不是 'Flags' 类找不到，而是 `screenshareNotificationHiding` 方法找不到。

可能解释：
- `kotlin 2.2.10` 编译器对 `@UnsupportedAppUsage` 注解的检查更严
- 当 `@UnsupportedAppUsage` 标记整个类时，kotlin 编译器拒绝解析其方法
- 或当 `@UnsupportedAppUsage` 在每个方法上时（系统检查模式），kotlin 拒绝看到它们

`Flags.class` 注解 (`javap -v`):
```
RuntimeInvisibleAnnotations:
  0: #92() com.android.aconfig.annotations.AconfigFlagAccessor
  1: #93() android.compat.annotation.UnsupportedAppUsage
```

每个方法都有 `@AconfigFlagAccessor` + `@UnsupportedAppUsage`。

### 2.5 我的修改和测量

```diff
// SystemUI-core/build.gradle.kts
+    // server-notification Flags (AOSP @aconfig Flags) - 显式声明，避免 Kotlin 编译器遗漏
+    implementation(libs.android.server.notification.flags)
```

```diff
// build.gradle.kts
        tasks.withType<JavaCompile>().configureEach {
+            // 把 server notification flags jar 放在 classpath 前面
+            if (serverNotificationFlagsJar.exists()) {
+                classpath = files(serverNotificationFlagsJar) + classpath
+            }
            if (frameworkJar.exists()) {
                ...
            }
```

构建报告:
- 第一次 (build.log): 2000 错误, 13 screenshareNotificationHiding
- 第二次 (build2.log): 2000 错误, 13 screenshareNotificationHiding
- 第三次 (build3.log): 2000 错误, 13 screenshareNotificationHiding

**无改善**。

---

## 3. 失败原因推测

### 3.1 假设 A: 编译器后端问题

可能性：高
- 现象: jar 在 classpath, javap 能看到方法, 但是 Kotlin 编译器 'unresolved'
- 推测: Kotlin 2.2.10 编译器对 `@UnsupportedAppUsage` 注解处理方式变了
- 证据: 独立 kotlin("jvm") 项目能编译（2026-07-23 文档）

### 3.2 假设 B: classpath 顺序问题

可能性：低
- 已验证通过 `libraries.from(serverNotificationFlagsJar)` 放在 framework.jar 之前
- 但还是 unresolved

### 3.3 假设 C: 缺 `FeatureFlags` 接口

可能性：中
- `Flags.class` 内部有 `private static com.android.server.notification.FeatureFlags FEATURE_FLAGS;`
- 但 FeatureFlags 是字段类型，不是方法返回类型
- 即使该接口缺失也不应影响 `screenshareNotificationHiding()` 方法解析

### 3.4 假设 D: AGP 9 内部 jar 转型

可能性：中
- AGP 9 处理 jar 时可能做了优化
- 错误信息明确是 Kotlin 编译器（`e: file:`），不是 javac

### 3.5 假设 E: Kotlin 编译缓存

可能性：低
- 已用 `--rerun-tasks`

---

## 4. 推荐的下一个实验

### 4.1 用 K2JVMCompiler 完整 classpath 跑

把 systemui-flags.jar 也加入，然后编译同样文件，看是否报错。

```bash
SF=/home/conv/myspace/SystemUI-Gradle/libs/systemui-flags.jar
FL=/home/conv/myspace/SystemUI-Gradle/libs/framework.jar
JS=/home/conv/myspace/SystemUI-Gradle/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar
SC=/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar

# 关键: 加上 systemui-flags.jar
java -cp "$KC:$KS:$KR:$KX" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
  -cp "$SC:$FL:$SF:$JS:$KS:$KR" \
  -d /tmp/out -jvm-target 21 -no-stdlib -no-reflect \
  SensitiveContentCoordinator.kt
```

**对比**: 
- AGP 编译时 classpath 包含相同 jars
- 直接 K2JVMCompiler 跑出来 vs AGP 编译

### 4.2 加 `-Xverbose` / `-Xlog-level=DEBUG`

Kotlin 编译器支持 verbose 模式。AGP 9 调用 K2JVMCompiler 时可加：

```kotlin
compilerOptions {
    freeCompilerArgs.add("-Xverbose")
    // 或
    freeCompilerArgs.add("-Xlog-level=DEBUG")
}
```

或将 `org.jetbrains.kotlin.cli.jvm.K2JVMCompiler` 直接替换为 `org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -Xverbose`，看真实日志。

### 4.3 提取 `FeatureFlags` 接口

```bash
# 在 AOSP 查找
find /home/conv/myspace/aosp -name "FeatureFlags.java" -path "*notification*" 2>/dev/null
# 或在 out/ 查找
find /home/conv/myspace/aosp/out -name "FeatureFlags.class" 2>/dev/null | head
```

如果有，抽出来和 Flags.class 一起打包。

### 4.4 降级 Kotlin 版本

- AGP 9.2 嵌入 2.2.10
- 尝试 mx.toml 锁 Kotlin 2.1.0（但这是项目级 plugins，可能不冲突）

```toml
# libs.versions.toml
kotlin = "2.1.0"  # 保住插件版本
# 但 AGP 仍会嵌入 2.2.10
```

### 4.5 转移到 Stage 3

如果 Stage 2 在 4 小时内无法突破，记录这个 BLOCKER 在 `docs/PITFALLS.md`，**接受**它作为"已知阻塞"，先推进 Stage 3/4。

---

## 5. 修改文件

### 5.1 实际修改

```diff
# SystemUI-core/build.gradle.kts
+    // server-notification Flags (AOSP @aconfig) - 显式声明
+    implementation(libs.android.server.notification.flags)
```

```diff
# build.gradle.kts (root)
+            // 把 server notification flags jar 放在 classpath 前面
+            if (serverNotificationFlagsJar.exists()) {
+                classpath = files(serverNotificationFlagsJar) + classpath
+            }
```

### 5.2 是否回滚

**建议保留**。这些改动无害（不增加错误数）。但下个 AI 可以考虑合并或简化。

---

## 6. 错误数演变

| 时点 | 错误数 | 改动 |
|------|--------|------|
| 进入本次 session | 2000 | 继承 |
| 加 implementation | 2000 | 无变化 |
| 加 libraries.from 双重 | 2000 | 无变化 |
| 离开本次 session | 2000 | 无突破 |

---

## 7. 下次 AI Agent 行动建议

1. **重读本文件** + `2026-07-23-server-notification-flags-unresolvable.md`
2. **跑 4.1 推荐的实验**（完整 K2JVMCompiler）
3. **尝试 4.2 加 verbose**（看真实日志）
4. **如果仍然失败**，按 4.5 接受阻塞，转 Stage 3
5. **不要先尝试降级 AGP**（破坏性改动，需要用户同意）

---

## 8. 实验数据

### 8.1 错误统计

```
=== build.log (修改前) ===
Total errors: 2000
screenshareNotificationHiding: 13
FlagDependencies: 6

=== build2.log (加 implementation) ===
Total errors: 2000
screenshareNotificationHiding: 13
FlagDependencies: 6

=== build3.log (加 双重注入) ===
Total errors: 2000
screenshareNotificationHiding: 13
FlagDependencies: 6
```

### 8.2 关键 javap 数据

```bash
$ javap -p /tmp/flagtest/com/android/server/notification/Flags.class
public final class com.android.server.notification.Flags {
  public static boolean screenshareNotificationHiding();
  public static boolean politeNotifications();
  ...
}

$ javap -v /tmp/flagtest/com/android/server/notification/Flags.class
RuntimeInvisibleAnnotations:
  0: #92() com.android.aconfig.annotations.AconfigFlagAccessor
  1: #93() android.compat.annotation.UnsupportedAppUsage
```

### 8.3 关键 classpath 验证

```bash
$ ./gradlew :SystemUI-core:compileDebugKotlin --debug 2>&1 | grep -oE "[-]classpath [^ ]+" | tr ':' '\n' | grep -i notification
/home/conv/myspace/SystemUI-Gradle/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar
```

✅ 类在 classpath。
