# SystemUI-Gradle 详细开发计划 (PLAN.md)

> **最后更新**: 2026-07-28
> **当前错误数**: 2000
> **目标错误数**: 0 → 可编译
> **当前阶段**: Stage 2 (server-notification-flags.jar) — **阻塞**

---

## 阶段总览

```
阶段 1 ✅ (2026-07-22): 文档 + 阶段性 commit
阶段 2 🚧 (2026-07-23 ~ 现在): server-notification-flags.jar 解析问题 — 阻塞中
阶段 3 ⏳ (待启动): Compose Scene Framework 集成
阶段 4 ⏳ (待启动): 业务模块错误
阶段 5 ⏳ (待启动): 完整编译验证 + 打包
```

---

## 阶段 1: 文档与阶段性 commit ✅ 已完成 (2026-07-22)

### 任务
1. ✅ 创建 AGENTS.md
2. ✅ 清理 build.gradle.kts debug 输出
3. ✅ 写 docs/issues/2026-07-22-stub-cleanup-and-deps.md
4. ✅ 提交 (commit `a7176c7` 等)

### 错误数变化
- 进入: 2412
- 离开: 2000
- 减少: 412（删除 stub + 加 Monet + 加 SystemUI Flags）

---

## 阶段 2: server-notification-flags.jar 解析问题 🚧 阻塞中

### 问题描述

- 错误: `Unresolved reference 'screenshareNotificationHiding'` × 13 + `FlagDependencies.kt` 6 个
- 现象: jar 在 classpath 中（`./gradlew --debug` 验证），但 Kotlin 仍报 Unresolved
- 推测根因: AGP 9 嵌入 Kotlin 2.2.10 + `@UnsupportedAppUsage` 注解交互

### 详细调研文档

- `docs/issues/2026-07-23-server-notification-flags-unresolvable.md` (2026-07-23 第一轮)
- `docs/issues/2026-07-28-server-flags-debug-session.md` (2026-07-28 第二轮)
- `docs/architecture/STAGE2-3-RESEARCH-LOG.md` (深度调研)

### 涉及文件

```
SensitiveContentCoordinator.kt       (25, 98, 108, 115, 178, 211, 217)
StackCoordinator.kt                  (20, 71)
NotifUiAdjustmentProvider.kt         (25, 73, 92, 145)
FlagDependencies.kt                  (79, 82, 85)
```

### 已尝试方案（全部失败）

| # | 方案 | 失败原因 |
|---|------|---------|
| 1 | `compileOnly(files("libs/server-notification-flags.jar"))` | 空 jar |
| 2 | `implementation(files("libs/server-notification-flags.jar"))` | 空 jar |
| 3 | Maven AAR | 仍 unresolved |
| 4 | Maven JAR | 仍 unresolved |
| 5 | flatDir repository | 仍 unresolved |
| 6 | allprojects `libraries.from()` 注入 | 注入成功但 unresolved |
| 7 | 提供 `AconfigFlagAccessor` 注解 | 仍 unresolved |
| 8 | 提供 `UnsupportedAppUsage` 注解 | 仍 unresolved |
| 9 | 提供 `FeatureFlags` 接口 | 未尝试 |
| 10 | 升级 Kotlin 到 2.2.10 | plugin 冲突 |
| 11 | 独立 kotlin("jvm") 2.1.0 项目测试 | 成功 → 证明问题在 AGP+Kotlin2.2.10 |

### 下一步（建议下个 AI 优先尝试）

| # | 实验 | 预期 | 风险 |
|---|------|------|------|
| A | 提取 `FeatureFlags` 接口跟 Flags 一起打包 | 可能解决 | 低 |
| B | 加 `-Xverbose` 看 Kotlin 真实日志 | 诊断根因 | 低 |
| C | K2JVMCompiler 完整 classpath（含 systemui-flags）跑测试 | 验证问题是否在 Kotlin 版本 | 低 |
| D | 接受阻塞，转 Stage 3 | 不阻塞主线 | 无 |

### 预期错误数变化

- 如果 A/B 成功: 2000 → 1970 (减少 30)
- 如果 D: 维持 2000，先做 Stage 3

---

## 阶段 3: Compose Scene Framework 集成 ⏳

### 问题描述

大量错误来自 `SystemUI-core/src/com/android/compose/` 包：
- `animation/scene/*` (12 个)
- `theme/*` (60 个)
- `nestedscroll/*` (0 个，已排除? 待确认)
- `ui/util/*` (0 个，已排除? 待确认)

### AOSP 来源

#### 3.1 Scene Framework

```bash
# 1. Scene Framework 是否存在于 AOSP?
find /home/conv/myspace/aosp -name "SceneTransitionLayout.kt" 2>/dev/null | head -3

# 2. 是否有编译好的 Scene jar?
find /home/conv/myspace/aosp/out -name "*.jar" | xargs -I{} \
  sh -c 'unzip -l "{}" 2>/dev/null | grep -q "scene/Scene" && echo "{}"' 2>/dev/null | head

# 3. 是否依赖 androidx.compose (Maven) 上游？
grep "import androidx.compose" SystemUI-core/src/com/android/compose/animation/scene/*.kt | head -3
```

#### 3.2 缺失符号

| 符号 | 类型 | 来源 |
|------|------|------|
| `thenIf` | Modifier 扩展 | Compose 内部 |
| `drawInContainer` | DrawModifier | Compose 内部 |
| `ContainerState` | 状态类 | Compose 内部 |
| `modifiers.*` | 子包 | Compose 内部 |
| `graphics.*` | 子包 | Compose 内部 |

### 实现方案

| 方案 | 描述 | 风险 |
|------|------|------|
| A | 提取 AOSP Scene AAR | 中（可能不存在） |
| B | 升级 androidx.compose 到 1.8.0 | 中 |
| C | 复制源码为独立 module | 中（违反规则 P? 待确认） |
| D | 排除源码（暂时禁用） | 高（用户看不到 UI） |

### Compose Theme R 冲突

- `AndroidColorScheme.kt` 同时 import `com.android.systemui.R` 和 `com.android.compose.theme.R`
- 解决方案：alias import

```kotlin
import com.android.systemui.R as SystemUiR
import com.android.compose.theme.R as ComposeR
```

### 预期错误数变化

- 成功: 2000 → 1850 (减少 150)

---

## 阶段 4: 业务模块错误 ⏳

### 4.1 分类剩余错误

```bash
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep -E "^e: " | \
  sed -E 's|.*\.kt:||' | \
  awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20
```

### 4.2 顶级错误包

| 错误数 | 包 |
|--------|-----|
| 81 | systemui/volume/domain/interactor |
| 79 | systemui/bluetooth/qsdialog |
| 57 | systemui/scene |
| 57 | systemui/communal/widgets |
| 56 | systemui/volume/panel/component/mediaoutput/domain/interactor |
| 51 | systemui/keyguard/ui/preview |
| 51 | systemui/education/data/repository |
| 48 | systemui/volume/dialog/sliders/ui |
| 46 | systemui/communal/data/repository |

### 4.3 常见错误类型

| 类型 | 数量(预估) | 解决方案 |
|------|----------|---------|
| Compose Modifier 内部 | ~400 | Stage 3 升级 Compose |
| aconfig Flag | ~50 | Stage 2 修复 |
| 缺失的业务类 | ~200 | 提取 AOSP 业务类 |
| 测试代码 | ~300 | 排除测试代码 |
| KAPT 注入 | ~600 | 解 KAPT 阻塞 |

### 4.4 排除测试代码

```kotlin
android {
    sourceSets {
        getByName("main") {
            java.exclude("**/test/**", "**/tests/**")
        }
    }
}
```

### 4.5 启用 KSP 替代 KAPT

```kotlin
// build.gradle.kts (root)
plugins {
    id("com.google.devtools.ksp") version "2.1.0-1.0.29" apply false
}

// SystemUI-core/build.gradle.kts
plugins {
    id("com.google.devtools.ksp")
}

dependencies {
    ksp(libs.dagger.compiler)
}
```

### 预期错误数变化

- 目标: 1850 → 500 (减少约 1350 个错误)

---

## 阶段 5: 最终验证 ⏳

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

### 5.4 安装到设备

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
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
| Kotlin 2.2.10 + AGP 9 不识别某些 Flags | unresolved | 提取相关接口 |

---

## 提交策略

每个阶段建议对应一个 commit：

1. ✅ `docs: add AGENTS.md with rules and progress`
2. ✅ `refactor: 遵循参考项目 (CarSystemUIGradle) 引入依赖方式 - 删除所有 stub`
3. ✅ `feat(SystemUI-core): 完整合并 framework.jar 到 SysUISdk/android.jar`
4. ⏳ `feat(deps): resolve server-notification-flags.jar ...`
5. ⏳ `feat(scene): integrate Compose Scene Framework AAR`
6. ⏳ `feat(deps): upgrade Compose to 1.8.x for internal APIs`
7. ⏳ `chore(deps): migrate from KAPT to KSP`
8. ⏳ `fix: exclude test code from main source set`
9. ⏳ `feat: complete SystemUI Gradle build pipeline`

---

## 开发时间估算

| 阶段 | 状态 | 预估时间 | 已用 |
|------|------|---------|------|
| 阶段 1 | ✅ | 0.5h | 0.5h |
| 阶段 2 | 🚧 | 2-4h | 4h (阻塞) |
| 阶段 3 | ⏳ | 4-8h | 0 |
| 阶段 4 | ⏳ | 2-4h | 0 |
| 阶段 5 | ⏳ | 1-2h | 0 |

总计：预估 9.5-18.5h，已用 ~4.5h

---

## 参考资源

- [AGENTS.md](../AGENTS.md) - 项目规则与进度
- [docs/HANDOFF.md](./HANDOFF.md) - ⭐ 下个 AI 入口
- [docs/CURRENT_STATE.md](./CURRENT_STATE.md) - 当前状态快照
- [docs/PITFALLS.md](./PITFALLS.md) - 踩坑记录
- [docs/GRADLE_MIGRATION_LOG.md](./GRADLE_MIGRATION_LOG.md) - 历史错误数演变
- [CarSystemUIGradle](../CarSystemUIGradle) - 参考实现 (同用户私有项目)
- [tools/gen_aar_maven.py](../tools/gen_aar_maven.py) - AAR 生成脚本