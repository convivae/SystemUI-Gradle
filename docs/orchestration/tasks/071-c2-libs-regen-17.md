# Task 071 — C2 libs/ 全删 + AOSP-17 适配 + 脚本再生

## 背景

- AOSP 树 `android-17.0.0_r1` 已全量构建（C1 完成）；C3 源码重对齐已完成（task070，对齐门全 0）。
- ADR 0007 Phase C 验收命题：**git clone 后仅凭 AOSP 树 + tools/ Python 脚本可从零复现，无一手工产物**。本任务执行「删光 libs/ 三类 → 脚本再生」并完成 16→17 的打包脚本适配。
- chief 预勘察（已核实，直接采用）——17 树产物漂移四项：
  1. **iconloader 结构重构**：17 拆为 `iconloader`（src_full_lib 2 个 Java 门面：IconFactory/SimpleIconCache）+ `iconloader_base`（src/ 43 文件 java+kt + res + R.txt）。项目需要的是消费闭包，AAR 必须合并：`iconloader/javac` + `iconloader_base/javac` + `iconloader_base/kotlin`；res/manifest 源树路径不变（`frameworks/libs/systemui/iconloaderlib/{res,AndroidManifest.xml}` 均存活）；R.txt 改取 `iconloader_base/android_common/R.txt`。注意 `iconloader/android_common/kotlin/` 在 17 **不存在**（旧冻结路径）。
  2. **WindowManager-Shell-proto 上游删除**：17 只剩 `WindowManager-Shell-lite-proto`；proto/protolog 类（ProtoLogImpl、ProtoLogController 等）已并入 `WindowManager-Shell` 主 jar（实测主 javac jar 含此类）。脚本删除该条目即可，主 AAR 吸收。
  3. **WifiTrackerLib manifest 移位**：源树 `frameworks/opt/net/wifi/libs/WifiTrackerLib/AndroidManifest.xml` 已删（17 bp 无 manifest 行）；改用 soong 生成物 `out/soong/.intermediates/frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLib/android_common/GeneratedManifest.xml`（已验存，package="com.android.wifitrackerlib.nores"）。res/R.txt 仍走 WifiTrackerLibRes（存活）。
  4. **motiontoollib 上游删除**：`frameworks/libs/systemui/motiontoollib` 整目录消失，17 全 AOSP 无 MotionToolManager 类，SystemUI 17 无任何 motiontool 引用。`libs/motion_tool_lib.jar` **不再产出**；`package_viewcapture_motiontool_jars.py` 改为只产 view_capture.jar（view_capture 目标路径在 17 存活）。C4 将从 build.gradle.kts 移除该依赖（本任务不碰 gradle）。
- 其余脚本冻结输入全部存活（misc/monet/compilelib/aconfig/build_sysuisdk 验存 8/8；viewcapture 2/4）。
- **范围纪律**：17 源码新增的 aconfig flags 需求（android.app.supervision/location/view/telephony/media/camera/power/companion 等 import）**不在本任务**——留给 C4 由编译错误驱动逐个补入 package_aconfig_jars.py。本任务只再生 16 功能等价集。

## Global Constraints

- **先改脚本、后删库**：脚本适配 + pytest 全绿后，才执行 `git rm -r libs/`。
- 删除前对 libs/ 全部文件做 sha256 快照（`/tmp/task071/pre-delete.sha256`），再生后逐文件对比出 **16→17 漂移报告**（字节相同/漂移/新增/消失四类计数 + 抽样明细）。漂移是预期，**不要求字节一致**（ADR 0007 验收形态）。
- **版本坐标纪律（AGENTS §3.2.4）**：maven AAR 内容随 vintage 漂移，`install_aar_to_maven.py` 坐标表全族 1.x → **2.0.0**（major = AOSP vintage 16→17），旧版本目录随全删消失。`libs.versions.toml` catalog 更新归 C4（本任务不动，移交清单注明 catalog 暂指向已退役 1.x）。
- Python 一律 `uv run`；临时脚本/快照放 `/tmp/task071/`。
- 不跑 Gradle、不改 `*.gradle.kts`/`libs.versions.toml`/`settings.gradle.kts`、不 push。
- AOSP 树只读（`/home/conv/myspace/aosp`）。
- 再生顺序（依赖序）：`package_misc_jars` → `package_monet_jar` → `package_viewcapture_motiontool_jars`（改名逻辑后）→ `package_compilelib_jars` → `package_aconfig_jars` → `package_aosp_aar --all` → `install_aar_to_maven`。
- 任何脚本对不存在输入的报错视为适配缺口：**禁止跳过或伪造**，回到脚本修正路径后重跑（规则 P 精神）。
- `build_sysuisdk.py` 不在本任务（SDK 不在 libs/；八输入已验存，C5 前重跑）。

## File Map

- 修改：`tools/package_aosp_aar.py`（iconloader closure、删 WM-Shell-proto 条目、WifiTrackerLib manifest）、`tools/package_viewcapture_motiontool_jars.py`（去 motiontool）、`tools/install_aar_to_maven.py`（坐标 2.0.0）
- 修改对应测试：`tools/tests/test_package_aosp_aar.py`（18 个 16 时代失败用例按 17 事实修正——iconloader closure 类数、WM-Shell-proto 断言移除、SettingsLib 闭包类数漂移等，**断言新数字必须实测自 17 产物**，不得照抄旧数字）
- 可能需改：`tools/tests/test_install_aar_to_maven.py`（版本号断言）
- 重生：`libs/`（根 jar + `libs/aars/` + `libs/maven/` 全部内容）
- 文档：`docs/issues/2026-08-27-c2-libs-regen-17.md`、`docs/orchestration/STATE.md` task071 行

## 步骤（checkbox）

### P0 脚本适配
- [ ] `package_aosp_aar.py`：iconloader 条目按预勘察 1 重构（三 jar 合并 + R.txt 改源）；删 WindowManager-Shell-proto 条目；WifiTrackerLib manifest 改 GeneratedManifest.xml 路径。
- [ ] `package_viewcapture_motiontool_jars.py`：移除 motiontool 部分，改名语义只产 view_capture.jar（脚本名与文档字符串同步修正；文件名不改，保留 git 历史）。
- [ ] `install_aar_to_maven.py`：坐标表全族 2.0.0。
- [ ] `uv run pytest tools/tests -q` 全绿（修正 16 时代断言为 17 实测值）。

### P1 快照 + 全删
- [ ] `find libs -type f | sort | xargs sha256sum > /tmp/task071/pre-delete.sha256`；统计三类文件数（根 jar 28 / aars 29 / maven aar 23 应与删除数吻合）。
- [ ] `git rm -r libs/`（commit 1）。

### P2 再生
- [ ] 按 Global Constraints 顺序跑 7 个脚本，全部零报错。
- [ ] `git add libs/`（commit 2）。

### P3 漂移报告
- [ ] 再生后 sha256 对比：统计 byte-identical / drifted / new（motion_tool_lib 消失）/ gone 四类。
- [ ] 抽样验证 5 个漂移 jar（unzip 类数对比 16 vs 17，记录进 issue 文档）。
- [ ] `uv run pytest tools/tests -q` 复跑全绿。

### P4 收尾
- [ ] issue 文档（背景/适配四项/操作日志/漂移报告/C4 移交清单）。
- [ ] STATE.md task071 行。
- [ ] 英文 commit（P0 脚本适配 / P1+P2 删与再生 / P3 文档 分次提交）。
- [ ] 四段式完成报告。

## 验收（Acceptance）

- `uv run python3 tools/tests -q`（全 tools/tests）全绿。
- libs/ 中每个文件均由脚本产出（worker 报告逐一列来源脚本）；无手工拷贝。
- 漂移报告四类计数完整；motion_tool_lib.jar 不存在。
- `git status` 干净；本地 commit，不 push。

## 五字段

- **Authority**: self-commit（分步；**never push**）
- **Allowed Paths**: `tools/package_*.py`、`tools/install_aar_to_maven.py`、`tools/tests/`、`libs/`、`docs/issues/2026-08-27-c2-libs-regen-17.md`、`docs/orchestration/STATE.md`、`/tmp/task071/`
- **Forbidden Paths**: `*.gradle.kts`、`gradle/`、`settings.gradle.kts`、`SystemUI-*/`、`app/`、`AGENTS.md`、`tools/check_source_alignment.py`、`tools/build_sysuisdk.py`、`git push`
- **Acceptance**: pytest 全绿 + 漂移报告 + libs/ 全部脚本产出可追溯
- **Reports To**: chief（herdr agent `task071`）

## 模型

joycode GLM-5.3。
