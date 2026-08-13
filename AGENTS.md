# SystemUI-Gradle 项目开发规则 (AGENTS.md)

> 这是本项目的全局指令。所有 AI Agent 在本项目中工作时必须遵守此文件。
> 用户指令优先级最高，本文件次之，最后是默认系统提示。
> **新 AI Agent 请先读 `docs/HANDOFF.md` 取得 5 分钟概要，再读本文件了解完整规则。**

---

## 〇、用户指令优先级

1. **用户明确指令** (用户在 chat 中的话) — 最高
2. **AGENTS.md + docs/HANDOFF.md** — 次之
3. **默认系统提示** — 最低

冲突时按顺序适用。例如：用户说"用 stub" → 听用户的；用户没说 → 遵守规则 P。

---

## 〇.二、ADR (架构决策记录)

项目所有**架构级决策**写在 [`docs/adr/`](./docs/adr/)。引用文件：

- **ADR 0001** `aosp-res-via-local-maven.md` — AOSP res 缺失处理优先级：AAR 先直接引入，确认冲突后才用 local Maven
- **ADR 0002** `tools-scripts-only-python.md` — `tools/` 下脚本一律 Python，禁止 .sh
- **ADR 0003** `app-module-aligns-aosp-bp.md` — 模块划分/依赖/入口类位置严格按 AOSP `Android.bp`
- **ADR 0004** `conv-markup-and-alignment-discipline.md` — AOSP 源码改动用 CONV 标记追溯；对齐工具 strict 不卡 MODIFIED，靠人工对账

写 ADR 的判定：决策 **难以反转 + 没有上下文会令人困惑 + 有真正权衡**。

---

## 一、依赖引入规则 (用户明确要求，2026-07-22)

> **规则 P (Project Rule)**: 不允许使用 stub 技术。

### 1.1 允许的三种依赖形态（用户明确更正，2026-08-06）

> **Maven 不是第四种依赖产物。**
> 本项目 `libs/maven/` 是 **AAR 的本地 Maven 交付仓库**；仓内应是 AAR + POM，
> 目的是在直接引入 AAR 发生资源/依赖冲突时，借 Gradle/AAPT2 的标准依赖解析完成资源合并。
> 公网 Maven（Google Maven / Maven Central）则是上游库的获取渠道，也不是新的产物类型。

| 形态 | 何时用 | 示例 |
|------|--------|------|
| 源码依赖 | **仅** AOSP `frameworks/base/packages/SystemUI/` 内的 SystemUI 自有代码 | `implementation(project(":SystemUI-shared"))` |
| jar | SystemUI 之外的纯代码 AOSP 产物、aconfig 生成类、无资源库 | `compileOnly(files("libs/framework.jar"))` |
| aar | SystemUI 之外且包含资源的 AOSP 库；**先直接引入**，出现冲突后才放入本地 Maven 仓 | `implementation(files("libs/<name>.aar"))`；冲突后 `implementation(libs.systemui.settingslib)`（catalog 统一管理，见 §3.2） |

### 1.2 禁止

- **不允许创建 *.java stub 类**只为让 IDE/编译器满意
- **不允许私自创建资源文件** (res/ 下的任何 .xml/.png/.9.png 等)
- **不允许创建 *.kt stub 文件**（同 Java）
- 所有资源文件必须来自：AOSP 源码、AAR（直接或由本地 Maven 仓交付）、或 Google/MavenCentral 上游依赖的原始产物
- 退路：如果所有方案都失败，**临时**用 stub 必须明显标注 `// TODO: temporary stub, replace with real impl` 并记录到 `docs/issues/`

### 1.3 允许

- 复制 AOSP SystemUI 源码目录作为 module（例如 `:SystemUI-monet`）
- 从 AOSP 编译产物提取 *.class 打包为 jar
- AOSP 非 SystemUI 纯代码产物以 jar 放入 `libs/`
- 含资源的 AOSP 库先以 AAR 直接引入；确认发生资源/依赖冲突后，再经脚本安装为 `libs/maven/` 下的本地 Maven AAR
- 复制 AOSP SystemUI 的 res 目录（例如 `res-keyguard/`, `res-product/`），保持文件集与内容 1:1
- 通过 Gradle `sourceSets`/模块配置消费原始资源；**不得**为适配 AAPT2 擅自修改、去重、合并或重写 AOSP SystemUI 资源文件。若构建系统无法直接消费，按规则 H 停止并询问用户

### 1.4 参考实现

- `CarSystemUIGradle` 项目（同用户私有项目）是参考实现
- 参考文档：`CarSystemUIGradle/docs/GRADLE_MIGRATION.md`、`DEPENDENCIES.md`、`README.md`
- `tools/install_aar_to_maven.py` 负责把 `libs/aars/*.aar` 安装为 `libs/maven/` 下的本地 Maven AAR（AAR + POM 骨架）；`tools/gen_aar_maven.py` 是旧脚本（R.jar 合并失败实验，已废弃）
- 关键资源：参考 `CarSystemUIGradle/SystemUI-core/build.gradle.kts` 的依赖引入方式
- 本项目对参考项目机制的“为什么”记录：`docs/architecture/2026-08-06-reference-project-rationale.md`

### 1.5 源码 vs jar 判定原则 (用户明确要求，2026-07-29)

> **规则 S (Source-first for SystemUI)**: AOSP `packages/SystemUI/` 下 **SystemUI 自有的代码**
> 一律**源码复制**做**源码依赖**（不用 jar）；**SystemUI 之外的模块**按下面三层策略引入。

依赖分三层（2026-07-29 初定，2026-08-06 用户细化交付方式）：

| 层 | 是什么 | 引入方式 | 例子 |
|---|---|---|---|
| ① SystemUI 自有代码 | soong 模块定义在 `frameworks/base/packages/SystemUI/**/Android.bp` 内 | **源码复制**（source module） | shared、animation、customization、log、common、unfold、kairos、compose/core、compose/scene、plugin、monet |
| ② AOSP 特有产物（非 SystemUI 源码） | 公网 Maven 没有 / 被 AOSP 改过 / aconfig 生成 | 无资源用 **jar**；含资源用 **AAR，先直接引入**；确认冲突后才改成本地 Maven AAR | framework.jar、android.car.jar、SettingsLib、WindowManager-Shell、WifiTrackerLib、iconloader、systemui/notification/settingslib flags |
| ③ 标准第三方上游库 | Google Maven / Maven Central 直接提供的通用库 | **直接使用官方坐标**，像普通 Android app 一样；不要下载后再手工打 jar/aar | androidx.*、Compose、kotlinx-coroutines、dagger2、material、lottie、jsr305/jsr330 |

- 判定 ①：看 soong 模块定义是否位于 `frameworks/base/packages/SystemUI/**/Android.bp`
- 判定 ②/③：能在 Google Maven / Maven Central 找到且未被 AOSP fork → ③ 官方坐标；否则 → ② AOSP jar/aar
- **Maven 是仓库/交付渠道，不是第四种产物形式**：
  - `libs/maven/` = 本项目的**本地 AAR 仓库**，仓内应是 AAR + POM；
  - `google()` / `mavenCentral()` = 上游第三方库的公网获取渠道。
- **② 里 jar vs AAR 的区别是是否含资源**：无资源用 jar；含资源用 AAR。
- **AAR 先直接引入**：先验证 AAR-AAR、AAR-jar 及传递依赖是否冲突；只有确认无冲突后，才用 `tools/install_aar_to_maven.py` 安装为 `libs/maven/` 下的本地 Maven AAR，并在 `libs.versions.toml` 声明 catalog alias 统一管理。
- **③ 上游库优先官方依赖**：androidx/Compose 等尽量不使用本地 jar/aar；如果官方版本无法满足 AOSP 源码，先记录问题、核对 `Android.bp` 的解决方式，再与用户讨论，禁止擅自打包替代。
- 若某模块同时有源码和 prebuilt jar/aar 会重复类：源码化时**必须移除对应 prebuilt**
- 完整调研见 `docs/architecture/2026-07-29-systemui-module-source-vs-jar.md` 和 `docs/architecture/2026-08-06-reference-project-rationale.md`
- SystemUI 自有源码应按 AOSP 完整复制；源码补全、依赖切换或结构校准造成的错误数变化只作为诊断信息，不构成回滚或审批条件。

### 1.6 SystemUI 源码/aidl/res 必须"不漏不多"（用户明确要求，2026-07-29）

> **规则 C (Complete & Exact)**: AOSP `packages/SystemUI/` 下与 SystemUI 相关的**代码、aidl、res 资源
> 必须全部复制过来**——**不能有漏的，也不能有多的**（即与 AOSP 对应目录逐一对齐，多余文件要删）。

- 校验方法：对比 AOSP `packages/SystemUI/{src,**/*.aidl,res*}` 与项目对应目录的文件集差异。
- "多的" = 项目里有、AOSP 没有的文件（如早期手写的 stub 副本），必须删除。
- "漏的" = AOSP 有、项目缺的文件，必须补齐。

### 1.7 framework（非 SystemUI）代码严禁源码复制（用户明确要求，2026-07-29）

> **规则 F (Framework via SDK/jar only)**: **只要不是 SystemUI 内部的代码，一律不许源码复制**，
> 只能通过 **jar / AAR** 引入（AAR 先直接引入，确认冲突后才放本地 Maven 仓）；若 **SysUISdk 里缺**
> framework 隐藏类、资源或 AIDL 声明，应**重新生成 / 补 SysUISdk 或更新 framework.jar**，
> 而不是把 framework 源码拷进 SystemUI 模块。

- 典型：SystemUI aidl `import android.os.IRemoteCallback`（framework @hide 接口），
  public `framework.aidl` 缺 → **在 SysUISdk 的 `framework.aidl` 追加 `interface X;` 声明**
  （由 `tools/install_sdk.py` 幂等完成），**不是**把 `IRemoteCallback.aidl` 拷进 `SystemUI-core/`。
- SysUISdk 不是不可变 SDK：可使用 AOSP `framework.jar` 补代码 API、使用 `framework-res.apk` 补私有资源、修改 `framework.aidl` 补 AIDL 声明；详见 §2.4。
- SysUISdk 生成/补丁方法参考 `CarSystemUIGradle/docs/GRADLE_MIGRATION.md` 问题二十四至二十六，以及 `docs/architecture/2026-08-06-reference-project-rationale.md`。
- 反面教训（2026-07-29）：一度把 framework `IRemoteCallback.aidl` 源码复制进 core → 被用户否决，
  改为补 SysUISdk。

### 1.8 res 缺失处理优先级（用户明确要求，2026-07-29）

> **规则 R (Res provenance)**: 资源文件 (res/) 一律来自 **AOSP 源码 / AAR（直接或本地 Maven 仓交付）/ Google 或 MavenCentral 上游原始依赖**，禁止凭空生成。

res 缺失时按以下顺序处理（详见 `docs/adr/0001-aosp-res-via-local-maven.md`）：

1. **AOSP 源码**（规则 S 优先）：SystemUI 自有的 res 在 `SystemUI-res/res{, -keyguard, -product}/`，
   必须与 AOSP 1:1 对齐（规则 C 不漏不多）
2. **AOSP 编译产物（非 SystemUI）**：
   - 无 res 的纯代码库 → `libs/<name>.jar`
   - 有 res 的库 → **先直接引入 AAR**，验证 AAR-AAR、AAR-jar 和传递依赖是否冲突
   - 只有确认直接 AAR 存在资源/类/依赖冲突后，才经 `tools/install_aar_to_maven.py` 安装为 `libs/maven/` 下的本地 Maven AAR，并在 `settings.gradle.kts` 配置本地仓库、在 `libs.versions.toml` 声明 catalog alias
3. **公网官方依赖**（规则 ③）：androidx/Compose/material/lottie 等直接使用 `google()` / `mavenCentral()` 官方坐标

**绝对禁止** Agent 在 res/ 下生成同名资源绕过编译错误。

> **规则 R 升级（2026-08-07，ADR 0004）**：规则 R 细化为“禁止**无 CONV 标记**地擅改 res/src”。AOSP 源码在 Gradle 无法直接消费时（如 `product="tv"` 资源变体），经用户授权后可用 `CONV_ADD`/`CONV_DEL`/`CONV_MOD` + `BEGIN`/`END` 块标记注释掉原内容（不删除字节），使改动可追溯可撤回。必须先跑 `check_source_alignment.py` 达 MISSING/MISPLACED/EXTRA 全 0 后才允许打标。工具 `--strict` 不卡 MODIFIED，“是否擅改”靠 MODIFIED 清单与 issue CONV 记录人工对账。详见 ADR 0004 与 `docs/issues/2026-08-07-conv-markup-spec.md`。

### 1.9 项目结构对齐 AOSP `Android.bp`（用户明确要求，2026-07-29；2026-08-06 修正为语义对齐）

> **规则 B (bp-aligned structure)**: `Android.bp` 是生产 source roots、资源 owner、
> static/libs/plugins **语义**的唯一依据；Gradle module 边界遵循真实 seam（R namespace、
> 多消费者、外部 API、处理器/AIDL 工具链、防依赖环），**不要求每个 Soong target 对应一个 Gradle module**。

详见 `docs/adr/0003-app-module-aligns-aosp-bp.md` 决策 1：

- `android_app "SystemUI"` → `:app`（APK 入口，仅 `static_libs: ["SystemUI-core"]`）
- `android_library "SystemUI-core"` → `:SystemUI-core`（含 src + compose + 所有子模块 static_libs）
- 多个内部 Soong target 可合入一个 Gradle module（如 Log+Common+utils → `:SystemUI-common`，
  Compose Core+Scene → `:SystemUI-compose`，全部 pods → `:SystemUI-core`）
- 目标 13-module 清单见 `docs/architecture/2026-08-06-module-structure-audit.md`，实施计划见
  `docs/superpowers/plans/2026-08-06-13-module-source-topology.md`
- `SystemUIApplication.java` / `SystemUIService.java` 位于 AOSP `SystemUI-core` 的 `src/**/*.java` glob 内，**必须保留在 `:SystemUI-core/src/com/android/systemui/`**；`:app` 按 bp 无独立源码
- `:app/src/main/AndroidManifest.xml` 从 AOSP 完整复制（1158 行），不允许最小化

---

## 二、本项目开发原则

### 2.1 项目向前推进原则

> **规则 I (Forward Progress)**：衡量改动的标准是项目是否在向正确、可维护、最终可构建的方向推进，而不是单次编译错误数上升或下降。

- 编译错误数是诊断信息，**不是提交门槛、回滚阈值或审批条件**；项目任何阶段都不要求“每次 commit 错误数必须下降”
- 源码补齐、违规源码删除、jar/AAR 切换、资源对齐和模块重构可能让错误数暂时上升、下降或让构建暂时中断，只要整体结构更接近 AOSP 且来源更合规，均可接受
- 优先保证：
  1. AOSP SystemUI 源码/AIDL/res 不漏不多
  2. SystemUI 自有模块使用源码依赖，非 SystemUI 代码不违规源码复制
  3. jar/AAR/官方 Maven 依赖的来源、边界和资源归属正确
  4. 不伪造、不遗漏、不擅改资源
  5. 模块图和 APK 打包边界对齐 AOSP `Android.bp`
- commit 应尽量聚焦且有明确意义；允许为保存真实进度提交已记录的中间态，不要求中间态能够完整编译
- **不要求每次修改或每次提交都运行编译**：编译是回答具体问题或验证阶段性里程碑的工具，只在它能提供有效证据时运行
- 文档必须如实记录本次是否运行构建、运行了什么命令及实际结果；未运行时直接写“未运行”，不得暗示构建成功
- `docs/GRADLE_MIGRATION_LOG.md` 保留错误数历史，但仅用于观察和诊断，不再作为开发规则

### 2.2 文档先行

> **规则 D (Documentation)**: 每个步骤开始前先在 `docs/issues/` 下写文档

- 文档命名：`docs/issues/YYYY-MM-DD-<topic>.md`
- 文档包含：背景、操作步骤、错误数演变、待解决问题
- 复杂调研写在 `docs/architecture/YYYY-MM-DD-<topic>.md`

### 2.3 遵循 AOSP 源码结构

| 资源类型 | 路径 |
|---------|------|
| AOSP 源码 | `/home/conv/myspace/aosp/` |
| AOSP 中间产物 | `/home/conv/myspace/aosp/out/soong/.intermediates/` |
| AOSP 编译 jar | `/home/conv/myspace/aosp/out/target/common/obj/*/classes.jar` |
| AOSP turbine-combined | `aosp/out/.../turbine-combined/*.jar` |

参考 AOSP 的 `Android.bp` 文件了解模块依赖关系。

### 2.4 自定义 SDK、framework.jar 与 framework-res.apk 的职责

- 我们的自定义 SDK：`compileSdkPreview = "SysUISdk"`，位于 `/home/conv/Android/Sdk/platforms/android-SysUISdk/`
- **自定义 SDK 不是不可变黑盒，可以从 AOSP/设备产物重新生成或补丁**（用户 2026-08-06 明确）：
  1. 将 AOSP `framework.jar` 的类合并/暴露到 SysUISdk `android.jar`，或作为 compileOnly/bootclasspath → 补标准 SDK 缺失的 @hide API、内部类和常量
  2. 将设备/AOSP `framework-res.apk` 的 `resources.arsc` + `res/` 写入 SysUISdk `android.jar` → 解决 `@*android:` 私有资源 ID 与设备 framework 不匹配
  3. 修改 SysUISdk `framework.aidl` → 补 framework @hide AIDL interface/parcelable 声明（`tools/install_sdk.py` 当前负责此项）
- **framework.jar 与自定义 SDK 资源不是一回事**：framework.jar 主要提供代码签名；单独把它放到 bootclasspath 不能解决 framework 私有资源 ID（参考项目问题二十五已证伪），资源 ID 必须由自定义 SDK 的 android.jar 资源部分解决
- 本项目根 `build.gradle.kts` 当前只把 framework.jar 注入 `JavaCompile.bootstrapClasspath/classpath`，**不注入 KotlinCompile**；后者会污染 Compose inline metadata，触发 `Couldn't inline method call` 等 IR 错误
- Kotlin 所需隐藏 API 由合并后的 SysUISdk/AGP classpath 提供
- **2026-08-12 更新**：Compose 1.11.4 + AGP builtInKotlin + `:SystemUI-core` 应用 Compose compiler plugin 后，Compose inline 问题已不再出现（此前 Kotlin 编译被 `Couldn't inline method call: Box$default` 阻塞）
- 内部 flags jar 必须放在 framework.jar 之前，否则 framework.jar 的同名 stub 会遮蔽真实 flags 类
- 参考：`CarSystemUIGradle/docs/GRADLE_MIGRATION.md` 问题二十四至二十六；`docs/architecture/2026-08-06-reference-project-rationale.md`

### 2.5 求助于用户

> **规则 H (Human Escalation)**: 遇到下面任一情况，**停止**并用 `AskQuestion` 询问用户

1. 必须创建 stub 类（违反规则 P）
2. 必须修改 res/ 下的资源文件（违反规则 R）
3. 必须凭空生成同名 res 资源解决编译错误（违反规则 R）
4. 必须创建 .sh 脚本（违反规则 R/ADR 0002，scripts must be Python）
5. 需要产品决策（多个等价方案）
6. 需要修改 AGENTS.md 的核心规则
7. 所有尝试过的方案都失败，需要决策下一步方向

---

## 二.二、架构决策记录 (ADR)

参考 `docs/adr/`：

- **ADR 0001** — AOSP res 缺失处理优先级：AAR 先直接引入，确认冲突后才用 local Maven（不用 flatDir）
- **ADR 0002** — `tools/` 下脚本一律 Python，禁止 .sh（除非纯系统 CLI 调用）
- **ADR 0003** — 项目结构/模块命名/依赖严格按 AOSP `Android.bp`
- **ADR 0004** — AOSP 源码改动用 CONV 标记追溯；对齐工具 strict 不卡 MODIFIED，靠人工对账

---

## 三、项目架构

### 3.1 模块结构

按 AOSP `frameworks/base/packages/SystemUI/Android.bp` 的**语义**对齐（详见 `docs/adr/0003-app-module-aligns-aosp-bp.md` 决策 1）。目标 13-module 拓扑（实施中，见 `docs/superpowers/plans/2026-08-06-13-module-source-topology.md`）：

```
:app                          # android_app "SystemUI"（无独立源码；负责 manifest、签名和最终 APK 打包）
:SystemUI-core                # android_library "SystemUI-core"（主模块，含入口类、src + compose + pods）
:SystemUI-res                 # 独立资源 namespace（res/res-keyguard/res-product），生成 com.android.systemui.res.R
:SystemUI-common              # Common + Log + shared-utils 合并（源码）
:SystemUI-animation           # PlatformAnimationLib + Shader(surfaceeffects) 合并（源码，含 res）
:SystemUI-plugin-core         # PluginCoreLib runtime API（JVM 源码）
:SystemUI-plugin-processor    # PluginAnnotationProcessor（build-time，不进 APK implementation）
:SystemUI-plugin              # SystemUIPluginLib runtime（源码，含 bcsmartspace）
:SystemUI-unfold              # SystemUIUnfoldLib（源码，KSP 跑 Dagger）
:SystemUI-customization       # SystemUICustomizationLib（源码，含 res）
:SystemUI-shared              # SystemUISharedLib + keyguard child 合并（源码，含 aidl+res）
:SystemUI-shared-biometrics   # biometrics（独立 R namespace，被 Settings 消费）
:SystemUI-compose            # Compose Core + Scene 合并（源码）
```

非 SystemUI 产物（不进源码 module）：`animationlib`（frameworks/libs/systemui）→ 直接 AAR；
`compilelib` → debug/release JAR；`kairos` → test-only，不进本 APK 生产图。

> **历史**：2026-07-29 源码化里程碑将 tier① 自有代码由 jar 改为源码依赖（规则 S）；
> unfold 引入 KSP（`2.2.10-2.0.2`，对齐编译器 2.2.10）跑 Dagger。详见
> `docs/architecture/2026-07-29-dependency-audit.md` §6。
> **2026-08-12 更新（Task 1–6）**：依赖升级 + 迁移 AGP `builtInKotlin=true`；
> KSP 0 错误（2933 文件生成），core Kotlin 编译 0 错误；Compose inline 问题消失。
> 后置审查发现的 `jsr305`、WM-Shell AAR 重复类、header flag JAR 与 release KSP/AIDL
> 依赖问题均已在 Task 1–5 修复；最终 APK 基线待 `:app:assembleDebug` 复验。

### 3.2 libs/ 内容

> **AAR 统一管理（2026-08-11 建立；2026-08-12 起提交入 git）**：所有 AAR 由 `tools/package_aosp_aar.py` 生成到 `libs/aars/`，
> 再由 `tools/install_aar_to_maven.py` 安装到 `libs/maven/`（AAR + POM 骨架），
> 在 `libs.versions.toml` 声明 catalog alias（如 `libs.systemui.settingslib`）统一引用。
> build.gradle.kts 中不再直接 `files("libs/aars/xxx.aar")`。
> **2026-08-12 起 `libs/`（含 jar/aars/maven）全部提交入 git**（用户明确要求），新 clone 可直接构建；
> 仅当需要重新生成 AOSP 产物时才跑 `python3 tools/package_aosp_aar.py --all` + `python3 tools/install_aar_to_maven.py`。

```
libs/
├── framework.jar                       # AOSP 框架 jar (隐藏 API)
├── framework-statsd.jar
├── android.car.jar                     # Car API
├── android_module_lib_stubs_current.jar
├── monet.jar                           # ColorScheme/Shades/Style
├── systemui-flags.jar                  # com.android.systemui.Flags
├── systemui-shared-flags.jar           # com.android.systemui.shared.Flags
├── settingslib-flags.jar               # com.android.settingslib.flags.Flags (aconfig)
├── settingslib-media-flags.jar         # com.android.settingslib.media.flags.Flags
├── device-state-flags.jar              # com.android.server.policy.feature.flags.Flags
├── libprotobuf-java-nano.jar           # com.google.protobuf.nano.MessageNano (SystemUI-proto 依赖)
├── WindowManager-Shell-shared.jar      # [已删] 合并入 libs/aars/WindowManager-Shell-shared.aar
├── aars/                               # 直接 AAR（package_aosp_aar.py 生成；2026-08-12 起提交入 git）
│   ├── animationlib.aar                  # frameworks/libs/systemui:animationlib
│   ├── WifiTrackerLib.aar                # frameworks/opt/net/wifi/libs/WifiTrackerLib
│   ├── iconloader.aar                    # frameworks/libs/systemui:iconloaderlib
│   ├── SettingsLib.aar                    # frameworks/base/packages/SettingsLib（含 32 个子模块合并）
│   ├── WindowManager-Shell.aar           # frameworks/base/libs/WindowManager/Shell
│   └── WindowManager-Shell-shared.aar    # WM-Shell static_libs 子模块（javac+kotlin 合并，含 PhysicsAnimator）
├── prebuilts/                          # 历史 prebuilt jar（逐步清理中）
└── maven/                              # 本地 Maven 仓库（install_aar_to_maven.py 安装；2026-08-12 起提交入 git）
    ├── com.android.systemui/
    │   ├── SettingsLib/1.0.0/            # libs.systemui.settingslib
    │   ├── iconloader/1.0.0/            # libs.systemui.iconloader
    │   ├── WindowManager-Shell/1.0.0/   # libs.systemui.wmshell
    │   ├── WindowManager-Shell-shared/1.0.0/  # libs.systemui.wmshell.shared
    │   ├── WifiTrackerLib/1.0.0/        # libs.systemui.wifitrackerlib
    │   ├── animationlib/1.0.0/          # libs.systemui.animationlib
    │   └── SystemUISharedLib/1.0.0/     # [旧] 遗留，待清理
    ├── com.android.systemui.flags/
    │   └── flags/1.0.0/
    └── com.android.server.notification/
        └── Flags/1.0.0/
```
```

**历史**: `libs/server-notification-flags.jar` 已在 Phase B 清理。notification flags 现由 `libs/maven/com/android/server/notification-flags/` 提供。

### 3.3 AOSP 源码镜像

```
SystemUI-core/src/             <--  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src/
SystemUI-res/res/              <--  AOSP SystemUI/res/
SystemUI-res/res-keyguard/     <--  AOSP SystemUI/res-keyguard/
SystemUI-res/res-product/      <--  AOSP SystemUI/res-product/
```

---

## 四、当前进度状态（历史记录至 2026-07-29；现状更新于 2026-08-12）

### 4.1 已完成

| 时间 | 错误数 | 操作 |
|------|--------|------|
| 2026-07-22 初 | 5296 | 仅有 sdk android.jar |
| 2026-07-22 | 4675 | 替换 framework.jar (AOSP 完整版) |
| 2026-07-22 | 3008 | 合并 SDK android.jar + framework.jar |
| 2026-07-22 | 2412 | 删除所有 v1 stub 文件 |
| 2026-07-22 | 2000 | 加 Monet jar + SystemUI Flags jar |
| 2026-07-23 | 2000 | (本日到此) |
| 2026-07-29 | 142 | biometrics/keyguard/kairos 等大批源码补全 |
| 2026-07-29 | 116 | clocks 塞 :SystemUI-plugin |
| 2026-07-29 | 102 | Phase A–C：tier① 全源码化 + KSP 跑 Dagger（无回归） |
| 2026-07-29 | 73 | Phase D：AIDL 源码编译删 systemui-aidl.jar（communal/widgets 29→0） |
| 2026-07-29 | 70 | 规则 C 审查：删 5 个伪造 stub + 18 处伪造 import（回归 AOSP 原貌） |
| 2026-08-11 | KSP: 0 | KSP + Dagger 2.55 useBindingGraphFix 首次通过（commit `05ea2064`） |
| **2026-08-12** | **KSP: 0 / Kotlin: 2** | **全依赖升级 + builtInKotlin 迁移（commit `e3548016`）** |
| **2026-08-12 实施** | **KSP: 0 / Kotlin: 0** | **Task 1–6：jsr305、aconfig JAR、WM-Shell AAR、variant KSP/AIDL、AGP 9.3.1、文档/格式清理** |
| **2026-08-12 验证** | **KSP: 0 / Kotlin: 0 / javac: 42** | **Task 7：完整验证链；`:app:assembleDebug` 在 core Java 编译阶段失败，APK 未生成，8 组根因已归属** |
| **2026-08-13 修复波次** | **javac: 20（仅 NeverCompile 组）** | **编排工作流修复 7/8 组根因（`2662423b`/`e454feda`/`f870be99`/`ddd334fb`）；新浮出 `processDebugResources` featureFlag 阻塞** |
| **2026-08-13 里程碑** | **javac: 0** | **brief 008 补 SysUISdk dalvik annotations（`a35906f4`）；`:SystemUI-core:compileDebugJavaWithJavac` 0 错误，8 组根因全部清零；仅剩 featureFlag 资源链接阻塞** |

### 4.2 当前构建状态（2026-08-12 实施检查点，Task 1–7）

- **KSP 编译**: debug/release 均 BUILD SUCCESSFUL，0 错误，2933 个文件生成；fresh checkout 已复验
- **Kotlin 编译**: `:SystemUI-core:compileDebugKotlin` BUILD SUCCESSFUL，0 错误
- **APK 编译**: core javac 已 0 错误；featureFlag 阻塞已修（`8ab860e9`，AGP `additionalParameters("--feature-flags", ...)`）；`:app:assembleDebug` 当前阻塞于 `:app:processDebugResources` 的 **`androidprv:` 框架私有资源缺失**（§2.4 第 2 条已知缺口：SysUISdk `android.jar` 缺 framework-res.apk 资源；此前被 featureFlag abort 遮蔽），修复方向已明确（framework-res.apk → SysUISdk），待用户批准
- **WM-Shell AAR**: 主/shared class-set 交集为 0，`:app:checkDebugDuplicateClasses` 通过
- **flag JAR**: `systemui-shared-flags.jar` 已换 Soong `javac` 完整 JAR；`settingslib-flags.jar` 为 `compileOnly`；D8 `Absent Code attribute` 消失
- **单元测试**: 60 个全部通过
- 错误数只作诊断，不构成提交、回滚或审批条件
- 审查与实施记录：`docs/issues/2026-08-12-current-progress-standards-review.md`
- 执行计划：`docs/superpowers/plans/2026-08-12-build-to-apk-readiness.md`

### 4.3 版本矩阵（2026-08-12）

| 组件 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.3.1 | settings.gradle.kts 硬编码 |
| Kotlin | 2.2.10 | AGP `builtInKotlin=true` 内置，**无显式 kotlin-android 插件** |
| KSP | 2.2.10-2.0.2 | 对齐 AGP 内置 Kotlin |
| Dagger | 2.59.2 | useBindingGraphFix 自 2.58 默认启用 |
| Compose | 1.11.4 | **最高保留 `ExperimentalAnimatableApi`**（1.12.0 已移除，AOSP 源码在用） |
| material3 | 1.5.0-alpha18 | 对齐 compose 1.11.x |
| androidx 系列 | 公网最新 | AOSP prebuilts 版本多在公网不存在，须逐个查 maven-metadata.xml |

**builtInKotlin 关键配置**（详见 PITFALLS §1.5）：
- `android.builtInKotlin=true`（gradle.properties）
- `android.disallowKotlinSourceSets=false`（允许 KSP 操作 kotlin sourceSets）
- 所有 Android 模块必须 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`（builtInKotlin 下 java.srcDirs 不含 .kt）
- SystemUI-core: AIDL 输出目录加入 kotlin sourceSet + `kspDebugKotlin→compileDebugAidl`、`kspReleaseKotlin→compileReleaseAidl`

### 4.4 待解决

1. 实施 androidprv 私有资源修复（framework-res.apk 的 `resources.arsc` + `res/` 写入 SysUISdk `android.jar`，§2.4 第 2 条先例，待用户批准），然后重跑 `:app:assembleDebug` 建立 APK 里程碑
2. 处理 Deferred Follow-ups：Room schema 导出、Kotlin 2.3 data-class copy 可见性、manifest 重复权限、评估移除 `android.disallowKotlinSourceSets=false`

### 4.5 已解决

- **server-notification-flags.jar** (Stage 2): 已解决。根因是源码 stub 遮蔽 jar，`git rm` 后 2000 → 1979
  - 详见 `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`
- **全项目 R import 歧义**: 已清零（7 文件删多余 `systemui.R`，1979→1879）
- **KSP + Dagger 绑定解析**: 已解决（Dagger 2.59.2 默认启用 useBindingGraphFix，KSP 0 错误）
- **Compose inline 问题**: 已解决（Compose 1.11.4 + builtInKotlin 后消失）
- **Kotlin 版本兼容**: 已解决（AGP builtInKotlin 锁定 2.2.10；2.3.x 插件与 newDsl 不兼容）

---

## 五、问题排查流程

当遇到 `Unresolved reference` 时：

### 5.1 诊断 5 步

```bash
# 1. 在 AOSP 查符号
find /home/conv/myspace/aosp -name "*.java" -o -name "*.kt" | xargs grep -l "<符号>" 2>/dev/null | head -3

# 2. 在 SDK android.jar 查
unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar | grep <符号所在包>

# 3. 在 framework.jar 查
unzip -l libs/framework.jar | grep <符号所在包>

# 4. 在 systemui-flags / monet / server-notification-flags 查
unzip -l libs/systemui-flags.jar | grep <符号>
unzip -l libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar

# 5. javap 看具体方法
javap -p <ClassName>
```

### 5.2 错误归类

| 错误种类 | 出现场景 | 处理路径 |
|---------|---------|---------|
| `Unresolved reference X` | 类/方法/字段找不到 | 5.1 找位置 → 写 jar/module |
| `Cannot infer type` | 多 overload 重叠 | 显式类型注解 |
| `Argument type mismatch` | 选错 overload | 同上 |
| `Conflicting import` | 多个 R 类 | alias import |
| `None of the following candidates is applicable` | receiver type 不匹配 | 看 arg 实际类型 |

### 5.3 通用解决方案

| 解决方案 | 风险 | 适用 |
|---------|------|------|
| 提取 .class 到 jar | 低 | aconfig Flags |
| 加 aar 依赖 | 低 | 含资源 |
| 复制源码为 module | 中 | 完整模块 |
| KSP 跑注解处理器 | 中 | Dagger 生成代码（KAPT 禁用，KSP 2.2.10-2.0.2 可用；见 unfold） |
| 升级 Compose 版本 | 中 | 内部 API |
| 排除源码 | 临时 | 暂时不用的代码 |

---

## 六、构建命令速查

```bash
# 编译主模块
./gradlew :SystemUI-core:compileDebugKotlin

# 统计错误数
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep -cE "^e: file:"

# 分类错误
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep "^e: file:" | \
  sed -E 's|.*/SystemUI-Gradle/SystemUI-core/src/com/android/||; s|/[^/]+\.kt.*||' | \
  sort | uniq -c | sort -rn | head -20

# 清理
./gradlew :SystemUI-core:clean

# 强制重跑
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks

# 查看依赖
./gradlew :SystemUI-core:dependencies --configuration debugCompileClasspath

# Debug 模式（看实际 classpath）
./gradlew :SystemUI-core:compileDebugKotlin --debug 2>&1 | grep -oE "[-]classpath [^ ]+"
```

---

## 七、文档位置

| 路径 | 说明 |
|------|------|
| `docs/HANDOFF.md` | 下个 AI 必读入口 |
| `AGENTS.md` | 本文件（规则 + 现状） |
| `docs/CURRENT_STATE.md` | 状态快照 |
| `docs/PLAN.md` | 阶段计划 |
| `docs/PITFALLS.md` | 踩坑记录 |
| `docs/GRADLE_MIGRATION_LOG.md` | 历史错误数演变 |
| `docs/issues/YYYY-MM-DD-<topic>.md` | 每日详细问题记录 |
| `docs/architecture/YYYY-MM-DD-<topic>.md` | 复杂调研 |
| `docs/adr/NNNN-<slug>.md` | 架构决策记录 (ADR) |
| `tools/package_aosp_aar.py` | 从 AOSP Soong 产物打包干净 AAR 到 `libs/aars/`（含多 JAR 合并、reject_sysui、确定性） |
| `tools/install_aar_to_maven.py` | 把 `libs/aars/*.aar` 安装到 `libs/maven/` 本地 Maven 仓（AAR + POM 骨架） |
| `tools/package_compilelib_jars.py` | 打包 compilelib debug/release JAR（确定性） |
| `tools/package_aconfig_jars.py` | 从 AOSP `javac` 产物打包完整 aconfig runtime JAR |
| `tools/install_sdk.py` | 校验 + 补 SysUISdk framework.aidl（framework 隐藏接口） |
| `tools/clean_prebuilts.py` | 清理 prebuilt jar 中的冲突类（与 maven 重复） |

---

## 八、用户偏好

- 用户使用中文交流
- 用户喜欢看代码改动总结
- 用户要求及时记录问题 (2026-07-23 提醒)
- 用户要求先做 plan 再开发 (2026-07-23 提醒)
- 用户希望增量提交，每个 commit 都有意义
- 用户希望参考 `CarSystemUIGradle` 项目的做法
- **用户要求给下一个 AI 留完整交接文档** (2026-07-28 提醒)
- 用户坚持"无 stub"原则 (2026-07-22 决定)
- **`tools/` 下脚本一律写 Python，不写 shell** (用户 2026-07-29 明确)
- **依赖尽可能升级到最新版本**；重要决策先与用户沟通 (用户 2026-08-12 明确)
- **commit message 用英文**，及时 commit 并 push (用户 2026-08-12 明确)
- **不用 `@Suppress("DEPRECATION")` 等绕过语法** (用户 2026-08-12 明确)
- **遇到不会的内容去查官方文档** (用户 2026-08-12 明确)

---

## 九、版本历史

| 日期 | 改动 |
|------|------|
| 2026-07-22 起草 | 初始版本，仅有规则 |
| 2026-07-23 增订 | 加入当前进度和待解决 |
| 2026-07-28 重写 | 配合 docs/HANDOFF.md 重组结构，新增 §0 优先级、§1.4 参考、§2.5 求助规则、§3.2 libs 警告、§4.1 错误数演变表 |
| 2026-07-29 增订 | 新增 §0.二 ADR 索引、§1.5 规则 S、§1.6 规则 C、§1.7 规则 F、§1.8 规则 R、§1.9 规则 B（bp 对齐）；同步 ADR 0001/0002/0003 |
| 2026-08-06 更正 | Maven 不再列为第四种产物；AAR 先直接引入、确认冲突后才用本地 Maven；补充自定义 SDK/framework.jar/framework-res 原理；删除错误数下降/阈值和逐次编译要求，改为“项目整体向前推进”原则 |
| 2026-08-07 增订 | 新增 ADR 0004（CONV 标记规范 + 对齐纪律）；规则 R 升级为“禁止无标记擅改”；`check_source_alignment.py --strict` 不再卡 MODIFIED |
| 2026-08-12 增订 | §4 更新：全依赖升级 + builtInKotlin 迁移（commit `e3548016`）；§4.2 重写为当前构建状态；新增 §4.3 版本矩阵；§2.4 记录 Compose inline 问题已解决 |

---

**下一步**: 阅读 `docs/CURRENT_STATE.md` 了解具体状态。
