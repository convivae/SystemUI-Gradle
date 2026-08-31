# Task 074 — C4c: Release/R8 编译闭环恢复绿（`:app:assembleRelease`）

- **Brief**: `docs/orchestration/tasks/074-c4c-release-r8-closure.md`
- **Worker**: w2:p1（task074，joycode GLM-5.3）
- **目标**: `./gradlew :app:assembleRelease` BUILD SUCCESSFUL（含 `minifyReleaseWithR8`），
  对齐门 / pytest / 冻结指纹保持绿。Runtime（C5）不在本任务范围。
- **基线事实**（chief 预核实，直接采信）：`:app:assembleDebug` 已绿（APK 199,845,582 B）；
  17 模块图已接线；SysUISdk 已按 17 重建（2026-08-31）。

## R0 基线门（2026-09-01，开工前）

| 门 | 命令 | 结果 |
|---|---|---|
| 对齐 | `python3 tools/check_source_alignment.py --strict` | exit 0 |
| pytest | `uv run pytest tools/tests -q` | 305 passed, 141 subtests passed |
| 冻结指纹 | `uv run python tools/package_misc_jars.py --verify-only` | 22/22 MATCH，0 非 MATCH |
| compilelib | `package_compilelib_jars.py --verify-only` 子命令**不存在**（brief 为条件式） | 改用 sha256 快照守恒：debug `9d12cbdd…`，release `ad605e3f…`；任务结束再核 git 未动 + 哈希不变 |

## 错误演变表

- 环境事故 SOP（chief 2026-09-01 批准）：**Release/R8 构建前必须同时清理 GradleDaemon 与 KotlinCompileDaemon**（`pkill -f GradleDaemon` + `pkill -f KotlinCompileDaemon`）——AGENTS 既有纪律只提 Gradle daemon，本次事故证明 Kotlin daemon 也可失联占用：Gradle daemon 16G + 残留 Kotlin compile daemon 10G 共 26G+ → kernel OOM。
  - 若双杀后仍 OOM：升级路径按序 `--max-workers=2` → `--max-workers=1`，再不足则如实报 swap/heap 数字报 chief（**不自行降 Xmx**，Task 024 既有裁决）。
  - 实操坑：`pkill -f GradleDaemon` 会匹配包含该字符串的自身 shell 命令行 → worker shell 自杀。正确写法 `pkill -9 -f 'Gradle[D]aemon'`（bracket 技巧）。

| 轮 | 命令 | 结果 | 根因 | 处置 |
|---|---|---|---|---|
| R1 | `./gradlew :app:assembleRelease --max-workers=4` | FAILED — daemon disappeared during `:app:minifyReleaseWithR8`（kern.log: `Out of memory: Killed process 1891402 (java) anon-rss:16266848kB`） | 11:52 构建遗留的 Kotlin compile daemon（RSS ~10G）与 Gradle daemon `-Xmx16g` 叠加超 30G 物理内存，R8 深度优化阶段 OOM | kill 遗留 Kotlin daemon（pid 1831865，进程态非文件改动），free 恢复 25G；R2 重跑 |
| R2 | `./gradlew :app:assembleRelease --max-workers=4`（杀双 daemon 后） | FAILED — `:app:minifyReleaseWithR8`：R8 missing classes 31 条（missing_rules.txt），BUILD FAILED in 1m 37s | R8 闭包 17 基线漂移（brief 预期内的首破冰点），逐类归属见 §R2 | 6 根因组 F1–F7，见 §R2 处置表 |
| R3 | 同上（F1 wmshell-aidls + F7 parcelize 接线后） | FAILED — missing classes 31→**8**（21 条 wmshell AIDL 引用 + parcelize 全闭） | F1/F7 为纯接线即可闭合；余 8 条归工件侧（F2–F6） | commit `4652adfd`；继续工件侧 |
| R4 | 同上（+ displaylib-kapt 全量 8 类初版 jar） | FAILED — R8 **duplicate class**：`PerDisplayInstanceRepositoryImpl_Factory` 在 application KSP 产物（`runtime_library_classes_jar/.../classes.jar`）与 `displaylib-kapt.jar` 双定义 | **根因**：bp `plugins: dagger2-compiler` 在 Soong 侧由 displaylib 自体 kapt 生成 8 类；Gradle 侧我方 `:SystemUI-application` KSP Dagger 对我方组件图重新生成其中 1 类（`PerDisplayInstanceRepositoryImpl_Factory`——由我方组件安装的 displaylib `@Provides` 模块触发），与 kapt jar 重叠；其余 7 类不被 KSP 生成（组件实现与工厂只被 displaylib 自体组件引用） | 收缩 displaylib-kapt 为子集提取：剔 KSP 重复类，保留 `DaggerDisplayLibComponent` 3 类（新增 `include_prefixes` 机制 + pytest） |
| R5 | 同上（displaylib-kapt 缩至 3 组件类 + F2/F3/F4 jar 到位） | FAILED — missing classes 8→**6**：3 条 `DaggerDisplayLibComponentImpl.initialize` 引用的 `DisplayRepositoryImpl_Factory`、`DisplaysWithDecorationsRepository{Compat,Impl}_Factory`（+ 3 条 SettingsLib Banner Kotlin——本批 F6 已准备） | **根因**：KSP 只为我方组件图触达的 @Provides 生成工厂；displaylib 自体组件 `DaggerDisplayLibComponentImpl.initialize` 内部引用的 3 个工厂不在触达面内，必须由 kapt 真实字节提供（KSP 无法从 jar 内已编译接口/实现生成）；`PerDisplayInstanceRepositoryImpl_Factory{,_Impl}` 前者与 KSP 重复、后者无引用，均不取 | `include_prefixes` 扩至 6 类（3 组件 + 3 组件内工厂）；SettingsLib per-target Kotlin 半边重产 AAR（F6） |
| R6 | `./gradlew :app:assembleRelease --max-workers=4`（F2–F6 工件 + F1–F7 全接线后） | **BUILD SUCCESSFUL in 5m 23s**（含 `:app:minifyReleaseWithR8`；missing classes 0） | R2–R5 全部根因组闭合 | 验收四门 + 复现验证，见 §R6 验收 |
| R7 | `./gradlew :app:minifyReleaseWithR8 --rerun-tasks --max-workers=4` + `:app:assembleRelease` | **BUILD SUCCESSFUL** ×2；APK sha256 复现一致 `c74d13fb…` | 可复现性验证 | — |
| — | `./gradlew :app:assembleDebug --max-workers=4` | **BUILD SUCCESSFUL in 1m 37s**（APK 211,710,774 B） | 硬门不回归（charter Part 4：每批须保持 assembleDebug 绿） | — |

## R2 missing_classes 逐类归属（31 条，6 根因组）

| 组 | 条数 | 类 | 根因（bp 实证） | 处置 |
|---|---|---|---|---|
| G1 | 21 | `com.android.wm.shell.{back,bubbles,common.pip,desktopmode{,.api},draganddrop,onehanded,recents,splitscreen,startingsurface}` 全部 I* AIDL Stub/Listener + `DisplayDeskState` | 17 `WindowManager-Shell-defaults` static_libs **L127** `WindowManager-Shell-aidls`（`frameworks/base/libs/WindowManager/Shell/Android.bp:36`，`src/**/*.aidl`）→ Soong 静态链 dex 进 APK；我们 wmshell AAR 不含静态依赖类，`libs/wmshell-aidls.jar`（80 类，冻结）仅 `:SystemUI-shared` compileOnly（task073 只闭编译期） | F1：`:SystemUI-core` 加 `implementation(files(wmshell-aidls.jar))`（先例：wm-shell-flags 16 A12 独立 jar 翻转）；重复类风险已实测：与 wmshell AAR/shared AAR 交集 0 |
| G2 | 1 | `com.android.server.am.Flags` | 同上 bp **L127** `am_flags_lib`（`services/core/java/com/android/server/am/Android.bp:15`，aconfig）static 链 | F2：`package_aconfig_jars.py` 新 entry `am-flags`（javac 产物 → `libs/am-flags.jar`，5 类 runtime 集校验）+ core implementation |
| G3 | 1 | `com.android.settingslib.widget.theme.flags.Flags` | `SettingsLibSettingsTheme` bp static_libs `aconfig_settingstheme_exported_flags_java_lib`（`SettingsTheme/Android.bp`，aconfig 声明在 `SettingsTheme/aconfig/settingstheme.aconfig`，package `com.android.settingslib.widget.theme.flags`）；我们 Theme AAR 只含 Kotlin 类，flags jar 缺 | F3：同 F2 新 entry `settingstheme-flags`（javac 5 类实测在 `android_common/javac/`）+ core implementation |
| G4 | 1 | `com.android.wm.shell.bubbles.user.model.BubbleUserInfo` | 17 `WindowManager-Shell-defaults` static_libs **L114** `bubbles-user-model`（`Shell/bubbles-user-model/Android.bp`，纯 Kotlin android_library 无 res）静态链 | F4：`package_misc_jars.py` 新 entry（kotlin jar → `libs/bubbles-user-model.jar`，冻结指纹+pytest，usertypelib 同款先例）+ core implementation |
| G5 | 3 | `settingslib.widget.BannerAnimationHelper`、`ResolutionAnimator{,$Data}` | SettingsLib 打包 discovery 只并 per-target **javac** jar，漏其 **kotlin** jar（BannerMessagePreference 模块 Kotlin 半边 34 类，含 R2 三个缺失类）；16 时代同样只有 javac，但 16 无这些 Kotlin 源 | F6：`package_aosp_aar.py` SettingsLib discovery 扩展为 javac + 同模块 sibling kotlin jar（模块界限内，Theme/Spa 等 kotlin-only 模块天然排除；合并器自带重复 entry 硬错）；重产 AAR 1372→1431 类；内容变化 → **坐标 2.0.0→2.0.1**（AGENTS §3.2.4），退役 2.0.0 目录，catalog+install 表+POM 同步 |
| G6 | 1 | `kotlinx.parcelize.Parcelize` | ace client bp static_libs **L34** `kotlin-parcelize-runtime`（`frameworks/libs/systemui/ace/src/.../client/Android.bp`）；AAR bytecode 引 CLASS-retention 注解；Maven Central 实测 `org.jetbrains.kotlin:kotlin-parcelize-runtime:2.2.10` 存在且含 `kotlinx/parcelize/Parcelize.class`（tier③ 官方坐标，版本对齐项目 Kotlin 2.2.10） | F7：catalog 新 alias + core implementation |

**待验证假设**（R3 起逐轮证实/证伪）：新 Kotlin 类（BannerAnimationHelper 引 androidx.dynamicanimation 等）可能触发更深层闭包缺失，属预期内新发现，逐类归类处理。

## R2 missing_classes 处置进度

| Fix | 内容 | 状态 | commit |
|---|---|---|---|
| F1 | core +implementation(wmshell-aidls.jar)（R3 实证闭合 21 条 AIDL 引用） | ✅ | `4652adfd` |
| F2 | am-flags 冻结 jar + core wiring | ✅ | `d6c19afd` / `174828f3` |
| F3 | settingstheme-flags 冻结 jar + core wiring | ✅ | `d6c19afd` / `174828f3` |
| F4 | bubbles-user-model 冻结 jar + core wiring | ✅ | `e54bb1da` / `174828f3` |
| F5 | displaylib kapt 子集 jar（6 类：3 组件 + 3 组件内工厂；R4/R5 收缩）+ core wiring | ✅ | `e54bb1da` / `174828f3` |
| F6 | SettingsLib AAR per-target Kotlin 半边（+59 类，1431 总量）+ 升坐标 2.0.1 | ✅ | `4b728f24` |
| F7 | kotlin-parcelize-runtime 2.2.10 官方坐标 + core wiring | ✅ | `4652adfd` |

（注：displaylib Kotlin jar 的 `DisplayLibComponentKt.createDisplayLibComponent` 直接 invokestatic `DaggerDisplayLibComponent.factory()` —— javap 实证；Soong bp `plugins: dagger2-compiler` kapt 产物在 `android_common/javac/`，即 F5。）

**R4/R5 关键机理（displaylib dagger 双生成问题的定性）**：Soong 单体编译时 kapt 为 displaylib 生成全 8 类；Gradle 图里 dagger 图分两层——我方 `:SystemUI-application` KSP 只为我方组件触达面生成 `PerDisplayInstanceRepositoryImpl_Factory`（KSP 输出目录实测唯一 displaylib 类，且 R4 duplicate 报错实证重叠），其余 7 类不被生成；其中 3 类组件实现/工厂在 displaylib 自体组件内部引用（R5 missing refs 实证）。故 `displaylib-kapt.jar` = Soong javac jar 的确定性子集（6 类），既补组件实现与内部工厂，又剔 KSP 重复类。子集提取带 `include_prefixes` + 固定时间戳 + pytest（确定性/精确集/排除 KSP 重复类均断言）。

## R6 验收（2026-09-01）

| 门 | 命令 | 实际结果 |
|---|---|---|
| Release 构建 | `./gradlew :app:assembleRelease --max-workers=4` | **BUILD SUCCESSFUL in 5m 23s**（`> Task :app:minifyReleaseWithR8` 执行并成功） |
| 可复现 | `:app:minifyReleaseWithR8 --rerun-tasks` 后重 assemble | BUILD SUCCESSFUL；APK sha256 前后一致 |
| 对齐 | `python3 tools/check_source_alignment.py --strict` | exit 0 |
| pytest | `uv run pytest tools/tests -q` | **310 passed**, 151 subtests passed |
| 冻结指纹 | `uv run python tools/package_misc_jars.py --verify-only` | **24/24 MATCH**，0 DIFF/MISSING |
| compilelib 字节守恒 | sha256 快照 | debug `9d12cbdd…`、release `ad605e3f…` 与 R0 快照一致；git 未动（`--verify-only` 子命令不存在，brief 为条件式，以此法代） |
| Debug 硬门 | `./gradlew :app:assembleDebug --max-workers=4` | **BUILD SUCCESSFUL in 1m 37s**（APK 211,710,774 B） |

**Release APK 初值（供 C5/C6 对照）**：

- 路径：`app/build/outputs/apk/release/app-release.apk`
- 大小：**45,030,130 B**（Debug 199,845,582 B → 16 时代 release 亦在数十 MB 量级；R8 shrink + resource shrink 生效）
- sha256：`c74d13fba6cfc36b05c891ea90366083019d65755458a990df5d8830f0e6ff9c`
- mapping：`app/build/outputs/mapping/release/mapping.txt` 存在（另有 seeds/usage/resources/configuration.txt 全套）
- 签名：platform keystore（signingConfig release，与 debug 同）

## 移交 C5 清单（runtime 侧）

1. **双 dagger 生成层的 runtime 验证点**：`displaylib-kapt.jar` 的 6 类与 application KSP 生成的 `PerDisplayInstanceRepositoryImpl_Factory` 并存于 dex（AOSP 语义：Soong 也同时有两者——单体 kapt 生成全套，我方只剔了与 KSP 重复的 1 类）。C5 需验证 `createDisplayLibComponent` 路径在设备上可走通。
2. **kotlin-parcelize-runtime**：首个 runtime 注解 provider 官方坐标；ace client `@Parcelize` 反序列化路径需设备验证。
3. **`AssumeTrueForR8`/`AssumeFalseForR8` -dontwarn adapter**（`app/proguard_gradle.flags`，ADR 0006 §5）：17 基线本轮 R8 未再报该类 missing（构建成功即说明 adapter 生效面未变），但 flag folding 语义未在设备上验证过。
4. **R8 keep 规则迁移评估**：`app/proguard_common.flags` 的 `-keep class com.android.wm.shell.* { void <init>(); }` 等规则在 17 基线未触发新 missing，本轮未动；若 C5 出现 ClassCastException 反射类缺失，优先核对该文件与 AOSP 17 `proguard.flags` 的差异。
5. **`-dontobfuscate` + 4 条 CoreStartable keep 规则**（task 060/061 教训）本轮未触发，但 C5 的 DumpManager 注册路径是已知敏感点。
6. **APK 差异观察点**：17 release 45 MB vs 16 时代 release（数 MB 量级？——供 C5/C6 对照；16 的数字在 CURRENT_STATE 历史）。R8 `usage.txt`/`seeds.txt` 已产出，可作删除面分析输入。

## 提交记录

- `4652adfd` task074 R3: wire wmshell-aidls jar + kotlin-parcelize-runtime into core runtime closure
- `d6c19afd` task074 F2/F3: freeze am-flags + settingstheme-flags aconfig runtime jars
- `e54bb1da` task074 F4/F5: freeze bubbles-user-model jar + displaylib-kapt subset jar
- `4b728f24` task074 F6: SettingsLib AAR gains per-target Kotlin halves, 2.0.0 -> 2.0.1
- `174828f3` task074 F1-F7 wiring: core runtime closure + SettingsLib 2.0.1 catalog bump
- （另：本文档 + STATE.md 单行，随末次 commit）

## 环境纪律（本轮实证）

- **Release/R8 前杀双 daemon**：`pkill -9 -f 'Gradle[D]aemon'` + `pkill -9 -f 'KotlinCompile[D]aemon'`（R1 OOM 根因：残留 Kotlin daemon 10G + Gradle daemon 16G）。
- `--max-workers=4`（30G RAM）；本轮 R8 峰值未再触发 OOM（双杀后内存余量 25G+）。

## 待解决问题

- 无阻塞项。R2 全部 31 条 missing classes 已逐类归因并闭合；无 stub、无 runtime 打包平台类、无 dontwarn 掩盖（proguard_gradle.flags 的既有 aconfig adapter 是 task 044/060 用户批准的存量，本轮未新增）。

## Chief 复核补注（2026-08-31）

- review-PASS：对齐 `--strict` exit 0；pytest 310 passed + 151 subtests；指纹 24 MATCH；`:app:assembleRelease` chief 亲手重跑 BUILD SUCCESSFUL。
- **APK 字节确定性定性**：三次独立 full build 的 APK sha 互异（`c74d13fb`/`bfc11de1`/`965f1318`），解包比对全部 entry（dex/resources.arsc/清单）逐字节一致——差异仅在 APK zip 容器时间戳/中央目录元数据。结论：**APK 内容确定性成立，容器字节不承诺确定**；sha 台账为“每次构建的操作性台账”，非确定性门禁（与 16 时代惯例一致）。

