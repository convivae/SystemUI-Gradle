# SystemUI 依赖策略：自有代码用源码，外部依赖用 jar/aar/maven (2026-07-29)

> **用户明确原则 (2026-07-29)**：AOSP `packages/SystemUI/` 下 **SystemUI 自有的代码**
> 一律**源码复制**过来做**源码依赖**，不用 jar；**SystemUI 之外的模块**尽量用
> jar / maven 的 aar 依赖。判定依据 = 看 AOSP 的 `Android.bp`。

## 一、判定标准（三层，2026-07-29 用户细化）

依赖分三层，按来源决定引入方式：

| 层 | 是什么 | 引入方式 | 例子 |
|---|---|---|---|
| ① SystemUI 自有代码 | soong 模块定义在 `packages/SystemUI/**/Android.bp` 内 | **源码复制**（source module） | shared、animation、customization、log、common、unfold、kairos、compose/core、compose/scene、plugin |
| ② AOSP 特有产物 | 公网 Maven 上没有 / 被 AOSP fork / aconfig 生成 | **jar / aar**（AOSP 编译产物提取） | framework.jar、android.car.jar、SettingsLib、WindowManager-Shell、WifiTrackerLib、monet/libmonet、iconloader、systemui/notification/settingslib flags |
| ③ 标准第三方上游库 | 公网 Maven 直接有的通用库 | **正常 Gradle Maven 版本依赖**（像普通 app，**不要** jar/aar） | androidx.*、kotlinx_coroutines、dagger2、com.google.android.material、lottie、jsr305/jsr330 |

判定流程：
1. soong 模块在 `frameworks/base/packages/SystemUI/**/Android.bp` 内？→ 是 → **①源码**
2. 否则，公网 Maven 找得到且未被 AOSP 改过？→ 是 → **③Maven 版本依赖**
3. 否则（AOSP 特有 / fork / 生成物）→ **②jar/aar**

## 二、`SystemUI-core` soong 模块真相 (Android.bp:424)

`SystemUI-core` 这个 `android_library` **只把下列目录当 srcs 编译**：
```
src/**/*.{kt,java,aidl}
:ReleaseJavaFiles / :DebugJavaFiles   (product_variables 切换 src-release/src-debug)
compose/features/src/**/*.kt
compose/facade/enabled/src/**/*.kt
```
**其余所有 SystemUI 自有代码都是独立的 `static_libs`**（独立编译单元再链接），
不属于 core 的 srcs。也就是说 **core 模块本身不含 shared/animation/log/… 的源码**。

## 三、SystemUI 自有子模块清单（应做成源码 Gradle module）

| soong 模块名 | AOSP 目录 | 当前本项目做法 | 目标 |
|---|---|---|---|
| SystemUISharedLib | `shared/src` | jar (prebuilts/SystemUISharedLib.jar) | **源码** :SystemUI-shared |
| SystemUISharedLib-Keyguard | `shared/keyguard/src` | 已并入 core/src | 源码（已在 core） |
| BiometricsSharedLib | `shared/biometrics/src` | 已并入 core/src | 源码（已在 core） |
| SystemUI-shared-utils | `utils/src` | 缺 | **源码** |
| kairos | `utils/kairos/src` | 刚复制进 core（+779 opt-in 错误） | **源码**（需 opt-in flag） |
| PlatformAnimationLib | `animation/src` | jar (prebuilts/PlatformAnimationLib.jar) | **源码** :SystemUI-animation |
| PlatformAnimationLib-core/server | `animation/lib/src` | 缺 | 源码 |
| SystemUICustomizationLib | `customization/src` | jar (prebuilts/SystemUICustomizationLib.jar) | **源码** :SystemUI-customization |
| SystemUILogLib | `log/src` | 刚复制进 core | **源码** |
| SystemUICommon | `common/src` | 刚复制进 core | **源码** |
| PlatformComposeCore | `compose/core/src` | 已在 core/src (compose/*) | 源码（已在 core） |
| PlatformComposeSceneTransitionLayout | `compose/scene/src` | 部分在 core | 源码 |
| SystemUIUnfoldLib | `unfold/src` | jar (我加的 SystemUIUnfoldLib jar) | **源码** |
| SystemUIPluginLib | `plugin/src` + `bcsmartspace/src` | 源码 :SystemUI-plugin (65 文件) | 源码 ✓ |
| PluginCoreLib / PluginAnnotationLib | `plugin_core/src` | 源码 :SystemUI-plugin-core (13 文件) | 源码 ✓ |
| SystemUI-res | `res` `res-keyguard` `res-product` | core res | 资源 ✓ |
| SystemUI-statsd / -tags / -proto | 生成代码 (proto/logtags) | jar | jar 可接受（生成物）|

## 四、外部依赖清单（②jar/aar 与 ③Maven 分开）

### 4.0 为什么区分 jar 和 maven-aar：**资源冲突**（用户 2026-07-29 说明）

引入形式的选择，核心动机是**资源（res）冲突处理**：

- **jar 里没有资源** → 只含 .class 的纯代码依赖用 jar 即可（无资源冲突风险）。
- **带资源的 AOSP 库**：若直接从源码生成 aar，多个库/模块间的 res 很可能**重复、冲突**
  （同名 resource、AAPT2 合并失败）。
- **解决办法**：用脚本 `tools/gen_aar_maven.py` 把这类库打成**本地 maven 仓的 aar** 形式
  （放 `libs/maven/`），借 Gradle/AAPT2 对 maven aar 的标准资源合并/去重来化解冲突。

→ 所以 **libs/maven/ 里的 aar 不是随意选的，是专门为"带资源且会冲突"的库准备的资源冲突方案**。
判定引入形式时：**纯代码 → jar；带资源会冲突 → maven-aar（gen_aar_maven.py）；标准三方 → Maven 版本依赖。**

### 4.1 清单

`SystemUI-core` static_libs 里非 SystemUI 自有的，按三层拆：

**② AOSP 特有产物 → jar/aar（公网 Maven 没有 / 被 fork / aconfig 生成）：**
- framework.jar、android.car.jar
- SettingsLib、WindowManager-Shell、WifiTrackerLib、iconloader_base
- monet / libmonet
- LowLightDreamLib、TraceurCommon/Traceur-res、motion_tool_lib、contextualeducationlib
- notification_flags_lib、com_android_systemui_flags_lib、device_state_flags_lib、settingslib flags
- SystemUI-statsd / -tags / -proto（logtags/proto 生成物）

**③ 标准第三方上游库 → 正常 Gradle Maven 版本依赖（像普通 app，不要 jar/aar）：**
- androidx.*（core-ktx、appcompat、recyclerview、room、datastore、media3、lifecycle、
  constraintlayout、compose.*、activity-compose…）
- kotlinx_coroutines(_android)
- dagger2 / dagger2-compiler（用 kapt/ksp 插件）
- com.google.android.material
- lottie / lottie_compose
- jsr305 / jsr330

> ⚠️ 现状核对项：本项目当前可能把部分 ③ 类库（androidx/kotlinx/dagger）以 jar 或本地
> maven 仓形式引入，后续应审计并改为标准 Maven 坐标版本依赖。

## 五、参考项目 CarSystemUIGradle 印证

`CarSystemUIGradle/settings.gradle.kts` 的模块，全部 `java.srcDirs("src")` 源码方式：
```
:app :SystemUI-core :SystemUI-shared :SystemUI-plugin :SystemUI-plugin-core
:SystemUI-animation :SystemUI-monet
```
- SystemUI-core: `java.srcDirs("src")` + src-debug/src-release + res.srcDirs
- SystemUI-shared: `java.srcDirs("src"); aidl.srcDirs("src")`
- SystemUI-animation: `java.srcDirs("src"); res.srcDirs("res")`
- SystemUI-plugin: `java.srcDirs("src","bcsmartspace/src")`
→ 印证：SystemUI 自有子模块都用**源码 module**，不用 jar。

## 六、待办（后续重构方向）

1. 把 shared / animation / customization / unfold 从 jar 改为**源码 Gradle module**
   （或直接把源码并入相应模块的 `src`），移除对应 prebuilt jar 避免重复。
2. kairos：加 `-opt-in=com.android.systemui.kairos.ExperimentalFrpApi` 编译 flag
   （AOSP `utils/kairos/Android.bp:25` 就是这么写的）→ 一次清掉 779 个 opt-in 错误。
3. 补齐 SystemUI-shared-utils、animation/lib、compose/scene 等缺失源码。
4. 每步遵守规则 I（增量、记录错误数演变）。

## 七、注意：源码 vs jar 冲突

若某模块**同时**存在源码和 prebuilt jar，会重复类。改为源码时**必须移除对应 jar**
（shared→SystemUISharedLib.jar、animation→PlatformAnimationLib.jar、
customization→SystemUICustomizationLib.jar、unfold→我加的 unfold jar）。
