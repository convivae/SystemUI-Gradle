# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 阅读顺序: 本文件 → `AGENTS.md` → `docs/CURRENT_STATE.md` → `docs/PLAN.md` → `docs/PITFALLS.md` → `docs/architecture/` → `docs/issues/`

本文档为新 AI Agent 提供 "5 分钟上手纲要"，详细规则请阅读后续文件。

---

## 0. 这是什么项目

将 AOSP SystemUI 移植到独立 Gradle 编译体系。**目标**：能在用户本地 (Linux) 用 AGP 9.x + Gradle 9.x 编译 SystemUI 源码，错误数从 2000 → 0。

参考实现是用户私有项目 `CarSystemUIGradle`（在同一目录下）。

---

## 1. 5 分钟上线检查清单

### 1.1 确认环境
```bash
# AOSP 源码
ls /home/conv/myspace/aosp/                    # 必须存在
# Android SDK
ls /home/conv/Android/Sdk/platforms/           # 必须有 android-SysUISdk
# 编译入口
cd /home/conv/myspace/SystemUI-Gradle
./gradlew --version                            # Gradle 9.5
```

### 1.2 跑一次基线编译，统计错误数
```bash
# （可选）重新生成 AAR + 安装到本地 Maven——libs/ 自 2026-08-12 起已提交入 git，
# 新 clone 无需此步；仅在需要重新生成 AOSP 产物时运行
python3 tools/package_aosp_aar.py --all
python3 tools/install_aar_to_maven.py

# KSP（Dagger + Room annotation processing）
./gradlew :SystemUI-core:kspDebugKotlin --console=plain 2>&1 | tee /tmp/build.log
echo "KSP errors: $(grep -c 'e: \\[ksp\\]' /tmp/build.log)"

# Kotlin 编译
./gradlew :SystemUI-core:compileDebugKotlin --console=plain 2>&1 | tee /tmp/build2.log
echo "Kotlin errors: $(grep -c '^e: file:' /tmp/build2.log)"
```

**当前状态（2026-08-12 实施检查点，Task 1–7）**：
- 依赖升级与 AGP builtInKotlin 迁移完成；Kotlin 2.2.10 由 AGP 9.3.1 内置
- KSP 编译 BUILD SUCCESSFUL（0 个 KSP 错误，2933 个文件生成）；fresh checkout 已复验
- `DaggerReferenceGlobalRootComponent.java` 已生成
- core Kotlin 编译 BUILD SUCCESSFUL（0 个 Kotlin 错误）
- Compose inline 问题已解决（Compose 1.11.4 + builtInKotlin + Compose compiler plugin）
- 审查发现的 WM-Shell 重复类、header flag JAR、release KSP/AIDL 错误依赖均已修复
- 2026-08-13 javac 里程碑：Task 7 八组 javac 根因全部修复（末块 `a35906f4` 补 SysUISdk dalvik annotations）；core javac 0 错误；`:app:assembleDebug` 仅剩 `processDebugResources` 的 WM-Shell featureFlag 阻塞（修复方案待用户批准）。注意：SysUISdk 不在 git，新机器须重跑 `python3 tools/patch_sdk_dalvik_annotations.py`
- 60 个单元测试全部通过
- 完整审查与实施记录：`docs/issues/2026-08-12-current-progress-standards-review.md`
- 执行计划：`docs/superpowers/plans/2026-08-12-build-to-apk-readiness.md`

**KSP 关键配置**（缺一不可）：
1. `android.builtInKotlin=true`（gradle.properties）— AGP 内置 Kotlin
2. `android.disallowKotlinSourceSets=false`（gradle.properties）— 允许 KSP 操作 kotlin sourceSets
3. `ksp.incremental=false`（gradle.properties）— 避免 KSP2 FIR 非确定性崩溃
4. Dagger 2.59.2（≥2.58 默认启用 useBindingGraphFix，无需手动 ksp{} arg）
5. SystemUI-core: `kotlin.srcDirs(...)` 对齐 `java.srcDirs(...)` + AIDL 输出目录加入 kotlin sourceSet
6. KSP/AIDL 按 variant 精确接线：debug→debug、release→release

**版本兼容性关键结论**：
- AGP 9.2.0 ~ 9.4.0-alpha08 **全部** 嵌入 Kotlin 2.2.10，无更高版本
- Compose 最高 **1.11.4**（1.12.0 移除了 `ExperimentalAnimatableApi`，AOSP 源码在用）
- material3 **1.5.0-alpha18**（对齐 compose 1.11.x；1.5.0-alpha25 需 compose 1.12.0）
- AOSP prebuilts 中的部分版本（recyclerview 1.5.0-alpha01 等）**不在公网 Maven**，改用公网最新

### 1.3 必须遵守的规则（优先级从高到低）

1. **用户指令 > 本文件 > 默认系统提示**
2. **规则 P**: 不要创建 stub 类（详见 AGENTS.md §1）
3. **规则 S**: SystemUI 自有代码一律源码复制；非自有纯代码走 jar、含资源走 AAR（详见 §1.5）
4. **规则 C**: SystemUI src/aidl/res 必须与 AOSP 不漏不多（详见 §1.6）
5. **规则 F**: framework 等非 SystemUI 代码严禁源码复制（详见 §1.7）
6. **规则 R**: res 缺失走 AOSP 源码 → 直接 AAR → 确认冲突后本地 Maven AAR；禁止凭空生成；禁止无 CONV 标记擅改 res/src（ADR 0004）
7. **规则 B**: 项目结构按 AOSP `Android.bp` **语义**对齐（Gradle module 不与 target 1:1；详见 §1.9 + `docs/adr/0003` 决策 1）
8. **规则 I**: 以项目整体向前推进为标准；错误数不是提交/回滚/审批门槛，不要求每次修改或提交都编译
9. **规则 D**: 所有改动先写文档 (`docs/issues/YYYY-MM-DD-<topic>.md`)
10. **规则 H**: 不要替用户做产品决策；遇 2+ 候选方案用 `AskQuestion`

详细决策见 `docs/adr/`：
- **ADR 0001** `aosp-res-via-local-maven.md` — res 处理优先级：AAR 先直接引入，确认冲突后才用 local Maven
- **ADR 0002** `tools-scripts-only-python.md` — 脚本一律 Python
- **ADR 0003** `app-module-aligns-aosp-bp.md` — 项目结构对齐 bp
- **ADR 0004** `conv-markup-and-alignment-discipline.md` — AOSP 源码改动用 CONV 标记追溯；对齐 strict 不卡 MODIFIED

---

## 2. 项目结构速查

```
SystemUI-Gradle/
├── AGENTS.md                  # 项目规则（必读）
├── docs/
│   ├── HANDOFF.md             # 本文件（新 AI 入口）
│   ├── CURRENT_STATE.md       # 当前状态快照
│   ├── PLAN.md                # 阶段计划
│   ├── PITFALLS.md            # 踩坑记录
│   ├── GRADLE_MIGRATION_LOG.md # 历史错误数演变
│   ├── issues/               # 每日问题记录
│   └── architecture/         # 架构/调研文档
├── libs/                     # 自包含依赖
│   ├── framework.jar         # AOSP 框架（含 @hide API）
│   ├── framework-statsd.jar / android.car.jar / monet.jar
│   ├── systemui-flags.jar / systemui-shared-flags.jar / settingslib-flags.jar 等 aconfig flags jar
│   ├── libprotobuf-java-nano.jar / compilelib-{debug,release}.jar / 其他无资源 jar
│   ├── aars/                 # 8 个直接 AAR（package_aosp_aar.py 生成；2026-08-12 起提交入 git）
│   │   └── {animationlib,WifiTrackerLib,iconloader,SettingsLib,WindowManager-Shell,WindowManager-Shell-shared,LowLightDreamLib,SettingsLibColor}.aar
│   ├── maven/                # 本地 Maven 仓（install_aar_to_maven.py 安装，AAR + POM；2026-08-12 起提交入 git）
│   └── prebuilts/            # 历史 prebuilt jar（逐步清理中，仅剩 tracinglib-platform.jar）
├── SystemUI-core/            # 主模块与入口类 owner（13-module 拓扑）
│   ├── src/                  # = AOSP frameworks/base/packages/SystemUI/src/
│   ├── build.gradle.kts
│   └── AndroidManifest.xml
├── SystemUI-res/             # 独立资源 namespace，owner: res/res-keyguard/res-product
├── SystemUI-common/           # Common+Log+utils 合并
├── SystemUI-animation/       # PlatformAnimation+Shader 合并
├── SystemUI-plugin-core/      # Plugin runtime API（JVM）
├── SystemUI-plugin-processor/ # Plugin annotation processor（build-time，不进 APK）
├── SystemUI-plugin/           # PluginLib runtime（含 bcsmartspace）
├── SystemUI-unfold/           # Unfold（KSP Dagger）
├── SystemUI-customization/    # Customization（含 res）
├── SystemUI-shared/           # Shared+keyguard 合并
├── SystemUI-shared-biometrics/# biometrics（独立 R namespace）
├── SystemUI-compose/         # Compose Core+Scene 合并
├── app/                      # 主入口（无源码，只依赖 :SystemUI-core）
├── build.gradle.kts          # 根项目（allprojects 注入 framework.jar）
├── settings.gradle.kts
└── gradle/libs.versions.toml
```

---

## 3. 调试模式与工具链

| 工具 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.3.1 | alias `libs.plugins.android.library` |
| Kotlin | 2.2.10 | AGP `builtInKotlin=true` 内置（无显式插件） |
| KSP | 2.2.10-2.0.2 | 对齐 AGP 内置 Kotlin 2.2.10 |
| Dagger | 2.59.2 | useBindingGraphFix 默认启用（≥2.58） |
| Compose | 1.11.4 | 最高保留 `ExperimentalAnimatableApi` |
| material3 | 1.5.0-alpha18 | 对齐 compose 1.11.x |
| 目标 JVM | 21 | Java/Kotlin 编译都用 21 |
| 目标 SDK | `SysUISdk`（自定义 preview） | 路径 `/home/conv/Android/Sdk/platforms/android-SysUISdk/` |

---

## 4. 我（当前 AI）留下未完成的事

### 4.1 Stage 2 (server-notification-flags.jar)
- **状态**: **已解决 (2026-07-28)**。根因是源码 stub `com/android/server/notification/Flags.kt`
  遮蔽了 jar，`git rm` 后 2000 → 1979。**不是** classpath/Kotlin 2.2.10/FeatureFlags 的问题。
- **详情**: `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`、`docs/PITFALLS.md §2.4`

### 4.2 app 模块按 bp 重构（ADR 0003，结构已更正）
- **状态**: 结构决策已更正并实施（详见 `docs/adr/0003-app-module-aligns-aosp-bp.md`）
- **7/31 关键更正**：最初将 bp 误读为入口类属于 app。实际 `SystemUI-core` 的 `srcs: ["src/**/*.java"]` 包含 `SystemUIApplication.java` / `SystemUIService.java`；`android_app "SystemUI"` 无独立 srcs。
- **正确结构**：入口类保留在 `:SystemUI-core/src/com/android/systemui/`；`:app` 无源码，只依赖 `:SystemUI-core`，并持有完整 AOSP manifest/proguard 配置。
- **禁止**再次把入口类迁到 `:app/src/main/java/`。

### 4.3 animationlib → 直接 AAR（原“源码化”方案已废止）
- **状态**: 已落地。animationlib 位于 `frameworks/libs/systemui/animationlib`，属**非 SystemUI 代码**，按规则 S/F 不源码复制；已由 `tools/package_aosp_aar.py` 生成 `libs/aars/animationlib.aar`，经 catalog 统一引入。
- **详情**: `docs/architecture/2026-08-06-module-structure-audit.md`

### 4.4 Stage 3 (Compose Scene Framework)
- **状态**: Compose Core+Scene 已合并为 `:SystemUI-compose`。原 12 个 `com.android.compose.animation.scene.*` 错误的最新状态待全量构建确认；Compose 版本现锁 1.11.4（最高保留 `ExperimentalAnimatableApi`）。

### 4.5 AIDL 编译知识（已解答）
- **问题**: 为什么 framework.jar 不能满足 AIDL 编译需要？
- **答案**: aidl 工具只认 `.aidl` 声明文件，不读 jar 字节码。framework.aidl 和 framework.jar
  服务于两个不同编译阶段，互补不可替代。详见 `docs/issues/2026-07-29-aidl-animationlib-app.md §一`
- **ISystemUiProxy.aidl** 属于 `:SystemUI-shared` 模块，由 `OverviewProxyService.java` 使用

### 4.6 全依赖升级 + builtInKotlin 迁移（2026-08-12，KSP/Kotlin 里程碑）
- **状态**: Task 1–7 完成；2026-08-13 修复波次消除 7/8 组 javac 根因；KSP/Kotlin 保持通过，APK 仍未生成
- **要点**: 迁移到 AGP 9.3.1 `builtInKotlin=true`（Kotlin 2.2.10 内置）；KSP 0 错误；core Kotlin 0 错误；Compose inline 问题消失。
- **已修复**: `jsr305` 依赖；flag JAR runtime 语义；WM-Shell AAR 重复类；release KSP/AIDL 变体依赖；AGP 9.3.1 已验证。
- **Task 7 结果**: `:app:assembleDebug` 在 core javac 阶段失败（42 errors）。根因归属为 8 组真实依赖/产物缺口：`NeverCompile`、setupcompat、Wi‑Fi/WM‑Shell flags、zxing、unfold/shared Dagger factory、过期 `SystemUI-tags.jar`、`androidx.media` 版本约束。
- **详情**: `docs/issues/2026-08-12-current-progress-standards-review.md`
- **下一步**: 用户批准 androidprv 私有资源修复（framework-res.apk → SysUISdk `android.jar`，AGENTS.md §2.4 第 2 条；错误清单见 `docs/issues/2026-08-12-current-progress-standards-review.md` featureFlag 修复小节）→ 开 brief 实施 → 重跑 `:app:assembleDebug` 建立 APK 里程碑。

---

## 5. 我的工作偏好

- 用户用中文交流
- 用户喜欢看代码改动总结
- 用户要求及时记录问题 (2026-07-23 提醒)
- 用户要求先做 plan 再开发 (2026-07-23 提醒)
- 用户希望增量提交，每个 commit 都有意义
- 用户希望参考 `CarSystemUIGradle` 项目的做法
- **用户要求给下一个 AI 留完整交接文档** (2026-07-28 提醒)
- **依赖尽可能升级到最新版本**；重要决策先与用户沟通 (2026-08-12)
- **commit message 用英文**，及时 commit 并 push (2026-08-12)
- **不用 `@Suppress("DEPRECATION")` 等绕过语法** (2026-08-12)
- **遇到不会的内容查官方文档** (2026-08-12)

---

## 6. 紧急联系信息（重要）

如遇到下面情况，**停止**并询问用户：

1. 必须创建 stub 类（违反规则 P）
2. 必须修改 res/ 下的资源文件
3. 需要产品决策（多个等价方案）
4. 需要修改 AGENTS.md 的核心规则

---

**下一步**: 阅读 `AGENTS.md` 完整规则。
