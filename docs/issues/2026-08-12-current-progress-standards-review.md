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
