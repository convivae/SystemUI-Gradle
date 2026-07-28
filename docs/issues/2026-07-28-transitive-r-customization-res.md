# Stage 4 (部分): customization res 补齐 + 开启 transitive R (2026-07-28)

> 承接 `2026-07-28-r-import-ambiguity.md`（1979→1879）与 datastore 依赖补齐（1879→1806）。
> 本次处理 clock/customization 资源引用 unresolved，错误数 **1806 → 1759 (−47)**。

## TL;DR

`com.android.systemui.R.dimen.large_clock_text_size` / `R.id.lockscreen_clock_view` 等
时钟/customization 资源引用 unresolved。根因是 **(1) `:SystemUI-customization` 模块没有 res 目录**，
且 **(2) `android.nonTransitiveRClass=true` 使依赖模块资源不合并进 `com.android.systemui.R`**。
从 AOSP 复制 customization res + 关闭 nonTransitiveRClass（对齐 AOSP 的传递合并），错误数 −47。

## 根因

1. **AOSP 靠传递资源合并**: AOSP Soong 把所有 static-lib（customization / shared / settingslib 等）
   的资源合并进 app 包，因此源码里统一写 `com.android.systemui.R.xxx`。
2. **Gradle 默认 `nonTransitiveRClass=true`**: 每个模块的 R 只含自身资源，依赖资源要用
   依赖自己的 R（`com.android.systemui.customization.R`）——与 AOSP 源码写法不符。
3. **customization 模块缺 res**: `:SystemUI-customization` 只有 src，没 res，
   连自己的 R 里都没有 `lockscreen_clock_view` 等 id/dimen。

## 方法

1. **定位资源出处**: AOSP `SystemUI/customization/res/values/{ids,dimens,...}.xml`。
2. **复制 res**（AGENTS §1 允许"复制 AOSP 的 res 目录"）:
   `cp -r aosp/.../customization/res SystemUI-customization/res` + `res.srcDir("res")`。
   → 单独此步无效（1806 不变），因为 nonTransitive 下资源进的是 customization.R。
3. **关闭 nonTransitiveRClass**: `gradle.properties` `android.nonTransitiveRClass=false`。
   → customization + 各 aar（settingslib 等）资源传递进 `com.android.systemui.R`，1806 → **1759**。
4. **无回归验证**: LC_ALL=C 对比 unresolved 符号集，**无新增符号类型**；被解决的符号见下。

## 被解决的资源（示例）

`lockscreen_clock_view` `lockscreen_clock_view_large` `large_clock_text_size`
`small_clock_text_size` `presentation_clock_text_size` `weather_clock_time`
`clock_padding_start` `keyguard_smartspace_top_offset` `status_view_margin_horizontal`
`lock_icon_margin_bottom` `right_icon` `small_clock_height` 等。

## 未解决（follow-up）

- **smartspace ids**（`bc_smartspace_view` `date_smartspace_view` `weather_smartspace_view`，~32）:
  定义在 AOSP `SystemUI/shared/res/values/ids.xml`。但 `:SystemUI-core` 通过 **prebuilt
  `SystemUISharedLib.jar`(aar)** 依赖 shared，而非 `:SystemUI-shared` project，
  所以给 `:SystemUI-shared` 加 res **无效**（已验证并回退）。
  正解：要么让 core 依赖 `:SystemUI-shared` project 的 res，要么在 shared aar 里带上这些 res。
  留作后续。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| datastore 后 | 1806 |
| 仅复制 customization res (nonTransitive=true) | 1806（无效）|
| 关闭 nonTransitiveRClass | **1759** |
