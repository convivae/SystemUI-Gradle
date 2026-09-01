# C5 AOSP-17 platform aconfig jarjar closure

**日期**：2026-09-01  
**状态**：诊断/方案裁决待执行；禁止直接实施 rewrite  
**任务**：task078

## 背景

Phase C 的 C1–C4 已完成。task075 在 AOSP 17 emu64x 上证明 Debug 可以运行，并将 Release 首个崩溃定位为 protobuf-lite 反射字段；task076 已以最小 `GeneratedMessageLite { <fields>; }` keep 修复该问题。task077 已完成 durable 部署基础设施：2880MiB dynamic-partition group、正式 `m -j16`、582MiB super-backed scratch、五分区 overlay 以及 64MiB 探针跨两次整机重启验证。

修复后的 Release APK 随后暴露独立 blocker：AOSP 17 对一组 framework aconfig 类使用自动传播 JarJar 规则，stock SystemUI DEX 引用 `com.android.internal.hidden_from_bootclasspath.*`，而 Gradle Release 仍引用原包名，因此设备上触发 `NoClassDefFoundError`。这不是 missing-rules 问题，也不能通过打包平台类、stub 或 `dontwarn` 修复。

## 已冻结事实

- 当前 APK：`app/build/outputs/apk/release/app-release.apk`。
- stock APK：`/home/conv/myspace/aosp/out/target/product/emu64x/system_ext/priv-app/SystemUI/SystemUI.apk`。
- 规则：`/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`。
- 规则文件 726 物理行 = **725 条规则** + 1 行末尾空行，SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`；`SystemUI-core`、`SystemUI-application` 与 compatibility library 的中间产物使用同一内容。
- AOSP host tool：`/home/conv/myspace/aosp/out/host/linux-x86/framework/jarjar.jar`，支持 `process <rulesFile> <inJar> <outJar>`。
- 四个已触发/确认的关键类：
  - `android.app.Flags`
  - `android.os.Flags`
  - `android.view.accessibility.Flags`
  - `com.android.window.flags.Flags`
- 初步 DEX type-table 扫描：当前 Gradle Release 对上述四项全部为 source-present/target-absent；stock 全部为 source-absent/target-present。
- 全 725 条 exact-rule 初筛：Gradle Release 为 30 source / 0 target；stock 为 1 source / 36 target。stock 的唯一 source 是已定义类 `android.app.admin.flags.FeatureFlagsImpl`，因此不能把“725 条 source 全部为 0”误写成通用 gate。

## 本步计划

1. 固化秒级静态 gate，精确区分 DEX type reference 与 class definition；当前 Release 必须稳定红，stock APK 必须绿。
2. 从 `frameworks/base/Android.bp` 与 Soong Java/JarJar 实现追出 725 条规则的生成、传播与执行时序。
3. 比较三条方案：R8 前程序输入引用改写、R8 后 DEX 改写、复用/再处理 Soong JarJar 产物。
4. 给出唯一推荐与下一张实现 brief，先交用户裁决；本任务不改 Gradle、不改源码/资源、不跑构建或设备。

## 验收口径

- 新工具单测全绿。
- 当前 Release：四个 source present、四个 target absent、exit 1。
- stock SystemUI：四个 source absent、四个 target present、exit 0。
- 架构报告必须覆盖 stage ordering、program/classpath 边界、平台类是否会被打包、Debug/Release 一致性、AOSP 可再生性和项目规则合规性。
- 未运行 Gradle/Soong/ADB 必须如实写明。

## 结果

**task078 已完成（研究+gate；rewrite 未实施，待用户裁决）。** 架构报告：`docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md`。

### P1 gate（已落地）

- 工具 `tools/check_aconfig_jarjar_references.py`（纯 stdlib DEX type-table/class-defs 读取器，exact 规则校验，critical 四类硬编码）+ 26 个单测全绿（二轮复审后；初审 19 + 一轮 4 + 二轮 3）：
  `uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q` → `26 passed`。
- gate 判定（二轮硬化）：(i) 四 critical source 必须完全不被引用；(ii) 四 critical target 必须被引用；(iii) **全规则集合任一 target 被 define 即 FAIL**（改名后的平台类不得进 APK；stock 全规则 36 target referenced / 0 defined，故预期结果不变）。
- Gradle Release：exit 1、`RESULT=FAIL`（4 source present / 4 target absent；全规则 30 source / 0 target；defined 原名仅 3：`android.os.Flags`、`android.os.FeatureFlagsImpl`、`com.android.window.flags.Flags`）。
- stock APK：exit 0、`RESULT=PASS`（4 source absent / 4 target present；全规则 1 source / 36 target）。
- 直接死因确认：`android.app.Flags` 被引用但 program input 无定义（`libs/systemui-aconfig-flags.jar` 只含 `android/os/Flags.class`、`com/android/window/flags/Flags.class` 等），设备 bootclasspath 又只有 hidden 名 → `NoClassDefFoundError`。
- 事实更正：规则文件 726 行 = **725 条规则** + 末尾空行（此前记录的 "726 rules" 不准确）。

### P2 Soong 重建（要点，全部一手源码）

- 规则生成：`java_aconfig_library` 以空 target 声明 5 类改名（`build/soong/aconfig/codegen/java_aconfig_library.go:127-135`）。
- 填充：`framework-minus-apex` 的 `jarjar_prefix: "com.android.internal.hidden_from_bootclasspath"`（`frameworks/base/Android.bp:580-581`）。
- 传播：blueprint provider + 非空胜过空（`build/soong/java/base.go:1272-1283`）；SystemUI-core/application/compat 三处 repackaging.txt 同 SHA `f79a08d4…`。
- 执行点：**各模块自己的 javac/kotlinc/turbine 产物上、编译后静态库合并前**（`base.go:1633,1718,1726,1795,1827,1833,3436-3441`）；命令 `builder.go:356-368`。SystemUI android_app 自身无重写（无自有源码）。
- 1/36 解释：settingslib 引用已被改写为 hidden `Flags`；`FeatureFlagsImpl` 是 SettingsLib 静态链接 `device_policy_aconfig_flags_lib`（`SettingsLib/Android.bp:82`）带入的原名定义，R8 后仅存该类。R8 存活链精确原因标注 unknown（R8 输入中无引用者、无 keep 规则，见报告 §2.5）。
- 可再生性：规则文件与 `jarjar.jar`（源码 `external/jarjar`，Apache-2.0）均可从干净 AOSP 树重建（`m framework-minus-apex` / `m jarjar.jar`）。

### P3 推荐（待用户裁决；复审修正后）

- 对比三族：A pre-R8 变换族（变体对齐 + 逐参与模块 PROJECT 改写）；B post-R8 DEX 改写；C 消费 Soong 预编译 SystemUI 产物（prebuilt 替换源码模块，违反规则 S/ADR 0003，红线）。B/C 否决；逐模块 Gradle 复刻属于 A 族的执行机制，不属于 C。
- **保留 A 族为首选，但具体算法证据不足，实施前必须完成四个有界实验（E1–E4）**：E1 逐产物变体表（stock R8 输入 rsp 与我们 `libs/` 清单对照）；E2 受影响 AAR 的 repackaged 变体干跑；E3 project 产物 jarjar 干跑 + 耗时实测；E4 SysUISdk android.jar 对 hidden 名的实际 R8 解析验证。
- 初审的“Scope.ALL 一次性 jarjar + 删除 hidden 定义”算法**已废弃**（所有权不安全：会误删/重定向 app 自带 aconfig 实现，与 stock `FeatureFlagsImpl` 证据矛盾）。候选算法：受影响 AAR 改从 AOSP `repackaged-jarjar/` 中间产物重打包 + 逐参与模块 project 编译产物做 jarjar 引用改写（`:app` 无源码，不存在单点 registration；AGP API 为 `Artifacts.forScope(Scope.PROJECT)`，`useScope` 不存在）+ **不做任何定义删除**（交给 R8 liveness）。
- 初审的“R8 missing-class 需附加 turbine jar 或窄域 dontwarn”论断**已撤销**（ fabrication）：SysUISdk android.jar 与 `libs/framework.jar` 均已同时含四 critical 类原名与 hidden 名两份；下一任务只需验证现有 SysUISdk 解析，`-dontwarn` 被 brief 禁止，不作为选项。
- 下一张可执行 brief 只覆盖 E1–E4 实验（含 Allowed/Forbidden Paths 与 gate，报告 §5.1）；实现任务范围显式 defer，待 E1 输出完整清单后另立（报告 §5.2）。

### 二轮复审修正记录（chief 二审 FAIL 后，本 commit）

五项修正：(1) AGP API 更正为 `Artifacts.forScope(Scope.PROJECT)`（一手源码：`gradle-api-9.3.1` 内 `Artifacts.kt:136`、`variant/ScopedArtifacts.kt:31-38`，`useScope` 不存在）；写入“`:app` 无源码、单点 registration 不可行”的关键限制，候选改为集中配置到每个参与 Android 源码模块 + JVM 模块显式盘点，否则 unresolved；逐模块机制从 C 的否决理由中移除，C 收窄为“消费 Soong prebuilt SystemUI 产物”（源码优先红线）。(2) gate 硬化：全规则任一 target 被 define 即 FAIL（新增 3 个单测：非 critical target 定义、critical target 定义、app 自带原名定义不误杀；共 26 个全绿；stock 预期结果不变）。（3）§3.1 收窄：仅四 critical source 强制完全缺席，不得推广到全规则 source（app 自带定义合法出现在 type_ids），全规则 source 统计降为诊断。(4) 变换 fixture 更正：jarjar 同时改名引用与定义，fixture 必须是分离输入（PROJECT artifact 零 source 定义被变换 + external 定义 jar 不变换），前置断言零 source 定义、后置断言零 hidden target 定义。(5) §5 重构：下一张可执行 brief 只定义 E1–E4 实验任务的 Allowed/Forbidden Paths 与 gate，实现任务的路径/坐标清单显式 defer 到 E1 输出之后；顺带修正 CRLF 单测注释（fixture 保留末尾换行）。

### 复审修正记录（初审 FAIL 后）

六项修正：(1) 方案 A 降级为“族级首选 + 算法待实验”，删除“无需补充实验”声明，改写候选算法与 E1–E4；(2) 撤销 fabricated 的 R8 missing-class 裁决项，改为“验证现有 SysUISdk 解析”；(3) Debug 语义更正——定义也出现在 type_ids，source-absent 判据对残留定义同样适用，今日未变换 Debug 观察与未来变换预测已明确分离；(4) “726 rules” 全部更正为“725 条规则 / 726 物理行”；(5) 分片证据更正——自动规则路径单 shard（`TransformJarJar` 硬编码 1，`builder.go:1156-1158`），`jarjar_shards: 10` 只作用于显式 rules 路径；(6) gate 工具加固——sha256 改为原始字节哈希、非法 UTF-8 规则文件干净 exit 2、uleb128 拒绝第 6 字节（`shift >= 35`），新增 4 个单测（共 23 个，全绿）。

新增直接证据：stock R8 输入清单 `withres/SystemUI.jar.rsp`（463 项，163 走 `repackaged-jarjar/`；SettingsLib/WM-Shell 为 repackaged 变体，device_policy export 等为普通 javac 变体）；我们 `libs/` 97 产物常量池扫描（SettingsLib-2.0.1、WM-Shell-2.0.0、WM-Shell-shared-2.0.1、personalcontext_ace_visualizer 四 AAR 引用 critical 原名、无 hidden 字符串——从非 repackaged 中间产物打包，与 stock 变体不一致）；SysUISdk android.jar 与 framework.jar 双形态验证。

### 构建声明

本任务**未运行**任何 Gradle/Soong/ADB/emulator 命令（任务约束）；Debug APK 未构建（输出目录为空），Debug 可运行性解释为推断。

## 错误数演变

本任务不以编译错误数为指标。静态 gate 的预期初始状态为 Release FAIL、stock PASS；实现任务只有在用户裁决后另开。

## 待解决问题

- [已答] 725 条规则生成/传播/执行机制：见架构报告 §2（生成→prefix 填充→provider 传播→各模块编译产物 jarjar，全部一手源码定位；含 §2.7 stock R8 输入逐产物变体选择）。
- [已答] Gradle seam 对比：保留 pre-R8 变换族为首选，**算法待 E1–E4 实验与用户裁决**（实验任务 brief 见报告 §5.1，实现范围 defer 至 §5.2）。
- [已答] 只改引用不打平台类：候选算法不含任何定义删除步骤——project 产物引用改写 + AAR repackaged 变体对齐，app 自带 aconfig 定义交 R8 liveness，与 stock 同构。
- [部分答] Debug/Release 一致性：今日未变换 Debug 为观察推断；未来变换后 Debug 将保留 app 自带 jar 的原名定义（出现在 type_ids，source-absent 判据同样适用），Debug gate 口径需用户裁决。
- [新] E1–E4 有界实验（变体表、AAR 干跑、project 产物干跑、SysUISdk R8 解析）——进入实现任务前必须完成；实验任务 brief（Allowed/Forbidden Paths 与 gate）见报告 §5.1。
- [新] 我们 AAR 从非 repackaged 产物打包的修正（`tools/package_aosp_aar.py` 输入选择；完整受影响清单依赖 E1）。
- [新] stock `FeatureFlagsImpl` 的 R8 存活链未完全追溯（不影响 gate 与方案，已标 unknown）。
