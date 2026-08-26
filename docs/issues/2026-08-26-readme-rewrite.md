# 2026-08-26 — Task 066：README.md / README.en.md 重写（Phase D 主体）

**任务**: `docs/orchestration/tasks/066-readme-rewrite.md`
**性质**: docs-only（无 Gradle、无代码改动）。

## 1. 背景

旧 README（中/英，2026-08-21 版）写于 Release closure 完成但 runtime 验证未做之时，
"装机验证 ⏳ 尚未进行" 已过时：2026-08-25 达成 DEBUG_RUNTIME_PASS（Task 058）、
2026-08-26 达成 RELEASE_RUNTIME_PASS（Task 061）并完成 062–065 清理与再生管线闭环。
README 需要整体重写为仓库门面：真实现状 + AOSP 版本声明 + 从零复现 Quickstart。

## 2. 写前事实核验（全部当场实测，非转抄）

| 事实 | 核验命令 | 结果 |
|---|---|---|
| pytest 数 | `uv run pytest tools/tests/ -q` | **276 passed + 102 subtests**（69.57s） |
| AOSP 树体积 | `du -sh /home/conv/myspace/aosp` | 418G（其中 `out/` 187G） |
| 内存/swap | `free -h` | 30Gi RAM + 8.0Gi swap |
| Gradle wrapper | `gradle/wrapper/gradle-wrapper.properties` | 9.5.0，腾讯镜像 URL 生效 |
| Maven 镜像 | `settings.gradle.kts` L3-7/L24-26 | 腾讯 nexus + 阿里云 google/gradle-plugin/public |
| manifest 快照 | `grep -c '<project' docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml` | **1042** |
| libs 文件数 | `git ls-files libs` | 104（29 jar + 52 aar + 23 pom） |
| 产物脚本 | `ls tools/*.py` | build_sysuisdk / package_aosp_aar / install_aar_to_maven / package_aconfig_jars / package_misc_jars / package_compilelib_jars / package_monet_jar / package_viewcapture_motiontool_jars 全部存在 |
| 引用文档存在性 | 逐个 `ls` | HANDOFF / CURRENT_STATE / PLAN / PITFALLS（§14 存在）/ docs/README.md / runbook / 再生报告 / SysUISdk 架构文档 全部存在 |

版本矩阵取自 `docs/CURRENT_STATE.md`（Gradle 9.5.0 / AGP 9.3.1 / Kotlin 2.2.10 builtInKotlin /
KSP 2.2.10-2.0.2 / Dagger 2.59.2 / Compose 1.11.4 / material3 1.5.0-alpha18 / JDK 21 /
compileSdkPreview SysUISdk）。

## 3. 产出

1. `README.md`（中文）整体重写
2. `README.en.md`（英文）等价重写
3. `docs/aosp-pinning/README.md`（新增）：解释 manifest 快照文件的生成方式与用途

## 4. 决策记录

- **"Phase C" 指向**：brief 要求写 "见 docs/PLAN.md Phase C"，但 PLAN.md 无字面 "Phase C"
  标题；Phase C 在 062–065 系列文档中指"全管线从零复现/重跑"阶段。README 措辞为
  "已规划的后续工程（Phase C，全管线从零复现；见 docs/PLAN.md 与
  docs/architecture/2026-08-26-regeneration-gap-closure.md）"，保证引用可落地。
- **JDK 版本**：brief 写 "JDK 17+"，CURRENT_STATE 工具链为 JDK 21。README 写
  "JDK 17+（项目工具链实测 JDK 21）"。
- **Release 基线**：Task 061 的 `14768581…` 已被 Task 065 jar 替换后的 `d3968fb2…`
  （34,688,965 B，同尺寸）取代；README 状态摘要引用 **d3968fb2**（当前基线、当前设备终态），
  过程历史（14768581）不进 README，归 CURRENT_STATE/log。
- **pytest 命令**：按用户 2026-08-25 规则写 `uv run pytest tools/tests/ -q`（而非 python3 -m unittest）。
- **License**：仓库无 LICENSE 文件；沿用旧 README 表述"Apache License 2.0，与 AOSP 一致"
  （源码主体来自 AOSP SystemUI）。
- **内部开发标识**：不写入 README（task 046 既有纪律：对外 README 省略内部开发标识）；
  emulator 实例路径等细节只留在 runbook，README 指向文档。

## 5. 构建记录

**Gradle 构建：未运行**（brief 明确 docs-only、不跑 Gradle）。验证 = pytest 276 passed +
引用路径存在性自查（§2）。

## 6. 遗留

无（README 属对外摘要，动态数字以后随对外里程碑更新，见 `docs/README.md` 维护触发表）。
