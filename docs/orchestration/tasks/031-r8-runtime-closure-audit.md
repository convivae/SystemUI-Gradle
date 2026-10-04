# Task 031 — R8 运行时依赖闭包逐类审计（A 类）

## Authority

`self-commit`，report-only。用户于 2026-08-20 批准修复 AOSP static_libs 对应的真实
runtime closure；本任务只形成精确实施图，不修改依赖或产物。worker 不 push。

## Goal

以 Task 030 的 140 个 R8 missing classes 为输入，逐类确认哪些属于真实 APK runtime
闭包（A 类），追溯到 owning Soong module 和通向 SystemUI 的 Android.bp edge，核对我方
JAR/AAR/compileOnly/implementation 状态，并形成无遗漏、无重复、可分批实施的修复计划。

## Primary Inputs

- `docs/issues/2026-08-20-release-r8-alignment-decisions.md`
- `docs/architecture/2026-08-20-aosp-release-config-analysis.md`
- `/tmp/task030-missing_rules.txt`（架构师从 Task 030 生成物保存；如不存在，用
  `./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` 重新生成）
- AOSP `frameworks/base/packages/SystemUI/Android.bp` 及每个 owner module 的 Android.bp
- `tools/package_aosp_aar.py`、`tools/package_aconfig_jars.py` 和当前 libs/build files

## Required Analysis

1. 解析全部 140 个 missing class；每个类必须恰好归属 A 类或 B 类，报告给出总数校验。
2. 对每个 A 类 class/group 记录：
   - owning source/Soong module；
   - 到最终 SystemUI app 的完整 `static_libs`/`libs` edge；
   - 是否含资源，从而判定 JAR/AAR/官方 Maven；
   - 当前 Gradle dependency scope 和当前 artifact 中是否真的包含该类；
   - 缺失原因（陈旧 header jar、javac/Kotlin/proto 未合并、compileOnly scope、传递闭包等）；
   - 修复策略、重复类风险、被替代产物/工具清理项。
3. 对标准第三方候选检查 Google Maven/Maven Central 官方 metadata；官方坐标优先，版本决策
   只做建议，不修改 catalog。
4. 对 SettingsLib、WM-Shell、iconloader 三个不完整 AAR 做 class-set 证据：缺失类、应合并
   的 Soong javac/Kotlin/proto 产物，以及资源 owner/冲突风险。
5. 对所有 `compileOnly` 候选逐项判断 AOSP 是 static runtime 还是 device-provided，禁止笼统
   把全部改 implementation。
6. 输出按依赖顺序的实现批次（每批 allowed paths、产物、工具测试、构建验收、清理项）。

## Allowed Paths

- `docs/architecture/2026-08-20-r8-runtime-closure-audit.md`
- `docs/issues/2026-08-20-release-r8-alignment-decisions.md`（仅添加审计链接/摘要）
- `docs/orchestration/tasks/031-r8-runtime-closure-audit.md`

## Forbidden Paths

- 所有 `build.gradle.kts`、`libs/**`、`tools/**`、`gradle/**`、SysUISdk
- `src/**`、`res/**`、AOSP 镜像
- 任何 keep/dontwarn 或依赖修复

## Acceptance

- 报告列出 140/140 missing classes 的唯一归属；A+B 总数相等且无 unclassified。
- 每个 A 类 group 有可复查的 Android.bp line/module 与 artifact class-set 证据。
- 所有官方 Maven 判断有 metadata/primary-source 证据。
- 实施批次明确区分 JAR、AAR、官方 Maven、SysUISdk/B 类，不含 stub/资源重写/dontwarn 绕过。
- `git diff --check` 干净；仅 Allowed Paths 变化。

## Reports To

架构师。English commit、never push、HANDOFF，报告真实命令与尚未确认项。
