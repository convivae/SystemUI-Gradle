# 2026-08-26 — libs/ 全量产物引用图审计（Task 062）

> **Type**: 只读研究（read-only audit）· **Worker**: task062 (joycode/GLM-5.3)
> **Brief**: `docs/orchestration/tasks/062-libs-artifact-inventory-audit.md`
> **Full report**: `docs/architecture/2026-08-26-libs-artifact-inventory-audit.md`

## 背景

task 001–061 演进多轮（task 057 合并 14 个 flags jar 为 `systemui-aconfig-flags.jar`；task 059 把 4 族 AAR 从本地 Maven 改为 `libs/aars/` 直接消费）。chief 预扫怀疑 libs/ 下有旧文件残留未被引用，派本 task 做全量引用图审计，为大扫除（删除孤儿）提供逐项证据。

## 操作步骤（全部只读）

1. 全量枚举 `libs/`（`find` + `git ls-files`，105 tracked 文件）。
2. 逐文件 `sha256sum` 前 8 位 + 字节大小。
3. 对每个产物 basename 在 `*.kts`/`*.toml`/`*.flags` 中 `grep -rn` 取 `file:line` 证据；另用 `grep -oE 'libs/...'` 全量兜底，确认无 `fileTree` 批量引入。
4. 读 `gradle/libs.versions.toml` 全量 alias + 各 module `libs.systemui.*` 实际消费，区分直接消费 vs POM 传递。
5. 读 `SettingsLib-1.0.1.pom` 确认 ADR 0005 的 17 条传递边。
6. 程序化比对 `libs/aars/*.aar` ↔ `libs/maven/**.aar` sha256（drift check）。
7. 对孤儿候选 `git log --follow`；对 task 057 `git log --diff-filter=D --name-only`。
8. 阿里云 google/central 镜像回查 keepanno / lifecycle-process / settingslib / animationlib 的官方坐标。

## 错误数演变

N/A（只读研究，无构建）。

## 核心结论

- **105 tracked 文件审计完毕：104 WIRED，1 ORPHAN。**
- **唯一 DELETE-CANDIDATE**：`libs/lifecycle-process-2.4.0-alpha01.aar`（0 引用，自首个 commit `a4bd7f94`(2026-07-18) 起未动；官方 Maven `androidx.lifecycle:lifecycle-process` 存在）。
- **chief 6 疑点**：5 证伪（11 个分散 flags jar 全仍 wired / 无第 5 个 aar 残留 / maven 23 artifact 全引用 / android_module_lib_stubs + SystemUI-tags wired / compilelib debug+release wired），1 证实（prebuilts 仅 tracinglib-platform.jar）。
- **task 057 真相**：合并的是另一组 14 个 hidden-twin aconfig jar（已 git-rm），与现存 11 个 per-target flags jar 无交集。
- **字节对齐**：23 个 Maven AAR 与 `libs/aars/` 源 23/23 sha256 一致，零 drift。
- **官方 Maven 回查**：keepanno-annotations 镜像 404（core 注释正确，无 Maven eq）；lifecycle-process 镜像有效 XML（存在）；settingslib/animationlib 镜像 404（AOSP fork，无公网等价物）。

## 旁观察（非删除候选）

- `monet.jar`：AGENTS.md §1.5 tier① 列 monet 为 SystemUI 自有代码 → 规则 S 可能要求源码化，但属"形态合规"非"删除"问题，超本 task 范围。判 KEEP，供 chief 知悉。
- `gradle/replace-sdk-jar.gradle.kts`：未被任何 build 文件 apply，引用的 `libs/platform/android.jar` 不在 git —— 未接线遗留脚本（已被 SysUISdk 生成器取代）。非 libs/ 产物，提请 chief 知悉。

## 验证证据

- 未运行任何 Gradle 构建（只读授权）。
- 全部 grep/sha256/git/curl 命令输出已纳入主报告 §2-§6 表格与 §7 疑点表。
- 复现命令见主报告 §12 附录 B。

## 待解决问题

- 删除 `libs/lifecycle-process-2.4.0-alpha01.aar` 需 chief 授权 + 构建验证（`./gradlew :app:assembleDebug` 应与基线 `e8aad131` 一致）。本 task 不执行删除。
- monet.jar 源码化评估建议单独派 task。
- `gradle/replace-sdk-jar.gradle.kts` 遗留脚本清理建议单独派 task（属 `gradle/` 目录）。

## Git

本地 commit（英文 message，未 push）：`docs: task062 libs artifact inventory audit (read-only, 1 orphan found)`

---

# 扩展审计：tools/ 与 scripts/ 脚本盘点（同日 chief 扩展授权）

**授权**: report-only（report + log line only；实际删除全部等待用户批准）。
**姿态**: 再生管线脚本为一等 KEEP；删除需四重否定证明；存疑即 KEEP/UNCERTAIN；borderline 一次性脚本标注 deferred。

## 结论

- **KEEP 23**（tools/ 16 脚本中 15 + 11 测试中…见下表）+ install_keystore.sh KEEP-with-fix（ADR 0002 转 .py 欠账）
- **UNCERTAIN 1**: fix_r_imports_to_res.py（自声明 disabled，等 R-namespace 梳理）
- **DELETE-CANDIDATE 16**（全部 deferred 至 Phase C pipeline 文档确认非成员资格）:
  1. gradle/replace-sdk-jar.gradle.kts（零接线、输入不 tracked、被 ADR 0006 取代 — 最强）
  2-9. scripts/ 8 个零引用一次性迁移（move_extras、rollback_moves、recover_aosp、recover_compose、strip_extras_already_in_jars、strip_extras_stubs、check_extras_in_jars、scan_aosp_bp_modules）
  10-15. scripts/ 6 个历史分析工具（check_aosp_src_parity[被 tools/check_source_alignment.py 取代]、check_aosp_extras_breakdown/sysui、map_extras_to_modules、propose_aosp_to_gradle_mapping、scaffold_aosp_modules[被 ADR 0003 取代]）
  16. tools/extract_prebuilts.sh（4 产物全被源码模块取代 + ADR 0002 .sh 违规）

## 再生性 GAP（重点，用户可复现目标阻塞）

libs/ 28 个根目录 jar 中 **15 个无再生脚本**：3 个 flags jar 是 quick win（settingslib-flags、settingslib-media-flags、device-state-flags —— 补 package_aconfig_jars.py CONFIGS 即可，注意 device-state-feature-flags 是已合并的另一个族勿混淆）；其余 12 个（framework、framework-statsd、android.car、android_module_lib_stubs、SystemUI-proto/statsd/tags、contextualeducationlib、msdl、PlatformMotionTestingComposeValues、keepanno-annotations、tracinglib-platform）需新增 AOSP out/ 提取脚本。覆盖良好：29/29 AAR、23/23 maven、monet/viewcapture/motiontool/compilelib、9/12 flags。

## Ghost 脚本考古

install_sdk/patch_sdk_dalvik_annotations/patch_sdk_r8_library_classes 已删于 8cb7279b；gen_aar_maven/rebuild_settingslib_aar/clean_aar_maven 已删于 6741324d —— chief 假设由 git 历史证实。仅剩 gitignored .pyc（本地卫生，`git clean -fdX tools/ scripts/` 可清，本次未执行）。

## aosp_paths 单一来源合规

合规 2 个（package_aconfig_jars、build_sysuisdk）；KEEP-with-fix 5 个（package_aosp_aar、package_compilelib_jars、check_source_alignment 无 --aosp-root；package_monet、package_viewcapture default 硬编码）；scripts/ 全部 14 个硬编码（若删除则自然消解）。

## 输出

- 主报告: `docs/architecture/2026-08-26-tools-scripts-inventory-audit.md`
- log line: `docs/orchestration/log.md`（task062-extension 一行）
- 本地 commit（英文 message，未 push）
- 未运行任何 Gradle 构建（report-only mandate）
