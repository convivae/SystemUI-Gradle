# 2026-08-20 — R8 Runtime Closure Batch 1: Pure Scope Corrections (Task 033)

## 背景

Task 030 开启 release R8（`isMinifyEnabled=true` + `isShrinkResources=true`）后，
`:app:minifyReleaseWithR8` 失败于 140 个 missing class（`missing_rules.txt`）。
Task 031 逐类审计（`docs/architecture/2026-08-20-r8-runtime-closure-audit.md`）将
140 类归属为 A 类（真实 APK runtime 闭包缺失，135）+ B 类（非 runtime，5），
并给出 7 个依赖序实施批次。用户已在 Task 030 后批准全部 A 类结构性闭包修复。

本任务实施 **Batch 1（纯 scope 翻转，零重打包）**：把四个产物形态已验证纯净的
tier② AOSP jar 由 `compileOnly` 改为 `implementation`，使其进入 APK program/runtime
闭包（D8 debug dex + R8 release 输入）。

## 四条 Soong 边（AOSP Android.bp 证据，Task 031 审计实测）

| jar | owning Soong module | 通向 SystemUI 的 edge | 审计组 |
|---|---|---|---|
| `libs/msdl.jar` | `msdl`（`frameworks/libs/systemui/msdllib/Android.bp:21`） | SystemUISharedLib `static_libs` `:msdl`（`shared/Android.bp:72`） | A10（6 类） |
| `libs/monet.jar` | `monet`（`frameworks/libs/systemui/monet/Android.bp:22`）+ `libmonet`（`external/libmonet`） | SystemUI-core `static_libs`（bp L494-495） | A6（7 类；jar 另含 27 个 errorprone 注解类，属 AOSP static 闭包，保留不剥离） |
| `libs/wifi-flags.jar` | `wifi_aconfig_flags_lib`（`WifiTrackerLib/Android.bp:28` static） | WifiTrackerLib → SystemUI-core（bp L447） | A12（1 类） |
| `libs/wm-shell-flags.jar` | `com_android_wm_shell_flags_lib`（`Shell/aconfig/Android.bp:11`，WM-Shell static L186） | WM-Shell → SystemUI-core（bp L448） | A12（1 类） |

`static_libs` = AOSP APK 打包闭包 → Gradle 正确映射是 `implementation(files(...))`
（program 输入）。四 jar 产物纯净性已在 Task 031 逐一 `unzip -l` 实测（msdl 46 类全
`com/google/android/msdl`；monet 83 类 = monet+libmonet 56 + errorprone 27；两个 flags
jar 各含完整 5 类生成 runtime 集，与 AAR 无重复）。

## 允许的改动（本任务全部）

1. `SystemUI-core/build.gradle.kts`：仅上述四行 `compileOnly` → `implementation`，
   并修正相邻注释（原注释误称 wifi/wm-shell flags "平台镜像在设备上提供，仅编译期需要"）。
2. 本 issue 文档（新建）。

**不得改动**：`view_capture.jar`、`motion_tool_lib.jar`、`TraceurCommon.jar`、
`traceur-res-R.jar`、`keepanno-annotations.jar` 维持 `compileOnly`（分属 Batch 3/4/6）；
任何 JAR/AAR/本地 Maven/catalog/版本/模块/SysUISdk/源码/res/keep 规则/dontwarn 均不动。

## 验证命令

```bash
git diff --check
python3 -m unittest discover -s tools/tests -p 'test_*.py'
./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4
/home/conv/Android/Sdk/cmdline-tools/latest/bin/apkanalyzer dex packages --defined-only \
    app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4
```

## 错误数演变

- **Pre-change 基线**：release R8 missing_rules = **140**（Task 030 实测存档）。
  Batch 1 预测翻转后 **125**（140 − A6 7 − A10 6 − A12 2）——此为闭包推算预测值，
  以实施后实际测量为准（新 missing class 不是可接受的计划内遗漏，须停下报告）。
- Pre-change scope 断言（Python，读 `SystemUI-core/build.gradle.kts`）：
  `pre-change: target compileOnly=4, implementation=0`（exit=1，目标状态未达，符合预期）。

### 实施后实测（2026-08-20，REDLINE 阻塞）

- Post-change scope 断言：`target implementation=4`、`target compileOnly=0`、
  `deferred compileOnly=5/5`、`deferred implementation=0`（ASSERTION: PASS，exit=0）。
- `git diff --check`：干净（DIFF_CHECK_OK）。
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`：**Ran 147 tests / OK**。
- `./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4`：
  **BUILD FAILED**（11s，`Task :app:checkDebugDuplicateClasses` 失败）——
  **27 条 Duplicate class 错误，全部且仅涉及 monet.jar**：
  `monet.jar` 携带的 27 个 `com.google.errorprone.annotations.**` 类与
  `com.google.errorprone:error_prone_annotations:2.50.0`（官方 Maven 运行时传递依赖）
  完全重叠（comm 实测 overlap=27；Maven 版另含 3 个 monet 没有的类）。
  APK 未生成；apkanalyzer 抽查与 `minifyReleaseWithR8` 测量因此未执行。

### 根因（systematic-debugging Phase 1 完成）

- `monet.jar` 是携带 static 闭包的 FAT 产物：AOSP `external/libmonet/Android.bp` 的
  `static_libs: ["error_prone_annotations"]` 被打进 jar（Task 031 审计已记录 27 类，
  但其“无其他产物重复（实测）”仅对 `libs/` 本地产物比对，未覆盖官方 Maven 运行时图）。
- 我方 Gradle 图中 `error_prone_annotations:2.50.0` 已经由 tier③ 官方坐标在运行时供给
  （guava 33.4.8-android、material 1.14.0、`:SystemUI-common` 直接声明等，
  `:SystemUI-core:dependencies --configuration debugRuntimeClasspath` 实测）。
- monet 翻转为 program 输入后，两个来源同类同 classpath → D8 duplicate class 硬错误。
  与 Batch 3 对 view_capture 的 FAT jar 预判同模式，审计漏掉了 monet 的同款风险。

### REDLINE（worker 停止点）

修复此冲突需要以下之一，均越出 brief 授权（“Do not modify or rebuild the JARs” /
 “No … catalog/version/module … change” / “change another dependency … is REDLINE”）：

1. **重打包 monet.jar**（剥离 27 个 errorprone 类，errorprone 由官方 Maven 2.50.0 统一供给，
   符合 AGENTS §1.5 “官方 Maven 坐标 > 本地 jar”优先级）→ 修改产物，REDLINE。
2. **对 Maven 依赖加 exclude**（改变另一条依赖声明）→ REDLINE，且方向错误
   （应调整本地 FAT 产物而非官方坐标）。
3. **monet 维持 compileOnly** → 放弃已批准的 A6 闭包范围，验收 #5 无法达成。

worker 未做任何上述变更；四行 scope 翻转保留为未提交 diff，交架构师决策。

### 建议（供架构师参考，非 worker 决策）

monet.jar 应比照 Batch 3 view_capture 纪律先“去 FAT 重打包再翻转”：
重产仅含 `com/android/systemui/monet/**` + `com/google/ux/material/libmonet/**`（56 类）
的干净 jar，errorprone 由既有官方坐标供给；msdl/wifi-flags/wm-shell-flags 三行翻转
本身无冲突（27 条 duplicate 全部来自 monet），可与新 monet 产物同批落地。

## 第二轮：用户批准方案 A（clean monet 重打包），2026-08-20

用户于 2026-08-20 明确批准上述 REDLINE 的推荐解决方案：

- 仅合并两个 owning Soong `javac` 产物：`monet`（9 类，
  `out/soong/.intermediates/frameworks/libs/systemui/monet/monet/android_common/javac/monet.jar`）
  与 `libmonet`（47 类，
  `out/soong/.intermediates/external/libmonet/libmonet/android_common/javac/libmonet.jar`）；
- `com.google.errorprone:error_prone_annotations:2.50.0` 继续由官方 Maven 供给（不 exclusion）；
- `libs/monet.jar` 替换为 56 类确定性 tier② JAR；
- 随后完成四个 jar 的 runtime scope 翻转。

实施采用 TDD：先写四个聚焦测试（namespace 合并过滤、确定性、重复类拒绝、非预期
namespace 拒绝），RED 后最小实现 `tools/package_monet_jar.py`。上方第一轮 REDLINE
诊断与全部实测证据**原样保留**。实施结果见下节。

### 第二轮实测（全部为真实命令输出）

**TDD RED**：`python3 -m unittest tools.tests.test_package_monet_jar -v` 先行失败于
`FileNotFoundError: tools/package_monet_jar.py`（预期原因：实现不存在）。

**TDD GREEN**：最小实现后连跑两次，均 `Ran 4 tests / OK`：
- `test_merges_only_expected_class_namespaces`：仅四个 .class 进入产物，
  MANIFEST/目录 entry 被过滤；`package_monet_jar()` 返回 `(2, 2)`（合成输入）
- `test_output_is_deterministic`：两次输出字节一致；entry 字典序 +
  timestamp `(1980,1,1,0,0,0)` + mode `0644`
- `test_rejects_duplicate_class_entries`：跨输入同名 class 抛 `MonetJarError`
- `test_rejects_unexpected_class_namespace`：混入 `com/google/errorprone/` 类抛 `MonetJarError`

**真实产物生成与机械校验**：

```
$ python3 tools/package_monet_jar.py   （运行两次）
libs/monet.jar (111175 bytes): monet=9 libmonet=47 total=56
sha256: 50f88d5137d2164fe23412d38d4b5d079b16c84652ef953b6bede7276808ce60  （两次相同）

$ python3 （class-set 对比两个 Soong javac 输入）
monet input=9
libmonet input=47
output=56
missing=0
extra=0
errorprone=0
ARTIFACT_ASSERTION: PASS
```

**Scope 断言（改后）**：`target implementation=4`、`target compileOnly=0`、
`deferred compileOnly=5/5`、`deferred implementation=0`（ASSERTION: PASS，exit=0）。

**静态/单元检查**：`git diff --check` 干净（DIFF_CHECK_OK）；
`python3 -m unittest discover -s tools/tests -p 'test_*.py'` → **Ran 151 tests / OK**
（147 存量 + 4 新增，符合验收 #2）。

**Debug 闭包验证**：`./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug
-Dorg.gradle.workers.max=4` → **BUILD SUCCESSFUL in 2m 44s**（216 actionable
 tasks: 198 executed, 18 up-to-date）。第一轮的 27 条 duplicate class 错误全部消失。
APK 产出：`app/build/outputs/apk/debug/app-debug.apk`（159,126,566 bytes）。

**Dex 定义抽查**（`apkanalyzer dex packages --defined-only`，`C d` 行）：

```
com.android.systemui.monet.ColorScheme             DEFINED: C d 38  38  4765
com.google.ux.material.libmonet.hct.Hct            DEFINED: C d 12  12  759
com.google.android.msdl.domain.MSDLPlayer          DEFINED: C d 5   5   287
com.android.wifi.flags.Flags                       DEFINED: C d 34  34  1933
com.android.wm.shell.Flags                         DEFINED: C d 25  25  1445
```

**Release R8 测量（真实失败，无任何绕过）**：

```
$ set -o pipefail && ./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4 \
    2>&1 | tee /tmp/task033-r8.log | tail -8
BUILD FAILED in 25s
REAL_GRADLE_EXIT=1
```

失败原因与 Task 030 同型（`ERROR: Missing classes detected while running R8`），
`app/build/outputs/mapping/release/missing_rules.txt` 重产于 10:33:47：**126 条**
`-dontwarn` 规则 / 126 个唯一 class 引用（基线 140，预测 125）。

**逐条 diff（vs `/tmp/task030-missing_rules.txt`，架构师独立 diff + worker 复现一致）**：
- **移除 = 15，与 Batch 1 预测的 A6+A10+A12 集合逐一吻合**：
  monet 4（ColorScheme/DynamicColors/Style/TonalPalette）+
  libmonet 3（DynamicColor/DynamicScheme/MaterialDynamicColors）+
  msdl 6（MSDLToken/InteractionProperties×2/MSDLPlayer×2/MSDLEvent）+
  wifi 1 + wmshell 1。
- **新增 = 1：`com.android.aconfig.annotations.AssumeTrueForR8`**
  （referenced from `com.android.wifi.flags.FeatureFlags.androidVWifiApi()` and
  1 other context）——wifi/wm-shell flags 类进入 R8 program 输入后新浮出。
  与 B3 `AconfigFlagAccessor` 同包 `com.android.aconfig.annotations`，
  同属构建期 aconfig 注解（Ch4 家族）。**分类：移交 B3/aconfig annotations 后续
  批次处置（架构师已裁定）；本任务不加 dontwarn、不改 scope**。
- 净结果 140 − 15 + 1 = 126，实测与推算一致；预测 125 与实测 126 的差即此新浮出类。

## 待解决 / 后续批次

- ~~**本任务阻塞项（最高优先）**：monet.jar FAT 污染与官方 Maven errorprone 重复类冲突，
  需架构师决策（重打包 / 授权其他方案），见上方 REDLINE 节。~~ → 已解决（用户批准
  方案 A，本轮已落地）。
- **B3/aconfig annotations 扩面**：`com.android.aconfig.annotations.AssumeTrueForR8`
  新浮出（同 B3 包，Ch4 家族）——与 `AconfigFlagAccessor` 一并移交 B3 逐类处置，
  本批不动。
- Batch 2：aconfig javac 全量 jar（A1/A2/A11-flags/A3-flags，7 类）+ notification-flags
  本地 Maven → 直引 jar 迁移。
- Batch 3：官方 protobuf-javalite 3.21.12 + view_capture 去污染重打包 + motion_tool
  后置翻转（A5/A8，11 类，批内有序）。
- Batch 4：五个产物 AAR 闭包重打包（A7/A3 剩余/A4/A11 Kotlin，102 类，风险最高）。
- Batch 5：B1–B3 四个 platform 类移交 Task 032 逐类处置。
- Batch 6：B4 keepanno release-R8 classpath 方案调查。
- Batch 7：清理与对账。
