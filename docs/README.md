# SystemUI-Gradle 文档索引

> **目的**: 让任何 AI Agent 都能快速找到所需文档。
> **最后更新**: 2026-08-12

---

## 必读文档 (新 AI 入口)

| 顺序 | 文档 | 说明 |
|------|------|------|
| 1 | [`docs/HANDOFF.md`](./HANDOFF.md) | 5 分钟上手纲要 + 项目概述 |
| 2 | [`../AGENTS.md`](../AGENTS.md) | 项目规则（必读） |
| 3 | [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) | 当前状态快照（构建状态、版本矩阵、待解决） |

**当前里程碑（2026-08-12 实施检查点，Task 1–6）**：依赖升级 + AGP `builtInKotlin` 迁移完成；
debug/release KSP 0 错误；core Kotlin 0 错误。审查发现的 `jsr305`、WM-Shell AAR 交集、
header flag JAR 与 release KSP/AIDL 依赖问题均已修复；最终 `:app:assembleDebug` 基线待 Task 7 记录。
详见 [`issues/2026-08-12-current-progress-standards-review.md`](./issues/2026-08-12-current-progress-standards-review.md)，
后续按 [`superpowers/plans/2026-08-12-build-to-apk-readiness.md`](./superpowers/plans/2026-08-12-build-to-apk-readiness.md) 执行。

---

## 规则与原则

- [`../AGENTS.md`](../AGENTS.md) - 全局规则、依赖引入、问题排查流程

### 架构决策记录 (ADR)

| ADR | 文档 | 决策 |
|-----|------|------|
| 0001 | [`adr/0001-aosp-res-via-local-maven.md`](./adr/0001-aosp-res-via-local-maven.md) | res 缺失处理：AAR 先直接引入，确认冲突后才用 local Maven |
| 0002 | [`adr/0002-tools-scripts-only-python.md`](./adr/0002-tools-scripts-only-python.md) | `tools/` 脚本一律 Python，禁止 .sh |
| 0003 | [`adr/0003-app-module-aligns-aosp-bp.md`](./adr/0003-app-module-aligns-aosp-bp.md) | 模块划分/依赖/入口类位置按 AOSP `Android.bp` 语义对齐 |
| 0004 | [`adr/0004-conv-markup-and-alignment-discipline.md`](./adr/0004-conv-markup-and-alignment-discipline.md) | AOSP 源码改动用 CONV 标记追溯；对齐 strict 不卡 MODIFIED |

---

## 现状与计划

- [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) - 当前构建状态、版本矩阵、待解决清单
- [`docs/PLAN.md`](./PLAN.md) - 阶段计划（含历史阶段记录）
- [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) - 历史问题与错误数演变
- [`docs/audit-2026-07-30-aosp-src-parity.md`](./audit-2026-07-30-aosp-src-parity.md) - AOSP 源码对齐审计
- [`docs/mapping-2026-07-30-aosp-bp-to-gradle.md`](./mapping-2026-07-30-aosp-bp-to-gradle.md) - Android.bp → Gradle 模块映射

---

## 踩坑与调研

- [`docs/PITFALLS.md`](./PITFALLS.md) - 看似简单但实际不行的方案（含 builtInKotlin/KSP/AIDL 兼容性 §1.5）
- [`docs/architecture/`](./architecture/) - 深度调研文档
  - [`STAGE2-3-RESEARCH-LOG.md`](./architecture/STAGE2-3-RESEARCH-LOG.md) - Stage 2-3 根因分析（历史）
  - [`2026-07-29-dependency-audit.md`](./architecture/2026-07-29-dependency-audit.md) - 依赖审计（三层策略）
  - [`2026-07-29-systemui-module-source-vs-jar.md`](./architecture/2026-07-29-systemui-module-source-vs-jar.md) - 源码 vs jar 判定调研
  - [`2026-08-06-module-structure-audit.md`](./architecture/2026-08-06-module-structure-audit.md) - 13-module 结构审计
  - [`2026-08-06-reference-project-rationale.md`](./architecture/2026-08-06-reference-project-rationale.md) - 参考项目机制的"为什么"
  - [`2026-08-06-soong-android-app-vs-gradle-app.md`](./architecture/2026-08-06-soong-android-app-vs-gradle-app.md) - Soong android_app vs Gradle app 分析

---

## 问题记录 (按时间)

### 2026-08（近期，先读这些）

| 日期 | 文档 | 主题 |
|------|------|------|
| 2026-08-12 | [`issues/2026-08-12-current-progress-standards-review.md`](./issues/2026-08-12-current-progress-standards-review.md) | 当前进度规范审查、APK 新阻塞与后续实施计划 |
| 2026-08-12 | [`issues/2026-08-12-deps-upgrade-builtin-kotlin.md`](./issues/2026-08-12-deps-upgrade-builtin-kotlin.md) | 全依赖升级 + builtInKotlin 迁移（KSP 里程碑） |
| 2026-08-11 | [`issues/2026-08-11-phase-c-final-4-decisions.md`](./issues/2026-08-11-phase-c-final-4-decisions.md) | Phase C 4 项版本决策（版本已被 08-12 升级超越） |
| 2026-08-11 | [`issues/2026-08-11-aar-maven-catalog-unification.md`](./issues/2026-08-11-aar-maven-catalog-unification.md) | AAR 统一到 Maven catalog（gitignore 策略已变更） |
| 2026-08-07 | [`issues/2026-08-07-conv-markup-spec.md`](./issues/2026-08-07-conv-markup-spec.md) | CONV 标记规范（ADR 0004） |
| 2026-08-07 | [`issues/2026-08-07-post-topology-review.md`](./issues/2026-08-07-post-topology-review.md) | 13-module 拓扑后置审查 |
| 2026-08-07 | [`issues/2026-08-07-aosp-artifact-recovery.md`](./issues/2026-08-07-aosp-artifact-recovery.md) | AOSP 产物恢复 |
| 2026-08-07 | [`issues/2026-08-07-product-variant-conv-del.md`](./issues/2026-08-07-product-variant-conv-del.md) | res-product `product=` 变体 CONV_DEL |
| 2026-08-07 | [`issues/2026-08-07-uncaught-exception-prehandler-reflection.md`](./issues/2026-08-07-uncaught-exception-prehandler-reflection.md) | 反射方案记录 |
| 2026-08-06 | [`issues/2026-08-06-gradle-module-boundary-research.md`](./issues/2026-08-06-gradle-module-boundary-research.md) | Gradle 模块边界调研 |
| 2026-08-06 | [`issues/2026-08-06-module-consolidation-plan.md`](./issues/2026-08-06-module-consolidation-plan.md) | 模块合并计划 |
| 2026-08-06 | [`issues/2026-08-06-soong-gradle-apk-and-progress-policy.md`](./issues/2026-08-06-soong-gradle-apk-and-progress-policy.md) | APK 政策与前进原则（规则 I） |
| 2026-08-06 | [`issues/2026-08-06-source-alignment-audit.md`](./issues/2026-08-06-source-alignment-audit.md) | 源码对齐审计 |

### 2026-07（历史）

| 日期 | 文档 | 主题 |
|------|------|------|
| 2026-07-31 | [`issues/2026-07-31-gen_aar_maven-rewrite.md`](./issues/2026-07-31-gen_aar_maven-rewrite.md) | gen_aar_maven.py 重写（已废弃） |
| 2026-07-30 | [`issues/2026-07-30-phase-d-modules-compile.md`](./issues/2026-07-30-phase-d-modules-compile.md) | Phase D 模块编译 |
| 2026-07-29 | [`issues/2026-07-29-aidl-animationlib-app.md`](./issues/2026-07-29-aidl-animationlib-app.md) | AIDL 编译知识（aidl 工具不读 jar） |
| 2026-07-29 | [`issues/2026-07-29-completeness-audit.md`](./issues/2026-07-29-completeness-audit.md) | 规则 C 完整性审计 |
| 2026-07-29 | [`issues/2026-07-29-shared-source-migration.md`](./issues/2026-07-29-shared-source-migration.md) | shared 源码迁移 |
| 2026-07-28 | [`issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`](./issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md) | stub 遮蔽 jar 根因（经典案例） |
| 2026-07-28 | [`issues/2026-07-28-server-flags-debug-session.md`](./issues/2026-07-28-server-flags-debug-session.md) | server-flags 调试 session |
| 2026-07-28 | [`issues/2026-07-28-r-import-ambiguity.md`](./issues/2026-07-28-r-import-ambiguity.md) | 全项目 R import 歧义清零 |
| 2026-07-28 | [`issues/2026-07-28-systemui-aidl-jar.md`](./issues/2026-07-28-systemui-aidl-jar.md) | AIDL jar（后被 AIDL 源码编译取代） |
| 2026-07-28 | [`issues/2026-07-28-settingslib-full-jar.md`](./issues/2026-07-28-settingslib-full-jar.md) | SettingsLib kotlin+javac 双 jar |
| 2026-07-28 | [`issues/2026-07-28-compose-core-source.md`](./issues/2026-07-28-compose-core-source.md) | PlatformComposeCore 源码补齐 |
| 2026-07-28 | [`issues/2026-07-28-compose-features-source.md`](./issues/2026-07-28-compose-features-source.md) | compose/features 源码补齐 |
| 2026-07-28 | [`issues/2026-07-28-transitive-r-customization-res.md`](./issues/2026-07-28-transitive-r-customization-res.md) | transitive R + customization res |
| 2026-07-28 | [`issues/2026-07-28-customization-api-exposure.md`](./issues/2026-07-28-customization-api-exposure.md) | implementation→api 暴露 |
| 2026-07-28 | [`issues/2026-07-28-proto-nano-gen-jar.md`](./issues/2026-07-28-proto-nano-gen-jar.md) | nano proto 生成类 jar |
| 2026-07-28 | [`issues/2026-07-28-systemui-log-jar.md`](./issues/2026-07-28-systemui-log-jar.md) | LogLib jar 冲突（classpath 顺序取胜） |
| 2026-07-28 | [`issues/2026-07-28-unfold-jar-androidx-window.md`](./issues/2026-07-28-unfold-jar-androidx-window.md) | unfold jar + androidx.window |
| 2026-07-28 | [`issues/2026-07-28-lottie-jar.md`](./issues/2026-07-28-lottie-jar.md) | lottie/lottie_compose jar |
| 2026-07-28 | [`issues/2026-07-28-biometric-shared-model.md`](./issues/2026-07-28-biometric-shared-model.md) | biometric shared model |
| 2026-07-28 | [`issues/2026-07-28-wifitrackerlib-update.md`](./issues/2026-07-28-wifitrackerlib-update.md) | WifiTrackerLib 更新 |
| 2026-07-23 | [`issues/2026-07-23-server-notification-flags-unresolvable.md`](./issues/2026-07-23-server-notification-flags-unresolvable.md) | server-notification-flags（已于 07-28 解决） |
| 2026-07-22 | [`issues/2026-07-22-framework-jar-replace-and-stubs.md`](./issues/2026-07-22-framework-jar-replace-and-stubs.md) | framework.jar 替换 |
| 2026-07-22 | [`issues/2026-07-22-sdk-android-jar-merge.md`](./issues/2026-07-22-sdk-android-jar-merge.md) | SDK android.jar 合并 |
| 2026-07-22 | [`issues/2026-07-22-stub-cleanup-and-deps.md`](./issues/2026-07-22-stub-cleanup-and-deps.md) | v1 stub 清理 |
| 2026-07-18 | [`issues/2026-07-18-real-framework-jar-migration.md`](./issues/2026-07-18-real-framework-jar-migration.md) | 真实 framework.jar 迁移 |

---

## 工具脚本（全部 Python，ADR 0002）

| 脚本 | 用途 |
|------|------|
| [`../tools/package_aosp_aar.py`](../tools/package_aosp_aar.py) | 从 AOSP Soong 产物打包 AAR 到 `libs/aars/`（多 JAR 合并、reject_sysui、确定性） |
| [`../tools/install_aar_to_maven.py`](../tools/install_aar_to_maven.py) | 安装 `libs/aars/*.aar` 到 `libs/maven/`（AAR + POM 骨架） |
| [`../tools/package_compilelib_jars.py`](../tools/package_compilelib_jars.py) | 打包 compilelib debug/release JAR |
| [`../tools/package_aconfig_jars.py`](../tools/package_aconfig_jars.py) | 从 AOSP `javac` 产物打包完整 aconfig runtime JAR |
| [`../tools/install_sdk.py`](../tools/install_sdk.py) | 校验 + 补 SysUISdk framework.aidl（framework 隐藏接口） |
| [`../tools/check_source_alignment.py`](../tools/check_source_alignment.py) | AOSP SystemUI src/AIDL/res 对齐校验（规则 C） |
| [`../tools/markup_product_variants.py`](../tools/markup_product_variants.py) | res-product `product=` 变体 CONV 标记 |
| [`../tools/clean_prebuilts.py`](../tools/clean_prebuilts.py) | 清理 prebuilt jar 中的冲突类 |
| [`../tools/clean_aar_maven.py`](../tools/clean_aar_maven.py) | 清理本地 Maven 仓 |
| [`../tools/fix_r_imports_to_res.py`](../tools/fix_r_imports_to_res.py) | R import 修正 |
| [`../tools/rebuild_settingslib_aar.py`](../tools/rebuild_settingslib_aar.py) | 重建 SettingsLib AAR |
| `../tools/gen_aar_maven.py` | 已废弃（R.jar 合并失败实验），勿用 |

单元测试：`python3 -m unittest discover -s tools/tests -p 'test_*.py'`（60 个）。

---

## 项目根目录

- [`../`](../) - SystemUI-Gradle/
  - [`../build.gradle.kts`](../build.gradle.kts) - 根项目（allprojects 注入 framework.jar）
  - [`../settings.gradle.kts`](../settings.gradle.kts) - 模块配置 + 插件版本声明
  - [`../gradle/libs.versions.toml`](../gradle/libs.versions.toml) - 版本目录（单一事实源）
  - [`../gradle.properties`](../gradle.properties) - builtInKotlin/KSP/sourceSets 关键开关
  - [`../libs/`](../libs/) - 自包含依赖（jar + aars + maven，**2026-08-12 起提交入 git**）

---

## 快速搜索

### "项目规则是什么？"
→ [`AGENTS.md`](../AGENTS.md) §1, §2

### "现在构建状态如何？"
→ [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) §0–§2（KSP 0 错误 / Kotlin 0 错误 / APK 最终基线待复验）

### "当前各依赖什么版本？"
→ [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) §3 或 [`AGENTS.md`](../AGENTS.md) §4.3

### "为什么不能用 Kotlin 2.3.x / Compose 1.12？"
→ [`issues/2026-08-12-deps-upgrade-builtin-kotlin.md`](./issues/2026-08-12-deps-upgrade-builtin-kotlin.md) §二

### "builtInKotlin 下 KSP/AIDL 怎么配？"
→ [`docs/PITFALLS.md`](./PITFALLS.md) §1.5

### "我能加 stub 类吗？"
→ 不能。`AGENTS.md` §1.2（规则 P）

### "server-notification-flags 怎么修的？"
→ 已解决：源码 stub 遮蔽 jar。[`issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`](./issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md)

### "错误数变化历史？"
→ [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md)（注意：错误数仅作诊断，规则 I）

### "哪些方案试过失败？"
→ [`docs/PITFALLS.md`](./PITFALLS.md) 全文

### "下次该做什么？"
→ [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) §5 待解决
