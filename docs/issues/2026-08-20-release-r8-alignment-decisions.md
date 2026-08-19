# 2026-08-20 — Release R8 / resource shrink AOSP 对齐决策

## 背景

Task 025 证明 `:app:assembleRelease` 被 `SystemUI-core/consumer-rules.pro` 悬挂引用阻塞。
Task 028 深度核对 AOSP Android.bp / Soong：AOSP 默认
`SYSTEMUI_OPTIMIZE_JAVA=true`，最终 app 开启 R8 optimize+shrink，非 eng 构建同时收缩资源；
SystemUI-core library 层零 ProGuard，plugin/plugin_core 通过 export flags 汇入 app。

## 用户批准（2026-08-20）

1. **G1**：完整删除 SystemUI-core 的 `consumerProguardFiles("consumer-rules.pro")` 和
   release `proguardFiles(..., "proguard-rules.pro")` 配置；core 与 AOSP 一样零 ProGuard。
2. **R3**：恢复 AOSP export flags 语义：
   - Android library `:SystemUI-plugin` 使用 `consumerProguardFiles`；
   - JVM library `:SystemUI-plugin-core` 无 AGP consumer DSL，AOSP 原始 flags 由 app
     `proguardFiles` 直接接入（规则文件仍归 module 所有；不为通道强改模块类型）。
3. **R1**：app release 开启 R8：`isMinifyEnabled=true`。
4. 保留官方 `proguard-android-optimize.txt`，叠加 byte-exact AOSP `proguard.flags` 链。
5. 不显式设置 `android.enableR8.fullMode`，采用 AGP 9.3.1 默认行为；如发现实证差异再单独决策。
6. **R2**：不推迟，R8 落地时同时设置 `shrinkResources=true`。
7. 不补 AOSP 自己未 export 的 SystemUIFlagsLib ParcelableFlag keep 规则。
8. 验收：release APK、platform 签名、关键类/dex、plugin rules 汇入、mapping/usage/seeds、147 tests。
9. 诊断边界：只可接入 AOSP 原始规则；禁止发明宽泛 keep、关闭 R8/检查或排除源码。
10. 批次：Task 029（G1+R3+未混淆 release 基线）→ Task 030（R1+R2 优化 release）。

## 依据

完整证据与 gap 表：`docs/architecture/2026-08-20-aosp-release-config-analysis.md`。
