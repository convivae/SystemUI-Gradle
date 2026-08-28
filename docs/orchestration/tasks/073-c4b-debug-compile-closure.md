# Task 073 — C4b：编译闭环（`:app:assembleDebug` 恢复绿）

## 背景

- C4a（task072，review-PASS）已完成接线：16 模块注册、catalog 2.0.0、依赖增删、`:app` 换 `:SystemUI-application`、四个新产物入库。配置解析绿，但**尚未编译过**。
- 本任务目标：**`:app:assembleDebug` BUILD SUCCESSFUL**。Release/R8 归 task074；runtime 归 C5。
- 预期错误面（task072 issue `docs/issues/2026-08-28-c4-gradle-wiring.md` §6 移交清单）：
  - kairos（60 文件 import）、personalcontext（9）、12 个新 flags 包、SerialPortAccessDialog、mechanics-compose、legacy-androidx 等 bp 未接线项、view_capture proto、dagger KSP flags、首次 manifest 合并（1338 行 library manifest 并入 app 壳）。

## chief 预核实事实（17 树，直接采用）

1. **kairos = tier① 源码模块（规则 S）**：bp `java_library "kairos"` 位于 `packages/SystemUI/utils/kairos/Android.bp`（src 63 个 kt，static_libs 仅 kotlin-stdlib；`kairos-test` 不进生产图）。16 时代被判 test-only 未入库是误判，17 已是 SystemUI-core 生产依赖。**做法**：拷贝 `utils/kairos/src`（63 kt）为新模块 `:SystemUI-utils-kairos`（纯 Kotlin JVM 模块，形态仿 `:SystemUI-plugin-core`；无 res、无 manifest），core 加 `implementation(project(":SystemUI-utils-kairos"))`。**同时**把 `utils/kairos/src` 加入 `tools/check_source_alignment.py` 的 src 映射（这是对齐工具本任务唯一授权的新增编辑；加完后 `--strict` 须仍然全 0/白名单）。
2. **personalcontext_ace_visualizer = tier② AAR（含 res）**：定义在 `frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/visualizer/Android.bp`（源树 111 kt/java，visualizer 子树带 res；SystemUI-17 import 面含 `com.android.personalcontext.ace.visualizer.compat.*`）。扩展 `tools/package_aosp_aar.py` 配置产出（参照 dynamiccolors 先例：Task 059 直接 AAR 形状，单 consumer core）。
3. **SerialPortAccessDialog = tier② AAR（含 res）**：定义在 `frameworks/base/libs/serial/accessdialog/Android.bp`（5 个源文件 + res）。同上经 packager 产出直接 AAR。
4. **mechanics / mechanics-compose = tier② jar（无 res）**：`frameworks/libs/systemui/mechanics/{,compose}`（合计 92 源文件，无 res 目录）。扩展 `tools/package_misc_jars.py` 产出 jar（冻结指纹风格）。
5. **新 flags 包**（`android.location.flags` 8 文件、`com.android.media.flags` 7、`com.android.systemui.display.flags` 6、`android.companion.virtualdevice.flags` 4、`com.android.internal.camera.flags` 3、`android.app.supervision.flags`/`android.view.flags`/`com.android.internal.telephony.flags` 各 2、`com.android.media.projection.flags`/`com.android.server.power.feature.flags` 各 1）：扩展 `tools/package_aconfig_jars.py`（优先沿用 task071 的 `extract_aggregate_subset()` 聚合分片机制；找不到产物的族如实报错，不伪造）。**编译错误驱动**：先编译看实际缺口再补，不预铺。
6. 其余 bp 未接线项（`androidx.legacy_support-v4`、`legacy_legacy-preference-v14`、`arch.core_core-runtime`、`lifecycle-extensions`、`autofill`、`graphics-core`、`com_android_server_accessibility_flags_lib`、`aconfig_settings_flags_lib`、`uilatencystats_flags` 已接）：编译错误驱动判定（多数是传递闭包已覆盖，无需单独引）。

## 编译错误处理纪律（规则映射）

| 错误类别 | 处理 |
|---|---|
| 缺 tier② 产物 | 扩展 tools 打包脚本产出（jar/AAR），冻结指纹 + pytest |
| 缺 tier① 源码 | 新源码模块/目录拷贝（如 kairos），同步对齐工具映射 |
| res 缺失 | AOSP 来源 AAR/源 res（规则 R）；**禁止**凭空生成 res |
| 需要改 SystemUI-*/src 内容 | ADR 0004 CONV 标记；改前先跑对齐工具确认基线；每处都进 issue 对账 |
| 需要 stub | **禁止**——停下向 chief 汇报（规则 H/P） |
| API 漂移（16→17 源码级） | 属源码对齐问题的按 CONV 纪律处理；属 SysUISdk 缺 API 的报告 chief（禁止自行拷 framework 源码，规则 F） |

## Global Constraints

- 单 Gradle 构建；长时间不用时 `pkill -f GradleDaemon`（30G RAM）。
- 不 push；worker 分步 commit（英文 message）。
- AOSP 树只读；临时文件 `/tmp/task073/`。
- `tools/build_sysuisdk.py` 禁改；`tools/check_source_alignment.py` 仅允许 §1 授权的 kairos 映射新增。
- 每轮编译后记录错误数与分类（诊断信息，不是门槛——规则 I：整体向前推进即可）。
- 主线 checkout 上工作（无 worktree）。

## File Map

- 读写：`SystemUI-*/build.gradle.kts`、`settings.gradle.kts`、`tools/package_misc_jars.py`、`tools/package_aconfig_jars.py`、`tools/package_aosp_aar.py`、`tools/tests/`、`tools/check_source_alignment.py`（仅 kairos 映射）、`libs/`、`SystemUI-utils-kairos/`（新建）、必要时 `SystemUI-*/src` 的 CONV 标记改动、`gradle/libs.versions.toml`（如新增官方坐标）
- 新建文档：`docs/issues/2026-08-28-c4b-debug-compile-closure.md`；更新 `docs/orchestration/STATE.md`

## 步骤（checkpoint 提交，允许循环多轮）

- [ ] P0 kairos 源码模块落地（拷贝 + build 文件 + 对齐工具映射 + settings 注册 + core 依赖）
- [ ] P1 新 tier② 产物打包（ace AAR、serial AAR、mechanics×2 jar）+ pytest
- [ ] P2 编译循环：`./gradlew :app:assembleDebug`，按错误分类逐个根因处理（一次一个根因），每轮记录错误数演变
- [ ] P3 验收：`:app:assembleDebug` BUILD SUCCESSFUL；`check_source_alignment.py --strict` exit 0；pytest 全绿
- [ ] P4 issue 文档（错误数演变表、每个新产物的 bp 依据、CONV 对账、移交 task074 清单：release/R8 预期面）；STATE.md

## 验收（Acceptance）

- `./gradlew :app:assembleDebug` **BUILD SUCCESSFUL**（APK 产出）。
- `python3 tools/check_source_alignment.py --strict` exit 0；pytest 全绿。
- 新产物全部由 tools 脚本产出（含冻结指纹），删除重跑字节一致。
- git status 干净，commit 分步，未 push。

## 五字段

- **Authority**: self-commit；never push；规则 H 情形（stub/伪造 res/改 AGENTS.md 核心规则/SysUISdk 需重建）停工向 chief 汇报
- **Allowed Paths**: 上列 File Map + `docs/issues/2026-08-28-c4b-debug-compile-closure.md`、`docs/orchestration/STATE.md`、`/tmp/task073/`
- **Forbidden Paths**: `tools/build_sysuisdk.py`、`AGENTS.md`、`docs/orchestration/CHARTER.md`、git push、release 构建（归 task074）、模拟器/设备（归 C5）
- **Acceptance**: assembleDebug BUILD SUCCESSFUL + 对齐门/pytest 绿 + 产物可复现
- **Reports To**: chief（herdr agent `task073`）

## 模型

joycode GLM-5.3。
