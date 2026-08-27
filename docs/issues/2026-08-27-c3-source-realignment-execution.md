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
| P1 | 删 EXTRA 628+219（`git rm` 847 文件；提交 `7e9999a5`） | 1989 | 34 | **0** | 2222 | 1 | 577 | **0** | 830 |
| P2 | 移 MISPLACED 34（`git mv`；提交 `087b397c`） | 1989 | **0** | 0 | 2236（+14：移位后内容与 17 有漂移的文件转为 MODIFIED，待 P4 覆盖；其余 20 个字节一致） | 1 | 577 | 0 | 830 |
| P3 | 拷 MISSING 1989+577（`cp --parents` 字节保留；提交 `bdf2dba5`+`30fe0026`；含 3 个新模块目录与 3 个模块 manifest） | **0** | 0 | 0 | 2236 | **0** | **0** | 0 | 830 |
| P4 | 覆 MODIFIED 2236+830（`cp` 覆盖 + 逐文件字节校验全一致；提交 `aa77057a`；`app/proguard_common.flags` → 17 版 72 行） | 0 | 0 | 0 | **0** | 0 | 0 | 0 | **0** |
| P5 | CONV 重标（提交 `68df52a1`） | 0 | 0 | 0 | 1（CONV_MOD 白名单 kt） | 0 | 0 | 0 | 86（CONV_DEL 白名单 res-product strings.xml） |
| P6 | 验收：`--strict` 退出码 0；MISSING/MISPLACED/EXTRA/APP 全 0；git status 无 untracked | **0** | **0** | **0** | 1 | **0** | **0** | **0** | 86 |

MODIFIED 终态 = 1 + RES-MODIFIED 终态 = 86，均为白名单授权改动（CONV 标记），与预期完全一致。

## 执行细节记录

- 所有批量操作脚本在 `/tmp/task070/`（extract.py / p1 / p2 / p3 / p4 / p5），均 `uv run`，不入库；逻辑已在本文档记录。
- P3 拷入 2566 文件 + 3 个模块 manifest；新模块：`SystemUI-application`（4 src + `src/main/AndroidManifest.xml` 1338 行）、`SystemUI-clocks-common`（21 src + 9 res + manifest，共 31 文件）、`SystemUI-accessibility-floatingmenu-res`（130 res + manifest，共 131 文件）。
- 6 个 AIDL（MediaProjectionCaptureTarget、IScreenRecordingService×2、ScreenRecordingParameters、ILauncherProxy）+ 1 个 proto（motion_cues.proto）已拷入核对。
- `res/flag(com.android.systemui.status_icons_in_compose_refresh)/` 15 文件目录名原样保留（决策 6，AAPT2 消费能力由 C4 验证）。
- floatingmenu manifest：按 brief File Map 落在 `SystemUI-accessibility-floatingmenu-res/AndroidManifest.xml`（源为 AOSP `AndroidManifest-floatingmenu.xml`），“原文件名保留”理解为不改动 AOSP 源侧文件名；C4 接线时如需改名/移位再处理。


## 白名单处理

### UncaughtExceptionPreHandlerManager.kt（CONV_MOD × 2）

判断依据（P4 执行时核实）：

1. AOSP 17 版本直接调用 `Thread.getUncaughtExceptionPreHandler()` / `Thread.setUncaughtExceptionPreHandler(...)`（注意：是 `Thread` 而非 brief 里笔误的 `ActivityThread` 类路径）。
2. AOSP 17 中这两个方法仍为 `@hide`：`libcore/ojluni/src/main/java/java/lang/Thread.java` L3311/L3325，且 `libcore/ojluni/annotations/hiddenapi/java/lang/Thread.java` L299/L305 仍列为 hiddenapi（会从 stub 剔除）。
3. 本项目 SysUISdk `android.jar` 的 `java.lang.Thread` 经 `javap -p` 实测**无** prehandler 方法（grep 无匹配）。

结论：17 **未提供**等价 public API → 按白名单指令拷 17 版本后重放原 CONV_MOD 反射 workaround（两处），标记升级为 `CONV_MOD BEGIN [task070]`，注释内记录判断依据与本次 issue 文档引用。文件现为全树唯一 src MODIFIED。

### 86 个 res-product strings.xml CONV 重标

- 重标范围：86 个 `SystemUI-res/res-product/values*/strings.xml`（3 个 fr-rCA-feminine/masculine/neuter 新文件只含 `product="default"`，无需重标；`values/config.xml` 非 strings.xml 不在 brief 范围）。
- 重标变体集：**tv / tablet / device / desktop**（共 5806 处：desktop 3230、tablet 1717、device 773、tv 86）。
- **与 brief 文字清单（tv/tablet/desktop）的差异及理由**：brief 变体清单漏列 `device`，但用户 2026-08-07 批准的原 2237 处标记实际覆盖 tv/tablet/device（`git show aa77057a^` 计数：device 8+tablet 18+tv 1 in values/strings.xml，全树 2237）；且 17 的 device 条目（773 处）与 default 同名共存，AAPT2 不支持 product 属性 → 不标会直接产生重复资源。故按既有授权方案全非 default 变体重标。**此差异已向 architect 报告，如需缩窄为 tv/tablet/desktop 可机械撤销 device 标记。**
- `values/config.xml` 的 3 个 `<bool>`（default/tablet/desktop）保持原状未标（与旧基线一致；旧工具只标 `<string>`）；这是 C4 需要注意的既有条件。
- 标记格式：`<!-- CONV_DEL BEGIN [task070] reason: product-variant unsupported by AGP -->` / 原行字节保留在注释内 / `<!-- CONV_DEL END -->`；90 个 xml 全部通过 ElementTree 解析（格式合法）。
- 重标后 RES-MODIFIED = 86，即这 86 个文件，符合预期（MODIFIED 不卡 strict）。

## 待办移交 C4

1. **新模块接线**（本任务只建了文件，未建任何构建脚本、未注册 settings）：
   - `:SystemUI-application`：`src/com/...` 4 文件 + `src/main/AndroidManifest.xml`（1338 行完整 manifest）；`:app` 换依赖（bp：android_app 依赖 SystemUI-application 而非 SystemUI-core）。
   - `:SystemUI-clocks-common`：21 src + 9 res + manifest，自有 R namespace。
   - `:SystemUI-accessibility-floatingmenu-res`：res-only module（130 res + manifest）。
2. `app/src/main/AndroidManifest.xml`（1157 行旧版）去留由 C4 决定（本任务按 brief 未动）。
3. AIDL 6 个 + proto 1 个的 sourceSet 管线（`motion_cues.proto` 为新增）。
4. SurfaceEffects 三库（Core/View/Compose）AAR 化并接入 `:SystemUI-animation` / `:SystemUI-core`（决策 4；24 个 surfaceeffects EXTRA 已删）。
5. SystemUI-res 新增 static_libs 补齐：dynamiccolors、AccessibilityFloatingMenu-res（源码 module 已建）、android.net.platform.flags-aconfig、uilatencystats_flags（WindowManager-Shell 已有坐标）。
6. `res/flag(...)` 限定目录 15 文件与 res-product fr-rCA 新变体的 AAPT2 消费验证（决策 6/7）。
7. `res-product/values/config.xml` 的 3 个 `<bool>` product 变体未标 CONV（既有状态），C4 若遇重复资源错误需处理。
8. `app/proguard_common.flags` 已更新到 17（72 行）；另两个 proguard 文件字节一致未动。
9. C4 起步前建议：`device` 变体标记范围确认（见上文差异报告）。

## 验收证据

- `uv run python3 tools/check_source_alignment.py --strict` → 输出“完成。”，`echo $?` → **0**
- `--summary`：MISSING=0、MISPLACED=0、EXTRA=0、MODIFIED=1（白名单 CONV_MOD kt）、APP=0、RES-MISS=0、RES-EXTRA=0、RES-MODIFIED=86（白名单 CONV_DEL res-product）
- `git status --short` → 空（无 untracked）
- 提交序列：`7e9999a5`（P1）→ `087b397c`（P2）→ `bdf2dba5`+`30fe0026`（P3）→ `aa77057a`（P4）→ `68df52a1`（P5）
- 本任务未运行 Gradle（按 brief 约束，C4 负责）
