# Stage 4 (部分): 补齐新版 SystemUILogLib jar (2026-07-28)

> 承接 proto gen jar（1039→938）。本次错误数 **938 → 885 (−53)**。

## TL;DR

`LogMessage.str1/str2/int1/bool1` 属性 + `MessageInitializer`/`MessagePrinter` typealias unresolved。
`com.android.systemui.log.core.LogMessage` 存在于 customization/shared/plugin 三个 prebuilt jar，
但**都是旧版**（无 str1、无 typealias）。补上 AOSP 新版 `SystemUILogLib.jar` 并放在依赖最前，
使新版 LogMessage 在 classpath 上优先。−53。

## 根因

- `str1`/`str2`/`int1`/`bool1` 是 `LogMessage` 接口的属性（LogBuffer 日志格式）。
- `MessageInitializer = LogMessage.() -> Unit` / `MessagePrinter = LogMessage.() -> String`
  是 `LogMessage.kt` 里的 top-level typealias。
- 我方三个 prebuilt jar（customization/shared/plugin）打包于较早 AOSP 快照，
  其 `log/core/LogMessage.class` 缺 str1（javap 验证 `str1` 计数=0），也缺 typealias。

## 解决方案（AGENTS §1）

```bash
cp aosp/.../SystemUILogLib/android_common/kotlin/SystemUILogLib.jar libs/SystemUI-log.jar
```
`SystemUI-core/build.gradle.kts` **依赖块最前**（优先于 prebuilt 旧版）：
```kotlin
api(files("${rootProject.projectDir}/libs/SystemUI-log.jar"))
```

16 个类：LogMessage/LogMessageKt(typealias facade)/Logger/LogBuffer/LogMessageImpl/
LogLevel/MessageBuffer/LogcatEchoTracker 等。

## classpath 优先级要点

多个 jar 含同名 `LogMessage.class`（旧版无 str1）。Kotlin 编译按 classpath 顺序取第一个，
故新 jar 必须排在 customization(api)/shared/plugin 之前 → 放 dependencies 块首行。

## 无回归

LC_ALL=C 对比：**无新增 unresolved 符号类型**。暴露出的 type-inference/argument-mismatch
是原被 unresolved 掩盖的下层业务错误。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| proto gen jar 后 | 938 |
| 补 SystemUI-log.jar | **885** |
