# Task 027 — 官方依赖落地 + 彻底清理（w026 延续任务）

## Goal

在 task-026 审计基础上落地替换并做**彻底清理**（用户 2026-08-20 指示：
替换官方坐标后，删掉被取代的 jar、删掉为这些 jar 写的配套配置/工具条目/注释）。

## 范围

### A. Batch 1 — 3 处替换落地

1. catalog（`gradle/libs.versions.toml`）增：
   - `com.google.zxing:core` — **先试用公网最新（3.5.4+，查 maven-metadata 取最新 stable）**：
     落地后全量构建通过则用最新；若编译/测试失败，回退 AOSP 钉版 3.5.2 并在 issue 记录原因
   - `com.google.protobuf.nano:protobuf-javanano:3.1.0`
2. `SystemUI-core/build.gradle.kts`：两行 `files(...)`（zxing-core.jar、libprotobuf-java-nano.jar）
   换 catalog alias；更新周边注释（删除"本地 jar"措辞，改为官方坐标说明）；
3. `SystemUI-unfold/build.gradle.kts`：`compileOnly(files("libs/dynamicanimation-1.1.0-alpha04.jar"))`
   换 `libs.androidx.dynamicanimation`（catalog 已有 1.1.0）；删除该处关于 alpha04 的注释
   （审计已证官方 1.1.0 与 alpha04 class 清单逐字节一致，消除编译/运行版本混挂）；
4. `git rm libs/zxing-core.jar libs/libprotobuf-java-nano.jar libs/dynamicanimation-1.1.0-alpha04.jar`；
5. `tools/package_aconfig_jars.py`：退役 zxing 打包条目（ZXING_CORE_JAVAC 常量、
   AOSP_ZXING 路径、映射表行），同步更新其 docstring/测试（如有断言该条目）。

### B. Batch 2 — orphan 清理

6. `git rm libs/SettingsLib-javac.jar`（审计证实无任何消费点）。

### C. 配套清理（用户明确要求的"彻底"）

7. `git grep -n "zxing-core.jar\|libprotobuf-java-nano\|dynamicanimation-1.1.0-alpha04\|SettingsLib-javac"`
   全仓扫描，清理所有引用：build 注释、docs 列表（AGENTS.md §3.2 libs 树中
   `libprotobuf-java-nano.jar` 行等）、PITFALLS/HANDOFF 中过时描述（只改与本次替换直接相关的行，
   历史 issue 文档不动）；
8. AGENTS.md §3.2 libs 树同步（删 3 个退役 jar + SettingsLib-javac.jar 行）。

## Non-goals

- 不动其余 44 个产物（keepanno、settingslib 家族等维持原形态）；
- 不动源码、res、SysUISdk；
- 不顺手升级其他依赖版本。

## Allowed Paths

- `gradle/libs.versions.toml`、`SystemUI-core/build.gradle.kts`、`SystemUI-unfold/build.gradle.kts`
- `libs/zxing-core.jar`、`libs/libprotobuf-java-nano.jar`、`libs/dynamicanimation-1.1.0-alpha04.jar`、
  `libs/SettingsLib-javac.jar`（删除）
- `tools/package_aconfig_jars.py`（仅 zxing 条目退役）+ `tools/tests/` 对应测试
- `AGENTS.md`（§3.2 libs 树 4 行）
- `docs/issues/2026-08-20-official-maven-audit.md`（追加落地记录）或新建 issue
- `docs/orchestration/tasks/027-official-deps-landing.md`（本文件勾选）

## Forbidden Paths

其它一切（尤其：app/、settings.gradle.kts、SysUISdk、其他模块 build 文件）。

## Acceptance

- `:app:assembleDebug` BUILD SUCCESSFUL；
- `:SystemUI-unfold:compileDebugKotlin` BUILD SUCCESSFUL；
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` 全 OK；
- `git grep "zxing-core.jar\|libprotobuf-java-nano\|dynamicanimation-1.1.0-alpha04\|SettingsLib-javac"`
  无残留（历史 issue 文档除外）；
- zxing 版本选择结果（3.5.4 成功 或 回退 3.5.2 + 原因）写入 issue；
- 英文 commit；不 push。

## Report

完成后汇报：commit、zxing 最终版本及理由、删除清单、验证输出、issue 更新、HANDOFF 块。

## Completion (2026-08-20)

- [x] A1 catalog 增 zxing（**最终 3.5.4**：latest stable 全量构建通过，未回退）+ protobuf-javanano 3.1.0
- [x] A2 core 两行 files(...) → 官方 alias，注释更新
- [x] A3 unfold compileOnly → libs.androidx.dynamicanimation，alpha04 注释删除
- [x] A4 `git rm` 4 个 jar（3 退役 + SettingsLib-javac.jar orphan）
- [x] A5 tools/package_aconfig_jars.py zxing 条目退役 + 测试同步（148→147 用例）
- [x] B6 orphan 清理（并入 A4）
- [x] C7 全仓引用清理（AGENTS.md §3.2、HANDOFF.md；历史文档按规则保留）
- [x] C8 AGENTS.md §3.2 libs 树同步（1 行删除；其余 3 jar 原本不在树中）
- 验证：`:SystemUI-unfold:compileDebugKotlin :app:assembleDebug` → BUILD SUCCESSFUL in 1m 10s；unittest → Ran 147 tests, OK；residue grep 仅剩 brief 自身与历史文档
