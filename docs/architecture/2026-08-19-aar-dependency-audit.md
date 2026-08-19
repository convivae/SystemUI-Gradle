# 全量 AAR 依赖审查（Task 017，只读）

> **审查基线**：worktree `task-017-audit` @ commit `de0f2151`（"docs: brief tasks 015
> (B2 implementation) and 017 (AAR audit)"）。
> **方法**：静态分析（grep、`unzip -l`、`sha256sum`、字节码包检查）；**未运行任何 Gradle
> 构建**（用户/brief 明令禁止 `./gradlew`）。
> **范围**：`libs/aars/`、`libs/maven/` 下的 AAR 产物及其消费点；jar 仅作相邻发现记录
> （brief Non-goals："不评价 jar"）。
> **Task 015 提示**：Task 015（并行，B2 = "SettingsLib 拆 7 个新 AAR"）尚未合入本基线；
> 本审查覆盖当前基线 10 个 AAR，Task 015 的新增 7 个属已批准增量，需在合并后复审。

## 1. 全量 Inventory 表

### 1.1 `libs/aars/` 直接 AAR（10 个，全部 git-tracked）

| # | AAR 文件 | 大小(bytes) | SHA-256(前16) | 提供者 | Maven 对应坐标 |
|---|---------|-----------:|--------------|--------|----------------|
| 1 | animationlib.aar | 19680 | 91f85a93f174c190 | `package_aosp_aar.py` CONFIGS["animationlib"] | com.android.systemui:animationlib |
| 2 | iconloader.aar | 106858 | a4c6def32f12ec38 | `package_aosp_aar.py` CONFIGS["iconloader"] | com.android.systemui:iconloader |
| 3 | LowLightDreamLib.aar | 28914 | 2a7b0939611434b6 | `package_aosp_aar.py` CONFIGS["LowLightDreamLib"] | com.android.systemui:LowLightDreamLib |
| 4 | SettingsLib.aar | 4218366 | 04791c47af946fd8 | `package_aosp_aar.py` CONFIGS["SettingsLib"] | com.android.systemui:SettingsLib |
| 5 | SettingsLibColor.aar | 2033 | 41a8d422ea3e7883 | `package_aosp_aar.py` CONFIGS["SettingsLibColor"] | com.android.settingslib:color（**安装时改名**）|
| 6 | SettingsLibSettingsTheme.aar | 142016 | 0cb09355bd3757a3 | `package_aosp_aar.py` CONFIGS["SettingsLibSettingsTheme"] | com.android.systemui:SettingsLibSettingsTheme |
| 7 | setupcompat.aar | 194066 | 0a4222bf22f81636 | `package_aosp_aar.py` CONFIGS["setupcompat"] | com.android.systemui:setupcompat |
| 8 | WifiTrackerLib.aar | 588337 | d45bbca98feb45f5 | `package_aosp_aar.py` CONFIGS["WifiTrackerLib"] | com.android.systemui:WifiTrackerLib |
| 9 | WindowManager-Shell.aar | 4341027 | 8a5dc18e54b288f3 | `package_aosp_aar.py` CONFIGS["WindowManager-Shell"] | com.android.systemui:WindowManager-Shell |
| 10 | WindowManager-Shell-shared.aar | 222686 | 1633db41becca42 | `package_aosp_aar.py` CONFIGS["WindowManager-Shell-shared"] | com.android.systemui:WindowManager-Shell-shared |

证据：`ls -la libs/aars/*.aar`（见大小列）；`sha256sum libs/aars/*.aar`（见 SHA 列）；
`tools/package_aosp_aar.py` 的 `CONFIGS = {...}` 字典（10 个 key，与上表 1:1）；
`tools/install_aar_to_maven.py` 的 `ARTIFACTS = {...}` 字典（10 个映射，SettingsLibColor
的 groupId 改为 `com.android.settingslib`、name 改为 `color`，其余 9 个 groupId/name 不变）。

### 1.2 `libs/maven/` 本地 Maven AAR 坐标（11 个）

| # | Maven 坐标 | packaging | 与 libs/aars 的 SHA 关系 | POM 是否骨架 |
|---|-----------|-----------|------------------------|-------------|
| 1 | com.android.systemui:animationlib:1.0.0 | aar | == animationlib.aar | 是（无 `<dependencies>`）|
| 2 | com.android.systemui:iconloader:1.0.0 | aar | == iconloader.aar | 是 |
| 3 | com.android.systemui:LowLightDreamLib:1.0.0 | aar | == LowLightDreamLib.aar | 是 |
| 4 | com.android.systemui:SettingsLib:1.0.0 | aar | == SettingsLib.aar | 是 |
| 5 | com.android.settingslib:color:1.0.0 | aar | == SettingsLibColor.aar（改名）| 是 |
| 6 | com.android.systemui:SettingsLibSettingsTheme:1.0.0 | aar | == SettingsLibSettingsTheme.aar | 是 |
| 7 | com.android.systemui:setupcompat:1.0.0 | aar | == setupcompat.aar | 是 |
| 8 | com.android.systemui:WifiTrackerLib:1.0.0 | aar | == WifiTrackerLib.aar | 是 |
| 9 | com.android.systemui:WindowManager-Shell:1.0.0 | aar | == WindowManager-Shell.aar | 是 |
| 10 | com.android.systemui:WindowManager-Shell-shared:1.0.0 | aar | == WindowManager-Shell-shared.aar | 是 |
| 11 | **com.android.systemui:SystemUISharedLib:1.0.0** | aar | **无 libs/aars 源**（SHA `db8be736...`，孤儿）| 是 |

证据：`find libs/maven/ -name "*.aar" -exec sha256sum {} \;`（10 个与 §1.1 逐一匹配 +
SystemUISharedLib 独立 SHA）；全部 11 个 POM 经 `cat` 检查均为 `groupId/artifactId/version/
packaging=aar` 四字段骨架，**无 `<dependencies>` 节**（印证 CHARTER Part 3 "POMs in
libs/maven/ are dependency-free skeletons"）。SystemUISharedLib 既不在
`package_aosp_aar.py` CONFIGS 也不在 `install_aar_to_maven.py` ARTIFACTS → **无注册来源**。

> 相邻发现（jar，非 AAR）：`libs/maven/` 另有两个 jar 坐标——
> `com.android.systemui.flags:flags:1.0.0` 与 `com.android.server:notification-flags:1.0.0`。
> 见 §5 相邻发现。

## 2. 直接 `files()` AAR 引用清单

**结论：零条。** AGENTS.md §3.2 声称 "build.gradle.kts 中不再直接 files(libs/aars/xxx.aar)"
**经核实为真**。

证据（`grep -rn -E "files\(|fileTree|\.aar" build.gradle.kts */build.gradle.kts`）：
所有 `files(...)` 引用的参数均以 `.jar` 结尾或为变量名，**无任何 `.aar` 路径**，也无
`fileTree` 引用 AAR。代表性的 jar 引用（非 AAR）：

- `build.gradle.kts:21` `file(".../libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar")`（jar，用于 allprojects classpath 排序，见 §5.3）
- `app/build.gradle.kts:141` `compileOnly(files(".../libs/framework.jar"))`
- `SystemUI-core/build.gradle.kts:149-231` 一系列 `compileOnly/implementation(files(".../libs/*.jar"))`（全为 jar）
- 其余模块同模式

因此 **(a) 迁移候选——未走 Maven 的直接 AAR 引用——数量为 0**：当前所有 AAR 消费均经
`libs.versions.toml` catalog alias 走本地 Maven 解析（见 §3）。

## 3. AAR 消费点（catalog alias → 模块:行号:配置）

来自 `grep -rn -E "libs\.(systemui|android-systemui-flags|android-server-notification-flags)" */build.gradle.kts`
+ 对 dotted accessor 的精确复核（`libs.systemui.sharedlib` / `libs.android.systemui.flags` /
`libs.android.server.notification.flags`）。

| Maven 坐标 | catalog alias | 消费模块 : 行号 : 配置 |
|-----------|---------------|----------------------|
| com.android.systemui:SettingsLib | `systemui-settingslib` | SystemUI-core:196 implementation；SystemUI-res:37 api |
| com.android.systemui:SettingsLibSettingsTheme | `systemui-settingslib-theme` | SystemUI-res:40 api |
| com.android.systemui:setupcompat | `systemui-setupcompat` | SystemUI-core:202 implementation |
| com.android.systemui:iconloader | `systemui-iconloader` | SystemUI-core:203 implementation |
| com.android.systemui:WindowManager-Shell | `systemui-wmshell` | SystemUI-animation:50 compileOnly；SystemUI-core:204 implementation；SystemUI-shared:63 compileOnly |
| com.android.systemui:WindowManager-Shell-shared | `systemui-wmshell-shared` | SystemUI-animation:51 compileOnly；SystemUI-core:208 implementation；SystemUI-shared:64 compileOnly |
| com.android.systemui:animationlib | `systemui-animationlib` | SystemUI-animation:54 api；SystemUI-compose:60 implementation；SystemUI-customization:63 api |
| com.android.systemui:LowLightDreamLib | `systemui-lowlight-dream-lib` | SystemUI-core:211 implementation |
| com.android.systemui:WifiTrackerLib | `systemui-wifitrackerlib` | SystemUI-core:227 implementation |
| com.android.settingslib:color | `systemui-settingslib-color` | SystemUI-core:231 implementation |
| **com.android.systemui:SystemUISharedLib** | `systemui-sharedlib`（catalog 第 135 行定义）| **无任何消费者**（dotted accessor `libs.systemui.sharedlib` 在所有 build.gradle.kts 中 0 命中）|

settings.gradle.kts 第 26 行配置本地 Maven 仓库：
`maven { url = uri("${rootProject.projectDir}/libs/maven") }`，与 `google()` / `mavenCentral()`
并列；`repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)` 禁止模块级仓库覆盖。

## 4. 使用性判定（每个被消费 AAR 的实际引用证据）

> 命令：`grep -rln "<package>" SystemUI-*/src`（res-only AAR 用 `SystemUI-*/res SystemUI-*/src`）。
> 每条至少一条证据；置信度标注。

| AAR | 证据（文件数 / 代表文件）| 置信度 |
|-----|----------------------|--------|
| animationlib | 149 文件 import `com.android.app.animation`；例 `SystemUI-animation/src/com/android/systemui/animation/ActivityTransitionAnimator.kt` | 高 |
| WifiTrackerLib | 9 文件 import `com.android.wifitrackerlib`；例 `SystemUI-core/src/com/android/systemui/qs/tiles/HotspotTile.java`、`statusbar/connectivity/AccessPointController.kt` | 高 |
| iconloader | 8 文件 import `com.android.iconloader`/`com.android.launcher3.icons`；AAR classes.jar 实含 59 类于 `com/android/launcher3/icons{,/cache}` + `util`；例 `SystemUI-core/src/com/android/systemui/people/PeopleStoryIconFactory.java` | 高 |
| SettingsLib | 289 文件 import `com.android.settingslib`；AAR classes.jar 780 类全在 `com/android/settingslib/` | 高 |
| WindowManager-Shell | 75 文件 import `com.android.wm.shell`（与 shared 共享包根，见下）| 高 |
| WindowManager-Shell-shared | 11 文件引用 shared 专属类 `PhysicsAnimator`/`ShellTransitions`/`TransitionUtil`；例 `SystemUI-animation/.../ActivityTransitionAnimator.kt`、`SystemUI-core/.../SwipeHelper.java` | 高 |
| LowLightDreamLib | 4 文件引用 `TruncatedInterpolator`/`com.android.dream.lowlight`；例 `SystemUI-core/src/com/android/systemui/dreams/DreamOverlayAnimationsController.kt` | 高 |
| setupcompat | 3 文件引用 `com.google.android.setupcompat`/`WizardManagerHelper`；例 `SystemUI-core/src/com/android/systemui/screenshot/ScreenshotController.kt`、`clipboardoverlay/ClipboardListener.java` | 高 |
| SettingsLibColor | 1 文件引用 `com.android.settingslib.color`：`SystemUI-core/src/com/android/systemui/biometrics/ui/viewmodel/SideFpsOverlayViewModel.kt`（与 `package_aosp_aar.py` 注释一致）| 高 |
| SettingsLibSettingsTheme | 17 个 res 文件引用 `settingslib_switch`（如 `SystemUI-res/res/values/styles.xml`、`layout/internet_connectivity_dialog.xml`）——即 AGENTS.md §4.2 记录的当前 `processDebugResources` 阻塞点所依赖的 `settingslib_switch_{track,thumb}` 来源 | 高 |

**结论**：10 个被消费 AAR 全部有 ≥1 条实际引用证据，**无 delete-candidate 因"无引用"**。
唯一"无消费者"的 AAR 是 SystemUISharedLib（见 §5.1）。

## 5. 冗余 / 重叠 / 孤儿判定

### 5.1 SystemUISharedLib（maven 孤儿，delete-candidate，高置信度）

- **无源 AAR**：`libs/aars/` 下无 `SystemUISharedLib.aar`；`package_aosp_aar.py` CONFIGS 与
  `install_aar_to_maven.py` ARTIFACTS 均不含它 → 手工安装的遗留产物。
- **无消费者**：catalog alias `systemui-sharedlib`（`gradle/libs.versions.toml:135`）在所有
  build.gradle.kts 中 dotted accessor `libs.systemui.sharedlib` 0 命中；源码/manifest/res 也
  0 命中（`grep -rn "SystemUISharedLib\|systemui\.sharedlib" SystemUI-*/src SystemUI-*/res* SystemUI-*/AndroidManifest.xml app/src` 空）。
- **AGENTS.md §3.2 明标 "[旧] 遗留，待清理"**。
- **是 fat jar**：classes.jar 1105 文件，顶层包含 `com/android/{app,keyguard,systemui,wm}` +
  `com/google/android/`；与既有 AAR **类重叠**：含 `com/android/wm/shell` 177 条、
  `com/android/app/animation` 5 条 → 与 WindowManager-Shell AAR、animationlib AAR 重复。
- **规则 S 语义**：SystemUI 自有代码（shared/keyguard）已源码化为 `:SystemUI-shared` 模块，
  该 prebuilt AAR 在源码化后即冗余。
- **风险提示（需用户批准后验证）**：因禁止运行 Gradle，无法 100% 排除某 class 仅存于此 AAR
  而未被源码模块覆盖；删除前应跑一次 `:app:assembleDebug` 验证。回滚成本低（git-tracked，
  `git rm -r libs/maven/com/android/systemui/SystemUISharedLib/` + 删 catalog alias）。

### 5.2 `com.android.systemui.flags:flags`（maven jar 孤儿，相邻发现，delete-candidate）

- catalog alias `android-systemui-flags`（`gradle/libs.versions.toml`）dotted accessor
  `libs.android.systemui.flags` 在所有 build.gradle.kts 中 **0 命中** → 无 Maven 消费者。
- `libs/maven/com/android/systemui/flags/flags/1.0.0/flags-1.0.0.jar` 与顶层
  `libs/systemui-flags.jar` **SHA-256 完全相同**
  （`3644731e5e8071317526a79f6ccbe83f687cfc151886a28c53c618b8814ea23f`）→ **内容重复**。
- 实际消费走顶层 jar：`SystemUI-core/build.gradle.kts:169` 与
  `SystemUI-animation/build.gradle.kts:56` 均 `compileOnly(files(".../libs/systemui-flags.jar"))`。
- 建议：删 `libs/maven/com/android/systemui/flags/` + 删 catalog alias `android-systemui-flags`；
  或反之统一改走 Maven（择一，需用户决策——属版本矩阵/依赖策略，CHARTER Part 5 红线 #4）。
- **注**：此为 jar 非 AAR，按 brief Non-goals 仅作相邻记录，不纳入主结论表。

### 5.3 `com.android.server:notification-flags`（jar，非孤儿，保留）

- catalog alias `android-server-notification-flags` **有消费者**：
  `SystemUI-core/build.gradle.kts:193` `implementation(libs.android.server.notification.flags)`。
- 同时 `build.gradle.kts:21` 以**直接 file 路径**引用同一 jar（`val serverNotificationFlagsJar =
  file(".../notification-flags-1.0.0.jar")`）注入 allprojects JavaCompile classpath 前部，
  注释明示是为保证 classpath 顺序（"否则 framework.jar 同名 stub 会遮蔽它"，AGENTS.md §2.4）。
- 双重引用（catalog + 直路径）是**有意的顺序控制机制**，非 Maven 绕过；保留。属 jar，相邻记录。

### 5.4 WM-Shell 主 vs shared 类集交集 = 0（验证 AGENTS.md §4.2 主张）

`comm -12 <(WM-Shell classes.class) <(shared classes.class)`（LC_ALL=C sort）= **0 重叠**。
AGENTS.md §4.2 "主/shared class-set 交集为 0，:app:checkDebugDuplicateClasses 通过" **经核实为真**。
`package_aosp_aar.py` 的 `exclude_prefixes`（WM-Shell 排除 `com/android/wm/shell/shared/I{Focus,Home}...` +
`IShellTransitions`）生效。

### 5.5 SettingsLib-full.jar 与 SettingsLib AAR 类集交集 = 0（非重叠，互补）

`comm -12 <(SettingsLib-full.jar) <(SettingsLib AAR classes.jar)` = **0 重叠**。
`SystemUI-core/build.gradle.kts:198` 注释 "含 SettingsLib 子模块类（与 AAR javac 0 重叠）"
**经核实为真**。两者同包 `com/android/settingslib` 但类集互补（full.jar 372 类 vs AAR 780 类，
0 交集；推测 turbine-stub vs javac-impl 之别）。**非删除候选**。属 jar，相邻记录。

### 5.6 WindowManager-Shell AAR 含 `com/android/internal/`（2 类，轻微泄漏）

WM-Shell AAR classes.jar 顶层包为 `com/android/internal/` + `com/android/wm/`；
`com/android/internal/` 仅 2 条 entry，属 framework 内部类轻微泄漏（`reject_sysui` 只拒
`com/android/systemui/`，未拒 `com/android/internal/`）。非重叠、非删除依据；记录备查。

### 5.7 工具链在役/废弃判定

| 工具 | 状态 | 证据 |
|------|------|------|
| `tools/package_aosp_aar.py` | **在役**（canonical AAR 打包器）| CONFIGS 10 个 key 与 §1.1 全量 1:1；AGENTS.md §3.2 指定为 AAR 生成器 |
| `tools/install_aar_to_maven.py` | **在役**（Maven 安装器）| ARTIFACTS 10 个映射与 §1.2 全量 1:1（除 SystemUISharedLib）；AGENTS.md §3.2 指定 |
| `tools/gen_aar_maven.py` | **废弃**（delete-candidate）| 文件头自警 "失败实验，暂勿运行"；AGENTS.md §1.4 "旧脚本，R.jar 合并失败实验，已废弃"；仅处理 4 个 artifact 且用已被取代的 R.jar 合并逻辑 |
| `tools/rebuild_settingslib_aar.py` | **废弃/被取代**（delete-candidate）| 2026-07-30 一次性补丁；硬编码 `PROJECT_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")`（非 worktree 路径，worktree 下会错路径）；其"从 AOSP 源 res 重补 SettingsLib"功能已被 `package_aosp_aar.py` CONFIGS["SettingsLib"]（`res: [AOSP_ROOT/.../SettingsLib/res]`）覆盖；且当前 §4 已知 SettingsLib 缺的是 SettingsTheme/res/drawable-v31/ 的 switch drawable，本脚本从 SettingsLib/res 补，**不解决**当前阻塞点 |
| `tools/clean_aar_maven.py` | 相邻：清理 gen_aar_maven.py 产物的冲突类；随 gen_aar_maven.py 废弃而失去用途，建议同废（需用户确认）|

## 6. 结论表（keep / migrate-to-Maven / delete-candidate）

| # | 对象 | 判定 | 证据摘要 | 回滚方式 |
|---|------|------|----------|----------|
| 1 | animationlib.aar / com.android.systemui:animationlib | **keep** | 149 文件引用；3 消费模块（animation/compose/customization）| — |
| 2 | iconloader.aar / com.android.systemui:iconloader | **keep** | 8 文件引用；1 消费模块（core）| — |
| 3 | LowLightDreamLib.aar / com.android.systemui:LowLightDreamLib | **keep** | 4 文件引用 TruncatedInterpolator；1 消费模块（core）| — |
| 4 | SettingsLib.aar / com.android.systemui:SettingsLib | **keep** | 289 文件引用；2 消费模块（core/res）；当前 processDebugResources 阻塞点依赖其 res | — |
| 5 | SettingsLibColor.aar / com.android.settingslib:color | **keep** | 1 文件引用（SideFpsOverlayViewModel.kt）；1 消费模块（core）| — |
| 6 | SettingsLibSettingsTheme.aar / com.android.systemui:SettingsLibSettingsTheme | **keep** | 17 res 引用 settingslib_switch；1 消费模块（res）；当前阻塞点正缺其 drawable-v31（AGENTS.md §4.2）| — |
| 7 | setupcompat.aar / com.android.systemui:setupcompat | **keep** | 3 文件引用 WizardManagerHelper；1 消费模块（core）| — |
| 8 | WifiTrackerLib.aar / com.android.systemui:WifiTrackerLib | **keep** | 9 文件引用；1 消费模块（core）| — |
| 9 | WindowManager-Shell.aar / com.android.systemui:WindowManager-Shell | **keep** | 75 文件引用 com.android.wm.shell；3 消费模块（animation/core/shared）| — |
| 10 | WindowManager-Shell-shared.aar / com.android.systemui:WindowManager-Shell-shared | **keep** | 11 文件引用 PhysicsAnimator/ShellTransitions；与主 AAR 0 类重叠；3 消费模块 | — |
| 11 | **com.android.systemui:SystemUISharedLib** | **delete-candidate** | 无源 AAR、无消费、AGENTS.md 标"待清理"、fat jar 与 WM-Shell/animationlib 类重叠、规则 S 下已被 :SystemUI-shared 源码取代 | `git rm -r libs/maven/com/android/systemui/SystemUISharedLib/` + 删 `gradle/libs.versions.toml:135` alias；删前跑 `:app:assembleDebug` 验证无遗漏类 |
| 12 | **com.android.systemui.flags:flags**（jar，相邻）| **delete-candidate**（或统一改 Maven，需用户决策）| catalog alias 无消费者；与 `libs/systemui-flags.jar` SHA 完全相同（重复）；实际消费走顶层 jar | `git rm -r libs/maven/com/android/systemui/flags/` + 删 alias；或反之删顶层 jar 改 Maven（红线 #4 版本矩阵，需用户拍板）|
| 13 | `tools/gen_aar_maven.py` | **delete-candidate**（废弃脚本）| 自警"失败实验"；AGENTS.md §1.4 标废弃；被 package_aosp_aar.py + install_aar_to_maven.py 取代 | `git rm tools/gen_aar_maven.py` |
| 14 | `tools/rebuild_settingslib_aar.py` | **delete-candidate**（废弃脚本）| 一次性补丁、硬编码非 worktree 路径、功能被 CONFIGS["SettingsLib"] 覆盖、不解决当前阻塞 | `git rm tools/rebuild_settingslib_aar.py` |
| 15 | `tools/clean_aar_maven.py` | delete-candidate（建议，需用户确认）| 仅服务 gen_aar_maven.py 产物；随其废弃而失用途 | `git rm tools/clean_aar_maven.py` |

**迁移候选（(a) 类）数量：0**——无任何直接 `files("*.aar")` 绕过 Maven 的引用，全部 AAR 已走
catalog + 本地 Maven。AGENTS.md §3.2 主张核实为真。

**删除候选（(b) 类）汇总**（按风险从低到高排序）：
1. （最低风险）`tools/gen_aar_maven.py`、`tools/rebuild_settingslib_aar.py`（废弃脚本，无消费链路）；
2. `com.android.systemui:SystemUISharedLib`（maven 孤儿 AAR，无消费、有重叠、规则 S 已取代——但删前需构建验证）；
3. `com.android.systemui.flags:flags`（重复 jar，与顶层 jar SHA 相同——但涉"删 maven 还是删顶层 jar"产品决策，红线 #4）。

## 7. 待用户决策项（CHARTER Part 5 红线，需 architect 转呈）

1. 是否批准删除 SystemUISharedLib（含删前构建验证方案）。
2. `com.android.systemui.flags:flags` 重复 jar：删 maven 坐标 + alias，还是删顶层 `libs/systemui-flags.jar` 改走 Maven？（涉版本矩阵红线 #4 + 依赖策略）
3. 废弃脚本 `gen_aar_maven.py` / `rebuild_settingslib_aar.py` / `clean_aar_maven.py` 是否删除？
4. SettingsLib AAR 当前缺 `SettingsLib/SettingsTheme/res/drawable-v31/settingslib_switch_{track,thumb}`
   （AGENTS.md §4.2 已记录）——与本次审查正交，但确认 SettingsLibSettingsTheme AAR（#6 keep）
   是这些 drawable 的正确归属，待 Task 015 / 重新打包时补齐。

## 8. 审查约束遵守

- 未删除/修改任何 AAR、POM、构建脚本、catalog、源码、资源（只读审查）；
- 未运行任何 `./gradlew` 命令（用户 + brief 明令禁止）；
- 仅写入 3 个 Allowed Path 文件：本文件、`docs/issues/2026-08-19-aar-dependency-audit.md`、
  `docs/orchestration/tasks/017-aar-dependency-audit.md`（checklist 勾选）；
- 临时解包目录均置于 `/tmp/audit_*`，未污染仓库。
