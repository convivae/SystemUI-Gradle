# D5 — kairos → tier① 源码模块 `:SystemUI-utils-kairos`（63 kt，task073 P0，commit `4ac49993`）

status: done
判读: **符合**（附带：AGENTS.md §3.1 一处过时注释需修订——属用户所有文档，审计只记录）

## 背景与决策原文

kairos 的判定史：

| 时间 | 判据来源 | 结论 |
|---|---|---|
| 2026-07-29 | 源码化调研（`docs/architecture/2026-07-29-systemui-module-source-vs-jar.md` L44） | kairos 源"刚复制进 core"（+779 opt-in 错误，须 opt-in flag） |
| 2026-08-06 | 模块结构审计（`docs/architecture/2026-08-06-module-structure-audit.md` L369、L472-474） | "kairos 仅测试使用，core BP 不依赖"→ 删除模块、不进生产图（作为 13-module 决策被用户采纳，a5aa2831 ADR 0003 方向） |
| 16 时代收尾（dec85d64） | 实测：workspace 中零 kairos 源、零引用 `com.android.systemui.kairos.*` 的 core 文件（git 实测：dec85d64 全树 0 kairos 路径、0 引用） | 删无实证损失，16 debug 构建绿（CURRENT_STATE 当时记录） |
| 2026-08-28（C3 重对齐后） | 17 全量源码+17 bp | `SystemUI-core/src` 出现 57 个引用 kairos 的源文件；17 top bp L569 `"kairos"` 属 SystemUI-core static_libs → 生产依赖 |

task073 P0（commit `4ac49993`，brief 主题就点名"kairos source module"）：按规则 S/B 建
tier① 源码模块——`utils/kairos/src`（63 kt）拷贝为 JVM 模块（模块形态仿
`:SystemUI-plugin-core`）；core `implementation(project(":SystemUI-utils-kairos"))`；
对齐工具映射 M(`utils/kairos/src` → SystemUI-utils-kairos)，strict gate exit 0（commit 信息）。

## 决策链

| 环节 | 证据 |
|---|---|
| 17 bp 生产依赖实证 | AOSP `frameworks/base/packages/SystemUI/Android.bp` L569 `"kairos"`；awk 定位最近声明 = L476 `name: "SystemUI-core"`（17 tree HEAD `94b4c163b7df`，tag android-17.0.0_r1） |
| 16-era "不依赖"先例复核 | AOSP git：本地树曾停在 16 vintage（2025-03-26，commit `b110a8e0`）；`git show b110a8e0:packages/SystemUI/Android.bp` L540 `"kairos"` 同样属 SystemUI-core。**即 16 时代 bp 就写明了生产依赖**——审计 L369"core BP 不依赖"为 **事实性误判**（当时 workspace 恰好没有消费者所以无损失） |
| workspace 差异解释 | dec85d64（C3 前最后提交）：core src 零 kairos 引用；C3 重对齐（aa77057a/bdf2dba5）把 17 src 不漏不多拷贝进来后，57 个消费者入境 → 模块成为硬需求 |
| 执行 | `4ac49993`（settings include + JVM build 文件 + core 依赖 + 对齐映射） |

## 证据链

1. **17 bp**：`Android.bp:569` kairos 在 SystemUI-core static_libs；`utils/kairos/Android.bp:23`
   `java_library "kairos"`（JVM，无 res/manifest）。
2. **workspace 现状**：`SystemUI-utils-kairos/src/com/android/systemui/kairos/*` 63 kt；
   `SystemUI-utils-kairos/build.gradle.kts`（java-library+Kotlin JVM 21，deps：framework.jar
   compileOnly、tracinglib-platform.jar compileOnly、coroutines、androidx.collection 1.5.0）；
   `gradle/libs.versions.toml:80` androidx-collection 1.5.0 官方坐标（tier③ 优先级）。
3. **bp 静态依赖核对**：kairos bp 的 static_libs 四项（kotlin-stdlib/kotlinx_coroutines/
   tracinglib-platform/androidx.collection_collection）与 build 文件 1:1 对应。
4. **CURRENT_STATE L97**：已记录"16 时代 test-only 判定为误判，17 已是 SystemUI-core 生产依赖"——
   与本次 git 复核一致（并且误判在 16 vintage 就成立，甚至比"17 起才变"更早）。

## 备选路径

1. **tier② jar**（从 AOSP turbine/javac 产物打包 kairos 类）——违反规则 S（① judged by soong
   module location、`utils/kairos/**/Android.bp` 在 packages/SystemUI 内）；若选则会与源码化先例矛盾。
2. **复制进 core**（回到 2026-07-29 形态）——违反 ADR 0003 seam 判据（独立 soong target、
   单独工具链：纯 JVM、无 res/manifest）；名录上也不如独立模块清楚。
3. **所选**：独立源码 JVM 模块（tier① Standard 形态）——规则 S、规则 B、模块审计 seam 判据
   三项同时满足。

## 优劣分析

优点：规则 S 直接适用（soong module 位置=packages/SystemUI/**）；生产依赖有据（bp L569、57 消费者）；
对依赖交付用全官方/既有形态（androidx.collection 官方 1.5.0 而非自打包）；模块形态最小（JVM）。
缺点/风险：AGENTS.md §3.1 L273 旧注释"compilelib → debug/release JAR；kairos → test-only，不进本 APK
生产图"仍在现行规则文档中，与新现实矛盾（17-include 已 17 个模块，CURRENT_STATE L16 记：C4b 起追加
kairos）——规则文档的滞后与 E4 发现同类。

## 判读与建议

判读：**符合**——这是按正确判据（规则 S + 17 bp 事实）落地；确证 16 时代的 "test-only" 判定本身就是
对 16 vintage bp 的事实误判（当前 kairos 始终为 SystemUI-core 生产依赖），但当时 workspace 恰好没有
消费者，故未造成构建损失。

建议：
1. 修订 AGENTS.md §3.1 L273 与 §1.5 tier① 例子表（L85 已与 17 一致含 kairos——两节自相矛盾）；
   AGENTS.md 属红区（CHARTER Part 5.3），需用户批准。
2. 无其余动作。

## 开放问题

- AGENTS.md §1.5 L85（tier① 例表已含 kairos）与 §3.1 L273（"kairos → test-only"）自相矛盾，
  请在用户口径下统一。
</content>
