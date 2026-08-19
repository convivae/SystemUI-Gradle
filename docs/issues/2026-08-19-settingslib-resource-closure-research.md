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

---

## 执行记录（2026-08-19，Task 014 worker）

### 执行方式

- 只读调研；未修改任何代码、资源、AAR、Maven 产物、构建脚本或版本目录；未运行 Gradle 构建。
- 量化审计使用 /tmp 一次性 Python 脚本（brace-aware Android.bp 解析 + ElementTree values 解析），未在仓库创建脚本。
- 全部结论来自一手来源实物读取/解包（CarSystemUIGradle 脚本与产物、AOSP Android.bp/intermediates、本项目 artifacts），无记忆推断。

### 结论摘要

1. **参考项目机制**：单一合并 AAR `com.android.systemui:SettingsLib:1.0.0`（本地 Maven，POM 为无依赖骨架）。
   `tools/gen_aar_maven.py` 把整个 `frameworks/base/packages/SettingsLib` 源码树下所有 res 目录物理拼接进一个 AAR `res/` 根；
   classes 来自 Soong combined/javac jar。实测参考 AAR 含 309 个 res 文件，确实包含子模块资源
   （preference_two_target_divider.xml、progress_* interpolator、settingslib_action_buttons.xml）。
   但参考配置**刻意删除全部 v31 资源目录**（res_to_remove），故其 AAR 无 settingslib_switch_track/thumb——不可照抄。
2. **重复路径处理**：参考项目不回避而是改写——非 values 同路径 first-wins 静默跳过、values XML 内容拼接、
   跨文件同名资源正则去重（首个定义胜出）。这违反本项目规则 R；且参考项目曾因单一 namespace 出现
   `NoClassDefFoundError: Lcom/android/wifitrackerlib/R$string;`，其修复方式恰是**另出独立 WifiTrackerLib AAR**。
3. **Soong 无完整合并产物（not found）**：主 target `package-res.apk` 只含自有 res（174 条目，子模块资源 0 命中）；
   R.txt 按包独立；SettingsLib intermediates 树中无任何 .aar；完整合并只发生在 app link。最接近可用中间产物＝
   每 target 的 res 源目录 + AndroidManifest（R namespace）+ R.txt，即本项目打包器已消费的三件套。
4. **量化闭包审计**：SettingsLib* 传递闭包 39 个 target 中 **33 个拥有资源**（主 + 30 直接 + SettingsTheme/Color 传递；
   Color 依赖 Soong 默认 resource_dirs=["res"]，无显式声明）；共 **1512** 个 res 文件、599 个唯一相对路径、
   **101 组同相对路径冲突**（85 组为 9 个 target 共享的 locale values 文件）；跨 target 同名资源仅 **5 个**
   （EntityHeader* 5 个 style，LayoutPreference values/ vs SettingsTheme values-v35/，单一 namespace 下为合法 config 变体）。
   结论：路径冲突只在物理拼接单一 res/ 根时致命；AAPT2 link 符号级合并天然消化（Task 013 已实证）。
5. **R namespace 运行期发现**：Soong 库级 R 类字段为非 final（javap 实测），子模块字节码以 getstatic 引用子包 R
   （TwoTargetPreference.class → preference.twotarget.R$id.two_target_divider）。当前合并 classes.jar 无任何 R 类，
   也无 AAR 提供子包 namespace → 存在运行期 NoSuchFieldError 隐患（参考项目 wifitrackerlib 同型故障实证）。
   per-target res-only AAR（原始 manifest 包名）会让 AGP 生成子包 R 类，恰好修复；单一合并 AAR 修复不了。
6. **推荐方案 C**：per-target res-only AAR + consumer 显式声明（新增约 30 个 AAR，流水线与 Task 013 同构）。
   方案 A 违反规则 R（101 组路径冲突必须静默改写）；方案 B 需把本地 Maven POM 从骨架升级为传递依赖，
   语义变更风险与 Task 013 迁移成本不成比例，可作后续演进。实施属红线区域，需用户批准后另立任务。

### 相邻发现（记录待查，不扩大本任务范围）

- `setupdesign`（external/setupdesign）是 SettingsLib 直接 static_lib 且含资源，当前未打包；
  SettingsLib src/res 未见其资源引用（grep 为空），暂不阻塞。
- 闭包与 SystemUI-res/framework-res/iconloader/WifiTrackerLib 的全局资源名冲突只能由 AAPT2 link 实测暴露。

详细证据（文件路径 + 行号 + 命令输出）：`docs/architecture/2026-08-19-settingslib-resource-closure-research.md`
