# SystemUI-Gradle 详细开发计划 (PLAN.md)

> ⚠️ **历史计划警告（2026-08-06）**：本文件 §阶段 1–5 主体停留在 2026-07-29，旧的错误数目标、“把 SystemUIApplication/SystemUIService 移到 app”计划、以及“animationlib 源码化”方案均已失效。入口类必须保留在 `:SystemUI-core`（见 ADR 0003 更正）；animationlib 是非 SystemUI 代码，须改为直接 AAR。
>
> **当前优先级（Phase A 完成后）**：`docs/superpowers/plans/2026-08-07-post-topology-correctness.md` 的 Task 1–6 已执行完毕。common/compose/plugin 三个 classpath blocker 已清除（均编译通过），但 core 首次失败暴露两个新 blocker：**B1** `:SystemUI-res:packageDebugResources` 因 AOSP `res-product` 的 `product="..."` 资源变体不被 AAPT2 支持（需规则 H）；**B2** `:SystemUI-plugin:compileDebugJavaWithJavac` processor 运行时缺 kotlin stdlib。core 自身 Kotlin 编译尚未开始。需用户对 B1（资源 owner/构建机制）和 B2 是否在本阶段修复决策后，再校准 `docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md`。错误数始终只作诊断，不作为提交门槛。下文历史阶段保留供参考，不代表当前优先级。

> **历史最后更新**: 2026-07-29
> **历史错误数**: 509
> **最终目标**: 0 → 可编译
> **历史阶段**: Stage 3/4 推进中（animationlib 源码化 + app 模块构建）

---

## 阶段总览

```
阶段 1 ✅ (2026-07-22): 文档 + 阶段性 commit
阶段 2 ✅ (2026-07-28): server-notification-flags.jar — 已解决（删除 stub Flags.kt）
阶段 2.5 ✅ (2026-07-28): R 歧义 + jar 补齐 + 源码补齐 — 5296→509（历史，非当前基线）
阶段 3 ✅/⚠️ (2026-08-08 checkpoint): 13-module 拓扑与 owner 迁移完成；编译/processor 验收部分完成
阶段 3.5 ✅ (Phase A): post-topology correctness 完成（工具确定性 + Common/Compose/Plugin classpath 全通过）
阶段 3.6 🚧 (blocker): res product-variant (B1 需规则 H) + processor kotlin stdlib (B2)
阶段 4 ⏳ (已规划): AAR artifact 恢复 + 重复 R/源码-prebuilt 重复类修复（`docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md`）
阶段 5 ⏳ (待启动): manifest merge + Kotlin 基线 + :app:assembleDebug
```

> 旧的“阶段 3: animationlib 源码化”已废止——animationlib 属非 SystemUI 代码，改为直接 AAR。

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

## 阶段 2: server-notification-flags.jar 解析问题 ✅ 已解决 (2026-07-28)

### 问题

- 错误: `Unresolved reference 'screenshareNotificationHiding'` × 13 + `FlagDependencies.kt` 6 个

### 根因

源码 stub `SystemUI-core/src/com/android/server/notification/Flags.kt`（`object Flags`）
遮蔽了 jar 里的真实 `Flags` 类。全项目编译时 Kotlin 优先用源码定义，stub 没有
`screenshareNotificationHiding()` 且把 flag 声明为 `val` 而非方法 → 13+6 个 unresolved。

### 修复

`git rm` 该 stub。2000 → 1979。

### 教训

之前几轮围绕 classpath/Kotlin 版本/FeatureFlags 的排查全部走偏。详见：
- `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`
- `docs/issues/2026-07-28-server-flags-debug-session.md`

---

## 阶段 2.5: jar 补齐 + 源码补齐 ✅ 已完成 (2026-07-28)

### 操作

- R 歧义修复（7 文件，1979→1879）
- 补齐 androidx.datastore 依赖（1879→1806）
- customization res 补齐 + 关闭 nonTransitiveRClass（1806→1759）
- 引入 systemui-aidl.jar（1759→1658）
- customization prebuilt jar 改 api 暴露给 core（1658→1491）
- 补齐完整 SettingsLib jar（1491→1039）
- 补齐 nano proto 生成类 jar（1039→938）
- 补齐 SystemUILogLib jar（938→885）
- 补齐 SystemUIUnfoldLib jar + androidx.window（885→844）
- 补齐 lottie/lottie_compose jar（844→809）
- 补齐 PlatformComposeCore 源码 + compose androidx 依赖（809→741）
- 补齐 compose/core 顶层组件文件（741→724）
- 补齐 compose/features+biometric+animation 源码 + res.R→R 规范化（724→509）

---

## 阶段 3: 13-module 拓扑与 owner 迁移 ✅/⚠️ checkpoint

已完成：

1. settings 收敛为目标 13 module；
2. `:app` 为空壳且只直接依赖 `:SystemUI-core`；
3. 入口类保留在 core；
4. SystemUI src/AIDL/res 归位到唯一 owner；
5. animationlib 改为 `libs/aars/animationlib.aar` 直接 AAR；
6. compilelib 改为 debug/release JAR；
7. pods、Compose Scene、Shader、shared-keyguard 等内部切片合并到真实 seam。

尚未完成：

1. Common/Compose/Plugin 的确定 classpath 修复；
2. PluginProtector 的 Kotlin annotation processing；
3. 四个大型 AOSP AAR 的 artifact recovery；
4. core、manifest merge 与 APK 验收。

准确结论与执行步骤见：

- `docs/issues/2026-08-07-post-topology-review.md`
- `docs/superpowers/plans/2026-08-07-post-topology-correctness.md`

**app/core 决策保持不变**：入口类必须位于 `:SystemUI-core/src/com/android/systemui/`，`:app` 无源码；禁止再次迁移入口类。

---

## 阶段 4: Compose Scene Framework + 业务模块错误 ⏳

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