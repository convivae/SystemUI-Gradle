# Task 088 — AGP / Gradle / Kotlin 官方升级可行性调研报告

- **日期**：2026-09-02（研究窗口 07:27–07:50 UTC）
- **性质**：read-only 第一方来源调研；本报告是唯一写入物
- **结论速览**：**未发现把升级裁定为 targeted fix 的直接第一方证据**；AGP 9.3.2/9.4.0/9.5.0-alpha 线的发行说明与源码在授权渠道不可得，其中是否存在相关修复保持 **unknown（不可证伪）**。Task 086 已排除"AGP 注入字段必然失败"；但 Task 087 单变量控制因目标 UP-TO-DATE 而 **INCONCLUSIVE**，失败触发条件仍 **unresolved**——既不能归因 custom parameters，也不能排除工具链因素。升级至多构成后续维护性/诊断实验，不构成当前 blocker 的修复手段。**本调研不授权任何升级，也不证明任何构建/运行时结果。**

---

## 1. 范围、方法与网络限制

本任务回答 brief 的五个问题：最新版本、官方兼容矩阵、AGP 9.3.1 之后与当前 `AsmClassVisitorFactory` 序列化失败相关的官方变更、证据化分类、以及（仅在证据成立时）最小可逆实验设计。**未执行任何升级、构建、Gradle 命令或包安装。**

**网络可达性（2026-09-02 实测，TCP connect 超时）**：`developer.android.com`、`maven.google.com`、`android.googlesource.com`、`issuetracker.google.com`、`github.com` 均不可达；`ksp.github.io` 根路径 404。**可达且已用的第一方渠道**：

| 渠道 | 用途 |
|---|---|
| `https://dl.google.com/android/maven2/...`（Google Maven 直连） | AGP `maven-metadata.xml` 与 9.3.1/9.3.2/9.4.0/9.5.0-alpha03 POM |
| `https://services.gradle.org/versions/*`、`/fixed-issues/*`、`/known-issues/*` | Gradle 当前版本与 fixed/known issues |
| `https://docs.gradle.org/9.6.0|9.7.0|9.7.1/release-notes.html`、`/current/...` | Gradle 发行说明 |
| `https://repo1.maven.org/maven2/...`（Maven Central） | Kotlin / KSP `maven-metadata.xml` |
| `https://kotlinlang.org/docs/ksp-quickstart.html` | KSP 官方版本配对示例 |
| `https://raw.githubusercontent.com/google/ksp/main/README.md` | KSP 官方 README |
| `android docs` 官方知识库 CLI（`kb://android/...`） | AGP 9.3.0 发行说明、Studio 版本表、AGP about 页 |

所有访问均流式只读，未在仓库外创建/下载/解包任何文件。未使用 Python。

## 2. 已验证事实（verified facts）

### 2.1 版本现状（研究日 2026-09-02）

| 组件 | 项目当前 | 最新 final（第一方元数据观察；渠道语义见各行注） | 最新预览 | 证据 |
|---|---|---|---|---|
| AGP | 9.3.1 | **9.4.0**（观察到的最新无后缀 final artifact；官方 stable 渠道标注不可得，见 §6.1） | 9.5.0-alpha03 | Google Maven `maven-metadata.xml`（`https://dl.google.com/android/maven2/com/android/tools/build/gradle/maven-metadata.xml`）：版本列表末端为 `...9.3.1, 9.3.2, 9.4.0-alpha01…rc02, 9.4.0, 9.5.0-alpha01…alpha03`。`<latest>`/`<release>` 标签值 `9.5.0-alpha03` 是**仓库元数据语义**（最近发布的 artifact），**不是稳定版声明**；版本列表中 9.4.0 为观察到的最新无后缀 final（9.3.2 为 9.3 线补丁），9.5 线仅有 alpha，无 rc/final |
| Gradle | 9.5.0 | **9.7.1**（final；metadata buildTime：9.7.0=2026-08-06、9.7.1=2026-08-19，9.7.1 commit `92f0512e7f06...`；9.7.1 为 9.7.0 的首个补丁） | 9.8.0-milestone-2 / 9.8.0 release-nightly / 9.9.0 nightly | `https://services.gradle.org/versions/current`、`/versions/all`、`https://docs.gradle.org/current/release-notes.html` |
| Kotlin | 2.2.10（AGP `builtInKotlin` 内置） | **2.4.10** | 2.4.20-RC2（RC，非稳定） | Maven Central `org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml`：`<latest>2.4.20-RC2`，版本列表中最后的非 RC/Beta 稳定版为 2.4.10 |
| KSP | 2.2.10-2.0.2 | **2.3.11**（Maven Central `<release>` 标签值；稳定性/渠道未经独立证明） | — | Maven Central `com/google/devtools/ksp/com.google.devtools.ksp.gradle.plugin/maven-metadata.xml`。**配对证据**：kotlinlang.org KSP quickstart（`https://kotlinlang.org/docs/ksp-quickstart.html`）官方示例将 **KSP 2.3.10 与 Kotlin 2.4.10 搭配**，证明 KSP 版本号前段已与 Kotlin 版本解耦；不得再按 `<kotlin>-<ksp>` 旧格式推断配对 |
| Android Studio | （IDE 提示触发本次调研；项目未使用 Studio 构建） | **渠道表**：Quail 1 = Stable、Quail 2 = RC、Quail 3 = Canary；表中 Stable 通道 AGP 标注为 9.2.0 | — | `android docs` KB `kb://android/studio/preview/features/index`（镜像 `developer.android.com/studio/preview/features`）。**Quail 的数字版本号未能从已取来源确认 → gap，见 §6** |

### 2.2 AGP 9.3.0 官方兼容矩阵（唯一完整取到的 AGP 矩阵）

来源：KB `kb://android/build/releases/agp-9-3-0-release-notes`（镜像 `https://developer.android.com/build/releases/past-releases/agp-9-3-0-release-notes`）：

- 最大支持 API level **37**（本项目 SysUISdk 基于 base `android-37.0`，在 9.3 线内）。
- **Gradle：min 9.5.0，default 9.5.0** —— 项目当前 Gradle 9.5.0 恰为 AGP 9.3.x 的最低兼默认版。
- SDK Build Tools 36.0.0（min=default）；NDK default 28.2.13676358；**JDK min 17，default 17**。
- **JDK 语义分层**（brief 特别要求区分）：AGP 的 JDK 17 下限指运行 Gradle/AGP 的 JVM。本项目 **runtime（daemon）JDK 为 25**，**Java 编译 toolchain 为 21**（`jvmTarget JVM_21`）；两层均高于 AGP 下限，且互不混淆。
- AGP 9.3.0 线（alpha01→rc01）全部公开 fixed issues 中，**没有**任何条目涉及 ASM instrumentation、`AsmClassVisitorFactory`、artifact/dependency transforms、worker isolation、configuration-cache 序列化、`DefaultProperty` 或 `InstrumentationContext.apiVersion`。已修复项为 lint、L8 mapping、KMP keepRules、`RecordTag` ClassNotFound（旧 AGP + Gradle 9.2）、Windows 句柄泄漏、JavaDoc workers 等。

### 2.3 AGP 9.3.1 → 9.5.0-alpha03 的 POM 依赖证据（Google Maven，第一方）

对 `com.android.tools.build:gradle` 四个版本 POM 逐项比对（`https://dl.google.com/android/maven2/com/android/tools/build/gradle/<v>/gradle-<v>.pom`）：

| 依赖 | 9.3.1 | 9.3.2 | 9.4.0 | 9.5.0-alpha03 |
|---|---|---|---|---|
| `kotlin-stdlib` | 2.2.10 | 2.2.10 | 2.2.10 | 2.2.10 |
| `asm` / `asm-analysis` / `asm-commons` / `asm-util` | 9.9 | 9.9 | 9.9 | 9.9 |
| `symbol-processing-gradle-plugin` | 2.2.10-2.0.2 | 2.2.10-2.0.2 | 2.2.10-2.0.2 | （见注） |
| `kotlin-gradle-plugin` | —（未在抓取段） | — | — | 2.2.10 |
| `sdk-common` 等 tools 侧 | 32.3.1 | — | 32.4.0 | — |

注：9.5.0-alpha03 POM 抓取段确认了 `kotlin-stdlib 2.2.10`、`kotlin-gradle-plugin 2.2.10`、ASM 全家 9.9，未抓取到 `symbol-processing-gradle-plugin` 行，如实记为未观测。**结论边界（严格限定）**：POM 相等**只证明这四个版本声明的依赖版本一致**。它**不**证明 AGP 自身插桩实现（`AsmClassVisitorFactoryEntry` / `AsmClassesTransform` 等 AGP 自有代码）在 9.3.1→9.5.0-alpha03 间未变，**不**证明升级不可能包含 targeted fix，也**不**构成"升级与该失败无关"的直接反证——9.4/9.5 的发行说明与源码不可得（§6.1），其中是否存在相关修复保持 unknown。

### 2.4 Gradle 9.6.0 / 9.7.x 发行说明与已知问题（docs.gradle.org / services.gradle.org）

- **9.7.0/9.7.1 无任何与 `AsmClassVisitorFactory`、transform 参数序列化、`DefaultProperty` 相关的修复条目**（发行说明全文过滤 `transform|isolation|serializ|worker` 无匹配修复；`fixed-issues/9.6.0` 首条为 log4j12 platform-compile 回归，`known-issues/9.7.1` 返回空数组）。
- **9.7.0 known issues（含 transform 回归，#38792）**：9.7.0 的 known issues 包含 **"Gradle 9.7.0 breaks a working Transformer implementation"（issue #38792）** 及 "BaseExecSpec streams"、"Click to see difference" 格式、"9.7 leaks bundled antlr into kapt classpath"、"ant.taskdef classpath parent-first" 等。经 Chief 复核，**#38792 列于 9.7.1 的 fixed issues 中**；本报告不暗示该回归在 9.7.1 仍然存在。该条目仅说明 9.x 线 transform/类加载区域变更活跃，且任何评估实验应指向 9.7.1 而非 9.7.0。
- 9.7.1 的 Configuration Cache 改进（`ResolutionResult` 可直接作为 task input、TestKit 第三方 javaagent、IDEA 伪失效削减）与 Isolated Projects 稳定化（`--isolated-projects`）均不涉及本项目的失败路径（`AsmClassesTransform` 参数隔离用的是 worker API + Java 序列化，非 Isolated Projects 特性）。

### 2.5 项目失败上下文（本仓库已验收证据，非本报告新产生）

Task 083/084：`NotSerializableException: org.gradle.api.internal.provider.DefaultProperty`，46 条 cause chain 均为 `InstrumentationContext_Decorated.__apiVersion__` → `AconfigReferenceRewriteFactory_Decorated.__instrumentationContext__` 字面路径（AGP 9.3.1 `AsmClassVisitorFactoryEntry.configure()` 注入）。Task 086：`InstrumentationParameters.None` no-op `ALL` control 同一 direct task **BUILD SUCCESSFUL**——已证明 AGP 注入的 `__apiVersion__` 并非对所有 factory 必然失败。Task 087（已执行，**INCONCLUSIVE**；状态由 Chief 评审补充，2026-09-02）：custom file parameters 单变量控制返回 BUILD SUCCESSFUL，但目标 task 为 **UP-TO-DATE**（未实际执行），不构成证据；失败触发条件仍 unresolved。

## 3. 推断（inference，与事实分层）

1. **分类为 "no targeted-fix evidence found"（不是"版本缺陷已被证伪"）**：(a) AGP 9.3.0 线 fixed issues 无相关项；(b) AGP 9.3.2/9.4.0/9.5.0-alpha 的发行说明与源码在授权渠道不可得，其中是否存在相关修复保持 unknown——unknown 不等于反证；(c) Gradle 9.6/9.7 已发布部分无相关修复（9.7.0 transform 回归 #38792 经 Chief 复核已列入 9.7.1 fixed issues）。POM 依赖相等只是依赖版本事实，不参与该分类的证明。按 brief 的证据标准（除非直接第一方证据匹配字面失败），当前证据不支持把升级当作 targeted fix。
2. **失败触发条件仍 unresolved**：Task 086 已证 AGP 注入字段在 `None` factory 下可通过（排除"必然失败"）；Task 087 的 custom file parameters 单变量控制因目标 UP-TO-DATE 而 INCONCLUSIVE。因此当前证据**既不支持**把失败归因于 custom parameters，**也不支持**排除 AGP/Gradle 侧因素——两个方向都缺少可用的直接证据。
3. 维护性升级（AGP 9.4.0 / Gradle 9.7.1）可行性存疑而非被否证：AGP 9.4 的 Gradle 最低版本未知（gap）；KB 当前 Studio Stable 表仅标 AGP 9.2.0（该表可能滞后于 Maven 发布，如实并列不裁决）。

## 4. 建议（recommendation）

1. **不进行任何版本升级作为 C5 blocker 的修复手段**。当前 blocker 的证据收集路径（Task 087 → 单变量控制）优先级高于换版本。
2. 升级讨论推迟到触发条件被 conclusively 隔离之后（Task 087 需以目标实际执行的方式重跑或设计后续控制）：若证据落回 buildSrc 侧（参数 shape / 序列化 seam），修复与 AGP/Gradle 版本无关；若证据指向工具链行为，再评估升级——届时仍需先补齐 §6 的版本证据。
3. Android Studio 的升级提示不是升级依据：IDE 建议（触发本次调研的来源）与 AGP 发布节奏（Maven 元数据）与本项目 CLI 构建互相独立，且预览 AGP 需配对应预览 Studio（KB 明示），不适用于本项目。

## 5. 最小可逆实验（design only，NOT executed；当前**不**被证据正当化）

仅当触发条件被隔离后、用户明确要求评估工具链因素时执行；设计如下以备存档：

- **单变量**：isolated worktree 中仅改 `gradle/wrapper/gradle-wrapper.properties` 的 `distributionUrl` 9.5.0 → 9.7.1（镜像 URL 同步），其余一切不动。
- **唯一命令**：`./gradlew :app:desugarDebugFileDependencies --stacktrace --console=plain --max-workers=4`（Task 083 的同一 direct task，5 秒级重现）。
- **判读**：失败 message/field path 不变 → Gradle 版本与该失败无关（维持不升级结论）；失败消失或变形 → 记录差异并升级为待查事实（此时才有升级实验价值）。
- **回滚**：恢复 wrapper 单行。
- **claim boundary**：该实验只覆盖一个 task 的序列化路径，不证明 `:app:assembleDebug`、Release/R8 或任何其他行为；不构成升级授权。

## 6. 未解决问题（gaps，如实保留，不做推断）

1. **AGP 9.3.2 / 9.4.0 / 9.5.0-alpha 线的发行说明、fixed issues 与兼容矩阵（Gradle 最低版、JDK、API 上限）**：`developer.android.com` 全域与 `maven.google.com` 不可达，KB 中 `agp-9-4-0-release-notes`/`agp-9-5-0-release-notes` 均返回 "No document found"。**以上内容按 unknown 记录**；POM 证据（§2.3）只能证明内嵌 ASM/Kotlin 未变，不能替代发行说明。
2. **Android Studio Quail 的数字版本号**（如 2026.x.x 对应关系）：已取来源只给出渠道表（Quail 1 Stable），未给出号码。unknown。
3. **AGP 9.3.1 在 Gradle >9.5.0（如 9.7.1）上的官方支持声明**：Google 兼容性页（`developer.android.com/build/releases/gradle-plugin`）不可达且 KB 无对应文档。unknown——这也是为什么 §5 实验只敢以"评估"而非"升级"为目标。
4. KSP 2.3.11 与 Kotlin 2.2.10（本项目当前内嵌 Kotlin）是否存在官方配对：Maven Central 元数据无法回答配对问题，kotlinlang quickstart 只示范 KSP 2.3.10+Kotlin 2.4.10。unknown（对本报告结论无影响，因任何 KSP 变更都依赖先换 AGP/Kotlin，而那不在建议内）。
5. Gradle 9.6.0 发行说明正文抓取仅得到样式噪音（正文为 JS 渲染），已用 `services.gradle.org/fixed-issues/9.6.0` 部分补偿；9.6.0 完整 fixed-issue 清单未逐条核验。对该报告结论无影响（9.7.1 的 known-issues 已返回空数组且发行说明全文已核）。

## 7. 风险清单（若未来仍选择升级）

- **Gradle 9.x transform 区域变更活跃**：9.7.0 曾出现 transform 回归（issue #38792 "breaks a working Transformer implementation"；经 Chief 复核已列入 9.7.1 fixed issues）。任何升级实验应直接评估 9.7.1 并预期 transform/类加载区域的行为差异需要重验，而不是把 9.7.0 回归当作回避 9.7.1 的依据。
- **Compose 1.11.4 上限**（1.12.0 移除 `ExperimentalAnimatableApi`）与 **kotlinx-coroutines 1.10.2 上限**：任何 Kotlin 升级都会触碰这两个钉版；而 AGP 9.5.0-alpha03 为止内嵌 Kotlin 仍是 2.2.10，Kotlin 升级实际不可达。
- **SysUISdk preview 耦合**：AGP 9.3 明示 max API 37；AGP 9.4 对自定义 preview platform（`compileSdkPreview`）的兼容性 unknown（gap §6.1）。
- **单机单构建纪律**（CHARTER Part 4）：任何升级实验必须独占构建窗口。

## 8. 声明边界

本报告为纯调研产物：**调研本身不授权任何升级**；未运行任何 Gradle 任务、测试、构建、设备或包管理操作；除本报告文件外零写入（无 /tmp、无缓存、无仓库内其他路径）；所有版本/兼容性/修复断言均附第一方来源与访问日期，unknown 项已显式列出而非推断填补。

## 9. 来源清单（访问日期均为 2026-09-02）

1. `https://dl.google.com/android/maven2/com/android/tools/build/gradle/maven-metadata.xml` — AGP 版本全集与 latest/release 标签。
2. `https://dl.google.com/android/maven2/com/android/tools/build/gradle/{9.3.1,9.3.2,9.4.0,9.5.0-alpha03}/gradle-<v>.pom` — 内嵌 kotlin-stdlib/kotlin-gradle-plugin/ASM/symbol-processing 版本。
3. `https://services.gradle.org/versions/current`、`https://services.gradle.org/versions/all` — Gradle 9.7.1 current 及 preview 通道。
4. `https://docs.gradle.org/current/release-notes.html`（=9.7.1）、`https://docs.gradle.org/9.7.0/release-notes.html`、`https://docs.gradle.org/9.6.0/release-notes.html` — 发行说明与 known issues。
5. `https://services.gradle.org/fixed-issues/9.6.0`、`https://services.gradle.org/known-issues/9.7.1` — 修复/已知问题 JSON。
6. `https://repo1.maven.org/maven2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml`、`https://repo1.maven.org/maven2/com/google/devtools/ksp/com.google.devtools.ksp.gradle.plugin/maven-metadata.xml` — Kotlin/KSP 版本元数据。
7. `https://kotlinlang.org/docs/ksp-quickstart.html` — KSP 2.3.10 + Kotlin 2.4.10 官方配对示例（版本解耦证据）。
8. `https://raw.githubusercontent.com/google/ksp/main/README.md` — KSP 官方仓库 README（版本配对文档指针）。
9. `android docs` KB：`kb://android/build/releases/agp-9-3-0-release-notes`（兼容矩阵与 fixed issues）、`kb://android/build/releases/about-agp`（升级指引）、`kb://android/studio/preview/features/index`（Studio 渠道表与 AGP-Studio 预览配对规则）、`kb://android/studio/releases/studio-release-names`（发布阶段定义）。
10. 本仓库 read-only 证据：`docs/issues/2026-09-02-c5-serialization-field-path.md`、`docs/issues/2026-09-02-c5-none-all-control-corrected.md`、`docs/CURRENT_STATE.md`、`gradle/libs.versions.toml`、`gradle/wrapper/gradle-wrapper.properties`、`gradle.properties`、根 `build.gradle.kts`、`buildSrc/build.gradle.kts`。
