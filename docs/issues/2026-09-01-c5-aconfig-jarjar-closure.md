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
- 规则文件 726 行，SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`；`SystemUI-core`、`SystemUI-application` 与 compatibility library 的中间产物使用同一内容。
- AOSP host tool：`/home/conv/myspace/aosp/out/host/linux-x86/framework/jarjar.jar`，支持 `process <rulesFile> <inJar> <outJar>`。
- 四个已触发/确认的关键类：
  - `android.app.Flags`
  - `android.os.Flags`
  - `android.view.accessibility.Flags`
  - `com.android.window.flags.Flags`
- 初步 DEX type-table 扫描：当前 Gradle Release 对上述四项全部为 source-present/target-absent；stock 全部为 source-absent/target-present。
- 全 726 条 exact-rule 初筛：Gradle Release 为 30 source / 0 target；stock 为 1 source / 36 target。stock 的唯一 source 是已定义类 `android.app.admin.flags.FeatureFlagsImpl`，因此不能把“726 条 source 全部为 0”误写成通用 gate。

## 本步计划

1. 固化秒级静态 gate，精确区分 DEX type reference 与 class definition；当前 Release 必须稳定红，stock APK 必须绿。
2. 从 `frameworks/base/Android.bp` 与 Soong Java/JarJar 实现追出 726 条规则的生成、传播与执行时序。
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

- 工具 `tools/check_aconfig_jarjar_references.py`（纯 stdlib DEX type-table/class-defs 读取器，exact 规则校验，critical 四类硬编码）+ 19 个单测全绿：
  `uv run pytest tools/tests/test_check_aconfig_jarjar_references.py -q` → `19 passed`。
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

### P3 推荐（待用户裁决）

- 对比三族：A pre-R8 AGP `ScopedArtifact.CLASSES`（`useScope(ALL)`）单点变换；B post-R8 DEX 改写；C 复用/再处理 Soong 产物（prebuilt 形态违反规则 S/ADR 0003）。
- **推荐 A**：复用 Soong 的 jarjar.jar + 冻结 725 规则在 AGP 公开 API seam 上做 classfile 级改写，剥离改名产生的 hidden 定义，R8 shrinking 自然清除失引用原名定义（与 stock 同构）。开放裁决项：R8 对 hidden 名 missing-class 的解法（附加 AOSP repackaged framework turbine 作 library vs 窄域 dontwarn，后者需用户逐条批准）。
- 实现 brief 草稿见报告 §5（未执行）。

### 构建声明

本任务**未运行**任何 Gradle/Soong/ADB/emulator 命令（任务约束）；Debug APK 未构建（输出目录为空），Debug 可运行性解释为推断。

## 错误数演变

本任务不以编译错误数为指标。静态 gate 的预期初始状态为 Release FAIL、stock PASS；实现任务只有在用户裁决后另开。

## 待解决问题

- [已答] 725 条规则生成/传播/执行机制：见架构报告 §2（生成→prefix 填充→provider 传播→各模块编译产物 jarjar，全部一手源码定位）。
- [已答] Gradle seam 对比与推荐：方案 A（AGP `ScopedArtifact.CLASSES` pre-R8 变换 + Soong jarjar.jar + 冻结规则），待用户裁决后开实现任务（brief 草稿见报告 §5）。
- [已答] 只改引用不打平台类：变换后剥离 `com/android/internal/hidden_from_bootclasspath/**` 定义条目（输入侧断言恒为零，输出侧全部为刚改名产物）；R8 missing-class 解法待裁决。
- [部分答] Debug/Release 一致性：方案 A 对 D8/R8 同一变换产物，Release 收敛到 stock 形态、Debug 保持自洽（原名定义残留但无悬空引用）；Debug 当前未构建，其可运行性为推断。
- [新] R8 侧对 hidden 名 missing-class 的裁决（附加 library jar vs 窄域 dontwarn）。
- [新] stock `FeatureFlagsImpl` 的 R8 存活链未完全追溯（不影响 gate 与方案，已标 unknown）。
