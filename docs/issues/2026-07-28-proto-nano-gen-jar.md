# Stage 4 (部分): 补齐 nano proto 生成类 jar (2026-07-28)

> 承接 SettingsLib jar（1491→1039）。本次错误数 **1039 → 938 (−101)**。

## TL;DR

`com.android.systemui.communal.nano.CommunalHubState` / `dump.nano.SystemUIProtoDump` /
`qs.nano.QsTileState` 等 nano proto **生成类** unresolved（字段 `str1`/`nano`/`int1` 级联）。
我方 `libs/SystemUI-proto.jar` **只含 protobuf.nano 运行时（MessageNano），缺 .proto 生成类**。
补上 AOSP 生成的 `SystemUI-proto-gen.jar`（15 个 nano 类）。−101。

## 根因

AOSP 用 protoc + javanano 从 `.proto` 生成 nano 类，编译进 `SystemUI-proto`。
我方早期打包的 `SystemUI-proto.jar` 只抓了 protobuf.nano 运行时（`com.google.protobuf.nano.*`），
漏了生成的业务 proto 类。

## 解决方案（AGENTS §1）

```bash
cp aosp/.../SystemUI-proto/android_common/javac/SystemUI-proto.jar libs/SystemUI-proto-gen.jar
```
`SystemUI-core/build.gradle.kts` 保留原 runtime jar，再加生成类 jar：
```kotlin
implementation(files("${rootProject.projectDir}/libs/SystemUI-proto.jar"))      // runtime
implementation(files("${rootProject.projectDir}/libs/SystemUI-proto-gen.jar"))  // generated
```

补入的 15 个类：CommunalHubState(+CommunalWidgetItem), SystemUIProtoDump, QsTileState,
Notifications(+Notification/NotificationList), TouchAnalyticsProto(+嵌套), ComponentNameProto。

## 无回归

LC_ALL=C 对比：**无新增 unresolved 符号类型**。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| SettingsLib jar 后 | 1039 |
| 补 SystemUI-proto-gen.jar | **938** |
