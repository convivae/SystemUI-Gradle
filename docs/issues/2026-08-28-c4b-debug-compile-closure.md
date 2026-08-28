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
| R5 | `:app:assembleDebug --continue`（build5） | FAILED | 5 e: + patch 任务 exit 5 | res-product CONV_DEL 已落地（用户授权，commit `02e60a60`）后新暴露：`:app:patchDebugAndroidPrvMergedResources` 里独立 aapt2 compile 报 `Resource flag value undefined: 'com.android.systemui.dream_overlay_updated_ui'`（merged values.xml 的 `android:featureFlag` 样式） |
| R6 | 同上（build6） | FAILED | 5 e: + link 错 | R5 修复（见下批次 2）后 compile 侧过；新暴露 link 侧：merged manifest `uses-permission` 的 `android:featureFlag`（aapt2 link 对 manifest 元素空 flag 表默认 fail_on_unrecognized_flags） |
| R7/R8 | 同上（build7/build8） | FAILED | 5 e: + link 错 | R6 修复（manifest 属性 CONV_DEL，R7 首次注释含 `--` 非法改写一次）后 link 过 featureFlag 门；最终暴露 20 条 `resource android:color/… not found`（见剩余阻塞 2，与 5 e: 同根因） |

### 批次 2 修复清单（R5→R8，本轮）

| 修复 | 文件 | 说明 |
|---|---|---|
| aapt2 compile 转发 feature flags | tools/patch_androidprv_merged_resources.py + libs/systemui-aconfig-flags.txt | Soong 用 `--feature-flags @aconfig-flags.txt`（Android.bp flags_packages）传值，AGP 无等价通道：merge 用的内嵌 Kotlin aaptcompiler 移植版不做 flag 校验，而本脚本独立 aapt2 compile 会校验。修复 = 脚本对每次 compile 转发 `--feature-flags @<file>`；flags 文件 = Soong `com_android_systemui_flags` aconfig_declarations 模块产物（282 行，sha256 `031f4e80…`），按 tier② 产物规则字节保全拷入 `libs/`。CLI：`--feature-flags FILE` / `--no-feature-flags`，默认自动发现 `libs/systemui-aconfig-flags.txt` |
| manifest featureFlag 属性 CONV_DEL | SystemUI-application/src/main/AndroidManifest.xml | AGP 9.3.1 `AaptV2CommandBuilder` 的 link 命令无 feature-flags 参数（字节码级实证）；唯一受影响元素 = `REPORT_UI_LATENCY_STATS` uses-permission（AOSP 17 manifest 仅此一处 featureFlag）。Soong 侧该 flag 为 READ_WRITE（元素保留、平台运行时过滤）；剥除属性后 permission 无条件请求（signature 权限，无功能面影响）。字节保全于相邻 CONV_DEL 块（同 Task 072 package 属性机制） |

### 批次 1 修复清单（R1→R2）

| 修复 | 文件 | bp 依据 |
|---|---|---|
| `log/core/src` source root | SystemUI-common/build.gradle.kts | SystemUILogCoreLib（log/Android bp，17 新增；log/src import com.android.systemui.log.core.*） |
| view_capture + systemui-flags compileOnly | SystemUI-common/build.gradle.kts | SystemUI-shared-utils bp static_libs（WindowManagerUtils.kt 用） |
| `annotations/src` source root | SystemUI-plugin-core/build.gradle.kts | PluginAnnotationLib（17 新增 source root） |
| api(:SystemUI-common) | SystemUI-plugin-core/build.gradle.kts | PluginCoreLib bp static_libs SystemUILogCoreLib（PluginListener 签名引用 MessageBuffer → api） |
| implementation(:SystemUI-common) | SystemUI-shared-biometrics/build.gradle.kts | BiometricsSharedLib bp static_libs SystemUI-shared-utils |
| wmshell-shared AAR 并入 aidls javac jar（19 类：IShellTransitions/AnimatedSurface/IHome/IFocus/IOverviewOverlayLeash） | tools/package_aosp_aar.py + install 升 2.0.1 + catalog | 17 WindowManager-Shell-shared bp static_libs WindowManager-Shell-shared-aidls |

### 剩余阻塞（一项，需 chief/生成器 owner）

1. **SysUISdk 需重建（brief authority 字段明确的汇报项）**：SysUISdk android.jar 生成于 2026-08-21，
   早于 C2/C3 的 17 树再同步（2026-08-27，task071 冻结指纹已记录多处 byte drift）；当前树 framework.jar
   含而 android.jar 缺的 17 新隐藏 API（至少）：`android.window.RemoteTransition.setFilter(TransitionFilter)`
   （animation）、`android.os.UserManager.USER_TYPE_PROFILE_SUPERVISING`、
   `android.hardware.fingerprint.FingerprintSensorProperties.TYPE_STANDALONE`（biometrics）；
   另 ace AAR 类引用 `android.service.personalcontext.insight.ContextInsight`（android.jar 无，dex 期可能报缺）。
   **R8 新增同类证据（link 侧）**：`processDebugResources` 报 20 条 `resource android:color/… not found`
   （system_surface_effect_{0..3}×{light,dark,fallback} 12 条、system_error_dim 2、
   system_on_{primary,secondary}_fixed{,_variant} 6），全部为 17 framework 新增色板资源：
   AOSP 17 `framework-res.apk`（emu64x）全部存在（aapt2 dump 实证），legacy SysUISdk android.jar 全部缺失。
   修复 = `python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp` 重建（脚本本身禁改，运行属重建，
   按 brief authority 需 chief 批准）。**即：5 个 Kotlin 错误与 20 条 link 颜色错误同根因，均由同一重建解除。**

   **→ Chief 已批准（裁决 1），2026-08-29 执行，但生成器自身防护拦截（新红线，已停工上报）：**

   | 项 | 记录 |
   |---|---|
   | 重建前 android.jar sha256 | `652fd3d4a719724b89fe3c8c8122c4f021ec3692307e3130cf8850c89b157e8e`（framework.aidl `d0497fdc8…464962e`） |
   | 旧目录处置 | 无 `.sysuisdk-generated.json` marker（旧补丁流程产物）→ 生成器拒 `--replace`；按 ADR 0006 语义整体移开为 `platforms/android-SysUISdk.bak-legacy-pre-aosp17`，全新生成 |
   | 生成器结果 | **exit 1**：`bridge collision: target entry android/compat/annotation/UnsupportedAppUsage$Container.class differs from the approved source bytes` |
   | 根因（已实证） | 17 树 framework.jar（turbine-combined）新内嵌 `android/compat/annotation/UnsupportedAppUsage{,$Container}` 两类，其 turbine 字节与桥接专用源 `unsupportedappusage.jar`（javac 产物）不同；javap 比对两者 API 完全一致（`public interface …$Container extends java.lang.annotation.Annotation { public abstract …[] value(); }`），纯编译器产物字节差异。39 个桥接条目中其余 37 个均不在 framework.jar，仅此 2 条碰撞（碰撞检查首条即 abort） |
   | 为什么停 | 修复需改 `tools/build_sysuisdk.py`（本 brief 禁改文件）：三选一 ①从 `_UNSUPPORTED_APP_USAGE_ENTRIES` 桥接条目移除该 2 条（framework.jar 副本本就会被合入）②桥接优先覆盖（改 collision 语义）③重准 bytes。均属生成器 owner 决策 |
   | 环境恢复 | SDK 目录已原名恢复（sha256 复验一致），构建环境可用；遗留 `platforms/android-SysUISdk-staging/`（旧流程产物）未动 |

## 5. 验证记录

| 门 | 命令 | 结果 |
|---|---|---|
| 对齐 | `python3 tools/check_source_alignment.py --strict` | exit 0（MISSING/MISPLACED/EXTRA 全 0；MODIFIED 1 = 既有白名单；RES-MODIFIED 87 = task070 5806 处 + task073 config.xml 1 处，均见 §6） |
| pytest | `uv run pytest tools/tests -q` | 303 passed + 121 subtests（含 P0/P1/P2a 新增断言与批次 2 的 flags 转发/默认发现/来源门测试 20 项） |
| 冻结指纹 | `uv run python tools/package_misc_jars.py --verify-only` | 17/17 MATCH（含 mechanics×2） |
| 编译 | 见 §4 演变表；当前剩 1 类阻塞项（SysUISdk 重建，同时解锁 5 e: + 20 link 色） | — |

## 6. CONV 对账

| 文件 | 标记 | 授权 | 记录 |
|---|---|---|---|
| SystemUI-res/res-product/values/config.xml | CONV_DEL ×2 块（tablet/desktop 两行 `config_enableLargeScreenScreencapture`，保留 default） | 用户 2026-08-28（chief 转达），Task 073，commit `02e60a60` | reason: product-variant unsupported by AGP；机制同 task070 strings.xml |
| SystemUI-application/src/main/AndroidManifest.xml | CONV_DEL ×1 块（`REPORT_UI_LATENCY_STATS` 的 `android:featureFlag` 属性，元素保留） | File Map 授权区（`SystemUI-*/src`）；机制同 Task 072 package 属性先例 | reason: AGP 9.3.1 aapt2 link 无 feature-flags 通道（见 §4 批次 2）；字节保全可撤回 |

（另：task070 既有 5806 处 strings.xml 标记与 task072 manifest package 属性标记不属本任务，不重复对账）

## 7. 移交 task074 清单

（待补）
