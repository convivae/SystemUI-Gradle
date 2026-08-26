# Task 064 — 关闭 15 个再生性 GAP（Phase C 前置工程）

## Goal

让 libs/ **每一个**保留产物都能从 AOSP `out/` 产物脚本化再生。当前 15 个 jar 是
2026-07 时代手工 cp 的（审计证据：`docs/architecture/2026-08-26-tools-scripts-inventory-audit.md` §7）。
这是用户"任何人可从 AOSP 复现全链"目标的直接阻塞点。

## Authority

- 可新增/修改 `tools/` 下脚本与 `tools/tests/` 测试
- **不得修改** `libs/` 下任何现存 jar（它们是基准；你的脚本产出物必须与之比对验证）
- 不得修改任何 `*.kts`/`*.toml` wiring
- 不得运行 Gradle（pytest 足够验证；构建门不适用本任务）

## 工作项

### W1. Quick win：3 个 aconfig flags jar（扩 CONFIGS）

`tools/package_aconfig_jars.py` CONFIGS 补 3 条：
1. `settingslib-flags.jar`（wired core:180 compileOnly）
2. `settingslib-media-flags.jar`（wired core:182 implementation）
3. `device-state-flags.jar`（wired core:256 implementation；**注意** CONFIGS 里已有
   `device-state-feature-flags`=android.hardware.devicestate.**feature**.flags 是另一个族，勿混淆）

先在 AOSP out/ 里找到对应 `*-aconfig-java` Soong 产物路径，确认模块名与 javac jar 位置，
再按既有五类校验模式补条目。**验证**：`--only <name>` 或单独运行生成后 sha256 与现存
`libs/*.jar` 一致（若不一致，diff 取证并报告——可能当年手工版含杂类，如实报告即可）。

### W2. 新提取脚本：12 个手工 jar

新建 `tools/package_misc_jars.py`（或按语义拆分，你判断，命名要表意）：
从 AOSP `out/soong/.intermediates/`（或 out/target/common/obj，视产物）按**冻结映射**
提取以下 jar。每个条目：AOSP soong 模块名 / intermediates 路径 / 目标 libs 路径 /
sha256 验证。模式参考 `tools/build_sysuisdk.py` 的八输入冻结映射（确定性、幂等、
`--aosp-root` 参数走 `tools/aosp_paths.py`）。

清单（12 个；AOSP 树在 `/home/conv/myspace/aosp`，用 soong 模块名定位 intermediates）：
1. `framework.jar` — `frameworks/base/framework` turbine-combined（与 build_sysuisdk 冻结映射同源；但注意 libs/framework.jar 是**当年手工 cp 的版本**，先 sha 比对，若不一致以报告为准）
2. `framework-statsd.jar`
3. `android.car.jar`
4. `android_module_lib_stubs_current.jar` — 模块 `android_module_lib_stubs_current`（frameworks/base 或 libcore 相邻，实查）
5. `SystemUI-proto.jar` — SystemUI proto soong 产物（frameworks/base/packages/SystemUI 内 proto 模块）
6. `SystemUI-statsd.jar` — 同上（statsd 相关模块）
7. `SystemUI-tags.jar` — 同上（SystemUI-tags）
8. `contextualeducationlib.jar` — `frameworks/libs/systemui/contextualeducationlib`
9. `msdl.jar` — `frameworks/libs/systemui/msdllib`（模块 msdl）
10. `PlatformMotionTestingComposeValues.jar` — SystemUI animation 相关（实查 animation/lib 或 motion 模块）
11. `keepanno-annotations.jar` — `prebuilts/r8/keepanno-annotations` combined（与 build_sysuisdk 冻结映射同源路径）
12. `libs/prebuilts/tracinglib-platform.jar` — `frameworks/libs/systemui/tracinglib/core`（chief 已溯源；生成后若需清洗走 clean_prebuilts.py 既有流程，你的脚本只负责提取）

**每个产物的验证纪律**：生成到**临时目录**（如 `out/`、`/tmp/gap-check/`），与现存
`libs/` 文件 sha256 比对，结果入表：`MATCH`（理想，字节一致）/ `DIFF`（列出差异摘要：
类数、大小、是否多/少条目；不覆盖 libs/ 现存文件，仅报告）。DIFF 不算失败——当年手工
版本可能本就不精确，你的报告为 Phase C 提供"以脚本产出为准还是以现存为准"的决策输入。
**特别注意 framework.jar**：它被 12 个 module compileOnly + root build.gradle.kts JavaCompile
classpath 引用，版本漂移敏感；DIFF 时必须精确列出 class 集差异。

### W3. 硬编码路径治理

`tools/aosp_paths.py` 单一来源改造（用户规则 2026-08-25）：
- `package_aosp_aar.py`、`package_compilelib_jars.py`、`check_source_alignment.py`：加 `--aosp-root` 参数并默认走 aosp_paths
- `package_monet_jar.py`、`package_viewcapture_motiontool_jars.py`：default 改走 aosp_paths
- **不改变行为**：`git diff` 下只有参数解析与路径来源变化；各脚本既有测试必须全绿

### W4. 测试

- 新脚本：单测覆盖冻结映射完整性、aosp_paths 集成（仿 test_package_aconfig_jars.py 的单源断言）
- 全套 `uv run pytest tools/tests/ -q` 全绿

## Output

报告 `docs/architecture/2026-08-26-regeneration-gap-closure.md`：
15 个产物逐一的"再生脚本 + sha256 比对结果表 + DIFF 分析"；W3 改造清单；
新脚本使用说明（Phase C runbook 会引用）。一行 log.md。
commit 英文、本地、不 push。四段式完成报告。

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
