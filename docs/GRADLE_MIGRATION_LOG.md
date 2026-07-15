# SystemUI Gradle Build System Migration Log

> **Status reset (2026-07-16):** The previous offline-Maven attempt is
> being abandoned in favour of the v2 design described in
> `docs/superpowers/specs/2026-07-16-systemui-gradle-conversion-v2-design.md`.
> Numbering in the `## 问题 N` section restarts from 1; the legacy
> `Remaining Issues` blocks above remain as historical context only.

## 问题 1：废弃 v1 离线策略，全面切换到 v2 设计

### 问题描述

v1 阶段（2026-04 至 2026-07-15）按"完全离线 + 拷贝 AOSP 源码 + 本地 stubs"
方向实施，累计 ~5000 → 898 个 Kotlin 编译错误仍在清理中，且与
用户最终确定的新策略矛盾。新策略（v2 spec）要求：

1. 从零开始重写，源码从 AOSP 拷贝改造
2. 第三方依赖（AndroidX/Compose/Kotlinx/Dagger/…）走 Gradle 联网解析
3. 首阶段交付物是 **可构建的双编译骨架**，再迭代填功能
4. 使用 AOSP 真实编译的 `framework.jar`，不用 platform stubs

继续在 v1 基础上修补会导致每次添加新模块都要重新跟 offline Maven
仓库和 platform stubs 体系纠缠，路径已不可行。

### 问题分析

- `libs/` (693MB) 里的 prebuilt JARs 大多源自 v1 离线策略下的
  `tools/extract_aosp_libs.sh` 与 `scripts/build_offline_maven.py`，
  v2 不需要。
- `scripts/build_offline_maven.py` / `extract_aosp_libs.sh` 是 v1
  离线 Maven 仓库的搭建脚本，v2 联网策略下作废。
- `animation/ common/ customization/ log/ plugin/ plugin-core/ shared/
  unfold/ utils/` 9 个 module 目录里的 build.gradle.kts 与
  `sourceSets` 都是按 v1 思路拼凑的，与 v2 的模块拆分不一致。
- 根目录 `build.gradle.kts / settings.gradle.kts / gradle.properties`
  在 v2 里要全部重写（AGP 9 + Gradle 9 + libs.versions.toml 路径不同）。
- `docs/superpowers/{specs,plans}/2026-04-30-systemui-...md` 是 v1
  文档，v2 spec 已 supersede。

### 解决方案

按用户确认的范围清理仓库，但保留：(a) `app/` 里的现有 AOSP 拷贝源码
（后续工作基础），(b) `docs/GRADLE_MIGRATION_LOG.md` 本文件（spec §11
要求），(c) `docs/superpowers/specs/2026-07-16-...md`（v2 spec），
(d) Gradle wrapper (`gradle/`, `gradlew*`)，(e) `.gitignore / .idea /
.gradle`（构建 / IDE 需要）。

执行的删除：

```bash
rm -rf animation common customization log plugin plugin-core \
       shared unfold utils libs scripts build
rm -f build.gradle.kts settings.gradle.kts gradle.properties
rm -f docs/superpowers/specs/2026-04-30-systemui-gradle-conversion-design.md
rm -f docs/superpowers/plans/2026-04-30-systemui-gradle-conversion.md
```

`app/src/main/res-keyguard/` 暂保留——它包含独立的 keyguard 资源
文件（arrays/attrs/bools/colors/...），可能对 v2 的 keyguard 模块
有用，由后续 task 评估是否纳入源码或丢弃。

### 修改文件
- 删除 9 个 module 目录 + libs/ + scripts/ + 3 个根目录 build 文件 +
  build/ + 2 个 v1 文档。

### 状态
✅ 已解决（仓库已重置为 v2 起点）。

### 下一步
1. 按 `writing-plans` skill 写出 v2 实施计划。
2. Task 1: 创建 libs.versions.toml + 根 build.gradle.kts + settings.gradle.kts。
3. Task 2: 提取 `framework.jar` 到 `libs/` + 创建自定义 SDK Platform
   脚本（如果还没有 SysUISdk）。
4. Task 3: 编写最小 `:app` 模块，跑通 `./gradlew :app:assembleDebug`。

---

## 附录 A：v1 历史（已废弃，仅供参考）

> 以下内容来自 2026-04 至 2026-07-15 的 v1 离线-Maven 尝试，已被
> 问题 1 的清理工作替换。仅作为已尝试方案与技术决策的归档，新工作
> 不再继承其中的命名（`com.android.systemui.res` / `框架 73MB 合并` /
> `nonTransitiveRClass=false` 等）。

### A.1 v1 当前状态（截至 2026-07-15）
- **Kotlin 编译错误数**：898（自初始 ~5000 下降）
- **资源处理**：通过
- **从源码编译的 module**：app, plugin-core, common, utils, log
- **使用 prebuilt JAR 的 module**：shared, unfold, customization, animation, plugin

### A.2 v1 主要里程碑

#### A.2.1 自定义 SDK Platform (SysUISdk)
- 创建于 `$ANDROID_HOME/platforms/android-SysUISdk/`
- 合并的 android.jar（SDK + framework.jar），含 hidden platform APIs
- 所有 Android module 使用 `compileSdkPreview = "SysUISdk"`
- 73MB 合并 jar 提供对 platform internals 的访问

#### A.2.2 资源系统
- 从 AOSP 恢复所有 value 资源文件（strings/colors/dimens/styles/attrs 等）
- 修复重复的 product-specific string 资源
- 把 `androidprv:`（platform-private）替换为 `android:` 或本地定义
- 把 `materialColor*` attrs 替换为 Material Components library 等价属性
- 增加 `res-keyguard` 资源用于 bouncer/keyguard
- App namespace 设为 `com.android.systemui.res` 以匹配 AOSP R 类引用

#### A.2.3 模块结构
- 从 10 个源 module 简化到 5 个活跃 module
- 复杂 module（shared、unfold 等）使用 AOSP soong 输出的 prebuilt JAR
- Prebuilt JARs：`libs/` 目录下 44 个文件

#### A.2.4 关键技术决策
- 用 `gradle.projectsEvaluated` 把 framework.jar 放在 classpath 最前面
- 用 `kotlin.srcDirs("src")` 触发 AGP 9.x Kotlin 文件检测
- 用 `android.nonTransitiveRClass=false` 开启 transitive 资源访问
- 对 Maven 不存在的依赖（lottie、slice）使用本地 JAR

### A.3 v1 未解决问题（898 errors 分类）

#### A.3.1 Settings Proxy（~200 errors）
- `SecureSettings`, `GlobalSettings`, `SystemSettings` — 由 AOSP 生成
- `SettingsProxyExt`, `UserSettingsProxy` — 生成
- 函数：`getIntForUser`, `getStringForUser`, `observerFlow` 等
- **当时方案**：创建 Settings proxy stubs 或从 AOSP 生成输出拷贝

#### A.3.2 资源引用（~100 errors）
- `kg_*` string 资源 — keyguard 字符串
- `bouncer_*` dimen 资源 — bouncer 尺寸
- `below_clock_*` dimen 资源 — 时钟布局
- `sharedR`, `customR` — 跨 module R 引用
- **当时方案**：补缺失的 string/dimen/style 定义

#### A.3.3 Flag Stubs（~20 errors）
- `Flags`, `NAMESPACE_SYSTEMUI` — aconfig 生成
- **当时方案**：创建 flag stub 类

#### A.3.4 平台 Hidden APIs（~50 errors）
- `StatsManager`, `StatsEvent`, `TrafficStateCallback`
- `SafetyCenterManager`, `DeviceConfig`
- `BluetoothLeBroadcast*`, `VcnTransportInfo`
- **当时方案**：已在合并 android.jar 里，可能需要 compileOnly 依赖

#### A.3.5 Dagger 生成（~5 errors）
- `DaggerReferenceGlobalRootComponent` — Dagger 生成
- **当时方案**：运行 Dagger 注解处理器

#### A.3.6 其他（~20 errors）
- `res` 扩展函数 — 来自 SystemUI-common module
- `NeverCompile`, `UsesReflection` — 编译器注解
- Protobuf nano 类
