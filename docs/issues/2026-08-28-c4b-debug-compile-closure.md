# Task 073 — C4b：编译闭环（`:app:assembleDebug` 恢复绿）

**日期**：2026-08-28
**任务**：docs/orchestration/tasks/073-c4b-debug-compile-closure.md
**前置**：C4a（task072 接线，`gradle help` 绿）、C2（task071 libs 再生）、C3（task070 源码重对齐）
**目标**：`:app:assembleDebug` **BUILD SUCCESSFUL**；对齐门/pytest 保持绿；新产物冻结指纹可复现。
Release/R8 归 task074；runtime 归 C5。

## 1. 计划

| 步骤 | 内容 |
|------|------|
| P0 | kairos 源码模块 `:SystemUI-utils-kairos`（tier①，拷贝 63 kt + JVM build 文件 + settings 注册 + 对齐工具映射 + core 依赖） |
| P1 | 新 tier② 产物：personalcontext_ace_visualizer AAR、SerialPortAccessDialog AAR、mechanics / mechanics-compose jar（tools 脚本扩展 + pytest + 冻结指纹） |
| P2 | 编译循环：`:app:assembleDebug`，按错误分类一次一个根因；新 flags 包按错误驱动补 `tools/package_aconfig_jars.py` |
| P3 | 验收：assembleDebug 绿 + `check_source_alignment.py --strict` exit 0 + pytest 全绿 |
| P4 | 文档收尾（错误数演变、bp 依据、CONV 对账、移交 task074 清单）+ STATE.md |

## 2. P0 记录：kairos 源码模块

- bp 依据：`packages/SystemUI/utils/kairos/Android.bp` — `java_library "kairos"`（JVM，无 res/manifest），
  srcs `src/**/*.kt`（63 文件），static_libs：kotlin-stdlib、kotlinx_coroutines、tracinglib-platform、
  androidx.collection_collection。tier①（规则 S）。
- 形态：仿 `:SystemUI-plugin-core`（`java-library` + `org.jetbrains.kotlin.jvm`，src 直根）。
- 依赖映射（Gradle）：
  - `android.os.Build/SystemProperties` → `compileOnly(files(libs/framework.jar))`
  - `com.android.app.tracing.*` → `compileOnly(files(libs/prebuilts/tracinglib-platform.jar))`（既有产物）
  - coroutines → `implementation(libs.kotlinx.coroutines.core)`
  - androidx.collection（ScatterMap/ObjectIntMap 族）→ `implementation(libs.androidx.collection)`
    （新 catalog alias `androidx-collection`，版本 1.5.0 = core 编译类路径当前解析版本，避免图漂移）
- 对齐工具映射新增：`M(["utils/kairos/src"], "SystemUI-utils-kairos", "src", note="kairos")`
  （brief §1 授权的唯一对齐工具编辑）。

## 3. P1 记录：新 tier② 产物

（待补）

## 4. 编译循环：错误数演变

（待补）

## 5. 验证记录

（待补）

## 6. CONV 对账

（待补）

## 7. 移交 task074 清单

（待补）
