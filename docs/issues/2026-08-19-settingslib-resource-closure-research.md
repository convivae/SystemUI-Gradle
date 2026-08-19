# SettingsLib 资源闭包调研

## 背景

Task 013 已证明：把 `SettingsLibSettingsTheme` 作为独立 res-only AAR 可以消除
`settingslib_switch_track/thumb` 缺失，但随后暴露了 `ProgressBar`、
`ActionButtonsPreference`、`TwoTargetPreference` 的资源缺口。进一步审计发现
`SettingsLib` 的直接 `static_libs` 中有 29 个带 `resource_dirs` 的 target。

用户提出关键问题：这些资源能否都放进 `SettingsLib.aar`，而不是生成大量独立 AAR？
在决定 Task 014 实施架构前，必须先调研参考项目 `CarSystemUIGradle` 的真实做法，
以及 AOSP/Soong 是否已经产出可复用的完整合并资源。

## 调研问题

1. `CarSystemUIGradle` 如何打包和接入 SettingsLib 资源？
   - 是单一合并 AAR、多个子 target AAR，还是直接复制资源目录？
   - 具体由哪些脚本、Gradle 文件或本地 Maven 产物实现？
2. 参考项目如何处理多个 AOSP `resource_dirs` 中的同相对路径资源？
3. AOSP Soong intermediates 是否已有完整 SettingsLib merged resource、AAR 或 package 产物可直接复用？
4. 当前项目可选架构的工程权衡是什么？
   - 方案 A：单一 `SettingsLib.aar` 内合并完整资源闭包
   - 方案 B：每个真实 Soong target 一个 res-only AAR，并用 POM 传递依赖
   - 方案 C：每个 res-only AAR 在 consumer 中显式声明
5. 哪个方案最符合规则 R/B、参考项目先例、可复现性和后续维护？

## 约束

- 只读调研；不修改任何代码、资源、AAR、Maven 产物、构建脚本或版本目录。
- 所有关键结论必须引用一手来源路径和必要的行号/命令输出。
- 不根据推断假设参考项目行为；必须读取实际文件或产物。
- 推荐方案必须说明如何处理重复资源路径，不得建议覆盖、伪造或手工改写 AOSP 资源。

## 输出

- 详细调研：`docs/architecture/2026-08-19-settingslib-resource-closure-research.md`
- 本文件追加真实执行记录和结论摘要。
