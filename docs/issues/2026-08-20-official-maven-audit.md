# 2026-08-20 Task 026 官方 Maven 全量审计（report-only）

## 背景

执行官方优先原则（官方 Maven > 本地 jar > 本地 Maven AAR，用户 2026-08-19），审计 `libs/`
全部产物并试替换候选。完整报告：`docs/architecture/2026-08-20-official-maven-audit.md`。

## 操作步骤

1. 盘点：32 jar（libs/ 31 + prebuilts/ 1）+ 17 个 `libs/maven/` AAR = 49 产物（brief 计 48，少计 1 AAR）。
2. 网络证据：对每个产物探测 Google Maven / Maven Central `maven-metadata.xml`（HTTP 200/404），全部亲测记录 URL。
3. 基线：`:app:assembleDebug` → BUILD SUCCESSFUL in 3m 5s。
4. 类集合比对：zxing（本地 ⊂ 官方 3.5.2）；protobuf-nano（本地多 3 个 AOSP 私有 `.android` 类，无引用）；
   dynamicanimation（官方 1.1.0 与 alpha04 类清单 diff 为空）。
5. 试替换 ×3（每次改 catalog/build 文件 → 构建 → `git checkout` 还原）：
   - zxing → `com.google.zxing:core:3.5.2`：PASS（assembleDebug 1m12s + classpath 亲验）
   - protobuf-nano → `com.google.protobuf.nano:protobuf-javanano:3.1.0`：PASS（1m8s + classpath 亲验）
   - unfold dynamicanimation → `androidx.dynamicanimation:dynamicanimation:1.1.0`：PASS（1m + classpath 亲验）
   - keepanno / setupcompat：无官方坐标（各 5/2 URL 404），不试。
6. `python3 -m unittest discover -s tools/tests` → Ran 148 tests, OK。
7. 最终 `git status` 干净（仅报告/brief/本文件入 commit）；未 push。

## 错误数演变

不涉及编译错误治理：基线与三次试替换构建全部 SUCCESSFUL。

## 待解决

- 用户批准后按报告 §6 落地：Batch 1（3 替换 + 3 jar 退役 + tools 条目退役）、Batch 2（git rm ORPHAN `SettingsLib-javac.jar`）。
- zxing 版本二选一：3.5.2（AOSP 对齐）vs 3.5.4（公网最新），待用户定夺。

## 落地记录（Task 027，同日，用户批准后执行）

### zxing 版本决策

- 先试公网 latest stable **3.5.4**：`:SystemUI-unfold:compileDebugKotlin` + `:app:assembleDebug` →
  **BUILD SUCCESSFUL in 1m 10s**，classpath 亲验 `+--- com.google.zxing:core:3.5.4`。
  **采用 3.5.4**（无需回退 3.5.2；审计已证本地 jar 是官方 3.5.2 类子集，3.5.4 同系 API 超集）。

### 落地内容

1. catalog：+`zxingCore = "3.5.4"`、+`protobufJavanano = "3.1.0"` 及两 alias；
2. `SystemUI-core/build.gradle.kts`：zxing/protobuf 两行 `files(...)` → 官方 alias，注释同步改写；
3. `SystemUI-unfold/build.gradle.kts`：`compileOnly(files(alpha04.jar))` → `libs.androidx.dynamicanimation`，alpha04 注释删除；
4. `git rm libs/{zxing-core,libprotobuf-java-nano,dynamicanimation-1.1.0-alpha04,SettingsLib-javac}.jar`（4 个）;
5. `tools/package_aconfig_jars.py`：退役 ZXING_CORE_JAVAC/CONFIGS 条目；对应测试 `test_zxing_core_config` 删除（148→147 用例）；
6. 清理：AGENTS.md §3.2 libs 树删 `libprotobuf-java-nano.jar` 行；HANDOFF.md libs 列表同步。
   历史 issue/plan/brief/GRADLE_MIGRATION_LOG/2026-07 架构文档中的引用为历史记录，保留不改。

### 验证

- `:SystemUI-unfold:compileDebugKotlin` + `:app:assembleDebug` → BUILD SUCCESSFUL in 1m 10s（216 tasks）；
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → Ran 147 tests, OK；
- 残留 grep：活动文件无残留（仅任务 brief 自身与历史文档引用）。

### 错误数演变

无新增编译错误；全量构建保持 SUCCESSFUL。
