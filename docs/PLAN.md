# SystemUI-Gradle 详细开发计划 (PLAN.md)

> 最近更新: 2026-07-23 (基于 AGENTS.md)
> 当前错误数: 2000
> 目标错误数: 0 → 可编译

---

## 阶段总览

```
阶段 1 (本次提交): 文档 + 阶段性 commit  ← 当前
阶段 2: 高优先级阻塞错误 (server-notification-flags.jar 解析问题)
阶段 3: Compose Scene Framework 集成
阶段 4: 业务模块错误
阶段 5: 完整编译验证 + 打包
```

---

## 阶段 1: 文档与阶段性 commit (已完成大部分)

### 目标
- 记录所有规则到 AGENTS.md
- 清理 debug 代码
- 提交当前进度

### 任务
1. ✅ 创建 AGENTS.md
2. ✅ 清理 build.gradle.kts debug 输出
3. ✅ 写 docs/issues/2026-07-22-stub-cleanup-and-deps.md
4. ⏳ 提交本次工作

### 提交命令
```bash
git add -A
git commit -m "..."
```

---

## 阶段 2: server-notification-flags.jar 解析问题

### 问题描述
- 错误: `Unresolved reference 'screenshareNotificationHiding'`
- 涉及文件: `SensitiveContentCoordinator.kt`, `StackCoordinator.kt`, `FlagDependencies.kt`
- 现象: jar 在 classpath 中（DEBUG 输出验证），但 Kotlin 仍报 Unresolved
- 推测: Kotlin compile 缓存、AGP 9 处理 jar 的特殊行为

### 调查步骤

#### 步骤 2.1: 验证 jar 内容正确
```bash
unzip -p libs/server-notification-flags.jar META-INF/MANIFEST.MF
javap -p -classpath libs/server-notification-flags.jar com.android.server.notification.Flags | head
unzip -p libs/server-notification-flags.jar com/android/server/notification/Flags.class | javap -p /dev/stdin
```

#### 步骤 2.2: 验证 classpath 顺序
- 检查 `internalFlagsJars` 是否在 framework.jar 之前
- 尝试将 jar 放到 `compileOnly` 中测试

#### 步骤 2.3: 检查 AGP 9 jar 解析行为
- AGP 9 可能要求 jar 包含 `module-info.class` 或 JVM module
- 检查是否有 `META-INF/versions/` 目录标记 Java 版本

#### 步骤 2.4: 尝试解决方案

| 方案 | 描述 | 风险 |
|------|------|------|
| A: 改用 AAR | 把 Flags + 资源打包成 AAR | 复杂 |
| B: 强制 --rerun-tasks | 清 Kotlin 缓存 | 可能无效 |
| C: 复制 source 源码作为 Kotlin 源 | 在 SystemUI-core/src 下复制 com.android.server.notification.Flags.kt | 违反"不允许 stub"规则 |
| D: 查找是否有 services.jar 集成方式 | 把 services.jar 整个引入 | 太大（~50MB） |
| E: 改用 classes.jar 的某个子目录 | 把整个 services_intermediates 的 com.android.server.notification 包打包 | 复杂 |

**首选方案**: A - 提取 Flags + 相关依赖为 AAR，包含 Resources

#### 步骤 2.5: 提取完整 notification Flags

如果方案 A 不可行，尝试提取完整的 `com.android.server.notification.*` 包到单个 jar：

```bash
unzip -j aosp/out/target/common/obj/JAVA_LIBRARIES/services_intermediates/classes.jar 'com/android/server/notification/*' -d /tmp/sn_full/
jar cf libs/server-notification.jar /tmp/sn_full/...
```

#### 步骤 2.6: 失败时的兜底方案

如果所有方案都不可行：
- 临时**移除**所有 `com.android.server.notification.Flags.screenshareNotificationHiding` 的引用
- 用 `false` 替换（因为 AOSP 默认 screenshareNotificationHiding() = false）
- 但要明确记录这是"受限的临时方案"违反规则 P

### 预期错误数变化
- 目标: 2000 → 1850 (减少约 150 个错误)
- 涉及 ~13 个文件中的 `screenshareNotificationHiding` + ~30 个其他 server.Flags 引用

---

## 阶段 3: Compose Scene Framework 集成

### 问题描述
大量错误来自 `SystemUI-core/src/com/android/compose/` 包：
- `animation/scene/*` - Scene Framework
- `nestedscroll/*` - NestedScroll 连接器
- `theme/*` - Material You 主题
- `ui/util/*` - 实用工具

### AOSP 来源

#### 3.1 Scene Framework
- AOSP 源码: `frameworks/base/packages/SystemUI/.../scene/` (也可能是 Jetpack Compose 内部)
- 检查: `/home/conv/myspace/aosp/`
- 关键文件: `SceneTransitionLayout.kt`, `AnimateToScene.kt` 等

#### 3.2 Compose 内部
- `thenIf`, `drawInContainer` 等内部 API 来自 Compose compiler
- 可能需要 Compose AAR（特定版本）

### 实现方案

#### 方案 A: 提取 Scene Framework AAR (优先)

```bash
# 从 AOSP 编译产物提取
find /home/conv/myspace/aosp/out -name "*.aar" | grep -i "scene\|compose" | head
```

如果没有 AAR，需要：
1. 用 `gen_aar_maven.py` 模式编译生成
2. 或复制源码到独立 module

#### 方案 B: 复制源码为独立 module

```bash
# 创建 :SystemUI-scene module
mkdir -p SystemUI-scene/src/com/android/compose/scene
cp -r aosp/frameworks/.../scene/* SystemUI-scene/src/
```

### 关键检查

```bash
# 1. Scene Framework 是否存在于 AOSP?
find /home/conv/myspace/aosp -name "SceneTransitionLayout.kt" 2>/dev/null | head -3

# 2. 是否有编译好的 Scene jar?
find /home/conv/myspace/aosp/out -name "*.jar" | xargs -I{} \
  sh -c 'unzip -l "{}" 2>/dev/null | grep -q "scene/Scene" && echo "{}"' 2>/dev/null | head

# 3. 是否依赖 androidx.compose (Maven) 上游？
grep "import androidx.compose" SystemUI-core/src/com/android/compose/animation/scene/*.kt | head -3
```

### 预期错误数变化
- 目标: 1850 → 1500 (减少约 350 个错误)

---

## 阶段 4: 业务模块错误

### 4.1 分类剩余错误

```bash
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep -E "^e: " | \
  sed -E 's|.*\.kt:||' | \
  awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20
```

### 4.2 常见错误类型

| 类型 | 数量(预估) | 解决方案 |
|------|----------|---------|
| Compose Modifier 内部 | ~400 | 升级 Compose 依赖 |
| aconfig Flag | ~50 | 提取 aconfig Flags jar |
| 缺失的业务类 | ~200 | 提取 AOSP 业务类 |
| 测试代码 | ~300 | 排除测试代码 |

### 4.3 排除测试代码

```kotlin
android {
    sourceSets {
        getByName("main") {
            java.exclude("**/test/**", "**/tests/**")
        }
    }
}
```

### 4.4 升级 Compose 依赖

```kotlin
implementation("androidx.compose.foundation:foundation:1.8.0")  // 内部 API 更全
```

### 预期错误数变化
- 目标: 1500 → 500 (减少约 1000 个错误)

---

## 阶段 5: 最终验证

### 5.1 编译完整 :SystemUI-core

```bash
./gradlew :SystemUI-core:assembleDebug 2>&1 | tail -20
```

### 5.2 编译整个项目

```bash
./gradlew assembleDebug 2>&1 | tail -20
```

### 5.3 APK 打包

```bash
./gradlew :app:assembleDebug 2>&1 | tail -20
```

### 预期最终错误数
- 目标: 0 → 完整编译通过

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Compose Scene 是 AOSP 内部修改 | 无法用 Maven 引入 | 复制源码为 module |
| KAPT 与 AGP 9 不兼容 | Dagger 错误 | 用 KSP 或退到 AGP 8 |
| AOSP framework.jar 与 SDK 冲突 | 重复类 | 详细 AAR 拆分 |
| 资源 ID 不匹配 | R 类引用错误 | framework.jar + private res |

---

## 提交策略

每个阶段建议对应一个 commit：

1. `docs: add AGENTS.md with rules and progress`
2. `feat(deps): resolve server-notification-flags.jar ...`
3. `feat(scene): integrate Compose Scene Framework AAR`
4. `feat(deps): upgrade Compose to 1.8.x for internal APIs`
5. `fix: exclude test code from main source set`
6. `feat: complete SystemUI Gradle build pipeline`

---

## 开发时间估算

| 阶段 | 预估时间 | 累计 |
|------|---------|------|
| 阶段 1 | 0.5h | 0.5h |
| 阶段 2 | 2-4h | 2.5-4.5h |
| 阶段 3 | 4-8h | 6.5-12.5h |
| 阶段 4 | 2-4h | 8.5-16.5h |
| 阶段 5 | 1-2h | 9.5-18.5h |

总计: 约 1-2 个工作日

---

## 参考资源

- [AGENTS.md](./AGENTS.md) - 项目规则与进度
- [docs/GRADLE_MIGRATION_LOG.md](./GRADLE_MIGRATION_LOG.md) - 历史错误数演变
- [CarSystemUIGradle](../CarSystemUIGradle) - 参考实现 (同用户私有项目)
- [tools/gen_aar_maven.py](./tools/gen_aar_maven.py) - AAR 生成脚本
