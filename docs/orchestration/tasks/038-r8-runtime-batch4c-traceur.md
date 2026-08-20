# Task 038 Brief: R8 Runtime Closure — Batch 4C（Traceur 双 AAR）

## Startup (MANDATORY)

1. Read `/home/conv/myspace/SystemUI-Gradle/AGENTS.md` — focus: §〇.二 ADR、§一（规则 P/S/C/F/R/B）、§2.4（SysUISdk）、§八（用户偏好）。
2. Read `/home/conv/myspace/SystemUI-Gradle/docs/orchestration/CHARTER.md` — 特别：Part 4 构建串行纪律（你是本批唯一构建者）、Part 5 红线、Part 6 验证纪律。
3. Read this brief.
4. Output `CONTRACT:` block per worker-contract skill.

## Context

- Issue: `docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md`（**先读**：AOSP 结构事实、640 类构成、闭合性实证、风险）
- Plan: `docs/superpowers/plans/2026-08-20-r8-runtime-batch4c-traceur.md`（Task 0-6）
- 前置批次先例：`docs/issues/2026-08-20-r8-runtime-batch4b-wmshell-proto.md`（static_libs 并入 AAR 的同类做法）

本批是**第一个含真实 res 的 AAR 批次**：TraceurCommon（640 类 + manifest）+ Traceur-res（105 res + namespace `com.android.traceur.res`），直接 AAR 引入（ADR 0001），退役 `libs/TraceurCommon.jar` / `libs/traceur-res-R.jar`。

## Read First (in order)

- `docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md`（完整事实）
- `tools/package_aosp_aar.py` + `tools/tests/test_package_aosp_aar.py`（现有 CONFIGS，特别 SettingsLibColor 的 `code=[]` res-only 形态；确认脚本对**无 res** 的支持情况）
- `SystemUI-core/build.gradle.kts` L195-197（待替换的两条 compileOnly）
- `/home/conv/myspace/aosp/packages/apps/Traceur/Android.bp`（bp 语义依据）

## Acceptance Criteria

- `python3 -m unittest discover -s tools/tests` 全绿（含新增用例）
- `libs/aars/TraceurCommon.aar`：恰好 640 类（`com/android/traceur/` 15 + `perfetto/protos/` 625，不相交并集）；manifest package=`com.android.traceur.common`；确定性哈希
- `libs/aars/Traceur-res.aar`：0 类；res 恰好 105 文件与 AOSP 一致；manifest package=`com.android.traceur.res`；R.txt 与 Soong 一致；确定性哈希
- 两 AAR 之间及与现有 jar/AAR 类集合零重叠
- `libs/TraceurCommon.jar`、`libs/traceur-res-R.jar` 已 `git rm` 且全仓无引用残留
- `./gradlew :app:assembleDebug` exit 0（`set -o pipefail` + tee 完整日志 + status 文件）——**硬门禁**
- APK 内 `com/android/traceur/` 15 类与 `perfetto/protos/` 625 类 defined；merged manifest 含 `android.permission.CONTROL_UI_TRACING`
- fresh `:app:minifyReleaseWithR8`：missing_rules 88→81，removed 恰为 7 个 traceur 目标、added=0、`com.android.aconfig.annotations.AssumeTrueForR8` 保留
- `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §4.2 A7 行更新为实际值
- 最终 `git status` clean；commit message 英文

## Non-goals

- 不处理 SettingsLib 74 / B1-B4 / AssumeTrueForR8
- 不新增任何 androidx 坐标（现状已闭合）；若资源链接失败 → **HALT 上报**，不得自行加依赖
- 不改 res、不加 keep/-dontwarn、不本地 Maven 化（除非确认冲突并上报）
- 不 `git push`

## Failure Handling

- `:app:processDebugResources` 缺资源（leanback/v14）→ 停止，HALT 上报用户（新官方依赖需批准）
- R8 added≠0 或 removed 不恰为 7 个目标 → 停止并报告实测清单
- `perfetto_config_java_protos` 或 Traceur Soong 产物缺失/结构不符 → 停止并报告
- 脚本不支持无 res AAR → 最小扩展 + 测试；不得绕过脚本手打 zip

## Model + Resources

- 指定 `joycode/GLM-5.3`
- 本批为构建批：你是**唯一构建者**（CHARTER Part 4 串行纪律）；Gradle 守护进程 16G 已配置；`--rerun-tasks` 只用于 fresh 差分
- 完成给 HANDOFF 报告（HANDOFF: 标题）
