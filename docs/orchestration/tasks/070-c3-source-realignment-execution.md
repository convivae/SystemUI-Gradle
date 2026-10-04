# Task 070 — C3 源码重对齐执行（SystemUI-17 整树重刷）

## 背景

- AOSP 树已切 `android-17.0.0_r1`（frameworks/base `94b4c163b`）并完成全量构建。
- 预研报告（task069，**必读**）：`docs/architecture/2026-08-27-sysui17-realignment-panorama.md`
- 用户已批准 7 项决策（详见预研报告 §5 + 本 brief「已裁决事项」）。
- 对齐工具映射已扩展（commit `25c7f61f`），新基线已冻结（见「验收」）。
- 本任务**只做源码/资源文件对齐**，不碰 Gradle 配置、不跑 Gradle、不管编译错误（C4 处理）。

## 已裁决事项（用户 2026-08-27 批准）

1. 新模块 `:SystemUI-application`（application/src 4 文件 + 1338 行完整 manifest → `SystemUI-application/src/main/AndroidManifest.xml`；`:app` 换依赖属 C4，本任务不动 build.gradle.kts）
2. 新模块 `:SystemUI-clocks-common`（customization/clocks/common 21 src + res + manifest，自有 R namespace）
3. pods 测试文件**原样拷入**（269 全量，不排除 test）
4. SurfaceEffects AAR 化（**C4 任务，本任务不处理**；本任务删 :SystemUI-animation 里 24 个 surfaceeffects EXTRA 文件即可）
5. 新模块 `:SystemUI-accessibility-floatingmenu-res`（res-only 源码 module：`accessibility/accessibilitymenu/res` 130 文件 + `AndroidManifest-floatingmenu.xml`）
6. `res/flag(...)/` 15 个文件直接拷贝
7. res-product 新变体（fr-rCA-feminine/masculine/neuter + product="desktop"）随 CONV 整批重标

## 冻结基线（开工前数字，验收用）

`python3 tools/check_source_alignment.py --summary`：

| 计数器 | 值 |
|---|---|
| MISSING | 1989 |
| MISPLACED | 34 |
| EXTRA | 628 |
| MODIFIED | 2222 |
| APP | 1（SystemUI-application/src/main/AndroidManifest.xml 缺失） |
| RES-MISS / RES-EXTRA / RES-MODIFIED | 577 / 219 / 830 |

## Global Constraints

- **操作顺序固定**：删 EXTRA → 移 MISPLACED（git mv）→ 拷 MISSING → 覆 MODIFIED → CONV 重标。每步后跑 `--summary` 记录数字演变（写入 issue 文档）。
- 文件操作全部用 `cp`（保留 AOSP 字节，不转换编码/换行符）；删除用 `git rm`；移动用 `git mv`。
- **白名单（不机械覆盖）**：
  - `SystemUI-shared/src/com/android/systemui/shared/system/UncaughtExceptionPreHandlerManager.kt`：先拷 17 版本；然后检查 17 是否提供等价 public API（`ActivityThread.getUncaughtExceptionPreHandler` 类路径）——若无则重放原 CONV_MOD workaround（hidden-API 反射），保留 CONV_MOD 标记并在 issue 文档记录判断依据。
  - 86 个 `SystemUI-res/res-product/values*/strings.xml`：拷贝 17 版本后**整批重标**（见下）。
- **CONV 重标规范**（ADR 0004）：对 17 版 res-product strings.xml 中所有带 `product="tv"`、`product="tablet"`、`product="desktop"` 的资源条目，用 `<!-- CONV_DEL BEGIN [task070] reason: product-variant unsupported by AGP -->` / `<!-- CONV_DEL END -->` 包裹注释（不删字节）。原 2237 个旧标记随文件覆盖消失，重标数量以 17 内容实际变体条目数为准。
- res `flag(...)` 限定目录（15 个文件）直接 `cp -r` 保持目录名。
- AOSP 源路径统一 `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/`（走 `tools/aosp_paths.py` 如需）。
- 不跑 Gradle、不改 `*.gradle.kts`/`libs.versions.toml`/`settings.gradle.kts`、不动 `libs/`（除下述唯一例外）、不 push。
- 新模块目录只放源码/res/manifest（build.gradle.kts 是 C4 的事；settings.gradle.kts 不注册——C4 做）。
- **唯一 libs 例外**：无。libs/ 完全不动。
- Python 脚本（如批量操作）一律 `uv run`；若写同步辅助脚本放 `/tmp/`（不入库），操作逻辑记录在 issue 文档。

## File Map

- 新建：`SystemUI-application/src/main/AndroidManifest.xml`（1338 行完整复制）+ `SystemUI-application/src/com/android/systemui/**`（4 文件）
- 新建：`SystemUI-clocks-common/src/**`（21 文件）、`SystemUI-clocks-common/res/**`、`SystemUI-clocks-common/AndroidManifest.xml`
- 新建：`SystemUI-accessibility-floatingmenu-res/res/**`（130 文件）、`SystemUI-accessibility-floatingmenu-res/AndroidManifest.xml`（复制 AOSP `AndroidManifest-floatingmenu.xml`，原文件名保留）
- 修改：13 个现有模块的 src/res 大批量 +/−/覆盖（见预研报告 §4.1/§4.2 矩阵）
- `app/proguard_common.flags` 更新为 17 版本（72 行）；`app/proguard.flags`/`proguard_kotlin.flags` 已字节一致不动
- **`app/src/main/AndroidManifest.xml` 不删**（C4 决定 :app 壳去留；本任务只新建 SystemUI-application 的完整版）
- 文档：`docs/issues/2026-08-27-c3-source-realignment-execution.md`
- STATE.md 本 task 行更新

## 步骤（checkbox）

### P1 删除 EXTRA（src 628 + res 219）
- [ ] 按预研报告 §1.2 三类归因全删（441+70+131）。70 类②删旧路径即可（新路径在 P3 拷入时自然补上）。
- [ ] res EXTRA 219 删除（84 个 locale 主干翻译删除前抽查 1-2 个：确认 17 里 biometrics/`shared/biometrics/res` 的同 locale 文件覆盖了相同 key，记录进 issue 文档）。
- [ ] 跑 `--summary` 记录。

### P2 移动 MISPLACED（34）
- [ ] 20 个原判 + 14 个新映射暴露的（core→shared 的 qualifiers/log-table、pods→shared 3 个、Dumpable、SpaceVectorConverter）逐个 `git mv`。
- [ ] 跑 `--summary` 记录。

### P3 拷贝 MISSING（src 1989 + res 577）
- [ ] 按映射逐 root `cp -r --parents`（pods 含 test 原样；`res/flag(...)/` 目录名原样）。
- [ ] `SystemUI-application`/`SystemUI-clocks-common`/`SystemUI-accessibility-floatingmenu-res` 三个新模块目录结构建立（只放文件，不建 build 脚本）。
- [ ] AIDL 6 个 + proto 1 个核对拷入（后续 C4 要接 sourceSet 管线）。
- [ ] 跑 `--summary` 记录。

### P4 覆盖 MODIFIED（src 2222 + res 830）
- [ ] 全部 `cp` 覆盖（预研已证 150/150 纯 vintage 漂移）。
- [ ] 白名单 2 处：UncaughtExceptionPreHandlerManager.kt（见 Global Constraints）；86 个 res-product strings.xml 拷贝后进 P5 重标。
- [ ] `app/proguard_common.flags` 更新。
- [ ] 跑 `--summary` 记录。

### P5 CONV 重标
- [ ] 86 个 res-product strings.xml 逐文件扫描 `product="tv"/"tablet"/"desktop"` 属性条目，按 ADR 0004 规范打 CONV_DEL BEGIN/END。
- [ ] `tools/check_source_alignment.py` MODIFIED 数会因标记增加——记录重标后数字（MODIFIED 不卡 strict，属预期）。
- [ ] UncaughtExceptionPreHandlerManager.kt 的 CONV_MOD 处理记录。

### P6 收尾验收
- [ ] `python3 tools/check_source_alignment.py --summary`：**MISSING=0、MISPLACED=0、EXTRA=0、APP=0**（MODIFIED 允许 >0：CONV 重标 + 白名单）。
- [ ] `python3 tools/check_source_alignment.py --strict` 退出码 0。
- [ ] `git status` 无 untracked 垃圾（新模块目录全部 add）。
- [ ] 英文 commit（可分步 commit：P1-P5 各一个，信息写清数字）。
- [ ] issue 文档完整（背景/步骤/数字演变表/待办移交 C4 清单）。
- [ ] 四段式完成报告。

## 五字段

- **Authority**: self-commit（多 commit 分步；**never push**）
- **Allowed Paths**: `SystemUI-*/`（src/res/manifest 文件操作）、`app/proguard_common.flags`、`docs/issues/2026-08-27-c3-source-realignment-execution.md`、`docs/orchestration/STATE.md`（本 task 行）、`/tmp/`（临时脚本）
- **Forbidden Paths**: `*.gradle.kts`、`gradle/`、`libs/`、`tools/`、`settings.gradle.kts`、`app/src/main/AndroidManifest.xml`（保留现状）、`AGENTS.md`、`git push`
- **Acceptance**: `uv run python3 tools/check_source_alignment.py --strict; echo $?` 输出 0；且 `--summary` 显示 MISSING/MISPLACED/EXTRA/APP 全 0
- **Reports To**: chief（herdr agent `task070`，主会话 `w2:p1`）

## 模型

joycode GLM-5.3。
