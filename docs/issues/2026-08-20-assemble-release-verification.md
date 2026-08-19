# 2026-08-20 — Task 025: assembleRelease 验证 + 诊断（不修复）

> **范围**：首次验证 release 变体。**验证 + 诊断，不修复**（用户 2026-08-19 批准；brief 025）。
> 本文为诊断报告，记录控制组（debug）结果、release 结果、根因归组、测试基线。
> **未做任何修复尝试**；修复决策属红线（构建配置/产物来源），交由架构师/用户裁定。

---

## 1. 背景

- 工作树：`/home/conv/myspace/SystemUI-Gradle-wt-025`，分支 `task-025`，起点 HEAD `e05318e5`。
- 目标：首次运行 `:app:assembleRelease`，验证 release 变体是否可构建。
- release 专有输入（brief 已知背景，已逐一核实存在）：
  - 签名：`keystore/platform.keystore`（debug/release 共用，`app/build.gradle.kts` `signingConfigs.release`）✓
  - 源码集：`SystemUI-core/src-release/`（4 个 .kt：DebugLogger/StartBinderLoggerModule/FlagsModule/FlagsFactory）✓
  - jar：`libs/compilelib-release.jar`（仅 `com/android/systemui/util/Compile.class`，IS_DEBUG 常量）✓
  - `SystemUI-core` `isMinifyEnabled = false`（release 不跑混淆）✓
  - KSP/AIDL release 接线：`kspReleaseKotlin → compileReleaseAidl`、`releaseImplementation(...)` ✓

---

## 2. 控制组：assembleDebug（成功）

```
$ ./gradlew :app:assembleDebug --console=plain
...
BUILD SUCCESSFUL in 2m 5s
216 actionable tasks: 216 executed
```

- APK 产物：`app/build/outputs/apk/debug/app-debug.apk`（platform 签名）。
- 结论：**debug 变体构建成功**，作为 release 对照基线成立。
- 注：debug 路径**不执行** `:SystemUI-core:mergeDebugConsumerProguardFiles`（见 §5 根因），因此掩盖了 consumer-proguard 缺陷。

---

## 3. release 结果：失败（首任务 + 错误原文）

### 3.1 首次运行 —— 守护进程被 OOM-kill（环境性失败，已排除）

```
$ ./gradlew :app:assembleRelease --console=plain
...
> Task :SystemUI-core:compileReleaseKotlin
> Task :SystemUI-core:compileReleaseJavaWithJavac
FAILURE: Build failed with an exception.
* What went wrong:
Gradle build daemon disappeared unexpectedly (it may have been killed or may have been crashed)
> Task :SystemUI-core:compileReleaseJavaWithJavac
```

- 守护进程 pid 2223887 在 `compileReleaseJavaWithJavac` 期间消失；守护进程日志在一条 deprecation 警告中**戛然而止**，无 Java 异常（SIGKILL 不可捕获，无法写栈/关闭钩子）。
- `journalctl` 铁证：
  ```
  Aug 20 00:45:14 kernel: oom-kill: ... task=java,pid=2223887,uid=1000
  Aug 20 00:45:14 kernel: Out of memory: Killed process 2223887 (java) total-vm:25915300kB, anon-rss:11149464kB
  Aug 20 00:45:14 kernel: redis-server invoked oom-killer: ... global_oom
  ```
- **根因**：宿主机全局内存耗尽 → 内核 OOM killer 选中最大受害进程（Gradle 守护进程，~11.1 GB RSS）SIGKILL。
- 诱因：① `-Xmx16g` 守护进程在刚结束的 `assembleDebug` 后仍驻留 debug 变体状态；② 残留的 Kotlin 编译守护进程（pid 2224083，`-Xmx16g`，~11.3 GB RSS）亦驻留；③ **另一工作树 `SystemUI-Gradle-wt-026` 同时在 30 GB 宿主上跑 `:app:assembleDebug`**，三 JVM 竞争内存。
- **性质**：环境/基础设施失败，**非项目缺陷**。
- 用户确认并发大项目已移除；清理残留守护进程后重跑（见 §3.2）。

### 3.2 清理后重跑 —— 真实构建失败（首任务定位）

清理动作（仅环境整理，**未改任何项目文件**）：
- `./gradlew --stop`（停掉残留 Gradle 守护进程 pid 2238977，释放 ~10 GB）
- `kill 2224083`（停掉残留 Kotlin 编译守护进程，释放 ~11 GB）
- 之后内存：22 GB free / 25 GB available，无残留 JVM。

```
$ ./gradlew :app:assembleRelease --console=plain
...
> Task :SystemUI-core:compileReleaseJavaWithJavac          # 之前被 OOM 杀，现已成功
> Task :SystemUI-core:mergeReleaseGeneratedProguardFiles
> Task :SystemUI-core:mergeReleaseConsumerProguardFiles FAILED
...
FAILURE: Build failed with an exception.
* What went wrong:
Execution failed for task ':SystemUI-core:mergeReleaseConsumerProguardFiles'
  (registered by plugin 'com.android.internal.library').
> Supplied consumer proguard configuration does not exist:
  /home/conv/myspace/SystemUI-Gradle-wt-025/SystemUI-core/consumer-rules.pro
BUILD FAILED in 23s
364 actionable tasks: 10 executed, 354 up-to-date
```

- **首个失败任务**：`:SystemUI-core:mergeReleaseConsumerProguardFiles`
- **错误原文**：`Supplied consumer proguard configuration does not exist: .../SystemUI-core/consumer-rules.pro`
- 此前被 OOM 阻断的 `compileReleaseJavaWithJavac` 现已成功通过——**OOM 确为环境问题，已排除**。

---

## 4. 测试基线

```
$ python3 -m unittest discover -s tools/tests -p 'test_*.py'
Ran 148 tests in 41.572s
OK
```

- 148 通过，0 失败——与 brief 期望的 148 基线一致。工具链未受 release 验证影响。

---

## 5. 根因归组（systematic-debugging Phase 1–2）

### 5.1 根因（确证）

| 项 | 证据 |
|----|------|
| 现象 | `:SystemUI-core:mergeReleaseConsumerProguardFiles` 失败：`consumer-rules.pro` 不存在 |
| 直接原因 | `SystemUI-core/build.gradle.kts:28`（`defaultConfig`）声明 `consumerProguardFiles("consumer-rules.pro")`，但该文件**磁盘不存在**且**从未入 git**（`git log --all -- SystemUI-core/consumer-rules.pro` 无记录；`git ls-files` 无；非 .gitignore 命中） |
| 引入来源 | commit `a4bd7f94`（2026-07-18，"feat(build): update Gradle config for AGP 9.2 + Kotlin 1.9.22"）添加该行，但**该 commit 未创建对应 .pro 文件**——悬挂引用自始即存在（>1 月） |
| AGP 行为 | AGP 9.3.1 `merge<Variant>ConsumerProguardFiles`（`com.android.internal.library` 注册）在执行时校验每个 `consumerProguardFiles` 路径必须存在，缺失即抛 "Supplied consumer proguard configuration does not exist" |
| 为何 debug 不暴露 | `:app:assembleDebug` 任务图**不含** `:SystemUI-core:mergeDebugConsumerProguardFiles`——app 消费 library 的 classes/jar 做 dex，不合并 library 的 consumer proguard。已实测验证（见 §5.2） |
| 为何 release 暴露 | release 路径**执行** `mergeReleaseConsumerProguardFiles`（consumer 规则随 AAR 发布/合并），缺失文件即失败 |

**根因归组**：**构建配置缺陷**——`consumerProguardFiles` 悬挂引用一个从未创建的文件。**非**源码/res/AOSP 对齐问题，**非**环境问题（OOM 已排除）。

### 5.2 debug/release 不对称的实证（systematic-debugging Phase 2: pattern）

直接触发 debug 等价任务以验证假设：

```
$ ./gradlew :SystemUI-core:mergeDebugConsumerProguardFiles --rerun-tasks
> Task :SystemUI-core:mergeDebugConsumerProguardFiles FAILED
> Supplied consumer proguard configuration does not exist:
  .../SystemUI-core/consumer-rules.pro
BUILD FAILED in 2m 3s
```

- debug 变体的同名任务**同样失败**，错误一字不差。
- 即 debug 并非"成功通过"该任务，而是 assembleDebug 根本不执行它——不对称性来自任务图差异，**非**变体行为差异。

### 5.3 参考项目对照（AGENTS §1.4 CarSystemUIGradle）

| 检查 | 结果 |
|------|------|
| `CarSystemUIGradle/SystemUI-core/consumer-rules.pro` 存在？ | 否 |
| `CarSystemUIGradle/SystemUI-core/proguard-rules.pro` 存在？ | 否 |
| `CarSystemUIGradle/SystemUI-core/build.gradle.kts` 同样声明？ | 是（line 25 `consumerProguardFiles("consumer-rules.pro")`；line 31–33 `proguardFiles(..., "proguard-rules.pro")`） |

- 参考项目**携带完全相同的潜伏缺陷**——本项目的悬挂引用是自参考项目 copy-inherit 而来。参考项目大概率也从未跑过 release，故同样未暴露。
- AOSP `frameworks/base/packages/SystemUI/Android.bp` **无** `consumer_proguard` / `proguard_specs`——这些 `.pro` 文件是 Gradle 专属构建产物，**无 AOSP 源码来源**。

### 5.4 次级发现（潜伏，未触发）

- `SystemUI-core/build.gradle.kts:36`（`release` buildType）`proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")`——`proguard-rules.pro` **同样不存在**。
- 未触发原因：① 失败先短路于 consumer proguard；② `isMinifyEnabled=false`，R8/全量 proguard 不跑。
- 修复 consumer-proguard 后将浮出（若仍引用该文件）。

---

## 6. 排除项（ruled out）

- ❌ 非 KSP/Dagger/release-Kotlin 问题：`kspReleaseKotlin`、`compileReleaseKotlin` 均成功。
- ❌ 非 release 源码（`src-release/`）问题：`compileReleaseKotlin`、`compileReleaseJavaWithJavac` 均成功。
- ❌ 非 `compilelib-release.jar` 问题：该 jar 仅 1 个 `Compile.class`，编译/资源阶段无相关报错。
- ❌ 非签名问题：`validateSigningRelease` UP-TO-DATE，`platform.keystore` 就位。
- ❌ 非 OOM：环境性 OOM 已排除（清理后 `compileReleaseJavaWithJavac` 成功）。

---

## 7. 复现性

- **确定性复现**：`:SystemUI-core:mergeReleaseConsumerProguardFiles`（及 `--rerun-tasks` 的 debug 同名任务）100% 失败，错误一致。
- **环境依赖**：OOM 部分（§3.1）依赖宿主机并发负载，环境性可复现但非确定性。

---

## 8. 待决修复方向（红线，未实施——交架构师/用户）

> 以下均属**构建配置/产物来源**变更，命中 CHARTER Part 5 红线（规则矩阵 + 配置），
> 且 brief 025 明令"不修任何构建/源码问题；不改版本、配置、依赖"。
> 列出供决策参考，**worker 未实施任何一项**。

1. **创建 `SystemUI-core/consumer-rules.pro`（及 `proguard-rules.pro`）**——空文件或真实 keep 规则。
   - 产物来源问题：AOSP 无对应；属 Gradle 构建产物，需用户裁定是否可凭空创建（rule R 针对 res/，.pro 非典型 res，但 provenance 仍需授权）。
   - 参考项目同缺陷，无现成模板可抄。
2. **移除/注释 `consumerProguardFiles("consumer-rules.pro")`（及 release `proguardFiles(..., "proguard-rules.pro")`）**——配置变更，红线。
   - `isMinifyEnabled=false` 下，proguard 规则对当前构建目标（生成未混淆 APK）非必需；移除在语义上最小侵入。
3. **改用 `getDefaultProguardFile` 或既有文件**——配置变更，红线。

**建议**：方向 2（移除悬挂引用）最小且对齐"无混淆 APK"目标；但属配置决策，需用户批准后由具备配置写权限的 worker 实施。

---

## 9. 未运行构建说明

- §2 assembleDebug：运行，BUILD SUCCESSFUL（真实输出见上）。
- §3.1 首次 assembleRelease：运行，环境性 OOM 失败（真实 journalctl 证据）。
- §3.2 清理后 assembleRelease：运行，真实构建失败（consumer-rules.pro 缺失）。
- §4 工具测试：运行，148 OK。
- 本文**未暗示** release 构建成功；release 当前**失败**。

---

## 10. HANDOFF

```text
HANDOFF:
- done: 验证 assembleDebug（成功）+ assembleRelease（失败，首任务 mergeReleaseConsumerProguardFiles）
        + 148 工具测试通过；按 systematic-debugging 归组根因（consumer-rules.pro 悬挂引用）
- verified: ./gradlew :app:assembleDebug -> BUILD SUCCESSFUL (2m5s)
            ./gradlew :app:assembleRelease -> BUILD FAILED (mergeReleaseConsumerProguardFiles: consumer-rules.pro 不存在)
            ./gradlew :SystemUI-core:mergeDebugConsumerProguardFiles --rerun-tasks -> 同样失败（证不对称性来自任务图）
            python3 -m unittest discover -s tools/tests -> Ran 148 tests, OK
- remaining: 修复 consumer-rules.pro / proguard-rules.pro 悬挂引用（红线，交架构师/用户决策方向 1/2/3）
```
