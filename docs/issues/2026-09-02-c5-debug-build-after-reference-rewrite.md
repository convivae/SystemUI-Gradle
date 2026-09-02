# C5 Task 082：Task 081 后 Debug APK 构建验证

**日期**：2026-09-02
**状态**：FAIL（2026-09-02，真实 Debug pipeline 在 AGP artifact-transform parameter isolation 阶段停止）
**前置**：Task 081 fixed range `aba9534f...3173d426` 已通过 Standards/Spec 双轴 review，并随 closure commit `26b1346b` push。

## 背景

Task 081 只证明了 `buildSrc` loader、ASM visitor、166-class filter 和 app-only `InstrumentationScope.ALL` registration 的 focused contract。它没有配置或执行 Android module task，因此尚不知道 AGP 9.3.1 是否能在真实 Debug pipeline 中实例化 plugin、处理 project/JAR/AAR program inputs并输出 APK。

本任务只构建 Debug，不运行 Release/R8，不启动模拟器，不执行 ADB，也不修改 production 或 build logic。Release build/static gate、Debug runtime、Release runtime继续作为后续独立串行任务。

## 操作

1. 确认没有 Gradle/Kotlin/Soong/Ninja 并发进程。
2. 只运行：
   ```bash
   ./gradlew :app:assembleDebug --console=plain --rerun-tasks --max-workers=4
   ```
3. 若构建成功，记录 `app/build/outputs/apk/debug/app-debug.apk` 的大小与 SHA-256，并执行 ZIP 完整性检查。
4. 以 authoritative AOSP 725-rule 文件运行现有 checker：
   ```bash
   uv run python tools/check_aconfig_jarjar_references.py \
     --apk app/build/outputs/apk/debug/app-debug.apk \
     --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
   ```
   Debug 不做 shrinking，`libs/systemui-aconfig-flags.jar` 中两个合法 old-name definitions 可能仍存在，因此现有 release-oriented checker 可预期 exit 1；不得把这个 exit 1 单独写成 Task 082 失败。真正的 Debug 静态判据是：四个 hidden targets 全部 referenced、所有 hidden target definitions 为 0；若仍出现任何非定义型 critical old-name caller，则任务失败并原样报告。
5. 构建结束后终止 Gradle/Kotlin daemons；不删除或改写旧 Release APK。

## 验收

- `:app:assembleDebug` 为 `BUILD SUCCESSFUL`。
- Debug APK 存在、ZIP 完整、SHA/大小已记录。
- 四个 critical hidden targets 均出现在 DEX type references；全 725 rules 的 hidden targets definition count 为 0。
- critical old-name 若仍存在，只允许是 APK 内对应 source class definition/self-reference；任何其他 caller residual 均 FAIL。
- tracked worktree 保持 clean；无 Release/R8、Soong/Ninja、emulator、ADB、源码/资源/build-logic修改。

## 执行结果

- Worker：`task082-debug-build`，独立 tab `w2:t39` / pane `w2:p3E`。
- Session JSON 已独立核实 `provider=joycode`、`modelId=GLM-5.3`、`thinkingLevel=high`；startup 按 AGENTS → CHARTER → brief/issue 的顺序完成，CONTRACT 经 Chief 接受。
- Preflight：无 Gradle/Kotlin/Soong/Ninja 活动进程，tracked worktree clean。
- 唯一 Gradle command 使用 `set -o pipefail` 运行，真实 exit code 为 1：
  ```text
  ./gradlew :app:assembleDebug --console=plain --rerun-tasks --max-workers=4
  BUILD FAILED in 1m 1s
  125 actionable tasks: 125 executed
  ```
- 首个 actionable failure：
  ```text
  Execution failed for task ':app:desugarDebugFileDependencies'
  > Could not isolate parameters ... of artifact transform AsmClassesTransform
     > Could not isolate value ... of type AsmClassesTransform.Parameters
        > Could not serialize value of type AconfigReferenceRewriteFactory
  ```
- 完整日志：`/tmp/task082-c5-debug-build/assemble-debug.log`（384 行）。
- 构建失败后未运行其他 Gradle task、未修复、未检查 APK/checker；tracked worktree 保持 clean。Chief 已终止本次 Gradle/Kotlin daemon。

## 结论

Task 082 验收为 **FAIL**。Task 081 focused tests 证明的 visitor/registration contract 尚不足以证明 factory 可被真实 `InstrumentationScope.ALL` dependency transform 隔离。该失败不等价于“factory 缺少 `Serializable`”：AGP 9.3.1 的 `AsmClassVisitorFactory` 接口自身已继承 `java.io.Serializable`，且当前唯一自有 cache field 的 classfile flags 为 `ACC_TRANSIENT`。下一任务必须先以同一 `:app:desugarDebugFileDependencies` 路径取得完整 serialization cause、建立最小 regression gate，再修改 build logic；在此之前不得猜测式添加接口或扩大 rewrite 范围。

## 待解决问题

- 确定 `AconfigReferenceRewriteFactory` 在 Gradle 9.5.0 / AGP 9.3.1 transform isolation 中不可序列化的最深层 cause。
- 建立能在数秒内重现该 exact isolation failure 的 focused Gradle gate，并在修复后保持 GREEN。
- 修复后重新执行独立 Debug build/static task；Task 082 本身不重试。
- `InstrumentationScope.ALL` 是否覆盖 Task 080 已证明的 project/JAR/AAR 输入，仍需成功 APK 的静态证据。
- Debug APK 是否达到 reference-only 预期，仍未证明，不能进入 Release/runtime gate。
