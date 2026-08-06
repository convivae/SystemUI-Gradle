# 参考项目四大机制的来龙去脉（知其然知其所以然）

**日期**: 2026-08-06
**参考项目**: `CarSystemUIGradle`（同用户私有项目，本项目的参考实现）
**参考文档**: `CarSystemUIGradle/docs/GRADLE_MIGRATION.md`、`DEPENDENCIES.md`、`README.md`
**目的**: 记录参考项目里**本地 Maven 仓库 / 自定义 SDK Platform / framework.jar / Python 脚本**四个机制各自**解决的问题**和**演进过程**，作为本项目同类决策的依据。知其然，更要知其所以然。

---

## 0. 一句话总览

| 机制 | 解决的问题 | 本质 |
|---|---|---|
| **本地 Maven 仓库** | AAR 直接引入（flatDir）资源合并不完整、R 类不生成 | **AAR 的交付载体**（仓里全是 AAR），借 Gradle/AAPT2 标准资源合并去重 |
| **自定义 SDK Platform** | `@*android:` 私有资源引用，标准 SDK 的 resources.arsc 与设备 framework ID 不匹配 → 运行时崩溃 | 替换标准 `android.jar` 的**资源部分**（resources.arsc + res/）为设备 framework-res.apk |
| **framework.jar** | 标准 SDK 不含 @hide API 和内部类签名 | compileOnly 的 AOSP `classes-header.jar`，**只提供代码签名**，不打包 |
| **Python 脚本 gen_aar_maven** | 多个 AAR 之间 / AAR 与源码之间资源/类冲突 | 从 AOSP out 提取 JAR + 合并 res + 清理冲突类 → 打成 AAR 装进本地 Maven 仓 |

> **关键区分**：本地 Maven 仓（装 AAR，解决 AAR 资源合并）≠ 公网 Maven（google/mavenCentral，装上游第三方库）。两者都叫 "Maven" 但是完全不同的用途。

---

## 1. 本地 Maven 仓库：为什么不用 flatDir

### 1.1 问题（参考项目 GRADLE_MIGRATION.md 问题七）
AOSP 的资源分散在多个依赖库（SettingsLib / WindowManager-Shell / iconloader 等）各自的 `res/`。bp 编译自动合并所有资源，但 Gradle 需要手动配置。编译时报一堆 `R.drawable.*` / `R.color.*` 找不到。

### 1.2 演进（三方案）
1. **方案一：手动复制资源到 res-gradle** ❌ 不推荐 — 易遗漏、与 AAR 资源冲突、不系统化
2. **方案二：flatDir 引入 AAR** ❌ 失败 — `flatDir` 引入的 AAR **资源合并不完整**：资源虽然在 `merged.dir` 里，但 **R 文件没有正确生成**
3. **方案三：本地 Maven 仓库** ✅ 最终采用 — Gradle 官方推荐方式，**完整的资源合并支持**

### 1.3 结论
- **本地 Maven 仓 = AAR 的交付载体**，仓里装的全是 AAR（`SettingsLib-1.0.0.aar` 等）
- 用本地 Maven 而非 flatDir，是因为 flatDir **不能正确处理 AAR 的资源合并**（R 类不生成）
- 本地 Maven 仓可提交 git，团队成员无需重新生成
- 配置：
  ```kotlin
  // settings.gradle.kts
  dependencyResolutionManagement {
      repositories {
          maven { url = uri("${rootProject.projectDir}/libs/maven") }  // 本地 Maven 仓（装 AAR）
          google(); mavenCentral()  // 公网 Maven（装上游第三方库）
      }
  }
  ```

### 1.4 本项目现状
`libs/maven/` 下有 SettingsLib / iconloader / WindowManager-Shell / WifiTrackerLib / SystemUISharedLib / server-notification-flags 等。结构与参考项目一致。

---

## 2. 自定义 SDK Platform：为什么标准 SDK 不行

### 2.1 问题（参考项目问题二十四/二十五/二十六）
Gradle 编译的 APK 在设备运行时崩溃：
```
UnsupportedOperationException: Can't convert value at index 2 to dimension: type=0x1
```

### 2.2 根本原因
- SystemUI 用 `@*android:style/Theme.DeviceDefault.SystemUI` 这种 **`@*android:` 私有 framework 资源引用**
- AAPT2 用**标准 SDK `android.jar` 的 `resources.arsc`** 解析这些私有引用 → 资源 ID 是标准 AOSP 的
- 但设备运行时用的是**厂商定制 framework**，私有资源 ID 被厂商改过 → 编译时 ID 与运行时 ID 不匹配 → `TypedArray.getDimension()` 失败
- **bp 编译没问题**：bp 用 `platform_apis: true`，链接 AOSP 完整 framework（含正确私有资源 ID）

### 2.3 演进（三方案）
1. **`-I framework-res.apk`** ❌ 失败 — 只影响 **AAPT2 资源编译阶段**，让 AAPT2 链接正确 framework 资源；但 **Java/Kotlin 代码编译仍用 `android.jar` 的资源 ID 常量**
2. **framework.jar 作 bootclasspath** ❌ 失败 — framework.jar 是**代码**（classes），不含资源（resources.arsc），解决不了资源 ID 问题（详见 §3）
3. **创建自定义 SDK Platform** ✅ 最终采用 — 替换 `android.jar` 的**资源部分**为设备 framework-res.apk

### 2.4 自定义 SDK 怎么生成（参考项目问题二十六）
```bash
# 1. 复制标准 SDK platform
cp -r $ANDROID_HOME/platforms/android-32 $ANDROID_HOME/platforms/android-JdJkcSdk

# 2. 从设备提取 framework-res.apk
adb pull /system/framework/framework-res.apk libs/framework-res.apk

# 3. 用 framework-res.apk 的 resources.arsc + res/ 替换 android.jar 的资源部分
unzip libs/framework-res.apk resources.arsc -d /tmp/device_res/
cd /tmp/device_res && zip -u $ANDROID_HOME/platforms/android-JdJkcSdk/android.jar resources.arsc
unzip libs/framework-res.apk 'res/*' -d /tmp/res_device/
cd /tmp/res_device && zip -r $ANDROID_HOME/platforms/android-JdJkcSdk/android.jar res/

# 4. 改 package.xml 的 localPackage path（SDK Manager 靠它识别）
# 5. Gradle: compileSdkPreview = "JdJkcSdk"
```
> 注意：`compileSdkPreview` 只接受字母开头的名称。

### 2.5 本项目现状
- 自定义 SDK：`compileSdkPreview = "SysUISdk"`，位于 `/home/conv/Android/Sdk/platforms/android-SysUISdk/`
- 有 `android.jar`（已改）+ `android.jar.orig`（原始备份）+ `framework.aidl`（补了隐藏接口）
- `tools/install_sdk.py` 目前只**补 framework.aidl 的隐藏接口声明**（如 `android.os.IRemoteCallback`、`com.android.internal.util.ScreenshotRequest`），不碰 android.jar 资源部分
- **自定义 SDK 可通过 framework.jar / framework-res.apk / framework.aidl 三处调整**（用户 2026-08-06 明确）：
  - 改 `android.jar` 资源部分（resources.arsc + res/）→ 解决私有资源 ID（参考项目问题二十六做法）
  - 改 `framework.aidl` → 补 framework @hide 接口/parcelable 声明（本项目 `install_sdk.py` 做法）
  - `framework.jar` 作 compileOnly/bootclasspath → 提供 @hide API 代码签名（见 §3）

---

## 3. framework.jar：提供 @hide API 代码签名

### 3.1 是什么
- AOSP 编译输出的 `classes-header.jar`（`out/soong/.intermediates/frameworks/base/framework/.../turbine-combined/framework.jar`）
- **compileOnly**，提供标准 SDK 不含的 @hide API 和内部类签名
- 编译时用，**不打包进 APK**（运行时由系统 framework 提供）

### 3.2 解决什么
- 标准 SDK `android.jar` 只含 public API
- SystemUI 源码大量调用 @hide 方法（如 `Thread.getUncaughtExceptionPreHandler()`）和内部类
- framework.jar 提供这些签名让编译通过

### 3.3 不能解决什么（重要）
- **framework.jar 解决不了私有资源 ID 问题**（参考项目问题二十五已证伪）——它是代码不含资源
- **framework.jar 不能加到 KotlinCompile.libraries**（本项目 2026-07-30 发现）——会污染 Compose runtime 的 inline metadata 解析，导致 `Couldn't inline method call: CompositionLocal.getCurrent()` 等 IR lowering 错误
- 故本项目 `build.gradle.kts` 只把 framework.jar 加到 `JavaCompile.bootstrapClasspath` + `classpath`，**不加到 KotlinCompile**

### 3.4 参考项目的另一条路：反射
参考项目问题十对部分隐藏 API（`Thread.getUncaughtExceptionPreHandler`）用**反射调用**绕过，而非 framework.jar。两种思路：
- framework.jar：编译时签名可见，代码直接调用（本项目主要走这条）
- 反射：编译时无签名，运行时反射调用（参考项目部分场景）

### 3.5 关键技巧
内部 flags jar（systemui-flags.jar / monet.jar / notification-flags.jar）必须放在 framework.jar **之前**，否则 framework.jar 的同名 stub 会遮蔽真实 flags 类。

---

## 4. Python 脚本 gen_aar_maven：解决 AAR 间资源/类冲突

### 4.1 是什么
- 从 AOSP `out/soong/.intermediates/` 提取 JAR + 合并源码目录 res + 清理冲突类 → 打成 AAR → 装进本地 Maven 仓
- 清理的冲突类：AndroidX、Framework 内部类、R 类等（防止与 maven 版本依赖重复）

### 4.2 何时用（用户 2026-08-06 明确）
- **现在先不要用**。先把 AAR **直接导入**，观察：
  - 不同 AAR 之间有没有冲突
  - AAR 与 jar 之间有没有冲突
  - 依赖之间有没有冲突
- **只有出现冲突时**，才用脚本生成本地 Maven 仓 AAR 解决冲突
- 具体遇到问题用脚本时，参考 `CarSystemUIGradle` 的处理方式

### 4.3 本项目现状（2026-08-06）
- `tools/gen_aar_maven.py` 有一版**未提交的改写**（issue `2026-07-31-gen_aar_maven-rewrite.md`），试图把 `busybox/R.jar` 的 R 类合并进 aar 的 classes.jar
- **该改写基于错误假设**（以为 AGP 不为 prebuilt aar 生成 R 类），实际 AGP 会从 aar 的 res/R.txt 生成 R.class，导致 classes.jar 的 R.class 与 AGP 生成的 R.class 撞车 → build 在 AAR transform 阶段失败
- **结论**：这版改写应回滚，恢复 `clean_jar` 删 R.class 的行为；原本的 `Unresolved reference 'R'` 需另做根因诊断（很可能是 nonTransitiveRClass / namespace / R 字段可见性，参考项目问题八就是 nonTransitiveRClass）

---

## 5. nonTransitiveRClass=false：为什么

### 5.1 问题（参考项目问题八）
新版 AGP 默认 `android.nonTransitiveRClass=true`（非传递性 R 类）：
- 每个模块只能访问自己定义的资源
- 依赖库的资源不会合并到当前模块的 R 类
- 需用依赖库的 R 类（如 `com.android.settingslib.R`）访问其资源

但 SystemUI 源码直接用 `R.xxx` 访问所有资源（包括依赖库的）。

### 5.2 解决
```properties
android.nonTransitiveRClass=false
```
让依赖库资源传递合并进 app 的 R（`com.android.systemui.R` 含所有依赖资源），对齐 AOSP 源码里的 `R.xxx` 引用方式。

### 5.3 本项目现状
`gradle.properties` 已设 `android.nonTransitiveRClass=false`。

---

## 6. 当前优先级重排（用户 2026-08-06 明确）

**错误数只作为诊断信息；首要目标是把整个框架搭对**（源码/jar/AAR 的来源和边界正确）。项目是否前进不以单次错误数升降判断。

### 6.1 目标 1：AOSP SystemUI 源码对齐审查（脚本）
- a. 哪些代码在 AOSP SystemUI 里有，但我们本地没源码引入（**缺的**）
- b. 哪些代码我们本地引入了，但 AOSP 里没有（**多的**）
- 即规则 C（不漏不多）的自动化校验

### 6.2 目标 2：源码引入边界
- a. **只有 AOSP SystemUI 目录下的代码可源码引入**
- b. 其他代码一律 jar/aar 引入（规则 F）

### 6.3 目标 3：上游第三方库
- androidx / Compose 等上游库**直接用谷歌原生 Maven 依赖**（公网 Maven），尽量不用 AAR/jar
- 只有实在解决不了的问题，记录下来，看 AOSP bp 怎么解决，讨论后再做

### 6.4 清理 1：删无用/违规 jar/aar
- a. 删用不到的 jar/aar
- b. 删不符合开发规则的 jar/aar
- c. 删以前生成的旧 jar/aar

### 6.5 清理 2：删违规源码引入
- a. 删不允许源码引入的内容（非 SystemUI 目录的代码）
- b. 删做了源码引入但不该引入的内容

---

## 7. 参考
- `CarSystemUIGradle/docs/GRADLE_MIGRATION.md` — 问题七（本地 Maven）、问题八（nonTransitiveRClass）、问题十（隐藏 API 反射）、问题二十四/二十五/二十六（自定义 SDK）
- `CarSystemUIGradle/docs/DEPENDENCIES.md` — 依赖清单 + "为什么用本地 Maven 而非 flatDir"
- `CarSystemUIGradle/docs/README.md` — 自定义 SDK 用途
- 本项目 `AGENTS.md` §1.1/§1.5/§2.4（本次同步更新表述）
