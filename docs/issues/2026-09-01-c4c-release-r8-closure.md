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
| R2 | `./gradlew :app:assembleRelease --max-workers=4`（杀双 daemon 后） | FAILED — `:app:minifyReleaseWithR8`：R8 missing classes 31 条（missing_rules.txt），BUILD FAILED in 1m 37s | R8 闭包 17 基线漂移（brief 预期内的首破冰点），逐类归属见 §R2 | 逐类诊断处理中 |

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

| Fix | 内容 | 状态 |
|---|---|---|
| F1 | core +implementation(wmshell-aidls.jar) | 待实施 |
| F2 | am-flags 冻结 jar + core wiring | 待实施 |
| F3 | settingstheme-flags 冻结 jar + core wiring | 待实施 |
| F4 | bubbles-user-model 冻结 jar + core wiring | 待实施 |
| F5 | displaylib 合并 kapt javac（8 类 Dagger/*_Factory，`android_common/javac/displaylib.jar`，与 kotlin jar 122 类零重叠实测） | 待实施 |
| F6 | SettingsLib AAR per-target Kotlin 半边（+59 类，1431 总量）+ 升坐标 2.0.1 | 待实施 |
| F7 | kotlin-parcelize-runtime 2.2.10 官方坐标 + core wiring | 待实施 |

（注：displaylib Kotlin jar 的 `DisplayLibComponentKt.createDisplayLibComponent` 直接 invokestatic `DaggerDisplayLibComponent.factory()` —— javap 实测；Soong bp `plugins: dagger2-compiler` kapt 产物在 `android_common/javac/`，即 F5。）

## 待解决问题

（随轮次记录。）
