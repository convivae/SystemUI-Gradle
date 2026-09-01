# Task 081 — 实现最小 pre-D8/R8 平台 aconfig 引用改写

**Authority**: `redline-gated self-commit`（用户明确批准本 brief 后才可 dispatch；worker 不 push）
**Reports To**: Chief architect
**执行方式**: shared checkout 串行；只能使用显式 `joycode/Kimi-K3` 或 `joycode/Kimi-K3-jcloud`
**Base**: Chief 在 dispatch 前固定为包含本 brief 的已 push commit

## Goal

用 AGP 9.3.1 公开 instrumentation API，在 class compilation 后、D8/R8 前，对 Task 080 已证明的 166 个 program class 做 reference-only 改写。只启用四条 runtime-critical exact mapping；不修改 class identity，不打包平台定义。

本任务只实现 build logic、冻结输入和 focused tests。不得构建 app APK，不得运行 R8、模拟器或 ADB。

## Approved design（用户批准后生效）

- 在 `buildSrc` 新增仓库内 Gradle plugin。
- 只在 `:app` 注册 `InstrumentationScope.ALL`。
- `isInstrumentable` 只接受冻结 allowlist 中 166 个 class identity。
- visitor 只改四个 exact source type 的引用；必须保持原始 `this_class` 和当前 class 自引用。
- 使用 `FramesComputationMode.COPY_FRAMES`。
- `settings.gradle.kts` 不变；不新增 production Gradle module。

四条 mapping：

```text
android.app.Flags -> com.android.internal.hidden_from_bootclasspath.android.app.Flags
android.os.Flags -> com.android.internal.hidden_from_bootclasspath.android.os.Flags
android.view.accessibility.Flags -> com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags
com.android.window.flags.Flags -> com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags
```

## Allowed Paths

只能修改或新增：

- `app/build.gradle.kts`
- `buildSrc/build.gradle.kts`
- `buildSrc/src/main/**`
- `buildSrc/src/test/**`
- `gradle/aosp17-critical-aconfig-reference-rules.txt`
- `gradle/aosp17-critical-aconfig-reference-classes.txt`
- `docs/adr/0008-pre-dex-aconfig-reference-rewrite.md`
- `docs/issues/2026-09-02-c5-pre-dex-reference-rewrite.md`
- `docs/orchestration/tasks/081-c5-pre-dex-reference-rewrite.md`（只补实际命令、证据、checkbox）

临时文件只能写入：

- `/tmp/task081-c5-pre-dex-reference-rewrite/`

## Forbidden Paths / Actions

- 不得修改 `settings.gradle.kts`、根 `build.gradle.kts`、version catalog、任何 Android module 的源码、资源、manifest、ProGuard、SDK、`libs/**`、AOSP 或 `out/**`。
- 不得修改/复制 AOSP SystemUI source import。
- 不得创建 stub，不得复制、生成或打包 platform class。
- 不得使用 `dontwarn`、suppression、post-R8 DEX rewrite、raw JarJar 或 class deletion。
- 不得运行 `:app:assembleDebug`、`:app:assembleRelease`、任何 Android module compile、R8、Soong/Ninja、emulator 或 ADB。
- 不得恢复 Task 079 或扩大到 725 条规则/464 个 stock 输入。
- Python 一律使用 `uv run`；禁止直接 `python`/`python3`。
- 不得 `git add -A` 或 `git add .`。

## Frozen provenance

完整 AOSP rules owner：

```text
/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt
```

- 完整规则文件 SHA-256：`f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`
- 完整规则语义：725 条 exact rules、726 物理行
- checked-in 四规则文件：按 source 字典序、LF、末尾换行
- 四规则文件 SHA-256：`ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85`
- checked-in class allowlist：Task 080 明细中的 166 个唯一 dot-FQCN，字典序、LF、末尾换行
- allowlist SHA-256：`926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b`

不得从 `/tmp/task080-*` 读取实现输入；Task 080 的 durable owner 是 `docs/issues/2026-09-01-c5-focused-reference-origins.md`。允许用 `uv run` inline helper 从该报告四个“逐目标引用类明细”生成候选 allowlist，但最终必须由 count + SHA 验证精确身份。

## TDD steps

- [ ] 依次读取 `AGENTS.md`、`docs/orchestration/CHARTER.md`、本 brief；独立核实 `provider/modelId` 后打印完整 `CONTRACT:`，等待 Chief 接受。
- [ ] 确认 fixed base、clean tree、无 active Gradle/Soong；只创建批准的 `/tmp` root。
- [ ] 先写 focused tests 和 fixtures；在没有 production implementation 时运行并记录预期 RED。
- [ ] 写入四规则文件与 166-class allowlist；验证精确 count、排序、LF、末尾换行与 SHA。
- [ ] 实现 fail-closed rule/allowlist loader；缺失、重复、格式错误、count/SHA/集合漂移均失败。
- [ ] 实现 ASM reference-only visitor：覆盖 descriptor、signature、annotation、instruction、handle、invokedynamic 等类型位置；不把任意字符串常量当类引用。
- [ ] 保持每个输入 class 的 `this_class` 与自引用；任何输出都不得定义四个 hidden target。
- [ ] 实现 `AsmClassVisitorFactory` 与 app plugin 注册；`isInstrumentable` 只接受 166-class allowlist，scope 固定 `ALL`，frames 固定 `COPY_FRAMES`。
- [ ] 在 `app/build.gradle.kts` 只应用该 buildSrc plugin；不得添加其他构建行为。
- [ ] 新增 ADR 0008，记录 provenance、seam、reference-only ownership、allowlist、fail-closed、替代方案和回滚方式。
- [ ] 运行 focused GREEN gate；不得运行 app build。
- [ ] 更新本 brief 与 issue 的实际命令/结果；显式 stage Allowed Paths，英文 commit，不 push。

## Mandatory tests

focused tests 至少证明：

1. checked-in rules 恰为四条映射，count/SHA/顺序正确，且每条逐字存在于 frozen full AOSP rules；
2. allowlist 恰为 166 个唯一 dot-FQCN，count/SHA/顺序正确；
3. allowlisted caller 的真实 class type reference 被改写；
4. 非 allowlisted class 不被 factory 接受；
5. source-named input class 的 `this_class` 和自引用不变，但对其他 mapped source 的引用可改写；
6. output `this_class` 不得等于任一 hidden target；
7. 普通字符串常量中的旧名不变；
8. 至少覆盖 descriptor/signature/annotation/type instruction/method handle/invokedynamic 的 reference remap；
9. malformed/duplicate/missing/hash drift 均 fail closed；
10. plugin 注册只发生在 Android application variant，scope 为 `ALL`、frames 为 `COPY_FRAMES`。

## Worker verification

允许的唯一 Gradle gate 是 build logic 自身的 focused test/check，例如：

```bash
./gradlew -p buildSrc test --console=plain
```

实际 task 名以实现为准，但不得触发根工程 Android modules。另运行：

```bash
sha256sum \
  gradle/aosp17-critical-aconfig-reference-rules.txt \
  gradle/aosp17-critical-aconfig-reference-classes.txt
git diff --check
```

若 buildSrc 独立 gate 意外配置或执行任何 Android module task，立即停止并报告。

## Acceptance

Worker 报告必须给出：

```text
RULES=4
RULES_SHA256=ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85
ALLOWLIST_CLASSES=166
ALLOWLIST_SHA256=926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b
REFERENCE_ONLY_TESTS=PASS
HIDDEN_TARGET_DEFINITIONS=0
ANDROID_APP_BUILD=NOT_RUN
RESULT=PASS
```

Chief 将独立检查：

- exact Allowed Paths 与 clean diff；
- buildSrc focused tests；
- rules/allowlist count、SHA 与 provenance；
- plugin 仅在 `:app` 使用 public AGP instrumentation seam；
- visitor 永不修改 `this_class`、永不产生 hidden target definition；
- 本任务没有 APK build/runtime 成功声明。

## Mandatory halt

发生任一情况立即停止，不得换方案：

1. public AGP instrumentation API 无法编译或无法表达 reference-only visitor；
2. 实现需要修改 `settings.gradle.kts`、Android module source、`libs/**`、SDK、AOSP/out 或规则之外路径；
3. 实现需要预改写/升版 JAR/AAR、删除 class、复制平台类、`dontwarn`、raw JarJar 或 DEX patch；
4. 无法从 Task 080 durable report 重建精确 166-class allowlist；
5. focused test 不能证明 `this_class` 保持和 hidden definition 为零；
6. 需要运行 app build 才能完成本任务。
