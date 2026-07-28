# Stage 2-3 深度调研日志 (STAGE2-3-RESEARCH-LOG.md)

> **创建**: 2026-07-28
> **目的**: 深入分析 Stage 2 (server-notification-flags) 和 Stage 3 (Compose Scene) 的根因，供下个 AI 决策

---

## 1. 背景

### 1.1 项目状态

- 当前错误数: 2000
- Stage 2 阻塞, Stage 3 待启动
- 之前所有尝试都失败

### 1.2 已尝试清单

详见 `docs/issues/2026-07-28-server-flags-debug-session.md` §5.1 和 `docs/PITFALLS.md` §2

---

## 2. Stage 2 根因分析

### 2.1 现象复述

```java
// com.android.server.notification.Flags.class
public static boolean screenshareNotificationHiding();  // ← Kotlin 编译器看不到
```

- ✅ 类在 jar
- ✅ 方法在类里 (javap 验证)
- ✅ jar 在 classpath (./gradlew --debug 验证)
- ❌ Kotlin 编译器报 Unresolved

### 2.2 候选根因（按可能性排序）

#### 假设 1: Kotlin 2.2.10 对 `@UnsupportedAppUsage` 注解处理变化

**证据**:
- Flags.class 每个方法都有 `@UnsupportedAppUsage` 注解
- systemui-flags.jar (没有这个注解) 能编译
- 独立 kotlin("jvm") 2.1.0 项目能编译

**反证**:
- 没找到 Kotlin 2.2.10 release notes 关于这个变化的明确文档

**验证方法**:
- 提取 Flags.class 的注解，看是否需要换注解
- 用 2.1.0 编译同一个 Flags class

#### 假设 2: `@AconfigFlagAccessor` 注解缺失

**证据**:
- Flags.class 有 `@AconfigFlagAccessor` 注解
- 这个注解类在 `com.android.aconfig.annotations.AconfigFlagAccessor`

**反证**:
- 我们已经提供 `aconfig-annotations-lib.jar`

**验证方法**:
- javap `aconfig-annotations-lib.jar`，确认有 `AconfigFlagAccessor`

#### 假设 3: `FeatureFlags` 接口缺失

**证据**:
- Flags.class 内部有 `private static com.android.server.notification.FeatureFlags FEATURE_FLAGS;`
- 字段类型 `FeatureFlags` 必须存在

**反证**:
- 字段是 private，不应影响方法解析

**验证方法**:
- 在 AOSP 找 FeatureFlags.class
- 提取到 server-notification-flags.jar 里

#### 假设 4: Kotlin 2.2.10 类加载逻辑严格化

**证据**:
- AGP 9 嵌入 2.2.10，比项目 plugins 2.1.0 新
- 类似问题在 stackoverflow 报道过

**反证**:
- 没有具体复现 case

**验证方法**:
- 强制 Kotlin 2.2.10 编译（如果有别的项目能编译同 jar）

#### 假设 5: AGP 9 jar 转换问题

**证据**:
- AGP 9 对 jar 处理逻辑改变
- 老的 `flatDir` 注入可能失效

**反证**:
- 已经用 `implementation(libs.android.server.notification.flags)` 走标准路径

**验证方法**:
- 看 AGP 9 文档关于 jar 解析

### 2.3 推荐的诊断流程

#### 步骤 A: 完整 K2JVMCompiler 编译测试

```bash
# 把 AGP 编译时的所有 jar 都用上
CP=$(./gradlew :SystemUI-core:compileDebugKotlin --debug 2>&1 | grep -oE "[-]classpath [^ ]+" | head -1 | cut -d' ' -f2-)

java -cp "$KC:$KS:$KR:$KX" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
  -cp "$CP" \
  -d /tmp/out -jvm-target 21 \
  -Xverbose \
  -Xlog-level=DEBUG \
  SensitiveContentCoordinator.kt 2>&1 | grep -iE "(notification|flags|error|warn)" | head -50
```

**预期**: 看 Kotlin 编译器为什么不解析 Flags 类。

#### 步骤 B: 提取 FeatureFlags

```bash
# 找 AOSP 编译产物
find /home/conv/myspace/aosp/out -name "FeatureFlags.class" -path "*notification*" 2>/dev/null | head

# 如果找到
JAR=libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar
FEATURE_FLAGS=$(find /home/conv/myspace/aosp/out -name "FeatureFlags.class" -path "*notification*" | head -1)
mkdir -p /tmp/fn && cd /tmp/fn
unzip -o "$FEATURE_FLAGS"  # 它本身可能是 jar
jar uf "$JAR" com/android/server/notification/FeatureFlags.class
```

#### 步骤 C: 加 verbose 日志

```kotlin
// build.gradle.kts (root)
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions {
        freeCompilerArgs.add("-Xverbose")
        freeCompilerArgs.add("-Xlog-level=DEBUG")
    }
}
```

然后重跑，看 Kotlin 输出。

#### 步骤 D: 锁 Kotlin 插件到 2.2.10

```toml
# libs.versions.toml
[plugins]
kotlin-android = { id = "org.jetbrains.kotlin.android", version = "2.2.10" }
```

这要求 AGP 9.2 + Kotlin 2.2.10 plugin 兼容。

**风险**: AGP 9.2 测过哪些 Kotlin plugin 版本未知。

### 2.4 决策树

```
Step A 成功找到具体错误原因？
├─ 是 → 针对性 fix
└─ 否 → Step B (FeatureFlags)
        ├─ 成功？
        │  └─ 是 → 完成 Stage 2
        └─ 否 → Step C (verbose 日志)
                ├─ 看到原因？
                │  └─ 是 → 针对性 fix
                └─ 否 → 接受阻塞，转 Stage 3
```

---

## 3. Stage 3 Compose Scene Framework 分析

### 3.1 缺失符号

| 符号 | 出现位置 | 用途 |
|------|---------|------|
| `thenIf` | Element.kt, SceneTransitionLayout.kt | Modifier 扩展，根据条件组合 |
| `drawInContainer` | Element.kt | DrawModifier，把 draw 限定在容器内 |
| `ContainerState` | Content.kt | Scene 内容容器状态 |
| `modifiers.*` | 多处 | 子包 |
| `graphics.*` | 多处 | 子包 |

### 3.2 这些符号的来源

- **不是 androidx.compose.foundation/Animation 等公开包**
- **不是 androidx.compose.material/material3**
- **疑似 androidx.compose.ui 内部 Modifier 接口**

### 3.3 在 androidx 源码中找

```bash
# 找 androidx-compose-ui 源码（如果有 aosp 拷贝）
find /home/conv/myspace/aosp -name "Modifier.kt" 2>/dev/null | head

# 或搜索方法定义
grep -rn "fun.*thenIf" /home/conv/myspace/aosp 2>/dev/null | head -3
grep -rn "fun.*drawInContainer" /home/conv/myspace/aosp 2>/dev/null | head -3
```

### 3.4 实现方案

#### 方案 A: 升级 androidx.compose 到 1.8.0

```kotlin
implementation("androidx.compose.foundation:foundation:1.8.0")
implementation("androidx.compose.ui:ui:1.8.0")
```

**风险**: 1.8.0 可能不支持 1.7.5 的 API，触发更多错误。

#### 方案 B: 提取 androidx.compose.internal

```bash
# Compose 内部 jar 不公开
# 但可以通过 aosp /external/ 找到源码（如果有）
ls /home/conv/myspace/aosp/external/jetpack/
```

#### 方案 C: 排除 scene 源码

```kotlin
android {
    sourceSets {
        getByName("main") {
            java.exclude(
                "com/android/compose/animation/scene/**",
                "com/android/compose/animation/scene",
                "com/android/compose/animation/scene/*"
            )
        }
    }
}
```

**风险**: Scene Framework 是 SystemUI 新 UI 核心，禁用后 SceneContainer 等都不工作。

#### 方案 D: 复制源码为 module（违反规则 P）

```bash
mkdir -p SystemUI-compose-scene/src/com/android/compose/animation/scene
cp -r /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src/com/android/compose/animation/scene/* SystemUI-compose-scene/src/com/android/compose/animation/scene/
```

**风险**: 是把问题推后，仍然 unresolved。

### 3.5 推荐路径

1. **先 grep 符号**: 找 thenIf/drawInContainer 究竟在 androidx 哪个版本引入
2. **升级 Compose 到 1.8.0**: 试错
3. **如果仍失败**: 接受阻塞或排除源码

---

## 4. 文档交叉引用

- `docs/HANDOFF.md` - 主入口
- `docs/CURRENT_STATE.md` §3 - 错误分类
- `docs/PLAN.md` - 阶段计划
- `docs/PITFALLS.md` §2, §3 - 失败方案
- `docs/issues/2026-07-28-server-flags-debug-session.md` - 本次实验数据
- `docs/architecture/STAGE2-3-RESEARCH-LOG.md` - 本文件

---

## 5. 数据附录

### 5.1 server-notification-flags.jar 详情

```
Size: 6285 bytes
Entry: com/android/server/notification/Flags.class
Compiler: javac (Java)
Methods: 28 个 boolean static + 25 个 String constants
Annotations:
  - @com.android.aconfig.annotations.AconfigFlagAccessor (RuntimeInvisible)
  - @android.compat.annotation.UnsupportedAppUsage (RuntimeInvisible)
```

### 5.2 systemui-flags.jar 对比

```
Size: 53220 bytes
Entry: com/android/systemui/Flags.class
Methods: 约 200 个 boolean static + 200 个 String constants
Annotations: 同样是 @AconfigFlagAccessor
```

差异：大小差 10x。但同样有 `@AconfigFlagAccessor`，所以问题**不**是该注解。

### 5.3 当前 classpath（实测）

```
android.jar                                  # SDK
framework.jar                                # AOSP 完整
framework-statsd.jar
android.car.jar
WindowManager-Shell.jar
android_module_lib_stubs_current.jar
monet.jar
SystemUI-proto.jar
SystemUI-tags.jar
SystemUI-statsd.jar
systemui-flags.jar                           # ✅ 工作
notification-flags-1.0.0.jar                 # ❌ 不工作
... 其他 androidx/compose/maven
```

### 5.4 build.gradle.kts 当前配置

```kotlin
// build.gradle.kts (root) - hack
val frameworkJar = file(".../libs/framework.jar")
val internalFlagsJars = listOf(
    file(".../libs/systemui-flags.jar"),
    file(".../libs/monet.jar")
)
val serverNotificationFlagsJar = file(".../libs/maven/.../notification-flags-1.0.0.jar")

tasks.withType<JavaCompile>().configureEach {
    if (frameworkJar.exists()) {
        options.bootstrapClasspath = files(frameworkJar) + ...
        classpath = files(frameworkJar) + classpath
    }
    classpath = files(internalFlagsJars) + classpath
    if (serverNotificationFlagsJar.exists()) {
        classpath = files(serverNotificationFlagsJar) + classpath
    }
}

tasks.withType<KotlinCompile>().configureEach {
    if (serverNotificationFlagsJar.exists()) {
        libraries.from(serverNotificationFlagsJar)
    }
    libraries.from(internalFlagsJars)
    if (frameworkJar.exists()) {
        libraries.from(frameworkJar)
    }
}
```

```kotlin
// SystemUI-core/build.gradle.kts (新加)
implementation(libs.android.server.notification.flags)
```

---

**下一步**: 阅读 `docs/GRADLE_MIGRATION_LOG.md` 了解历史。