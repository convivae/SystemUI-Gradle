# Stage 4 (部分): customization jar 用 api 暴露给 core (2026-07-28)

> 承接 AIDL jar（1759→1658）。本次错误数 **1658 → 1491 (−167)**。

## TL;DR

`com.android.systemui.shared.keyguard.shared.model.KeyguardQuickAffordanceSlots` /
`com.android.systemui.shared.clocks.ClockRegistry` 等大量 `com.android.systemui.shared.*`
引用 unresolved。这些类**明明在** `libs/prebuilts/SystemUICustomizationLib.jar` 里
（路径完全匹配 import），但 `:SystemUI-customization` 用 `implementation(files(...))` 引入该 jar，
**`implementation` 不向下游暴露**，所以 `:SystemUI-core` 看不到。改成 `api(files(...))` 即可。−167。

## 根因

Gradle 依赖可见性：
- `implementation` 依赖只在本模块可见，**不**传递给依赖本模块的下游。
- `api` 依赖会传递暴露给下游。

`:SystemUI-customization` 把 prebuilt jar 声明为 `implementation`，
`:SystemUI-core` 虽 `implementation(project(":SystemUI-customization"))`，
但拿不到 customization 内部 `implementation` 进来的那 829 个 class。

## 排查关键

一开始怀疑是 Stage 2 那种"源码 stub 遮蔽 jar"，但：
1. `find SystemUI-core/src -path "*KeyguardQuickAffordanceSlots*"` → 无遮蔽源码。
2. `unzip -l .../SystemUICustomizationLib.jar | grep KeyguardQuickAffordanceSlots`
   → 类在，路径 `com/android/systemui/shared/keyguard/shared/model/…` 与 import 完全一致。
3. → 排除遮蔽与缺类，只剩"可见性"：果然是 `implementation` vs `api`。

## 解决方案

`SystemUI-customization/build.gradle.kts`：
```kotlin
// implementation(files(".../SystemUICustomizationLib.jar"))
api(files("${rootProject.projectDir}/libs/prebuilts/SystemUICustomizationLib.jar"))
```

## 无回归

LC_ALL=C 对比：**无新增 unresolved 符号类型**。剩余非-unresolved 错误（type inference /
override nothing 等）是原本被 unresolved 掩盖、现在暴露出的下一层业务错误，非本次引入。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| AIDL jar 后 | 1658 |
| customization jar 改 api | **1491** |
