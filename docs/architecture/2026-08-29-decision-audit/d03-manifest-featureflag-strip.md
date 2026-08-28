# D3 — application manifest 剥 `REPORT_UI_LATENCY_STATS` 权限的 `android:featureFlag` 属性

status: done
判读: **可接受但需补记录**（技术上有一处更贴近先例的备选没被采用；授权链停在 chief 泛授权，见 p01）

## 背景与决策原文

AOSP-17 manifest（`SystemUI-application/src/main/AndroidManifest.xml`，源自
`/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/AndroidManifest.xml:426-427`）里
`REPORT_UI_LATENCY_STATS` 的 `uses-permission` 携带
`android:featureFlag="com.android.server.ui_latency_stats.ui_latency_stats_service"`——17 manifest 中
**唯一**出现 featureFlag 的元素（issue §4 批次 2 记录）。

aapt2 的 manifest featureFlag 过滤：选项 `fail_on_unrecognized_flags` 默认 true
（`aapt2 link/FeatureFlagsFilter.h:36`，任务007 调研已实证；
`docs/issues/2026-08-13-aapt-feature-flags-research.md` §"Established the mechanism"）。
AGP 9.3.1 的 link 命令不携带任何 `--feature-flags`（`AaptV2CommandBuilder`，字节码级实证，
issue §4 批次 2）→ link 时该元素必报错。

task073 R6–R8 轮的决策（commit `6e66a0ea`）：在 manifest 上以 CONV_DEL 注释剥除该属性、保留
permission 元素本身；被打标行字节保全。理由记录为：Soong 侧 flag 是 aconfig 默认 READ_WRITE
（`flags.aconfig` 未声明 mode，即默认 READ_WRITE；
`/home/conv/myspace/aosp/frameworks/base/services/core/java/com/android/server/uilatencystats/flags.aconfig:5-8`）；
剥属性后 permission 无条件请求；因属 signature 权限，记录为"无功能面影响"（此断言未经设备验证，
见开放问题）。

## 决策链

| 环节 | 证据 |
|---|---|
| 错误实证 | task073 R6：`merged manifest uses-permission 的 android:featureFlag` 在 link 阶段被 aapt2 fail_on_unrecognized_flags 拒绝（issue §4 错误数表） |
| 授权来源 | task073 brief File Map "必要时 SystemUI-*/src 的 CONV 标记改动"（类别级泛授权，见 p01）；issue §6 对账表"File Map 授权区（SystemUI-*/src）；机制同 Task 072 package 属性先例" |
| 执行 | commit `6e66a0ea`（含 manifest 14 行改动 + 一次 R7 的 `--` 改写失误已自纠；issue §4 错误数表 R7 行如实标注） |

## 证据链

1. **manifest 现状**：`SystemUI-application/src/main/AndroidManifest.xml:431-443` CONV_DEL 块存在；
   其它元素（`uses-permission` 元素体）保留。
2. **AOSP 来源**：上面 `AndroidManifest.xml:426-427`（AOSP-17 原版两行 uses-permission
   带 featureFlag 属性）。
3. **flag 声明**：`flags.aconfig:5-8` 未声明 mode → aconfig 默认 READ_WRITE；
   `AconfigFlags.bp:217-221` 定义 `uilatencystats_flags_core_java_lib`（17 SystemUI-core bp
   static_libs L572，接线成为 task072 产出的 flags jar）。
4. **Soong 的对照行为**：`build/soong/java/aapt2.go:107-108, 305-307` —— Soong 在 **compile 和
   link 两侧**都转发了 `--feature-flags @<path>`；17 SystemUI-res bp `flags_packages` 列表
   （L429-434）含 `uilatencystats_flags`。
5. **先例**：2026-08-13 task007/task009 在 **app 侧**用
   `androidResources.additionalParameters("--feature-flags", "…=true")` 解决同类问题
   （wm.shell `enable_retrievable_bubbles`），**用户预批准**于 2026-08-13
   （commit `8ab860e9` + research doc §"2026-08-13 update"）。该代码段至今保留在
   `app/build.gradle.kts:82-89`。

## 备选路径（按侵入度排序）

1. **`additionalParameters` 加一行**（16 时代 task009 方案延伸）：
   `--feature-flags com.android.server.ui_latency_stats.ui_latency_stats_service=true` —— 零 manifest
   改动、有用户预批准先例、语义与 Soong 一致（READ_WRITE flag，Soong keeps element）。
   **未被选**。注：该参数只会传给最终 link（`processDebugResources` 的 link 命令），
   沿用的正是 16 时代已解决的问题类别。
2. **CONV_DEL 剥属性**（所选）：零 build 文件改动、机制与 D1/E3 一致、可逆；代价是 manifest 与
   AOSP/Soong 行为偏差（Soong 留着元素供 PackageManager 过滤，本 build 则全是无条件请求）。
3. **按 product 分流 manifest / flavor**：成本过高。

## 优劣分析

优点（所选）：机制同构（CONV 打标、对账、可撤回）；不引入新的 build 配置面；与 D1/E3
同一模式。语义上，Soong 保留元素供 PackageManager 按 flag 状态运行时过滤，本 build 改为
无条件静态请求——在 signature 权限前提下列为可接受偏差；但这是一项**语义判定**而非
“无法绕开”，因为备选路径 1（additionalParameters）同样能越过 link 检查。
缺点：
- 授权链停在 chief 的类别级泛授权（p01 的直接后果）；
- 有更接近先例的备选（路径 1）没被采用，也没在 issue 里明示放弃理由；
- R7 出现一次 `--` 非法注释改写失误——泛授权 + 仓促落地已有一次实现实例；
- "signature 权限无功能面影响"的判定未经运行时验证（release/真机面未知）。

## 判读与建议

判读：**可接受但需补记录**——结论方向与规则 R 的对账/可撤回要求相符；但（a）要在 issue §6
对账表里补上"为何弃用 additionalParameters 路径"的理由，（b）把 D3 提交用户追认（连同 p01）。

注：上条（a）应以本审计的备选路径 1-3 为准写进 issue 对账表。

建议：
1. 在用户确认前保持现状（改动本身建证充分、可逆）；
2. 若用户重选，撤回 CONV_DEL 三行、改在 `app/build.gradle.kts:82-89` 的
   `additionalParameters` 追加该 flag —— 这更接近 Soong 语义与 16 时代先例。

## 开放问题

- D2/D3 的"保留/剥除"自定义语事实链需用户裁决一次（p01 的授权结构裁决点）；
- REPORT_UI_LATENCY_STATS 在实际设备/镜像上是否是 signature 权限（若 platform.xml 未列，
  无条件请求被拒拉倒，另需 fallback）——17 框架 runtime 面待 C5 验证。
