# Task 044 Brief — Narrow `AssumeTrueForR8` Release R8 Adapter

> **执行模式 / Authority**: `redline-gated`, self-commit, never push
> **Reports To**: main-worktree chief architect
> **必读顺序**: worker-contract → `AGENTS.md` → `docs/orchestration/CHARTER.md`
> → 本 brief → `docs/superpowers/specs/2026-08-21-gradle-native-systemui-build-design.md`
> → `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`
> → `docs/superpowers/plans/2026-08-21-r8-aconfig-narrow-dontwarn.md`
>
> 开始工作前必须输出完整 `CONTRACT:` 块。

## Authority and approved red-line boundary

用户已于 2026-08-21 明确选择并批准 option A：仅为 Release R8 增加一条精确规则：

```proguard
-dontwarn com.android.aconfig.annotations.AssumeTrueForR8
```

该单 FQN suppression 及其 release-only Gradle wiring 是本 brief 唯一预批准的 build-behavior
红线。禁止扩大到 wildcard/package、其他 class、annotation artifact、SysUISdk 或 assumption
rules。Task 042 的 S3c + byte-exact AOSP rule-file 方案已在实施前否决，不得复活。

## Goal

以项目自有的最小 Gradle adapter 关闭 fresh Release R8 的唯一 missing ref，使：

- fresh missing refs 精确 **1→0**；
- debug duplicate-class / assembly hard gate 保持成功；
- `minifyReleaseWithR8` 和完整 `assembleRelease` 首次成功；
- resource shrinking 执行，Release APK 不含 annotation class，APK V2 签名有效；
- 不改变 aconfig flag runtime 语义，不引入 AOSP flag-folding assumptions。

## Allowed Paths

### Implementation and tests

- `app/proguard_gradle.flags`（新建；comments + 唯一 active rule）
- `app/build.gradle.kts`（仅在 `release.proguardFiles(...)` 增加上述文件）
- `tools/tests/test_gradle_r8_adapter_rules.py`（新建）

### Evidence and current state

- `docs/issues/2026-08-21-r8-aconfig-narrow-dontwarn.md`
- `docs/CURRENT_STATE.md`（仅按真实结果更新 R8/Release/device 状态）

### Generated outputs

- `app/build/**`、`.gradle/**` 与 `/tmp/task044-*` 可由命令生成，但不得 commit。

## Forbidden Paths and actions

- 五个现有规则文件：`app/proguard.flags`、`app/proguard_common.flags`、
  `app/proguard_kotlin.flags`、`SystemUI-plugin-core/proguard.flags`、
  `SystemUI-plugin/proguard_plugins.flags`
- `tools/build_sysuisdk.py`、任何 SysUISdk stage/live SDK 修改
- 任何 `libs/**`、catalog、dependency、version、artifact、Maven/POM、manifest 或 module boundary
- 所有 `SystemUI-*/src/**`、`SystemUI-*/res*/**`、AOSP source/output
- `AGENTS.md`、ADR、architecture spec/audit、CHARTER、STATE、log、Task 042 文档
- annotation class/JAR/AAR、S3c、AOSP `aconfig_proguard.flags` 的完整或部分导入
- wildcard/package `dontwarn`、第二条 suppression、`keep`、`assumevalues`、
  `assumenosideeffects`、关闭 R8/shrink/check、源码排除、private AGP hook
- debug wiring；push；未获批准的追加修复

## Required execution order

1. Fresh pre-change `minifyReleaseWithR8 --rerun-tasks`，保存真实 exit 和日志；机械断言
   singleton missing set 恰为 `AssumeTrueForR8`。
2. TDD RED：先新建 focused Python test，因 adapter file 不存在而失败。
3. 最小 GREEN：新建 exact rule file，只在 release wiring；focused + full Python tests 成功。
4. 提交英文 focused implementation commit。
5. serialized debug duplicate-class + assembly hard gate。
6. fresh Release R8 成功；missing refs 为 0；effective config 对该 FQN 只有一个 exact
   `dontwarn`，无 assumption treatment。
7. 完整 `assembleRelease`；确认 shrink task、APK ZIP、annotation class 不打包、V2 签名。
8. 只按真实输出更新 issue 和 `docs/CURRENT_STATE.md`，提交英文 docs commit。
9. `git diff --check`、终态路径检查和完整 `HANDOFF:`；Worker 不 push。

## Command-based Acceptance

全部必须真实满足：

1. Pre-change：带 `set -o pipefail`/`tee` 的 fresh
   `:app:minifyReleaseWithR8 --rerun-tasks` real exit `1`；generated missing set 精确为：
   `{com.android.aconfig.annotations.AssumeTrueForR8}`。
2. TDD RED 已保存：`python3 -m unittest tools.tests.test_gradle_r8_adapter_rules -v` 非 0，
   原因是批准的 adapter file/contract 尚不存在。
3. `app/proguard_gradle.flags` 去注释/空行后恰一行 exact rule；无 `**`、keep 或 assume；
   release 引用恰一次，debug 引用 0 次，其他 app rule files 对该 FQN active rule 为 0。
4. Focused test 及
   `python3 -m unittest discover -s tools/tests -p 'test_*.py' -v` 均 exit 0。
5. `set -o pipefail; ./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug
   --console=plain -Dorg.gradle.workers.max=4 | tee ...` real exit 0 且 `BUILD SUCCESSFUL`。
6. Fresh post-change `:app:minifyReleaseWithR8 --rerun-tasks` real exit 0；missing refs 0；
   `configuration.txt` 对 FQN 只有 exact `-dontwarn`，无 keep/assume treatment。
7. `:app:assembleRelease` real exit 0 且 `BUILD SUCCESSFUL`；日志出现
   `:app:shrinkReleaseRes`；`app/build/outputs/apk/release/app-release.apk` 非空且 `unzip -t`
   成功。
8. Android SDK `apkanalyzer dex packages` 输出不含
   `com.android.aconfig.annotations.AssumeTrueForR8`；输出 `PACKAGED=0` 证据。
9. Android SDK `apksigner verify --verbose --print-certs` exit 0，并明确显示 V2 scheme `true`。
10. Issue 记录真实 exits/test count/hash/size/results；`docs/CURRENT_STATE.md` 区分 Release build
    成功与 device smoke test deferred。不得暗示已装机运行。
11. 最终两类 focused 英文 commit；所有 changed paths 属于 Allowed Paths；generated outputs
    未 commit；`git diff --check` 无输出；Worker 未 push。

## REDLINE conditions

以下任一出现立即停止，不扩大 scope：

- baseline 不是 exact singleton 或 failure 未到 R8 missing-reference diagnostics；
- TDD RED 原因不是 adapter contract 缺失；
- 新 missing ref 出现，R8 仍失败，或需要另一条/更宽规则；
- effective config 出现该 FQN 的 keep/assume/重复 treatment；
- debug、duplicate class、shrink、Release package、APK class absence 或签名 gate 失败；
- 需要修改 Forbidden Path、class/JAR/AAR、SysUISdk、dependency、source、resource、artifact、
  version、manifest、module boundary 或现有 AOSP rule file；
- 工具/输出格式不同，以至于必须削弱 acceptance；
- 所有合规尝试失败。

`REDLINE:` 报告必须包含已验证事实、命令真实 exit、当前 diff/commit 状态和建议；禁止自行
切换 option B/C 或恢复 Task 042。

## Completion report

成功时 terminal-final 必须输出：

```text
HANDOFF:
- done: exact release-only AssumeTrueForR8 adapter and truthful current-state update
- verified: focused RED/GREEN, full Python tests, debug gate, R8 1→0, full shrunk Release, APK class absence, V2 signature
- remaining: compatible-device install/SystemUI restart/runtime smoke test; or exact blocker
```
