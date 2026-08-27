# SystemUI-17 源码再对齐全景调研（Task 069，Phase C / C3 前置只读扫描）

- 日期：2026-08-27
- 性质：**只读调研**，未改动任何源码 / res / Gradle 配置，未运行 Gradle 构建
- 任务简报：`docs/orchestration/tasks/069-sysui17-source-realignment-panorama.md`
- 对照基准：AOSP `frameworks/base` @ `94b4c163b7`（tag `android-17.0.0_r1` 对应 checkout）
- 工具：`tools/check_source_alignment.py`（结构化数据经 `/tmp/task069/alignment.json` 提取，临时文件不入库）

---

## 0. TL;DR

1. **规模**：项目当前源码树与 AOSP 17 的漂移总量约 **5700 项**（源码 MISSING 1963 + EXTRA 642 + MODIFIED 2222 + MISPLACED 20；res MISSING 438 + EXTRA 219 + MODIFIED 830）。这是一次"整树重刷"级别的再对齐，不是补丁级。
2. **漂移性质**：MODIFIED 2222 个文件中抽样 150 个**全部**能在 AOSP git 历史中找到字节一致的版本（0 个疑似项目手改）——漂移主体是**陈旧拷贝**而非分叉，C3 可以安全地"整文件覆盖"。EXTRA 642 中有 131 个文件在 2025-03-26 声称的基线**之前**就已被 AOSP 删除，证明现有拷贝本身是多个 vintage 的拼盘。
3. **结构变化**：17 的 `Android.bp` 出现 6 个**新生产 source root**（`application/src`、`log/core/src`、`plugin_core/annotations/src`、`shared/flag/src`+`flag/types/src`、`customization/clocks/common/src`），pods 由 5 个 bp 重构为 35+ 个 bp 的 `src/{api,main,dagger,test}` 布局。当前 Gradle 拓扑的映射表**不覆盖**这些新根（约 40 个生产文件在现有对齐工具视野之外）。
4. **CONV 标记**：2239 个 CONV 标记**全部属于 class B**（AOSP 17 未吸收 product 变体，甚至新增了 `product="desktop"`），C3 拷贝后需要**整批重标**，不能沿用。
5. **七个决策点**需要用户拍板后才能开 C3（见 §5）：application/src 归属、clocks/common 是否独立模块、pods 测试目录排除、SurfaceEffects 三库 AAR、AccessibilityFloatingMenu-res AAR、AAPT2 flag 限定目录、res-product 新语法变体。

### 基线对账表（与 chief 下发的 baseline 逐项一致）

| 计数器 | baseline | 本次提取 | 一致 |
|---|---|---|---|
| MISSING | 1963 | 1963 | ✅ |
| MISPLACED | 20 | 20 | ✅ |
| EXTRA | 642 | 642 | ✅ |
| MODIFIED | 2222 | 2222 | ✅ |
| APP | 0 | 0 | ✅ |
| RES-MISS | 438 | 438 | ✅ |
| RES-EXTRA | 219 | 219 | ✅ |
| RES-MODIFIED | 830 | 830 | ✅ |

---

## 1. S1 — 源码漂移普查

### 1.1 MISSING（1963）按模块 / AOSP source root

| AOSP root | 现映射 Gradle 模块 | 缺失数 | 备注 |
|---|---|---:|---|
| `src` | :SystemUI-core/src | 1464 | 主体；其中 587 个位于 17 **全新目录** |
| `pods` | :SystemUI-core/pods | 269 | ⚠️ 含 50 个 test/testFixtures 文件（见 §2.3） |
| `compose/features/src` | :SystemUI-core/compose/features/src | 102 | scene/ui 29、keyguard/ui 25、ambientcue/ui 14 等 |
| `plugin/src` | :SystemUI-plugin/src | 30 | |
| `compose/core/src` | :SystemUI-compose/core/src | 23 | |
| `shared/src` | :SystemUI-shared/src | 21 | 含 1 个 aidl |
| `compose/scene/src` | :SystemUI-compose/scene/src | 16 | |
| `customization/src` | :SystemUI-customization/src | 11 | 10 个为 clocks 迁出文件（见 §2.2） |
| `animation/src` | :SystemUI-animation/src | 10 | |
| `plugin_core/src` | :SystemUI-plugin-core/src | 5 | |
| `compose/facade/enabled/src` | :SystemUI-core | 3 | |
| `shared/biometrics/src` | :SystemUI-shared-biometrics/src | 3 | |
| `utils/src` | :SystemUI-common | 3 | |
| `log/src` | :SystemUI-common | 1 | |
| `plugin_core/processor/src` | :SystemUI-plugin-processor | 1 | |
| `unfold/src` | :SystemUI-unfold | 1 | |
| **合计** | | **1963** | |

**未计入 1963 的视野外新根**（当前工具映射不覆盖，C3 需先扩映射）：`application/src` 4、`log/core/src` 4、`plugin_core/annotations/src` 6、`shared/flag/src` 4、`shared/flag/types/src` 1、`customization/clocks/common/src` 21 → 合计 **40 个生产文件**。

**src/ 缺失按包分布（top）**：statusbar 369、screencapture 160（全新子系统）、qs 144、keyguard 60、media 54。`screencapture/`、`quickactions/av`、`lowlight/`、`decor/dagger`、`flashlight` 等 17 个新目录贡献 587 个缺失文件——这部分是**新功能代码**，不是漂移遗漏。

**非 kt/java 缺失清单（6 个，C3 必须逐一核对 aidl/proto 管线）**：

| 文件 | root |
|---|---|
| `src/com/android/systemui/mediaprojection/MediaProjectionCaptureTarget.aidl` | src |
| `src/com/android/systemui/screenrecord/service/IScreenRecordingService.aidl` | src |
| `src/com/android/systemui/screenrecord/service/IScreenRecordingServiceCallback.aidl` | src |
| `src/com/android/systemui/screenrecord/shared/model/ScreenRecordingParameters.aidl` | src |
| `src/com/android/systemui/shared/recents/ILauncherProxy.aidl` | shared/src |
| `src/com/android/systemui/motioncues/proto/motion_cues.proto` | src（唯一 proto） |

### 1.2 EXTRA（642）三分类归因

对每个 EXTRA 文件在 AOSP git 历史（`git log --diff-filter=D` / `ls-tree`）中回溯，得到三类：

| 类 | 数量 | 含义 | C3 处置 |
|---|---:|---|---|
| ① 旧基线存在、17 已删除 | 441 | 真正的 17 删码（重构、功能下线） | 直接删除 |
| ② basename 在 17 仍存在于**别的路径** | 70 | AOSP 17 内部搬移（QS tiles → pods、`qs/tiles/base/domain` → `interactor` 等）；项目文件在旧路径、17 在新路径 | 删旧路径 + 拷新路径（等效 move+overwrite） |
| ③ 在 2025-03-26 旧基线**之前**就已被 AOSP 删除 | 131 | 现有拷贝比声称的基线更老——拼盘证据（KeyguardStatusView.java 2024-12-19 删、AuthDialog.java 2025-01-30 删，项目却于 2026-07-18 加入） | 直接删除 |

441 + 70 + 131 = 642 ✅。**结论：EXTRA 无一例外都应删除**，不存在需要保留的项目自有文件。

### 1.3 MODIFIED（2222）vintage 分析

- 665 个文件字节等于旧基线 `f0354eeb`（2025-03-26）版本 → 纯 17 漂移，覆盖即可。
- 1557 个文件匹配**更早**的 AOSP vintage（CarrierText.java = 2023-08-23 版，EmergencyButton.java = 2024-11-15 版）。
- 随机抽样 150 个 MODIFIED 文件，逐 commit 比对字节：**150/150 全部**能找到字节一致的 AOSP 提交，0 个无匹配 → **没有证据表明存在项目手改的源文件**（唯一的已知手改是 CONV 标记文件，见 §3）。
- 抽样 vintage 直方图峰值在 2024-08 ～ 2024-12（79/150），最老 2020-10。**C3 对 MODIFIED 可以无脑整文件覆盖**，覆盖后 MODIFIED 归零是可验证的验收标准。

### 1.4 MISPLACED（20）

| 方向 | 数量 | 明细 |
|---|---:|---|
| :SystemUI-core/src → :SystemUI-shared/src | 16 | 11 个 `dagger/qualifiers/*`（BroadcastRunning、Default、DisplayId、InstrumentationTest、LongRunning、NotifInflation、PerUser、RootView、SystemUser、TestHarness 等）+ 5 个 `log/table/*`（LogBufferFactory、Diffable、TableLogBuffer、TableLogBufferFactory、TableRowLogger） |
| :SystemUI-core/pods → :SystemUI-shared/src | 3 | SysUISingleton.java、dagger/qualifiers/Application.java、Background.java |
| :SystemUI-core/src → :SystemUI-common (log/src) | 1 | Dumpable.java |
| :SystemUI-compose/scene → :SystemUI-compose/core | 1 | SpaceVectorConverter.kt |

C3 处置：按 AOSP 17 位置 `git mv` 到目标模块（这些是 AOSP 17 的真实搬移，项目停在了旧位置）。

### 1.5 res 漂移（MISSING 438 / EXTRA 219 / MODIFIED 830）

**MISSING 438**：
- `SystemUI-res/res/` 342：drawable 225、layout 41、**`flag(com.android.systemui.status_icons_in_compose_refresh)/` AAPT2 flag 限定目录 15 个**、color 8、raw 8、anim 7、animator 4、xml 4、values* 29（含 de/es/es-rUS/fr-rCA/it 各 feminine/masculine/neuter 三件套）、menu 1、drawable-nodpi 1
- `SystemUI-shared-biometrics/res/` 84：全部是逐 locale 的 `values-*/strings.xml`（17 给 biometrics 补齐了全语种翻译）
- `SystemUI-res/res-keyguard/` 7：drawable 6 + layout 1
- `SystemUI-res/res-product/` 4：`values/config.xml` 1 + `values-fr-rCA-{feminine,masculine,neuter}` 3（**新语法变体**，AAPT2 支持性待验证）
- `SystemUI-customization/res/` 1：drawable 1

**EXTRA 219**：`SystemUI-res/res/` 190（drawable 45 + layout 42 + color 7 + xml 5 + 其它限定符目录约 52 + `values-*/strings.xml` 逐 locale 84——17 把 res 主干翻译文件删除/迁移，与 biometrics 的 84 个新增 locale 文件对称，疑似翻译归属搬家，**C3 执行时需抽查 1-2 个 locale 确认**）、`res-keyguard/` 16（drawable 10 + layout 6）、`customization/res/` 13。190+16+13=219 ✅

**MODIFIED 830**：`res/` 636（drawable 146、layout 111、raw 49、color 26、其余 values*/xml/限定符）、`res-keyguard/` 104、**`res-product/` 86**（正是携带 2237 个 CONV_DEL 标记的 86 个 strings.xml，见 §3——MODIFIED 主体就是 CONV 标记造成的 diff，C3 重标后此项应大幅归零）、`SystemUI-shared/res/` 3、`SystemUI-animation/res/` 1。636+104+86+3+1=830 ✅

### 1.6 app 级文件

- `AndroidManifest.xml`：AOSP 17 为 **1338 行**，项目现 1157 行；缺 `INTERNET`、`WARM_UP_CAMERA`、`READ_PROJECTION_STATE` 等新权限及新组件/feature 声明。C3 需整文件替换（规则 B：`:app` manifest 从 AOSP 完整复制，不允许最小化）。
- `proguard.flags`、`proguard_kotlin.flags`：与 17 **字节一致**，不动。
- `proguard_common.flags`：项目 50 行 vs AOSP 17 的 72 行，需更新。

---

## 2. S2 — Android.bp 语义 diff 与拓扑建议

对照旧基线 `f0354eeb`（2025-03-26）与 17 HEAD `94b4c163b7` 的 `packages/SystemUI/Android.bp` 及子目录 bp。

### 2.1 生产图内结构变化

| 变化 | 内容 | 对现拓扑的影响 |
|---|---|---|
| **新增** `android_library "SystemUI-application"` | `application/src` 4 文件（PhoneSystemUIAppComponentFactory、SystemUIInitializerImpl、ReferenceSysUIComponent、ReferenceGlobalRootComponent），**拥有 AndroidManifest.xml**；`android_app "SystemUI"` 改为依赖它而非直接依赖 SystemUI-core | 新 source root + manifest 归属变化；映射方案见 §5 决策 1 |
| **pods 重构** | 旧 5 个 bp → 35+ 个 bp，统一 `src/{api,main,dagger,test}` 布局；新增 `pods/bundle/phone/Android.bp` 聚合 `com.android.systemui.bundle.phone_dagger` + `phone_api`；`pods/src/api/CoreStartable.kt` 属 `com.android.systemui-api`（生产） | `:SystemUI-core/pods` 映射需细化到**排除 test 目录**（见 2.3） |
| **新增** `SystemUILogCoreLib`（`log/core/src`，4 文件） | log 拆出 core 子库 | 建议 → `:SystemUI-common`（与 log/src 同宿主） |
| **新增** `PluginAnnotationLib`（`plugin_core/annotations/src`，6 文件） | 注解独立成库 | 建议 → `:SystemUI-plugin-core` |
| **flags 迁出 shared** | `shared/flag/src`（4）+ `shared/flag/types/src`（1）从 `shared/src` 移出 | 建议 → `:SystemUI-shared`（同 namespace，无需新模块） |
| **新增** `SystemUIClocks-CommonLib`（`customization/clocks/common`，21 src + 自有 res + manifest） | 7 个 clock 文件从 `customization/src` 迁出；sample clock app 为独立 bp（非生产图） | 自有 res/R namespace → 建议独立模块；见 §5 决策 2 |
| **`SystemUIShaderLib` 移除** | surfaceeffects 回归 `frameworks/libs/systemui/surfaceeffects/`：`SurfaceEffectsCoreLib` / `SurfaceEffectsViewLib` / `SurfaceEffectsComposeLib` 三库 28 个 kt，**无 res**；PlatformAnimationLib 依赖 ViewLib，SystemUI-core 依赖 ComposeLib | 项目 `:SystemUI-animation` 里 24 个 EXTRA surfaceeffects 文件即为此迁出；需按 animationlib 家族管线打 AAR（§5 决策 4） |
| `PluginProtectorStub.kt` → `PluginProtector.kt` 重命名 | 仍标记 exclude，非生产 | 无动作，仅记录 |
| **SystemUI-res static_libs 新增** | WindowManager-Shell、dynamiccolors、**AccessibilityFloatingMenu-res**、android.net.platform.flags-aconfig、uilatencystats_flags | 前 4 个需在 Gradle 侧补依赖；AccessibilityFloatingMenu-res 的 res 位于 `accessibility/accessibilitymenu/`（**虽 app 代码在独立 app、不在生产图，但其 res 经该 AAR 进入 SystemUI 生产资源闭包**，必须引入 AAR；见 §5 决策 5） |

### 2.2 17 源码生产图全量盘点（6133 个源文件）

按 17 bp 逐 root 统计生产文件数（排除 tests/multivalentTests）：

| AOSP root | 生产文件数 | 建议归属 |
|---|---:|---|
| `src` + `src-debug` + `src-release` | 5192+4+4 | :SystemUI-core |
| `compose/features/src` | 200 | :SystemUI-core |
| `compose/facade/enabled/src` | 11 | :SystemUI-core |
| `application/src` | 4 | 决策 1（:SystemUI-application 或并入 core） |
| `pods`（排除 test） | 219 | :SystemUI-core/pods |
| `common/src` + `log/src` + `log/core/src` + `utils/src` | 2+7+4+5 | :SystemUI-common |
| `animation/src` | 40 | :SystemUI-animation |
| `plugin_core/src` + `plugin_core/annotations/src` | 7+6 | :SystemUI-plugin-core |
| `plugin_core/processor/src` | 3 | :SystemUI-plugin-processor |
| `plugin/src` + `plugin/bcsmartspace/src` | 59+2 | :SystemUI-plugin |
| `unfold/src` | 38 | :SystemUI-unfold |
| `customization/src` | 24 | :SystemUI-customization |
| `customization/clocks/common/src` | 21 | 决策 2（建议新模块） |
| `shared/src` + `shared/keyguard/src` + `shared/flag/*` | 105+2+5 | :SystemUI-shared |
| `shared/biometrics/src` | 14 | :SystemUI-shared-biometrics |
| `compose/core/src` + `compose/scene/src` | 48+57 | :SystemUI-compose |
| **合计** | **6133** | |

### 2.3 pods 测试文件污染（重要）

pods 目录 269 个文件中，**50 个**属 `src/test/`、`src/testFixtures/`、`multivalentTests/`——不在生产图。当前对齐工具把 `pods` 整目录映射进 `:SystemUI-core/pods`，导致：
1. MISSING 269 虚高（真实生产缺失 219）；
2. 若 C3 照单全收，会把 50 个测试文件拷进生产源码树，违反规则 B。

**建议**：C3 前先更新 `tools/check_source_alignment.py` 的 pods 映射为排除 test 目录的 glob，此后 baseline 中 pods MISSING 应重算为 219。

### 2.4 生产图之外（建议排除、不拷贝）

`metrics/`（perfetto textproto filegroup）、`compose/scene/debugger`（独立 debug app）、`checks/`（lint）、`aconfig/`、`schemas/`、`docs/`、`scripts/`、`tests/`、`multivalentTests*`、clocks sample app、accessibilitymenu **app 代码**（但其 res 经 AAR 进入生产闭包，见 §2.1）。


---

## 3. S3 — CONV 标记存量盘点

| 标记 | 数量 | 位置 | 分类 |
|---|---:|---|---|
| CONV_DEL | 2237 | `SystemUI-res/res-product/values*/strings.xml` 86 个文件（product="tv"/"tablet" 变体） | **全部 class B** |
| CONV_MOD | 2 | `SystemUI-shared/src/.../UncaughtExceptionPreHandlerManager.kt`（hidden-API 反射 workaround） | class B（17 未吸收） |
| CONV_ADD | 0 | — | — |

- **class A（上游已吸收，标记可摘）＝ 0**；**class C（17 出现新变体待评估）＝ 0**。
- 17 的 res-product **仍有** `product="tv"/"tablet"` 属性（未吸收），且**新增 `product="desktop"`**——class B 判定成立，2237 个标记**不能直接摘除**。
- C3 拷贝会覆盖 86 个 res-product strings.xml → **2237 个 CONV_DEL 标记将全部失效，必须按 ADR 0004 规范对新内容整批重标**（tv/tablet/desktop 三种 product 属性逐条 `CONV_DEL BEGIN/END`）。重标工作量 ≈ 86 文件 × 平均 26 条。
- `UncaughtExceptionPreHandlerManager.kt` 的 2 个 CONV_MOD：17 版本若仍未提供等价 public API，则拷贝后**需重放同样 workaround 并保留标记**；若 17 已吸收则直接用 17 版本。执行时逐条判断。

---

## 4. S4 — C3 批量执行计划（估算，供派单参考）

### 4.1 源码操作矩阵（按 Gradle 模块）

| 模块 | 拷入（MISSING） | 覆写（MODIFIED） | 删除（EXTRA） | 移动（MISPLACED） | 备注 |
|---|---:|---:|---:|---|---|
| :SystemUI-core | 1464(src) + 102(features) + 3(facade) + **219(pods 排 test)** = 1788 | 2091 | 531 | 移出 19（→shared 16+3） | ①70 个 EXTRA 类② 同步删旧路径 |
| :SystemUI-common | 1(log) + 4(log/core 新根) + 3(utils) = 8 | 5 | 6 | 移入 1（Dumpable） | log/core/src 为新根 |
| :SystemUI-animation | 10 | 13 | 24 | — | 24 个 EXTRA = surfaceeffects 迁出至 frameworks/libs |
| :SystemUI-plugin | 30 | 14 | 21 | — | |
| :SystemUI-plugin-core | 5 + 6(annotations 新根) = 11 | 2 | 11 | — | |
| :SystemUI-plugin-processor | 1 | 2 | 0 | — | |
| :SystemUI-compose | 23(core) + 16(scene) = 39 | 47 | 11 | 内部移动 1（SpaceVectorConverter scene→core） | |
| :SystemUI-customization | 11 + 21(clocks/common，决策 2) = 32 | 9 | 22 | — | clocks 21 文件落点待决策 |
| :SystemUI-shared | 21 + 5(flag 新根) = 26 | 29 | 15 | 移入 19 | |
| :SystemUI-shared-biometrics | 3 | 4 | 0 | — | 另有 84 个 locale res 拷入 |
| :SystemUI-unfold | 1 | 6 | 1 | — | |
| :SystemUI-application（新？） | 4（application/src 新根，决策 1） | — | — | — | 含 manifest 归属问题 |
| **合计** | **≈1953**（1963 − 50 pods test）+ 40 新根文件 | 2222 | 642 | 20 | |

**操作安全性依据**：MODIFIED 抽样 150/150 字节匹配 AOSP 历史、EXTRA 642 全部三类归因成立、CONV_ADD 为 0 → C3 可以按"先删 EXTRA → 移 MISPLACED → 拷 MISSING → 覆 MODIFIED → 重放 CONV"顺序机械执行，无需逐文件人工三审（例外见 §4.4 白名单）。

### 4.2 res 操作矩阵

| 资源根 | 拷入 | 覆写 | 删除 |
|---|---:|---:|---:|
| SystemUI-res/res | 342（含 15 个 flag() 限定目录，决策 6） | 636 | 190（含 84 locale，删前抽查） |
| SystemUI-res/res-keyguard | 7 | 104 | 16 |
| SystemUI-res/res-product | 4（含 3 个 fr-rCA 语法变体，决策 7） | 86（= CONV 重标文件） | 0 |
| SystemUI-shared-biometrics/res | 84 | 0 | 0 |
| SystemUI-customization/res | 1 | 0 | 13 |
| SystemUI-animation/res | 0 | 1 | 0 |
| SystemUI-shared/res | 0 | 3 | 0 |
| **合计** | **438** | **830** | **219** |

### 4.3 app 级与杂项

1. `:app` manifest 整文件替换（1157 → 1338 行）。
2. `proguard_common.flags` 更新（50 → 72 行）；另两个 proguard 文件不动。
3. 5 个 AIDL + 1 个 proto 拷入后，核对 Gradle AIDL/proto sourceSet 管线能消费。
4. SystemUI-res 新增 static_libs 依赖（WindowManager-Shell 已有坐标；dynamiccolors、AccessibilityFloatingMenu-res、android.net.platform.flags-aconfig、uilatencystats_flags 需补 AAR/jar，走 `tools/package_aosp_aar.py` 管线）。
5. SurfaceEffects 三库（Core/View/Compose）AAR 化并接入 :SystemUI-animation / :SystemUI-core。
6. 重跑 `tools/check_source_alignment.py`：预期 src MISSING/MISPLACED/EXTRA/MODIFIED 全 0（映射扩到新根后）；res 同理（flag() 目录与 product 变体除外，以 CONV/决策结果为准）。

### 4.4 执行白名单（不可机械覆盖的文件）

- `UncaughtExceptionPreHandlerManager.kt`（CONV_MOD × 2，逐条判断后重放）
- 86 个 res-product strings.xml（CONV 重标，非单纯覆盖）
- `flag(...)` 目录 15 个文件与 3 个 fr-rCA 语法变体（先验证 AAPT2 消费能力）

---

## 5. 用户决策点（C3 开工前置，规则 H）

| # | 决策 | 选项 | 建议 |
|---|---|---|---|
| 1 | `application/src` 4 文件归属 | (a) 新模块 `:SystemUI-application`（严格 bp 对齐，manifest 随之）/ (b) 并入 `:SystemUI-core`，manifest 留 `:app` | (a)，ADR 0003 精神：它拥有独立 manifest 与 AppComponentFactory 角色 |
| 2 | `customization/clocks/common`（21 src + res + manifest） | (a) 新模块 `:SystemUI-clocks-common` / (b) 并入 `:SystemUI-customization` | (a)，自有 R namespace 是真实 seam（ADR 0003 判据） |
| 3 | pods 50 个 test 文件 | 排除出生产拷贝 + 更新对齐工具映射 | 排除（生产图外） |
| 4 | SurfaceEffects 三库 | 经 `tools/package_aosp_aar.py` 打 AAR（无 res，纯 jar 亦可） | 走既有 animationlib 家族管线，AAR |
| 5 | AccessibilityFloatingMenu-res | 打 AAR 引入（res 在生产闭包） | 必须引入；app 代码本身不拷 |
| 6 | `res/flag(...)/` 15 个文件 | (a) 直接拷入验证 AGP/AAPT2 是否支持 flag 限定目录 / (b) 不支持时走 CONV 标记 | 先 (a) 试，失败再 (b) 并回报 |
| 7 | res-product fr-rCA-feminine 等 3 个新语法变体 + `product="desktop"` | 与 CONV 重标一并处理 | 随 §3 批次重标 |

---

## 6. 复现方法

```bash
# 全量对齐计数
uv run tools/check_source_alignment.py          # （以 tools 内实际入口/参数为准）

# 结构化提取（本次用的临时脚本，不入库）
# /tmp/task069/extract.py  -> alignment.json
# AOSP git 回溯：git -C /home/conv/myspace/aosp/frameworks/base log --diff-filter=D -- <path>
# vintage 比对：git show <commit>:<path> 与项目文件逐字节比较
```

