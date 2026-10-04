# R8 Runtime Closure — Batch 4C（Traceur）实施计划

> 日期：2026-08-20。设计：`docs/issues/2026-08-20-r8-runtime-batch4c-traceur.md`。
> 目标：Traceur 双 AAR（TraceurCommon 含 perfetto protos + Traceur-res）直接引入，
> 退役 TraceurCommon.jar / traceur-res-R.jar；fresh R8 88→81 精确；debug 硬门禁。
> 红线：不加 keep/-dontwarn、不改 res、不动 SettingsLib、构建串行、禁止直接 patch SysUISdk。

## Task 0：Branch & 基线

**Files:** 无（仅确认）

- [ ] 分支 `task-038-r8-runtime-batch4c-traceur`，基 main `34cac970` 或更高
- [ ] 记录基线 missing_rules 行数=88、`git status` clean
- [ ] `python3 -m unittest discover -s tools/tests` 基线全绿
- [ ] 确认 AOSP 产物路径存在（issue §3 表）

## Task 1：`tools/package_aosp_aar.py` 新增 Traceur 两个 CONFIGS

**Files:**
- Modify: `tools/package_aosp_aar.py`
- Test: `tools/tests/test_package_aosp_aar.py`

- [ ] 新增 `TRACEUR_DIR = AOSP_ROOT / "packages/apps/Traceur"` 等常量
- [ ] `TraceurCommon` CONFIG：code = [TraceurCommon javac jar, perfetto_config_java_protos javac jar]（合并去重，预期 640 类）；res = 无；manifest = `AndroidManifest-common.xml`；rtxt = 无。**先读脚本确认 res/rtxt 缺省行为；若不支持无 res，做最小扩展**（复用 SettingsLibColor 的 code=[] 反向形态）+ 测试
- [ ] `Traceur-res` CONFIG：code = []；res = [Traceur/res]；manifest = `AndroidManifest-res.xml`；rtxt = Soong `Traceur-res/android_common/R.txt`
- [ ] 新增/更新测试：两 CONFIG 的 output、来源路径、预期类数（640/0）、manifest/R.txt 路径
- [ ] `python3 -m unittest discover -s tools/tests` 全绿

## Task 2：生成并审计 AAR

**Files:**
- Create: `libs/aars/TraceurCommon.aar`、`libs/aars/Traceur-res.aar`

- [ ] `python3 tools/package_aosp_aar.py --only TraceurCommon`（无 --only 则按脚本现有接口逐名跑）+ `--only Traceur-res`
- [ ] TraceurCommon.aar：恰好 640 类；`com/android/traceur/`=15、`perfetto/protos/`=625；manifest package=`com.android.traceur.common`；无 res 条目
- [ ] Traceur-res.aar：无 classes 条目；res 恰好 105 文件与 AOSP 一致；manifest package=`com.android.traceur.res`；R.txt 与 Soong 一致
- [ ] 两 AAR 类集合互斥，且与 `libs/maven` 既有 AAR、`libs/*.jar` 无重叠（重点：protobuf-javalite 是官方坐标不含 perfetto.protos）
- [ ] 确定性：连续两次生成 SHA-256 一致，记录哈希
- [ ] `git status`：恰好两个新 AAR

## Task 3：接线 + 退役占位物

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`（L195-197 两条 compileOnly → 两条 `implementation(files("libs/aars/..."))`）
- Delete: `libs/TraceurCommon.jar`、`libs/traceur-res-R.jar`

- [ ] 替换依赖声明（直接 AAR 优先，ADR 0001；进 git，与 libs/ 现行策略一致）
- [ ] 删除两个旧 jar 并 `git rm`
- [ ] `git grep -n 'TraceurCommon.jar\|traceur-res-R.jar'` 全仓无残留
- [ ] `python3 -m unittest discover -s tools/tests` 全绿

## Task 4：构建验收（本任务唯一构建者）

- [ ] `set -o pipefail; ./gradlew :app:assembleDebug 2>&1 | tee /tmp/task038-debug.log; echo "exit=$?" | tee /tmp/task038-debug.status` —— **exit 0（硬门禁）**
- [ ] 若 `:app:processDebugResources` 报缺 leanback/v14 等资源 → **HALT 上报用户**（不得自行新增 androidx 坐标）
- [ ] APK 内容：APK 内 `com/android/traceur/`（15 类）与 `perfetto/protos/`（625 类）defined（dex 引用计数或类列表，证明打包而非仅编译）
- [ ] merged manifest（`app/build/intermediates/.../AndroidManifest.xml` 或 APK 反解析）含 `android.permission.CONTROL_UI_TRACING`
- [ ] 若 assembleDebug 出现非资源类失败 → 停止并报告

## Task 5：Fresh R8 验收（复用 Task 033/035/036/037 框架）

- [ ] **Baseline**：`git stash -u` → fresh `:app:minifyReleaseWithR8` → missing_rules=88 → 排序存 `task038-baseline-missing.txt` → `git stash pop` → 确认工作区恢复
- [ ] **Changed**：fresh `:app:minifyReleaseWithR8` → missing_rules=81 → `task038-changed-missing.txt`
- [ ] **精确差分**：removed = 恰好 7 个 traceur 目标（FileSender、PresetTraceConfigs、TraceConfig、PresetTraceConfigs$TraceOptions、TraceConfig$Builder、traceur.res.R$array、traceur.res.R$string）；added=0；`AssumeTrueForR8` 保留
- [ ] 若 release 有**资源链接**失败（leanback 等）→ 属新资源闭包问题，停止上报（不得用 -dontwarn/排除 res 绕过）

## Task 6：文档 + 提交

**Files:**
- Modify: `docs/architecture/2026-08-20-r8-runtime-closure-audit.md`（§4.2 A7 行：实际 88→81、批次=Batch 4C (Task 038)）
- Modify: `docs/orchestration/STATE.md`、`docs/orchestration/log.md`（编排事实）

- [ ] commit（英文）：工具+测试 → AAR → 接线+退役 → 文档（可合并为 1-2 个 commit）
- [ ] 最终 `git status` clean、全套测试绿
- [ ] HANDOFF：报告 debug/R8 退出码、missing 88→81、removed/added、AAR 类数与哈希、APK/manifest 证据
