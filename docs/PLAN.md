# SystemUI-Gradle 详细开发计划 (PLAN.md)

> ⚠️ **历史计划警告（2026-08-06）**：本文件主体停留在 2026-07-29，旧的错误数目标和“把 SystemUIApplication/SystemUIService 移到 app”计划已失效。入口类必须保留在 `:SystemUI-core`（见 ADR 0003 更正）。
>
> 当前优先级以 `AGENTS.md`、`docs/architecture/2026-08-06-reference-project-rationale.md` 和 `docs/architecture/2026-08-06-soong-android-app-vs-gradle-app.md` 为准：先完成源码 1:1 审查、非 SystemUI 违规源码清理、无用/违规/旧 jar/AAR 清理和依赖边界校准；AAR 先直接引入，确认冲突后才使用本地 Maven。错误数始终只作诊断，不作为提交门槛；编译按问题和阶段性里程碑需要执行，不要求每次修改都运行。

> **历史最后更新**: 2026-07-29
> **历史错误数**: 509
> **最终目标**: 0 → 可编译
> **历史阶段**: Stage 3/4 推进中（animationlib 源码化 + app 模块构建）

---

## 阶段总览

```
阶段 1 ✅ (2026-07-22): 文档 + 阶段性 commit
阶段 2 ✅ (2026-07-28): server-notification-flags.jar — 已解决（删除 stub Flags.kt）
阶段 2.5 ✅ (2026-07-28): R 歧义 + jar 补齐 + 源码补齐 — 5296→509
阶段 3 🚧 (2026-07-29): animationlib 源码化 + app 模块构建
阶段 4 ⏳ (待启动): Compose Scene Framework + 业务模块错误
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

## 阶段 3: animationlib 源码化 + app 模块按 bp 重构 🚧 进行中

### 3.1 animationlib 源码化

根据规则 S，`animationlib` 属于 ① SystemUI 自有代码，应源码复制做源码依赖。

**已完成的操作**：
1. 从 AOSP 复制 4 个 Java 源文件 + 4 个 res 资源文件到 `SystemUI-animationlib/`
2. 创建 `SystemUI-animationlib/build.gradle.kts`（library 模块）
3. `settings.gradle.kts` 添加 `include(":SystemUI-animationlib")`

**待完成**：
1. `:SystemUI-animation` / `:SystemUI-customization` 的 `compileOnly(animationlib.jar)` → `api(project(":SystemUI-animationlib"))`
2. 删除 `libs/animationlib.jar`
3. 检查 WMShell.jar 的 6 个重叠类是否冲突
4. 编译验证

**详情**: `docs/issues/2026-07-29-aidl-animationlib-app.md §三`

### 3.2 app 模块按 AOSP `Android.bp` 重构 (ADR 0003) ✅ 结构已更正

按规则 B（详见 `docs/adr/0003-app-module-aligns-aosp-bp.md`），项目结构必须对齐 AOSP bp。

**2026-07-31 更正**：旧计划误以为 `SystemUIApplication.java` / `SystemUIService.java` 属于 `android_app` 源码。实际：

- `android_library "SystemUI-core"` 的 `srcs: ["src/**/*.java", ...]` **包含**这两个入口类
- `android_app "SystemUI"` 无独立 `srcs`，只 `static_libs: ["SystemUI-core"]`
- 因此入口类必须保留在 `:SystemUI-core/src/com/android/systemui/`，`:app` 无源码

**正确结构**：

1. `:app` 的 project module 依赖只保留 `implementation(project(":SystemUI-core"))`；当前额外 compileOnly/上游 implementation 需继续审查是否应由 core 传递
2. `:app/src/main/AndroidManifest.xml` 使用 AOSP 完整 manifest
3. `:app` 持有最终 APK 的 proguard 配置；`AndroidManifest-res.xml` 实际属于 AOSP `SystemUI-res`，当前 app 中未被消费的副本应在建立 `:SystemUI-res` module 时归位
4. `:SystemUI-core` 持有入口类和 AOSP SystemUI 源码/资源
5. 禁止再次把入口类迁到 `:app/src/main/java/`

**详情**: `docs/adr/0003-app-module-aligns-aosp-bp.md`

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