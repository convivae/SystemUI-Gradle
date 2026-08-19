# 实验：移除 `android.disallowKotlinSourceSets=false`

- 任务: `docs/orchestration/tasks/023-disallow-kotlin-sourcesets.md`
- 授权: 用户 2026-08-19 授权做移除实验
- 实际执行日: 2026-08-20（brief 用 2026-08-19 命名文件，本文件路径遵循 brief 的 Allowed Paths）
- 权限: self-commit（gradle.properties 不在 CHARTER Part 5 红线区；非依赖版本矩阵）

## 背景

`gradle.properties` 中 `android.disallowKotlinSourceSets=false` 是 builtInKotlin 迁移
（2026-08-12 Task 1–6）时为让 KSP 插件通过 `kotlin.sourceSets` 添加生成源码目录而加的实验性
开关。AGP 9.3.1 每次构建在配置阶段都打印 experimental 警告。本实验评估在当前工具链
（AGP 9.3.1 + KSP 2.2.10-2.0.2 + Gradle 9.5.0）下能否安全移除该开关。

关键事实（来自基线警告文本）：AGP 提示 **"The current default is 'true'"**，即不显式设置时
默认值为 `true`（= disallow），将阻止插件操作 `kotlin.sourceSets`。移除 `=false` 覆盖后，
默认 `true` 生效 → 可能导致 KSP 无法注册生成源码目录。本实验用真实构建验证。

## 实验前 gradle.properties 相关片段

```properties
android.builtInKotlin=true
# 允许 KSP 插件通过 kotlin.sourceSets 添加生成源码；builtInKotlin 下需允许此操作
android.disallowKotlinSourceSets=false
ksp.incremental=false
```

## 步骤 1 — 基线（未改动）

命令:
```
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --console=plain
```

结果:
```
BUILD SUCCESSFUL in 3m 34s
89 actionable tasks: 89 executed
```

experimental 警告（基线日志 line 4，`> Configure project :app` 阶段）:
```
WARNING: The option setting 'android.disallowKotlinSourceSets=false' is experimental.
The current default is 'true'.
Add android.sync.suppressAgpWarnings=UNSUPPORTED_PROJECT_OPTION_USE to the gradle.properties file to suppress this warning.
```

→ 基线确认: KSP + Kotlin 编译均成功，且 AGP 确实每次打印 experimental 警告。

## 步骤 2 — 删除开关

删除 `gradle.properties` 中的注释行 + `android.disallowKotlinSourceSets=false` 行。
（实验失败时 `git checkout -- gradle.properties` 恢复。）

## 步骤 3 — 全量验证（实验改动后）

### 3.1 KSP debug + release（--rerun-tasks）

命令:
```
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:kspReleaseKotlin --rerun-tasks --console=plain
```

结果: **BUILD FAILED in 1s**（配置阶段失败，未进入任务执行）。

失败任务/阶段: `A problem occurred configuring project ':SystemUI-core'.`

首条错误（完整）:
```
> Using kotlin.sourceSets DSL to add Kotlin sources is not allowed with built-in Kotlin.
  Kotlin source set 'debug' contains: [/home/conv/myspace/SystemUI-Gradle-wt-023/SystemUI-core/build/generated/ksp/debug/kotlin, /home/conv/myspace/SystemUI-Gradle-wt-023/SystemUI-core/build/generated/ksp/debug/java]
  Solution: Use android.sourceSets DSL instead.
  For more information, see https://developer.android.com/r/tools/built-in-kotlin
  To suppress this error, set android.disallowKotlinSourceSets=false in gradle.properties.
```

experimental 警告检查: 改动后日志中**不再出现** `WARNING: The option setting 'android.disallowKotlinSourceSets=false' is experimental.`
（因为开关已被删除），但代价是 KSP 直接在配置阶段失败。AGP 自己的错误提示即要求重新设置
`android.disallowKotlinSourceSets=false`。

### 3.2 后续构建命令

由于 3.1 已在配置阶段失败（`BUILD FAILED in 1s`），且失败明确与该开关相关
（AGP 错误文本直接指向 `android.disallowKotlinSourceSets=false`），按 brief 判定条款
立即进入失败路径，**不再执行** `compileDebugKotlin`/`compileDebugJavaWithJavac`/
`:app:assembleDebug`——保留删除态重跑只会复现同一配置失败，无新证据。

### 3.3 Python 工具测试

命令:
```
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

结果:
```
Ran 148 tests in 34.116s
OK
```
（exit 0；与 brief Acceptance 期望的 148 一致；与 AGENTS.md §4.2 记录的 131 相比新增了
17 个测试，本实验未改动 tools/，数量增长来自先前其他任务。）

### 3.4 恢复 gradle.properties

命令:
```
git checkout -- gradle.properties
```

验证恢复: `git diff -- gradle.properties` 输出为空（与基线字节一致），`cat gradle.properties`
重新出现:
```
# 允许 KSP 插件通过 kotlin.sourceSets 添加生成源码；builtInKotlin 下需允许此操作
android.disallowKotlinSourceSets=false
```

（未在恢复后重跑 Gradle 构建: 基线已证明带开关可 BUILD SUCCESSFUL，且 `git diff` 为空
证明恢复后与基线字节一致，重跑只会复现基线，无新信息。如架构师要求可再跑一次确认。）

## 判定

**结论: 该开关在当前工具链（AGP 9.3.1 + KSP 2.2.10-2.0.2 + Gradle 9.5.0）下仍为必需，不可移除。**

依据:
1. 移除 `android.disallowKotlinSourceSets=false` 后，AGP 默认值 `true`（disallow）生效；
2. KSP 在配置阶段即失败（`BUILD FAILED in 1s`），错误明确为
   `Using kotlin.sourceSets DSL to add Kotlin sources is not allowed with built-in Kotlin`，
   且 AGP 自身给出的 solution 就是重新设置该开关；
3. 失败明确与该开关相关（满足 brief 失败路径判定），故执行恢复 + 仅文档 commit。

根因: SystemUI-core 的 KSP 配置（`SystemUI-core/build.gradle.kts`）通过 `kotlin.srcDirs(...)`
把 KSP 生成目录（`build/generated/ksp/<variant>/kotlin` 与 `/java`）加入 kotlin sourceSet，
使 KSP 生成的 Kotlin 源码参与 Kotlin 编译。builtInKotlin 下 AGP 默认禁止插件用
`kotlin.sourceSets` DSL 添加源码，必须显式 `disallowKotlinSourceSets=false` 才能放开。
要真正移除该开关，需先把 KSP 生成目录迁移到 `android.sourceSets` DSL（AGP 提示的
`Solution: Use android.sourceSets DSL instead`），这超出本 brief 的 Non-goals
（不改 KSP/sourceSets 配置），应作为独立任务与用户讨论。

## 后续建议（非本 brief 范围）

若未来希望消除该 experimental 警告，可选路径（均需用户决策 + 独立 brief）:
- A. 把 SystemUI-core 的 KSP 生成源码目录从 `kotlin.srcDirs` 迁到 `android.sourceSets`
  （AGP 推荐方案）；需评估对其它已 `kotlin.srcDirs(...)` 对齐 java.srcDirs 的模块的影响；
- B. 等待 AGP 把该开关稳定化 / 改默认值；
- C. 用 `android.sync.suppressAgpWarnings=UNSUPPORTED_PROJECT_OPTION_USE` 仅抑制警告文本
  （AGP 警告本身给出的临时抑制手段），但开关仍需保留——不消除根因，仅消音。

本实验结论: **保留现状，开关不可移除。**
