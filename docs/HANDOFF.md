# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 阅读顺序: 本文件 → `AGENTS.md` → `docs/CURRENT_STATE.md` → `docs/PLAN.md` → `docs/PITFALLS.md` → `docs/architecture/` → `docs/issues/`

本文档为新 AI Agent 提供 "5 分钟上手纲要"，详细规则请阅读后续文件。

---

## 0. 这是什么项目

将 AOSP SystemUI 移植到独立 Gradle 编译体系。**目标**：能在用户本地 (Linux) 用 AGP 9.x + Gradle 9.x 编译 SystemUI 源码，错误数从 2000 → 0。

参考实现是用户私有项目 `CarSystemUIGradle`（在同一目录下）。

---

## 1. 5 分钟上线检查清单

### 1.1 确认环境
```bash
# AOSP 源码
ls /home/conv/myspace/aosp/                    # 必须存在
# Android SDK
ls /home/conv/Android/Sdk/platforms/           # 必须有 android-SysUISdk
# 编译入口
cd /home/conv/myspace/SystemUI-Gradle
./gradlew --version                            # Gradle 9.5
```

### 1.2 跑一次基线编译，统计错误数
```bash
./gradlew :SystemUI-core:compileDebugKotlin --console=plain 2>&1 | tee /tmp/build.log
echo "Total errors: $(grep -c '^e: file:' /tmp/build.log)"
echo "screenshareNotificationHiding: $(grep -c 'screenshareNotificationHiding' /tmp/build.log)"
```

**当前基线（2026-07-28）**: 1979 错误（Stage 2 已解决，见 §4.1）。其中：
- ~~server-notification Flags~~: ✅ 已清零（删除 stub `Flags.kt`）
- Compose Scene Framework (`com.android.compose.animation.scene.*`): 12 个
- Compose Theme (`AndroidColorScheme.kt` R 冲突): 60 个
- 其他业务模块: 剩余 ~1907 个

### 1.3 必须遵守的规则（优先级从高到低）

1. **用户指令 > 本文件 > 默认系统提示**
2. **不要创建 stub 类**（详细规则见 AGENTS.md §1）
3. **不要擅自创建资源文件**（res/ 下的任何东西必须来自 AOSP 源码 / aar / maven）
4. **增量开发**：每次 commit 错误数必须下降
5. **所有改动先写文档** (`docs/issues/YYYY-MM-DD-<topic>.md`)
6. **不要替用户做产品决策**：遇到 2+ 候选方案时用 `AskQuestion` 询问

---

## 2. 项目结构速查

```
SystemUI-Gradle/
├── AGENTS.md                  # ⭐ 项目规则（必读）
├── docs/
│   ├── HANDOFF.md             # ⭐ 本文件（新 AI 入口）
│   ├── CURRENT_STATE.md       # ⭐ 当前状态快照
│   ├── PLAN.md                # 阶段计划
│   ├── PITFALLS.md            # ⚠️ 踩坑记录
│   ├── GRADLE_MIGRATION_LOG.md # 历史错误数演变
│   ├── issues/               # 每日问题记录
│   └── architecture/         # 架构/调研文档
├── libs/                     # 自包含依赖（不入 gitignore）
│   ├── framework.jar         # AOSP 框架（含 @hide API）
│   ├── framework-statsd.jar
│   ├── android.car.jar
│   ├── WindowManager-Shell.jar
│   ├── android_module_lib_stubs_current.jar
│   ├── SystemUI-{proto,tags,statsd}.jar
│   ├── monet.jar            # ColorScheme/Shades/Style
│   ├── systemui-flags.jar   # com.android.systemui.Flags
│   ├── maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar
│   ├── prebuilts/
│   │   ├── SystemUISharedLib.jar
│   │   ├── SystemUIPluginLib.jar
│   │   ├── SystemUICustomizationLib.jar
│   │   ├── PlatformAnimationLib.jar
│   │   └── tracinglib-platform.jar
│   └── maven/com/android/systemui/{settingslib,iconloader,WindowManager-Shell,WifiTrackerLib,SystemUISharedLib}/1.0.0/
├── SystemUI-core/            # 主模块 ~95% 代码
│   ├── src/                  # = AOSP frameworks/base/packages/SystemUI/src/
│   ├── res/                  # = AOSP SystemUI/res/
│   ├── res-keyguard/         # = AOSP SystemUI/res-keyguard/
│   ├── res-product/          # = AOSP SystemUI/res-product/
│   ├── build.gradle.kts
│   └── AndroidManifest.xml
├── SystemUI-{shared,animation,customization,plugin,plugin-core}/
├── app/                      # 主入口
├── build.gradle.kts          # 根项目（allprojects 注入 framework.jar）
├── settings.gradle.kts
└── gradle/libs.versions.toml
```

---

## 3. 调试模式与工具链

| 工具 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.2.0 | alias `libs.plugins.android.library` |
| Kotlin Plugin | 2.1.0（项目）/ 2.2.10（AGP 内部嵌入） | 关键：**AGP 嵌入的 kotlin-compiler-embeddable 比插件新** |
| KAPT | 1.9+ 临时禁用 | 1.9+ 与 Gradle 9.5 报 "IR 内部错误" |
| 目标 JVM | 21 | Java/Kotlin 编译都用 21 |
| 目标 SDK | `SysUISdk`（自定义 preview） | 路径 `/home/conv/Android/Sdk/platforms/android-SysUISdk/` |

---

## 4. 我（当前 AI）留下未完成的事

### 4.1 Stage 2 (server-notification-flags.jar)
- **状态**: ✅ **已解决 (2026-07-28)**。根因是源码 stub `com/android/server/notification/Flags.kt`
  遮蔽了 jar，`git rm` 后 2000 → 1979。**不是** classpath/Kotlin 2.2.10/FeatureFlags 的问题。
- **详情**: `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`、`docs/PITFALLS.md §2.4`

### 4.2 Stage 3 (Compose Scene Framework)
- **状态**: 12 个错误，全部在 `com.android.compose.animation.scene.*`
- **错误种类**: `thenIf`, `drawInContainer`, Modifier 内部 API, `ContainerState`
- **下次 Agent 行动**: 详查 `docs/CURRENT_STATE.md` §3

### 4.3 Stage 4 (业务模块错误)
- **状态**: ~1909 个错误分散在 ~80 个包
- **下次 Agent 行动**: 用 `docs/PITFALLS.md` 中的分类模板分析

---

## 5. 我的工作偏好

- 用户用中文交流
- 用户喜欢看代码改动总结
- 用户要求及时记录问题 (2026-07-23 提醒)
- 用户要求先做 plan 再开发 (2026-07-23 提醒)
- 用户希望增量提交，每个 commit 都有意义
- 用户希望参考 `CarSystemUIGradle` 项目的做法
- **用户要求给下一个 AI 留完整交接文档** (2026-07-28 提醒)

---

## 6. 紧急联系信息（重要）

如遇到下面情况，**停止**并询问用户：

1. 必须创建 stub 类（违反规则 P）
2. 必须修改 res/ 下的资源文件
3. 错误数大幅上升（>200）而非下降
4. 需要产品决策（多个等价方案）
5. 需要修改 AGENTS.md 的核心规则

---

**下一步**: 阅读 `AGENTS.md` 完整规则。
