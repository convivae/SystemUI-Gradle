# Task 072 — C4a：Gradle 接线（新模块注册 + catalog 2.0.0 + 依赖增删 + 新 jar 打包）

## 背景

- C2 完成（task071，review-pass）：libs/ 102 个产物全部由脚本从 AOSP-17 再生；maven 全族坐标 **2.0.0**（catalog 尚未更新，现指向已退役 1.x，本任务更新）；`motion_tool_lib.jar` / `settingslib-selector-flags.jar` 已退役。
- C3 完成（task070）：三个新模块目录已有源码/res/manifest 但**没有 build.gradle.kts、未在 settings 注册**：
  - `SystemUI-application/`（bp `android_library "SystemUI-application"`：src 4 文件 = Dagger 根组件等 + `src/main/AndroidManifest.xml` 1338 行完整 manifest）
  - `SystemUI-clocks-common/`（bp `SystemUIClocks-CommonLib`，`customization/clocks/common/`：src 21 + res + manifest，被 SystemUICustomizationLib static_libs 消费）
  - `SystemUI-accessibility-floatingmenu-res/`（bp `AccessibilityFloatingMenu-res`，res-only，被 SystemUI-res static_libs 消费）
- 本任务只做**接线/打包/配置**：`./gradlew help`（配置解析）必须通过；**不要求编译通过**（编译闭环归 task073）。但也**禁止**明知会留错时绕过：所有接线以 17 树 bp 为依据。
- 权威依据是 17 树 bp（规则 B），chief 已预核实以下关键事实（直接采用）。

## chief 预核实事实（17 树）

1. `android_app "SystemUI"` 的 `static_libs: ["SystemUI-application"]`，`resource_dirs: []`，`enable_ksp`——`:app` 依赖换为 `:SystemUI-application`，`:app` manifest 改为**最小合并壳**（16 时代 1157 行完整 manifest 的角色已由 `SystemUI-application` 接管）。
2. `SystemUI-application` bp：`srcs: ["application/src/**/*.java|kt"]`，static_libs `["SystemUI-core", "com.android.systemui.bundle.phone_dagger", "dagger2"]`，`enable_ksp: true`（Dagger flags 见 bp 第 612–618 行）。Gradle：android.library 模块，`implementation(project(":SystemUI-core"))` + dagger 依赖 + KSP（接线仿 `:SystemUI-core` 现有写法，phone_dagger bundle 的 pods 已并入 `:SystemUI-core`）。
3. 17 版完整 manifest（`SystemUI-application/src/main/AndroidManifest.xml`）根标签带 `package="com.android.systemui"` 属性；**AGP 9 拒绝源 manifest 的 package 属性**（16 时代 app manifest 已剥除该属性）。必须剥除并按 ADR 0004 / `docs/issues/2026-08-07-conv-markup-spec.md` 用 CONV_DEL 标记（注释块记录被删字节），随后 `python3 tools/check_source_alignment.py --strict` 仍须 exit 0（MODIFIED 不卡，但修改必须进 issue 记录对账）。
4. `SystemUIClocks-CommonLib` bp：`srcs src/**`，`resource_dirs: ["res"]`，manifest 在模块根，static_libs `[PlatformAnimationLib, androidx.compose.runtime_runtime, androidx.compose.ui_ui, dagger2, jsr330, kotlinx_coroutines, monet]`，`libs: ["SystemUIPluginLib"]`，plugins dagger2-compiler。Gradle：android.library，`java.srcDirs("src")`+`res.srcDirs("res")`+`manifest.srcFile("AndroidManifest.xml")`，namespace `com.android.systemui.customization.clocks`（与 manifest package 一致），deps：`:SystemUI-animation`、`:SystemUI-monet`、`:SystemUI-plugin`、compose runtime/ui、coroutines、jsr330、dagger+ksp。`:SystemUI-customization` 加 `implementation(project(":SystemUI-clocks-common"))`。
5. `AccessibilityFloatingMenu-res` bp：纯 res（`accessibilitymenu/res`）+ manifest `AndroidManifest-floatingmenu.xml`（已按 AGP 惯例改名放入模块根，字节一致）。Gradle：android.library，namespace `com.android.systemui.accessibility.floatingmenu`，`res.srcDirs("res")`，无源码。`:SystemUI-res` 加 `implementation(project(":SystemUI-accessibility-floatingmenu-res"))`。
6. **新产物打包（扩展 tools/ 脚本，C2 风格）**：
   - **surfaceeffects 三库**：`frameworks/libs/systemui/surfaceeffects/{core,compose,view}` → `SurfaceEffectsCoreLib` / `SurfaceEffectsComposeLib` / `SurfaceEffectsViewLib`（`frameworks/libs/systemui/`，非 SystemUI 自有 → 规则 F 产物依赖；bp **无 resource_dirs**，源树无 res 目录 → **jar**，kotlin 产物在 `.../surfaceeffects/{core,compose,view}/<Target>/android_common/kotlin/*.jar`）。扩展 `tools/package_misc_jars.py`（或等价入口）产出 `libs/SurfaceEffectsCoreLib.jar` 等，带冻结指纹的既有风格；补/改对应 pytest。
   - **uilatencystats flags**：17 SystemUI-core static_libs 含 `uilatencystats_flags_core_java_lib`，定义在 `frameworks/base/services/core/java/com/android/server/uilatencystats/Android.bp`（产物目录 `out/soong/.intermediates/frameworks/base/services/core/java/com/android/server/uilatencystats/uilatencystats_flags/`）。扩展 `tools/package_aconfig_jars.py` 产出对应 jar。SystemUI 17 源码确有 import（如 `android.uilatencystats.UiLatencyStatsManager` 周边 flags）。
   - 17 源码新增的其他 flags import（`android.app.supervision.flags`、`android.companion.virtualdevice.flags`、`android.location.flags`、`android.view.flags`、`com.android.internal.camera.flags`、`com.android.internal.telephony.flags`、`com.android.media.flags`、`com.android.media.projection.flags`、`com.android.server.power.feature.flags`、`com.android.systemui.display.flags` 等）**不在本任务**——归 task073 由编译错误驱动补入。
   - `SystemUI-core/build.gradle.kts`：删除 `motion_tool_lib.jar`、`settingslib-selector-flags.jar` 依赖行；加入新打 jar 的 `files(...)` 依赖（surfaceeffects 三 jar、uilatencystats flags jar）。
7. catalog：`gradle/libs.versions.toml` 中 23 个本地 maven 族坐标 1.x → **2.0.0**（与 task071 的 `install_aar_to_maven.py` 坐标表一致；SettingsLib POM 的 17 条传递边也已是 2.0.0，核对同名同版）。
8. `:SystemUI-res` static_libs 17 版（主 bp 415–427 行）：`SystemUISharedLib, SystemUICustomizationLib, SettingsLib, WindowManager-Shell, leanback, slice-core, slice-view, dynamiccolors, AccessibilityFloatingMenu-res`。与现 build.gradle.kts 对照，唯一新增应为 floatingmenu-res 模块依赖；若发现其他漂移，按 17 bp 修正并记录。

## Global Constraints

- 单 Gradle 守护进程；构建前 `pkill -f "GradleDaemon" || true`（如空置）。
- 不 push；worker 分步 commit，commit message 英文。
- AOSP 树只读；临时文件放 `/tmp/task072/`。
- 不改 `SystemUI-*/src`、`SystemUI-*/res` 下任何 AOSP 镜像文件（唯一例外：§3 的 manifest package 属性 CONV 剥除）；不改 `tools/build_sysuisdk.py`、`tools/check_source_alignment.py`。
- `AGENTS.md` 允许两处编辑（用户已预批准）：§1.9 中 manifest 归属改为「完整 manifest 归 `:SystemUI-application`，`:app` 留最小合并壳」；§3.1 模块清单补三个新模块。
- `:app` 最小 manifest 需保留使合并成功的最小要素（根 `manifest` 标签；`sharedUserId`/`coreApp` 若原最小壳需要则留，由 worker 以 16 时代惯例和合并器要求判断），并在 issue 文档记录其形式。
- 运行验证仅限：`./gradlew help`、pytest、对齐工具。**禁止**尝试 `:app:assembleDebug`（归 task073）。

## File Map

- 读写：`settings.gradle.kts`、`gradle/libs.versions.toml`、`app/build.gradle.kts`、`app/src/main/AndroidManifest.xml`、`SystemUI-application/`（新建 build.gradle.kts；manifest CONV 剥除）、`SystemUI-clocks-common/`（新建 build.gradle.kts）、`SystemUI-accessibility-floatingmenu-res/`（新建 build.gradle.kts）、`SystemUI-core/build.gradle.kts`、`SystemUI-res/build.gradle.kts`、`SystemUI-customization/build.gradle.kts`、`AGENTS.md`（§1.9、§3.1）、`tools/package_misc_jars.py`、`tools/package_aconfig_jars.py`、`tools/tests/`、`libs/`（新 jar 产出）
- 新建文档：`docs/issues/2026-08-28-c4-gradle-wiring.md`；更新 `docs/orchestration/STATE.md`

## 步骤（checkbox）

- [ ] P0 tools：打包 surfaceeffects 三 jar + uilatencystats flags jar（脚本 + 测试），`uv run pytest tools/tests -q` 全绿。
- [ ] P1 settings 注册三模块；写三个 build.gradle.kts。
- [ ] P2 catalog 23 族升 2.0.0；`:SystemUI-res` 加 floatingmenu-res 依赖；`:SystemUI-customization` 加 clocks-common 依赖；`:SystemUI-core` 删两退役 jar、加新 jar 依赖。
- [ ] P3 `:app` 依赖换 `:SystemUI-application`；app manifest 最小化；`SystemUI-application` manifest 剥 package 属性 + CONV 标记。
- [ ] P4 验证：`pkill -f GradleDaemon; ./gradlew help` 配置解析通过；`python3 tools/check_source_alignment.py --strict` exit 0；pytest 复绿。
- [ ] P5 AGENTS.md 两处编辑；issue 文档（含逐条 bp 依据摘录、manifest 壳形式、CONV 记录、移交 task073 清单：新 flags、view_capture proto keep 规则、编译错误预期面）；STATE.md。

## 验收（Acceptance）

- `./gradlew help` 成功（settings/配置解析通过，三新模块被识别）。
- 三个新 build.gradle.kts 依赖与 17 bp static_libs 对应（逐条摘录对照进 issue 文档）。
- catalog 无 1.x 残留指向本地 maven；`libs.versions.toml` 里 23 族全 2.0.0。
- `check_source_alignment.py --strict` exit 0；pytest 全绿；新 jar 由脚本产出且入库。
- `git status` 干净，commit 分步清晰，未 push。

## 五字段

- **Authority**: self-commit；never push；遇规则 H 情形停下来问 chief
- **Allowed Paths**: `settings.gradle.kts`、`gradle/`、`app/`、`SystemUI-application/`、`SystemUI-clocks-common/`、`SystemUI-accessibility-floatingmenu-res/`、各模块 `build.gradle.kts`、`AGENTS.md`、`tools/`（除 `build_sysuisdk.py`、`check_source_alignment.py`）、`libs/`、`docs/issues/2026-08-28-c4-gradle-wiring.md`、`docs/orchestration/STATE.md`、`/tmp/task072/`
- **Forbidden Paths**: `SystemUI-*/src/**`、`SystemUI-*/res/**`（application manifest 的 CONV 剥除除外）、`docs/orchestration/CHARTER.md`、git push、`:app:assembleDebug` 等编译任务
- **Acceptance**: `./gradlew help` 通过 + catalog 全 2.0.0 + 对齐门与 pytest 绿
- **Reports To**: chief（herdr agent `task072`）

## 模型

joycode GLM-5.3。
