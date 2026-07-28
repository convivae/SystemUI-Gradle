# Stage 4 (部分): 补齐完整 SettingsLib jar (2026-07-28)

> 承接 customization api（1658→1491）。本次错误数 **1491 → 1039 (−452)**（分两步）。

## TL;DR

`com.android.settingslib.volume.data.repository.AudioRepository` /
`com.android.settingslib.bluetooth.LocalBluetoothLeBroadcast` 等大量
`com.android.settingslib.*` 引用 unresolved。我方 `libs/maven/.../SettingsLib-1.0.0.aar`
**只含 res，不含 kotlin/java class**。从 AOSP 补两个 jar：
- `SettingsLib-full.jar`（kotlin 编译产物，含 AudioRepository 等 kotlin 类）→ 1491→1150 (−341)
- `SettingsLib-javac.jar`（javac 编译产物，含 LocalBluetoothLeBroadcast 等 java 类）→ 1150→**1039** (−111)

## 根因

AOSP SettingsLib 是 kotlin+java 混合模块，编译产物分两个 jar：
- `android_common/kotlin/SettingsLib.jar`（372 class，kotlin 类如 volume.*.AudioRepository）
- `android_common/javac/SettingsLib.jar`（601 class，java 类如 bluetooth.LocalBluetoothLeBroadcast）

单独任一 jar 都不全（kotlin jar 无 BT，javac jar 无 AudioRepo），两个都要。
我方 aar 是早期用 gen_aar_maven.py 生成的，只打包了 res，漏了 class。

## 解决方案（AGENTS §1：从 AOSP 编译产物提取 jar）

```bash
cp aosp/.../SettingsLib/android_common/kotlin/SettingsLib.jar libs/SettingsLib-full.jar
cp aosp/.../SettingsLib/android_common/javac/SettingsLib.jar  libs/SettingsLib-javac.jar
```
`SystemUI-core/build.gradle.kts`：
```kotlin
compileOnly(files("${rootProject.projectDir}/libs/SettingsLib-full.jar"))
compileOnly(files("${rootProject.projectDir}/libs/SettingsLib-javac.jar"))
```

保留原 `implementation(libs.systemui.settingslib)`（提供 res / R）。

## 无回归

两步都 LC_ALL=C 对比 unresolved 符号集：**无新增符号类型**。

## 备选（未采用）

`android_common/turbine-combined/SettingsLib.jar`（11431 class，含全部 kotlin+java+传递依赖头）
一个 jar 就够，但太大且含大量 androidx/kotlin-stdlib 头，故选两个精确的编译产物 jar。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| customization api 后 | 1491 |
| + SettingsLib-full.jar (kotlin) | 1150 |
| + SettingsLib-javac.jar (java) | **1039** |
