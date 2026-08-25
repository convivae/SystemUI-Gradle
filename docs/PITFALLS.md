# SystemUI-Gradle 踩坑记录 (PITFALLS.md)

> **目的**: 记录所有"看似简单但实际不行"的方案，帮助下个 AI 避免重复失败。
> **格式**: 现象 → 尝试 → 失败原因 → 替代方案
> **职责边界（2026-08-20 起）**: 本文件只保存**可复用根因/防错经验**，不维护当前错误数、当前 blocker 等动态状态；完整实时状态唯一见 `docs/CURRENT_STATE.md`。

---

## 1. 环境类踩坑

### 1.1 AGP 版本与 Kotlin 编译器版本绑定（2026-08-12 更新）

**现象**: 项目声明 `kotlin("android") version "2.1.0"`，但 AGP 9.2 内部嵌入 `kotlin-compiler-embeddable 2.2.10`。编译时实际使用 2.2.10。

**根因**: AGP 9.2 故意用比 plugin 更新的 Kotlin 编译器。

**2026-08-12 更新**: 已迁移到 `android.builtInKotlin=true`，移除显式 kotlin-android 插件。
Kotlin 版本由 AGP 内置（2.2.10），不再单独声明。

**关键发现**：
- AGP 9.2.0 ~ 9.4.0-alpha08 **全部** 嵌入 Kotlin 2.2.10（查 POM 确认）
- Kotlin 2.3.x 的 `kotlin-android` 插件与 AGP `newDsl=true` 不兼容
- `builtInKotlin=true` 是 AGP 9.x 的推荐路径
- JVM 模块仍需显式 `id("org.jetbrains.kotlin.jvm")`（builtInKotlin 只影响 Android 模块）

### 1.2 KAPT 1.9+ 与 Gradle 9.5 不兼容

**现象**: 启用 KAPT 后报 "IR fake override builder 内部错误"

**根因**: KAPT 1.9+ 引入了 IR backend，但与 Gradle 9.5 的 class 文件结构冲突

**结论**: KAPT 全面禁用（历史案例，见上）；所有注解处理改用 **KSP**（Dagger 自 2026-08-11 起经 KSP 生成代码，问题已解决）。

**替代方案**:
- KSP (推荐)
- 降级 AGP 到 8.x
- 显式 Provider

### 1.3 SysUISdk 是 preview SDK

**现象（AGP 9.2.0）**: AGP 曾警告 "compile SDK preview version 'SysUISdk' has not been tested"。

**根因**: `SysUISdk` 是我们基于 AOSP 产物生成的自定义 preview SDK。

**当前（AGP 9.3.1）**: core KSP/Kotlin 编译日志不再出现该警告；无需额外 suppression。

**后果**: `@hide` API 由自定义 SDK/android.jar 与 framework.jar 的真实 AOSP 产物提供，不依赖 stub。

### 1.5 AGP builtInKotlin + KSP + AIDL 兼容性（2026-08-12 新增）

**现象**: 迁移到 `android.builtInKotlin=true` 后，KSP 编译失败。

**三个独立问题，逐一解决**：

**问题 1：KSP 通过 `kotlin.sourceSets` 添加源码被禁止**
```
Using kotlin.sourceSets DSL to add Kotlin sources is not allowed with built-in Kotlin.
```
**解决**: `android.disallowKotlinSourceSets=false`（gradle.properties）

**问题 2：KSP `NO-SOURCE`（找不到 Kotlin 源码）**
**根因**: builtInKotlin 下 `java.srcDirs()` 不自动包含 `.kt` 文件。
传统 Kotlin 插件会同时扫描 java.srcDirs 中的 `.kt` 文件，builtInKotlin 不会。
**解决**: 所有 Android 模块添加 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`：
```kotlin
sourceSets {
    getByName("main") {
        java.srcDirs("src")
        kotlin.srcDirs("src")  // 必须添加！
    }
}
```

**问题 3：KSP 无法解析 AIDL 生成的接口（`IHomeControlsRemoteProxy`）**
**根因**: builtInKotlin 下 AIDL 生成的 Java 源码默认不在 KSP/Kotlin 源码集中。
KSP 任务也不自动依赖 `compileDebugAidl`。
**解决**:
1. AIDL 输出目录按 variant 加入 kotlin sourceSet（不使用 sourceSets provider API）：
```kotlin
android.sourceSets {
    getByName("debug") {
        kotlin.srcDir("build/generated/aidl_source_output_dir/debug/out")
    }
    getByName("release") {
        kotlin.srcDir("build/generated/aidl_source_output_dir/release/out")
    }
}
```
2. 按 variant 添加任务依赖：
```kotlin
tasks.matching { it.name == "kspDebugKotlin" }.configureEach { dependsOn("compileDebugAidl") }
tasks.matching { it.name == "kspReleaseKotlin" }.configureEach { dependsOn("compileReleaseAidl") }
```

**结果**: KSP 0 错误，2933 个文件生成，AIDL 接口全部解析；release KSP 不再错误依赖 debug AIDL 输出。

### 1.6 Compose 版本与 AOSP 源码兼容性（2026-08-12 新增）

**现象**: 升级 Compose 到 1.12.0-rc01 后，`ExperimentalAnimatableApi` 未解析。

**根因**: `ExperimentalAnimatableApi` 在 Compose 1.12.0 中被移除，
但 AOSP SystemUI 源码（`ContainerReveal.kt` 等）仍在使用。

**排查过程**:
- 1.11.4 有 `ExperimentalAnimatableApi`
- 1.12.0-alpha01 已移除
- 1.12.0-rc01 已移除

**结论**: Compose 最高只能用到 **1.11.4**。
material3 对齐 **1.5.0-alpha18**（依赖 compose 1.11.0-beta02；
1.5.0-alpha25 需 compose 1.12.0-beta01 不兼容）。

### 1.7 AOSP prebuilts 版本 ≠ 公网 Maven 版本（2026-08-12 新增）

**现象**: 按 AOSP prebuilts 配置 androidx 版本后，Gradle 依赖解析失败（404）。

**根因**: AOSP 内部构建的 androidx 版本（如 `recyclerview:1.5.0-alpha01`、
`constraintlayout:2.3.0-alpha01`）**不在公网 Maven 发布**。
AOSP 有自己的构建系统，版本号可能领先公网。

**对策**: 升级时先用 `maven-metadata.xml` 检查公网可用版本：
```bash
curl -s 'https://dl.google.com/dl/android/maven2/androidx/recyclerview/recyclerview/maven-metadata.xml' \
  | grep -oP '<latest>\K[^<]+'
```

**踩过的坑**: recyclerview 1.5.0-alpha01 → 公网最新 1.4.0；
constraintlayout 2.3.0-alpha01 → 公网最新 2.2.2。

---

## 2. aconfig Flags 类踩坑

### 2.1 [历史案例] `libs/server-notification-flags.jar` 是空 jar

**现象（2026-07，历史案例）**:
```bash
$ unzip -l libs/server-notification-flags.jar
(empty)
```

**当时真实位置**: 本地 Maven `notification-flags` JAR（后被 Task 034 迁出本地 Maven）。

**根因**: 历史拷贝错，或 git LFS 丢失。文件名误导。

**教训**: 同名/易混文件名会误导 classpath 排查；引入或排查 flags JAR 时先 `unzip -l` 实测内容与真实坐标。

**当前状态**: 该 jar 已不存在；notification flags 现为 `libs/notification-flags.jar`（Task 034 落地的完整 Soong `javac` 产物）。

### 2.2 [已证伪 2026-07-28] Kotlin 2.2.10 看不到 aconfig Flags `@UnsupportedAppUsage` 注解的类

> **本条推测已被证伪**。真正根因：源码 stub `com/android/server/notification/Flags.kt`
> 遮蔽了 jar。孤立 K2JVMCompiler（含完整 128 项 AGP classpath）编译成功，证明 classpath 和
> Kotlin 2.2.10 都无罪。见下方 §2.4 与 `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`。
> 下面保留原推测内容供"如何走偏"的教训参考。

**现象**:
- Jar 在 classpath（`./gradlew --debug` 验证）
- `javap -p` 能看到方法
- 独立 K2JVMCompiler 同样报错
- 但独立 `kotlin("jvm") 2.1.0` 项目能编译

**根因（推测）**: Kotlin 2.2.10 对 `@UnsupportedAppUsage` 注解的语义改变，可能需要 `LIBRARY` 或 `WHITELIST` 标记。

**已尝试**:
- `compileOnly` / `implementation` / `api` 各种配置
- 提供 `AconfigFlagAccessor` 注解类
- 提供 `UnsupportedAppUsage` 注解类
- 提供 `FeatureFlags` 接口
- `libraries.from()` 双重注入
- 加 `implementation` 显式声明

**全部失败**。

**下一步**:
- 提取 `FeatureFlags` 接口跟 Flags.class 一起打包
- 用 K2JVMCompiler 完整 classpath 测试
- 加 `-Xverbose` 看真实日志

### 2.3 systemui-flags.jar 可以，server-notification-flags.jar 不行

**对比**:
- `com.android.systemui.Flags` (systemui-flags.jar, 53220 bytes) → 工作
- `com.android.server.notification.Flags` (notification-flags.jar, 6285 bytes) → unresolved

**差异**:
- 包名: `com.android.systemui.*` vs `com.android.server.*`
- 类大小: 53220 vs 6285 字节

**可能根因**:
- Kotlin Android plugin 对 `com.android.systemui.*` namespace 特殊处理
- 或者大类的某个方法签名不同
- 或者 `@UnsupportedAppUsage` 在不同类的处理方式不同

> 以上全部错。真正差异见 §2.4。

### 2.4 [真正根因 2026-07-28] 源码 stub 遮蔽 jar 类

**现象**: `Unresolved reference '<方法名>'`，但 jar 在 classpath、`javap` 能看到方法、孤立编译成功。

**根因**: 源码树里存在同包同名的 stub（如 `src/com/android/server/notification/Flags.kt` 里的
`object Flags`）。**全项目编译时 Kotlin 优先用源码定义，而非 jar**。stub 缺少 jar 里的方法
（或把方法写成了 `val` 属性），于是消费者 import 该方法就 unresolved。

**为何 systemui-flags.jar 能工作**: 因为源码里**没有** `com.android.systemui.Flags` 的 stub，
所以它正常从 jar 解析——与包名/类大小/注解统统无关。

**诊断决定性实验**:
```bash
# 1. 孤立编译最小复现（只 import 那个方法并调用）
java -cp "$KC:$KS:$KR:$KX" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler \
  -cp "<完整 AGP classpath>" -d /tmp/out -jvm-target 21 Test.kt
# → 成功 ⇒ classpath / 编译器都无罪，问题在源码集

# 2. 查有没有同名源码遮蔽 jar
find . -path "*/<包路径>/<类名>.*" -not -path "*/build/*"
```

**修复**: `git rm` 该 stub（本身违反 §规则1）。

**通用规律**: 只有 (源码是 stub) + (有真实 jar 提供该类) + (消费者引用了 stub 缺失的成员)
三者同时满足才致错。见 `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md` §3 的同类隐患清单。

### 3.1 Compose 内部 API (`thenIf`, `drawInContainer`)

**现象**: `com.android.compose.animation.scene.*` 12 个 Unresolved

**缺失符号**:
- `thenIf` (Modifier extension)
- `drawInContainer` (DrawModifier)
- `ContainerState` (Scene 内部)

**根因**: 这些是 Compose 内部的 Modifier，**未在公开 API 中**

**绕道**:
- 升级 androidx.compose 到 1.8.0（可能没有这些内部 API）
- 提取 AOSP Compose 内部 AAR（如果存在）
- 复制源码但反编译 androidx.compose（违反规则 P）
- 暂时排除这些源码

**历史案例（2026-07）**: 当时源码未入 git 而被 `srcDir("src")` 隐式包含。现 Scene 源码已作为 `:SystemUI-compose` 模块入库；本条保留作"隐式 srcDir 吞噬未跟踪文件"的防错案例。

### 3.2 Compose / 多命名空间 R import 歧义 (2026-07-28 **已解决**)

**现象**: `imported name 'R' is ambiguous`，且**级联**使文件内所有 `R.xxx` 报 unresolved。
全项目 7 个文件命中（不止 Compose Theme）。

**根因**: 这些文件被（非 AOSP 地）多加了一行 `import com.android.systemui.R`，
与文件本应使用的另一个 R（`internal.R` / `wm.shell.R` / `android.R` / `settingslib.R`）冲突。
**AOSP 原文件每个都只 import 一个 R。**

**正解（对齐 AOSP）**: 删除多余的那一个 import，而**不是**改成 alias import。
之前本节猜测用 `import ... as SystemUiR / ComposeR` alias —— **是错的**，
实际 7 个文件各自只需保留单一 R（见下表），删掉多余的 `systemui.R` 即可。

| 文件 | 保留(对齐AOSP) | 删除 |
|------|---------------|------|
| compose/theme/AndroidColorScheme.kt | `com.android.internal.R` | systemui.R |
| compose/theme/PlatformTheme.kt | `com.android.internal.R` | systemui.R |
| accessibility/floatingmenu/DragToInteractView.kt | `com.android.wm.shell.R` | systemui.R |
| screenshot/ScreenshotWindow.kt | `android.R` | systemui.R |
| user/ui/dialog/AddUserDialog.kt | `com.android.settingslib.R` | systemui.R |
| user/ui/dialog/ExitGuestDialog.kt | `com.android.settingslib.R` | systemui.R |
| volume/domain/interactor/DeviceIconInteractor.kt | `com.android.settingslib.R` | systemui.R |

**结果**: 1979 → 1879 (−100)，全项目 R 歧义清零。详见 `docs/issues/2026-07-28-r-import-ambiguity.md`。

**残留 caveat**: `AddUserDialog.kt` / `DragToInteractView.kt` 因我们多模块资源拆分，
**确实同时**需要两个 R 命名空间（少数 id/string 只在 SystemUI-core/res）。删 systemui.R 后仍净下降，
故先按对齐 AOSP 处理；这几个残留 unresolved（`user_add_user_message_guest_remove`、`action_edit` 等）
是诚实的资源缺口，正解是**这时才用 alias import**，留作 Stage 4 资源完整性处理。

---

## 4. Gradle / AGP 9 踩坑

### 4.1 `libraries.from()` 顺序

**技巧**: 在 `KotlinCompile` 中，`libraries.from()` 添加顺序决定优先级

```kotlin
// 顺序很重要
libraries.from(serverNotificationFlagsJar)  // 高优先级
libraries.from(internalFlagsJars)          // 中
libraries.from(frameworkJar)               // 低（同名 stub 兜底）
```

### 4.2 `emptySet()` 需要类型参数

**现象**: Kotlin DSL 不让 `emptySet()` 隐式推断

**解决**:
```kotlin
files(frameworkJar) + files(options.bootstrapClasspath?.files ?: emptySet<File>())
```

### 4.3 `frameworks/base/libs/WindowManager/Shell.jar` 41MB

**笔记**: AOSP 编译产物是 41MB / 20155 class，比参考项目 CarSystemUIGradle 用的 8.7MB 大很多。

**历史案例**: 早期曾直接 cp 完整版不裁剪；后改为确定性本地 Maven AAR（`libs.systemui.wmshell`，现 1.0.1 含 proto 闭包）。

### 4.4 AOSP 命名 vs 参考项目命名

| Plan 假设 | 实际 AOSP |
|-----------|-----------|
| `SystemUI-shared.jar` | `SystemUISharedLib.jar` |
| `SystemUI-animation.jar` | `PlatformAnimationLib.jar` |
| `SystemUI-customization.jar` | `SystemUICustomizationLib.jar` |
| `SystemUI-plugin.jar` | `SystemUIPluginLib.jar` |

**踩坑**: 直接复制 CarSystemUIGradle 命名会找不到文件。

### 4.5 相对路径 `libs/` vs `${rootProject.projectDir}/libs/`

**现象**: `compileOnly(files("libs/xxx.jar"))` 在 module 内会从 `${moduleDir}/libs/` 找

**解决**: 显式用 `${rootProject.projectDir}/libs/xxx.jar`

---

## 5. AOSP 拷贝踩坑

### 5.1 SystemUI `src/` 共 4183 文件

**笔记**: 直接全量拷贝不现实，要分模块渐进。

### 5.2 `SystemUIApplication` 501 LoC 注入依赖

**笔记**: Dagger 根文件 24 个，迁移要小心。

### 5.3 `Dependency.java` 是 legacy static bridge (~2500 LoC)

**笔记**: 全量重构波及整个 SystemUI，要谨慎。

### 5.4 AOSP `compile SDK preview` 不在 androidx 路径

**笔记**: 自定义 SDK 在 `/home/conv/Android/Sdk/platforms/android-SysUISdk/`

---

## 6. 调试工具陷阱

### 6.1 `--info` 看 kotlin 编译器输出

**现象**: `--info` 不显示 kotlin 编译器的实际命令行

**解决**:
```bash
./gradlew :SystemUI-core:compileDebugKotlin --debug 2>&1 | grep -oE "[-]classpath [^ ]+"
```

### 6.2 手动 K2JVMCompiler 缺 jar

**最小需求**:
```
KC: kotlin-compiler-embeddable-2.2.10.jar
KS: kotlin-stdlib-2.2.10.jar
KR: kotlin-reflect-2.2.10.jar
KX: kotlinx-coroutines-core-jvm-1.10.2.jar  # 在 Gradle wrapper lib
```

### 6.3 `unzip -l ... | grep -i` 大 jar 慢

**解决**: 先用 `unzip -l jar.zip | grep -i name` 快速

---

## 7. 决策类陷阱

### 7.1 "看起来简单的方案"通常不行

| 方案 | 看似简单 | 实际 |
|------|---------|------|
| `compileOnly(files("..."))` | 一行 | 编译时序问题 |
| "加更多 androidx" | 一行 | 内部 API 不公开 |
| "复制源码" | 一行 | 违反规则 P |
| "降级 AGP" | 一行 | 破坏性改动 |

### 7.2 不要重复尝试失败方案

**做法**: 每次尝试前先看 `docs/issues/2026-07-28-server-flags-debug-session.md` §5.1（已尝试清单）。

### 7.3 错误数可能因环境波动

**现象**: 同一命令两次跑结果差几个错误

**原因**: KAPT/Gradle 缓存、并行编译顺序

**应对**: 错误数只作诊断；需要比较同一问题时再保持相同参数重跑，不把数量变化作为提交或回滚门槛。

---

## 8. 文档陷阱

### 8.1 文档写"0 错误"或"构建成功"但没有证据

**避免**: 只有在需要作出对应结论时才运行能够证明该结论的命令，并记录退出码/结果。**不要求每次 commit 都跑 FULL build**；未运行时明确写“未运行”。

### 8.2 文档没记录 false positive

**避免**: 错误数统计前手动看 5-10 个错误样本，避免 grep 误匹配

### 8.3 计划文档 vs 实际状态不同步

**避免**: 在阶段里程碑、架构决策、交接或状态发生实质变化时同步文档；不要求每个 commit 机械更新所有计划文件。

---

## 9. 资源类陷阱

### 9.1 AOSP 资源文件不能改

**规则**: AOSP `res/`、`res-keyguard/`、`res-product/` 是只读镜像

**例外**: AOSP 合并冲突时手动去重

### 9.2 AAPT2 不支持 product 属性

**解决**: 把 product 资源合并到主 res 目录

### 9.3 platform key 用 pk8 + x509.pem

**解决**: 用 openssl + keytool 转换为 JKS
```bash
openssl pkcs8 -inform DER -nocrypt -in platform.pk8 -out platform.pem
openssl pkcs12 -export -in x509.pem -inkey platform.pem -out platform.p12 \
  -password pass:android -name AndroidDebugKey
keytool -importkeystore -deststorepass android -destkeystore platform.keystore \
  -srckeystore platform.p12 -srcstoretype PKCS12 -srcstorepass android
```

**注意**: `keytool` 把 alias 转小写，所以 `keyAlias=androiddebugkey`

---

## 10. 行为类陷阱

### 10.1 AI Agent 持续产出 stub

**现象**: 紧急情况下 AI 倾向创建 stub 类

**应对**: 看到 `class Foo { ... }` 在 `SystemUI-core/src/com/android/...` 下立即 grep `TODO: temporary stub`

### 10.2 AI Agent 跳过文档

**现象**: "先写代码，文档稍后补"

**应对**: 规则 D 强制要求文档先于代码

### 10.3 AI Agent 改 res/ 资源

**现象**: "为了编译通过" 改 image 或 xml

**应对**: 看到 `git diff res/` 立即回滚

---

## 11. 必读历史踩坑

- `2026-07-22-stub-cleanup-and-deps.md` - 删除 v1 stub 的过程
- `2026-07-22-sdk-android-jar-merge.md` - 合并 SDK 上的问题
- `2026-07-22-framework-jar-replace-and-stubs.md` - framework.jar 替换
- `2026-07-23-server-notification-flags-unresolvable.md` - 上一阶段 server-notification
- `2026-07-28-server-flags-debug-session.md` - 本次 session

---

## 12. 配置模板速查

### 12.1 加 aconfig Flag 依赖（历史模板；机制仍有效）

> 本节为历史模板：notification flags 原经本地 Maven 坐标引入，Task 034 后改为
> `libs/notification-flags.jar` 直接 JAR（当前坐标/位置以 `docs/CURRENT_STATE.md` 为准）。
> 仍然有效的机制：**内部 flags jar 必须排在 framework.jar 之前**（顺序即优先级），
> 否则 framework.jar 的同名 stub 会遮蔽真实 flags 类。

```kotlin
// build.gradle.kts (root)
val notificationFlagsJar = file("${rootProject.projectDir}/libs/notification-flags.jar")
tasks.withType<JavaCompile>().configureEach {
    classpath = files(notificationFlagsJar) + classpath
}
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    libraries.from(notificationFlagsJar)
    libraries.from(internalFlagsJars)
    libraries.from(frameworkJar)
}
```

### 12.2 加新 module 的 7 步

```bash
# 1. 创建目录
mkdir -p SystemUI-new/{src/main/java,src/main/AndroidManifest.xml}
touch SystemUI-new/.gitkeep

# 2. include 到 settings.gradle.kts
include(":SystemUI-new")

# 3. 添加 plugins
cat > SystemUI-new/build.gradle.kts <<EOF
plugins {
    alias(libs.plugins.android.library)
}
android {
    namespace = "com.android.systemui.new"
    compileSdkPreview = "SysUISdk"
}
EOF

# 4. 复制源码
cp -r /home/conv/myspace/aosp/.../new/* SystemUI-new/src/main/java/

# 5. 添加依赖
echo 'implementation(project(":SystemUI-new"))' >> SystemUI-core/build.gradle.kts

# 6. 跑 build 验证
./gradlew :SystemUI-new:compileDebugJavaWithJavac

# 7. 文档
echo "docs/issues/YYYY-MM-DD-add-new-module.md"
```

---

## 13. 构建与产物纪律（2026-08-20 收录，长期有效）

### 13.1 SysUISdk 只能经 `tools/build_sysuisdk.py --apply` 修改

SysUISdk 是可从 tracked inputs 从零重建的自定义 SDK；任何修补（framework 类、framework-res、framework.aidl）都必须走受控脚本入口 `python3 tools/build_sysuisdk.py --apply`，禁止手工改 `android-SysUISdk/` 下的产物（不可重现、无法审计）。

### 13.2 Soong `static_libs` 必须进入 program/packaging closure

Soong 的 `static_libs` 传递依赖**不会**自动出现在 Gradle compile classpath，更不会自动进 R8 program closure。每个 AAR/JAR 落地时必须核对其 `Android.bp` `static_libs` 闭包（Task 7 八组 javac 根因、R8 Batch 1–4C 全部源于此）。CHARTER Part 3 决策树是判定入口。

### 13.3 本地 AAR 内容变化必须升坐标

`libs/maven/` 下的本地 Maven AAR 一旦内容（类集/资源）变化，必须升 version（如 iconloader/WM-Shell 1.0.0→1.0.1 并退役旧版），否则 Gradle 缓存与消费方无法感知变化，产生难排查的陈旧产物问题。

### 13.4 真实 R8 missing refs 不得用宽泛 keep/`-dontwarn` 掩盖

Release R8 的 missing refs 是真实 closure 缺口的信号；用宽泛 `-keep`/`-dontwarn` 压掉只会把运行时 NoClassDefFoundError 推迟到设备上。正解是逐批补齐真实产物（Batches 1–4C 的做法），platform/build classpath 桥接类只允许窄域处理。

### 13.5 Debug 每批硬门禁

每个改动批次必须保持 `:app:assembleDebug` BUILD SUCCESSFUL（用户 2026-08-20 强制）；不允许以"先修 release"为由让 debug 基线失败。

### 13.6 全系统只允许一个 Gradle build

构建机无法支撑两个并发 SystemUI Gradle 构建：worker 在自己 worktree 内拥有构建；reviewer 只做静态验证（禁止 Gradle）；architect 的 main fresh 验证在 worker/reviewer 之后串行执行（CHARTER Part 4）。

---

**下一步**: 阅读 `docs/architecture/STAGE2-3-RESEARCH-LOG.md` 深入调研。

## 14. 设备/模拟器部署类踩坑（2026-08-25 收录）

### 14.1 `adb enable-verity` 会拆掉 adb-remount overlay，部署的 APK 静默回退 stock

**现象**: 按 task 054/055 流程把 Debug APK 部署到 `/system_ext/priv-app/SystemUI/` 并验证 sha256 正确后，想"恢复原状"执行了 `adb enable-verity` + reboot；重启后设备上的 APK 变回 stock（36,378,017 字节 / sha `dd1ff45a…`），部署产物凭空消失，无任何报错。

**根因**: `adb disable-verity` + remount 走的是 overlayfs；`enable-verity` 重启后 dm-verity 重新启用，overlay 被整体拆除，底层只读分区原样暴露。部署态与 verity enabled 是**互斥**的两种终态。

**结论/纪律**:
- 采用 overlay 部署路线的设备，**verity 必须保持 disabled**，直到你主动决定放弃部署产物
- reboot 本身不拆 overlay（overlay 跨重启存活已实测），**只有 enable-verity 才拆**
- 每次 reboot 后 overlay 挂载可能需重新 `su 0 mount -o remount,rw /system_ext`（视镜像而定），但 enable-verity 是销毁性的，两者别混淆

### 14.2 设备上 toybox `cp` 在 ENOSPC 时静默截断，必须 sha256 二次校验

**现象**: task 058 部署时 scratch 空间将满，staged `cp` 返回成功但目标 APK 被截断（字节数不足），后续流程若无校验会把残缺 APK 当成功部署。

**根因**: 设备端 toybox 的 `cp` 对写失败的兜底行为是截断而非报错退出。

**结论/纪律（已写入部署规程）**:
1. staging（`/data/local/tmp`）→ 同目录临时名 cp → `sync` → 原子 `mv`（同分区 rename）
2. **mv 之后立刻 `su 0 sha256sum` 对比本地构建产物**，不一致 = 失败重来
3. 空间不足时先 `am force-stop` + `kill -9` SystemUI 释放句柄，再删残缺文件
