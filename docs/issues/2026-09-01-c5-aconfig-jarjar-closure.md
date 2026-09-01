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

待 task078 获批并执行后填写。

## 错误数演变

本任务不以编译错误数为指标。静态 gate 的预期初始状态为 Release FAIL、stock PASS；实现任务只有在用户裁决后另开。

## 待解决问题

- 726 条规则在 Soong 中的精确自动传播机制和最终执行点。
- Gradle 可支持且最接近 Soong 的程序类变换 seam。
- 如何只改写应改写的引用，同时避免将 framework-owned 原名或改名类作为 APK 自有实现打包。
- Debug 当前是否因打包部分原名 Flags 类而“偶然可运行”，以及最终方案是否必须统一 Debug/Release 输出语义。
