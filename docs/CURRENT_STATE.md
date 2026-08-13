# SystemUI-Gradle 当前状态快照 (CURRENT_STATE.md)

> **当前阶段（2026-08-13 javac 里程碑）**：**Task 7 八组 javac 根因全部修复（最后一块：补 SysUISdk dalvik annotations，`a35906f4`）；`:SystemUI-core:compileDebugJavaWithJavac` 0 错误；`:app:assembleDebug` 仅剩 `:app:processDebugResources` 的 WM-Shell `android:featureFlag` AAPT 链接阻塞（修复方案已调研，待用户批准），APK 尚未生成**。注意：SysUISdk 不在 git，新机器须重跑 `python3 tools/patch_sdk_dalvik_annotations.py`。

---

## 0. TL;DR — 2026-08-12 里程碑

| 指标 | 值 |
|------|-----|
| KSP 编译 | **BUILD SUCCESSFUL**，0 个 KSP 错误（debug/release 均验证） |
| KSP 生成文件 | 2933 个（含 `DaggerReferenceGlobalRootComponent.java`） |
| Kotlin 编译 | **BUILD SUCCESSFUL**，0 个 Kotlin 错误 |
| APK 编译 | **未生成**：core javac 已 0 错误；仅剩 `processDebugResources`（WM-Shell featureFlag）阻塞 |
| 单元测试 | 60 个全部通过 |
| 实施基线 | Task 1–7 已完成 |

**前一次里程碑（commit `05ea2064`）**：KSP + Dagger 2.55 useBindingGraphFix 首次通过，
但 Kotlin 编译被 Compose inline 问题（`Couldn't inline method call: Box$default`）阻塞。

**本次关键突破**：通过升级 Compose 到 1.11.4 + 迁移到 AGP `builtInKotlin=true`，
**Compose inline 问题已消失**；Task 1 补齐 JSR-305 与 Compose compiler plugin 后，core Kotlin 编译达到 0 错误。

**2026-08-12 后置审查补充**：fresh checkout 已复验 KSP 成功；首次运行
`2026-08-13` 编排修复波次消除 7/8 组 javac 根因（详见 issue 记录 Wave 修复验证小节）。此前 `:app:assembleDebug` 证明 APK 曾被 WM-Shell AAR class-set 重叠及两个不可执行的
header flag JAR 阻塞。Task 1–5 已逐项修复这些阻塞；Task 6 完成构建脚本与维护文档一致性清理；Task 7 完整验证链
确认 KSP/Kotlin 仍通过；2026-08-13 修复波次后 core javac 仅剩 NeverCompile 组（20 个错误），`:app:assembleDebug` 另被 WM-Shell `android:featureFlag` 资源链接错误阻塞。
完整证据见
[`issues/2026-08-12-current-progress-standards-review.md`](./issues/2026-08-12-current-progress-standards-review.md)。

---

## 1. 本次升级详情（2026-08-12）

### 1.1 版本兼容性调研结论

**核心约束**：AGP 9.2.0 ~ 9.4.0-alpha08 **全部** 嵌入 Kotlin 2.2.10（查 POM 确认），
没有更高版本的 AGP 支持 Kotlin 2.3.x。因此无法使用 Kotlin 2.3.x / 2.4.x。

**最终版本矩阵**：

| 组件 | 升级前 | 升级后 | 说明 |
|------|--------|--------|------|
| Kotlin | 2.1.0（显式插件） | 2.2.10（AGP builtInKotlin） | AGP 9.2.0 内置，无法更高 |
| KSP | 2.2.10-2.0.2 | 2.2.10-2.0.2（不变） | 对齐 AGP 内置 Kotlin 2.2.10 |
| Dagger | 2.55 | 2.59.2 | useBindingGraphFix 自 2.58 起默认启用 |
| Compose | 1.8.3 | 1.11.4 | **最高保留 `ExperimentalAnimatableApi` 的版本**（1.12.0 已移除） |
| material3 | 1.4.0-alpha09 | 1.5.0-alpha18 | 对齐 compose 1.11.x（1.5.0-alpha25 需 compose 1.12.0） |
| androidx.core | 1.16.0-beta01 | 1.19.0 | 公网最新 |
| androidx.lifecycle | 2.9.0-alpha11 | 2.11.0 | 公网最新 |
| androidx.activity | 1.11.0-alpha01 | 1.13.0 | 公网最新 |
| androidx.room | 2.7.0-beta01 | 2.8.4 | 公网最新 |
| androidx.recyclerview | 1.5.0-alpha01 | 1.4.0 | 公网最新（AOSP 版本不在公网） |
| constraintlayout | 2.3.0-alpha01 | 2.2.2 | 公网最新（AOSP 版本不在公网） |
| kotlinx-coroutines | 1.10.2 | 1.11.0 | 公网最新 |
| guava | 33.4.8-android | 33.4.8-android（不变） | 已是最新 |
| lottie | 6.6.6 | 6.6.6（不变） | 已是最新 |
| media3 | 1.11.0 | 1.11.0（不变） | 已是最新 |
| errorprone | 2.50.0 | 2.50.0（不变） | 已是最新 |

> **注意**：AOSP prebuilts 中的 `recyclerview:1.5.0-alpha01`、`constraintlayout:2.3.0-alpha01`
> 等版本是 AOSP 内部构建，**不在公网 Maven 发布**。升级时改用公网可用的最新版。

### 1.2 AGP builtInKotlin 迁移

**背景**：Kotlin 2.3.x 的 `kotlin-android` 插件与 AGP `newDsl=true`（9.0 默认）不兼容，
报 `ClassCastException: ApplicationExtensionImpl$AgpDecorated → BaseExtension`。
AGP 建议用 `android.builtInKotlin=true` 迁移到 AGP 内置 Kotlin。

**改动**：
1. `gradle.properties`：`android.builtInKotlin=true`
2. 所有 Android 模块移除 `alias(libs.plugins.kotlin.android)`（AGP 内置提供）
3. JVM 模块（common, plugin-core, plugin-processor）用 `id("org.jetbrains.kotlin.jvm")`（无版本，根 settings 声明 `apply false`）
4. `settings.gradle.kts` 声明 `id("org.jetbrains.kotlin.jvm") version "2.2.10" apply false`
5. catalog `kotlin = "2.2.10"`（仅 `kotlin-compose` 插件引用，须与 AGP 内置版本一致）

### 1.3 DSL 迁移

所有 Android模块的 `android { kotlinOptions { } }` → 顶层 `kotlin { compilerOptions { } }`：
- `freeCompilerArgs = listOf(...)` → `freeCompilerArgs.addAll(...)`
- 涉及 8 个文件：app, SystemUI-core, SystemUI-compose, SystemUI-customization, SystemUI-animation, SystemUI-unfold, SystemUI-shared, SystemUI-shared-biometrics

### 1.4 builtInKotlin + KSP + AIDL 兼容性修复

迁移到 `builtInKotlin=true` 后出现三个兼容性问题，逐一解决：

| 问题 | 根因 | 解决方案 |
|------|------|---------|
| KSP 通过 `kotlin.sourceSets` 添加源码被禁止 | builtInKotlin 不允许第三方插件操作 kotlin sourceSets | `android.disallowKotlinSourceSets=false` |
| KSP `NO-SOURCE`（找不到 Kotlin 源码） | builtInKotlin 下 `java.srcDirs()` 不自动包含 `.kt` 文件 | 所有模块添加 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)` |
| KSP 无法解析 AIDL 生成的接口（`IHomeControlsRemoteProxy`） | builtInKotlin 下 AIDL 输出不在 KSP 源码集中，且 KSP 不自动依赖 AIDL 编译 | AIDL 输出按 variant 加入 `kotlin.srcDir(...)`；`kspDebugKotlin→compileDebugAidl`、`kspReleaseKotlin→compileReleaseAidl` |

### 1.5 新增依赖

- `androidx.asynclayoutinflater:1.1.0` — 解决 `AsyncLayoutInflater` 未解析（KSP 111→4 错误）
- `androidx.leanback-preference:1.2.0` — 独立版本（与 leanback 1.3.0-alpha02 分离，因 leanback-preference 最新仅 1.2.0）

### 1.6 Dagger useBindingGraphFix 简化

- **之前**（commit `05ea2064`）：Dagger 2.55 需手动 `ksp { arg("dagger.useBindingGraphFix", "ENABLED") }`
- **现在**：Dagger 2.59.2（≥2.58）默认启用 useBindingGraphFix，移除手动 `ksp{}` arg
- `ksp.incremental=false` 仍保留（避免 KSP2 FIR 非确定性崩溃 google/ksp#2542）

---

## 2. 当前构建状态详解

### 2.1 KSP 编译（通过）

```bash
./gradlew :SystemUI-core:kspDebugKotlin --console=plain
# → BUILD SUCCESSFUL
# → 0 个 KSP 错误
# → 2933 个文件生成（含 DaggerReferenceGlobalRootComponent.java）
```

**KSP 关键配置**（缺一不可）：
1. `android.builtInKotlin=true`（gradle.properties）— AGP 内置 Kotlin
2. `android.disallowKotlinSourceSets=false`（gradle.properties）— 允许 KSP 操作 kotlin sourceSets
3. `ksp.incremental=false`（gradle.properties）— 避免 KSP2 FIR 崩溃
4. Dagger 2.59.2（≥2.58 默认启用 useBindingGraphFix）
5. SystemUI-core: `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)` + AIDL 输出目录加入 kotlin sourceSet
6. KSP/AIDL 按 variant 精确接线：debug→debug、release→release

### 2.2 Kotlin 编译（通过）

```bash
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --console=plain
# → BUILD SUCCESSFUL
# → 0 个 Kotlin 错误
```

Task 1 补充了 AOSP `Android.bp` 明确声明的 `com.google.code.findbugs:jsr305:3.0.2`，
并应用了 Soong 等价的 Compose compiler plugin；此前的 `GuardedBy` 与 Box inline 错误均消失。

### 2.3 APK 入口（Task 7 已复验，当前被 core javac 阻塞）

审查阶段发现的 3 类前置阻塞已逐项修复：

1. `jsr305` 缺失 → 官方 `com.google.code.findbugs:jsr305:3.0.2` 已接入；
2. WM-Shell 12 个重复 shared AIDL 类 → 主/shared AAR class-set 交集已为 0；
3. 两个 header flag JAR 无法 D8 → shared flags 换成 Soong `javac` JAR，SettingsLib flags 改 `compileOnly`。

Task 7 运行 `:app:assembleDebug` 后，构建越过上述阶段，但在
`:SystemUI-core:compileDebugJavaWithJavac` 仍有 NeverCompile 组 20 个错误（2026-08-13 波次已修复其余 7 组）；`:app:processDebugResources` 另有 WM-Shell featureFlag AAPT 链接错误。`app-debug.apk` 未生成。
错误集中在真实依赖/产物缺口：`NeverCompile`、setupcompat、Wi‑Fi/WM‑Shell aconfig flags、
zxing、SystemUI-tags 过期 JAR、`:SystemUI-shared` 未运行 Dagger KSP、以及 `androidx.media`
被传递解析为 1.4.1。逐项根因见
[`issues/2026-08-12-current-progress-standards-review.md`](./issues/2026-08-12-current-progress-standards-review.md#task-7完整验证链与真实-apk-阻塞2026-08-12)。

### 2.4 Compose inline 问题已解决

**之前**（commit `05ea2064`）：`:SystemUI-core:compileDebugKotlin` 被
`Couldn't inline method call: Box$default` 阻塞（AGENTS.md §2.4 已知问题：
framework.jar 污染 KotlinCompile Compose inline metadata）。

**现在**：升级到 Compose 1.11.4 + Kotlin 2.2.10（builtInKotlin）后，
**Compose inline 问题已消失**，Kotlin 编译可正常运行到源码错误。

---

## 3. 工具链版本

| 工具 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.3.1 | `libs.plugins.android.library` |
| Kotlin | 2.2.10 | AGP `builtInKotlin=true` 内置（无显式插件） |
| KSP | 2.2.10-2.0.2 | 对齐 AGP 内置 Kotlin 2.2.10 |
| Dagger | 2.59.2 | useBindingGraphFix 默认启用（≥2.58） |
| Compose | 1.11.4 | 最高保留 `ExperimentalAnimatableApi` |
| material3 | 1.5.0-alpha18 | 对齐 compose 1.11.x |
| JDK | 21 | 工具链 |
| 目标 SDK | `SysUISdk` | 自定义 preview |

---

## 4. 模块结构

**最终 13 个 Gradle module**：

```
:app                          # APK 入口（无源码，只依赖 :SystemUI-core）
:SystemUI-core                # 主模块（src + compose + pods + 入口类）
:SystemUI-res                 # 独立资源 namespace（res/res-keyguard/res-product）
:SystemUI-common              # Common + Log + utils 合并（JVM）
:SystemUI-animation           # PlatformAnimation + Shader 合并
:SystemUI-plugin-core         # Plugin runtime API（JVM）
:SystemUI-plugin-processor    # Plugin annotation processor（build-time）
:SystemUI-plugin              # PluginLib runtime（含 bcsmartspace）
:SystemUI-unfold              # Unfold（KSP Dagger）
:SystemUI-customization       # Customization（含 res）
:SystemUI-shared              # Shared + keyguard 合并
:SystemUI-shared-biometrics   # biometrics（独立 R namespace）
:SystemUI-compose             # Compose Core + Scene 合并
```

**8 个 AAR**（`libs/aars/` + `libs/maven/`，2026-08-12 起随 `libs/` 全部提交入 git）：
animationlib、WifiTrackerLib、iconloader、SettingsLib、WindowManager-Shell、WindowManager-Shell-shared、LowLightDreamLib、SettingsLibColor。

**构建依赖**：`libs/` 已提交入 git，新 clone 无需重新生成 AOSP 产物即可复现当前构建基线；
当前尚不能成功产出 APK：首个失败层是 `:app:processDebugResources`（WM-Shell featureFlag）。仅在需要更新 AOSP 产物时才跑
`python3 tools/package_aosp_aar.py --all` → `python3 tools/install_aar_to_maven.py`。

---

## 5. 待解决

1. **修复 Task 7 记录的 8 组 Java classpath/产物缺口**，然后重新运行 `:app:assembleDebug`
2. 处理 Deferred Follow-ups：Room schema 导出、Kotlin 2.3 data-class copy 可见性、manifest 重复权限、评估移除 `android.disallowKotlinSourceSets=false`

执行计划：[`superpowers/plans/2026-08-12-build-to-apk-readiness.md`](./superpowers/plans/2026-08-12-build-to-apk-readiness.md)

---

## 6. 历史错误数演变（供诊断参考）

| 日期 | 错误数 | 关键改动 |
|------|--------|----------|
| 2026-07-22 初 | 5296 | 仅有 sdk android.jar |
| 2026-07-22 | 2000 | framework.jar + 删 stub + Monet + Flags jar |
| 2026-07-28 | 1979 | 删 server-notification-flags stub |
| 2026-07-28 | 1879 | 全项目 R import 歧义清零 |
| 2026-07-29 | 509 | 大批源码补齐 |
| 2026-07-29 | 70 | tier① 全源码化 + KSP + AIDL 源码编译 + 规则 C 审查 |
| 2026-08-11 | — | KSP + Dagger 2.55 useBindingGraphFix 首次通过（0 KSP 错误） |
| **2026-08-12** | **KSP: 0, Kotlin: 2** | **全依赖升级 + builtInKotlin 迁移** |
| **2026-08-12 实施** | **KSP: 0, Kotlin: 0** | **Task 1–6：jsr305、aconfig JAR、WM-Shell AAR、variant KSP/AIDL、AGP 9.3.1、文档/格式清理** |
| **2026-08-12 验证** | **KSP: 0, Kotlin: 0, javac: 42** | **Task 7：完整验证链；`:app:assembleDebug` 在 core Java 编译阶段失败，APK 未生成** |

> **注意**：错误数仅作诊断参考，不是提交/回滚/审批门槛（规则 I）。

---

## 7. 验证清单

提交前确认：

- [ ] 改动是否让模块结构、依赖来源、源码/资源对齐或最终可构建性向前推进
- [ ] 来源和决策已记录；中间态的已知问题没有被隐瞒
- [ ] 没引入新 stub
- [ ] 没有凭空生成或擅自修改 res/ 资源
- [ ] 已如实记录本次是否运行编译/验证及实际结果

---

## 8. 快速命令

```bash
# 重新生成 AOSP 产物（可选——libs/ 已提交入 git，新 clone 无需此步）
python3 tools/package_aosp_aar.py --all && python3 tools/install_aar_to_maven.py

# KSP 编译 + 统计错误
./gradlew :SystemUI-core:kspDebugKotlin --console=plain 2>&1 | tee /tmp/build.log
echo "KSP errors: $(grep -c 'e: \[ksp\]' /tmp/build.log)"

# Kotlin 编译 + 统计错误
./gradlew :SystemUI-core:compileDebugKotlin --console=plain 2>&1 | tee /tmp/build2.log
echo "Kotlin errors: $(grep -c '^e: file:' /tmp/build2.log)"

# 分类错误
grep "^e: file:" /tmp/build2.log | \
  sed -E 's|.*/SystemUI-Gradle/SystemUI-core/src/com/android/||; s|/[^/]+\.kt.*||' | \
  sort | uniq -c | sort -rn | head -20

# 单元测试
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```
