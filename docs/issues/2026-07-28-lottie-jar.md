# Stage 4 (部分): 补齐 lottie / lottie_compose jar (2026-07-28)

> 承接 unfold jar（885→844）。本次错误数 **844 → 809 (−35)**。

## TL;DR

`com.airbnb.lottie.*` / `com.airbnb.lottie.compose.*`（rememberLottieComposition、
LottieAnimation、LottieDynamicProperties 等）unresolved。补 AOSP `external/lottie`
编译产物 `lottie.jar`（277 类）+ `lottie_compose.jar`（50 类）。−35。

## 解决方案（AGENTS §1）

```bash
cp aosp/.../external/lottie/lottie_compose/android_common/kotlin/lottie_compose.jar libs/lottie_compose.jar
cp aosp/.../external/lottie/lottie/android_common/javac/lottie.jar libs/lottie.jar
```
`SystemUI-core/build.gradle.kts`（compileOnly，只为解析符号，避免 lottie 资源冲突）：
```kotlin
compileOnly(files("${rootProject.projectDir}/libs/lottie.jar"))
compileOnly(files("${rootProject.projectDir}/libs/lottie_compose.jar"))
```
AOSP Android.bp 依赖名即 `lottie` + `lottie_compose`。

## 残留（非 lottie，另属 SettingsLib widget）

`LottieColorUtils` 实为 `com.android.settingslib.widget.LottieColorUtils`（PromptIconViewBinder，2 处），
属 SettingsLib widget 子库缺口，与 lottie 本身无关，留待 SettingsLib widget 补齐。

## 无回归

LC_ALL=C 对比：**无新增 unresolved 符号类型**。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| unfold jar 后 | 844 |
| + lottie/lottie_compose | **809** |
