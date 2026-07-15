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