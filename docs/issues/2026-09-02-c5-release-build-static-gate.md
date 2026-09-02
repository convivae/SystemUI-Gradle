# C5 Task 097：fresh Release APK build/R8/static gate

**日期**：2026-09-02
**状态**：PASS（fresh Release build/R8/static closure；不声明runtime）
**前置**：Task 095 production immutable-input seam已在`2994fa8f`落地；Task 096 fresh Debug build/static gate已PASS并由`7c0f4f0c`完成durable closure。

## 背景

Task 096已证明完整Debug APK包含四条runtime-critical hidden references、全725规则hidden target definitions为0，并通过old-owner residual gate。但Debug不经过Release shrinking/optimization，不能证明R8后的descriptor closure。当前磁盘上的旧Release APK仍来自production rewrite接入前，其checker为`RESULT=FAIL`，不得用于验收。

本任务是独立、no-fix、单Gradle调用的fresh Release build/R8/static gate。它不启动设备、不运行Debug、不修改production或checker，也不恢复Task 079 broad replay。

## 计划与验收

1. 只读确认`HEAD == origin/main`、`7c0f4f0c`为ancestor、tracked worktree clean且无Gradle/Kotlin/Soong/Ninja活动进程。
2. 建立`/tmp/task097-c5-release-build-static/`并冻结preflight；删除仅生成物`app/build/outputs/apk/release/app-release.apk`，防止失败后误收旧APK。
3. 全程仅运行一次Gradle wrapper：
   ```bash
   ./gradlew :app:assembleRelease --console=plain --rerun-tasks --max-workers=4
   ```
   用`set -o pipefail`保存真实exit code和完整日志。失败即停止，不做修复。
4. 成功后记录APK size/SHA-256、`unzip -t`结果和DEX清单；日志必须包含`BUILD SUCCESSFUL`，且`:app:minifyReleaseWithR8`与`:app:packageRelease`实际执行而非沿用旧产物。
5. 使用authoritative AOSP `repackaging.txt`运行`tools/check_aconfig_jarjar_references.py`。Release静态PASS要求checker exit 0、`RESULT=PASS`、四个critical source descriptors全部`referenced=no, defined=no`、四个critical hidden targets全部`referenced=yes, defined=no`，且全725条hidden target definitions为0。
6. 记录R8 mapping/configuration/missing-rules等存在性与身份，仅作诊断；不得将任何旧输出冒充当前build证据。
7. 保存tracked status并执行一次冻结cleanup；不commit、不push。

## 成功边界

PASS仅表示fresh Release APK完成R8且四映射静态闭合。它不证明部署、runtime或整机重启稳定，也不授权修改visitor、R8规则或checker。PASS后依次另立Debug runtime与Release runtime任务。

## 错误数演变与待解决问题

- 旧Release APK：critical old sources referenced，hidden targets `0/4`，checker FAIL。
- Task 096 Debug APK：hidden targets `4/4`、hidden target definitions 0、old-owner residual PASS。
- 本任务必须证明R8后的fresh Release APK达到checker严格PASS；失败时保留首个actionable failure和全部静态证据，由Chief另立修复任务，本任务自身不改代码。

## 执行结果（2026-09-02）

- fresh replacement `task097-release-r3`在pushed base `1420c7c5`上执行；session独立证明`joycode/GLM-5.3`、`thinking=high`、`HERDR_ENV=1`，startup严格串行。
- 唯一Gradle-wrapper调用为冻结的`:app:assembleRelease --console=plain --rerun-tasks --max-workers=4`；exit 0，`BUILD SUCCESSFUL in 7m 5s`，`493 actionable tasks: 493 executed`。
- `:app:minifyReleaseWithR8`与`:app:packageRelease`均实际执行，不是`UP-TO-DATE`、`FROM-CACHE`或skipped。
- fresh APK：`app/build/outputs/apk/release/app-release.apk`，45,030,130 B，SHA-256 `641c6533e78a5977f2d8de97f293be236976e1053b40ff3a05a182bc594a1756`；`unzip -t` exit 0，2 DEX。
- authoritative checker exit 0且`RESULT=PASS`：四个critical old source descriptors均`referenced=no, defined=no`；四个hidden targets均`referenced=yes, defined=no`；全725条规则hidden target definitions为0。
- final worktree clean，Chief独立确认无Java/Gradle/Kotlin/Soong/Ninja残留进程。证据根：`/tmp/task097-c5-release-build-static/`。
- 已披露cleanup过程偏差：第一条冻结`pkill -f`以内联形式执行并self-match杀死shell，因此其exit code丢失；该命令只执行一次，后两条各执行一次并返回1。最终独立process census为零。该偏差不改变fresh build、APK或checker技术PASS，也不声明runtime成功。

下一步严格串行执行fresh Debug APK runtime reboot gate，再执行fresh Release APK runtime reboot gate。
