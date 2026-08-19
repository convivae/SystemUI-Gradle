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
