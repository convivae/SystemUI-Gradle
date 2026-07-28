# SystemUI-Gradle 项目开发规则 (AGENTS.md)

> 这是本项目的全局指令。所有 AI Agent 在本项目中工作时必须遵守此文件。
> 用户指令优先级最高，本文件次之，最后是默认系统提示。
> **新 AI Agent 请先读 `docs/HANDOFF.md` 取得 5 分钟概要，再读本文件了解完整规则。**

---

## 〇、用户指令优先级

1. **用户明确指令** (用户在 chat 中的话) — 最高
2. **AGENTS.md + docs/HANDOFF.md** — 次之
3. **默认系统提示** — 最低

冲突时按顺序适用。例如：用户说"用 stub" → 听用户的；用户没说 → 遵守规则 P。

---

## 一、依赖引入规则 (用户明确要求，2026-07-22)

> **规则 P (Project Rule)**: 不允许使用 stub 技术。

### 1.1 允许的四种依赖形式

| 形式 | 何时用 | 示例 |
|------|--------|------|
| 源码复制 | AOSP 完整模块的源码 | `implementation(project(":SystemUI-shared"))` |
| jar | AOSP 编译产物、对 `aconfig` Flag、单类 | `compileOnly(files("libs/framework.jar"))` |
| aar | 含资源的 AOSP 库 | `implementation(libs.systemui.settingslib)` |
| maven | 上游 AndroidX / Compose | `implementation("androidx.compose.ui:ui:1.7.5")` |

### 1.2 禁止

- ❌ **不允许创建 *.java stub 类**只为让 IDE/编译器满意
- ❌ **不允许私自创建资源文件** (res/ 下的任何 .xml/.png/.9.png 等)
- ❌ **不允许创建 *.kt stub 文件**（同 Java）
- ❌ 所有资源文件必须来自：AOSP 源码、aar 包、maven 依赖
- ⚠️ 退路：如果所有方案都失败，**临时**用 stub 必须明显标注 `// TODO: temporary stub, replace with real impl` 并记录到 `docs/issues/`

### 1.3 允许

- ✅ 复制 AOSP 源码目录作为 module (例如 `:SystemUI-monet`)
- ✅ 从 AOSP 编译产物提取 *.class 打包为 jar
- ✅ 从 AOSP 编译产物提取 jar/aar 放到 `libs/` 或 `libs/maven/`
- ✅ 复制 AOSP 的 res 目录 (例如 `res-keyguard/`, `res-product/`)
- ✅ 对 res 目录做必要的去重/合并 (AAPT2 不支持 product 属性)

### 1.4 参考实现

- `CarSystemUIGradle` 项目 (同用户私有项目) 是参考实现
- 关键脚本：`tools/gen_aar_maven.py` （已从 CarSystemUIGradle 复制）
- 关键资源：参考 `CarSystemUIGradle/SystemUI-core/build.gradle.kts` 的依赖引入方式

---

## 二、本项目开发原则

### 2.1 增量开发

> **规则 I (Incremental)**: 每次 commit 必须: (1) 改动小而聚焦 (2) 编译错误数下降 (3) 记录在文档

- 错误数演变表必须维护 (`docs/GRADLE_MIGRATION_LOG.md`)
- 不要跨大步、一次做太多事
- 如果一次改动让错误数上升 >50，立即回滚并重新设计

### 2.2 文档先行

> **规则 D (Documentation)**: 每个步骤开始前先在 `docs/issues/` 下写文档

- 文档命名：`docs/issues/YYYY-MM-DD-<topic>.md`
- 文档包含：背景、操作步骤、错误数演变、待解决问题
- 复杂调研写在 `docs/architecture/YYYY-MM-DD-<topic>.md`

### 2.3 遵循 AOSP 源码结构

| 资源类型 | 路径 |
|---------|------|
| AOSP 源码 | `/home/conv/myspace/aosp/` |
| AOSP 中间产物 | `/home/conv/myspace/aosp/out/soong/.intermediates/` |
| AOSP 编译 jar | `/home/conv/myspace/aosp/out/target/common/obj/*/classes.jar` |
| AOSP turbine-combined | `aosp/out/.../turbine-combined/*.jar` |

参考 AOSP 的 `Android.bp` 文件了解模块依赖关系。

### 2.4 SDK 与 framework.jar 关系

- 我们的 SDK: `compileSdkPreview = "SysUISdk"` (位于 `/home/conv/Android/Sdk/platforms/android-SysUISdk/`)
- AOSP `framework.jar` 提供 SDK 不含的 @hide API 和内部类
- `build.gradle.kts` 通过 `allprojects { ... }` 注入 framework.jar 到所有 Kotlin/Java 编译
- 关键技巧：内部 flags jar 必须放在 framework.jar 之前，否则 framework.jar 的同名 stub 会遮蔽

### 2.5 求助于用户

> **规则 H (Human Escalation)**: 遇到下面任一情况，**停止**并用 `AskQuestion` 询问用户

1. 必须创建 stub 类（违反规则 P）
2. 必须修改 res/ 下的资源文件
3. 错误数大幅上升（>200）而非下降
4. 需要产品决策（多个等价方案）
5. 需要修改 AGENTS.md 的核心规则
6. 所有尝试过的方案都失败，需要决策下一步方向

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
├── server-notification-flags.jar       # 见 notes: 实际为空, 真实 jar 在 libs/maven/
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
        └── Flags/1.0.0/                # 真实的 notification-flags-1.0.0.jar (6285 bytes)
```

**⚠️ 重要**: `libs/server-notification-flags.jar` 当前是**空 jar**（0 字节）。真实的 jar 在 `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`，plugin id `android-server-notification-flags` 已被 libs.versions.toml 定义。

### 3.3 AOSP 源码镜像

```
SystemUI-core/src/             <--  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src/
SystemUI-core/res/             <--  AOSP SystemUI/res/
SystemUI-core/res-keyguard/    <--  AOSP SystemUI/res-keyguard/
SystemUI-core/res-product/     <--  AOSP SystemUI/res-product/
```

---

## 四、当前进度状态 (2026-07-28)

### 4.1 已完成

| 时间 | 错误数 | 操作 |
|------|--------|------|
| 2026-07-22 初 | 5296 | 仅有 sdk android.jar |
| 2026-07-22 | 4675 | 替换 framework.jar (AOSP 完整版) |
| 2026-07-22 | 3008 | 合并 SDK android.jar + framework.jar |
| 2026-07-22 | 2412 | 删除所有 v1 stub 文件 |
| 2026-07-22 | 2000 | 加 Monet jar + SystemUI Flags jar |
| 2026-07-23 | 2000 | (本日到此) |

### 4.2 当前错误数

- **2000** (截至 2026-07-28)
- 详细分类见 `docs/CURRENT_STATE.md` §3

### 4.3 待解决 (按优先级)

#### 高优先级 (阻塞主流程)
1. **server-notification-flags.jar 不可解析** (Stage 2)
   - 现象: `Unresolved reference 'screenshareNotificationHiding'` 等等
   - 状态: jar 实际在 classpath（`./gradlew --debug` 验证），但 Kotlin 2.2.10 编译器仍报 Unresolved
   - 详细: `docs/issues/2026-07-28-server-flags-debug-session.md`
   - **下次 AI Agent 必读**

#### 中优先级 (Compose)
2. **Compose Scene Framework** (`com.android.compose.animation.scene.*`) — 12 错误
3. **Compose Theme** (`AndroidColorScheme.kt`) — 60 错误（R 冲突）
4. **Compose NestedScroll** (`com.android.compose.nestedscroll.*`) — 0 错误（已排除）
5. **Compose UI Util** (`com.android.compose.ui.util.*`) — 0 错误（已排除）

#### 低优先级 (功能模块)
6. 业务模块编译错误 (~1909 个分散在 80+ 包)
7. 测试代码编译

### 4.4 紧急修复

`compose/animation/scene` 之外的 `compose/{nestedscroll,ui/util}` 文件已**未跟踪**（`git status` 中的 `??`），但 `compose/animation/scene` 文件也已 untracked。可推断这些文件不会被编译（源码未被 build.gradle 引用）。

---

## 五、问题排查流程

当遇到 `Unresolved reference` 时：

### 5.1 诊断 5 步

```bash
# 1. 在 AOSP 查符号
find /home/conv/myspace/aosp -name "*.java" -o -name "*.kt" | xargs grep -l "<符号>" 2>/dev/null | head -3

# 2. 在 SDK android.jar 查
unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar | grep <符号所在包>

# 3. 在 framework.jar 查
unzip -l libs/framework.jar | grep <符号所在包>

# 4. 在 systemui-flags / monet / server-notification-flags 查
unzip -l libs/systemui-flags.jar | grep <符号>
unzip -l libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar

# 5. javap 看具体方法
javap -p <ClassName>
```

### 5.2 错误归类

| 错误种类 | 出现场景 | 处理路径 |
|---------|---------|---------|
| `Unresolved reference X` | 类/方法/字段找不到 | 5.1 找位置 → 写 jar/module |
| `Cannot infer type` | 多 overload 重叠 | 显式类型注解 |
| `Argument type mismatch` | 选错 overload | 同上 |
| `Conflicting import` | 多个 R 类 | alias import |
| `None of the following candidates is applicable` | receiver type 不匹配 | 看 arg 实际类型 |

### 5.3 通用解决方案

| 解决方案 | 风险 | 适用 |
|---------|------|------|
| 提取 .class 到 jar | 低 | aconfig Flags |
| 加 aar 依赖 | 低 | 含资源 |
| 复制源码为 module | 中 | 完整模块 |
| 升级 Compose 版本 | 中 | 内部 API |
| 排除源码 | 临时 | 暂时不用的代码 |

---

## 六、构建命令速查

```bash
# 编译主模块
./gradlew :SystemUI-core:compileDebugKotlin

# 统计错误数
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep -cE "^e: file:"

# 分类错误
./gradlew :SystemUI-core:compileDebugKotlin 2>&1 | grep "^e: file:" | \
  sed -E 's|.*/SystemUI-Gradle/SystemUI-core/src/com/android/||; s|/[^/]+\.kt.*||' | \
  sort | uniq -c | sort -rn | head -20

# 清理
./gradlew :SystemUI-core:clean

# 强制重跑
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks

# 查看依赖
./gradlew :SystemUI-core:dependencies --configuration debugCompileClasspath

# Debug 模式（看实际 classpath）
./gradlew :SystemUI-core:compileDebugKotlin --debug 2>&1 | grep -oE "[-]classpath [^ ]+"
```

---

## 七、文档位置

| 路径 | 说明 |
|------|------|
| `docs/HANDOFF.md` | ⭐ 下个 AI 必读入口 |
| `AGENTS.md` | ⭐ 本文件（规则 + 现状） |
| `docs/CURRENT_STATE.md` | 状态快照 |
| `docs/PLAN.md` | 阶段计划 |
| `docs/PITFALLS.md` | 踩坑记录 |
| `docs/GRADLE_MIGRATION_LOG.md` | 历史错误数演变 |
| `docs/issues/YYYY-MM-DD-<topic>.md` | 每日详细问题记录 |
| `docs/architecture/YYYY-MM-DD-<topic>.md` | 复杂调研 |
| `tools/gen_aar_maven.py` | AAR 生成脚本 |

---

## 八、用户偏好

- 用户使用中文交流
- 用户喜欢看代码改动总结
- 用户要求及时记录问题 (2026-07-23 提醒)
- 用户要求先做 plan 再开发 (2026-07-23 提醒)
- 用户希望增量提交，每个 commit 都有意义
- 用户希望参考 `CarSystemUIGradle` 项目的做法
- **用户要求给下一个 AI 留完整交接文档** (2026-07-28 提醒)
- 用户坚持"无 stub"原则 (2026-07-22 决定)

---

## 九、版本历史

| 日期 | 改动 |
|------|------|
| 2026-07-22 起草 | 初始版本，仅有规则 |
| 2026-07-23 增订 | 加入当前进度和待解决 |
| 2026-07-28 重写 | 配合 docs/HANDOFF.md 重组结构，新增 §0 优先级、§1.4 参考、§2.5 求助规则、§3.2 libs 警告、§4.1 错误数演变表 |

---

**下一步**: 阅读 `docs/CURRENT_STATE.md` 了解具体状态。
