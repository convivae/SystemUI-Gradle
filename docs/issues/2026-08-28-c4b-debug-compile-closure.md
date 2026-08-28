# Task 073 — C4b：编译闭环（`:app:assembleDebug` 恢复绿）

**日期**：2026-08-28
**任务**：docs/orchestration/tasks/073-c4b-debug-compile-closure.md
**前置**：C4a（task072 接线，`gradle help` 绿）、C2（task071 libs 再生）、C3（task070 源码重对齐）
**目标**：`:app:assembleDebug` **BUILD SUCCESSFUL**；对齐门/pytest 保持绿；新产物冻结指纹可复现。
Release/R8 归 task074；runtime 归 C5。

## 1. 计划

| 步骤 | 内容 |
|------|------|
| P0 | kairos 源码模块 `:SystemUI-utils-kairos`（tier①，拷贝 63 kt + JVM build 文件 + settings 注册 + 对齐工具映射 + core 依赖） |
| P1 | 新 tier② 产物：personalcontext_ace_visualizer AAR、SerialPortAccessDialog AAR、mechanics / mechanics-compose jar（tools 脚本扩展 + pytest + 冻结指纹） |
| P2 | 编译循环：`:app:assembleDebug`，按错误分类一次一个根因；新 flags 包按错误驱动补 `tools/package_aconfig_jars.py` |
| P3 | 验收：assembleDebug 绿 + `check_source_alignment.py --strict` exit 0 + pytest 全绿 |
| P4 | 文档收尾（错误数演变、bp 依据、CONV 对账、移交 task074 清单）+ STATE.md |

## 2. P0 记录：kairos 源码模块

- bp 依据：`packages/SystemUI/utils/kairos/Android.bp` — `java_library "kairos"`（JVM，无 res/manifest），
  srcs `src/**/*.kt`（63 文件），static_libs：kotlin-stdlib、kotlinx_coroutines、tracinglib-platform、
  androidx.collection_collection。tier①（规则 S）。
- 形态：仿 `:SystemUI-plugin-core`（`java-library` + `org.jetbrains.kotlin.jvm`，src 直根）。
- 依赖映射（Gradle）：
  - `android.os.Build/SystemProperties` → `compileOnly(files(libs/framework.jar))`
  - `com.android.app.tracing.*` → `compileOnly(files(libs/prebuilts/tracinglib-platform.jar))`（既有产物）
  - coroutines → `implementation(libs.kotlinx.coroutines.core)`
  - androidx.collection（ScatterMap/ObjectIntMap 族）→ `implementation(libs.androidx.collection)`
    （新 catalog alias `androidx-collection`，版本 1.5.0 = core 编译类路径当前解析版本，避免图漂移）
- 对齐工具映射新增：`M(["utils/kairos/src"], "SystemUI-utils-kairos", "src", note="kairos")`
  （brief §1 授权的唯一对齐工具编辑）。

## 3. P1 记录：新 tier② 产物

| 产物 | 形态 | bp 依据 | Gradle 接线 |
|---|---|---|---|
| `libs/mechanics.jar`（190 类） | jar | `frameworks/libs/systemui/mechanics`（android_library，无 resource_dirs） | core `implementation(files(...))` |
| `libs/mechanics-compose.jar`（23 类） | jar | `.../mechanics/compose`；17 core bp static_libs L559 | 同上 |
| `libs/aars/personalcontext_ace_visualizer.aar` | AAR | `frameworks/libs/systemui/ace/src/.../visualizer`（含 res，7 drawable） | core 直接 AAR（Task 059 例外） |
| `libs/aars/personalcontext_ace_client.aar` | AAR | 同目录 client（含 clientsdk/compat/res： declare-styleable/id） | 同上 |
| `libs/aars/SerialPortAccessDialog.aar` | AAR | `frameworks/base/libs/serial/accessdialog`（含 res 全 locale strings） | 同上 |

要点：
- **ace 拆双 AAR**：visualizer（viz Kotlin jar + ace_common Kotlin jar 合并，bp static_libs 闭包，
  TraceurCommon 先例；common 无 res 无 R 引用，且 common 的 `**/*.kt` 已含 embeddedscroll 同名类）
  与 client（自有 R namespace `com.android.personalcontext.ace.client`，`AceEmbeddedSurfaceViewCompat`
  引用 client R；visualizer 公有签名引用 client 的 `ClientActionInsight`）必须拆两个 AAR——
  单 AAR 只能承载一个 manifest package/R namespace。三 Kotlin jar 互不相交已验证（comm 为空）；
  visualizer KSP 输出（ksp-classes.jar）为空 → Kotlin jar 即完整类集。
- **SerialPortAccessDialog**：manifest 携带 AccessDialogActivity 声明 + MANAGE_SERIAL_PORTS 权限
  （必须 AAR 交付并入 app manifest）；`android:theme="@style/Theme.SystemUI.Dialog.Alert"` 引用
  SystemUI-res 资源（bp static_libs SystemUI-res），Gradle 侧由 app 合并资源解析。
- 冻结指纹：mechanics×2 源=基线（首生即冻结，同 surfaceeffects）；AAR 三件由
  `tools/package_aosp_aar.py` 固定 ZIP metadata 重建，字节确定性已由既有 pytest 覆盖模式保证。
- pytest：`test_package_aosp_aar.py`（CONFIGS 33）+ `test_package_misc_jars.py`（17 条目）
  新增路径断言全绿。

## 4. 编译循环：错误数演变

| 轮次 | 命令 | 结果 | 错误 | 根因与处理 |
|---|---|---|---|---|
| R1 | `:app:assembleDebug`（build1） | FAILED 30s | 182 e: | 三类：①17 新 source root 未接入（common 缺 log/core/src、plugin-core 缺 annotations/src）②17 bp 新依赖边未接（plugin-core→LogCore、biometrics→shared-utils、common 缺 view_capture/flags）③wmshell-shared AAR 缺 AIDL 闭包 + SysUISdk 缺 17 新隐藏 API |
| R2 | 同上（build2） | FAILED | 0 e:（Kotlin 全清） | 批次 1 修复后 Kotlin 编译全绿；新阻塞：res-product bool product-variant 资源重复 |
| R3 | `biometrics/plugin-core/shared:compileKotlin`（build3） | FAILED | 2 e:（animation setFilter） | RemoteTransition.setFilter 为 SysUISdk 缺失的 17 新隐藏 API |
| R4 | 六模块 compile + --continue（build4） | FAILED | 5 e: | biometrics 3（USER_TYPE_PROFILE_SUPERVISING / TYPE_STANDALONE×2）+ animation 2（setFilter）；plugin/unfold/customization/clocks-common/compose 全绿——均属 SysUISdk 缺 API |

### 批次 1 修复清单（R1→R2）

| 修复 | 文件 | bp 依据 |
|---|---|---|
| `log/core/src` source root | SystemUI-common/build.gradle.kts | SystemUILogCoreLib（log/Android bp，17 新增；log/src import com.android.systemui.log.core.*） |
| view_capture + systemui-flags compileOnly | SystemUI-common/build.gradle.kts | SystemUI-shared-utils bp static_libs（WindowManagerUtils.kt 用） |
| `annotations/src` source root | SystemUI-plugin-core/build.gradle.kts | PluginAnnotationLib（17 新增 source root） |
| api(:SystemUI-common) | SystemUI-plugin-core/build.gradle.kts | PluginCoreLib bp static_libs SystemUILogCoreLib（PluginListener 签名引用 MessageBuffer → api） |
| implementation(:SystemUI-common) | SystemUI-shared-biometrics/build.gradle.kts | BiometricsSharedLib bp static_libs SystemUI-shared-utils |
| wmshell-shared AAR 并入 aidls javac jar（19 类：IShellTransitions/AnimatedSurface/IHome/IFocus/IOverviewOverlayLeash） | tools/package_aosp_aar.py + install 升 2.0.1 + catalog | 17 WindowManager-Shell-shared bp static_libs WindowManager-Shell-shared-aidls |

### 剩余阻塞（两项，均需 chief/user）

1. **REDLINE res-product**：17 res-product/values/config.xml 新增 `<bool config_enableLargeScreenScreencapture product="default|tablet|desktop">` 三变体；
   AAPT2 不支持 product 属性 → `packageDebugResources` 报重复。修复需按 ADR 0004 对 tablet/desktop 两行加
   CONV_DEL 标记（与 task070 对 strings.xml 的 5806 处同类同目录同机制），但 res** 属 CHARTER Part 5.1
   红线（CONV 也需用户授权），本 brief File Map 仅授权 `SystemUI-*/src` 的 CONV → 停工待授权。
2. **SysUISdk 需重建（brief authority 字段明确的汇报项）**：SysUISdk android.jar 生成于 2026-08-21，
   早于 C2/C3 的 17 树再同步（2026-08-27，task071 冻结指纹已记录多处 byte drift）；当前树 framework.jar
   含而 android.jar 缺的 17 新隐藏 API（至少）：`android.window.RemoteTransition.setFilter(TransitionFilter)`
   （animation）、`android.os.UserManager.USER_TYPE_PROFILE_SUPERVISING`、
   `android.hardware.fingerprint.FingerprintSensorProperties.TYPE_STANDALONE`（biometrics）；
   另 ace AAR 类引用 `android.service.personalcontext.insight.ContextInsight`（android.jar 无，dex 期可能报缺）。
   修复 = `python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp` 重建（脚本本身禁改，运行属重建，
   按 brief authority 需 chief 批准）。

## 5. 验证记录

（待补）

## 6. CONV 对账

（待补）

## 7. 移交 task074 清单

（待补）
