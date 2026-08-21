# 2026-08-21 — SysUISdk 单入口 AOSP composition（Task 045）

## Background

旧 `tools/build_sysuisdk.py` 通过 S0–S5 分阶段流水线、仓库 payload blobs
（`libs/android-merged.jar`、`libs/framework-res.apk`）、helper 脚本
（`install_sdk.py`、`patch_sdk_*.py`）、`--apply` 与永久备份文件来复现并 patch
legacy live SDK。用户已批准（2026-08-21）以单一事务性生成器替换该模型：
消费只读官方 SDK platform + 已构建的 AOSP `out/` 产物。

架构与冻结 artifact 映射：
`docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`。

## Approved outcome

```bash
python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp
```

默认输出 `<sdk-root>/platforms/android-SysUISdk`；纯 Python 标准库 ZIP/文件操作；
不调用 Soong；不 patch 官方 base；无 S0–S5/`--apply`/restore/备份接口。

## TDD execution record（RED/GREEN 摘要）

基线（pre-change contract）：legacy focused suite 53/53 OK；full suite 239/239 OK
（仅作证据，不构成新设计证明）。

| Plan step | RED 证据（实现前真实失败） | GREEN 结果 |
|---|---|---|
| 2 CLI/discovery | 20 tests 全部 AttributeError（新契约不存在） | 20/20 OK |
| 4 inputs/AIDL | 12 tests AttributeError（`resolve_inputs`/`derive_aidl_declaration` 缺失） | 32/32 OK |
| 6 composition | 13 tests AttributeError（`compose_android_jar`/`compose_core_modules_jar` 缺失； harness str/Path bug 修复后用 feature 删除法重新验证纯 RED：13/13 AttributeError） | 45/45 OK |
| 8 bridge | 9 tests AttributeError（`BRIDGE_ENTRIES`/`load_bridge` 缺失） | 54/54 OK |
| 10 transaction | 16 tests AttributeError（`build_platform`/`run`/`_validate_platform` 缺失；fixture 幂等修复后转绿） | 70/70 OK |

Step 12 full gate：`python3 -m unittest discover -s tools/tests -p 'test_*.py'`
→ **256 tests OK**（239 − 53 legacy + 70 new；≥200 ✓）。

## Real AOSP builds（Step 13）

私有 SDK roots `/tmp/task045-sdk-a`、`/tmp/task045-sdk-b`（各含官方
`android-37.0` 的只读副本作为 base；官方 SDK 未改动）：

```bash
python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp --sdk-root /tmp/task045-sdk-a
python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp --sdk-root /tmp/task045-sdk-b
```

两次均 exit 0（各约 7s）。**确定性证明**：两个输出的完整相对文件清单 + SHA-256
完全相等（11382 个文件，含 marker）。marker 只含 stock-base/AOSP provenance
（无绝对主机路径）。两个 target JAR 均含且仅含冻结 39-entry bridge（源字节一致，
独立于工具自身常量、由 legacy Task 041 allowlist + core-libart 差集重新推导验证）；
resources（8203 entries）与 AIDL 均字节校验通过；无备份文件。

拒绝/替换语义实测：未标记已存在输出 → 拒绝（exit 1）；已标记输出无 `--replace`
→ 拒绝；`--replace` 成功替换且替换后与 sdk-b 仍逐字节相等。

## AOSP 输入与生成产物 SHA-256

| 项 | SHA-256 |
|---|---|
| framework turbine aggregate | `0fe39d800f34f6c7b17e5c936571bc29367e1329c8af9c6ab47e894beb05be26` |
| framework-res.apk | `7e76ce7d9de50d47a47396d36f4d0fd10a9d15048b6aef498d7ad434b018bef7` |
| core-libart.jar | `decb349c4a27c33ce7e668e45bca3a9ca0382de9dd62f8f24c562aefdcd119af` |
| unsupportedappusage.jar | `25d4fe4e49731df2822efb0a6bfaef867da00dbfe2b1df40607c9eddd7cf2912` |
| aconfig-annotations-lib.jar | `ef431f923f6925ec835282afb3ee62c909987dd2f053dbcdccc1f7294923f551` |
| keepanno-annotations.jar (AOSP) | `056412aa7731b573f06940c792db082859ad49e464be08f464a4bba52fd856c5` |
| IRemoteCallback.aidl | `31120af262690e1d7f4dd4f2befdcca13c4fa30ed10278bfdc722c31298e0b2a` |
| ScreenshotRequest.aidl | `546b69d24adfba6c0796deecd63f6b6c84d817b0612fa0f4678f8a12c89a115a` |
| base android.jar (android-37.0) | `06893f4a316277dfe8c8fe42d4a25552b4e84be474d8c7ea7d34b6ddc26e2ad6` |
| 生成 android.jar | `c01a910ac61b7b9a6a45271c7237a7264a5c0ab02cfd83c165f31ae39d78791d` |
| 生成 core-for-system-modules.jar | `e7bc0115d4e276245ac2ef40789cc7d03033f5419613a1c31999e45129a69c5d` |
| 生成 framework.aidl | `d0497fdc8ce140a04e7c64ec3fee6aa2b6836a9e47cba021e16be1c80464962e` |

## Gradle gates（Steps 14–16，生成 SDK 位于 /tmp/task045-sdk-a）

私有 root 通过 symlink 暴露官方 build-tools/platform-tools/cmdline-tools/licenses
（未复制、未修改官方 SDK）；worktree 忽略文件 `local.properties` 临时指向该 root，
事后按原始状态恢复（原文件不存在 → 删除）。

- **Debug**：`./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug
  -Dorg.gradle.workers.max=4 --console=plain` → pipeline exit 0，
  `BUILD SUCCESSFUL in 2m 57s`（216 tasks）。日志 `/tmp/task045-debug.log`。
- **Fresh R8**：`./gradlew :app:minifyReleaseWithR8 --rerun-tasks ...` →
  pipeline exit 0，`BUILD SUCCESSFUL in 3m 14s`，**Missing class 0**。
  日志 `/tmp/task045-r8.log`。
- **完整 Release**：`./gradlew :app:assembleRelease --no-daemon ...` →
  pipeline exit 0，`BUILD SUCCESSFUL in 3m 55s`；日志实际执行
  `optimizeReleaseResources` 与 `convertShrunkResourcesToBinaryRelease`。
  日志 `/tmp/task045-release.log`。
- **APK gate**：`app-release.apk` 28,600,808 B，SHA-256
  `d53f815ca9a72570f3be55e3f9bd25f1ac64c9c166adca6c2adf886fb7f9a14f`；
  `unzip -t` 无错；V2 scheme **true**（v1/v3 false，与既有签名配置一致）；
  dexdump 全量 15,683 defined classes 中 **0/39** bridge FQN、无
  `AssumeTrueForR8`。

无 REDLINE：冻结 artifact map 一次编译通过，未扩任何输入族。

## 删除（Step 17，全部功能门禁通过后）

仅删除七个已批准路径（git commit `76ad180f`）：
`libs/android-merged.jar`、`libs/framework-res.apk`、`tools/install_sdk.py`、
`tools/patch_sdk_dalvik_annotations.py`、`tools/patch_sdk_r8_library_classes.py`、
`tools/tests/test_patch_sdk_dalvik_annotations.py`、
`tools/tests/test_patch_sdk_r8_library_classes.py`。

`libs/keepanno-annotations.jar` **保留**（`:SystemUI-core` 独立 compile-only 依赖，
非 SysUISdk 输入）。删除前 grep 确认 active code/config 无引用（tools/ 与全部
Gradle 文件）；剩余 `framework-res.apk` 字样均为冻结 AOSP 相对路径映射，非仓库
payload。外部 legacy live SysUISdk 的 9 个历史备份未触碰（需单独的不可逆删除审批）。

残留文档引用（归 architect/用户处理，本 Worker 无权修改）：
`AGENTS.md` §7 表格仍列 `tools/install_sdk.py`；`README.md` 未查改。

## 删除后回归（Step 18）

- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → **220 tests OK**
  （256 − 36 个被删 patch 测试；≥200 ✓）。
- Debug 硬门禁重跑 → pipeline exit 0，`BUILD SUCCESSFUL`（214 up-to-date +
  2 executed；被删路径本就不是 Gradle 输入）。
- `git diff --check` 无 whitespace 错误；`local.properties` 恢复为原始缺失状态。

## Boundaries 遵守情况

- 未改任何 SystemUI 源码/AIDL mirror/res；未改任何 Gradle 配置/依赖/版本/模块。
- 未调用 Soong；AOSP 树只读。
- 官方 `android-37.0` 与 legacy live `android-SysUISdk` 均未触碰。
- 未创建非 Python 脚本；无 stub；无 suppress。
- 设备/模拟器 install+runtime 验证：**仍未运行，明确 deferred**。

## 失败/偏差记录

- Step 6 首次 RED 运行中 6 个测试因 test harness 的 str/Path 错误先于
  AttributeError 失败（harness bug，非 feature 缺失证据）；修复 harness 后用
  "删除 feature 属性重跑" 方法补取纯 RED（13/13 AttributeError）。该偏差已如实
  记录，最终测试均在实现存在/缺失两态下分别验证过。
- 无 OOM 或其他环境事件；所有 heavy 命令均带
  `-Dorg.gradle.workers.max=4`、`set -o pipefail`、`tee`。

## Commits

- `991b6302` tools: rewrite build_sysuisdk.py as single-entry AOSP composition
- `76ad180f` tools: delete superseded SysUISdk payloads and patch helpers
- （文档更新 commit 见 git log）
