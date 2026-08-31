# Namespace 全景设计与不冲突设计规则（2026-08-29）

应用户要求：解释每个 namespace 是谁在用、为什么有这么多、会有什么问题、设计规则是什么。
本文同时作为审计 P2/D11/D6 的配套设计说明。数据均来自当日实测。

## 1. 三个不能混的概念

| 概念 | 归属 | 参与运行期？ | 本项目实例 |
|---|---|---|---|
| `applicationId` | `:app` 的 `defaultConfig` | **是**（APK 身份、intent-filter 匹配、pm 查询） | `com.android.systemui`（= AOSP APK id，不可改） |
| `namespace`（per-module） | 每个 Android library 模块 | **否**（纯编译期：①该模块 R 类的包名 ②BuildConfig 包名 ③ManifestMerger 展开该模块 manifest 相对组件名时的前缀） | 见 §2 |
| Soong 侧无 namespace 概念 | AOSP `Android.bp` | — ①Soong 的 R 包名来自各 `android_library` 的 `AndroidManifest.xml` `package` 属性 ②AOSP 源码所以到处显式 `import com.android.systemui.res.R` 等 FQ R | `AndroidManifest-res.xml` package=`com.android.systemui.res` 等 |

**AGP 硬约束**：同 build 里两个模块 namespace 必须唯一（重复即编译错误）。这是"为什么这么多"的直接答案——
Soong 里 30+ target 共享一个 R/Manifest 体系，AGP 必须每模块一格。**数量是 AGP 结构性必然**；
收敛路径只有合并模块（本项目 30+ Soong target → 17 模块已是收敛结果）。

## 2. 全景盘点（2026-08-29 实测）

### 2.1 Gradle 模块 namespace（13 个 Android 模块 + 4 个 JVM）

| 模块 | namespace | 档级（见 §3） | 实测依据 |
|---|---|---|---|
| `:SystemUI-application` | `com.android.systemui` | **A 承重** | AOSP 顶层 manifest package=同名；**88 个相对组件名靠它展开**（与 AOSP 原文件 88=88 精确相等） |
| `:SystemUI-res` | `com.android.systemui.res` | **A 承重** | 源码 **1162 个文件 import com.android.systemui.res.R**；AOSP `AndroidManifest-res.xml` package=同名 |
| `:SystemUI-shared` | `com.android.systemui.shared` | B 镜像 | AOSP shared/AndroidManifest.xml 同名；源码 12 处 import 自 R |
| `:SystemUI-shared-biometrics` | `com.android.systemui.shared.biometrics` | B 镜像 | AOSP 同名 manifest package |
| `:SystemUI-animation` | `com.android.systemui.animation` | B 镜像 | AOSP Animation manifest 同名 |
| `:SystemUI-customization` | `com.android.systemui.customization` | B 镜像 | AOSP 同名；3 处 import |
| `:SystemUI-clocks-common` | `com.android.systemui.customization.clocks` | B 镜像 | AOSP 同名；18 处 import（含 as clocksR 别名） |
| `:SystemUI-unfold` | `com.android.systemui.unfold` | B 镜像 | AOSP 同名 manifest |
| `:app` | `com.android.systemui.app` | C 占位 | shell manifest 无条目、展开 0 个组件名；无源码 import 其 R；纯标签 |
| `:SystemUI-core` | `com.android.systemui.core` | C 占位 | core 无自有 res，其 R 类为空；源码 0 处 import com.android.systemui.core.*R 系 |
| `:SystemUI-compose` | `com.android.compose` | C 占位 | 合并 AOSP `com.android.compose.core`+`com.android.compose.animation.scene` 两包；merge 后无镜像对象；源码 0 处发行版 R import |
| `:SystemUI-plugin` | `com.android.systemui.plugin` | C 占位（**与 AOSP `com.android.systemui.plugins` 有一字漂移**，见 §4.3） | 源码 0 处 import 自 R |
| `:SystemUI-common` / `:SystemUI-plugin-core` / `:SystemUI-plugin-processor` / `:SystemUI-utils-kairos` | **无（JVM 模块）** | — | java-library 插件，无 namespace 概念 |

### 2.2 AAR（prebuilt）manifest package → 资源 R 归属

- 绝大多数 AAR manifest **无 package 属性**（SettingsLib 全系、WM-Shell×2、animationlib、setupcompat、iconloader、Traceur×2、SerialPortAccessDialog、LowLightDreamLib、color）——17 Soong 产物本就不写 package；资源挂消费者侧符号解析，稳定（16 时代全量验证过）。
- 有 package 的 4 个（AGP 以此定 R 归属）：
  `com.android.systemui.dynamiccolors`、`com.android.personalcontext.ace.client`、`com.android.personalcontext.ace.visualizer`、`com.android.wifitrackerlib.nores`（占位）。
- **ace 双 namespace 的由来**：AOSP `ace/src/.../visualizer` 与 `clientsdk/compat` 是两个独立库、manifest 各带自己的 package；prebuilt classes 中的 R 引用已固化在各自包（`AceEmbeddedSurfaceViewCompat` 引用 client R）。**单 AAR 只能装一个 package**，所以拆双 AAR 是必然，不是选择。
- `com.android.internal.R`（源码 77 处 import）来自 SysUISdk `android.jar` 私有资源桥（ADR 0006），与任何模块 namespace 无关。

## 3. 三档设计规则（本文确立，供 AGENTS.md 同步引用）

- **档 A（语义承重，锁死，不可变化）**：`com.android.systemui`（manifest 展开）+ `com.android.systemui.res`（全量 R import）。
  这两个由 AOSP 字节决定，没有任何自由度。
- **档 B（镜像 AOSP manifest package）**：模块有对应 AOSP `AndroidManifest.xml` 且自身有资源 →
  namespace = AOSP package 原射。对账方式：对齐工具未来可加硬检查（AOSP manifest package ↔ build.gradle.kts namespace 相等）。
- **档 C（Gradle-only 占位标签）**：无镜像对象或镜像对象已合并 → 任意**不与 A/B 撞名**的占位；
  约定后缀化（如 `.app`/`.core`），允许但无义务对齐。改任何名都不影响运行期。

## 4. 会不会有问题（风险清单与现状裁决）

1. **AGP 唯一性**：当前 13 个全部两两不同，已验证（构建过）。
2. **错配的两类后果须区分清楚**：
   - "namespace ≠ 源码 import 的 R 包" → **编译期立即报错**（白错不藏 bug）；
   - "manifest 展开的 namespace ≠ 组件预期前缀" → **运行时才炸**（16 时代 Task 049/050 的 97 错项就是这个）。所以**唯一危险的动作是动手改承重 namespace 或 manifest 展开路径**——这是 task072 改名方案的核心洞察，也是 D11 评审接收的理由。
3. **已知漂移点（非阻塞，登账待清）**：`:SystemUI-plugin` 是 `com.android.systemui.plugin`、AOSP 是 `com.android.systemui.plugins`（一字之差）。当前源码 0 处 import 自 R → 无害；若未来 plugin 源码新增 own-R import 会先编译错再修。建议按档 B 规则一次性对齐为 `com.android.systemui.plugins`（低风险重命名，编译期即可验证）。
4. **":app 的 namespace 与 applicationId 不一致"不是问题**：namespace 不进 runtime；`com.android.systemui.app` 只是 16 时代起的占位名。若想去掉误导，可改名（如 `.appshell`），但零必要性——当前 shell manifest 无条目，它什么都不展开。
5. **com.android.systemui 是谁在用？** 答：`:SystemUI-application` 的 namespace（编译期）+ `:app` 的 applicationId（运行期 identity）。它没有被 R import 使用（源码 0 处 `com.android.systemui.R`）。

## 5. 结论

当前布局唯一需要动作的是 §4.3 的 plugin 一字漂移（待用户批准重命名）；其余每格都有明确职责与实测依据，
不存在"多了"或"冲突"。三档规则将以 AGENTS.md 编辑报批（与审计优先级清单第 4 项的文档同步合并执行）。

*数据复现：模块表=grep 各 build.gradle.kts；R import 普查=find+xargs grep（1162/77/18/12/3 计数）；AAR manifest=unzip+文本 grep；AOSP package 对照=grep 各子树 AndroidManifest.xml。*
