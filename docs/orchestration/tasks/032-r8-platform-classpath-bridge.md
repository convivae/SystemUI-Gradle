# Task 032 — R8 platform/library classpath 与 SysUISdk bridge 研究（B 类）

## Authority

`self-commit`，report-only。用户于 2026-08-20 批准：优先用声明式 SysUISdk/library
classpath 解决平台类，只有无受支持通道时才允许对 Aconfig 注解使用单条精确 dontwarn。
本任务不实施修改。worker 不 push。

## Goal

对 Task 030 的四个 B 类 missing classes 给出基于 AGP/R8/Soong/SysUISdk primary source
的最小、可复现解决方案，避免将真实 runtime 缺口误标为 dontwarn。

## Scope

- `android.compat.annotation.UnsupportedAppUsage`
- `libcore.io.IoUtils`
- `libcore.util.NativeAllocationRegistry`
- `com.android.aconfig.annotations.AconfigFlagAccessor`

## Required Analysis

1. 证明每个类的 AOSP owner、retention/runtime 语义、设备是否提供、AOSP Soong R8 为什么可见。
2. 核对 AGP 9.3.1/R8 的 app shrinker 输入：compileSdk android.jar、runtime dependencies、
   compileOnly dependencies；找受支持的 additional library classpath/public DSL，禁止依赖未文档化 hack。
3. 核对 live 与声明式 SysUISdk：上述类当前是否存在；若补入，具体从哪个 AOSP 编译产物提取、
   `tools/build_sysuisdk.py` 需要什么 manifest/stage/test，是否可能污染 Kotlin/Compose 或 APK。
4. 比较方案：
   - SysUISdk android.jar library class；
   - AGP/R8 supported library input；
   - runtime `implementation`（通常不应把 platform/build annotation 打进 APK）；
   - 精确 `-dontwarn`。
5. 推荐顺序应遵循用户批准：前三个优先声明式 SysUISdk；Aconfig 先找受支持 library 通道，
   若不存在，只建议精确
   `-dontwarn com.android.aconfig.annotations.AconfigFlagAccessor`，单独 Gradle bridge 文件，
   不修改 byte-exact AOSP flags。
6. 给出实施 task 的 exact allowed paths、验证命令和失败/回滚标准。

## Primary Sources

- AOSP class source/Android.bp/Soong shrinker implementation
- AGP 9.3.1 本地 API/source JAR、R8 官方文档/源码
- `tools/build_sysuisdk.py` 与 SysUISdk reproducibility docs/tests
- 禁用二手博客作为结论依据

## Allowed Paths

- `docs/architecture/2026-08-20-r8-platform-classpath-bridge.md`
- `docs/issues/2026-08-20-release-r8-alignment-decisions.md`（仅添加研究链接/摘要）
- `docs/orchestration/tasks/032-r8-platform-classpath-bridge.md`

## Forbidden Paths

- SysUISdk/live SDK、`tools/**`、`app/build.gradle.kts`、ProGuard 文件
- `libs/**`、依赖配置、`src/**`、`res/**`

## Acceptance

- 四个类逐项有 owner/retention/device/Soong/AGP 证据。
- 明确 AGP 9.3.1 是否有受支持 library-classpath 通道，不猜测。
- 推荐方案可由 `tools/build_sysuisdk.py` 声明式重建并有 exact tests。
- dontwarn 若被推荐，只能是 Aconfig 单类、作为最后手段，并说明为何安全。
- `git diff --check` 干净；仅 Allowed Paths 变化。

## Reports To

架构师。English commit、never push、HANDOFF，区分已证实事实与待验证假设。
