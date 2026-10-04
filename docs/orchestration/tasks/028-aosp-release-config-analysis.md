# Task 028 — AOSP Release 构建配置深度分析 + 我方 release 对齐建议（只读研究）

## Goal

用户 2026-08-20 指示：AOSP 编译 SystemUI 的 release 时到底有哪些配置项？逐项分析后
对比我方 Gradle 配置，给出"尽可能与 AOSP 编译流程一致"的 release 写法建议。
**只读研究 + 报告，不改任何构建文件**（修复落地待用户批准后另行实施）。

## 分析范围（AOSP 侧，`/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/`）

### a. Release 编译哪些代码
- `android_app "SystemUI"`、`java_library "SystemUI-core"` 的 `srcs`/`exclude_srcs`
- `product_variables.debuggable` 分支：`:DebugJavaFiles` vs `:ReleaseJavaFiles`
  filegroup 的具体文件清单与内容（`grep -n "DebugJavaFiles\|ReleaseJavaFiles" Android.bp`）
- 对应我方：`SystemUI-core/src-release/` 4 个 .kt、`libs/compilelib-{debug,release}.jar`

### b. 哪些地方加优化 / c. 哪些加混淆
- `SystemUI_optimized_defaults`（soong_config，`SYSTEMUI_OPTIMIZE_JAVA` 变量）：
  谁设置该变量、默认值、true/false 各启什么（optimize/shrink/shrink_resources/
  optimized_shrink_resources/ignore_warnings/proguard_compatibility）
- `platform_app_defaults` defaults 链里与 optimize 相关的配置
- `proguard.flags` → `proguard_common.flags` → `proguard_kotlin.flags` 包含链的
  每条规则语义（keep 谁、strip 什么 log、assumenosideeffects 哪些）
- AOSP 里 SystemUI-core（java_library）层是否确实**零** proguard 配置（复核）
- plugin/shared/plugin_core 各自的 proguard flags 文件（proguard_plugins.flags、
  proguard_flags.flags、plugin_core/proguard.flags）如何进最终构建

### d/e. Debug-only vs Release-only
- `product_variables.debuggable` 在 Soong 的触发条件（eng/userdebug vs user）
- compilelib 的 src-debug/src-release（IS_DEBUG 常量）如何被选择
- Soong 里还有没有其他按 build variant 切换 SystemUI 行为的机制
  （如 `systemui_optimized_java_defaults` 之外的 soong_config、aconfig 的 release 模式）

### f. 其他 release 相关
- dex 配置（dexpreopt、dex2oat）、`use_resource_processor`、aapt 标志、
  manifest placeholder、签名（certificate: "platform"）在 user 构建的差异

## 对比侧（我方）

逐项对比 `app/build.gradle.kts`、`SystemUI-core/build.gradle.kts` 的
buildTypes{debug,release}、isMinifyEnabled、proguardFiles、sourceSets、
compilelib jar 选择、签名，输出 **gap 表**：AOSP 行为 vs 我方行为 vs 建议。

## 交付物

- `docs/architecture/2026-08-20-aosp-release-config-analysis.md`：
  AOSP 配置逐项分析（a–f）+ gap 表 + release 写法建议（含已知问题：
  core 悬挂 consumer-rules.pro/proguard-rules.pro 引用的处理建议）
- `docs/issues/2026-08-20-assemble-release-verification.md` 追加链接（只加一行引用）

## Non-goals

- 不改任何 build 文件 / 源码 / res / 配置（纯研究）
- 不跑全量构建（允许只读查看与 grep；如需验证性构建限 `:SystemUI-core:tasks` 级别）

## Allowed Paths

- `docs/architecture/2026-08-20-aosp-release-config-analysis.md`（新建）
- `docs/issues/2026-08-20-assemble-release-verification.md`（仅追加一行链接）
- `docs/orchestration/tasks/028-aosp-release-config-analysis.md`（本文件勾选）

## Forbidden Paths

其它一切。

## Acceptance

- 报告覆盖 a–f 全部六项，每项有 AOSP 文件路径 + 行号证据；
- gap 表完整；release 写法建议具体（哪行改成什么）；
- 英文 commit；不 push。

## Report

完成后汇报：commit、gap 表摘要、release 建议要点、HANDOFF 块。
