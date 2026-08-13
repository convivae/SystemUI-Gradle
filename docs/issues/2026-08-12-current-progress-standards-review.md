# 当前进度规范审查与 APK 就绪度评估

> 审查日期：2026-08-12
> 审查基线：`05ea2064..cde2a6ed`
> 当前提交：`cde2a6ed`（`main` 与 `origin/main` 一致）
> 后续实施计划：[`../superpowers/plans/2026-08-12-build-to-apk-readiness.md`](../superpowers/plans/2026-08-12-build-to-apk-readiness.md)

## 一、审查目标

本次审查回答三个问题：

1. 另一个 AI 在依赖升级、AGP built-in Kotlin 迁移、KSP/Dagger 和产物提交方面的改动，是否符合项目既定规则；
2. 当前里程碑能否在干净 checkout 中复现，距离 `:app:assembleDebug` 还有哪些真实阻塞；
3. 下一步应按什么顺序推进，才能保持 AOSP 对齐并避免 stub、伪造资源或错误产物进入 APK。

本次只做审查和规划，不修改 AOSP 镜像源码、AIDL 或资源。

## 二、结论摘要

### 2.1 总体判断

**总体方向正确，规范符合度较高，但“只剩 2 个 Kotlin 错误即可进入 APK 验证”的状态描述不完整。**

已经确认的正向成果：

- 13-module 拓扑与 AOSP `Android.bp` 语义一致；`:app` 无独立源码，只依赖 `:SystemUI-core`；
- SystemUI 源码、AIDL 和资源未因本轮升级被替换为 stub；
- KSP + Dagger 在 fresh checkout 中可从零生成 2933 个文件；
- Kotlin/Compose/Dagger/AndroidX 升级整体使用官方 Maven 坐标；
- `libs/` 已纳入 Git，fresh checkout 无需先从 AOSP 重新生成 AAR；
- 57 个 Python 工具测试全部通过；
- AOSP 对齐检查的 `MISSING`、`MISPLACED`、`EXTRA` 均为 0，已有差异受 CONV 记录约束。

但首次实际运行 `:app:assembleDebug` 后，发现除 2 个已知 Kotlin 错误外，还有两类独立 APK 打包阻塞：

1. `WindowManager-Shell.aar` 与 `WindowManager-Shell-shared.aar` 重复包含 12 个 shared AIDL 生成类；
2. `settingslib-flags.jar` 与 `systemui-shared-flags.jar` 是缺少方法 `Code` attribute 的 header/turbine 类，作为 runtime `implementation` 进入 D8 后失败。

因此当前应定义为：

> **KSP 里程碑已完成；core Kotlin 接近通过；APK 打包链路已经能启动，但尚有依赖产物边界与 runtime JAR 正确性问题。**

这不否定已有迁移成果，但下一步不能只修 `GuardedBy` 后就宣称 APK 可构建。

### 2.2 规范判定矩阵

| 规则 | 判定 | 证据与说明 |
|------|------|------------|
| P：禁止 stub | 通过 | 本轮未新增 Java/Kotlin stub；两个失败的 flag JAR 是既有 Soong header 产物选型错误，不应通过手写实现规避 |
| S：SystemUI 自有代码源码优先 | 通过 | 13-module 生产图继续使用 SystemUI 源码模块；未回退到 SystemUI fat prebuilt |
| C：源码/AIDL/res 不漏不多 | 通过 | 对齐工具：`MISSING=0`、`MISPLACED=0`、`EXTRA=0` |
| F：framework 不源码复制 | 通过 | 隐藏 API 继续通过 SysUISdk/framework JAR；未复制 framework 源码 |
| R：资源来源与 CONV | 通过 | 本轮没有无标记修改 res；现有 MODIFIED 项均有既有 CONV 记录 |
| B：按 `Android.bp` 语义对齐 | 基本通过 | 模块边界正确；但 SettingsLib flag 的 `libs`/runtime 语义和 WM-Shell shared AIDL 交付边界需要修正 |
| D：文档先行与状态真实 | 部分通过 | 升级过程有 issue 文档；但 APK 打包错误此前未运行、未记录，部分构建脚本注释和 README 已漂移 |
| I：整体向前推进 | 通过 | built-in Kotlin、KSP 0 错误、依赖升级和自包含产物均是可维护的正向推进；错误数未被错误地作为回滚条件 |

## 三、审查范围与方法

### 3.1 Git 范围

- `HEAD`：`cde2a6ed`
- 远端：`origin/main = cde2a6ed`
- 工作区：审查开始前干净
- `cde2a6ed` 之后没有本地或远端新增进度
- 实质审查区间：`05ea2064..cde2a6ed`

该区间主要包含：

- Dagger/KSP binding graph 修复；
- 依赖升级与 AGP built-in Kotlin 迁移；
- built-in Kotlin 下 source set 与 AIDL/KSP 集成；
- 文档同步；
- JAR/AAR/本地 Maven 产物提交到 Git。

### 3.2 实际执行的验证

```text
python3 -m unittest discover -s tools/tests -p 'test_*.py'
=> Ran 57 tests, OK

python3 tools/check_source_alignment.py --strict
=> MISSING=0, MISPLACED=0, EXTRA=0
=> 1 个源码 MODIFIED 与 86 个资源 MODIFIED 均为既有 CONV 差异

./gradlew :SystemUI-core:kspDebugKotlin --rerun-tasks --console=plain
=> BUILD SUCCESSFUL
=> 2933 个生成文件
=> DaggerReferenceGlobalRootComponent.java 存在

./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain
=> BUILD FAILED
=> 仅 2 个错误：javax.annotation.concurrent.GuardedBy 未解析

./gradlew :app:assembleDebug --console=plain
=> BUILD FAILED
=> core Kotlin 2 个错误
=> WM-Shell 12 个重复类
=> 两个 flag JAR 在 D8 阶段因缺少 Code attribute 失败
```

另外在 `/tmp/SystemUI-Gradle-fresh-review` 使用 `git clone --no-local` 创建无项目构建缓存的 checkout：

```text
HEAD=cde2a6e
tracked_lib_files=59
./gradlew :SystemUI-core:kspDebugKotlin --console=plain
=> BUILD SUCCESSFUL in 40s
=> 87 tasks executed
=> generated_files=2933
```

这证明“提交的依赖产物足以复现 KSP 里程碑”成立；它不等价于“fresh checkout 已可产出 APK”。

## 四、符合既定方向的改动

### 4.1 模块拓扑

`settings.gradle.kts` 当前恰好包含 13 个目标模块。`:app` 中只有：

```kotlin
implementation(project(":SystemUI-core"))
```

且 `app/src/main/` 只有 AOSP manifest，没有新增 app 层入口源码。这符合 ADR 0003 和规则 B。

### 4.2 built-in Kotlin 与 KSP

迁移结果在 debug 变体上有效：

- Android 模块不再应用旧 `kotlin-android` 插件；
- JVM 模块仍使用 Kotlin JVM 插件；
- KSP `2.2.10-2.0.2` 与 AGP 内置 Kotlin 2.2.10 对齐；
- Dagger 2.59.2 使用新的 binding graph 行为；
- AIDL 生成源码已加入 Kotlin source set；
- fresh checkout 可完成 KSP 与 Dagger 生成。

这是本轮最重要、且已经有可重复证据支持的成果。

### 4.3 依赖与产物提交

- 公网第三方依赖集中在 version catalog；
- 8 个 `libs/aars/*.aar` 与本地 Maven 对应 AAR 字节一致；
- `libs/` 共有 59 个 tracked 文件，可被 fresh checkout 直接取得；
- 没有要求新 clone 先执行 AOSP 打包脚本。

该方向符合用户对可复现仓库的明确要求。

## 五、发现的问题

### P1：APK 打包使用了不可执行的 header flag JAR

**位置：**

- `SystemUI-core/build.gradle.kts:168-175`
- `SystemUI-core/build.gradle.kts:206-207`
- `libs/settingslib-flags.jar`
- `libs/systemui-shared-flags.jar`

**现象：**

`:app:desugarDebugFileDependencies` 报错：

```text
Absent Code attribute in method that is not native or abstract
```

受影响产物：

- `libs/settingslib-flags.jar`
- `libs/systemui-shared-flags.jar`

`javap -c` 已确认两者当前 `Flags` 方法无字节码。它们可以作为编译 header，但不能作为 runtime `implementation` 进入 D8。

**AOSP 语义：**

- `aconfig_settingslib_flags_java_lib` 在 SettingsLib `Android.bp` 中位于 `libs`，旁注说明该 flag 库已经加入 framework JAR；Gradle 侧应使用 `compileOnly`，不应打进 APK；
- `com_android_systemui_shared_flags_lib` 是 SystemUI shared 的生产依赖，需要使用 Soong `javac/...jar` 的完整实现产物。该完整 JAR 已存在，且 `Flags` 方法包含 `Code` attribute。

**禁止的错误修法：**

- 不得手写 Flags stub；
- 不得仅用 D8 参数跳过校验；
- 不得把所有 flag JAR 一律改为 `compileOnly`，因为 shared flags 在 APK 中需要真实实现。

### P1：WM-Shell 两个 AAR 的 shared AIDL 类重复

**位置：**

- `SystemUI-core/build.gradle.kts:198-202`
- `tools/package_aosp_aar.py` 中两个 WM-Shell CONFIG
- `libs/aars/WindowManager-Shell.aar`
- `libs/aars/WindowManager-Shell-shared.aar`

**现象：**

`:app:checkDebugDuplicateClasses` 报告 12 个重复类，来自 3 个 AIDL 接口及其嵌套生成类：

- `IFocusTransitionListener`
- `IHomeTransitionListener`
- `IShellTransitions`

实测：

- 主 Shell AAR：1862 entries，其中 `com/android/wm/shell/shared/` 有 12 个；
- shared AAR：154 entries，其中该 package 有 152 个；
- 两者交集正是上述 12 个 AIDL 生成类。

AOSP 主 `WindowManager-Shell` 和 `WindowManager-Shell-shared` 都引用 `:wm_shell-shared-aidls`；独立 Gradle 同时消费两件 AAR 时必须在交付层保证 class set 无交集。不能删除整个 shared AAR，因为其中还有 140 个主 AAR 不包含的生产类。

### P2：release KSP 错误依赖 debug AIDL

**位置：** `SystemUI-core/build.gradle.kts:307-311`

当前配置：

```kotlin
tasks.matching { it.name.startsWith("ksp") }.configureEach {
    dependsOn("compileDebugAidl")
}
```

`kspReleaseKotlin --dry-run` 已证明 release 任务图会拉入 `:SystemUI-core:compileDebugAidl`，却没有拉入 `:SystemUI-core:compileReleaseAidl`。与此同时 release Kotlin source set 指向 release AIDL 输出目录。

这会让 release 变体读取错误变体的生成接口。应改为 debug→debug、release→release 的显式映射，并用 dry-run 做回归验证。

### P2：AGP “全部升级到最新”声明与实际版本不一致

**位置：**

- `settings.gradle.kts:8-9`
- `gradle/libs.versions.toml:3`
- `docs/HANDOFF.md:47-49`
- `docs/issues/2026-08-12-deps-upgrade-builtin-kotlin.md:29-35`

升级文档自己确认最新稳定 AGP 为 9.3.1，且同样嵌入 Kotlin 2.2.10；实际仍为 AGP 9.2.0，同时 handoff 声明“所有依赖升级到公网最新可用版本”。

处理方式只有两种：

1. 升级并验证 AGP 9.3.1；或
2. 记录留在 9.2.0 的具体兼容性证据，并把“全部最新”改成带约束的准确表述。

当前没有看到保留 9.2.0 的技术证据，因此计划中应先验证 9.3.1。

### P2：维护文档与构建脚本注释发生版本漂移

代表性位置：

- `SystemUI-core/build.gradle.kts:6` 写 Dagger 2.60.1，实际为 2.59.2；
- `SystemUI-core/build.gradle.kts:94,102` 写 Kotlin 2.3.x，实际为 2.2.10；
- `SystemUI-core/build.gradle.kts:121-123` 写 KSP 2.3.11/Kotlin 2.3.21/Dagger 2.60.1；
- `build.gradle.kts:4-6` 写 KSP 2.3.11/Kotlin 2.3.21；
- `gradle/libs.versions.toml:96` 与 core 注释仍写 Compose 1.9.0-alpha01；
- `README.md:70-74` 仍把资源描述为 `SystemUI-core/res-*` 且称其 gitignored，实际资源 owner 是 `SystemUI-res`，产物也已提交。

这些不会立即改变编译结果，但会误导后续 AI 做出错误依赖判断，违反文档真实记录要求。

### P3：构建卫生与未来兼容警告

1. `git diff --check 05ea2064..HEAD` 有 1 个 EOF 空行和 4 个尾随空格；
2. `android.sourceset.disallowProvider=false` 已废弃，将在 AGP 10 删除；
3. `android.suppressUnsupportedCompileSdk=JdJkcSdk` 未包含实际 preview 名 `SysUISdk`；
4. Room KSP 未配置 schema 输出；
5. Kotlin 警告指出 3 个 data class copy visibility 问题会在 language 2.3 变为错误。

前两项应在本轮已知阻塞之后立即清理。Room schema 和 Kotlin 2.3 源码兼容应单独记录，不能通过 `@Suppress` 或无 CONV 修改 AOSP 源码。

## 六、下一步优先级

按风险和依赖关系排序：

1. **补官方 `jsr305` 依赖**，解决 `GuardedBy` 两个 core Kotlin 错误；
2. **纠正 flag JAR runtime 语义**：SettingsLib flags 改 `compileOnly`，shared flags 换完整 javac JAR；
3. **修复 WM-Shell AAR class set 交集**，重新生成并安装本地 Maven AAR；
4. **修复 KSP/AIDL variant 映射**，移除已废弃 provider 开关；
5. **验证 AGP 9.3.1**，并清理所有版本注释、README 和格式漂移；
6. **重新运行完整验证链**，以 `:app:assembleDebug` 的新结果建立下一里程碑；
7. 若出现新的打包错误，先写入 issue 并按 AOSP `Android.bp` 查来源，不得用 stub、排除源码或伪造资源绕过。

具体文件、测试、提交边界见实施计划：

[`docs/superpowers/plans/2026-08-12-build-to-apk-readiness.md`](../superpowers/plans/2026-08-12-build-to-apk-readiness.md)

## 七、审查后的里程碑定义

完成本审查后，项目状态应按以下口径对外描述：

- KSP/Dagger debug：已通过，fresh checkout 可复现；
- core Kotlin debug：2 个 `jsr305` 依赖错误；
- APK debug：除上述 Kotlin 错误外，还有 WM-Shell duplicate classes 和两个 flag JAR D8 错误；
- 13-module/AOSP 对齐：保持正确；
- Python 工具测试：57/57 通过；
- APK：尚未生成，不得声明 build successful。

## 八、实施记录

### Task 1：JSR-305 依赖与 Compose compiler plugin（2026-08-12）

**变更**：

- `gradle/libs.versions.toml` 新增 `com.google.code.findbugs:jsr305:3.0.2`；
- `SystemUI-core/build.gradle.kts` 新增 `implementation(libs.jsr305)`；
- `SystemUI-core/build.gradle.kts` 新增 `alias(libs.plugins.kotlin.compose)`。

**验证命令与结果**：

```bash
./gradlew :SystemUI-core:compileDebugKotlin --console=plain
# 变更前：BUILD FAILED；CommunalAppWidgetHost.kt 仅有 concurrent/GuardedBy 2 个错误

./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain
# 变更后：BUILD SUCCESSFUL；Kotlin errors: 0
```

**额外根因**：补 JSR-305 后，编译第一次进入 backend codegen，暴露
`Couldn't inline method call: Box$default`。AOSP Soong 在
`build/soong/java/base.go` 中对包含 `androidx.compose.runtime_runtime` static lib 的模块自动追加
`kotlin-compose-compiler-plugin`；`SystemUI-core` 符合该条件且含 154 个 `@Composable` Kotlin 文件，
但 Gradle 模块此前未应用 Compose compiler plugin。应用插件后 Box inline IR 错误消失。

### Task 2：aconfig JAR compile/runtime 语义（2026-08-12）

**变更**：

- 新增 `tools/package_aconfig_jars.py` 和 `tools/tests/test_package_aconfig_jars.py`；
- `libs/systemui-shared-flags.jar` 替换为 AOSP Soong `javac` 完整实现 JAR（7111 → 11197 bytes），方法含 `Code` attribute；
- `SystemUI-core/build.gradle.kts` 将 `settingslib-flags.jar` 从 `implementation` 改为 `compileOnly`。

**TDD 记录**：

```bash
python3 -m unittest tools.tests.test_package_aconfig_jars -v
# RED：FileNotFoundError: tools/package_aconfig_jars.py
# GREEN：2 tests passed
```

**验证命令与结果**：

```bash
python3 tools/package_aconfig_jars.py systemui-shared-flags
javap -classpath libs/systemui-shared-flags.jar -p -c com.android.systemui.shared.Flags
# ambientAod() 等方法含 Code attribute

./gradlew :app:desugarDebugFileDependencies --rerun-tasks --console=plain
# BUILD SUCCESSFUL；Absent Code attribute 不再出现

./gradlew :SystemUI-core:compileDebugKotlin --console=plain
# BUILD SUCCESSFUL；Kotlin errors: 0

python3 -m unittest discover -s tools/tests -p 'test_*.py'
# 59 tests passed
```

### Task 3：WM-Shell AAR class-set 去重（2026-08-12）

**变更**：

- `tools/package_aosp_aar.py` 新增确定性 `exclude_prefixes` 机制；
- `WindowManager-Shell` config 仅排除 3 个由 shared artifact 拥有的 AIDL interface class tree：
  `IFocusTransitionListener`、`IHomeTransitionListener`、`IShellTransitions`；
- `libs/aars/WindowManager-Shell.aar` 与本地 Maven 交付 AAR 重新生成（4352053 → 4341027 bytes）。

**TDD 记录**：

```bash
python3 -m unittest tools.tests.test_package_aosp_aar.TestAssembleAar.test_excluded_prefix_is_omitted_but_other_classes_remain -v
# RED：TypeError: assemble_aar() got an unexpected keyword argument 'exclude_prefixes'
# GREEN：1 test passed
```

**验证命令与结果**：

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
# 60 tests passed

python3 tools/package_aosp_aar.py WindowManager-Shell
python3 tools/install_aar_to_maven.py
# libs/aars 与 libs/maven 中的 WindowManager-Shell AAR 字节一致

# ZIP class-set intersection check
# WindowManager-Shell ∩ WindowManager-Shell-shared = 0

./gradlew :app:checkDebugDuplicateClasses --rerun-tasks --console=plain
# BUILD SUCCESSFUL；无 Duplicate class
```

### Task 4：variant-aware KSP/AIDL wiring（2026-08-12）

**变更**：

- `kspDebugKotlin → compileDebugAidl`；
- `kspReleaseKotlin → compileReleaseAidl`；
- 移除 `android.sourceset.disallowProvider=false`；
- AIDL 生成目录改为项目相对路径，避免 sourceSets provider API。

**实现调整**：计划中的 `tasks.named("kspDebugKotlin")` 在 KSP 任务注册完成前解析会失败；
实际改用 `tasks.matching { it.name == ...configureEach` 保持 lazy registration，
同时仍按 variant 精确映射，不回到 `startsWith("ksp") → compileDebugAidl`。

**验证命令与结果**：

```bash
./gradlew :SystemUI-core:kspReleaseKotlin --dry-run --console=plain
# 包含 :SystemUI-core:compileReleaseAidl，不包含 :SystemUI-core:compileDebugAidl

./gradlew :SystemUI-core:kspDebugKotlin --console=plain
# BUILD SUCCESSFUL；Kotlin errors: 0

./gradlew :SystemUI-core:kspReleaseKotlin --console=plain
# BUILD SUCCESSFUL；Kotlin errors: 0

# 两条实际构建均无 android.sourceset.disallowProvider deprecation warning
python3 -m unittest discover -s tools/tests -p 'test_*.py'
# 60 tests passed
```

**诊断记录**：一次性执行 debug+release 且加 `--rerun-tasks` 会在同一 Gradle daemon 中
同时运行两套完整链，KSP worker 因 4 GiB heap 耗尽失败。分别停止 daemon 后单独验证
两个 variant，均成功；这不是源码错误或 wiring 回归，未增加任何 workaround。

### Task 5：AGP 9.3.1 原子升级（2026-08-12）

**变更**：`settings.gradle.kts` 与 `gradle/libs.versions.toml` 同步从 AGP 9.2.0 升级到 9.3.1。
未改变 Kotlin/KSP 矩阵：AGP 内置 Kotlin 仍为 2.2.10，KSP 仍为 2.2.10-2.0.2。

**验证命令与结果**：

```bash
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --console=plain
# BUILD SUCCESSFUL；Kotlin errors: 0
```

### Task 6：构建脚本注释、资源 owner 与维护文档一致性（2026-08-12）

**变更**：

- 将构建脚本中的漂移版本注释修正为实际矩阵：Kotlin 2.2.10（AGP builtInKotlin）、
  KSP 2.2.10-2.0.2、Dagger 2.59.2、Compose 1.11.4、Room 2.8.4；
- 移除过时的 `android.suppressUnsupportedCompileSdk=JdJkcSdk`：AGP 9.3.1 下 `SysUISdk`
  不再触发 unsupported preview SDK 警告，保留旧 SDK 名 suppression 只会误导；
- 修正 `AGENTS.md` §1.8 的 SystemUI res owner 为 `SystemUI-res/res{, -keyguard, -product}/`；
- 同步 `README.md`、`docs/README.md`、`docs/CURRENT_STATE.md`、`docs/HANDOFF.md`、
  `docs/PITFALLS.md` 与 AGENTS 的真实状态：core Kotlin 0 错误、WM-Shell/header JAR/variant
  wiring 已修复、AGP 9.3.1 已验证、最终 APK 基线仍待 Task 7；
- 清理本轮触及的构建脚本与维护文档尾随空格。AOSP 镜像资源中的原始尾随空格保持不改，
  以满足 res 1:1 对齐规则。

**验证命令与结果**：

```bash
git diff --check
# 无输出

python3 -m unittest discover -s tools/tests -p 'test_*.py'
# 60 tests passed

./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --console=plain
# BUILD SUCCESSFUL；Kotlin errors: 0
```

### Task 7：完整验证链与真实 APK 阻塞（2026-08-12）

**验证命令与结果**：

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
# 60 tests passed

python3 tools/check_source_alignment.py --strict
# MISSING=0 MISPLACED=0 EXTRA=0 APP=0 RES-MISS=0 RES-EXTRA=0
# 已知允许偏差：1 个 src MODIFIED、86 个 res byte-diff；strict 通过

git diff --check
# 无输出

./gradlew :SystemUI-core:clean
./gradlew :SystemUI-core:kspDebugKotlin :SystemUI-core:compileDebugKotlin --console=plain
# BUILD SUCCESSFUL；KSP 2933 files；Kotlin errors: 0

./gradlew :app:assembleDebug --console=plain
# BUILD FAILED
# 首个失败任务：:SystemUI-core:compileDebugJavaWithJavac
# 42 errors；app-debug.apk 未生成
```

**结论**：KSP/Kotlin 里程碑保持通过，但最终 APK 仍未生成。新的首个失败层是
core Java 编译，不是 Kotlin、KSP、D8 duplicate-class 或资源打包阶段。完整日志为
`/tmp/final-app.log`。

**42 个 javac 错误的根因归属**（本任务只调查与记录，不添加依赖、不改源码）：

| 组别 | 首个错误 | AOSP owner / 实际解析来源 | 类别 | 根因 |
|------|----------|---------------------------|------|------|
| `NeverCompile` | `import dalvik.annotation.optimization.NeverCompile` | `libcore/dalvik/src/main/java/dalvik/annotation/optimization/NeverCompile.java`；Soong `core-libart` JAR 含该类 | JAR/SDK classpath | 该类不在 SysUISdk `android.jar`、`core-for-system-modules.jar` 或项目 `framework.jar` 中；现有 `keepanno-annotations.jar` 只含 `com.android.tools.r8.keepanno.*`，不含 `dalvik.annotation.optimization.*` |
| setupcompat | `com.google.android.setupcompat.util.WizardManagerHelper` | `external/setupcompat` 的 `android_library "setupcompat"` | AAR/传递依赖 | SettingsLib 在 Soong 中经 `setupdesign -> setupcompat` 获得 compile classpath；本地 `SettingsLib.aar` 的 POM 骨架没有传递依赖，AAR classes 也不含 setupcompat |
| Wi‑Fi flags | `import com.android.wifi.flags.Flags` | `packages/modules/Wifi/flags:wifi_aconfig_flags_lib` 的 Soong javac JAR | aconfig JAR | WifiTrackerLib 的 `static_libs` 依赖未进入本项目 classpath；现有 `WifiTrackerLib.aar` 不含该生成 flags 类 |
| zxing | `import com.google.zxing.WriterException` | `external/zxing:zxing-core` 的 Soong javac JAR | JAR/传递依赖 | SettingsLib 声明 `zxing-core` static lib；本地 SettingsLib AAR/POM 未携带该依赖 |
| WM‑Shell flags | `import static com.android.wm.shell.Flags.enableTaskbarOnPhones` | `frameworks/base/libs/WindowManager/Shell/aconfig:com_android_wm_shell_flags_lib` 的 Soong javac JAR | aconfig JAR | WindowManager-Shell 的 `static_libs` 依赖未进入本项目 classpath |
| unfold Dagger factories | `SystemUnfoldSharedModule_Companion_ProvideBgLooperFactory` | `SystemUI/shared/src/com/android/systemui/unfold/system/SystemUnfoldSharedModule.kt`；AOSP `SystemUISharedLib` 声明 `plugins: ["dagger2-compiler"]` | 注解处理配置 | Gradle `:SystemUI-shared` 未运行 KSP/Dagger；`:SystemUI-unfold` 的 KSP 只处理自身源码，无法为 shared 源码生成这些 factory。AOSP `SystemUISharedLib` javac JAR 确认包含 3 个缺失 factory |
| `SystemUI-tags` | `EventLogTags.writeSysuiKeyguard(int,int)` | `SystemUI-tags` 由 `SystemUI-core/src/com/android/systemui/EventLogTags.logtags` 生成 | 生成 JAR 过期 | 项目 `libs/SystemUI-tags.jar`（2026 bytes）缺少 `SYSUI_KEYGUARD`/`writeSysuiKeyguard`；当前 AOSP Soong javac JAR（2086 bytes）包含该方法 |
| media completion extra | `MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE` | AOSP prebuilt `androidx.media_media` 为 `1.7.0-alpha02`；公网 `androidx.media:media` 1.7.0 与最新 1.8.0 均含该常量 | Maven 版本约束 | 项目没有直接声明 `androidx.media:media`；`mediarouter:1.9.0-alpha01` 将其解析到 1.4.1，而 1.4.1 不含该常量 |

**后续合规调查/修复入口**（留给后续实施计划）：

```bash
# media 版本链证据
./gradlew :SystemUI-core:dependencyInsight \
  --configuration debugCompileClasspath --dependency androidx.media:media

# SystemUI-tags 过期证据
javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags
javap -classpath /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar \
  com.android.systemui.EventLogTags

# shared Dagger factory 缺失证据
find SystemUI-shared/build/generated/ksp/debug -type f
unzip -l /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/shared/SystemUISharedLib/android_common/javac/SystemUISharedLib.jar \
  | grep 'SystemUnfoldSharedModule'
```

**下一步**：为这些 Java classpath 缺口建立新的实施计划：补齐真实 AOSP JAR/AAR 或官方 Maven 约束、
让 `:SystemUI-shared` 按 AOSP `SystemUISharedLib` 的 `plugins: ["dagger2-compiler"]` 运行 KSP/Dagger、
重新生成 `SystemUI-tags.jar`，然后再运行 `:app:assembleDebug`。禁止用 stub、排除源码、伪造资源
或关闭 D8/javac 校验绕过这些错误。

---

## 后续修复记录

### Task 001（2026-08-13）：刷新 `libs/SystemUI-tags.jar`

对应 Task 7 八组根因中的 "SystemUI-tags" 组。`libs/SystemUI-tags.jar`
为 2026 字节的过期版本，缺少 `EventLogTags.writeSysuiKeyguard(int,int)`；
AOSP Soong `javac` 产物为 2086 字节且包含该方法。

操作：

```bash
# 1) 旧 jar 缺方法
javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep -c writeSysuiKeyguard
# 0

# 2) 用 AOSP Soong javac jar 覆盖
cp /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar libs/SystemUI-tags.jar
# 旧大小 2026 → 新大小 2086

# 3) 新 jar 含方法
javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard
#   public static void writeSysuiKeyguard(int, int);
```

来源单一可信：AOSP Soong `SystemUI-tags` 模块 `javac` 产物（由
`SystemUI-core/src/com/android/systemui/EventLogTags.logtags` 生成）。
本次未运行 Gradle 构建（单一产物替换，javap 已验证方法签名到位；
`:app:assembleDebug` 复验留待其余根因修复后统一进行）。

### Task 002（2026-08-13）：打包 zxing-core / wifi-flags / wm-shell-flags JAR

对应 Task 7 八组根因中的 “zxing”、“Wi‑Fi flags”、“WM‑Shell flags” 三组。
三组都是 Soong `static_libs` 传递依赖未进入 Gradle classpath（CHARTER Part 3
机制警告）：本地 `SettingsLib.aar` / `WifiTrackerLib.aar` / `WindowManager-Shell.aar`
的 POM 骨架不携带传递依赖，AAR classes 也不含这些生成 flags / 第三方库类。

**AOSP 来源**（均为 Soong `javac` 产物，非 turbine；`copy_jar` 有 turbine 守卫）：

| config | AOSP javac jar | 目标 | scope |
|--------|----------------|------|-------|
| `zxing-core` | `external/zxing/zxing-core/android_common/javac/zxing-core.jar`（608370 B，314 个 `com/google/zxing/` 类） | `libs/zxing-core.jar` | `implementation`（Soong `static_libs`，dex 进 APK） |
| `wifi-flags` | `packages/modules/Wifi/flags/wifi_aconfig_flags_lib/android_common/javac/wifi_aconfig_flags_lib.jar`（15664 B，含 `com/android/wifi/flags/Flags.class`） | `libs/wifi-flags.jar` | `compileOnly`（平台镜像在设备上提供） |
| `wm-shell-flags` | `frameworks/base/libs/WindowManager/Shell/aconfig/com_android_wm_shell_flags_lib/android_common/javac/com_android_wm_shell_flags_lib.jar`（13314 B，含 `com/android/wm/shell/Flags.class`） | `libs/wm-shell-flags.jar` | `compileOnly`（平台镜像在设备上提供） |

操作：

1. `tools/package_aconfig_jars.py` 的 `CONFIGS` 新增三条（顶部分别声明
   `ZXING_CORE_JAVAC` / `WIFI_FLAGS_JAVAC` / `WM_SHELL_FLAGS_JAVAC` 常量，沿用
   `systemui-shared-flags` 既有模式；`copy_jar` 复用既有 turbine 守卫与
   `zipfile.is_zipfile` 校验）。
2. `tools/tests/test_package_aconfig_jars.py` 为每条新 config 断言
   (a) 源路径含 `/javac/` 且不含 `turbine`，(b) 目的地在 `libs/` 下且名称正确，
   并新增 `test_copy_preserves_bytes_for_each_config` 用 `subTest` 对所有 CONFIGS
   逐一验证字节一致拷贝。
3. `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 64 tests ... OK`（60 → 64）。
4. 逐条 `python3 tools/package_aconfig_jars.py <name>`；`cmp` 确认三个 jar 与源 jar 字节一致。
5. `SystemUI-core/build.gradle.kts` 在 `systemui-shared-flags.jar` 行后新增三条，
   注释说明 scope 选择依据：zxing 为 Soong `static_libs`（`implementation`，dex 进 APK），
   两个 aconfig flags 为平台镜像提供（`compileOnly`，与 `settingslib-flags.jar` 同例）。

**验证**（rule D 如实记录）：

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain \
  -Dorg.gradle.jvmargs="-Xmx12g -Dfile.encoding=UTF-8" --no-daemon 2>&1 | tee /tmp/task002.log
# BUILD FAILED（首失败仍为 :SystemUI-core:compileDebugJavaWithJavac）

# 错误总数：62（Task 7 基线为 42）
grep -cE 'error:' /tmp/task002.log   # 62

# 三组目标根因已清零
grep -cE 'com\.google\.zxing|com\.android\.wifi\.flags|com\.android\.wm\.shell\.Flags' /tmp/task002.log
# 0
```

**错误数 42 → 62 的解释（rule I，非回归）**：三组目标的 import 语句原先在
javac 早期即报错，使编译器中止处理相关源文件，下游 "cannot find symbol" 被抑制；
现在这三组 import 全部解析成功，javac 得以深入这些文件，从而**更完整地暴露**
其余根因组（`NeverCompile`、`setupcompat`、`SystemUnfoldSharedModule_*Factory`、
`DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`、`SETTINGS_SECURE_USER_SETUP_COMPLETE`）
的全部出现位置。逐条核对 62 个错误的 `symbol:` / `location:`，全部归属 Task 7
已记录的八组根因，未引入任何新根因组，也未出现与 zxing / wifi-flags / wm-shell-flags
相关的新符号错误。结构向前推进，无回归。

**环境备注**：首次运行 `:SystemUI-core:compileDebugJavaWithJavac`（默认 4G daemon）
在 `compileDebugKotlin` 阶段 `OutOfMemoryError: Java heap space` 失败，未到达 javac。
这是环境资源问题，非代码问题；`gradle.properties` 的 `org.gradle.jvmargs=-Xmx4g`
属 Part 5.4 红线相邻，不在本任务 allowed_paths 内，故未改文件，改用 CLI
`-Dorg.gradle.jvmargs=-Xmx12g ... --no-daemon` 覆盖重跑通过。建议后续统一调大堆。
### Task 003（2026-08-13）：`:SystemUI-shared` 经 KSP 运行 Dagger

对应 Task 7 八组根因中的 "unfold Dagger factories" 组。AOSP
`frameworks/base/packages/SystemUI/shared/Android.bp` 的 `SystemUISharedLib`
声明 `plugins: ["dagger2-compiler"]`；Gradle `:SystemUI-shared` 此前只有
`implementation(libs.dagger)` 而未运行注解处理器，导致
`SystemUI/shared/src/com/android/systemui/unfold/system/SystemUnfoldSharedModule.kt`
的 3 个 `@Provides` factory 未生成，被 `:SystemUI-unfold` 源码（编译进 core javac）
引用时报 "cannot find symbol"。

操作（镜像 `:SystemUI-unfold` 的 KSP 模式，仅改 `SystemUI-shared/build.gradle.kts`）：

- plugins 块追加 `id("com.google.devtools.ksp")`；
- dependencies 块在 tier② compileOnly 与 tier③ implementation 之间追加
  `ksp(libs.dagger.compiler)`，注释对齐 AOSP `SystemUISharedLib`
  `plugins: ["dagger2-compiler"]`。未改版本、未加其它处理器、未触碰源码/资源/版本目录。

验证命令与结果：

```bash
./gradlew :SystemUI-shared:kspDebugKotlin --console=plain 2>&1 | tail -5
# BUILD SUCCESSFUL in 26s；52 actionable tasks: 52 executed

find SystemUI-shared/build/generated/ksp -name 'SystemUnfoldSharedModule*Factory*' | sort
# SystemUI-shared/build/generated/ksp/debug/java/com/android/systemui/unfold/system/SystemUnfoldSharedModule_Companion_ProvideBgLooperFactory.java
# SystemUI-shared/build/generated/ksp/debug/java/com/android/systemui/unfold/system/SystemUnfoldSharedModule_Companion_UnfoldBgDispatcherFactory.java
# SystemUI-shared/build/generated/ksp/debug/java/com/android/systemui/unfold/system/SystemUnfoldSharedModule_Companion_UnfoldBgProgressHandlerFactory.java

./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task003.log >/dev/null
grep -cE 'SystemUnfoldSharedModule_.*Factory|UnfoldBg(Dispatcher|ProgressHandler)Factory' /tmp/task003.log || echo '0 (factory group gone)'
# 0 (factory group gone)
```

说明：brief 列出的短名 `UnfoldBgDispatcherFactory` / `UnfoldBgProgressHandlerFactory`
实际生成名为 `SystemUnfoldSharedModule_Companion_UnfoldBgDispatcherFactory` /
`..._UnfoldBgProgressHandlerFactory`（`@Provides` 方法位于 `Companion` 对象）；
brief 的 `SystemUnfoldSharedModule*Factory*` glob 命中全部 3 个，与预期一致。

错误组归属与 delta：

- `:SystemUI-shared:compileDebugJavaWithJavac` UP-TO-DATE（factory 与 shared 源码一同编译通过）；
  `:SystemUI-core:compileDebugJavaWithJavac` 实际执行（非 SKIPPED）后 FAILED。
- core javac 剩余错误 0 处涉及 unfold/factory 符号；Task 7 八组中 "SystemUI-tags"
  组亦因 Task 001 修复在本构建中消失（0 命中）。其余错误全部落在 Task 7 已归属的另外 6 组：
  `NeverCompile`（`dalvik.annotation.optimization.NeverCompile`）、setupcompat
  （`WizardManagerHelper.SETTINGS_SECURE_USER_SETUP_COMPLETE`）、`com.android.wifi.flags`、
  `com.google.zxing`（`WriterException`）、`com.android.wm.shell.Flags`
  （`enableTaskbarOnPhones` / `enableTaskbarNavbarUnification`）、
  `MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`。
- 错误数变化：Task 7 基线 42；本次 core javac "error:" 行 70（= 35 条 raw javac +
  35 条 AGP 失败摘要重印），即 35 条去重错误，**较基线下降**，与 "unfold Dagger factories"
  组被解决一致。按规则 I，错误数仅作诊断；本改动结构上对齐 AOSP `Android.bp` 且未引入新错误组。
- 整体 `:app:assembleDebug` 仍因其余 6 组阻塞，APK 未生成（不在本任务范围）。
- 资源争用备注：本任务 Step 4 首次运行（900s）因与 sibling worker（wt-002）争用同一 Gradle
  daemon 且 core javac 较重而超时；待 wt-002 构建结束后重跑，1m19s 完成（Kotlin/KSP UP-TO-DATE，
  仅 javac 实跑）。非源码或 wiring 问题。

### Task 004（2026-08-13）：setupcompat AAR 经本地 Maven 交付

对应 Task 7 八组根因中的 “setupcompat” 组。AOSP `external/setupcompat` 是
`android_library "setupcompat"`（`resource_dirs: ["main/res"]`）；SettingsLib 在
Soong 中经 `setupdesign -> setupcompat` 获得 compile classpath，而本地 `SettingsLib.aar`
的 POM 骨架不带传递依赖、AAR classes 也不含 setupcompat，导致
`com.google.android.setupcompat.util.WizardManagerHelper`（及
`WizardManagerHelper.SETTINGS_SECURE_USER_SETUP_COMPLETE`）无法解析。

**用户决策（2026-08-13，本任务 brief 引用）**：因 setupcompat 含资源
（`resource_dirs: ["main/res"]`），采用 AAR 交付，jar-only 方案对本模块豁免。
`gradle/libs.versions.toml` 的 catalog-alias 增加为本任务唯一预授权的 toml 改动。

**AOSP 来源**（均为 Soong `javac` 产物 + 原始 res，无 turbine）：

| 输入 | AOSP 路径 |
|------|-----------|
| code | `external/setupcompat/setupcompat/android_common/javac/setupcompat.jar`（206400 B，126 个 `com/google/android/setupcompat/**` 类，无 R.class/R$） |
| res | `external/setupcompat/main/res`（`Android.bp resource_dirs: ["main/res"]`） |
| manifest | `external/setupcompat/AndroidManifest.xml`（788 B） |
| R.txt | `external/setupcompat/setupcompat/android_common/R.txt` |

**变更**（均在 allowed_paths 内）：

1. `tools/package_aosp_aar.py` 的 `CONFIGS` 新增 `"setupcompat"` 条目（code/res/manifest/rtxt/output；
   无 `exclude_prefixes`、无 `reject_sysui`——setupcompat 是 `com.google.android.setupcompat`，
   无 `com/android/systemui/` 类）。
2. `tools/tests/test_package_aosp_aar.py` 新增 `test_setupcompat_config_paths`（断言 javac 路径、
   不含 turbine、res/manifest/rtxt 路径、output 名、不 reject_sysui）；并把
   `test_configs_covers_six_artifacts` 的 CONFIGS 集合从 8 更新到 9（加入 "setupcompat"）。
3. `gradle/libs.versions.toml` 在 `systemui-settingslib-color` 行后新增
   `systemui-setupcompat = { group = "com.android.systemui", name = "setupcompat", version = "1.0.0" }`
   （与既有 `systemui-*` alias 同模式，inline version，未动 [versions] 块）。
4. `SystemUI-core/build.gradle.kts` 在 `implementation(libs.systemui.settingslib)` /
   `compileOnly(…/SettingsLib-full.jar)` 之后、`implementation(libs.systemui.iconloader)` 之前，
   新增 `implementation(libs.systemui.setupcompat)`（注释说明 setupdesign→setupcompat 传递来源）。

**`install_aar_to_maven.py` 不在 allowed_paths 的处理**：`tools/install_aar_to_maven.py` 使用
静态 `ARTIFACTS` dict（无 setupcompat）且不在本任务 allowed_paths 内，不得编辑。故不运行
`install_aar_to_maven.py` 全量安装（会改写既有 8 个 AAR 的 maven 副本，虽字节一致仍越界），
改为复用其 `install_aar()` 函数经 `python3 -c` import 直装 setupcompat 到
`libs/maven/com/android/systemui/setupcompat/1.0.0/`（AAR + POM 骨架），POM 字节与模板一致。
产物路径为 slashed `com/android/systemui/`（installer `group.replace(".", "/")`），brief 中
dotted `libs/maven/com.android.systemui/setupcompat/**` 为简写。未改 `install_aar_to_maven.py`，
`ARTIFACTS` 暂不含 setupcompat——**遗留**：后续需把 setupcompat 加入 `ARTIFACTS` 以支持
`install_aar_to_maven.py` 全量重装（需把该脚本纳入对应任务的 allowed_paths）。

**打包范围**：仅 `python3 tools/package_aosp_aar.py setupcompat`（不 `--all`），避免重写
allowed_paths 之外的既有 AAR。

**验证命令与结果**：

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
# Ran 65 tests ... OK（Task 002 后为 64；+1 test_setupcompat_config_paths → 65）

python3 tools/package_aosp_aar.py setupcompat
# setupcompat AAR → libs/aars/setupcompat.aar (194066 bytes)

# install_aar() import（不编辑 install_aar_to_maven.py）
python3 -c "import sys; sys.path.insert(0,'tools'); from pathlib import Path; \
from install_aar_to_maven import install_aar; \
install_aar(Path('libs/aars/setupcompat.aar'),'com.android.systemui','setupcompat','1.0.0',Path('libs/maven'))"
# installed: libs/maven/com/android/systemui/setupcompat/1.0.0/setupcompat-1.0.0.aar (194066 bytes)
#            libs/maven/com/android/systemui/setupcompat/1.0.0/setupcompat-1.0.0.pom

unzip -l libs/aars/setupcompat.aar | grep -E 'classes.jar|AndroidManifest.xml|res/' | head -5
# AndroidManifest.xml (788 B) / classes.jar (201834 B) / res/color-v23/... / res/layout/... / res/layout-sw600dp/...

# Maven AAR 的 classes.jar 内 setupcompat 类计数（AAR 类嵌在 classes.jar，须先解 classes.jar；
# brief step-4e 的 `unzip -l <aar> | grep -c 'com/google/...'` 对任何标准 AAR 均返回 0——
# classes 在嵌套 classes.jar 内，非 AAR 顶层；既有 SettingsLib.aar 同样返回 0，属验证形式问题）
unzip -p libs/maven/com/android/systemui/setupcompat/1.0.0/setupcompat-1.0.0.aar classes.jar \
  > /tmp/maven_sc_classes.jar && unzip -l /tmp/maven_sc_classes.jar | grep -c 'com/google/android/setupcompat/'
# 126
# 含 com/google/android/setupcompat/util/WizardManagerHelper.class + $SuwLifeCycleEnum.class

cmp libs/aars/setupcompat.aar libs/maven/com/android/systemui/setupcompat/1.0.0/setupcompat-1.0.0.aar
# IDENTICAL
```

**Step 6 acceptance（core javac）**：

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain \
  -Dorg.gradle.jvmargs="-Xmx12g -Dfile.encoding=UTF-8" --no-daemon 2>&1 | tee /tmp/task004.log
# BUILD FAILED in 2m16s（首失败仍为 :SystemUI-core:compileDebugJavaWithJavac）
# javac summary: 22 errors

grep -c 'setupcompat' /tmp/task004.log   # 0（brief step-6 grep）
grep -cE 'WizardManagerHelper|SETTINGS_SECURE_USER_SETUP_COMPLETE' /tmp/task004.log   # 0
```

**错误组归属与 delta**：

- setupcompat 组：**0 命中，已清零**。Task 7 八组中 “setupcompat”
  （`WizardManagerHelper` / `SETTINGS_SECURE_USER_SETUP_COMPLETE`）随本任务 AAR 落地而解析。
- 去重错误数：Task 7 基线 42 → Task 002（zxing/wifi/wm-shell-flags）62（升，已解释）→
  Task 003（unfold factories）35 → **Task 004 22**。Task 004 清除 setupcompat 组约 13 处错误
  （35 − 22）。按规则 I，错误数仅作诊断；本改动新增真实 AOSP AAR 产物、结构对齐 AOSP `Android.bp`
  且未引入新错误组。
- 剩余 22 条去重错误全部落在 Task 7 已归属的另外两组（均不在本任务范围）：
  - `NeverCompile`（`dalvik.annotation.optimization.NeverCompile`，20 处，跨 10 文件：
    VolumeDialogControllerImpl / CentralSurfacesImpl / NetworkControllerImpl /
    QuickSettingsControllerImpl / NotificationPanelViewController / QSImpl /
    NavigationBarControllerImpl / SysUiState / ScreenDecorations / KeyguardUpdateMonitor）；
  - `MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`（2 处，MediaDataUtils.java:80,82）。
- 整体 `:app:assembleDebug` 仍因 NeverCompile + MediaConstants 两组阻塞，APK 未生成（不在本任务范围）。
- 环境备注：`gradle.properties` 的 `org.gradle.jvmargs=-Xmx4g` 默认 daemon 在 core javac
  阶段 OOM（Task 002 已记录）；该文件属 Part 5.4 红线相邻、不在本任务 allowed_paths，未改文件，
  改用 CLI `-Dorg.gradle.jvmargs="-Xmx12g …" --no-daemon` 覆盖。`--no-daemon` 亦规避与
  sibling worker 争用同一 Gradle daemon（Task 003 已记录该争用）。

### Task 006（2026-08-13）：Pin androidx.media 1.8.0

对应 Task 7 八组根因中的 "media completion extra" 组。项目未直接声明
`androidx.media:media`；`mediarouter:1.9.0-alpha01` 将其传递解析到 1.4.1，
而 1.4.1 不含 `MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`，
导致 `MediaDataUtils.java:80,82` 报 cannot find symbol。公网
`androidx.media:media` 1.7.0 与最新 1.8.0 均含该常量。

**授权**：用户 2026-08-13 预批准 `androidx.media = 1.8.0` 的 toml 版本矩阵
编辑（CHARTER Part 5.4 红线，仅此一项）。authority = redline-gated。

**AOSP / Maven 来源核对（CHARTER Part 3 决策树）**：

```text
$ curl -s https://dl.google.com/dl/android/maven2/androidx/media/media/maven-metadata.xml | grep -E '<latest>|<release>'
    <latest>1.8.0</latest>
    <release>1.8.0</release>
```

1.8.0 为公网最高稳定版（高于 1.4.1），属 tier ③ 官方 Maven 坐标，
非 AOSP fork。规则③优先官方依赖，符合 AGENTS.md §1.5。

**变更**（均在 allowed_paths 内，仅触及 media 条目）：

1. `gradle/libs.versions.toml`：
   - [versions] 新增 `media = "1.8.0"`（紧邻 `androidxMedia`，注释标明与 mediarouter
     alias 区别；**未改** `androidxMedia = "1.9.0-alpha01"`）；
   - [libraries] 新增 `androidx-media = { group = "androidx.media", name = "media", version.ref = "media" }`（紧邻 media3 条目，沿用 group/name 风格）。
2. `SystemUI-core/build.gradle.kts`：在 `implementation(libs.androidx.mediarouter)` 后
   新增 `implementation(libs.androidx.media)`，注释说明 pin 原因。

**验证命令与结果**：

```bash
# Step 1：变更前解析证据（应为 1.4.1 via mediarouter）
./gradlew :SystemUI-core:dependencyInsight --configuration debugCompileClasspath \
  --dependency androidx.media:media 2>&1 | grep -E '1\.4\.1|1\.8\.0' | head -5
# androidx.media:media:1.4.1
#       - By conflict resolution: between versions 1.4.1 and 1.0.0
# androidx.media:media:1.0.0 -> 1.4.1

# Step 4a：变更后解析证据（应选中 1.8.0）
./gradlew :SystemUI-core:dependencyInsight --configuration debugCompileClasspath \
  --dependency androidx.media:media --console=plain 2>&1 | grep -E 'androidx.media:media' | head -3
# androidx.media:media:1.8.0
# androidx.media:media:1.8.0
# androidx.media:media:1.0.0 -> 1.8.0

# Step 4b：core javac + 常量错误 grep
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain \
  -Dorg.gradle.jvmargs="-Xmx12g -Dfile.encoding=UTF-8" --no-daemon 2>&1 | tee /tmp/task006.log >/dev/null
grep -c 'DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE' /tmp/task006.log || echo '0 (media group gone)'
# 0
# 0 (media group gone)
```

**错误组归属与 delta（rule I，仅诊断）**：

- media 组：**0 命中，已清零**。Task 7 八组中 "media completion extra"
  （`MediaConstants.DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE`，
  MediaDataUtils.java:80,82 共 2 处）随 1.8.0 pin 落地而解析。
- 去重错误数：Task 7 基线 42 → Task 002 62 → Task 003 35 → Task 004 22
  → **Task 006 20**。本次清除 media 组 2 处（22 − 20），与该组错误数一致。
  （`grep -cE 'error:'` 原始计数 40 = 20 raw + 20 AGP 摘要重印。）
- **未引入新错误组**：20 条去重错误全部为 `symbol: class NeverCompile`
  （`dalvik.annotation.optimization.NeverCompile`），跨 Task 7 已归属的同一组
  10 文件（VolumeDialogControllerImpl / CentralSurfacesImpl / NetworkControllerImpl /
  QuickSettingsControllerImpl / NotificationPanelViewController / QSImpl /
  NavigationBarControllerImpl / SysUiState / ScreenDecorations / KeyguardUpdateMonitor）。
- 整体 `:app:assembleDebug` 仍因 NeverCompile 组阻塞，APK 未生成
  （不在本任务范围；NeverCompile 由后续任务处理，需 keepanno 或 core-libart JAR）。
- 环境备注：`gradle.properties` 的 `org.gradle.jvmargs=-Xmx4g` 默认 daemon 在 core javac
  阶段 OOM（Task 002/004 已记录）；该文件属 Part 5.4 红线相邻、不在本任务
  allowed_paths，未改文件，改用 CLI `-Dorg.gradle.jvmargs="-Xmx12g …" --no-daemon`
  覆盖（与 Task 002/003/004 同例）。

### Wave 修复验证（2026-08-13，架构师亲验）

编排工作流修复波次（briefs 002–006，herdr worktree + worker，架构师审查后合并）结果：

| 根因组 | 修复 | 验证 |
|--------|------|------|
| zxing / Wi-Fi flags / WM-Shell flags | brief 002：`package_aconfig_jars.py` 打包 3 个 JAR（`2662423b`） | 架构师重跑 javac：3 组 grep = 0 |
| unfold Dagger factories | brief 003：`:SystemUI-shared` 接 KSP+Dagger（`e454feda`） | 3 个 factory 生成，组内 0 |
| setupcompat | brief 004：AAR + 本地 Maven + catalog alias（`f870be99`） | 126 类 + res 齐，组内 0 |
| androidx.media | brief 006：显式 pin 1.8.0（`ddd334fb`） | dependencyInsight 1.8.0，组内 0 |
| SystemUI-tags.jar | pilot brief 001（`8cc85f74`） | 此前已修复 |
| NeverCompile | **未修**：调研完成（brief 005，`d7eccecb`），等用户对方案拍板 | 仍 20 个 distinct 错误 |

**当前 `:app:assembleDebug` 阻塞（按任务图顺序）**：

1. `:app:processDebugResources` — **新浮出**（非回归；Task 7 时 javac 先失败、该任务未调度）：
   WM-Shell AAR manifest 含 `android:featureFlag="com.android.wm.shell.enable_retrievable_bubbles"`
   （AOSP `frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml:39,53`），
   AAPT `--feature_flags` 参数中没有该 flag。候选方向：SysUISdk 缺 feature-flags 声明 /
   AGP feature-flags 机制对齐。待调查。
2. `:SystemUI-core:compileDebugJavaWithJavac` — NeverCompile 组 20 个错误。
   w005 调研结论：该类**存在**于已接线 compileOnly 的 `libs/android_module_lib_stubs_current.jar`，
   但被 bootclasspath split-package 遮蔽；推荐方案 = 按 AGENTS.md §2.4 先例补 SysUISdk `android.jar`。

验证命令（main，2026-08-13）：
`./gradlew :app:assembleDebug` → FAILED at `:app:processDebugResources`（/tmp/waveC-app.log）；
`./gradlew :SystemUI-core:compileDebugJavaWithJavac` → FAILED，40 error: 行（20 distinct，全为 NeverCompile 组，/tmp/waveC-javac.log）；
`python3 -m unittest discover -s tools/tests` → 65/65 OK；`check_source_alignment.py --strict` → 0/0/0（MODIFIED 1 为已知 CONV 偏差）。

### NeverCompile 修复 + javac 里程碑（2026-08-13，架构师亲验）

用户 2026-08-13 批准调研推荐方案 (a)（`docs/issues/2026-08-13-nevercompile-research.md`）。
brief 008（worker `a35906f4`）：新增 `tools/patch_sdk_dalvik_annotations.py`（幂等、`.orig` 备份、
仅注入缺失类），将 AOSP `core-libart` javac JAR 的 4 个 `dalvik.annotation.optimization.*`
类（NeverCompile/NeverInline/DeadReferenceSafe/ReachabilitySensitive）补入 SysUISdk
`android.jar` 与 `core-for-system-modules.jar`。

架构师亲验（main）：SDK 两 jar 各含 6 个目标类；工具重跑 no-op；`python3 -m unittest` 77/77 OK；
**`:SystemUI-core:compileDebugJavaWithJavac` BUILD SUCCESSFUL，0 错误（/tmp/milestone-javac.log）——
Task 7 的 8 组 javac 根因全部清零**。

注意：SysUISdk 不在 git，新机器/重装 SDK 后必须重跑 `python3 tools/patch_sdk_dalvik_annotations.py`。

剩余唯一阻塞：`:app:processDebugResources` 的 WM-Shell `android:featureFlag`（调研结论：
推荐 AGP `androidResources.additionalParameters("--feature-flags", ...)`，待用户批准后实施）。
