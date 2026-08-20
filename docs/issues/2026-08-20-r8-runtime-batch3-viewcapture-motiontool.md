# R8 Runtime Closure Batch 3：protobuf-javalite + view_capture + motion_tool

日期：2026-08-20

## 背景

Task 034 合并后，`:app:minifyReleaseWithR8` 仍如实失败于 119 个 unique missing refs。Task 031 的闭包审计把其中 11 个归入同一有序依赖链：

```text
motion_tool_lib
├── view_capture
├── motion_tool_proto
│   ├── view_capture_proto
│   └── libprotobuf-java-lite
└── androidx.core_core

view_capture
├── view_capture_proto
│   └── libprotobuf-java-lite
└── androidx.core_core
```

当前仓库状态不满足 APK program/runtime closure：

- `libs/view_capture.jar` 是 3427-class FAT JAR，混入 AndroidX、Kotlin、kotlinx、protobuf 等上游类；不能直接改为 `implementation`，否则 D8 duplicate classes。
- `libs/motion_tool_lib.jar` 只含 main Kotlin 的 8 类，缺 `motion_tool_proto` 的 57 类。
- 两个 JAR 都是 `compileOnly`，因此真实 runtime 类没有进入 APK。
- `protobuf-javalite` 尚未声明为官方 Maven runtime dependency。

## 依赖判定

| 依赖 | tier | 交付方式 | 依据 |
|---|---|---|---|
| `protobuf-javalite` | ③ 标准上游 | Maven Central `com.google.protobuf:protobuf-javalite` | AOSP `libprotobuf-java-lite` 对应官方 protobuf lite runtime；无 AOSP fork API 需求 |
| `view_capture` / `view_capture_proto` | ② AOSP 非 SystemUI 纯代码 | 确定性 clean JAR | 定义于 `frameworks/libs/systemui/viewcapturelib/Android.bp`，无资源 |
| `motion_tool_lib` / `motion_tool_proto` | ② AOSP 非 SystemUI 纯代码 | 确定性 clean JAR | 定义于 `frameworks/libs/systemui/motiontoollib/Android.bp`，无资源 |

Maven Central metadata 于 2026-08-20 实测：`latest/release=4.36.0-RC2`，过滤 RC 后最新稳定版为 **4.35.1**。依用户“优先尝试公网最新稳定版，构建通过则采用”的既定授权，本批先使用 4.35.1；只有出现可复现的二进制/编译兼容失败时，才可 REDLINE 请求回退 AOSP pin `3.21.12`，不得静默降级。

## 干净产物输入

所有输入必须来自 owning Soong implementation 产物，禁止 turbine/header/FAT 输入：

### `libs/view_capture.jar`

1. `view_capture/android_common/javac/view_capture.jar` — 9 类
2. `view_capture/android_common/kotlin/view_capture.jar` — 23 类
3. `view_capture_proto/android_common/javac/view_capture_proto.jar` — 24 类

输出必须恰为 56 个 `com/android/app/viewcapture/**.class`。

### `libs/motion_tool_lib.jar`

1. `motion_tool_lib/android_common/kotlin/motion_tool_lib.jar` — 8 类
2. `motion_tool_proto/android_common/javac/motion_tool_proto.jar` — 57 类

输出必须恰为 65 个 `com/android/app/motiontool/**.class`。

打包器必须拒绝缺失/空输入、批准 namespace 外的 class、输入内或跨输入重复 class；输出 class 按路径排序并固定 ZIP timestamp/权限，重复运行 byte-identical。非 class entry 不进入输出。

## 操作步骤

1. 在改动前 fresh 运行 `:app:minifyReleaseWithR8`，保存真实 Gradle exit code 和 119-ref baseline。
2. TDD 新增 `tools/package_viewcapture_motiontool_jars.py` 及聚焦单测。
3. 生成并提交 clean 56-class `libs/view_capture.jar` 和 65-class `libs/motion_tool_lib.jar`。
4. `gradle/libs.versions.toml` 新增 `protobufJavalite = "4.35.1"` 与 `protobuf-javalite` alias。
5. 严格按顺序接入：
   - `protobuf-javalite` + clean view_capture；
   - 再接入 clean motion_tool。
6. `SystemUI-core`：view_capture、motion_tool 从 `compileOnly` 改为 `implementation`，并加入 `implementation(libs.protobuf.javalite)`。
7. `SystemUI-shared`：view_capture 从 `compileOnly` 改为 `implementation`，并加入 `implementation(libs.protobuf.javalite)`，使该库自身 runtime closure 完整。
8. 运行全套 Python tests、debug duplicate/build、APK class 定义检查和 fresh R8 差分。

## 预期 R8 差分

119 → 108，必须恰好移除以下 11 项，新增 0：

- `com.android.app.motiontool.DdmHandleMotionTool$Companion`
- `com.android.app.motiontool.DdmHandleMotionTool`
- `com.android.app.motiontool.MotionToolManager$Companion`
- `com.android.app.motiontool.MotionToolManager`
- `com.android.app.viewcapture.LooperExecutor`
- `com.android.app.viewcapture.ViewCapture`
- `com.android.app.viewcapture.ViewCaptureAwareWindowManager$Factory`
- `com.android.app.viewcapture.ViewCaptureAwareWindowManager`
- `com.android.app.viewcapture.ViewCaptureFactory`
- `com.google.protobuf.GeneratedMessageLite$Builder`
- `com.google.protobuf.GeneratedMessageLite`

`com.android.aconfig.annotations.AssumeTrueForR8` 必须继续保留，不在本批处理。

## 红线与禁止项

- 不修改任何 AOSP mirrored `src/` 或 `res/`。
- 不添加 stub、keep/dontwarn、source exclusion 或 build bypass。
- 不使用 turbine/header/FAT 产物。
- 不将 JAR 放进 `libs/maven/`，不调用 `install_aar_to_maven.py`。
- 不改除 protobuf-javalite 之外的任何依赖版本。
- 4.35.1 若失败，必须保留证据并 REDLINE；不得自行改用 3.21.12。

## 错误数演变

| 阶段 | R8 unique missing refs | 说明 |
|---|---:|---|
| Task 034 后 | 119 | fresh main baseline |
| 本批目标 | 108 | 精确移除 A5+A8 共 11 项，0 additions |

## 实施记录（2026-08-20，worker task 035）

### 已完成步骤及真实证据

1. **Fresh 前置 R8 基线**（改动前）：
   - 命令：`./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4`（全日志 `/tmp/task035-r8-before.log`）
   - 真实 exit code：`GRADLE_EXIT=1`（保存在 `/tmp/task035-r8-before.status`），失败模式为 R8 missing classes（非 D8 重复类）
   - 机器断言：`BASELINE=119 PASS`（119 个唯一 `-dontwarn` refs；11 个目标 refs 与 `AssumeTrueForR8` 均在）

2. **TDD 打包器**（先写失败测试再实现，superpowers TDD 流程）：
   - 新增 `tools/package_viewcapture_motiontool_jars.py` + `tools/tests/test_package_viewcapture_motiontool_jars.py`
   - 聚焦测试：`python3 -m unittest tools.tests.test_package_viewcapture_motiontool_jars` → `Ran 6 tests ... OK`

3. **干净产物**（两次运行 byte-identical）：
   - `view_capture: (9 + 23 + 24) = 56 classes`；SHA-256 `7ed2eb141ec1d491a5c9b0f205eb2649862b6a6e5595150b92e6d7e25ed5d315`
   - `motion_tool_lib: (8 + 57) = 65 classes`；SHA-256 `e2f5d0a96f43e535e8ead5096ea31f93c9f991504a19cf077d303142c50bbf72`
   - 双次运行 `sha256sum` 完全一致（`/tmp/task035-hash-{first,second}.txt` diff 为空）；命名空间/排序/计数断言全部通过

4. **全量 Python 测试**：`python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 160 tests in 35.937s ... OK`（154 基线 + 6 新增）

5. **protobuf-javalite Maven 元数据实测**（2026-08-20）：
   - `latest = 4.36.0-RC2`、`release = 4.36.0-RC2`（RC 预发布）；过滤 RC 后最新稳定 = **4.35.1**（最近 10 版：`4.34.0-RC2, 4.34.0, 4.34.1, 4.34.2, 4.35.0-RC1, 4.35.0-RC2, 4.35.0, 4.35.1, 4.36.0-RC1, 4.36.0-RC2`）
   - 与预授权版本一致，已加入 `gradle/libs.versions.toml`（`protobufJavalite = "4.35.1"` + alias，未动其他任何版本）

### 阻断：kotlinx-coroutines 1.11.0 编译不兼容（REDLINE 停止）

按序接入 view/protobuf 后，`:SystemUI-core:compileDebugKotlin` **可复现失败**（debug 与 release 均 fail，同一错误，全日志 `/tmp/task035-debug.log`、`/tmp/task035-release-compile.log`）：

```text
e: .../statusbar/notification/collection/coordinator/OriginalUnseenKeyguardCoordinator.kt:142:25
   Return type 'Nothing' needs to be specified explicitly.
```

**系统化定位（逐项 bisect，全部可复现）**：

| 实验 | 变量 | 结果 |
|---|---|---|
| A | 全部改动 stash（旧 FAT jar + compileOnly） | compileDebugKotlin `BUILD SUCCESSFUL` |
| B | 仅移除 core 的 `implementation(libs.protobuf.javalite)` | 仍失败（排除 protobuf） |
| C | core 的 jar scope 回退 compileOnly（新 jar 仍在） | 仍失败（排除 scope 翻转） |
| D | 恢复旧 FAT jar、保留其余全部 Gradle 改动 | `BUILD SUCCESSFUL`（锁定 jar 内容） |
| E | 新 jar + 仅补 FAT 内 `kotlinx/coroutines/**`（1.9.0）的 compileOnly 探针 jar | `BUILD SUCCESSFUL`（锁定 coroutines 遮蔽） |
| F | 仅把 `kotlinxCoroutines` 临时改为 `1.10.2`（诊断后已回退） | `BUILD SUCCESSFUL`（锁定 1.11.0 版本本身） |

**根因**：旧 FAT `view_capture.jar` 内嵌 AOSP `kotlinx-coroutines`（pin 1.9.0，见 `external/kotlinx.coroutines/METADATA`）全量类，compileOnly 位于 classpath 靠前位置，编译期遮蔽了 Maven `kotlinxCoroutines = "1.11.0"`。换干净 jar 后首次真正对 1.11.0 编译。`javap` 对比（`/tmp/task035-probe/`）：1.11.0 的 `FlowKt.collectLatest` 新增了第二个 `SharedFlow`-receiver 重载（Continuation 为通配符 `Continuation<?>`），而 `KeyguardRepository.isDozing: StateFlow<Boolean>`（`SharedFlow` 子类型）恰好命中新重载，K2 推断 `OriginalUnseenKeyguardCoordinator.kt:142` 表达式体的返回类型为 `Nothing`，报错要求显式标注。该文件为 AOSP 镜像源码（红线 1）。

**阻断的验收项**：#5（assembleDebug）与 #7（post-change R8）—— release 编译同样失败（`GRADLE_EXIT=1`，同一错误）。

**需要用户决策的选项**（均触碰红线，worker 不擅自处置）：

1. 把 `kotlinxCoroutines` 从 `1.11.0` 回退到 `1.10.2`（实测可编译；AOSP pin 为 1.9.0）——版本矩阵红线（CHARTER Part 5 #4）；
2. 修改 AOSP 镜像源码 `OriginalUnseenKeyguardCoordinator.kt` 加显式返回类型——源码红线（Part 5 #1）；
3. 其他用户认可的方案。

当前工作区为 REDLINE 状态的未提交 diff（8 个文件，全部在 Allowed Paths 内，`git diff --check` 干净）：打包器 + 测试 + 两个干净 jar + 三处 Gradle 接线（core 侧目前处于诊断中间态后已恢复：view/protobuf/motion 均 implementation、无探针 jar、无临时版本）。待决策后重跑验收 #5–#7。

### REDLINE 批准后的续作（2026-08-20，用户批准 coroutines 1.10.2）

用户批准架构师建议：保持 AOSP 镜像源码不动，使用最高兼容官方版本。主仓 commit `c747debc` 已更新 brief/plan；worker 已 fast-forward `task-035` 并保留全部未提交 diff。

**应用授权改动**：`gradle/libs.versions.toml` 仅 `kotlinxCoroutines = "1.11.0"` → `"1.10.2"`（带根因注释）；protobuf-javalite 保持 4.35.1；未改任何源码；未加 shadow jar。

**验收 #5（debug 组装）**：
- 命令：`./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4`（全日志 `/tmp/task035-debug.log`）
- 真实 exit：`GRADLE_EXIT=0`；`BUILD SUCCESSFUL in 46s`；无 duplicate-class 失败；AOSP 镜像源码零改动

**验收 #6（APK dex 定义）**：`apkanalyzer dex packages --defined-only`（输出存 `/tmp/task035-dex-defined.txt`，788738 行）五个目标类全部为 `C d`（DEFINED，非仅引用）：

```text
C d 74  83  3963  com.android.app.viewcapture.data.ExportedData
C d 35  35  2542  com.android.app.viewcapture.ViewCapture
C d 55  61  3294  com.android.app.motiontool.MotionToolsRequest
C d 12  12  1595  com.android.app.motiontool.MotionToolManager
C d 80  81  5587  com.google.protobuf.GeneratedMessageLite
```

**验收 #7（fresh post-change R8）——11 项精确移除达成，但差分多出 1 个新增 ref（已上报 REDLINE）**：
- 命令：`./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4`（全日志 `/tmp/task035-r8-after.log`）
- 真实 exit：`GRADLE_EXIT=1`（失败模式仍为 missing classes，非 D8 重复类）
- 机器比对（before=`/tmp/task035-missing-before.txt` vs after=新 `missing_rules.txt`）：
  - before = 119 ✅；removed = **恰好审计列表的 11 项，无多无少** ✅；AssumeTrueForR8 保留 ✅
  - **after = 109（原预期 108，差分 +1）；added = 1 项：`org.apache.harmony.dalvik.ddmc.ChunkHandler`**（后续经用户裁决接受为 B2 发现，见下方“用户裁决”）
- 新增 ref 根因（非本批错误，是闭包变深的必然暴露）：
  - 引用点：`com.android.app.motiontool.DdmHandleMotionTool.<clinit>()`（`ChunkHandler.type("MOTO")`，AOSP 源码 `motiontoollib/src/.../DdmHandleMotionTool.kt:22,42`）+ 1 个其他 context
  - 此前 `DdmHandleMotionTool` 本身是 missing class，R8 在此截断；干净 jar 使 motiontool 可解析后 R8 首次触达其 ddmc 引用
  - `ChunkHandler` 为 libcore `@hide` bootclasspath 类（`libcore/dalvik/src/main/java/org/apache/harmony/dalvik/ddmc/ChunkHandler.java:32 @hide`），**与 B2 类（`libcore.io.IoUtils`/`libcore.util.NativeAllocationRegistry`，仍留在 missing set，设备提供，AOSP 不 dex）同类别**；存在于 `libs/android_module_lib_stubs_current.jar`（compileOnly，不在 R8 library classpath），不在 SysUISdk android.jar/framework.jar
  - 修复途径全部越界：B1–B4 classpath 桥接（本 brief Forbidden Paths）、dontwarn（禁止）、排除 motiontool（禁止）→ 按 brief 要求上报 REDLINE 待决策

**用户裁决（2026-08-20，接受本批真实结果）**：

- 接受 truthful 差分 **119 → 109**：恰好移除计划的 11 项 A/program refs，恰好新增 1 项 `org.apache.harmony.dalvik.ddmc.ChunkHandler`
- `ChunkHandler` 归类为 **device-provided @hide core-libart B2 library-classpath ref**，并入已规划的 B2 桥接批次处理；**非 Batch 3 失败**，不回滚已验证正确的工件
- 明确禁止：不加 dontwarn、不把 ChunkHandler 打进 APK、不动 SysUISdk/B2 桥、不扩大 scope
- `com.android.aconfig.annotations.AssumeTrueForR8` 继续保留在 missing set（实测确认）

## 错误数演变（更新）

| 阶段 | R8 unique missing refs | 说明 |
|---|---:|---|
| Task 034 后 | 119 | fresh main baseline |
| 本批最终（用户接受） | **109** | 恰好移除 A5+A8 的 11 项；+1 项 B2 类 `ddmc.ChunkHandler`（闭包变深暴露，用户裁决归入 B2 桥接批次） |

## 待解决问题（更新）

- ~~REDLINE 待决（新）~~ **已裁决（2026-08-20）**：119→109 结果被用户接受；`org.apache.harmony.dalvik.ddmc.ChunkHandler` 归类 B2（device-provided @hide core-libart，与 `IoUtils`/`NativeAllocationRegistry` 同类），并入已规划 B2 桥接批次；worker 未加 dontwarn、未加 jar、未动 SysUISdk。
- 本批结束后（以 109 计）继续按已审计顺序处理 Batch 4 的 Traceur、SettingsLib、SettingsTheme、WM-Shell、iconloader 闭包；B1–B4 classpath 问题仍不得越界处理。

## 双轴审查与主分支 fresh 复验（2026-08-20）

固定范围 `c747debc..26d63629` 的独立双轴审查均通过：

- Standards（`wX:p1`，GLM-5.2）：PASS；BLOCKER/HIGH/MEDIUM/LOW 均为 0，仅 3 个不影响行为的 TRIVIAL 可选整洁度建议。
- Spec（`wY:p1`，GLM-5.2）：PASS；无缺项、无 scope creep、无错误实现。
- worker commit `26d63629` 已由架构师 cherry-pick 为主分支 commit `bf6ff75f`。

架构师在主分支重新执行验收，结果如下：

- focused tests：6/6，`OK`；全套工具测试：160/160，`OK`。
- 打包器连续运行两次 SHA-256 完全一致：
  - `view_capture.jar`：`7ed2eb141ec1d491a5c9b0f205eb2649862b6a6e5595150b92e6d7e25ed5d315`，56 个排序后的纯 `com/android/app/viewcapture/**` class。
  - `motion_tool_lib.jar`：`e2f5d0a96f43e535e8ead5096ea31f93c9f991504a19cf077d303142c50bbf72`，65 个排序后的纯 `com/android/app/motiontool/**` class。
- `:app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4`：真实 exit 0，`BUILD SUCCESSFUL in 2m 8s`，216 tasks。
- 首次主分支增量 APK 为 199,943,097 B；ZIP 结构诊断确认其包含 39,399,416 B 未被 central directory 引用的旧增量区段。删除旧 APK 输出及 `packageDebug` 增量状态后，`:app:packageDebug` 在 6s 内成功重打包为 160,547,785 B，只有正常 4 KiB signing alignment；V2 签名有效。这是本机构建缓存现象，不是代码或依赖差异。
- 重打包 APK 中五个代表类均有 `C d` defined row：`ViewCapture`、`ExportedData`、`MotionToolManager`、`MotionToolsRequest`、`GeneratedMessageLite`。
- 首次带 `--rerun-tasks` 的 release R8 验证因全量重编时系统 OOM 被内核杀死 Gradle daemon（PID 3307107，约 12.6 GiB RSS；同时孤立 Kotlin daemon 占约 10.8 GiB），没有生成可接受的 R8 结论。停止无活跃客户端的孤立 Kotlin daemon 后，重新执行标准验收命令，真实 exit 1 且准确失败于剩余 missing classes：before=119、after=109、removed=精确计划 11 项、added=仅 `org.apache.harmony.dalvik.ddmc.ChunkHandler`、`AssumeTrueForR8` 保留。
- `git diff --check` 干净；没有 source/res、suppress、keep/dontwarn、SysUISdk/B2 或 local-Maven JAR 越界改动。
