# Current State（唯一完整实时技术状态）

> **Owner**: 本文件是项目**唯一完整实时技术状态 owner**。其他文档（HANDOFF/PLAN/README/AGENTS/CHARTER/STATE）只链接或摘要，不复制完整状态。
> **Last verified**: 2026-08-26（Release runtime 闭环：task 060/060b/061 三轮修复 AssumeFalseForR8 → -dontobfuscate → -keep 抗 R8 水平合并，emulator-5554 现跑 Release APK 14768581 零 crash；此前 2026-08-25（**DEBUG_RUNTIME_PASS 达成**：Task 058 gate suite 全绿——pytest 243+、duplicate-classes、源码对齐 0/0/0、manifest-dex 闭包、clean build `e8aad131`、emulator-5554 原子部署后 PID 稳定零 crash；Tasks 053–059 same-tree x86_64 runtime 全线闭环；origin/main 同步至 `abbecdde`+镜像提交）
> **Update triggers**: 任何 merge 改变了 build/test/blocker/toolchain/当前下一步 → 必须更新本文件（见 `docs/README.md` 维护触发条件表）

---

## TL;DR

| 维度 | 状态 |
|------|------|
| Debug APK | **`:app:assembleDebug` SUCCESS**（每批硬门禁；Task 045 main fresh 对生成 SDK 验证 1m10s） |
| Python 工具测试 | **220/220 通过**（Task 045 main fresh） |
| Release R8 | **SUCCESS（Task 045 main fresh，exit 0，missing refs 0）**：对生成 SDK fresh `--rerun-tasks` 3m41s |
| `:app:assembleRelease` | **SUCCESS（Task 045 main fresh）**：两个 AGP 9.3.1 optimized-resource tasks 实际执行 + V2 签名；APK 28,600,808 B，SHA-256 `cd4b885e...` |
| SysUISdk 生成器 | **单入口落地并 main fresh 验收（Task 045）**：`python3 tools/build_sysuisdk.py --aosp-root <aosp>`；确定性、事务性、39-entry bridge；两次 11,382-file 输出逐字节相等 |
| 设备/模拟器运行验证 | **DEBUG_RUNTIME_PASS（2026-08-25，Task 058）**：same-tree `sdk_phone64_x86_64` emulator-5554 运行迁移后最终树 Debug APK（sha256 `e8aad131…`，本地构建与设备逐字节相同）；PID 稳定 10×30s 采样、零 FATAL/NoClassDefFoundError、StatusBar/NotificationShade/Taskbar 在屏。路径：Task 052c 产品矩阵 → Task 053 dex forensics 定根因（SysUISdk 公开名 vs 设备 hidden twin）→ Task 054/055 批量 12 个 aconfig flags JAR 补类 → Task 057 合并单 JAR `libs/systemui-aconfig-flags.jar` → Task 059 四族 AAR 直接消费迁移（字节中性已证）。 |
| 当前唯一工程优先级 | Release runtime **已 PASS**（task 061，2026-08-26）。剩余：tracinglib-platform.jar 溯源；维护性观察（Kotlin 2.3/AGP 9.5 解锁、AOSP 树漂移回查、官方 Maven 等价物回查）。 |

R8 missing refs 轨迹：140 → 126 → 119 → 109 → 106 → 88 → 81 → 7 → 1 → **0（Task 044）**。该轨迹继续作为诊断证据，但不再驱动 artifact seam 或要求 Soong/Gradle 输出一致。

## Verified milestones（已完成里程碑，最新在后）

| 时间 | 里程碑 | 证据 |
|------|--------|------|
| 2026-08-11 | KSP + Dagger 首次通过（0 KSP 错误） | commit `05ea2064` |
| 2026-08-12 | 全依赖升级 + AGP builtInKotlin；KSP/Kotlin/core javac 全部 0 错误 | `docs/issues/2026-08-12-current-progress-standards-review.md` |
| 2026-08-13 | core javac 0 错误（8 组根因清零）；SysUISdk 可复现 + framework-res + `androidprv` 修复 | `docs/issues/2026-08-13-agp-androidprv-namespace-fix.md` |
| 2026-08-19 | **首个 debug APK**（Task 015，158,775,460 B）；SettingsLib per-target res closure（ADR 0005） | `docs/issues/2026-08-19-settingslib-per-target-aars.md` |
| 2026-08-19 | 无混淆 release 基线（Task 029，126,642,058 B，V2 签名）；AOSP release 配置对齐 | `docs/issues/2026-08-20-release-r8-alignment-decisions.md` |
| 2026-08-20 | 官方 Maven 依赖审计落地（zxing 3.5.4 等，4 个本地 jar 退役） | `docs/issues/2026-08-20-official-maven-audit.md` |
| 2026-08-20 | R8 Batch 1–4C：clean monet/aconfig/view-capture/iconloader/WM-Shell proto/Traceur 产物；140→81 | `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` |
| 2026-08-20 | Traceur 双 AAR（Task 038）：640 类 + 105 res；R8 88→81 精确；179/179 | `docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md` |
| 2026-08-21 | SettingsLib program/resource 闭包（Task 040）：主 AAR 1153 类、Theme 15 类、17 个 per-target 资源 AAR；R8 81→7 精确；195/195 | `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md` |
| 2026-08-21 | SysUISdk R8 library bridge（Task 041）：两个 SDK target 各注入 35 个真实 library classes；APK 0 打包；R8 7→1 精确；233/233 | `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md` |
| 2026-08-21 | **完整 Release closure（Task 044，main fresh）**：单 FQN release-only adapter；R8 1→0；`assembleRelease` + optimized resource shrink + V2 签名成功；APK 28,600,808 B；239/239 | `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md` |
| 2026-08-21 | **SysUISdk 单入口 composition（Task 045，main fresh）**：`build_sysuisdk.py` 重写为事务性单命令生成器；两次 11,382-file 真实 AOSP 生成逐字节相等；main 上 Debug/R8/Release/ZIP/V2/DEX 全绿；七个 superseded 仓库文件已删；220/220 | `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md` |
| 2026-08-22 | 单入口文档同步与 legacy live SysUISdk 清理（Tasks 046–047）：用户批准后精确删除 8 个冗余备份（163,149,374 bytes），保留唯一历史快照，live primary hashes 不变 | `docs/architecture/2026-08-21-legacy-sysuisdk-backup-inventory.md` |
| 2026-08-22 | **首个真实专用模拟器替换实验（Task 048）— `RUNTIME_FAIL`**：root/remount/push/hash/rescan 成功；Application 入口 namespace/R8 双重缺陷导致 crash loop；原 APK + userdata 恢复验证通过，AVD 删除；修正后双轴审查与 main fresh 静态验收 PASS | `docs/architecture/2026-08-21-device-systemui-runtime-preflight.md` |
| 2026-08-22 | **Debug 入口与真实首 fatal（Task 050）**：manifest 79 个组件入口改为 FQCN；fresh Debug APK 163,561,195 B / `4d8240fd…`，manifest→DEX 93 present + 2 aliases + 0 missing；扩容并重组 full super 后 byte-identical 部署，`-wipe-data` 触发 fresh PackageManager scan；真实 `SystemUIApplication` 启动后首 fatal 为 `Trace.registerWithPerfetto()` hidden-API denial | `docs/issues/2026-08-22-direct-debug-apk-runtime-closure.md` |
| 2026-08-23 | **Task 051 根因审计闭环**：证明 `SystemUIApplication` 的 AOSP `static_libs`→Gradle project dependency→APK DEX assembly 正确；Soong `platform_apis:true` 注入 `usesNonSdkApi=true`，Google image 上 Gradle APK 为 policy 2 / `usesNonSdkApi=false` 且不在该 image 平台签名域；Debug 24 DEX / 77,342 classes，Release 2 DEX / 15,683 classes；四类方案均 `NOT APPROVED`，用户选择 same-tree Family B；双轴 PASS + main fresh static PASS | `docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md` |
| 2026-08-23 | **Task 052 ARM64 构建/probe + 052A/B/C 研究闭环**：`sdk_phone64_arm64` `emu_img_zip` 在第二次严格 `-j4` 构建成功；direct SDK AArch64 QEMU/TCG 仅达 kernel/init/ADB、zygote 不稳且未 boot-complete；官方 source 证明 x86_64 launcher 拒绝 ARM64 guest、acloud 仍走该 launcher、`virt` 探针不是 Goldfish 支持路径；host-native `sdk_phone64_x86_64` 被选为下一候选；三个报告 main fresh acceptance PASS | `docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md` |
| 2026-08-25 | **Task 059 直接 AAR 迁移（用户裁定 Task 043 packet）**：WifiTrackerLib/iconloader/setupcompat/LowLightDreamLib 四族从本地 Maven 退役改直接消费 `libs/aars/`（AGENTS.md §3.2 例外）；animationlib 按设计保留、SettingsLib 伞形实验永久关闭、tracinglib 推迟 Release——6/8 packet 关闭。新旧解析路径串行干净重建 APK 逐字节相同（`e8aad131…`），类集合 77,832 全等，243/243 测试 | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` |

## Current build and verification matrix

| 验证项 | 状态 | 最新证据 |
|--------|------|---------|
| KSP（debug/release） | ✅ 0 错误（2933 文件生成） | Task 041 main fresh |
| core Kotlin | ✅ 0 错误 | Task 041 main fresh |
| core javac | ✅ 0 错误 | Task 041 main fresh |
| `:app:assembleDebug` | ✅ BUILD SUCCESSFUL（硬门禁，每批必过） | Task 045 main fresh（对生成 SDK，exit 0 in 1m10s，含 checkDebugDuplicateClasses；216 tasks） |
| Python 工具测试 | ✅ 220/220（Task 045：70 个新单入口生成器测试；36 个 legacy patch 测试随被删模块退役） | Task 045 main fresh |
| APK 类定义检查 | ✅ SysUISdk bridge 39/39 present in SDK；APK 0/39 packaged；无 `AssumeTrueForR8` | Task 045 main fresh（dexdump 15,683 defined classes 全量检查） |
| `:app:minifyReleaseWithR8` | ✅ exit 0，missing refs 0；effective config 对 FQN 仅一条 exact `-dontwarn`，无 keep/assume | Task 045 main fresh（对生成 SDK，`--rerun-tasks`，3m41s） |
| `:app:assembleRelease` | ✅ BUILD SUCCESSFUL：resource shrinking（`optimizeReleaseResources` + `convertShrunkResourcesToBinaryRelease` 实际执行） | Task 045 main fresh，exit 0（最终 optimized/package run 1m09s） |
| Release APK 检查 | ✅ 非空 28,600,808 B，SHA-256 `cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374`；`unzip -t` 无错；V2 scheme true | Task 045 main fresh |
| SysUISdk 单入口生成器 | ✅ 两次独立真实 AOSP 构建输出逐字节相等（11,382 文件）；refusal/replace 语义实测；marker 纯 provenance | Task 045 main fresh（`/tmp/task045-main-sdk-{a,b}`） |
| 设备/模拟器 install + runtime | ❌ **`RUNTIME_FAIL`；same-tree baseline 尚未成立**：Task 050 FQCN Debug APK 在 fresh scan 后进入 `SystemUIApplication`，首 fatal 为 Google image 上 hidden-API `using linking: denied`；Task 051 证明 assembly 正确并锁定 `usesNonSdkApi`/platform-signature runtime contract divergence。Task 052 same-tree ARM64 product已构建，但官方 x86_64-host launcher 拒绝 ARM64 guest；direct `virt` 探针仅达 ADB且 zygote/system_server 不稳，`sys.boot_completed` 为空，未部署 Gradle APK。下一候选 `sdk_phone64_x86_64` 尚未构建。 | Tasks 050–052；`docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md` |

## Toolchain and module topology

版本矩阵（升级须先与用户沟通；Compose **不得升 1.12**，`ExperimentalAnimatableApi` 已移除而 AOSP 在用）：

| 组件 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.3.1 | settings.gradle.kts 硬编码 |
| Kotlin | 2.2.10 | AGP `builtInKotlin=true` 内置，无显式 kotlin-android 插件 |
| KSP | 2.2.10-2.0.2 | 对齐 AGP 内置 Kotlin |
| Dagger | 2.59.2 | useBindingGraphFix 默认启用（≥2.58） |
| Compose | 1.11.4 | **上限**（1.12.0 移除 `ExperimentalAnimatableApi`） |
| material3 | 1.5.0-alpha18 | 对齐 compose 1.11.x |
| JDK | 21 | 工具链 |
| compileSdk | `SysUISdk`（自定义 preview） | 可由 AOSP `out/` 从零重建：`python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp`（Task 045 单入口；默认 base `android-37.0`，输出 `<sdk-root>/platforms/android-SysUISdk`） |
| kotlinx-coroutines | 1.10.2 | **上限**：1.11.0 新 `SharedFlow.collectLatest` overload 破坏 AOSP 源码（Task 035 REDLINE 裁定） |
| protobuf-javalite | 4.35.1 | latest-stable 政策（Task 035） |
| zxing | 3.5.4 | 官方 Maven 最新（Task 026/027） |

builtInKotlin 三件套（PITFALLS §1.5）：`android.builtInKotlin=true`、`android.disallowKotlinSourceSets=false`（Task 023 实验证实 REQUIRED）、每个 Android 模块 `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)`。

13-module 拓扑（语义对齐 AOSP `Android.bp`，ADR 0003）：

```
:app :SystemUI-core :SystemUI-res :SystemUI-common :SystemUI-animation
:SystemUI-plugin-core :SystemUI-plugin-processor :SystemUI-plugin
:SystemUI-unfold :SystemUI-customization :SystemUI-shared
:SystemUI-shared-biometrics :SystemUI-compose
```

## Dependency and artifact state

- `libs/`（jar + aars + maven）全部提交入 git；新 clone 可直接构建。仅在重新生成 AOSP 产物时运行 `python3 tools/package_aosp_aar.py --all` + `python3 tools/install_aar_to_maven.py`。
- 当前 artifact 数量是新架构只读审查的重点：`libs/maven/` 有 23 个 AAR（Task 059 退役 4 个单 consumer 族后），其中 20 个属于 SettingsLib family；`libs/aars/` 有 29 个 AAR。它们不是自动回退清单。
- 当前本地 Maven 交付包括 SettingsLib 1.0.1（1153 类；POM 携 17 条 per-target 依赖边，ADR 0005）、SettingsLibSettingsTheme 1.0.1（15 类）、17 个 SettingsLib per-target res-only AAR、WindowManager-Shell 1.0.1（含 proto 闭包 1888 类）、WindowManager-Shell-shared 1.0.0、animationlib（3 个模块共享，用户裁定按设计保留本地 Maven）、SettingsLibColor。
- **直接 AAR 消费集（Task 059，用户 2026-08-25 批准，AGENTS.md §3.2 例外）**：WifiTrackerLib、iconloader、LowLightDreamLib、setupcompat 四个单 artifact、单 consumer（仅 `:SystemUI-core`）族经 `files("libs/aars/*.aar")` 直接消费；旧 Maven 坐标与 `libs/maven/` 树已退役。新旧解析路径各自串行干净重建产出**逐字节相同**的 APK（`e8aad131…`），定义类集合 77,832 全等（与 emulator-5554 现行部署基线 `b827df78…` 亦类集合全等，仅 D8 dex 打包布局差异）；详见 `docs/issues/2026-08-25-aar-direct-consumption-migration.md`。
- Traceur：双直接 AAR（TraceurCommon 640 类 + Traceur-res 105 res，Task 038）；占位 jar 已退役。
- 官方 Maven 坐标优先（Task 026 审计后）：zxing、protobuf-javalite、coroutines 1.10.2、errorprone 等走公网；AOSP prebuilts 版本多数不在公网，逐个查 `maven-metadata.xml`。
- aconfig flags：五个完整 Soong `javac` 产物 JAR（Task 034，位于 `libs/` 根目录）；notification flags 已从本地 Maven 迁出，现为 `libs/notification-flags.jar`。
- aconfig 运行时闭包族（2026-08-24 起；task 057 用户方案 M 合并）：`libs/systemui-aconfig-flags.jar` 为 14 个 framework exportable-aconfig owning `java_aconfig_library`（window / device-state-feature / android-os / smartspace / content-pm / biometrics / usb / net-platform / permission / provider / security / service-controls / service-notification / quickaccesswallet，base 变体）javac 源的**确定性并集**（70 类 + 56 `.uau` 逐字节对源一致，连跑两次 sha256 相同 `5b629580…2174`），由 `uv run python tools/package_aconfig_jars.py --merge-framework` 生成，修复设备 bootclasspath 只有 `hidden_from_bootclasspath` 重写名、缺公开名的 `NoClassDefFoundError`。`:SystemUI-core` 单条 wiring。14 个单 JAR 已删（其配置仍留在 packager 作 provenance/单名调试口）。详见 `docs/issues/2026-08-25-aconfig-flags-single-jar-merge.md`。
- **Task 045 后**：`libs/android-merged.jar` 与 `libs/framework-res.apk` 已删除（被单入口生成器的 AOSP 输入取代）；`libs/keepanno-annotations.jar` 保留（`:SystemUI-core` 独立 compile-only 依赖）。
- `libs/prebuilts/` 仅剩 `tracinglib-platform.jar`（历史遗留，逐步清理）。

## Release closure：已关闭（Task 044）

最后一个 missing ref `com.android.aconfig.annotations.AssumeTrueForR8` 已按用户批准的 option A
关闭：`app/proguard_gradle.flags` 唯一 active rule 为 exact
`-dontwarn com.android.aconfig.annotations.AssumeTrueForR8`，仅接入 release build type（debug
与 5 个 AOSP-owned 规则文件未动）。不引入 annotation class/JAR/AAR、SysUISdk 变更或任何
assume/folding 规则；aconfig flag runtime 语义不变。Task 044 contract 测试
（`tools/tests/test_gradle_r8_adapter_rules.py`）机械钉住该边界。

**Resource-shrink 验收裁定**：brief 原字面判据（日志含 `:app:shrinkReleaseRes`）在 AGP 9.3.1
下不可满足（该任务已不存在）；Worker 未先提 REDLINE 而直接替换为 AGP-native 证据，属流程
偏差。双轴 review（base `3cc95a49` / head `4a0a8b08`）判 Spec FAIL BLOCKER；架构师向用户
披露后，用户批准继续，**post-review waiver** 接受 `optimizeReleaseResources` +
`convertShrunkResourcesToBinaryRelease` 实际执行的证据作为修正后的语义验收。详见
`docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`。

## Next ordered work

1. ✅ Tasks 046–048：SysUISdk 文档/备份闭环与首个 disposable Google AVD runtime `RUNTIME_FAIL` 已完成。
2. ✅ Task 050：FQCN Debug APK 构建、镜像扩容/full-super 重组、fresh PackageManager scan 与首个真实 hidden-API fatal 已完成；调用点 `try/catch NoSuchMethodError` 被用户否决。
3. ✅ Task 051：app→core→DEX assembly、hidden-API/platform-signature 分歧和 Debug size 根因审计完成；双轴 review 与 main fresh static acceptance 通过。四类修复 family 保持 `NOT APPROVED`；用户只批准了 Family B 方向。
4. ✅ Tasks 052/052A/B/C：same-tree ARM64 `emu_img_zip` 构建与诊断 probe 完成；官方 launcher/source/product matrix 研究确定 ARM64-on-x86_64 非正式支持路径，`sdk_phone64_x86_64` 为主候选，Cuttlefish x86_64 为 prerequisite-gated 备选。
5. **等待聊天内 bounded-design 批准**：先停止 PID 1727011 的 `task052-arm64`，证明无 QEMU/Emulator/ADB target；在严格 `m -j4 emu_img_zip`、29 GiB 当前可用空间、预计新增 15–17 GiB、10 GiB stop threshold、无并行 Gradle/Soong 下构建 `sdk_phone64_x86_64 trunk_staging userdebug`，并在实际 launcher context 证明 effective KVM access。未经独立证据与决策不删除既有 AOSP output。

6. ✅ Task 053：DEX 字节码取证完成（`docs/issues/2026-08-25-dex-bytecode-forensics.md`），NLSUMI 重复注册根因锁定为构造首次拋出（`alreadyRegistered` 循环）。
7. ✅ Task 054：`libs/android-os-flags.jar`（base 变体，byte-identical）已打包并接入 `:SystemUI-core`；task053 三处 TEMP-DEBUG 已移除且源对齐 MISSING/MISPLACED/EXTRA=0。设备验收：`android/os/Flags` NCDF 归零、重复注册 crash 归零、SysUIDup 静默；**PID 稳定被下一族 hazard `android/service/notification/Flags` 阻塞**（预扫描共 11 个，均有 hidden twin），建议 Task 055 同法修复。
   - ✅ **Task 055（2026-08-25 验收全绿）**：11 个同族 hazard 一次性批量关闭——8 个缺失 owning `java_aconfig_library` 单次 `m -j4`（lunch `sdk_phone64_x86_64-trunk_staging-userdebug`）构建齐，11 个 base-变体 javac JAR byte-identical 进 `libs/` + 接线；APK 24 dex 全扫 11+1（android/os 回归）Flags 类各恰好 1 处定义；emulator-5554 部署后 **PID 835 稳定 ≥5min、全窗零 NoClassDefFoundError、零 FATAL EXCEPTION、状态栏窗口存在且可见**（`docs/issues/2026-08-25-aconfig-flags-batch-closure.md`）。注：构建时 `export TOP=$(pwd)` 会破坏非交互 envsetup，应 `cd $AOSP_ROOT && . build/envsetup.sh`；部署 rm+cp 后必须校验目标 sha256（本任务拦到过 cp 静默截断）。
   - ✅ **Task 057（2026-08-25 验收全绿，用户方案 M）**：14 个族 JAR 合并为单一 `libs/systemui-aconfig-flags.jar`（确定性：连跑 sha256 相同；70 类+56 .uau 逐字节对源；类路径重叠 fail、manifest 去重）；wiring 收敛为 1 行；14 单 JAR 已 `git rm`；重建 APK 与 task055 已验基线**逐字节相同**（`b827df78…`），14/14 Flags 类 defs=1；设备按字节目标已满足，正式验证窗 PID 835 稳定 5min+、零 NCDF、状态栏可见。`pdvc_impl.txt` 确认为 task053 scratch 已删。（`docs/issues/2026-08-25-aconfig-flags-single-jar-merge.md`）
8. same-tree stock baseline 只有在 `sys.boot_completed=1`、`system_server` 与原厂 SystemUI 稳定后才允许部署 frozen Debug APK；最终 Debug gate 为 PID 稳定至少 60 秒，以及状态栏、Quick Settings、锁屏/唤醒/解锁、launcher 交互均无 fatal/ANR/watchdog/crash loop。
9. Debug runtime closure 后再单独验证 Release。Task 043 八个 `NOT APPROVED` packets 中 6 个已按用户 2026-08-25 裁定关闭（Task 059：4 族迁直接 AAR、animationlib 按设计保留、SettingsLib 伞形实验永久关闭）；AssumeTrueForR8 维持原标签（Release 姿态已由 Task 044 关闭），tracinglib-platform.jar 推迟到 Release 阶段。

## Verification commands and evidence

```bash
# SysUISdk 单入口重建（Task 045；需已构建的 AOSP out/）
python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp

# 单元测试（Python 工具测试）
python3 -m unittest discover -s tools/tests -p 'test_*.py'   # 当前 220/220

# Debug APK（每批硬门禁）
./gradlew :app:assembleDebug --console=plain

# Release R8（exit 0，missing refs 0）
./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain

# 完整 Release（minify + optimized resource shrink + V2 签名）
./gradlew :app:assembleRelease --console=plain
```

最新证据：Task 045 architect main fresh（2026-08-21，生成 SDK 位于 `/tmp/task045-main-sdk-a`，私有 root 暴露官方 SDK tools；`local.properties` 每次均 byte-for-byte 恢复）— 220/220 tests；两次真实 AOSP 构建输出逐字节相等（11,382 文件），marker 8 inputs/portable/no backups，refusal + owned replace 实测；`:app:checkDebugDuplicateClasses :app:assembleDebug` exit 0（1m10s）；fresh `:app:minifyReleaseWithR8 --rerun-tasks` exit 0（3m41s）、missing refs 0；最终 `assembleRelease --no-daemon` exit 0（1m09s），`optimizeReleaseResources` + `convertShrunkResourcesToBinaryRelease` 均实际执行；APK 28,600,808 B，SHA-256 `cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374`，`unzip -t` 无错，V2 scheme true，dexdump 全量 15,683 defined classes 中 0/39 bridge、无 `AssumeTrueForR8`。一次额外的全量 `assembleRelease --rerun-tasks` 在 R8 阶段 daemon disappeared；失败后发现同轮残留 Kotlin daemon 约 8.9 GiB RSS，释放后按 R8 与 optimized/package 两阶段串行恢复成功；当前权限下无内核 OOM 记录，因此不把该失败断言为已证实 OOM。该段是 Task 045 构建证据；当时设备/模拟器验证尚未运行。详细证据：`docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`。

最新 runtime 证据分三层。Task 048（2026-08-22）在 disposable Google API 37 AVD 上证明了 root/remount、动态 `pm path`、push、hash 与 PackageManager rescan 路径，但 frozen Release 因 manifest namespace/R8 双重入口缺陷进入 crash loop；原 APK 恢复并经 wipe-data 验证稳定，AVD 删除。详细证据：`docs/architecture/2026-08-21-device-systemui-runtime-preflight.md`。

Task 050 的 frozen Debug APK 为 163,561,195 B、SHA-256 `4d8240fdbbc144dfeb69b43dc3e5ad3911762afc90a8f83e07434d0669f78997`。79 个 manifest component 改为 FQCN 后，静态 gate 为 95 references（93 present + 2 aliases + 0 missing；`appComponentFactory` 尚需独立 gate）。在扩容 `system_ext`、生成 `--force-full-image` full super、重组 GPT 并 `-wipe-data` 后，设备 APK 与 frozen artifact byte-identical，PackageManager 正确实例化 `com.android.systemui.SystemUIApplication`。首个真实 fatal 为 line 87 `Trace.registerWithPerfetto()` 的 hidden-API `using linking: denied`，不是物理缺少方法。Task 051 进一步证明 app/core assembly 正确；Google image 上原厂包 `usesNonSdkApi=true` / policy 0，而 Gradle 包 `usesNonSdkApi=false` / policy 2，且双方 apksigner SHA-256 分别为 `301aa3cb…` 与 `c8a2e9bc…`。Debug 体积主因是未 shrink 的 24 个 DEX（134,153,384 uncompressed bytes，77,342 classes），不是单一资源。Task 051 固定范围最终 Standards PASS 零 finding；Spec PASS 无 BLOCKER/HIGH/MEDIUM（仅两个不影响结论的 TRIVIAL）；main fresh scope/hash/report gates PASS。未运行 Gradle或设备 mutation。详细证据：`docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md`。

Task 052 在同一 checkout 完成 `sdk_phone64_arm64 trunk_staging userdebug` 的 `m -j4 emu_img_zip`；第二次构建 exit 0，产物 ZIP 完整。SDK Emulator 36.6.6 的 AArch64 backend 在 TCG + 诊断性 `-machine type=virt` 下可达 kernel/init/ADB，但 `sys.boot_completed` 为空、zygote/system_server/SystemUI 不稳，Gradle APK 未部署。Tasks 052A/B/C 的 first-party docs/source/product research证明：x86_64 top-level launcher 有意拒绝 ARM64 guest；acloud local Goldfish 仍调用该 launcher；QEMU backend 能翻译不等于受支持的 Android product；ranchu PCI/MMIO mismatch 与 generic `virt` 均不能构成正式 Goldfish baseline。三个报告双轴阻断项清零并经 main fresh `TASK052A/B/C_REPORT=PASS`。当前 ARM64 诊断 guest PID 1727011 仍占约 3.4 GiB RSS 与 ports 5556/5557；在任何新 mutation 前必须干净停止。主候选为尚未构建的 `sdk_phone64_x86_64`；最新磁盘可用约 29 GiB，stop threshold 10 GiB；AOSP build 严格最多 `-j4`。详细证据：`docs/issues/2026-08-22-same-tree-arm64-emulator-runtime.md`。

构建纪律：全系统同一时刻**只允许一个 Gradle build**（CHARTER Part 4）；每批必须保持 `:app:assembleDebug` 成功（硬门禁）。

## Historical pointers

- 错误数/迁移历史：`docs/GRADLE_MIGRATION_LOG.md`（append-only）
- 深度调研与 audit：`docs/architecture/`（含 active operational audit `2026-08-20-r8-runtime-closure-audit.md`）
- 每日问题记录：`docs/issues/`
- 踩坑经验：`docs/PITFALLS.md`
- 未完成路线：`docs/PLAN.md`
