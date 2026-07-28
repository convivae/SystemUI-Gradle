# SystemUI-Gradle 当前状态快照 (CURRENT_STATE.md)

> **最后更新**: 2026-07-28
> **当前错误数**: 1979
> **当前阶段**: Stage 2 (server-notification-flags.jar) **已解决** → 转 Stage 3 (Compose)

> ⚠️ **Stage 2 根因更正 (2026-07-28)**: 阻塞**不是** classpath/Kotlin 2.2.10/缺 FeatureFlags，
> 而是源码 stub `com/android/server/notification/Flags.kt` 遮蔽了 jar。已 `git rm`，2000 → 1979。
> 详见 `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`。

---

## 1. 工具链版本

| 工具 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.2.0 | `libs.plugins.android.library` |
| Kotlin Plugin | 2.1.0 | 项目声明 |
| Kotlin 编译器 | 2.2.10 | AGP 内部嵌入（比插件新） |
| KAPT | 1.9+ | 临时禁用（IR 错误） |
| JDK | 21 | 工具链 |
| AGP target SDK | `SysUISdk` | preview, 非标准 |

---

## 2. 错误数演变

| 日期 | 错误数 | 关键改动 |
|------|--------|----------|
| 2026-07-22 初 | 5296 | 仅有 sdk android.jar |
| 2026-07-22 | 4675 | 替换 framework.jar (AOSP 完整版) |
| 2026-07-22 | 3008 | 合并 SDK android.jar + framework.jar |
| 2026-07-22 | 2412 | 删除所有 v1 stub (~60 个) |
| 2026-07-22 | 2000 | 加 Monet + SystemUI Flags jar |
| 2026-07-23 | 2000 | Stage 2 启动，暂无突破 |
| 2026-07-28 | 2000 | 调试 session，未减少 |
| 2026-07-28 | **1979** | **删除遮蔽 jar 的 stub `server/notification/Flags.kt`（Stage 2 解决）** |

**目标**: 0 (完整编译通过)

---

## 3. 错误分布（2000 错误按包分类）

### 3.1 顶级错误包（前 25）

| 错误数 | 目录 |
|--------|------|
| 81 | systemui/volume/domain/interactor |
| 79 | systemui/bluetooth/qsdialog |
| 60 | compose/theme |
| 57 | systemui/scene |
| 57 | systemui/communal/widgets |
| 56 | systemui/volume/panel/component/mediaoutput/domain/interactor |
| 51 | systemui/keyguard/ui/preview |
| 51 | systemui/education/data/repository |
| 48 | systemui/volume/dialog/sliders/ui |
| 46 | systemui/communal/data/repository |
| 45 | systemui/keyguard/ui/view/layout/sections |
| 43 | systemui/volume/dagger |
| 43 | systemui/scene/ui/view |
| 40 | systemui/keyguard/ui/viewmodel |
| 39 | systemui/inputdevice/tutorial |
| 38 | systemui/qs/panels/ui/compose/infinitegrid |
| 29 | systemui/inputdevice/tutorial/ui/composable |
| 28 | systemui/volume/panel/component/volume/slider/ui/viewmodel |
| 28 | systemui/keyguard/data/repository |
| 27 | systemui/statusbar/policy/domain/interactor |
| 25 | systemui/user/ui/dialog |
| 23 | systemui/unfold |
| 23 | systemui/communal/shared/log |
| 22 | systemui/volume |
| 22 | systemui/inputdevice/tutorial/data/repository |

### 3.2 Stage 2 关键错误（13 个 + 6 个）

| 错误 | 文件 | 行 |
|------|------|-----|
| Unresolved 'screenshareNotificationHiding' | SensitiveContentCoordinator.kt | 25, 98, 108, 115, 178, 211, 217 |
| Unresolved 'screenshareNotificationHiding' | StackCoordinator.kt | 20, 71 |
| Unresolved 'screenshareNotificationHiding' | NotifUiAdjustmentProvider.kt | 25, 73, 92, 145 |
| Argument type mismatch + Unresolved 'politeNotifications' | FlagDependencies.kt | 79 |
| Argument type mismatch + Unresolved 'crossAppPoliteNotifications' | FlagDependencies.kt | 82 |
| Argument type mismatch + Unresolved 'vibrateWhileUnlocked' | FlagDependencies.kt | 85 |

### 3.3 Stage 3 Compose 错误（72 个）

| 错误数 | 子区域 |
|--------|--------|
| 60 | `com.android.compose.theme.AndroidColorScheme.kt` R 冲突 |
| 12 | `com.android.compose.animation.scene.*` 内部 API |

具体缺失符号：
- `thenIf` (Modifier extension)
- `drawInContainer` (DrawModifier)
- `ContainerState` (Scene 内部)
- `modifiers.*`, `graphics.*` (Qualified access 失败)

### 3.4 其他（剩余 ~1909）

分散在 80+ 包。错误种类混合：
- Dagger `@Inject` 找不到 (无 KSP 生成)
- 业务类未引用
- 第三方库 API 漂移

---

## 4. 已知问题与决策点

### 4.0 ✅ [已解决 2026-07-28] Stage 2 server-notification-flags

**根因**: 源码 stub `SystemUI-core/src/com/android/server/notification/Flags.kt`（`object Flags`）
遮蔽了 jar 里的真实 `Flags` 类。全项目编译时 Kotlin 优先用源码定义，stub 没有
`screenshareNotificationHiding()` 且把 flag 声明为 `val` 而非方法 → 13+6 个 unresolved。

**修复**: `git rm` 该 stub。2000 → 1979。前面几轮围绕 classpath/Kotlin 版本/FeatureFlags 的
排查全部走偏（详见 `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`）。

> 下方 4.1/4.2 记录的是历史怀疑点，**已被证伪**，保留供教训参考。

### 4.1 ⚠️ [已证伪] `libs/server-notification-flags.jar` 是空 jar

```bash
$ unzip -l libs/server-notification-flags.jar
# 完全空!
```

正确 jar 在 `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`（6285 字节，含 `Flags.class`）。

**根因**: `gradle/libs.versions.toml` 已定义 `android-server-notification-flags`，但 `SystemUI-core/build.gradle.kts` 和 `build.gradle.kts` 中没显式使用它。`build.gradle.kts` 里通过 `libraries.from(serverNotificationFlagsJar)` 注入到 KotlinCompile classpath。

**行动**: 已在 `SystemUI-core/build.gradle.kts` 加 `implementation(libs.android.server.notification.flags)`，但仍报错。详见 `docs/issues/2026-07-28-server-flags-debug-session.md`。

### 4.2 🚨 AGP 9.2 嵌入 Kotlin 2.2.10，但项目声明 2.1.0

- 项目 plugins: `kotlin("android") version 2.1.0`
- AGP 9.2 内部使用 `kotlin-compiler-embeddable 2.2.10`
- 行为：编译时用 2.2.10
- 影响：对 jar 内 `@UnsupportedAppUsage` 等注解的解析更严格

**这是 stage 2 阻塞的核心怀疑点**。详见 `docs/architecture/STAGE2-3-RESEARCH-LOG.md`。

### 4.3 KAPT 已禁用

```kotlin
// SystemUI-core/build.gradle.kts 第 4 行
// id("kotlin-kapt") // 临时禁用：KAPT 1.9+ 与 Gradle 9.5 不兼容（IR 内部错误）
```

**后果**: Dagger 不会生成代码，所有 `@Inject` 注入失败。

**候选解**:
- 改 KSP（`com.google.devtools.ksp` 1.9+）
- 降级 AGP 到 8.x
- 退而要求 Dagger 显式 Provider

### 4.4 未跟踪源码（可能不参与编译）

`git status` 显示以下文件是 `??`（未跟踪）：

```
SystemUI-core/src/com/android/compose/animation/scene/* (47 个)
SystemUI-core/src/com/android/compose/nestedscroll/* (2 个)
SystemUI-core/src/com/android/compose/ui/util/* (3 个)
SystemUI-core/src/com/android/compose/theme/AndroidColorScheme.kt (1 个)
SystemUI-plugin-core/src/main/java/.../* (移动过)
SystemUI-plugin/src/main/java/.../* (移动过)
```

**重要**: 这些文件**不在编译路径**（git status 证明它们是新增但未提交）。`SystemUI-core/build.gradle.kts` 通过 `java.srcDir("src")` 包含 `src/` 下所有 .kt/.java，所以它们**会被编译**。

---

## 5. 已尝试的方案（保留供下个 AI 参考）

### 5.1 server-notification-flags

| 方案 | 结果 | 详情 |
|------|------|------|
| `compileOnly(files("libs/server-notification-flags.jar"))` | 失败 | 空 jar |
| `implementation(files("libs/server-notification-flags.jar"))` | 失败 | 空 jar |
| `api(files("libs/server-notification-flags.jar"))` | 失败 | 空 jar |
| `implementation(libs.android.server.notification.flags)` | 失败 | 在 classpath 但仍报错 |
| `implementation(libs.android.server.notification.flags)` + `libraries.from` 双注入 | 失败 | 错误数不变 |
| `allprojects` `libraries.from()` 注入 | 失败 | 注入已生效，但 Kotlin 仍 Unresolved |
| 提供 `AconfigFlagAccessor` 注解类 | 失败 | jar 已有 |
| 提供 `UnsupportedAppUsage` 注解类 | 失败 | jar 已有 |
| 提供 `FeatureFlags` 接口 | N/A | jar 引用 `com.android.server.notification.FeatureFlags` |
| 升级 Kotlin 到 2.2.10 | 失败 | plugin 冲突 |
| 独立 kotlin("jvm") 2.1.0 项目测试 | 成功 | 同样的 jar 能编译 |

### 5.2 Compose Scene Framework

| 方案 | 状态 |
|------|------|
| 加 androidx.compose 1.8.0 | 未尝试 |
| 提取 AOSP Scene AAR | 未尝试 |
| 复制源码为独立 module | 未尝试 |
| 排除源码（暂时禁用） | 未尝试 |

### 5.3 Compose Theme R 冲突

| 方案 | 状态 |
|------|------|
| alias import | 理论可行未尝试 |
| 限定 R 类 | 理论可行未尝试 |
| 排除 AndroidColorScheme.kt | 理论可行未尝试 |

---

## 6. 下一个 AI 的 5 个优先行动

### 优先级 1: Stage 2 server-notification-flags
- 详读 `docs/issues/2026-07-28-server-flags-debug-session.md`
- 尝试用 K2JVMCompiler 手动调用绕过 AGP，看是否问题在 AGP 层
- 尝试让 Kotlin 编译器日志输出（`-Xverbose` / `-Xlog-level=DEBUG`）
- 尝试提取 server.notification.FeatureFlags 接口类

### 优先级 2: KAPT 替代方案
- 决定走 KSP 还是降级 AGP
- 这是进一步降低错误数的前置

### 优先级 3: Compose Scene Framework
- 找到 `thenIf`, `drawInContainer` 等内部 API 来源
- 决策：提取 AAR vs 排除源码

### 优先级 4: Compose Theme R 冲突
- 加 alias import

### 优先级 5: 业务模块错误
- 用 `Pitfalls.md` 模板化分类，逐个击破

---

## 7. 验证清单

每次 commit 前确认：

- [ ] 错误数下降
- [ ] docs/GRADLE_MIGRATION_LOG.md 写入新行
- [ ] docs/issues/YYYY-MM-DD-*.md 更新
- [ ] 没引入新 stub
- [ ] 没改 res/ 资源
- [ ] build.gradle.kts 只在 dependencies 块改

---

## 8. 快速命令

```bash
# 一键状态报告
./gradlew :SystemUI-core:compileDebugKotlin --console=plain 2>&1 | tee /tmp/build.log | tail -5
echo "Errors: $(grep -c '^e: file:' /tmp/build.log)"
echo "screenshareNotificationHiding: $(grep -c 'screenshareNotificationHiding' /tmp/build.log)"
echo "FlagDependencies: $(grep -c 'FlagDependencies.kt' /tmp/build.log)"

# 哪个包错误最多
grep "^e: file:" /tmp/build.log | sed -E 's|.*/SystemUI-Gradle/SystemUI-core/src/com/android/||; s|/[^/]+\.kt.*||' | sort | uniq -c | sort -rn | head -10
```
