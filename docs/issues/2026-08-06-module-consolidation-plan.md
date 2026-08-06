# 13-module 架构实施计划

**日期**：2026-08-06

## 背景

`docs/architecture/2026-08-06-module-structure-audit.md` 已重新审定：当前 22 个 Gradle module 应按真实资源 namespace、复用 seam、依赖方向和构建工具链收敛为 13 个目标 module。实施前需要把该架构拆为可独立审查、可验证、可增量提交的任务，避免再次使用 BP target 数量机械搭脚手架。

## 操作步骤

1. 核对当前 settings、各 module build script、sourceSets、源码目录和依赖图。
2. 同步 ADR 0003、AGENTS/HANDOFF 等政策文档中的模块边界表述。
3. 将实施拆分为政策/对齐工具、源码 module 收敛、外部 JAR/AAR 清理与最终构建恢复三个阶段。
4. 为每个阶段列出精确文件、命令、预期证据和提交点。
5. 保存到 `docs/superpowers/plans/`，实施前由用户选择执行方式。

## 错误数演变

- 计划开始前：构建仍阻塞于 SettingsLib/iconloader/WindowManager-Shell AAR transform 重复 R 类，没有可信 Kotlin 错误数。
- 本阶段只编写计划，不修改 Gradle module、源码或资源，不运行源码编译。

## 待解决问题

1. 按实施计划执行政策同步、owner-aware 对齐工具和 13-module source topology。
2. `SystemUI-plugin-processor` 的 KAPT 接入是 fail-fast 检查点；失败时禁止恢复 `PluginProtectorStub.kt`，需询问用户选择工具链方向。
3. 13-module checkpoint 后另写 artifact recovery 计划，处理 SettingsLib/iconloader/WM Shell/WifiTrackerLib 直接 AAR 和重复 R transform。
4. 最终阶段再验证 manifest merge、core Kotlin 基线和 `:app:assembleDebug`。

## 计划产物

已保存可执行计划：

- `docs/superpowers/plans/2026-08-06-13-module-source-topology.md`

计划包含 10 个任务、58 个以上可追踪步骤和逐任务提交点。本计划只负责政策、源码/resource owner、animationlib AAR、compilelib JAR和 13-module 内部依赖图；既有四个大型 AAR 的恢复被明确拆为下一份独立计划。

## 计划阶段验证

- 未运行源码编译；本阶段只编写实施计划。
- 已核对当前 22 个 include module、目标 13 个 module、AOSP source roots、参考项目模块数及 animationlib/compilelib 中间产物。
- 计划占位符扫描和 Markdown code fence 检查通过。
- `git diff --check`：通过。

## 政策同步验证

- 未运行源码编译；本任务仅同步架构政策。
- `git diff --check`：通过。
- 当前构建阻塞仍为既有 AAR transform 重复 R 类。
- 目标 13-module 清单已写入 ADR 0003 决策 1、AGENTS.md §3.1、HANDOFF §2。
- animationlib 确认为非 SystemUI 代码，"源码化"方案废止，改为直接 AAR。
- kairos 确认为 test-only，不进本 APK 生产图。

## Task 2: 对齐脚本内容感知 + 目标 owner 感知

- 新增 `tools/tests/test_check_source_alignment.py`（8 个单测，全过）。
- 重写 `tools/check_source_alignment.py`：
  - 每条映射对应一个 AOSP source root → 目标 13-module 物理 source root
  - 新增 `diff_pair` 字节级内容比较（[MODIFIED] / [RES-MODIFIED]）
  - root-aware misplaced 判定（同 module 不同 source root 也算放错）
  - `--strict` 在任一 missing/misplaced/extra/modified/app/res 问题时退出 1
  - 移除 SURFACEEFFECTS_PREFIX / check_shader_lib（surfaceeffects 现归入 animation 映射）
- 红色基线（迁移未发生，`--strict` 退出 1）：
  - [MISSING] 212 / [MISPLACED] 162 / [EXTRA] 107 / [MODIFIED] 1046 / [RES-MISS] 2196
  - MODIFIED 1046 反映历史对 core/src 的 R import 规范化等改动，Task 8 重新同步 AOSP 后将归零

## Task 3: 合并 Common + Log + shared-utils

- 同步 AOSP `common/src`、`log/src`、`utils/src` → `SystemUI-common/{common,log,utils}/src`
  - common 3 文件、log 10 文件、utils 2 文件
- `SystemUI-common/build.gradle.kts` 改为 `java-library` + `kotlin.jvm`（JVM 21），
  三个 source root 合入 main sourceSet
- 依赖块按计划：`compileOnly(framework.jar)` + `tracinglib` + `api(kotlinx-coroutines-core)`
  + `implementation(kotlin.stdlib)` + `compileOnly(androidx.annotation)` + `implementation(errorprone)`
- 消费者重连：plugin `:SystemUI-log` → `api(:SystemUI-common)`；core 删除 `:SystemUI-log`；
  customization `:SystemUI-log` → `:SystemUI-common`（Task 5 再精简）
- `settings.gradle.kts` 移除 `include(":SystemUI-log")`，删除 `SystemUI-log/` 目录
- **验证结果（用户裁决：保留错误，继续）**：
  - `:SystemUI-common:compileKotlin` FAILED
  - `e: LogMessage.kt:19 Unresolved reference 'icu'`
  - `e: LogMessage.kt:101 Unresolved reference 'SimpleDateFormat'`
  - 根因：JVM 模块无 AGP android.jar；`android.icu.text.SimpleDateFormat` 只在 SysUISdk
    android.jar，不在 framework.jar。计划依赖块未列 android.jar。
  - 用户明确：严格按计划执行，此错误先保留，不修复，继续后续任务。

## Task 4: animationlib 直接 AAR + Shader 源码合并

- 新增 `tools/package_aosp_aar.py`（严格直接-AAR 打包器）+ `tools/tests/test_package_aosp_aar.py`（8 单测全过）
  - 合并 Soong javac + kotlin JAR；拒绝 R.class；重复非 MANIFEST entry 报 DuplicateEntryError
  - res 字节级复制；不生成 POM；不触碰 libs/maven/
- 生成 `libs/aars/animationlib.aar`（19677 bytes，含 Animations/Interpolators，无 R.class）
- 同步 AOSP `animation/src`（54 文件，含 22 surfaceeffects）+ `animation/res`（4 文件）→ SystemUI-animation
- 消费者重连：animation/customization `api(files(aars/animationlib.aar))`；compose-core `implementation(files(...))`
- 删除 `:SystemUI-animationlib` 模块、`libs/animationlib.jar`；settings 移除 include
- 清理 AGENTS.md §3.2、README.md、scripts/scaffold 中的旧引用
- **验证**：`:SystemUI-animation:compileDebugKotlin` BUILD SUCCESSFUL（仅警告）
- 对齐：MISSING 175（↓37）、MISPLACED 162、EXTRA 107、MODIFIED 1046
