# 2026-07-22 补充: framework.jar 合并到 SDK android.jar

## 背景

在 `702679e` commit 中替换 framework.jar 为 AOSP 完整版本后，错误从
5,296 降到 4,675。但仍有 1,667 个错误（与替换前 5,296 比较），看起来
framework.jar 的 @hide API 没有被 Kotlin 编译器使用。

## 问题：framework.jar 在 classpath 中被 SDK android.jar 遮蔽

### 诊断

通过在 `build.gradle.kts` 添加 `doFirst { println(... libraries ...) }`
输出编译期 classpath：

```
=== KOTLIN CP for :SystemUI-core:compileDebugKotlin ===
[0] android.jar                              ← SDK (SysUISdk) 在最前
[1] core-lambda-stubs.jar
[2] R.jar
[3] framework.jar                            ← AOSP 完整版被排在后面
[4] framework-statsd.jar
[5] android.car.jar
[6] WindowManager-Shell.jar
...
```

Kotlin 编译器按顺序查找符号，**先到先得**。android.jar 中的简化版
(只有 `SOME_AUTH_REQUIRED_AFTER_USER_REQUEST`，缺
`SOME_AUTH_REQUIRED_AFTER_TRUSTAGENT_EXPIRED` 等) 遮蔽了
framework.jar 的完整版。

### 失败的尝试

1. `libraries.from(frameworkJar)` — 已加，但顺序错误
2. 修改 classpath order — AGP 不允许重排 android.jar
3. `bootstrapClasspath` — 仅对 JavaCompile 有效，Kotlin 用 libraries

## 解决方案：合并 framework.jar + android.jar

### 策略

framework.jar 作为"主"，android.jar 补充 framework.jar 没有的类。
最终 jar 替换 SDK android.jar。

### 合并脚本 (python3)

```python
import os, shutil

# 提取
os.makedirs('framework'); os.system("unzip -q framework.jar -d framework")
os.makedirs('android');   os.system("unzip -q android.jar   -d android")

# 计算差集
android_entries = set()
for r, _, fs in os.walk('android'):
    for f in fs:
        android_entries.add(os.path.relpath(os.path.join(r,f), 'android'))

framework_entries = set()
for r, _, fs in os.walk('framework'):
    for f in fs:
        framework_entries.add(os.path.relpath(os.path.join(r,f), 'framework'))

# 复制 framework.jar 全部 + android.jar 中 framework.jar 没有的
shutil.copytree('framework', 'merged')
for e in android_entries - framework_entries:
    src = os.path.join('android', e)
    dst = os.path.join('merged', e)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)

# 打包
os.system("cd merged && jar cf android-merged.jar .")
```

### 合并产物

`libs/android-merged.jar` (44MB, 29131 个 .class)
- framework.jar (master): 25918 个 .class
- + android.jar 补充: 7560 个 .class
- - framework/android 重复: 0

### 替换 SDK android.jar

```bash
cp libs/android-merged.jar /opt/SysUISdk/android.jar
```

`build.gradle.kts` 的 framework.jar 注入逻辑保留 (作为冗余保险)，
不再需要 libs/framework.jar.bak (已经 commit 进 702679e)。

## 验证

```bash
unzip -p /opt/SysUISdk/android.jar \
  com/android/internal/widget/LockPatternUtils\$StrongAuthTracker.class | \
  javap -p | grep SOME_AUTH_REQUIRED_AFTER
```

输出 (合并后):
```
public static final int SOME_AUTH_REQUIRED_AFTER_USER_REQUEST;
public static final int SOME_AUTH_REQUIRED_AFTER_TRUSTAGENT_EXPIRED;
public static final int SOME_AUTH_REQUIRED_AFTER_ADAPTIVE_AUTH_REQUEST;
```

输出 (SDK 原版):
```
public static final int SOME_AUTH_REQUIRED_AFTER_USER_REQUEST;  ← 缺 2 个
```

## 编译错误数演变

| Commit | 描述 | 错误数 |
|--------|------|--------|
| `702679e` | 替换 framework.jar (但被 SDK 遮蔽) | 4,675 |
| **`5836ec4`** | **合并到 SDK android.jar** | **3,008** |

降幅 1,667 = 大量 @hide API 现在可解析。

## 剩余错误 top 25

```
34 it           ← 类型推断级联 (通常由其他错误触发)
29 data         ← 同上
28 color        ← R.color.X (来自 internal.R.color 仍缺)
26 compose      ← Scene 框架
26 ColorScheme  ← Material ColorScheme
25 composable
16 T            ← 泛型推断
15 quickaffordance
15 domain
15 Preferences
14 communalSceneKtfRefactor  ← Flag
14 CommunalHubState         ← Scene
13 screenshareNotificationHiding  ← Flag
12 modifiers
11 preferences
11 monet        ← Monet color engine
11 graphics
11 fasterUnlockTransition  ← Flag
11 Style
10 thenIf       ← Scene framework
```

## 后续计划

1. **Flags 修复**：手写 `Flags.kt` 缺失字段 (`communalSceneKtfRefactor` 等)
   - 检查是否因为 `Flags.kt` 编译错误导致级联失败
2. **Monet API**：从 AOSP `frameworks/base/graphics/java/android/graphics/Monet*` 复制
3. **Scene 框架**：补全 `SceneTransitionLayout`, `MovableElement` 等
4. **Compose ColorScheme**：检查 androidx.compose.material3 版本