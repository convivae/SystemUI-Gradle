# 2026-08-19 — Kotlin 2.3 升级解锁核查（read-only）

> **任务**: [docs/orchestration/tasks/021-kotlin-23-unlock-check.md](../orchestration/tasks/021-kotlin-23-unlock-check.md)
> **性质**: 只读调研，不改任何构建文件 / 依赖版本 / 源码；不跑本项目 Gradle 构建。
> **前置结论**: [docs/issues/2026-08-12-deps-upgrade-builtin-kotlin.md](../issues/2026-08-12-deps-upgrade-builtin-kotlin.md) §2.1（"所有可用 AGP 版本都绑定 Kotlin 2.2.10"）
> **日期**: 2026-08-19

---

## 一、结论（先说结论）

**结论 (a) — 仍被阻塞。**

截至 2026-08-17（Google Maven `maven-metadata.xml` 的 `lastUpdated`），**最新 AGP
`9.5.0-alpha01` 仍然内嵌 Kotlin `2.2.10`**（`kotlin-stdlib` 2.2.10 +
`kotlin-gradle-plugin` 2.2.10 + `symbol-processing-gradle-plugin` 2.2.10-2.0.2）。
AGP 在 9.4.0-rc01 → 9.5.0-alpha01 两个新版本里都没有把内置 Kotlin 从 2.2.10 抬到
2.3.x。因此本项目依赖的 `android.builtInKotlin=true` 路径仍无法使用 Kotlin 2.3。

Kotlin 上游本身已经走到 **2.4.10 stable**（2026-07-14）与 **2.4.20-RC**（2026-08-12），
但只要 AGP 不内嵌，就与本项目的 builtInKotlin 路径无关。

**与 08-12 结论的差异**: 无本质变化。08-12 时最新 AGP 为 `9.4.0-alpha08`
（内嵌 2.2.10）；08-19 时最新 AGP 为 `9.5.0-alpha01`（仍内嵌 2.2.10）。AGP 向前
走了两个 pre-release（9.4.0-rc01、9.5.0-alpha01），但**没有抬 Kotlin**。阻塞原因
与 08-12 完全一致。

---

## 二、查询命令与原始返回摘要

### 2.1 AGP `com.android.tools.build:gradle` 元数据

```bash
curl -s https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml
```

来源 URL: <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml>

关键原始返回：

```xml
<latest>9.5.0-alpha01</latest>
<release>9.5.0-alpha01</release>
...
      <version>9.4.0-alpha08</version>
      <version>9.4.0-rc01</version>
      <version>9.5.0-alpha01</version>
    </versions>
    <lastUpdated>20260817140736</lastUpdated>
```

- `lastUpdated = 20260817140736` → 2026-08-17 14:07 UTC（本次复查距上次更新 ≤ 2 天）
- 最新（含 pre-release）: **`9.5.0-alpha01`**
- 最新 RC: `9.4.0-rc01`
- 最新 stable（非 alpha/beta/rc）: **`9.3.1`**（08-12 时即如此，未变）
- **08-12 之后新增加的 AGP 版本**: `9.4.0-rc01`、`9.5.0-alpha01`（08-12 时最新为 `9.4.0-alpha08`）

> 注: Google 的 `<release>` 字段对 AGP 仍把 alpha 计入 release（此处 `9.5.0-alpha01`）。
> 判断 "stable" 以人工排除 alpha/beta/rc 为准 → `9.3.1`。

### 2.2 AGP POM 中内嵌的 Kotlin 版本（决定性证据）

```bash
curl -s https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.5.0-alpha01/gradle-9.5.0-alpha01.pom \
  | grep -iE 'kotlin|<version>|<artifactId>'
```

来源 URL: <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.5.0-alpha01/gradle-9.5.0-alpha01.pom>

关键原始返回（节选 Kotlin 相关行）：

```xml
        <artifactId>symbol-processing-gradle-plugin</artifactId>
        <version>2.2.10-2.0.2</version>
      ...
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>2.2.10</version>
      ...
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-gradle-plugin</artifactId>
      <version>2.2.10</version>
```

对三个 AGP 版本逐个比对（POM 中 `org.jetbrains.kotlin:kotlin-gradle-plugin` 与
`kotlin-stdlib` 的 `<version>`）：

| AGP 版本 | kotlin-stdlib | kotlin-gradle-plugin | symbol-processing-gradle-plugin (KSP) | 来源 POM URL |
|----------|--------------|----------------------|---------------------------------------|--------------|
| 9.4.0-alpha08（08-12 基线） | 2.2.10 | 2.2.10 | 2.2.10-2.0.2 | <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.4.0-alpha08/gradle-9.4.0-alpha08.pom> |
| 9.4.0-rc01 | 2.2.10 | 2.2.10 | 2.2.10-2.0.2 | <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.4.0-rc01/gradle-9.4.0-rc01.pom> |
| 9.5.0-alpha01（最新） | 2.2.10 | 2.2.10 | 2.2.10-2.0.2 | <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.5.0-alpha01/gradle-9.5.0-alpha01.pom> |

**结论**: 从 9.4.0-alpha08 到 9.5.0-alpha01，AGP 内嵌 Kotlin 一直是 `2.2.10`，
KSP 也一直是 `2.2.10-2.0.2`（与本项目 `libs.versions.toml` 完全一致）。
**没有任何 AGP 版本内嵌 Kotlin 2.3.x 或 2.4.x。**

> 方法论注记: AGP 的 `builtInKotlin` 只有一个 `android.builtInKotlin` 开关，
> **没有** `builtInKotlinVersion` 覆盖属性（08-12 §2.2 已验证）；内置版本由 AGP
> POM 的 `kotlin-gradle-plugin` runtime 依赖硬编码，不可用户覆盖。因此 POM 里的
> 版本即 builtInKotlin 实际使用的版本，是本调查的决定性证据，比官方 release notes
> 文本更权威（release notes 页面为 JS 渲染，且 POM 是构建实际解析的产物）。

### 2.3 Kotlin 上游最新版本（`kotlin-gradle-plugin`）

```bash
curl -s https://plugins.gradle.org/m2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml
```

来源 URL: <https://plugins.gradle.org/m2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml>
（GitHub Releases API 交叉验证: <https://api.github.com/repos/JetBrains/kotlin/releases>）

关键原始返回：

```xml
<latest>2.4.20-RC</latest>
<release>2.4.20-RC</release>
...
<version>2.3.21-RC2</version>
<version>2.4.0</version>
<version>2.4.0-Beta1</version>...
<version>2.4.10</version>
<version>2.4.10-RC</version>...
<version>2.4.20-Beta1</version>...
<version>2.4.20-RC</version>
```

GitHub Releases（`prerelease` 字段交叉验证）：

| tag | prerelease | published_at |
|-----|-----------|-------------|
| v2.4.20-RC | true | 2026-08-12 |
| v2.4.10 | **false**（stable） | 2026-07-14 |
| v2.4.0 | false（stable） | 2026-06-03 |

- Kotlin 最新 stable: **`2.4.10`**（2026-07-14）
- Kotlin 最新 RC: `2.4.20-RC`（2026-08-12）
- Kotlin 2.3.0 stable、2.3.10/2.3.20/2.3.21 系列均已 GA。
- **与本项目的关系**: 无关。只要 AGP 内嵌 2.2.10，公网 Kotlin 2.3/2.4 走不进
  builtInKotlin 路径；走显式 `kotlin-android` 插件 + `builtInKotlin=false` 的备选
  路径在 08-12 已被证伪（见 §四风险 3）。

### 2.4 Compose BOM / Compose / material3（复查 AOSP 源码约束是否松动）

```bash
curl -s https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml   # BOM
curl -s https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/maven-metadata.xml  # compose-foundation
curl -s https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/maven-metadata.xml   # material3
curl -s 'https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/1.5.0-alpha26/material3-1.5.0-alpha26.pom' | grep -iE 'compose|<version>'
```

来源 URL:
- BOM: <https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml>
- foundation: <https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/maven-metadata.xml>
- material3: <https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/maven-metadata.xml>
- material3 alpha26 POM: <https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/1.5.0-alpha26/material3-1.5.0-alpha26.pom>

关键原始返回：

- Compose BOM 最新: **`2026.08.00`**
- compose-foundation: 最新 `1.13.0-alpha01`；最新 stable **`1.12.0`**；`1.11.4` 仍在列
- material3: 最新 `1.5.0-alpha26`；最新 stable `1.4.0`
- material3 `1.5.0-alpha26` POM 的 Compose 依赖:

```xml
      <groupId>androidx.compose.material</groupId>
      <artifactId>material-ripple</artifactId>
      <version>1.12.0-beta01</version>
      <groupId>androidx.compose.runtime</groupId>
      <artifactId>runtime</artifactId>
      <version>1.12.0-beta01</version>
      <groupId>androidx.compose.foundation</groupId>
      <artifactId>foundation</artifactId>
      <version>1.12.0-beta01</version>
```

**结论（AOSP 源码约束未松动）**: AOSP SystemUI 源码使用 `ExperimentalAnimatableApi`
（见 `ContainerReveal.kt` 等），该 API 在 Compose `1.12.0` 起被移除（08-12 §2.3 已
验证 1.12.0-alpha01/rc01 均已移除）。因此：

- **Compose 上限仍为 `1.11.4`**（与 08-12 一致，未变）
- **material3 上限仍为 `1.5.0-alpha18`**（依赖 Compose 1.11.0-beta02，兼容 1.11.4；
  alpha19+ 依赖 1.12.0-beta01，与我们 1.11.4 cap 不兼容）
- material3 `1.5.0-alpha26` 仍依赖 Compose `1.12.0-beta01` → 不可用

> Compose 这条约束与 Kotlin 2.3 解锁**互相独立**：即便将来 AGP 内嵌 Kotlin 2.3，
> Compose 上限仍受 `ExperimentalAnimatableApi` 约束停在 1.11.4，除非 AOSP 上游改写
> 源码移除对 `ExperimentalAnimatableApi` 的依赖（属规则 R/规则 S 的源码对齐范畴，
> 不在本调研范围）。

---

## 三、版本对照表（08-12 vs 08-19）

| 组件 | 08-12 实测 | 08-19 实测 | 变化 | 来源 |
|------|-----------|-----------|------|------|
| AGP 最新（含 pre-release） | 9.4.0-alpha08 | **9.5.0-alpha01** | +9.4.0-rc01, +9.5.0-alpha01 | [maven-metadata](https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml) |
| AGP 最新 stable | 9.3.1 | **9.3.1** | 不变 | 同上 |
| AGP 内嵌 Kotlin | 2.2.10 | **2.2.10** | **不变（阻塞未解除）** | [9.5.0-alpha01 POM](https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.5.0-alpha01/gradle-9.5.0-alpha01.pom) |
| AGP 内嵌 KSP | 2.2.10-2.0.2 | **2.2.10-2.0.2** | 不变 | 同上 |
| Kotlin 最新 stable | （08-12 未直接查 Kotlin 上游） | **2.4.10**（2026-07-14） | 上游已到 2.4.x | [GitHub releases](https://api.github.com/repos/JetBrains/kotlin/releases) |
| Kotlin 最新 RC | — | 2.4.20-RC（2026-08-12） | — | 同上 |
| Compose BOM 最新 | — | 2026.08.00 | — | [BOM metadata](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml) |
| Compose foundation 最新 stable | 1.11.4 | **1.12.0**（+1.13.0-alpha01） | 上游已到 1.12.0 stable | [foundation metadata](https://dl.google.com/dl/android/maven2/androidx/compose/foundation/foundation/maven-metadata.xml) |
| **本项目 Compose 上限** | 1.11.4 | **1.11.4** | **不变**（`ExperimentalAnimatableApi` 约束） | 08-12 §2.3 |
| material3 最新 | 1.5.0-alpha18 | 1.5.0-alpha26 | 上游走到 alpha26 | [material3 metadata](https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/maven-metadata.xml) |
| **本项目 material3 上限** | 1.5.0-alpha18 | **1.5.0-alpha18** | **不变**（依赖 Compose 1.11.x） | [material3 alpha26 POM](https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/1.5.0-alpha26/material3-1.5.0-alpha26.pom) 证 alpha26 依赖 1.12.0-beta01 |

**与 08-12 的差异说明**: 唯一实质差异是 AGP 多了 `9.4.0-rc01` 与 `9.5.0-alpha01`
两个 pre-release、以及 Compose 上游从 1.11.4 走到了 1.12.0 stable。但**这两条变化
都没有解除 Kotlin 2.3 阻塞**：AGP 内嵌 Kotlin 仍是 2.2.10；Compose 上限仍因
`ExperimentalAnimatableApi` 停在 1.11.4。08-12 §八 遗留问题 #4（"AGP 适配 Kotlin 2.3.x
后可再次升级"）的状态：**未达成**。

---

## 四、阻塞根因与备选路径为何仍不可行

### 4.1 主路径（builtInKotlin=true）

本项目 [AGENTS.md §4.3 版本矩阵](../../AGENTS.md) 与
[08-12 迁移记录](../issues/2026-08-12-deps-upgrade-builtin-kotlin.md) 使用
`android.builtInKotlin=true`，Kotlin 版本完全由 AGP 内嵌决定。AGP 9.5.0-alpha01
仍内嵌 2.2.10 → 主路径无法上 Kotlin 2.3。**根因未消除。**

### 4.2 备选路径（显式 kotlin-android 插件 + builtInKotlin=false）— 仍不可行

08-12 §2.2 尝试 Kotlin 2.2.21 + 显式 `kotlin-android` 插件覆盖内置版本，失败：

```
ClassCastException: ApplicationExtensionImpl$AgpDecorated_Decorated
  cannot be cast to BaseExtension
```

根因: Kotlin 插件与 AGP 9.x 的 `newDsl`（默认开启、不可关闭）不兼容。本次复查未发现
Kotlin 官方宣布修复该 incompatibility 的 release notes；且即便修复，重新切回显式插件会
**重新引入 08-12 §一/§七 已解决的 Compose inline IR 问题**（`Couldn't inline method
call: Box$default`，builtInKotlin 才让它消失，见 [AGENTS.md §2.4](../../AGENTS.md)）。
因此备选路径不作为解锁备选。

### 4.3 Compose inline / KSP / data-class copy 的连锁风险（供"解锁后"预案参考）

即便将来 AGP 内嵌 Kotlin 2.3，升级也不是无脑切换，至少要同时复核：

1. **Compose inline IR**: 08-12 验证 builtInKotlin + Compose 1.11.4 组合下 inline
   问题已消失；切到 Kotlin 2.3 + 内置 Compose compiler 须重新验证 `Box$default`
   等 inline 不复发（[AGENTS.md §2.4](../../AGENTS.md)）。
2. **KSP 版本**: 须改为对齐 Kotlin 2.3 的 `2.3.x-2.0.2`（或当时最新），并重跑
   `:SystemUI-core:kspDebugKotlin` 0 错误基线（08-12 §七）。
3. **Data class copy 可见性**: Kotlin 2.2 起将 "Treat 'copy' calls of a data class
   as explicit constructor usages" 落地（YouTrack
   [KT-72722](https://youtrack.jetbrains.com/issue/KT-72722)，见
   [Kotlin 2.2.0 release notes](https://github.com/JetBrains/kotlin/releases/tag/v2.2.0)）；
   AOSP SystemUI 源码里若存在构造器可见性比 `copy()` 受限的 data class，在 2.2+/2.3
   下会变 deprecation 乃至 error。本项目 [AGENTS.md §4.4 待解决 #2](../../AGENTS.md)
   已把 "Kotlin 2.3 data-class copy 可见性" 列为 Deferred Follow-up，升级时须实测。
4. **`android.disallowKotlinSourceSets=false`** 等实验回退开关在 Kotlin 2.3 + 新 AGP
   下是否仍有效（08-12 §五问题 1-3 的三件套依赖它）。
5. **Compose 上限独立约束**（§2.4 结论）：与 Kotlin 解锁无关，仍停在 1.11.4。

> 以上仅是 "解锁后" 的风险清单预读，**本次不实施任何升级**（结论 (a)）。

---

## 五、下次复查触发条件

满足以下**任一**条件时重新跑本调研的 §二 查询：

1. **AGP 有新版本发布**（Google Maven `maven-metadata.xml` 的 `lastUpdated` 推进），
   特别是出现 `9.5.0-alpha02`/`9.5.0-beta01`/`9.5.0-rc01` 或任何 `9.5.x`/`9.6.0-alpha`
   stable。复查命令:
   ```bash
   curl -s https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml | tail -20
   curl -s https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/<NEW_VER>/gradle-<NEW_VER>.pom | grep -iE 'kotlin-gradle-plugin|kotlin-stdlib|symbol-processing'
   ```
   **解锁判定**: 任一 AGP POM 的 `org.jetbrains.kotlin:kotlin-gradle-plugin`/`kotlin-stdlib`
   `<version>` 出现 `2.3.x` 或更高 → 阻塞解除，转结论 (b) 起草升级路径。
2. **AGP 官方 release notes 明确宣布内嵌 Kotlin 版本升级**（来源:
   <https://developer.android.com/build/releases/gradle-plugin>，注意页面为 JS 渲染，
   须以 POM 为准交叉验证）。
3. **Kotlin 官方宣布修复 "kotlin-android 插件 vs AGP newDsl" incompatibility**
   （YouTrack / Kotlin release notes），使 §4.2 备选路径重新可行——届时即便 AGP 未
   内嵌 2.3，也可重新评估显式插件路径（但仍须同时解决 Compose inline 复发风险）。
4. **定期复查**: 每 ~30 天，或当下次触动 [AGENTS.md §4.3 版本矩阵](../../AGENTS.md)
   时，顺手跑一次 §二 查询。

**当前判定**: 以上 1–3 均未触发 → 维持现状（Kotlin 2.2.10 / KSP 2.2.10-2.0.2 /
Compose 1.11.4 / material3 1.5.0-alpha18 / AGP 9.3.1）。

---

## 六、本次未实施的操作（对齐 Non-goals）

- 未改任何构建文件（`gradle/libs.versions.toml`、`settings.gradle.kts`、
  `*/build.gradle.kts`、`gradle.properties`）。
- 未改任何依赖版本、未改任何源码、未改任何 res。
- 未跑本项目 Gradle 构建（只做了公网 `curl` 查询与 GitHub API 查询）。
- 本文件是本次产出**唯一**的新文档（对齐 brief Allowed Paths）。

---

## 七、证据可复查性

每个版本号均有可复查的公网 URL（见 §二 各小节"来源 URL"与 §三"来源"列）。复核
者直接 `curl` 上述 URL 即可得原始返回；POM 证据（§2.2 三表）是构建实际解析的产物，
比 release notes 文本更权威。
