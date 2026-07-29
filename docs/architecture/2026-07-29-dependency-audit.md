# 依赖合规性全面审查 (2026-07-29)

> 目标：按三层规则（源码 / jar-aar / maven）审查项目**所有**依赖，标出不合规项，
> 给出正确做法与迁移顺序，并列出**技术困难**供共同决策。参照 `CarSystemUIGradle`。

三层规则回顾（详见 `2026-07-29-systemui-module-source-vs-jar.md`）：
- **① SystemUI 自有代码**（soong 模块在 `packages/SystemUI/**/Android.bp`）→ **源码依赖**
- **② AOSP 特有产物**（公网 maven 没有 / 被 fork / aconfig 生成）→ **jar / aar**
- **③ 标准第三方**（公网 maven 有）→ **正常 maven 版本依赖**

参照项目印证：`CarSystemUIGradle` 的 `:SystemUI-shared/-animation/-core` 等
**全部 `java.srcDirs("src")` 源码方式**，SystemUI 自有子模块无一用 jar。

---

## 一、总体结论

| 项 | 数量 | 说明 |
|---|---|---|
| ✅ 合规 | 多数 tier②③ | framework/monet/flags/androidx/compose/room… 引入方式正确 |
| ❌ tier① 违规（应源码却用 jar/aar） | **5 处** | shared、animation、customization、log、unfold |
| ❌ tier③ 违规（应 maven 却用 jar） | **2 处** | lottie.jar、lottie_compose.jar（且与 maven 重复） |
| 🧹 重复引入 | **2 组** | SystemUISharedLib×3、SettingsLib×3 |
| 🗑️ 死依赖 | **6+** | SystemUIPluginLib.jar、car-*.aar、android-merged 等 |
| ⚠️ 技术困难 | **5 项** | 见第四节 |

---

## 二、逐项分类清单

### 2.1 ❌ tier① 违规：SystemUI 自有代码被当 jar/aar（应改源码）

| Gradle 模块 / 依赖 | 当前引入 | 正确做法 | AOSP 源码 | 参照项目 |
|---|---|---|---|---|
| `:SystemUI-shared` | `prebuilts/SystemUISharedLib.jar` | 源码 `shared/src` + `aidl.srcDirs` | 75 文件 | ✔ 源码 |
| `:SystemUI-animation` | `prebuilts/PlatformAnimationLib.jar` | 源码 `animation/src`+`animation/lib/src`+`res` | 54+7 | ✔ 源码 |
| `:SystemUI-customization` | `prebuilts/SystemUICustomizationLib.jar` (api) | 源码 `customization/src` | 35 | (ref 无此模块) |
| `SystemUI-log.jar` (core api) | jar | 源码，抽 `:SystemUI-log` 模块 | `log/src` 10 | — |
| `SystemUI-unfold.jar` (core) | jar | 源码 `unfold/src` | 36 | — |
| `common/src`（跨模块用） | 现并入 core | 抽 `:SystemUI-common` 模块 | 3 | — |

补充（已在 core 源码，属 tier① 正确，仅记录）：`compose/core/src`(27)、`kairos`(42, 已 opt-in)、
`shared/keyguard`、`shared/biometrics`、clocks 插件(15, 刚迁 :SystemUI-plugin)。
仍缺源码待补：`shared-utils utils/src`(2)、`compose/scene/src`(50, 见困难③)。

### 2.2 ❌ tier③ 违规：标准第三方被当 jar（应 maven）

| 依赖 | 当前 | 正确做法 |
|---|---|---|
| `lottie.jar` (core compileOnly) | jar **且与 `libs.lottie` maven 重复** | 删 jar，保留 `implementation(libs.lottie)` |
| `lottie_compose.jar` (core compileOnly) | jar | 删 jar，加 maven `com.airbnb.android:lottie-compose` |

### 2.3 🧹 重复引入（同一物多种形态，需合一）

- **SystemUISharedLib ×3**：`prebuilts/SystemUISharedLib.jar`（:SystemUI-shared）
  + `libs.systemui.sharedlib` maven-aar（core compileOnly）
  + `libs/maven/.../SystemUISharedLib-1.0.0.aar`。→ 改源码后**三者全删**。
- **SettingsLib**：`libs.systemui.settingslib` maven-aar（**只含 res**）+ `SettingsLib-full.jar`(413)
  + `SettingsLib-javac.jar`(645, code)。→ **经核实非冗余**：aar 供资源、jar 供代码，是合理的
  res/code 拆分，tier② 合规，**保留**。（原审查误判为三重冗余，已更正）

### 2.4 🗑️ 死依赖（无任何 build.gradle 引用，可删）

`prebuilts/SystemUIPluginLib.jar`（plugin 已源码）、`libs/maven/car-*.aar`、`CarNotificationLib`
（CarSystemUI 遗留）、`android-merged.jar`、`aconfig-annotations-lib.jar`、
`app-compat-annotations.jar`、`compat-annotations.jar`、`car-admin-ui-lib.jar`。

### 2.5 ✅ tier② 合规（AOSP 特有产物，jar/aar 正确）

framework.jar、framework-statsd.jar、android.car.jar、WindowManager-Shell.jar、
android_module_lib_stubs_current.jar（framework stub）；monet.jar（libmonet）；
systemui-flags / settingslib-flags / notification-flags / flags（aconfig 生成）；
iconloader / wmshell / wifitrackerlib（maven-aar，源在 `frameworks/libs/systemui`）；
motion_tool_lib、TraceurCommon、traceur-res-R；
**tracinglib-platform.jar**（源在 `frameworks/libs/systemui/tracinglib`，**非** packages/SystemUI → tier② ✔）；
SystemUI-tags / -statsd / -proto / -proto-gen（**logtags/proto/statsd 生成代码** → jar 合理，非手写源码）。

### 2.6 ✅ tier③ 合规（maven 版本依赖，正确）

androidx.*（core-ktx/appcompat/recyclerview/room/datastore/media3/lifecycle/
constraintlayout/compose.*）、kotlinx_coroutines、dagger、guava、
com.google.android.material、androidx.window、lottie(maven)。

---

## 三、迁移方案（按依赖图顺序，遵守规则 I 增量）

**Phase A — 清理（零风险，错误数不变）**
1. 删死依赖（2.4）。
2. tier③：删 lottie.jar/lottie_compose.jar，补 lottie-compose maven（2.2）。
3. 合并重复 SettingsLib（保留 maven-aar，删两 jar）（2.3）。

**Phase B — 抽公共源码模块（打通跨模块源码依赖）**
4. 新增 `:SystemUI-common`（common/src 3）。
5. 新增 `:SystemUI-log`（log/src 10）；删 SystemUI-log.jar；
   plugin 的 MessageBuffer 由 `compileOnly(shared.jar)` 改 `project(":SystemUI-log")`。

**Phase C — jar→源码 迁移（大改，逐模块，错误会飙升，已获授权）**
6. `:SystemUI-shared`：删 jar → `shared/src`+aidl 源码；同步删 SystemUISharedLib ×3。
7. `:SystemUI-animation`：删 jar → `animation/src`+`lib/src`+res 源码。
8. `:SystemUI-customization`：删 jar → `customization/src` 源码。
9. `:SystemUI-unfold`（或并入 core）：删 SystemUI-unfold.jar → `unfold/src` 源码。

**Phase D — Compose / AIDL（含技术困难）**
10. `compose/scene/src` 源码 + 补 Compose 依赖（困难③）。
11. AIDL 方案决策（困难②）。

---

## 四、技术困难（需共同决策）

**困难① 跨模块自有代码（log / common）必须独立成 module**
log、common 被 core、plugin、shared、animation 多方引用。现 log/common 源码在 core 内，
plugin 无法反向依赖 core（已遇 `MessageBuffer` 问题，临时用 `compileOnly(shared.jar)` 绕过）。
正解 = 抽 `:SystemUI-log`、`:SystemUI-common` 独立源码模块。
→ **请确认**是否新增这两个模块。

**困难② AIDL 无法从源码编译（systemui-aidl.jar）**
14 个 `.aidl` 引用 framework 隐藏 AIDL 接口（`IRemoteCallback`、`IAppWidgetHostListener` 等），
SysUISdk 的 `framework.aidl` 缺这些 → AGP aidl 编译器解析失败，现用预编译 systemui-aidl.jar 兜底。
这是 tier① 代码但**当前无法源码编译**。选项：
(a) 保留 jar 作**有文档说明的 tier② 例外**（推荐，先跑通）；
(b) 补全 framework.aidl 的隐藏接口 .aidl 后再源码编译；
(c) 复制所需 framework .aidl 到项目。
→ **倾向 (a)**，请确认。

**困难③ compose/scene(50) 依赖 Compose 内部/实验 API**
`thenIf`、`drawInContainer` 等非公开 API，源码化需对齐 Compose 版本或补依赖，会引入一批错误。
→ 建议放 Phase D，单独处理。

**困难④ shared/animation/customization jar→源码 是大迁移**
各自有独立依赖链，去 jar 会触发大量 duplicate-class 与 unresolved，错误数将明显上升
（用户已授权源码补全可升错误）。需按依赖图顺序、逐模块提交。
→ 确认按 Phase C 顺序推进。

**困难⑤ KAPT/Dagger 注解处理已禁用**
KAPT 与 Gradle 9.5 不兼容（IR 内部错误），Dagger 注解处理关闭。当前 116 错误里
Dagger 生成符号（`Dagger*`/`*_Factory`）仅 2 个，暂不阻塞；但**最终可运行**需迁 KSP。
→ 非本次 tier 审查范围，记录待办。

---

## 五、待办跟踪

- [ ] Phase A 清理（死依赖 + lottie + SettingsLib 合并）
- [ ] Phase B `:SystemUI-common`、`:SystemUI-log` 模块
- [ ] Phase C shared / animation / customization / unfold 源码化
- [ ] Phase D compose/scene + AIDL 决策
- [ ] （另议）Dagger KAPT→KSP
