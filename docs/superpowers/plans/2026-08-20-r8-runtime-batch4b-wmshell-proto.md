# Plan: R8 Runtime Batch 4B — WM-Shell proto 闭包（106→88）

> 实施前先读本计划与 `docs/issues/2026-08-20-r8-runtime-batch4b-wmshell-proto.md`。
> 方法论：TDD（先红后绿）、确定性产物、精确差分验收、debug 编译硬性门禁。

## 目标

把 AOSP `WindowManager-Shell` 的两个 proto `static_libs`（bp L188-189）的 Soong
javac 产物并入 WM-Shell AAR，补上 18 个 R8 missing refs（lite 15 + nano 3），
fresh R8 精确 106→88（18 removed、0 added），同时保持 `:app:assembleDebug` 成功。

## 输入事实（架构师已实测，worker 复核）

- `libs/aars/WindowManager-Shell.aar` 当前 classes.jar = **1848 类**
- proto jar A：`…/WindowManager-Shell-proto/android_common/javac/WindowManager-Shell-proto.jar`
  = **4 类**（全部 `com/android/wm/shell/nano/`）
- proto jar B：`…/WindowManager-Shell-lite-proto/android_common/javac/WindowManager-Shell-lite-proto.jar`
  = **36 类**（全部 `com/android/wm/shell/desktopmode/`）
- A∪B = 40 类，与现有 AAR **零重叠**，与 `WindowManager-Shell-shared.aar` **零重叠**，
  18 个 missing 目标 **100% 覆盖**
- 输出 AAR 目标 = **1888 类**（1848+40 精确并集），全部 `com/android/wm/shell/**`
- nano runtime 已由 `protobuf-javanano:3.1.0` 提供；lite 已由 `protobuf-javalite:4.35.1`
  提供——不得新增任何 protobuf 依赖声明

## 步骤

### Step 1 — TDD 红：先写失败测试

在 `tools/tests/test_package_aosp_aar.py` 与 `tools/tests/test_install_aar_to_maven.py`
新增聚焦测试（仿 036 的 iconloader 测试）：

1. `WindowManager-Shell` config 的 code 列表含主 javac、主 kotlin、proto（nano）、
   lite-proto 四个 Soong 路径（顺序固定）。
2. 打包产物 classes.jar 恰为 **1888 类** = 1848 基线 ∪ 40 proto，且四个 jar 类集
   两两不相交（对 proto 两个 jar 验证；对主产物按差集验证）。
3. 40 个 proto 类逐字节等于两个 Soong proto jar 中同名字节。
4. 18 个 R8 目标类名全部存在（从固定清单断言，含 `$` 内部类名）。
5. 全部类在 `com/android/wm/shell/` 命名空间下；res / AndroidManifest.xml / R.txt
   与 AOSP/Soong 源逐字节一致；连续两次打包 byte-identical（确定性）。
6. `install_aar_to_maven.py` ARTIFACTS 中 WindowManager-Shell 坐标恰为
   `com.android.systemui:WindowManager-Shell:1.0.1`；WindowManager-Shell-shared
   仍为 1.0.0（不动）。

先运行确认这些测试**失败**（红），再实施。

### Step 2 — 绿：实现

1. `tools/package_aosp_aar.py` `CONFIGS["WindowManager-Shell"].code` 追加：
   - `SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell-proto/android_common/javac/WindowManager-Shell-proto.jar"`
   - `SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell-lite-proto/android_common/javac/WindowManager-Shell-lite-proto.jar"`
   （保持主 javac、kotlin 在前；加注释标明 nano/lite 来源与 bp L138/L148/L188-189）
2. `tools/install_aar_to_maven.py` `ARTIFACTS["WindowManager-Shell"]["version"]`
   改为 `"1.0.1"`（只动这个值）。
3. 运行 `python3 tools/package_aosp_aar.py WindowManager-Shell` 重打包；验证 1888 类、
   确定性、res/manifest/R.txt 不变。
4. 删除 `libs/maven/com/android/systemui/WindowManager-Shell/1.0.0/` 整目录；运行
   `python3 tools/install_aar_to_maven.py`（或其等价调用）安装 1.0.1；验证 AAR 与
   `libs/aars/WindowManager-Shell.aar` byte-identical、POM 为骨架（无 dependencies）、
   目录中无 1.0.0 残留。
5. `gradle/libs.versions.toml` 将 `systemui-wmshell` 版本改为 `1.0.1`
   （**只此一行**；`systemui-wmshell-shared` 不动）。

### Step 3 — 全套验证（全部前台运行并记录真实退出码）

1. 新增聚焦测试全绿；全套 `python3 -m unittest discover -s tools/tests -p 'test_*.py'`
   通过（164 + 新增数）。
2. `git diff --check` 干净。
3. `set -o pipefail` + tee 保存日志：
   `./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4`
   必须 BUILD SUCCESSFUL（**硬性门禁**）。
4. `apkanalyzer dex packages --defined-only app-debug.apk` 验证 18 个目标类
   全部有 `C d` 行。
5. fresh R8 精确差分：
   - 先保存当前 `app/build/outputs/mapping/release/missing_rules.txt` 为 before
     （必须恰为 106 条 `-dontwarn`）
   - `./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4`（预期失败，
     因为还剩 88 个其他闭包缺口——失败是预期行为，missing_rules 才是验收物）
   - after 必须恰为 88 条；before−after 恰为 18 个 wm.shell 目标；after−before = 0；
     `AssumeTrueForR8` 仍在 after 中
   - 与上述任何一项不符 → REDLINE，停止并如实上报

### Step 4 — 文档与提交

- 在 issue 文档补全"错误数演变 / 证据"段（真实命令、退出码、数字）。
- 单个英文 commit，提交全部产物（含 `libs/aars/WindowManager-Shell.aar` 与
  `libs/maven/.../1.0.1/`）；**不 push**。
- 终态输出 HANDOFF: 块（done / verified / remaining）。

## 风险与红线

- **REDLINE**：1888≠并集、出现重叠类、res/manifest/R.txt 有字节变化、debug 失败、
  R8 差分非精确 106→88、新增 added 类、测试无法转绿。
- 任何"顺手修"其他闭包（Traceur/SettingsLib/B*）= 越界，禁止。
- 全程单次等待 ≤90s；构建长任务用 tee 落盘 + 真实退出码。
