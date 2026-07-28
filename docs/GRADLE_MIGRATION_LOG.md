# SystemUI Gradle 迁移工作记录

> 参考 [CarSystemUIGradle/docs/GRADLE_MIGRATION.md](../CarSystemUIGradle/docs/GRADLE_MIGRATION.md)
> 的格式与编号体系。本项目从问题一开始。

---

## 问题一：废弃 v1 离线策略，切换到 v2 设计

### 问题描述
v1 阶段（2026-04 ~ 2026-07-15）按"完全离线 + 拷贝 AOSP 源码 + 本地 stubs"
实施，残留 898 个 Kotlin 编译错误且与用户最终确定的 v2 策略矛盾。
详见 `docs/superpowers/specs/2026-07-16-systemui-gradle-conversion-v2-design.md`。

### 问题分析
- `libs/` (693MB) 与 `scripts/{build_offline_maven.py,extract_aosp_libs.sh}` 是 v1
  离线 Maven 仓库体系的产物。
- `animation/ common/ customization/ log/ plugin/ plugin-core/ shared/ unfold/ utils/`
  9 个 module 目录的 `build.gradle.kts` 与 `sourceSets` 是按 v1 思路拼凑的。
- 根目录 `build.gradle.kts / settings.gradle.kts / gradle.properties` 要按
  AGP 9 + Gradle 9 全部重写。

### 解决方案
```bash
rm -rf animation common customization log plugin plugin-core shared unfold \
       utils libs scripts build
rm -f build.gradle.kts settings.gradle.kts gradle.properties
rm -f docs/superpowers/specs/2026-04-30-systemui-gradle-conversion-design.md
rm -f docs/superpowers/plans/2026-04-30-systemui-gradle-conversion.md
```

### 修改文件
- 删除 9 个 module 目录
- `libs/` `scripts/` `build/` 目录
- `build.gradle.kts` `settings.gradle.kts` `gradle.properties`
- v1 spec / plan 文档
- 保留：`app/`（包含 AOSP 拷贝源码、`res-keyguard/` 资源）

---

## 问题二：误读清理范围导致 app/ 未删

### 问题描述
问题一的清理 commit (`6fd8846`) 错误地保留了 `app/`。原因：澄清问卷里
`c1-keep-all` 的 label 与 id 含义相反（label 是"全删"，id 暗示"保留全部"），
agent 误读为"保留 app/"，用户实际意图是"连 app/ 一起全删"。

### 问题分析
`app/` 仍含 v1 阶段 6,487 文件 / 65MB 的 AOSP 拷贝源码 + `app/build/`
中间产物 + untracked 的 `app/src/main/res-keyguard/`。v2 设计要求把
`app/` 当成从零开始的容器，先跑通空系统再按模块迭代。

### 解决方案
`rm -rf app/`，由后续 v2 骨架任务按需重新拷贝。

### 修改文件
- `app/`（整目录）

---

## 问题三：v1 骨架交付

### 问题描述
v2 spec §9 要求交付双编译骨架；本任务执行 §9 全部步骤。执行中暴露两个
配置层问题：

1. 现有 `.gitignore` 第 84 行 `libs/` 与 v2 spec §7 "libraries committed"
   矛盾——会让 framework.jar 和 4 个 prebuilt JAR 被忽略。
2. plan 里 `build.gradle.kts` 的 `emptySet()` 不能让 Kotlin 类型推导，
   需显式 `emptySet<File>()`。

### 问题分析
1. v1 离线策略阶段把 `libs/` 当成"全部第三方依赖临时缓存"，需要忽略；
   v2 改为"自包含 + commit 到仓库"，需要保留 jar/aar 但忽略 maven 子树
   （参考项目也用 `libs/maven/`）。
2. plan 写成 verbatim 参考项目 CarSystemUIGradle 的写法，而该项目用的是
   `JavaCompile` 在 Groovy build.gradle 里能隐式推断；切到 Kotlin DSL
   后必须给 `emptySet()` 提供类型参数。

### 解决方案
1. `.gitignore` 末尾改为：
   ```
   !libs/
   libs/maven/
   !libs/**/*.jar
   !libs/**/*.aar
   ```
2. `build.gradle.kts` 第 15 行 `emptySet()` → `emptySet<File>()`。

### 修改文件
- `.gitignore`
- `build.gradle.kts`

（详细模块拆分见 `docs/superpowers/plans/2026-07-16-systemui-v2-dual-build-skeleton.md`。）

---

## 问题四：Task 1 需要占位目录

### 问题描述
`settings.gradle.kts` 写了 7 个 `include(":...")`，但执行 Task 1 时
7 个 module 目录都还不存在，`./gradlew help` 直接失败。

### 问题分析
plan 的 Step 6 预料到了这个失败，但明确"Task 1 still DONE"。这是
不完全忠实于 §6 "expected: PASS" 的描述。把目录创建挪到 Task 1
内部才合理。

### 解决方案
Task 1 创建 7 个空目录 + 每个一个 `.gitkeep`，让 `./gradlew help`
和 `./gradlew projects` 都 PASS。

### 修改文件
- 7 个 module 目录（每个含 `.gitkeep`）

---

## 问题五：AOSP JAR 产物命名与 plan 不符

### 问题描述
plan Task 5/6 假设 AOSP 产物 jar 名为：
`SystemUI-{shared,animation,customization,plugin}.jar`，
实际 AOSP 编译产物为：

| Plan 假设 | 实际 AOSP 路径 |
|-----------|--------------|
| `SystemUI-shared.jar` | `SystemUISharedLib.jar` |
| `SystemUI-animation.jar` | `PlatformAnimationLib.jar` |
| `SystemUI-customization.jar` | `SystemUICustomizationLib.jar` |
| `SystemUI-plugin.jar` | `SystemUIPluginLib.jar` |

### 问题分析
plan 复制了 CarSystemUIGradle 的命名，但 CarSystemUIGradle 是 JD 定制版，
AOSP 原版命名是 `{ModuleName}Lib.jar`。必须用实际 AOSP 名称，
否则 `compileOnly(files("libs/prebuilts/SystemUI-*.jar"))` 会指向不存在的文件。

### 解决方案
`tools/extract_prebuilts.sh` 和 Task 6 的 `compileOnly` 路径都改用实际名称：

```bash
# extract_prebuilts.sh 用 copy_jar("SystemUISharedLib") 等
# build.gradle.kts 用 compileOnly(files("libs/prebuilts/SystemUISharedLib.jar")) 等
```

### 修改文件
- `tools/extract_prebuilts.sh`（Task 5 实现时）
- 4 个 `SystemUI-*/build.gradle.kts` 的 `compileOnly` 路径

---

## 问题六：prebuilt-jar module 相对路径错误

### 问题描述
4 个 prebuilt-jar module 的 `compileOnly(files("libs/prebuilts/X.jar"))`
用了 module 内相对路径，AGP 从 module 目录解析，找不到文件：

```
File/directory does not exist: /home/conv/myspace/SystemUI-Gradle/SystemUI-plugin/libs/prebuilts/...
```

### 问题分析
相对路径 `libs/` 从每个 module 的 `${moduleDir}/libs/` 开始找，
而不是从根项目 `${project.rootDir}/libs/` 开始。

### 解决方案
改用 `${rootProject.projectDir}/libs/prebuilts/X.jar`。

### 修改文件
- `SystemUI-shared/build.gradle.kts`
- `SystemUI-animation/build.gradle.kts`
- `SystemUI-customization/build.gradle.kts`
- `SystemUI-plugin/build.gradle.kts`

---

## 问题七：v1 骨架交付（问题三补完）

### 问题描述
v2 spec §9 deliverable 已完成：所有 9 个 Task 执行完毕，骨架交付。

### 完成情况
| Task | 文件 | 状态 |
|------|------|------|
| 1 | root Gradle config + 7 placeholder dirs | ✅ `0632789` |
| 2 | framework.jar 提取 | ✅ `2704f80` |
| 3+4 | :SystemUI-core, :SystemUI-plugin-core | ✅ `5f87314` |
| 5+6 | 4 prebuilt JARs + extract script + 4 library modules | ✅ `e1a2710` |
| 7 | :app skeleton (SystemUIService stub + APK 12MB) | ✅ `d158fa8` |
| 8 | Android.bp + CleanSpec.mk | ✅ `5d0f7a9` |
| 9 | 本条目 + 末尾 push | ✅ |

### 制品汇总
| 文件 | 说明 |
|------|------|
| `libs/framework.jar` | 19MB AOSP framework stub |
| `libs/prebuilts/*.jar` | 58MB AOSP 模块 jar (4个) |
| `app/build/outputs/apk/debug/app-debug.apk` | 12MB stub APK (com.android.systemui) |
| `Android.bp` | AOSP 双编译入口 |
| `tools/extract_prebuilts.sh` | JAR 提取脚本 |

### 未解决问题（后续 Task）
- 真实 `SystemUIService` / Dagger graph 移植
- `tools/sync_aosp_sources.sh`（按需从 aosp/ 拷贝源码）

---

## 问题八：平台签名 keystore 集成

### 问题描述
v1 骨架 Task 7 暂用 AGP debug key，但 spec §11.7 风险 #10 要求最终用
AOSP platform key 签名。AGP 9.2 的 `signingConfig.storeFile` 需要 JKS/PKCS12
格式，但 AOSP 提供的是 `pk8 + x509.pem` 组合。

### 问题分析
AOSP README 已经给出标准 recipe：
1. `openssl pkcs8 -inform DER -nocrypt -in platform.pk8 -out platform.pem`
2. `openssl pkcs12 -export -in x509.pem -inkey platform.pem -out platform.p12
   -password pass:android -name AndroidDebugKey`
3. `keytool -importkeystore -deststorepass android
   -destkeystore platform.keystore -srckeystore platform.p12
   -srcstoretype PKCS12 -srcstorepass android`

把它做成 `tools/install_keystore.sh` 脚本。AGP 用 `storePassword=android`,
`keyAlias=androiddebugkey`, `keyPassword=android`（小写 alias 因为
keytool 把 alias 转小写）。

### 解决方案
1. 写 `tools/install_keystore.sh`（幂等），运行后产出 `keystore/platform.keystore` (3.1K)。
2. `app/build.gradle.kts` 加 `signingConfigs.release` + `buildTypes.debug`
   引用它。
3. `Android.bp` 已有 `certificate: "platform"`（无需改）。

### 修改文件
- `tools/install_keystore.sh`（新增）
- `app/build.gradle.kts`（加 signingConfig + buildTypes.debug）
- `keystore/platform.keystore`（新增二进制，3.1KB）

### 制品来源
| 文件 | 来源 | 说明 |
|------|------|------|
| `keystore/platform.keystore` | `aosp/build/target/product/security/platform.{pk8,x509.pem}` 经 openssl + keytool 转换 | 平台签名 JKS |
| `Android.bp` `certificate: "platform"` | AOSP 命名约定 | Soong build 时用同名 key |

### 验证
- `apksigner verify --print-certs` 显示 DN：
  `EMAILADDRESS=android@android.com, CN=Android, ...`
- SHA-256: `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`

---

## 问题九：Port SystemUIService plan 编写

### 问题描述
用户要求"Port 真实 SystemUIService：从 AOSP 拷源码 + Dagger graph"。
但 AOSP `src/` 共 4183 文件，SystemUIService 本身 140 LoC 但依赖几百个
`@Inject` 绑定。直接全量拷贝不现实。

### 问题分析
Probe 结果：
- Dagger 根文件 24 个，可控
- `SystemUIApplication` 501 LoC 含 `WMComponent` 注入，依赖 WMShell
- `WindowManager-Shell.jar` 已存在于 AOSP out（498 文件源，但我们用 prebuilt）
- `Dependency.java` 是 legacy static bridge（~2500 LoC），全量重构波及整个 SystemUI

### 解决方案
写 `docs/superpowers/plans/2026-07-16-port-systemui-service.md`
（6 个 milestone 设计文档），不直接 port。每个 milestone 末尾
`./gradlew :app:assembleDebug` 必须绿，向用户提出 4 个 open questions
决定后续执行。

### 修改文件
- `docs/superpowers/plans/2026-07-16-port-systemui-service.md`（新增 158 行）

---

## 问题十：M1 WindowManager-Shell prebuilt

### 问题描述
Port 计划 M1：把 AOSP `WindowManager-Shell.jar` 引入 build，作为
`com.android.wm.shell.*` 包来源。

### 问题分析
- AOSP `frameworks/base/libs/WindowManager/Shell/` 有 498 java/kt 源
- out/ 已 compile 出 `WindowManager-Shell.jar` (turbine-combined)
- 路径：`aosp/out/soong/.intermediates/frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/turbine-combined/`
- **关键发现**：该 jar **41MB / 20155 class**，参考项目 CarSystemUIGradle
  用的 8.7MB jar 是 AOSP 较旧版本人工精简产物（4924 class），我们不裁剪。
- 集成方式按参考项目：`compileOnly(files(...))` 直接放进 `app/build.gradle.kts`，
  不做独立 `:SystemUI-wm-shell` module（避免重复 manifest / R class）。
- AOSP 同名 `SystemUIInitializer` / `SystemUIService` 都 import
  `com.android.wm.shell.dagger.WMComponent` — 引入是后续 M2-M4 的前置。

### 解决方案
1. `cp` AOSP `WindowManager-Shell.jar` (41MB) 到 `libs/WindowManager-Shell.jar`。
2. `app/build.gradle.kts` 加 `compileOnly(files(...WindowManager-Shell.jar))`。
3. `Android.bp` 加 `java_import` + `static_libs`。

### 修改文件
- `libs/WindowManager-Shell.jar` (41MB 二进制)
- `app/build.gradle.kts` (compileOnly line)
- `Android.bp` (java_import + static_libs)

### 验证
临时 `WMShellSmoke.java` 包含 `import com.android.wm.shell.dagger.WMComponent`
+ `import com.android.wm.shell.sysui.ShellInterface` → `:app:compileDebugJavaWithJavac`
BUILD SUCCESSFUL。临时文件已删除。

### Plan 修订
M1 描述已根据参考项目发现更新（不再做独立 module，直接 `compileOnly`）。
Q2 (Dagger codegen) 答案 = kapt，按参考项目 `kotlin-kapt` 插件 + `kapt(libs.dagger.compiler)`。
---

## 问题十一：错误数演变（2026-07-22 ~ 2026-07-28）

### 错误数时间线

| 日期 | 错误数 | Δ | 改动 |
|------|--------|---|------|
| 2026-07-22 初 | 5296 | — | 仅 sdk android.jar |
| 2026-07-22 | 4675 | -621 | 替换 framework.jar (AOSP 完整版) |
| 2026-07-22 | 3008 | -1667 | 合并 SDK android.jar + framework.jar |
| 2026-07-22 | 2412 | -596 | 删除所有 v1 stub (~60 个) |
| 2026-07-22 | 2000 | -412 | 加 Monet + SystemUI Flags jar |
| 2026-07-23 | 2000 | 0 | 启动 Stage 2 (server-notification-flags) |
| 2026-07-28 | 2000 | 0 | Stage 2 调试 session，未突破 |

### 趋势

- **2026-07-22 一日减少 3296 个错误**（最大单日降幅）
- **2026-07-23 起进入平台期** (2000 难以下降)
- 主要阻塞: server-notification-flags.jar + KAPT 禁用 + Compose 内部 API

---

## 问题十二：Stage 2-3 文档化 (2026-07-28)

### 问题描述
用户要求把所有"当前正在做的、需要做的、长期做的、遇到的问题、原则"记录到多个文档，
让下一个 AI Agent 拿上就能上手。

### 解决方案

创建/更新以下文档：

1. `docs/HANDOFF.md` (新) - 5 分钟上手纲要
2. `AGENTS.md` (重写) - 完整规则 + 现状
3. `docs/CURRENT_STATE.md` (新) - 状态快照
4. `docs/PITFALLS.md` (新) - 踩坑记录
5. `docs/issues/2026-07-28-server-flags-debug-session.md` (新) - 本次实验
6. `docs/architecture/STAGE2-3-RESEARCH-LOG.md` (新) - 深度调研
7. `docs/PLAN.md` (更新) - 阶段计划
8. `docs/GRADLE_MIGRATION_LOG.md` (本条目) - 历史演变

### 下个 AI 必读顺序

```
docs/HANDOFF.md → AGENTS.md → docs/CURRENT_STATE.md → docs/PLAN.md →
docs/PITFALLS.md → docs/architecture/STAGE2-3-RESEARCH-LOG.md →
docs/issues/2026-07-28-server-flags-debug-session.md →
docs/GRADLE_MIGRATION_LOG.md
```

---

## 问题十三：Stage 2 根因定位 —— stub 源码遮蔽 jar (2026-07-28)

### 问题描述
`com.android.server.notification.Flags` 的 `screenshareNotificationHiding` 等
19 个 `Unresolved reference`，卡了 2026-07-23 ~ 2026-07-28 多轮排查未解。

### 根因（与此前所有推测相反）
源码 `SystemUI-core/src/com/android/server/notification/Flags.kt` 是一个 `object Flags` **stub**，
全项目编译时 Kotlin 优先用它而非 jar。stub 缺 `screenshareNotificationHiding()`，
并把 `politeNotifications` 等写成 `val` 而非方法 → 13 + 6 个错误。

此前围绕 classpath 注入 / Kotlin 2.2.10 / 缺 FeatureFlags 的排查全部走偏。
决定性实验：孤立 K2JVMCompiler 用**完整 128 项 AGP classpath** 编译最小复现文件 → 成功，
证明 classpath 与编译器都无罪，问题只可能在源码集。

### 解决方案
`git rm SystemUI-core/src/com/android/server/notification/Flags.kt`。

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| 修复前 | 2000 |
| 删除 stub | **1979** |

详见 `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md` 与 `docs/PITFALLS.md §2.4`。

---

## 2026-07-28 — Stage 3 (部分): 消除全项目 R import 歧义

### 现象
7 个文件同时 import 两个名为 `R` 的类 → `imported name 'R' is ambiguous`，
并级联使文件内所有 `R.xxx` 报 unresolved。

### 解决方案
每个文件删除多余的 `import com.android.systemui.R`，对齐 AOSP 原文件的单一 R import
（保留 `internal.R` / `wm.shell.R` / `android.R` / `settingslib.R`）。

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| Stage 2 后 | 1979 |
| 修 AndroidColorScheme.kt | 1953 |
| 修 PlatformTheme.kt | 1923 |
| 修其余 5 个文件（R 歧义清零） | **1879** |

详见 `docs/issues/2026-07-28-r-import-ambiguity.md` 与 `docs/PITFALLS.md §3.2`。

---

## 2026-07-28 — 补齐 androidx.datastore 依赖

### 现象
多个文件 `import androidx.datastore.preferences.core.*` / `androidx.datastore.core.DataStore`
报 `Unresolved reference 'Preferences' / 'longPreferencesKey' / 'preferences'` 等，级联影响使用处。

### 根因
AOSP SystemUI `Android.bp` 依赖 `androidx.datastore_datastore-preferences`，
但 Gradle 迁移时未声明该依赖。

### 解决方案
`SystemUI-core/build.gradle.kts` 添加（google() 仓库已配置，直接 maven 引入）：
```
implementation("androidx.datastore:datastore-preferences:1.1.1")
implementation("androidx.datastore:datastore-core:1.1.1")
```

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| 修复前 | 1879 |
| 加 datastore 依赖 | **1806** |

无新增错误类型（LC_ALL=C 对比 unresolved 符号集，新增为空）。

---

## 2026-07-28 — Stage 4 (部分): customization res + transitive R

### 现象
`com.android.systemui.R.dimen.large_clock_text_size` / `R.id.lockscreen_clock_view` 等
时钟/customization 资源引用 unresolved。

### 根因
(1) `:SystemUI-customization` 模块没有 res 目录；
(2) `android.nonTransitiveRClass=true` 使依赖资源不合并进 `com.android.systemui.R`
（AOSP 靠 static-lib 传递合并，源码统一写 `com.android.systemui.R`）。

### 解决方案
- 从 AOSP 复制 `customization/res` → `SystemUI-customization/res` + `res.srcDir("res")`。
- `gradle.properties`: `android.nonTransitiveRClass=false`（对齐 AOSP 传递合并）。

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| 修复前 | 1806 |
| 仅复制 res (nonTransitive=true) | 1806（无效）|
| 关闭 nonTransitiveRClass | **1759** |

无新增错误类型。smartspace ids（在 shared/res）未解决：core 用 prebuilt SharedLib.jar
依赖 shared 而非 project，给 shared 加 res 无效（已回退）。详见
`docs/issues/2026-07-28-transitive-r-customization-res.md`。

---

## 2026-07-28 — 引入 SystemUI AIDL 生成接口 jar

### 现象
`IGlanceableHubWidgetManagerService` / `IHomeControlsRemoteProxy` / `IScreenshotProxy` 等
AIDL 接口 unresolved，级联 `clearCallingIdentity` / `restoreCallingIdentity`。

### 根因
14 个 `.aidl` 与源码同放 `src/`，但 AGP 8+ 默认关闭 aidl 编译；开启后又因
`SysUISdk/framework.aidl` 缺 hidden 接口（`android.os.IRemoteCallback` 等）而失败。

### 解决方案（AGENTS §1：从 AOSP 编译产物提取 jar）
从 `aosp/out/.../SystemUI_intermediates/classes.jar` 提取 11 个 `I*Service`
接口 + 嵌套类打包为 `libs/systemui-aidl.jar`，`compileOnly` 引入。

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| 修复前 | 1759 |
| 引入 systemui-aidl.jar | **1658** |

无新增错误类型。残留 9 个为嵌套回调接口的 nullability mismatch（非 unresolved）。
详见 `docs/issues/2026-07-28-systemui-aidl-jar.md`。

---

## 2026-07-28 — customization prebuilt jar 改 api 暴露给 core

### 现象
`com.android.systemui.shared.keyguard.shared.model.KeyguardQuickAffordanceSlots` /
`ClockRegistry` 等大量 `com.android.systemui.shared.*` unresolved。

### 根因
类明明在 `SystemUICustomizationLib.jar`（路径匹配 import），但 `:SystemUI-customization`
用 `implementation(files(...))` 引入 —— `implementation` 不向下游 `:SystemUI-core` 暴露。

### 解决方案
`SystemUI-customization/build.gradle.kts`：`implementation(files(...))` → `api(files(...))`。

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| 修复前 | 1658 |
| 改 api | **1491** |

无新增 unresolved 符号类型。详见 `docs/issues/2026-07-28-customization-api-exposure.md`。

---

## 2026-07-28 — 补齐完整 SettingsLib jar

### 现象
`com.android.settingslib.volume.data.repository.AudioRepository` /
`bluetooth.LocalBluetoothLeBroadcast` 等大量 `com.android.settingslib.*` unresolved。

### 根因
我方 `SettingsLib-1.0.0.aar` 只含 res 不含 class。AOSP SettingsLib 混合模块编译产物分
kotlin jar（kotlin 类）+ javac jar（java 类），单独任一都不全。

### 解决方案（AGENTS §1）
补 `libs/SettingsLib-full.jar`（kotlin）+ `libs/SettingsLib-javac.jar`（javac），
`compileOnly` 引入 core，保留原 aar 提供 res。

### 错误数演变
| 时点 | 错误数 |
|------|--------|
| 修复前 | 1491 |
| + kotlin jar | 1150 |
| + javac jar | **1039** |

两步均无新增 unresolved 符号类型。详见 `docs/issues/2026-07-28-settingslib-full-jar.md`。
