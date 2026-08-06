# SystemUI 源码与资源对齐差异诊断

**日期**：2026-08-06
**方法**：systematic-debugging Phase 1-2（逐条核对 AOSP `Android.bp` 真实 owner，不按包名猜测）

## 结论摘要

脚本报告 13 missing + 7 extra src + 7 extra res，经核对 AOSP `Android.bp` 后**无一是简单的"漏/多"**，
全部归因于四类根因：脚本映射错误、违规源码复制、放错模块、真实缺失。

| 根因类别 | 差异 | 处理方向 |
|---|---|---|
| A 脚本映射错误 | animationlib 8 missing | 排除出检查范围（test-only，无生产引用） |
| B 违规源码复制（规则 S/F） | animationlib 4 src+7 res；core Compile.java | 删源码改 AAR/jar |
| C 真实缺失（规则 C） | pods retail 4 kt | 补齐复制 |
| D 放错模块 | common 2 Conflated | 迁到 `:SystemUI-shared-utils` |

---

## 逐条根因

### 1. animationlib：脚本把一个模块当成两个

AOSP 有**三个**不同的 animation 库：

| AOSP 源码树 | soong 模块 | 包名 | 归属 | 谁引用 |
|---|---|---|---|---|
| `packages/SystemUI/animation/` | `PlatformAnimationLib` | `com.android.systemui.animation` | SystemUI 自有 | SystemUI-core (bp:449)、compose/core (bp:34) |
| `packages/SystemUI/animation/lib/` | `PlatformAnimationLib-core` / `-server` | `com.android.systemui.animation[.server/.shared]` | SystemUI 自有 | **仅 tests**，无生产引用 |
| `frameworks/libs/systemui/animationlib/` | `animationlib` | `com.android.app.animation` | frameworks/libs（非 SystemUI） | PlatformAnimationLib 间接 static_libs |

项目 `:SystemUI-animationlib` 实际复制的是**第三个**（`frameworks/libs/systemui/animationlib`，包 `com.android.app.animation`），
但脚本按 AOSP `packages/SystemUI/animation/lib/` 对齐 → 同时报 8 missing（第二个的文件）和 4+7 extra（第三个的文件）。

- **8 missing**（`OriginRemoteTransition.java` 等）：属于 `PlatformAnimationLib-core/server`，AOSP 全树只有
  `animation/lib/tests/` 引用，**无任何生产代码引用** → 项目根本不需要复制。
- **4 extra src + 7 extra res**（`Interpolators.java`/`Animations.kt`/`MathUtils.java`/`InterpolatorsAndroidX.java`
  + 6 个 interpolator XML + `ids.xml`）：属于 `frameworks/libs/systemui/animationlib`，**非 SystemUI 自有**，
  当前源码复制违反规则 S/F。项目依赖方：`:SystemUI-compose-core` (build.gradle.kts:71)。

### 2. pods retail：真实缺失，需补齐

AOSP `pods/com/android/systemui/retail/{data,domain}/` 是 SystemUI 自有代码，SystemUI-core 通过
`pods/.../retail:impl` (bp:445/725) 引用。项目 core 实际 import 了 `RetailModeInteractor`
(QSFooterViewController.java:35) 和 `RetailModeRepository` (TileSpecRepository.kt:28)。

项目已建 `:SystemUI-pods-retail-data-impl` / `:SystemUI-pods-retail-domain-impl` 模块，但 **src 为空**，
4 个 kt 未复制：
- `data/repository/RetailModeRepository.kt`（soong `retail/data:api`，srcs: `repository/*.kt`）
- `data/repository/impl/RetailModeSettingsRepository.kt`（soong `retail/data:impl`）
- `domain/interactor/RetailModeInteractor.kt`（soong `retail/domain:api`）
- `domain/interactor/impl/RetailModeInteractorImpl.kt`（soong `retail/domain:impl`）

→ **真实缺失，按规则 C 补齐复制**。

### 3. common 的 2 个 Conflated：放错模块

`FlowConflated.kt` / `LatestConflated.kt` 在 AOSP 位于 `packages/SystemUI/utils/src/com/android/systemui/utils/coroutines/flow/`，
属于 soong **`SystemUI-shared-utils`**（`utils/Android.bp`，`srcs: ["src/**/*.java","src/**/*.kt"]`），
**不在 `common/src/`**（`SystemUICommon` 的 srcs 是 `common/src/**`）。

项目把它们放进 `:SystemUI-common/src/main/java/.../utils/coroutines/flow/` → 脚本报 extra（AOSP common 确实没有）。
项目有 `:SystemUI-utils-kairos`（对应 kairos），但**没有对应 `SystemUI-shared-utils` 的模块**。

→ **迁到 `:SystemUI-shared-utils`**（需新建模块，对齐 AOSP `utils/`），或确认现有结构如何提供这些类。

### 4. core 的 Compile.java：违规源码复制

`Compile.java` 在 AOSP 位于 `frameworks/libs/systemui/compilelib/src-{debug,release}/`，soong 模块 `compilelib`
（debuggable 变体切换 src-debug/src-release）。SystemUI-core 引用 compilelib (bp:442/722/783)。

`frameworks/libs/systemui/` 非 SystemUI 自有 → 当前源码复制到 `:SystemUI-core` 违反规则 F。

→ **删源码改 jar 引入**（compilelib 无资源，tier② jar）。注意 debug/release 变体。

### 5. shared 的 UncaughtExceptionPreHandlerManager.kt：已用 jar 替代（合规）

build.gradle.kts 注释说明：该 .kt 依赖 libcore 隐藏 API `Thread.setUncaughtExceptionPreHandler`，
Kotlin/JDK21 工具链无法从源码编译，已用 `libs/shared-uncaught-handler.jar` 替代。

→ 当前合规（tier② jar）。脚本报 missing 是因为它只对源码集检查；可在脚本中标注 expected-jar-substituted。

---

## 修正方案分类（待用户决策优先级）

- **A 脚本修正**（无代码改动）：在 `check_source_alignment.py` 标记 `PlatformAnimationLib-core/server`
  为 test-only（expected-absent），标注 `UncaughtExceptionPreHandlerManager` 为 jar-substituted。
- **B 违规源码删除 + jar/AAR**（规则 F 执行，需新产物）：
  - animationlib：删 `:SystemUI-animationlib` 源码，改 AAR 引入 `frameworks/libs/systemui/animationlib`
  - compilelib：删 `Compile.java`，改 jar 引入 `compilelib`
- **C 真实缺失补齐**（规则 C，纯源码复制）：复制 4 个 pods retail kt 到对应模块 src。
- **D 放错模块迁移**（需新建 `:SystemUI-shared-utils` 模块）：把 2 个 Conflated 从 common 迁到新模块。

## 验证记录

本阶段仅诊断，未修改源码、资源或运行编译。下一步修正方案涉及新产物（AAR/jar）和模块新建，属结构决策。
