# tools/ 与 scripts/ 全量脚本盘点审计（task 062 扩展，report-only）

**日期**: 2026-08-26
**性质**: 只读审计（REPORT-ONLY）。未删除、未移动、未修改任何脚本/产物/接线；所有删除均等待用户显式批准。
**审计姿态**（chief 2026-08-26 指令）: 再生管线脚本为一等 KEEP 公民；删除判定需证明脚本**不是**管线成员、无 doc/runbook 引用、非测试基建、非对齐/验证工具；存疑一律 KEEP/UNCERTAIN；borderline 一次性脚本标注 "deletion deferred until Phase C pipeline doc confirms non-membership"。
**姊妹报告**: `docs/architecture/2026-08-26-libs-artifact-inventory-audit.md`（libs/ 105 个产物审计）。

## 1. 盘点范围与方法

- **范围**: `tools/` 全部 git-tracked 文件（16 个脚本 + 11 个测试 = 27）+ `scripts/` 全部（14 个 .py）+ chief 指定追加的 `gradle/replace-sdk-jar.gradle.kts`。共 **42 个 tracked 条目**。
- **方法**: 逐脚本读 docstring/purpose → `grep -rn` 全 docs/ + AGENTS.md + build 文件找引用 → 与 libs/ 审计的 artifact↔generator 映射交叉验证 → git log 考古（引入/最后修改/删除历史）→ 硬编码路径 vs `tools/aosp_paths.py` 单一来源检查。
- **未运行任何 Gradle 构建**；`__pycache__/*.pyc` 均 gitignored（tracked 数 = 0），不在删除范围（见 §9 本地卫生）。

## 2. 结论速览

| 类别 | 数量 | 明细 |
|---|---|---|
| **KEEP**（管线一等公民） | 8 | build_sysuisdk, package_aosp_aar, package_aconfig_jars, install_aar_to_maven, package_compilelib_jars, package_monet_jar, package_viewcapture_motiontool_jars, aosp_paths |
| **KEEP**（活跃接线/验证） | 4 | patch_androidprv_merged_resources（app build 接线）, check_source_alignment, check_manifest_dex_closure, clean_prebuilts（仍处理 prebuilts/*.jar） |
| **KEEP-with-fix**（ADR 0002 .sh 转换欠账） | 1 | install_keystore.sh（产出 tracked keystore/platform.keystore） |
| **KEEP**（测试基建，11 文件） | 11 | tools/tests/* 全部；无孤儿测试（已删脚本的测试已随 8cb7279b/6741324d 同步删除 ✓） |
| **UNCERTAIN** | 1 | fix_r_imports_to_res.py（自声明 disabled，R-namespace 方案悬而未决） |
| **DELETE-CANDIDATE**（全部带 deferred 标注） | 16 | gradle/replace-sdk-jar.gradle.kts + scripts/ 全部 14 个 + tools/extract_prebuilts.sh |

**再生性 GAP（用户可复现目标的阻塞点，须重点报告）**: libs/ 28 个根目录 jar 中 **15 个没有任何再生脚本**（详见 §7）。

## 3. tools/ 逐脚本审计表

| # | 脚本 | 一句话用途 | ALIVE 证据 | 判定 | 备注 |
|---|---|---|---|---|---|
| 1 | aosp_paths.py | AOSP 路径单一来源模块（用户规则 2026-08-25） | 被 package_aconfig_jars.py + 其测试 import；3 doc 引用 | **KEEP** | 违规治理见 §8：目前仅 1 个消费者 |
| 2 | build_sysuisdk.py | 单入口 SysUISdk 生成器（ADR 0006，冻结八输入映射） | 39 个 doc 引用；AGENTS.md §2.4/§7；测试 ✓ | **KEEP** | 无硬编码 AOSP 绝对路径（--aosp-root 必填 + 相对映射）✓ |
| 3 | check_manifest_dex_closure.py | APK manifest→DEX 闭包门禁（Task 050） | task 058 gate suite 引用（brief:12）+ issues 2026-08-25 PASS 证据 | **KEEP** | aapt2 路径硬编码但有 `--aapt2` 覆盖 |
| 4 | check_source_alignment.py | 规则 C/ADR 0004 源码-资源对齐门禁（内容+owner 感知） | 25 doc 引用；AGENTS.md；ADR 0004；测试 ✓ | **KEEP** | 硬编码 AOSP_ROOT/PROJECT_ROOT，无 --aosp-root（§8 fix） |
| 5 | clean_prebuilts.py | 清理 libs/prebuilts/*.jar 中与 Maven 冲突的包前缀 | glob 整个 prebuilts 目录 → 今天仍处理 tracinglib-platform.jar；AGENTS.md §7；issues 2026-07-18 | **KEEP** | 是 tracinglib 再生管线第 2 步（提取器缺失见 §7 GAP-12） |
| 6 | extract_prebuilts.sh | 从 AOSP out/ 拷 4 个 SystemUI *Lib.jar 到 libs/prebuilts/ | **4 个产物全部已被源码模块取代**（规则 S 2026-07-29，目录现仅剩 tracinglib）；ADR 0002 记录其为待转 .py 的违规 .sh | **DELETE-CANDIDATE**（deferred） | 产物全部消亡的 generator；ADR 0002 + plan 2026-07-16 引用需先记档；亦不产出 tracinglib |
| 7 | fix_r_imports_to_res.py | 将 R import 改回 AOSP 风格 `systemui.res.R` 的 codemod | 自声明 "DEPRECATED 暂不启用 (2026-07-30)"（错误数 66→78）；1 个 plan 引用（2026-08-06 checkpoint:101） | **UNCERTAIN** | 悬置非死亡：docstring 写明等 AGP R 子包生成问题解决后可启用；R-namespace 现状与 SystemUI-res 的 `.res.R` 演进需 Phase C 梳理后再定 |
| 8 | install_aar_to_maven.py | libs/aars/*.aar → libs/maven/ 本地 Maven（AAR+POM，ADR 0005） | 46 doc 引用；AGENTS.md §3.2/§7；测试 ✓；覆盖全部 23 个 maven 产物 | **KEEP** | 无 AOSP 路径需求 ✓ |
| 9 | install_keystore.sh | AOSP platform.pk8+x509.pem → keystore/platform.keystore | 产出 **tracked** 的 keystore/platform.keystore（app 签名用）= 受保护产物的唯一再生脚本；ADR 0002 + MIGRATION_LOG:317 引用 | **KEEP**（fix: 转 .py） | ADR 0002 记录 `install_keystore.sh → install_keystore.py` 转换欠账 |
| 10 | markup_product_variants.py | res-product 非 default product 变体加 CONV_DEL 标记 | docs/README.md 活跃工具表:97；ADR 0004；4 doc 引用；8 单测 ✓ | **KEEP** | 一次性已执行但可重跑（res 重新同步后需重标记）+ 有测试 |
| 11 | package_aconfig_jars.py | 从 AOSP javac 产物打包 aconfig flags JAR（五类校验 + 14 族合并） | 28 doc 引用；AGENTS.md §7；README 表:91；测试 ✓；import aosp_paths ✓ | **KEEP** | 覆盖审计见 §7：22 CONFIGS = 8 在盘 + 14 已合并族（设计如此）；3 个缺口 GAP-13/14/15 |
| 12 | package_aosp_aar.py | AOSP Soong javac/kotlin + 原始 res → 确定性 AAR | 43 doc 引用；AGENTS.md §3.2/§7；README 表:89；测试 ✓ | **KEEP** | **29 CONFIGS 输出与 libs/aars/ 29 个磁盘文件集合完全一致**（diff 验证）；硬编码 AOSP_ROOT 无 --aosp-root（§8 fix） |
| 13 | package_compilelib_jars.py | AOSP compilelib Compile.java → debug/release 两 JAR | 9 doc 引用；README 表:92；测试 ✓；产物 compilelib-{debug,release}.jar wired core:130-131 | **KEEP** | 硬编码 AOSP_ROOT 无 --aosp-root（§8 fix） |
| 14 | package_monet_jar.py | monet+libmonet 干净 JAR（去 errorprone 冲突，Task 033） | 6 doc 引用；README 表:93；测试 ✓；产物 monet.jar wired | **KEEP** | 有 --aosp-root CLI ✓（default 硬编码见 §8） |
| 15 | package_viewcapture_motiontool_jars.py | view_capture + motion_tool_lib 两个 class-only JAR | 7 doc 引用；README 表:93；测试 ✓；两产物 wired | **KEEP** | 有 --aosp-root CLI ✓ |
| 16 | patch_androidprv_merged_resources.py | AGP 9.3.1 丢失 xmlns:androidprv 的合并资源修复 | **接线于 app/build.gradle.kts:129**（build-time 活跃钩子）；5 doc 引用；测试 ✓ | **KEEP** | 活跃构建工具，非一次性 |

### 3.1 tools/tests/（11 文件，全部 KEEP — 测试基建）

test_build_sysuisdk, test_check_source_alignment, test_gradle_r8_adapter_rules（契约测试：钉住 app/proguard_gradle.flags 窄 dontwarn 边界, Task 044）, test_install_aar_to_maven, test_markup_product_variants, test_package_aconfig_jars（含 aosp_paths 单源断言）, test_package_aosp_aar, test_package_compilelib_jars, test_package_monet_jar, test_package_viewcapture_motiontool_jars, test_patch_androidprv_merged_resources。

已删脚本（install_sdk / patch_sdk_dalvik_annotations / patch_sdk_r8_library_classes，commit 8cb7279b；gen_aar_maven / rebuild_settingslib_aar / clean_aar_maven，commit 6741324d）的测试**已随脚本同步删除**，无孤儿测试 ✓。

## 4. scripts/ 逐脚本审计表（14 个，全部 2026-07-30 "extras/Phase A-B" 时代产物）

统一背景：全部依赖 `docs/extras-file-mapping.csv`（仍 tracked，61KB，历史记录）；全部硬编码路径（§8）；**docs/README.md 活跃工具表收录数为 0**；AGENTS.md 引用数为 0；scripts/ 无任何测试；最后一次 commit 触及 scripts/ 是 df83e2cd（task 019 清理）。功能上已被 `tools/check_source_alignment.py`（规则 C 现役门禁）+ 13-module 源码拓扑（ADR 0003）+ 源码模块化（规则 S）整体取代。

| # | 脚本 | 用途 | doc 引用 | 判定 |
|---|---|---|---|---|
| 1 | check_aosp_src_parity.py | 早期 src 1:1 文件集对齐扫描（规则 C 首版） | audit-2026-07-30 + task 019（"仅当有 delta 需移植时"保留——delta 早已解决） | DELETE-CANDIDATE（deferred） |
| 2 | check_aosp_extras_breakdown.py | extras 按包名分类细化 | audit-2026-07-30 | DELETE-CANDIDATE（deferred） |
| 3 | check_aosp_extras_sysui.py | extras 中 systemui 子目录分类 | audit-2026-07-30 | DELETE-CANDIDATE（deferred） |
| 4 | check_extras_in_jars.py | 找 extras 里已被 jar 覆盖的伪源码 | **0** | DELETE-CANDIDATE（deferred） |
| 5 | map_extras_to_modules.py | extras → AOSP 真实模块定位 | audit-2026-07-30 + issues 2026-07-30-phase-d（记录其自身 bug） | DELETE-CANDIDATE（deferred） |
| 6 | move_extras_to_modules.py | Phase B 按 CSV 批量搬移（已执行） | **0** | DELETE-CANDIDATE（deferred） |
| 7 | propose_aosp_to_gradle_mapping.py | bp→Gradle 模块映射提案 | docs/mapping-2026-07-30 | DELETE-CANDIDATE（deferred） |
| 8 | recover_aosp_files.py | 按 CSV 从 AOSP 1:1 恢复源码（已执行） | **0** | DELETE-CANDIDATE（deferred） |
| 9 | recover_compose_files.py | 恢复被 rm -rf 误删的 compose 文件（已执行） | **0** | DELETE-CANDIDATE（deferred） |
| 10 | rollback_moves.py | 回滚 #6 的搬移（安全网，已无需） | **0** | DELETE-CANDIDATE（deferred） |
| 11 | scaffold_aosp_modules.py | Phase A 生成 bp-1:1 模块脚手架 | issues 2026-08-19-aar-cleanup:59（当时"仅报告不处理"） | DELETE-CANDIDATE（deferred） |
| 12 | scan_aosp_bp_modules.py | 扫描 bp 模块（#7 的输入） | **0** | DELETE-CANDIDATE（deferred） |
| 13 | strip_extras_already_in_jars.py | 删 jar 已覆盖的伪源码（已执行） | **0** | DELETE-CANDIDATE（deferred） |
| 14 | strip_extras_stubs.py | 删 stub 伪源码（规则 P 时代，已执行） | **0** | DELETE-CANDIDATE（deferred） |

**全部标注**: *deletion deferred until Phase C pipeline doc confirms non-membership*。其中 #6/#8/#9/#13/#14 为效果已在树内的一次性迁移；#1-5/#7/#11/#12 为历史分析工具；删除前需同步处理的 doc 引用：`docs/audit-2026-07-30-aosp-src-parity.md`、`docs/mapping-2026-07-30-aosp-bp-to-gradle.md`、`docs/issues/2026-07-30-phase-d-modules-compile.md`、task 019 brief、issues 2026-08-19-aar-cleanup（历史记录，可加"已删除"注记而非改写）。

## 5. gradle/replace-sdk-jar.gradle.kts（chief 追加范围）

- **用途**: 旧 SDK jar 替换脚本（commit b6f4508f，2026-08 初）。
- **证据**: `apply(from=...)` 全项目 0 命中（我的 libs 审计 §10.2 已核实）；引用的 `libs/platform/android.jar` 不在 git；被 ADR 0006 单入口生成器（build_sysuisdk.py）彻底取代。
- **判定**: **DELETE-CANDIDATE**（deferred；本清单中最强候选——零引用、输入不 tracked、被 ADR 0006 明确取代）。

## 6. 已死亡脚本考古（确认无残留源码）

6 个 ghost 脚本只剩 `__pycache__/*.pyc`（gitignored，本地字节码）：
- **8cb7279b** "tools: delete superseded SysUISdk payloads and patch helpers" → install_sdk.py, patch_sdk_dalvik_annotations.py, patch_sdk_r8_library_classes.py（与 2026-08-21 SysUISdk 单入口架构文档 §6 记载一致 ✓）
- **6741324d** "Remove orphan SystemUISharedLib AAR, Maven-side flags jar, and 3 obsolete tools scripts" → gen_aar_maven.py, rebuild_settingslib_aar.py, clean_aar_maven.py

chief 假设中的 `gen_aar_maven.py`（被 install_aar_to_maven 取代）与 `rebuild_settingslib_aar.py` 均已在 6741324d 删除——**假设已由 git 历史证实**。源码层面无需再删。

## 7. ⚠️ 再生性 GAP（可复现目标阻塞点，重点报告）

**libs/ 28 个根目录 jar（含 prebuilts/1 个）中 15 个今天无法用脚本从 AOSP 再生**（chief 原则 4：kept 产物无生成脚本 = GAP）。按可修复难度排序：

| # | 产物 | wired 于 | 缺失原因 | 修复建议 |
|---|---|---|---|---|
| **1** | settingslib-flags.jar | core:180 (co) | package_aconfig_jars.py CONFIGS 无此条目 | **quick win**：按既有五类校验模式补 CONFIGS 条目 |
| **2** | settingslib-media-flags.jar | core:182 (impl) | 同上 | 同上 |
| **3** | device-state-flags.jar | core:256 (impl) | 同上（注意：CONFIGS 里的 `device-state-feature-flags`=android.hardware.devicestate.**feature**.flags 是已合并的另一个族，勿混淆） | 同上 |
| 4 | framework.jar | 12 module co + root JC | 2026-07-18 手工 cp（issues 文档记载"从 out/soong/.intermediates 提取"），无脚本 | 新增提取脚本（与 build_sysuisdk 冻结映射同源：framework turbine-combined） |
| 5 | framework-statsd.jar | core co | 无任何脚本引用 | 同上模式 |
| 6 | android.car.jar | core co | 同上 | 同上 |
| 7 | android_module_lib_stubs_current.jar | core:155 co | 同上 | 同上 |
| 8 | SystemUI-proto.jar | core | 同上 | 同上（AOSP proto javac 产物） |
| 9 | SystemUI-statsd.jar | core | 同上 | 同上 |
| 10 | SystemUI-tags.jar | core:167 impl | 同上 | 同上 |
| 11 | contextualeducationlib.jar | core | 同上 | 同上 |
| 12 | prebuilts/tracinglib-platform.jar | core（chief 2026-08-26 确认 keep） | extract_prebuilts.sh 的拷贝清单不含它；clean_prebuilts.py 只是第 2 步清洗器 | 在 prebuilts 提取器（若保留该管线）补 tracinglib 条目 |
| 13 | msdl.jar | core | 无脚本 | 新增提取脚本 |
| 14 | PlatformMotionTestingComposeValues.jar | core | 无脚本 | 同上 |
| 15 | keepanno-annotations.jar | core co | 无专用脚本（SysUISdk 架构文档 §6 明言"非 SysUISdk 组成输入，独立 compileOnly"；来源路径在冻结映射有记载） | 一行 cp 脚本或并入提取器 |

**覆盖良好的部分**（无 GAP）：29/29 AARs（package_aosp_aar.py，集合 diff 验证一致）、23/23 maven 产物（install_aar_to_maven.py）、monet/view_capture/motion_tool_lib/compilelib×2、9/12 flags jars（8 个独立 + systemui-aconfig-flags 合并 jar）。

## 8. 硬编码 AOSP 路径 vs aosp_paths.py 单一来源（KEEP-with-fix，非删除）

用户规则（2026-08-25）：AOSP 根路径唯一来源 `tools/aosp_paths.py`。当前合规情况：

- ✅ 合规：package_aconfig_jars.py（唯一 import aosp_paths 者）、build_sysuisdk.py（--aosp-root 必填 + 相对映射，无绝对路径）
- ⚠️ 硬编码待修（KEEP）：package_aosp_aar.py:25（无 --aosp-root）、package_compilelib_jars.py:22（无 --aosp-root）、check_source_alignment.py:37-38（无 --aosp-root）、package_monet_jar.py:27 / package_viewcapture_motiontool_jars.py:30（有 --aosp-root 但 default 硬编码，应改走 aosp_paths）、check_manifest_dex_closure.py:141（aapt2 SDK 路径，有覆盖参数，低优）
- ⚠️ scripts/ 全部 14 个硬编码（若 §4 删除则自然消解；若保留需迁移）
- ℹ️ aosp_paths.py:17 自身持有 `DEFAULT_AOSP_ROOT = /home/conv/myspace/aosp` —— 这就是设计上的单一来源本体 ✓

## 9. 本地卫生（非 git 层面，仅记录）

`tools/__pycache__/`、`tools/tests/__pycache__/`、`scripts/__pycache__/` 中存有 6 个已删脚本 + 全部在世脚本的 .pyc。全部被 .gitignore 覆盖（tracked=0），对新 clone 零影响；如需清理本地：`git clean -fdX tools/ scripts/`（report-only，本次未执行）。

## 10. 排序 DELETE-CANDIDATE 清单（16 项，全部 deferred：删除延后至 Phase C pipeline 文档确认非成员资格；实际删除待用户批准）

1. **gradle/replace-sdk-jar.gradle.kts** — 最强候选：零接线引用、输入不 tracked、被 ADR 0006 取代
2. scripts/check_extras_in_jars.py（0 引用）
3. scripts/move_extras_to_modules.py（0 引用，已执行）
4. scripts/rollback_moves.py（0 引用，安全网已失效）
5. scripts/recover_aosp_files.py（0 引用，已执行）
6. scripts/recover_compose_files.py（0 引用，已执行）
7. scripts/strip_extras_already_in_jars.py（0 引用，已执行）
8. scripts/strip_extras_stubs.py（0 引用，已执行）
9. scripts/scan_aosp_bp_modules.py（0 引用）
10. scripts/check_aosp_src_parity.py（2 历史引用；被 tools/check_source_alignment.py 取代）
11. scripts/check_aosp_extras_breakdown.py（1 历史引用）
12. scripts/check_aosp_extras_sysui.py（1 历史引用）
13. scripts/map_extras_to_modules.py（2 历史引用，含记录其 bug 的 issue）
14. scripts/propose_aosp_to_gradle_mapping.py（1 历史引用）
15. scripts/scaffold_aosp_modules.py（1 历史引用；被 ADR 0003 13-module 拓扑取代）
16. tools/extract_prebuilts.sh（4 产物全部被源码模块取代 + ADR 0002 违规 .sh；删除需先处理 ADR 0002 中的示例引用）

UNCERTAIN（1）：tools/fix_r_imports_to_res.py —— 自声明 disabled 且写明重启前提；等 R-namespace/CONV 现状梳理（Phase C）后复判。

## 11. 验证证据（实际命令）

- `git ls-files tools/ scripts/` → 27 + 14 tracked 文件（`__pycache__` tracked=0）
- `grep -rn --include='*.md' --include='*.kts' <script>` 逐脚本 → 引用证据入表
- `grep -oE '"libs/aars/[^"]+\.aar"' tools/package_aosp_aar.py | sort -u` vs `ls libs/aars/` → 29 vs 29 **集合一致**
- `grep -n "settingslib-flags\|settingslib-media-flags\|device-state" SystemUI-core/build.gradle.kts` → 180/182/256 全 wired
- `git log --diff-filter=D --follow -- tools/<ghost>.py` → 8cb7279b ×3、6741324d ×3
- `git log -1 -- scripts/` → df83e2cd（task 019）；`git log -1 -- tools/` → e69b9bc7（task 057）
- `grep -c "scripts/" AGENTS.md` → 0；docs/README.md 活跃工具表 → 9 个 tools/ 脚本、0 个 scripts/ 脚本
- `git ls-files keystore/` → platform.keystore（tracked，install_keystore.sh 的产物）
- `ls docs/extras-file-mapping.csv` → 存在（61KB，tracked）
- AOSP 路径硬编码 grep → §8 全量清单
- 未运行任何 Gradle 构建（report-only mandate）
