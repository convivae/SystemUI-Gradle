# SystemUI-Gradle 项目开发规则 (AGENTS.md)

> 这是本项目的全局指令。所有 AI Agent 在本项目中工作时必须遵守此文件。
> 用户指令优先级最高，本文件次之，最后是默认系统提示。

---

## 一、依赖引入规则 (用户明确要求，2026-07-22)

> **不允许使用 stub 技术**。所有依赖必须是以下三种形式之一：
> 1. **源码复制** 过来作为子项目 (project(":xxx"))
> 2. **jar 包**：`compileOnly(files("libs/xxx.jar"))` / `implementation(files("libs/xxx.jar"))`
> 3. **aar 包**：本地 Maven (`libs/maven/com/...`) 或 `implementation(files("libs/xxx.aar"))`
> 4. **maven**：`implementation("group:artifact:version")` (本地或远程仓库)

### 禁止
- ❌ 不允许创建 *.java stub 类只为让 IDE/编译器满意
- ❌ 不允许私自创建资源文件 (res/ 下的任何 .xml/.png/.9.png 等)
- ❌ 所有资源文件必须来自：AOSP 源码、aar 包、maven 依赖

### 允许
- ✅ 复制 AOSP 源码目录作为 module (例如 `:SystemUI-monet`)
- ✅ 从 AOSP 编译产物提取 *.class 打包为 jar
- ✅ 从 AOSP 编译产物提取 jar/aar 放到 `libs/` 或 `libs/maven/`
- ✅ 复制 AOSP 的 res 目录 (例如 `res-keyguard/`, `res-product/`)
- ✅ 对 res 目录做必要的去重/合并 (AAPT2 不支持 product 属性)

### 参考实现
- `CarSystemUIGradle` 项目 (同用户私有项目) 是参考实现
- 关键文件：`tools/gen_aar_maven.py` (已复制到本项目的 `tools/`)
- 关键资源：参考 `CarSystemUIGradle/SystemUI-core/build.gradle.kts` 的依赖引入方式

---

## 二、本项目开发原则

### 2.1 增量开发，每次提交都要可验证
- 每次 commit 必须: (1) 改动小而聚焦 (2) 编译错误数下降 (3) 记录在文档
- 错误数演变表必须维护 (`docs/GRADLE_MIGRATION_LOG.md`)
- 不要跨大步、一次做太多事

### 2.2 文档先行
- 每个步骤开始前先在 `docs/issues/` 下写文档
- 文档结构：`docs/issues/YYYY-MM-DD-<topic>.md`
- 文档包含：背景、操作步骤、错误数演变、待解决问题

### 2.3 遵循 AOSP 源码结构
- AOSP 路径: `/home/conv/myspace/aosp/`
- AOSP 中间产物: `/home/conv/myspace/aosp/out/soong/.intermediates/`
- AOSP 编译 jar: `/home/conv/myspace/aosp/out/target/common/obj/*/classes.jar`
- 参考 AOSP 的 `Android.bp` 文件了解模块依赖关系

### 2.4 SDK 与 framework.jar 关系
- 我们的 SDK: `compileSdkPreview = "SysUISdk"` (位于 `/home/conv/Android/Sdk/platforms/android-SysUISdk/`)
- AOSP `framework.jar` 提供 SDK 不含的 @hide API 和内部类
- `build.gradle.kts` 通过 `allprojects { ... }` 注入 framework.jar 到所有 Kotlin/Java 编译

---

## 三、项目架构

### 3.1 模块结构
```
:app                          # 主入口，依赖其他所有模块
:SystemUI-core                # 主模块 (~95% 代码)
:SystemUI-shared              # 共享库
:SystemUI-animation           # 动画库
:SystemUI-customization       # 配置库
:SystemUI-plugin              # 插件接口 (运行时)
:SystemUI-plugin-core         # 插件注解 (编译时)
```

### 3.2 libs/ 内容
```
libs/
├── framework.jar                       # AOSP 框架 jar (隐藏 API)
├── framework-statsd.jar
├── android.car.jar                     # Car API
├── WindowManager-Shell.jar
├── android_module_lib_stubs_current.jar
├── SystemUI-proto.jar                  # protobuf
├── SystemUI-tags.jar
├── SystemUI-statsd.jar
├── monet.jar                           # ColorScheme/Shades/Style
├── systemui-flags.jar                  # com.android.systemui.Flags
├── server-notification-flags.jar       # com.android.server.notification.Flags
├── prebuilts/
│   ├── SystemUISharedLib.jar
│   ├── SystemUIPluginLib.jar
│   ├── SystemUICustomizationLib.jar
│   ├── PlatformAnimationLib.jar
│   └── tracinglib-platform.jar
└── maven/                              # 本地 Maven 仓库
    ├── com.android.systemui/
    │   ├── SettingsLib/1.0.0/
    │   ├── iconloader/1.0.0/
    │   ├── WindowManager-Shell/1.0.0/
    │   ├── WifiTrackerLib/1.0.0/
    │   └── SystemUISharedLib/1.0.0/
    ├── com.android.systemui.flags/
    │   └── flags/1.0.0/
    └── com.android.server.notification/
        └── Flags/1.0.0/
```

### 3.3 AOSP 源码镜像 (在 git 中)
```
SystemUI-core/src/    <--  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src/
SystemUI-core/res/    <--  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/res/
SystemUI-core/res-keyguard/   <-- 不入 git，自动从 AOSP 复制
SystemUI-core/res-product/    <-- 不入 git，自动从 AOSP 复制
```

---

## 四、当前进度状态

### 4.1 已完成
- ✅ 合并 SDK android.jar (减少 错误 5296 → 4675)
- ✅ 替换 framework.jar 为 AOSP 完整版 (减少错误 4675 → 3008)
- ✅ 删除所有 stub 文件 (~60 个) (减少错误 3008 → 2412)
- ✅ 添加 Monet jar 引入 (从 2412 → 2000)
- ✅ 添加 SystemUI Flags jar 引入

### 4.2 当前错误数
- **2000** (截至 2026-07-22)

### 4.3 待解决 (按优先级)

#### 高优先级 (阻塞主流程)
1. **server-notification-flags.jar 不可解析**
   - 现象: `Unresolved reference 'screenshareNotificationHiding'` 等等
   - 状态: jar 在 classpath 中（已 DEBUG 输出验证），但 Kotlin 编译器仍报错
   - 推测原因: kotlin 编译缓存、AAR vs jar 兼容、class visibility issue
   - 涉及文件: `FlagDependencies.kt`, `SensitiveContentCoordinator.kt`, `StackCoordinator.kt`

#### 中优先级 (Compose Scene 框架)
2. **Compose Scene 框架** (`com.android.compose.animation.scene.*`)
   - 依赖内部 Compose API (`modifiers.*`, `graphics.*`, `thenIf`, `drawInContainer`)
   - 需要 SceneFramework AAR 或更多 Compose 依赖
   - 可能提取 AOSP 编译的 androidx.compose.* 进入 jar

3. **Compose Theme/Animation/NestedScroll**
   - `com.android.compose.theme.*` (TypefaceTokens, PlatformTheme 等)
   - `com.android.compose.nestedscroll.*`
   - `com.android.compose.ui.util.*`

#### 低优先级 (功能模块)
4. 各种功能模块编译错误 (CommunalHub, Notification, QS 等)
5. 测试代码编译

---

## 五、问题排查流程

当遇到"Unresolved reference"时：

1. **检查 AOSP 是否有这个符号**
   ```bash
   find /home/conv/myspace/aosp -name "*.java" -o -name "*.kt" | xargs grep -l "<符号>" 2>/dev/null | head -3
   ```

2. **检查 SDK android.jar 是否已包含**
   ```bash
   unzip -l <SDK android.jar> | grep <符号所在包>
   ```

3. **检查 framework.jar 是否已包含**
   ```bash
   unzip -l libs/framework.jar | grep <符号所在包>
   ```

4. **如果是 aconfig Flags 类** → 提取 .class 到独立 jar

5. **如果是 AOSP 编译产物** → 复制对应 jar 到 libs/ 或 libs/maven/

6. **记录到 `docs/issues/YYYY-MM-DD-<topic>.md`**

---

## 六、构建命令速查

```bash
# 编译主模块
./gradlew :SystemUI-core:compileDebugKotlin

# 统计错误数
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep -E "^e: " | wc -l

# 清理
./gradlew :SystemUI-core:clean

# 强制重跑
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks

# 查看依赖
./gradlew :SystemUI-core:dependencies --configuration debugCompileClasspath
```

---

## 七、文档位置

- `docs/GRADLE_MIGRATION_LOG.md` - 主迁移日志 (历史错误数演变表)
- `docs/issues/YYYY-MM-DD-<topic>.md` - 每日详细问题记录
- `tools/gen_aar_maven.py` - AAR 生成脚本 (从 CarSystemUIGradle 复制)

---

## 八、用户偏好

- 用户使用中文交流
- 用户喜欢看代码改动总结
- 用户要求及时记录问题 (2026-07-23 提醒)
- 用户要求先做 plan 再开发 (2026-07-23 提醒)
- 用户希望增量提交，每个 commit 都有意义
- 用户希望参考 `CarSystemUIGradle` 项目的做法
