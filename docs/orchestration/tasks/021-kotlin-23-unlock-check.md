# Task 021 — 重查 AGP/Kotlin/Compose 上游版本（Kotlin 2.3 解锁核查）

## Goal

只读调研（用户 2026-08-19 批准）：重查公网 Maven 元数据，判断"Kotlin 2.3 升级"
是否仍被 AGP 阻塞：

1. `com.android.tools.build:gradle` 的 maven-metadata.xml —— 最新 stable/alpha 版本；
2. 对最新 AGP 版本，查其内置 Kotlin 版本（官方文档 release notes 或 AGP 的
   `gradle/dependency-locks` / 公告；也可参考 `androidx.compose.compiler` 兼容矩阵）；
3. Kotlin 当前最新 stable 版本（`org.jetbrains.kotlin:kotlin-gradle-plugin` metadata）；
4. Compose BOM 最新版与 Kotlin 2.2.10/2.3 的兼容情况；
5. 结论二选一：(a) 仍被阻塞 → 给出下次复查触发条件；(b) 已解锁 → 给出升级路径草案
   （版本矩阵 + 风险清单），**只出方案不实施**。

## Non-goals

- 不改任何构建文件、依赖版本、源码；
- 不实施升级；
- 不跑本项目 Gradle 构建（只允许读文件和网络查询）。

## Allowed Paths

- `docs/architecture/2026-08-19-kotlin-23-unlock-check.md`（新建，调研结果）
- `docs/orchestration/tasks/021-kotlin-23-unlock-check.md`（本文件勾选）

## Forbidden Paths

其它一切（只读 + 单一新文档）。

## Execution Hints

1. 先 worker-contract skill 输出 `CONTRACT:`；
2. 查询示例：
   `curl -s https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml`
   `curl -s https://plugins.gradle.org/m2/org/jetbrains/kotlin/...` 或 maven central metadata；
3. AGP ↔ Kotlin 内置版本对照可查官方 release notes
   （https://developer.android.com/build/releases/gradle-plugin）；
4. 引用 2026-08-12 旧结论 `docs/issues/2026-08-12-deps-upgrade-builtin-kotlin.md` 做对比；
5. 英文 commit；**不 push**。

## Acceptance

- 调研文档含：查询命令与原始返回摘要、版本对照表、明确结论 (a) 或 (b)、
  与 08-12 旧结论的差异说明；
- 每个版本号都有可复查的来源 URL。

## Report

完成后汇报：commit、结论 (a)/(b) 及证据、新发现、HANDOFF 块。

---

## Completion (2026-08-19, worker task 021)

**结论 (a) — 仍被阻塞。** 最新 AGP `9.5.0-alpha01`（Google Maven `lastUpdated`
2026-08-17）仍内嵌 Kotlin `2.2.10`（`kotlin-stdlib` 2.2.10 + `kotlin-gradle-plugin`
2.2.10 + `symbol-processing-gradle-plugin` 2.2.10-2.0.2）。与 08-12 结论无本质差异。

调研文档: `docs/architecture/2026-08-19-kotlin-23-unlock-check.md`

### Acceptance 勾选

- [x] 调研文档含查询命令与原始返回摘要
      — `docs/architecture/2026-08-19-kotlin-23-unlock-check.md` §二（curl 命令 + XML 节选）
- [x] 版本对照表
      — 同文档 §三（08-12 vs 08-19 对照表）
- [x] 明确结论 (a) 或 (b)
      — 同文档 §一：结论 (a) 仍被阻塞
- [x] 与 08-12 旧结论的差异说明
      — 同文档 §一末段 + §三：AGP 多了 9.4.0-rc01/9.5.0-alpha01 但内嵌 Kotlin 仍 2.2.10；
        Compose 上限仍 1.11.4（`ExperimentalAnimatableApi` 约束未松动）
- [x] 每个版本号都有可复查的来源 URL
      — 同文档 §二 各小节 + §七；关键来源:
        AGP metadata <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml>、
        AGP 9.5.0-alpha01 POM <https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/9.5.0-alpha01/gradle-9.5.0-alpha01.pom>、
        Kotlin GitHub releases <https://api.github.com/repos/JetBrains/kotlin/releases>、
        Compose BOM <https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/maven-metadata.xml>、
        material3 alpha26 POM <https://dl.google.com/dl/android/maven2/androidx/compose/material3/material3/1.5.0-alpha26/material3-1.5.0-alpha26.pom>、
        data-class copy YouTrack KT-72722 <https://youtrack.jetbrains.com/issue/KT-72722>

### Non-goals 遵守

- 未改任何构建文件 / 依赖版本 / 源码 / res；未跑本项目 Gradle 构建。
- 唯一新文档为 `docs/architecture/2026-08-19-kotlin-23-unlock-check.md`；
  未创建 `docs/issues/` 文件（brief Forbidden Paths 限定"只读 + 单一新文档"；
  本调研属 AGENTS.md §2.2 "复杂调研"，记于 `docs/architecture/` 即满足规则 D）。

### 新发现（08-12 之后）

1. AGP 新增 `9.4.0-rc01` 与 `9.5.0-alpha01`（08-12 时最新为 9.4.0-alpha08），
   但内嵌 Kotlin 未变（仍 2.2.10）。
2. Kotlin 上游已到 2.4.10 stable（2026-07-14）/ 2.4.20-RC（2026-08-12）。
3. Compose foundation 1.12.0 已 stable、1.13.0-alpha01 已发；但本项目受
   `ExperimentalAnimatableApi` 约束仍停在 1.11.4（与 Kotlin 解锁互相独立）。
4. material3 上游走到 alpha26（仍依赖 Compose 1.12.0-beta01，不可用）。

### 下次复查触发条件（详见调研文档 §五）

- AGP 新 pre-release/stable 出现时复查其 POM 的 `kotlin-gradle-plugin` 版本；
  出现 `2.3.x`+ 即解锁，转结论 (b) 起草升级路径。
- Kotlin 官方修复 "kotlin-android 插件 vs AGP newDsl" incompatibility 时重评备选路径。
- 每 ~30 天或触动 AGENTS.md §4.3 版本矩阵时顺手复查。
