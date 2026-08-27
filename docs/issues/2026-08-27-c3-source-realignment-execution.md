# Task 070 — C3 源码重对齐执行（SystemUI-17 整树重刷）

- 日期：2026-08-27
- 任务简报：`docs/orchestration/tasks/070-c3-source-realignment-execution.md`
- 前置调研：`docs/architecture/2026-08-27-sysui17-realignment-panorama.md`（task069）
- 对照基准：AOSP `frameworks/base` @ `94b4c163b7`（`android-17.0.0_r1`）
- 性质：批量文件对齐（删 EXTRA → 移 MISPLACED → 拷 MISSING → 覆 MODIFIED → CONV 重标）。不跑 Gradle、不改任何 `*.gradle.kts`、不动 `libs/`、不 push。

## 冻结基线（开工前）

`uv run python3 tools/check_source_alignment.py --summary`：

| 计数器 | 值 |
|---|---|
| MISSING | 1989 |
| MISPLACED | 34 |
| EXTRA | 628 |
| MODIFIED | 2222 |
| APP | 1 |
| RES-MISS / RES-EXTRA / RES-MODIFIED | 577 / 219 / 830 |

结构化数据提取：`/tmp/task070/extract.py`（临时脚本，不入库）导入 `tools/check_source_alignment.py` 纯函数导出 JSON，与工具输出数字一致（1989/34/628/2222/1/577/219/830）。

## res EXTRA 84 个 locale 文件抽查（P1 前置要求）

- brief 要求：删除前抽查 1-2 个 locale，确认 17 里 `shared/biometrics/res` 同 locale 文件覆盖相同 key。
- 实际抽查：`values-de`、`values-ja`、`values-zh-rCN` 三个 locale。
- **发现（修正预研报告 §1.5 的归因）**：
  - 84 个 locale EXTRA 文件的真实 basename 是 `strings_car.xml`（Car SystemUI 遗留），**不是**主干 `strings.xml`；
  - AOSP 17 的 `res/values-*/strings.xml` 主干翻译**仍然存在**（如 `res/values-de/` 下有 `strings.xml` + `tiles_states_strings.xml`），预研报告"17 把 res 主干翻译删除/迁移"的表述有误——被删的是本项目多拷进来的 `strings_car.xml`；
  - `shared/biometrics/res/values-*/strings.xml` 仅含 4 个 `udfps_accessibility_touch_hints_*` key，与项目 res 主干 1464 个 key **零重叠**（重叠 0）。
- 结论：`strings_car.xml` 属"项目有、AOSP 17 全无"的真 EXTRA（与工具判定一致），删除正确；删除依据从"翻译归属搬家"修正为"car 项目遗留文件"。主 `strings.xml` 翻译文件不在删除集内（其中部分是 MODIFIED，走 P4 覆盖）。

## 操作日志（数字演变表）

| 步骤 | 操作 | MISSING | MISPLACED | EXTRA | MODIFIED | APP | RES-MISS | RES-EXTRA | RES-MOD |
|---|---|---|---|---|---|---|---|---|---|
| 基线 | — | 1989 | 34 | 628 | 2222 | 1 | 577 | 219 | 830 |
| P1 | 删 EXTRA 628+219 | (待填) | | | | | | | |
| P2 | 移 MISPLACED 34 | | | | | | | | |
| P3 | 拷 MISSING 1989+577 | | | | | | | | |
| P4 | 覆 MODIFIED 2222+830 | | | | | | | | |
| P5 | CONV 重标 | | | | | | | | |
| P6 | 验收 | 0 | 0 | 0 | >0 允许 | 0 | 0 | 0 | >0 允许 |

（各步骤执行后回填实际数字）

## 白名单处理

### UncaughtExceptionPreHandlerManager.kt（CONV_MOD × 2）
（P4 执行时填写判断依据）

### 86 个 res-product strings.xml CONV 重标
（P5 执行时填写实际重标数量）

## 待办移交 C4

（收尾时填写：新模块 build.gradle.kts、settings 注册、AIDL/proto sourceSet、SurfaceEffects AAR、SystemUI-res 新增 static_libs、:app 壳去留等）
