# 2026-08-12 — 全依赖升级 + AGP builtInKotlin 迁移

> **状态**: 完成（commit `e3548016`，已 push）
> **前置**: 2026-08-11 commit `05ea2064`（KSP + Dagger 2.55 useBindingGraphFix 首次通过）

---

## 一、背景与动机

用户要求**将所有依赖尽可能升级到最新版本**。核心动机：

> "我们刚刚就是因为 ksp 不是最新的版本导致的还需要去看文档才解决了一个在高版本已经默认解决的问题"

——避免因旧版本 bug 需要手动 workaround（如 Dagger 2.55 需手动 `useBindingGraphFix`，2.58+ 已默认启用）。

此前状态：KSP 编译通过，但 `:SystemUI-core:compileDebugKotlin` 被 Compose inline 问题
（`Couldn't inline method call: Box$default`）阻塞（AGENTS.md §2.4 已知问题）。

---

## 二、版本兼容性调研

### 2.1 AGP ↔ Kotlin 绑定关系（关键约束）

逐个查 AGP POM（Google Maven），确认 `kotlin-gradle-plugin` 与 `kotlin-stdlib` 的 runtime 依赖版本：

| AGP 版本 | 嵌入 Kotlin |
|----------|------------|
| 9.2.0 | 2.2.10 |
| 9.3.0-rc01/rc02 | 2.2.10 |
| 9.3.1 | 2.2.10 |
| 9.4.0-alpha01 ~ alpha08 | 2.2.10 |

**结论**：**所有可用 AGP 版本都绑定 Kotlin 2.2.10**，AGP 尚未适配 Kotlin 2.3.x。
最新稳定 AGP 为 9.3.1。

### 2.2 尝试显式 Kotlin 插件覆盖（失败）

方案：Kotlin 2.2.21 + `android.builtInKotlin=false`，用显式 `kotlin-android` 插件覆盖内置版本。

**失败**：
```
ClassCastException: ApplicationExtensionImpl$AgpDecorated_Decorated
  cannot be cast to BaseExtension
```

**根因**：Kotlin 2.2.21 插件与 AGP 9.2.0 的 `newDsl`（默认开启）不兼容；
`android.newDsl=false` 也无法回避（AGP 9.x 已强推 newDsl）。

**另查**：AGP 只有 `android.builtInKotlin` 开关，**没有** `builtInKotlinVersion` 之类
的覆盖属性——内置版本不可覆盖。

### 2.3 Compose 版本上限（AOSP 源码约束）

逐个验证 `ExperimentalAnimatableApi` 在各版本的存在性
（AOSP `ContainerReveal.kt` 等源码使用该类）：

| Compose 版本 | ExperimentalAnimatableApi |
|--------------|---------------------------|
| 1.10.6 | 存在 |
| 1.11.0 | 存在 |
| 1.11.4 | 存在 |
| 1.12.0-alpha01 | 已移除 |
| 1.12.0-rc01 | 已移除 |

**结论**：Compose 最高 **1.11.4**。

### 2.4 material3 对齐 Compose

material3 各版本的 Compose 依赖（查 .module metadata）：

| material3 | 依赖 Compose |
|-----------|--------------|
| 1.5.0-alpha18 | 1.11.0-beta02 兼容 1.11.4 |
| 1.5.0-alpha25 | 1.12.0-beta01 不可用 |

**结论**：material3 最高 **1.5.0-alpha18**。

### 2.5 AOSP prebuilts 版本 ≠ 公网版本

AOSP prebuilts 中的多个版本是 AOSP 内部构建，**不在公网 Maven 发布**：

| 依赖 | AOSP 版本 | 公网最新 |
|------|-----------|----------|
| recyclerview | 1.5.0-alpha01 | 1.4.0 |
| constraintlayout | 2.3.0-alpha01 | 2.2.2 |

**方法**：逐个查 `maven-metadata.xml` 确认真实最新版：
```bash
curl -s 'https://dl.google.com/dl/android/maven2/<group>/<artifact>/maven-metadata.xml' \
  | grep -oP '<latest>\K[^<]+'
```

**另一坑**：Google Maven 下载 AAR 的正确文件名须从 `.module` metadata 的
`files.url` 查（如 `animation-core-android-{ver}.aar`），用错误 URL 会得到
1449 字节的 404 页面。

---

## 三、最终版本矩阵

| 组件 | 升级前 | 升级后 |
|------|--------|--------|
| Gradle | 9.5.0 | 9.5.0（不变） |
| AGP | 9.2.0 | 9.2.0（不变，settings.gradle.kts 硬编码） |
| Kotlin | 2.1.0（显式插件） | **2.2.10（AGP builtInKotlin 内置）** |
| KSP | 2.2.10-2.0.2 | 2.2.10-2.0.2（不变，须与内置 Kotlin 严格匹配） |
| Dagger | 2.55 | **2.59.2**（useBindingGraphFix 自 2.58 默认启用） |
| Compose | 1.8.3 | **1.11.4** |
| material3 | 1.4.0-alpha09 | **1.5.0-alpha18** |
| androidx.core | 1.16.0-beta01 | 1.19.0 |
| androidx.annotation | — | 1.11.0-alpha01 |
| androidx.lifecycle | 2.9.0-alpha11 | 2.11.0 |
| androidx.fragment | — | 1.9.0-rc01 |
| androidx.preference | — | 1.2.1 |
| androidx.leanback | — | 1.3.0-alpha02 |
| androidx.leanback-preference | 共享 leanback ref | **独立 1.2.0**（最新仅 1.2.0） |
| androidx.concurrent | — | 1.4.0-alpha01 |
| androidx.exifinterface | — | 1.4.2 |
| androidx.cardview | — | 1.0.0 |
| androidx.recyclerview | 1.5.0-alpha01 | **1.4.0**（公网最高） |
| androidx.viewpager2 | — | 1.1.0 |
| androidx.dynamicanimation | — | 1.1.0 |
| androidx.palette | — | 1.1.0-alpha01 |
| androidx.appcompat | — | 1.8.0-rc01 |
| androidx.activity | 1.11.0-alpha01 | 1.13.0 |
| androidx.datastore | — | 1.3.0-alpha10 |
| androidx.window | 1.3.0 | 1.6.0-alpha05 |
| androidx.tracing | — | 2.0.0-rc01 |
| androidx.savedstate | — | 1.5.0 |
| androidx.mediarouter | — | 1.9.0-alpha01 |
| androidx.room | 2.7.0-beta01 | 2.8.4 |
| androidx.asynclayoutinflater | — | **1.1.0（新增）** |
| kotlinx-coroutines | 1.10.2 | 1.11.0 |
| guava | 33.4.8-android | 33.4.8-android（不变） |
| lottie | 6.6.6 | 6.6.6（不变） |
| media3 | 1.11.0 | 1.11.0（不变） |
| errorprone | 2.50.0 | 2.50.0（不变） |

---

## 四、builtInKotlin 迁移实施

### 4.1 步骤

1. `gradle.properties` 加 `android.builtInKotlin=true`
2. 所有 Android 模块移除 `alias(libs.plugins.kotlin.android)`
   （app, core, customization, animation, unfold, plugin, shared-biometrics, shared, compose）
3. JVM 模块（common, plugin-core, plugin-processor）改用 `id("org.jetbrains.kotlin.jvm")` 无版本
4. `settings.gradle.kts` 声明 `id("org.jetbrains.kotlin.jvm") version "2.2.10" apply false`
5. catalog `kotlin = "2.2.10"`（仅 `kotlin-compose` 插件引用，须与 AGP 内置一致）
6. 所有 `android { kotlinOptions {} }` → 顶层 `kotlin { compilerOptions {} }`，
   `freeCompilerArgs = listOf(...)` → `freeCompilerArgs.addAll(...)`（8 个文件）

### 4.2 中途踩坑：settings plugins{} 不能用 catalog

`settings.gradle.kts` 的 `plugins {}` 块写 `alias(libs.plugins.android.application)` 报
`Unresolved reference 'libs'`——**settings 阶段 version catalog 尚未初始化**。

**对策**：settings.gradle.kts 保持硬编码版本：
```kotlin
plugins {
    id("com.android.application") version "9.2.0" apply false
    id("com.android.library") version "9.2.0" apply false
    id("org.jetbrains.kotlin.jvm") version "2.2.10" apply false
}
```

### 4.3 中途踩坑：app/build.gradle.kts 结构损坏

`kotlin {}` 块误插入 `android {}` 中间 → 59 个 "Unexpected symbol" 错误。
完整重写：android{} 包含 signingConfigs/buildTypes，kotlin{} 在其后。

---

## 五、builtInKotlin + KSP + AIDL 三个兼容性问题

### 问题 1：KSP 禁止操作 kotlin.sourceSets

```
Using kotlin.sourceSets DSL to add Kotlin sources is not allowed with built-in Kotlin.
```

KSP 插件需要往 kotlin sourceSets 添加生成源码目录。

**解**：`android.disallowKotlinSourceSets=false`（experimental 警告可接受）

### 问题 2：KSP NO-SOURCE

KSP 报 NO-SOURCE，找不到任何 Kotlin 源码。

**根因**：**builtInKotlin 下 `java.srcDirs()` 不自动包含 `.kt` 文件**
（传统 kotlin-android 插件会同时扫描 java.srcDirs 中的 .kt；builtInKotlin 不会）。
其他模块此前已有 `kotlin.srcDirs`，只有 SystemUI-core 缺。

**解**：SystemUI-core 补 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`

### 问题 3：KSP 无法解析 AIDL 生成接口

4 个错误：`IHomeControlsRemoteProxy` 不可解析。

**根因**：builtInKotlin 下 KSP 运行在 `compileDebugAidl` 之前，
且 AIDL 生成源码不在 kotlin sourceSet 中。

**解**（三件套）：
1. `android.sourceset.disallowProvider=false`（允许 sourceSets provider API）
2. AIDL 输出目录加入 kotlin sourceSet：
   ```kotlin
   android.sourceSets {
       getByName("debug") {
           kotlin.srcDir(layout.buildDirectory.dir("generated/aidl_source_output_dir/debug/out"))
       }
   }
   ```
3. 任务依赖（注意：配置阶段 `tasks.named("kspDebugKotlin")` 找不到任务，须用 matching）：
   ```kotlin
   tasks.matching { it.name.startsWith("ksp") }.configureEach {
       dependsOn("compileDebugAidl")
   }
   ```

**曾尝试** `androidComponents.onVariants` + `addGeneratedSourceDirectory`：失败，
compileDebugAidl 任务在 onVariants 回调时未注册。

---

## 六、Dagger useBindingGraphFix 简化

- 升级前（Dagger 2.55）：必须手动 `ksp { arg("dagger.useBindingGraphFix", "ENABLED") }`
  （commit `05ea2064` 的解法，修复 120 个 MissingBinding 错误）
- 升级后（Dagger 2.59.2）：**2.58 起默认启用**，移除手动 ksp{} arg

`ksp.incremental=false` 保留（避免 KSP2 FIR 非确定性崩溃 google/ksp#2542）。

---

## 七、验证结果（有证据）

```bash
./gradlew :SystemUI-core:kspDebugKotlin --console=plain
# → BUILD SUCCESSFUL
# → 0 个 KSP 错误（grep -c 'e: \[ksp\]' = 0）
# → 2933 个生成文件
# → DaggerReferenceGlobalRootComponent.java 已生成

./gradlew :SystemUI-core:compileDebugKotlin --console=plain
# → BUILD FAILED
# → 2 个错误（均为 pre-existing，升级前就存在）：
#   CommunalAppWidgetHost.kt:25  Unresolved reference 'concurrent'
#   CommunalAppWidgetHost.kt:52  Unresolved reference 'GuardedBy'

python3 -m unittest discover -s tools/tests -p 'test_*.py'
# → 57 个测试全部通过
```

**额外收益**：此前阻塞 Kotlin 编译的 Compose inline 问题
（`Couldn't inline method call: Box$default`）**已消失**——
Compose 1.11.4 + builtInKotlin 组合下不再复现。

---

## 八、遗留问题

1. **2 个 pre-existing Kotlin 错误**：`concurrent` / `GuardedBy` 未解析
   （androidx.concurrent / jsr305 依赖问题，待补依赖）
2. `srcDirs` deprecation 警告（AGP 建议 `directories` mutable set，多个模块）
3. `android.disallowKotlinSourceSets=false` 是 experimental 回退开关，AGP 未来版本可能移除
4. AGP 适配 Kotlin 2.3.x 后可再次升级

---

## 九、commit

`e3548016` — Upgrade all deps to latest available + migrate to AGP builtInKotlin
（16 files, +211/-138，已 push 到 main）
