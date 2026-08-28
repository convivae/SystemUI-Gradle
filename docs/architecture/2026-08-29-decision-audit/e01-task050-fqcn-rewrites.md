# E1 — Task 050：79 处 manifest FQCN 手工改写（先例健康度）

status: done
判读: **可接受但需补记录**

## 背景与决策原文

16 时代（2026-08-22，Task 050 Phase A）：AOSP SystemUI manifest 的组件名是相对名
（`.SystemUIApplication`、`SystemUIService` 等）。AGP 把 package-dependent 属性按 `:app`
的 namespace `com.android.systemui.app` 展开，导致 **79 of 95 个打包 manifest 入口类
不在 Debug DEX 中**，运行时 `ClassNotFoundException`（Task 048/049 实证）。

决策（commit `baf5c25d`，分支 `task-050-direct-debug-runtime-closure`；
同内容以 merge-commit `2cb578be`（2026-08-25）落入 main，commit message 为
"docs: record window-flags runtime closure progress"）：

> 将 79 个 package-dependent 入口属性改写为 FQCN（74 dotted + 2 bare `android:name`，
> 2 `android:targetActivity`，1 `android:backupAgent`），语义上与 AOSP 相对名经
> package 展开后等价。

首选项（只把 `:app` namespace 改成 `com.android.systemui`）被拒：

> "AGP 9.3.1 manifest merger rejects two modules sharing one namespace"
> （`baf5c25d` commit message；`app/build.gradle.kts` 注释亦保留错误原文
> "Namespace 'com.android.systemui' is used in multiple modules"）

## 决策链（谁、何时、凭哪份授权）

| 环节 | 证据 |
|---|---|
| 用户泛授权 | `docs/issues/2026-08-22-direct-debug-apk-runtime-closure.md` §"User-authorized operating model"：`app/src/main/AndroidManifest.xml` may be changed / `:app` namespace may be changed |
| orchestration log | `docs/orchestration/log.md` L236：user rejected over-conservative constraints and explicitly authorized direct edits to AOSP manifest/app namespace |
| brief 指明回退路径 | `docs/orchestration/tasks/050-direct-debug-apk-runtime-closure.md` §Execution A.5：build 失败即回退 namespace 实验，"directly rewrite the manifest's package-dependent entry attributes (`android:name`, `android:backupAgent`, `android:targetActivity`) to correct com.android.systemui.* FQCNs" |
| 实施 | commit `baf5c25d`（task-050 分支）→ merge 入 main：`2cb578be`（标题与内容不符，标题只写 docs 记录） |

## 证据链

1. **改写规模**：`git show 2cb578be -- app/src/main/AndroidManifest.xml` →
   新增 FQCN `android:name="com.android.systemui*"` 76 行 + `backupAgent` 1 行 +
   `targetActivity` 2 行 = 79 处属性（与 commit message 的分解 74+2+2+1 一致）。
2. **首选项被拒的本体验证**：commit message + `app/build.gradle.kts` 注释（2cb578be 版）记录了
   merger 错误原文；该错误即后来 task072 issue 引用的 ENFORCE_UNIQUE_PACKAGE_NAMES
   （`docs/issues/2026-08-28-c4-gradle-wiring.md` §3.1）。
3. **验证门**：commit message 报告新工具 `tools/check_manifest_dex_closure.py`
   （纯 Python DEX class-def reader + aapt2 packaged-manifest reader）"PASS (93 present,
   2 activity-alias handles, 0 missing)"。该工具至今仍在 main（`tools/check_manifest_dex_closure.py`）。
   本次审计未重跑（任务禁止 gradle 构建；16 时代 APK 产物已不存在）——PASS 结论按 commit
   message 采信，标注为**未能独立复验**。
4. **16 时代存续**：Task 072 minimal shell 之前（`git show 80be3e58^:app/src/main/AndroidManifest.xml`，
   1157 行）仍有 103 处 `com.android.systemui*` FQCN、0 处相对名（grep 计数）——FQCN 改写贯穿
   整个 16 时代。
5. **无 CONV 标记**：`git show 2cb578be -- app/src/main/AndroidManifest.xml | grep -c CONV` = 0。
   158 行字节被直接替换，未按 ADR 0004（2026-08-07，先于本任务）打 CONV_BEGIN/END。

## 备选路径

1. **namespace 统一**（`:app` namespace = `com.android.systemui`）——被 merger 唯一性检查拒绝（实证）。
2. **FQCN 手工改写**（所选）——语义等价、一次到位；代价是 AOSP 字节失真 79 处、无 CONV 标记。
3. **manifest merger placeholder**（如 `${packageName}`）或 Gradle 构建期 manifest transform——
   Task 049 曾研究 MERGED_MANIFEST transform，被用户在 08-22 否决为过度保守（orchestration log L236）。
4. **把 AOSP manifest 放进 namespace=`com.android.systemui` 的 library**
   （= 17 时代 Task 072 的 D11/D2 方案）——16 时代没有 `SystemUI-application` 这个 bp 结构（那是
   AOSP-17 的新 bp），当时不可行。
5. **参考项目 CarSystemUIGradle 做法**：app namespace 取 `com.android.systemui.car`
   （`app/build.gradle.kts:22`），SystemUI-core namespace 保留 `com.android.systemui`；
   碰到同样的相对名误展开问题（`appComponentFactory=".SystemUIAppComponentFactory"` 被展开到
   `com.android.systemui.car.*`），解法是**把该属性改成 FQCN 并用 JD MOD 注释块标记**
   （`docs/GRADLE_MIGRATION.md` L890–928；SystemUI-core/AndroidManifest.xml 的 JD MOD 块）。
   即参考项目对同一类问题采用的同样是"相对名 → FQCN 手工改写"，且**有改动标记**。

## 优劣分析

优点：
- 语义等价（FQCN = AOSP 相对名 + 正确 package 展开），无运行期行为差异；措施直接、可验证
  （check_manifest_dex_closure.py 门）。
- 用户显式授权（brief + issue），不违反规则 H 的升级纪律。
- 与参考项目做法同构（Car 也是 FQCN 改写应对同类问题）。

缺点/风险：
- **CONV 纪律缺口**：ADR 0004 于 2026-08-07 建立，Task 050 在 2026-08-22，当时已要求
  "res/src 改动用 CONV 标记追溯"。79 处改写零 CONV 标记，
  只靠 build 文件注释与 commit message 追溯，属**可追溯性降级但未越授权**（brief 明确授权了
  这套 edit 本身）。
- **commit message 失真**：`2cb578be` 标题为 "docs: record window-flags runtime closure progress"
  却携带 manifest + build 文件 + 新工具的实质改动（158 行 manifest、12 行 build、194 行工具），
  降低 git 考古可读性。
- **演进债务**：改写把 app manifest 与 AOSP 字节解耦，17 树重对齐时必须整体更换（Task 072 的
  minimal shell + application library 方案正是终结它的动作）。

## 判读与建议

判读：**可接受但需补记录**——授权链完整（用户显式授权 → brief 指明路径 → 实证门），
技术方案正确且有门验证；缺 CONV 标记、merge commit 标题失真属于记录纪律问题，非规则红灯。
作为先例其"相对名展开必须落在 `com.android.systemui` 上"的核心认知被 17 时代 D11 继承并升级。

建议：
- **保持**历史记录不动（已随 Task 072 minimal shell 退役）。
- 如需补记录：在本审计 index/总结中承认两处记录缺口（无 CONV 标记、commit message 失真），
  作为 P 系列流程审计的输入。

## 开放问题

- 是否需要把"FQCN 改写缺 CONV 标记"补写进 Task 050 issue 文档（`docs/issues/2026-08-22-…`）的
  对账段？（历史文档补写，供用户裁决）
</content>
