# Gradle 模块边界重新调研

**日期**：2026-08-06

## 背景

用户否决 `docs/architecture/2026-08-06-module-structure-audit.md` 中“约 30 个 Soong target 因而 22 个 Gradle module 数量合理”的推导。Soong target 数量不能机械等价为 Gradle module 数量；需要按正常 Gradle 改造重新判断源码模块、内部源码切片、JAR/AAR 和官方 Maven 边界。

## 调研目标

1. 以 AOSP `Android.bp` 的 `srcs`、`static_libs`、`libs`、`resource_dirs`、`sdk_version`、`plugins`、`visibility`、被引用关系为证据。
2. 对照参考项目 `CarSystemUIGradle` 的实际 Gradle module 边界和依赖交付方式。
3. 区分：
   - 必须独立的 Gradle 源码模块；
   - 可归入父 Gradle module 的 Soong 内部切片；
   - 应使用 AOSP JAR/AAR 的非 SystemUI 产物；
   - 应使用官方 Maven 的第三方依赖；
   - 无生产引用、不应进入项目的 test-only/dead target。
4. 直接修订 `docs/architecture/2026-08-06-module-structure-audit.md`，形成后续开发唯一模块划分指导。

## 原则

- 不以 Soong target 数量推导 Gradle module 数量。
- Gradle module 必须对应有意义的编译/复用 seam，而不是仅对应目录或 `java_library` 名称。
- AOSP `packages/SystemUI/` 内生产源码仍须源码引入，但允许多个内部 Soong target 归入同一 Gradle module，只要源码归属、依赖方向和最终打包语义准确。
- 非 SystemUI 源码按规则 F 使用 JAR/AAR；含资源用 AAR，无资源用 JAR。
- 本阶段只调研和修订架构文档，不修改模块源码或资源。

## 调研结论

- Soong `static_libs` 的实现 JAR和资源会合入父 target，不能用 target 数量推导 Gradle module 数量。
- 参考项目的 7 module 证明了可合并原则，但其源码代际、资源和依赖图与当前 AOSP 不同，不能照抄。
- 当前 22 个 include module 建议收敛为 13 个：12 个 Android/SystemUI 构建模块 + 1 个仅构建期 host annotation processor。
- 应合并：
  - Common + Log + shared-utils → `:SystemUI-common`
  - PlatformAnimation + Shader → `:SystemUI-animation`
  - Shared + Keyguard child → `:SystemUI-shared`
  - Compose Core + Scene → `:SystemUI-compose`
  - 全部 pods 生产源码 → `:SystemUI-core`
- 必须保留的细边界：
  - `:SystemUI-res`：约 959 个源码文件显式导入 `com.android.systemui.res.R`；
  - `:SystemUI-shared-biometrics`：源码显式导入独立 biometrics R，且 Settings 消费；
  - `:SystemUI-unfold`：shared/customization 多消费者 + AIDL/Dagger；
  - `:SystemUI-plugin-processor`：host build tool，不能打进 runtime。
- 应删除/替换：animationlib 源码 module、kairos、空 proto module、5 个 pods module、shared-keyguard、compose-scene、SystemUI-log 和两个 pods 空壳目录。
- AOSP generated code 使用 JAR；非 SystemUI 含资源库使用 AAR；标准第三方使用官方 Maven。

完整判定已直接写入：

- `docs/architecture/2026-08-06-module-structure-audit.md`

## 操作步骤

1. 完整复核当前 AOSP SystemUI 生产 `Android.bp` 及跨树消费者。
2. 检查 Soong `base.go` 的 static library 合并语义。
3. 检查参考项目 7 个 module 的 Gradle sourceSets 和依赖形式。
4. 统计各 source root 的文件数、资源 namespace 和当前 module 归属。
5. 重写原架构调研文档，给出确定的 13-module 目标图、当前 22-module 处置表及 JAR/AAR/Maven 分类。

## 错误数演变

- 调研前：当前构建在 AAR transform 重复 R 类阶段阻塞，没有可信 Kotlin 错误数。
- 调研后：未运行编译，错误数状态不变；本次只修改文档，不以编译错误数作为架构判定依据。

## 待解决问题

1. 实施前同步更新 ADR 0003、AGENTS/HANDOFF 中过强的“逐 BP target 建 Gradle module”表述。
2. 分阶段执行 module 合并、新建和删除，并更新 source alignment owner 映射。
3. 单独验证 Kotlin 2/Gradle 9 下 `ProtectedPluginProcessor` 的源码构建和接入方式。
4. 恢复直接 AAR，解决当前 transform 重复 R 类后再取得 Kotlin 基线。
5. 最终验证 manifest merge 和 `:app:assembleDebug`。

## 验证记录

未运行源码编译；本阶段以 AOSP BP、Soong 合并实现、源码 import/消费者图和参考项目 Gradle 配置为证据。文档通过 `git diff --check` 后方可提交。
