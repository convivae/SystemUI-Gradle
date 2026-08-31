# Task 074 — Phase C：Release/R8 编译闭环恢复绿（`:app:assembleRelease`）

## Task Scope

**Goal**: `./gradlew :app:assembleRelease` **BUILD SUCCESSFUL**（含 `minifyReleaseWithR8`），
对齐门 / pytest / 冻结指纹保持绿。Phase C 验收命题：Release 侧 R8 闭包在 17 基线上闭合。
**strictly out of scope**: runtime（设备/模拟器验证归 C5）、SysUISdk 再重建（17 基线已重建
2026-08-31，缺 API 一律报 chief）、Docker/签名/渠道。

参考十六时代 R8 闭环经验（16→17 可能重现/漂移）：Task 031/032（runtime closure 审计 +
platform-classpath 桥）、033/034（aconfig adapter）、035-038（viewcapture/motiontool/iconloader/
wmshell-proto）、044（missing refs 140→0）。facts 已在 17 基线上变化的：所有 AOSP 产物已再生、
SysUISdk 已按 17 重建、依赖图已重新接线（17 模块）。

## Pre-verified Facts (chief 已核实，直接采信)

1. **`:app:assembleDebug` 已绿**（2026-08-31 chief 重跑证实），APK 199,845,582 B。
   Release 与 Debug 的差异面 = minify/R8、resource shrink（16 时代 Task 030）、signing、
   compilelib release 变体（`libs/compilelib-release.jar` 已再生并冻结）。
2. **已知首个待破冰点（预期）**：`:app:minifyReleaseWithR8` 的 missing-references / keep 规则集
   17 漂移。16 时代规则文件在 `app/proguard.flags` + `app/proguard_common.flags`；audit 文档
   `docs/architecture/2026-08-20-r8-runtime-closure-audit.md` 是方法学参考而非结论。
3. **已知新风险点**（task073 issue §7 移交）：
   - ace AAR 类引用 `android.service.personalcontext.insight.ContextInsight`——编译期 jar 已过，
     dex/R8 期如果报缺，**禁止拷 framework 源码**，报 chief 走 SysUISdk/library-classes 通道；
   - `AssumeTrueForR8` -dontwarn adapter（ADR 0006 第 5 条）在 17 基线未验证；
   - pods 测试源不入生产图（有意如此，勿"补"）。
4. **view_capture proto**：17 源码零引用（task070/072 已核实），libs 已无该产物，勿回引。
5. **验收标准**：`:app:assembleRelease` BUILD SUCCESSFUL；`--strict` exit 0；
   `uv run pytest tools/tests -q` 全绿；`package_misc_jars.py --verify-only` 22/22 MATCH；
   `package_compilelib_jars.py --verify-only`（若存在该子命令）同名 APP 产物字节不变；
   APK 大小/entry 变化与本 issue 记录，供 C5/C6 对照。

## File Map

- 读写：`app/build.gradle.kts`、`app/proguard.flags`、`app/proguard_common.flags`、
  `SystemUI-*/build.gradle.kts`（release 段、minify/R8 参数）、`tools/`（如需新冻结产物：
  严格按 C2/C4b 格式：打包配置 + pytest + 冻结指纹）、`libs/`（仅限经 tools 脚本再生的产物）、
  `docs/issues/2026-09-01-c4c-release-r8-closure.md`（新建）、本文件的汇报、
  `libs.versions.toml`（如需官方坐标，先用 5.x 步骤核实 AOSP 版本）
- **禁改**：`tools/build_sysuisdk.py`（ADR 0006 红线）、`tools/check_source_alignment.py`
  （AGENTS.md 禁改面）、`SystemUI-*/src/**`（任何改动——含 CONV——须先报 chief 转用户逐点授权；
  **绝对禁止**参照 task073 D3 教训自行行使"类别授权"）、`SystemUI-*/res/**`、`docs/orchestration/CHARTER.md`、
  AOSP 树（只读）、git push
- 构建命令纪律：全工作区串行——你在唯一 pane；先 `pkill -f GradleDaemon --signal 9` 再开构建；
  `--max-workers=4`（Release R8 内存高，30G RAM 环境）。

## 分层策略（按错误类别选路径，一错误一根因）

| 错误类别 | 首选路径 | 禁令 |
|---|---|---|
| R8 missing references（framework/hidden API） | SysUISdk 已有 37 条桥接；缺 → 报 chief（禁 runtime 打包/dontwarn 掩盖，ADR 0006） | 禁拷 framework 源码、禁 new stub |
| aconfig AssumeTrueForR8 等 | 16 时代 adapter 规则复核后迁移（ADR 0006 §5）；aconfig 产物若缺 → 扩展 `tools/package_aconfig_jars.py`（冻结指纹+pytest） | 禁 runtime 打包 |
| keep 规则漂移（类移动/删除） | 先核对该类 17 是否存在（`find AOSP | grep`），不存在→删规则并记录；存在→按 17 FQCN 修规则 | 禁“保住规则不管真假” |
| 资源 shrink 报错 | 16 时代 Task 030 方法与 17 res 差异逐条核实 | 禁减 res 源文件 |
| dex 超大/方法数 | 如实记录大小数字，报 chief；不考虑 multidex 新策略（bp `dxflags: ["--multi-dex"]`自动） | — |
| 新 tier② 产物需求 | 扩展 tools 脚本（同 P1 纪律：配置+pytest+冻结指纹） | 禁手工产物 |

错误处理纪律映射（AGENTS §五 + 审计教训）：一次一个根因；每轮--continue 收集；
错误数演变如实记表（引用 log 文件）；**任何需要碰 AOSP 镜像 src/res 的绕法先停工上报**。

## Report Contract

1. **Status**: assembleRelease 是否 BUILD SUCCESSFUL。
2. **Evidence**: 错误演变表（R1→Rn，每轮命令+错误数+根因+处置）；最终四门验证输出；
   APK 大小/sha 初值（`sha256sum app/build/outputs/apk/release/*.apk`）；mapping 文件存在性。
3. **RED LINE REPORT**: 每个虽停-上报点（若有）：触发条件、已验证步骙、等待的裁决。
4. **Next steps**: 移交 C5 的清单（runtime 侧风险、17 APK 与 16 差异观察点）。

## Acceptance

- `:app:assembleRelease` BUILD SUCCESSFUL（成功构建可复现）
- `--strict` exit 0；pytest 全绿；冻结指纹全 MATCH
- issue 文档含错误演变表 + 每个修复的 bp/规则依据；无手工产物；无未授权 src/res 改动
- 汇报按 Report Contract 四部分

### AUTHORITY

- May: 编全量 release 构建（受限内存参数）、proguard·build 文件修改、tools 扩展（产物+测试+指纹）、
  issue 文档、小步 commit
- May NOT: 碰 AOSP 镜像 src/res（先报）、`build_sysuisdk.py`、CHARTER、`git add -A`/`.`、git push、
  runtime 类打包（ADD-R8-invariant）、dontwarn 掩盖缺失引用、stub
- 汇报对象：chief（`w2:p1`）

### 五字段

- **Authority**: 见上
- **Allowed Paths**: `app/`、`SystemUI-*/build.gradle.kts`、`tools/`（含 tests）、`libs/`（脚本再生产物）、
  `gradle/libs.versions.toml`、`docs/issues/2026-09-01-c4c-release-r8-closure.md`、本文件、`docs/orchestration/log.md`/STATE.md（单行）
- **Forbidden Paths**: `SystemUI-*/src/**`、`SystemUI-*/res/**`、`tools/build_sysuisdk.py`、
  `tools/check_source_alignment.py`、`docs/orchestration/CHARTER.md`、AOSP 树、git push
- **Acceptance**: 见上“Acceptance”
- **Reports To**: chief

## 模型

joycode GLM-5.3。
