# SystemUI-Gradle 踩坑记录 (PITFALLS.md)

> **目的**: 记录所有"看似简单但实际不行"的方案，帮助下个 AI 避免重复失败。
> **格式**: 现象 → 尝试 → 失败原因 → 替代方案

---

## 1. 环境类踩坑

### 1.1 AGP 版本与 Kotlin 编译器版本不同

**现象**: 项目声明 `kotlin("android") = "2.1.0"`，但 AGP 9.2 内部嵌入 `kotlin-compiler-embeddable 2.2.10`。编译时实际使用 2.2.10。

**错误**:
- `Unresolved reference` 出现在 valid jar 中的方法
- 独立 kotlin("jvm") 项目用同样 jar 编译成功

**根因**: AGP 9.2 故意用比 plugin 更新的 Kotlin 编译器。

**绕道**:
- 升级项目 plugin 到 2.2.10: plugin 冲突
- 降级 AGP: 风险高，需要全部重测
- 接受现状: 锁定 2.1.0，但 AGP 仍用 2.2.10

### 1.2 KAPT 1.9+ 与 Gradle 9.5 不兼容

**现象**: 启用 KAPT 后报 "IR fake override builder 内部错误"

**根因**: KAPT 1.9+ 引入了 IR backend，但与 Gradle 9.5 的 class 文件结构冲突

**当前**:
```kotlin
// SystemUI-core/build.gradle.kts
// id("kotlin-kapt")  // 临时禁用
// kapt(libs.dagger.compiler)  // 临时禁用
```

**后果**: Dagger 不会生成代码，所有 `@Inject` 注入失败

**替代方案**:
- KSP (推荐)
- 降级 AGP 到 8.x
- 显式 Provider

### 1.3 SysUISdk 是 preview SDK

**现象**: AGP 警告 "compile SDK preview version 'SysUISdk' has not been tested"

**根因**: AGP 9.2 官方测到 SDK 37，`SysUISdk` 是我们自定义

**后果**: 编译时 SDK 不识别，但 `@hide` API 仍能通过 framework.jar 引入

**绕道**: 忽略（这是已知）

---

## 2. aconfig Flags 类踩坑

### 2.1 `libs/server-notification-flags.jar` 是空 jar

**现象**: 
```bash
$ unzip -l libs/server-notification-flags.jar
(empty)
```

**真实位置**: `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`

**根因**: 历史拷贝错，或 git LFS 丢失。文件名误导。

**正确做法**:
```kotlin
// build.gradle.kts (root)
val serverNotificationFlagsJar = file("${rootProject.projectDir}/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar")
```

### 2.2 [已证伪 2026-07-28] Kotlin 2.2.10 看不到 aconfig Flags `@UnsupportedAppUsage` 注解的类

> ⚠️ **本条推测已被证伪**。真正根因：源码 stub `com/android/server/notification/Flags.kt`
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
- `com.android.systemui.Flags` (systemui-flags.jar, 53220 bytes) → ✅ 工作
- `com.android.server.notification.Flags` (notification-flags.jar, 6285 bytes) → ❌ unresolved

**差异**:
- 包名: `com.android.systemui.*` vs `com.android.server.*`
- 类大小: 53220 vs 6285 字节

**可能根因**: 
- Kotlin Android plugin 对 `com.android.systemui.*` namespace 特殊处理
- 或者大类的某个方法签名不同
- 或者 `@UnsupportedAppUsage` 在不同类的处理方式不同

> ⚠️ 以上全部错。真正差异见 §2.4。

### 2.4 ✅ [真正根因 2026-07-28] 源码 stub 遮蔽 jar 类

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

**当前**: 源码**未在 git 中**（`SystemUI-core/src/com/android/compose/animation/scene/*` 显示 `??`），但被 `srcDir("src")` 包含，会被编译。

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

**当前**: 直接 cp 完整版，不裁剪。

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

### 12.1 加 aconfig Flag 依赖的完整流程

```toml
# gradle/libs.versions.toml
android-server-notification-flags = { group = "com.android.server", name = "notification-flags", version = "1.0.0" }
```

```kotlin
// SystemUI-core/build.gradle.kts
implementation(libs.android.server.notification.flags)
```

```kotlin
// build.gradle.kts (root)
val serverNotificationFlagsJar = file("${rootProject.projectDir}/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar")
tasks.withType<JavaCompile>().configureEach {
    classpath = files(serverNotificationFlagsJar) + classpath
}
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    libraries.from(serverNotificationFlagsJar)
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

**下一步**: 阅读 `docs/architecture/STAGE2-3-RESEARCH-LOG.md` 深入调研。
