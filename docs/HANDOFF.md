# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 阅读顺序: 本文件 → `AGENTS.md` → `docs/CURRENT_STATE.md` → `docs/PLAN.md` → `docs/PITFALLS.md` → `docs/architecture/` → `docs/issues/`

本文档为新 AI Agent 提供 "5 分钟上手纲要"，详细规则请阅读后续文件。

---

## 0. 这是什么项目

将 AOSP SystemUI 移植到独立 Gradle 编译体系。**目标**：能在用户本地 (Linux) 用 AGP 9.x + Gradle 9.x 编译 SystemUI 源码，错误数从 2000 → 0。

参考实现是用户私有项目 `CarSystemUIGradle`（在同一目录下）。

---

## 1. 5 分钟上线检查清单

### 1.1 确认环境
```bash
# AOSP 源码
ls /home/conv/myspace/aosp/                    # 必须存在
# Android SDK
ls /home/conv/Android/Sdk/platforms/           # 必须有 android-SysUISdk
# 编译入口
cd /home/conv/myspace/SystemUI-Gradle
./gradlew --version                            # Gradle 9.5
```

### 1.2 跑一次基线编译，统计错误数
```bash
./gradlew :SystemUI-core:compileDebugKotlin --console=plain 2>&1 | tee /tmp/build.log
echo "Total errors: $(grep -c '^e: file:' /tmp/build.log)"
echo "screenshareNotificationHiding: $(grep -c 'screenshareNotificationHiding' /tmp/build.log)"
```

**历史基线（2026-07-29）**: **70** 错误（src/aidl/res 完整性审查后）。其中：
- ~~server-notification Flags~~: ✅ 已清零（删除 stub `Flags.kt`）
- ~~全项目 R import 歧义~~: ✅ 已清零
- Compose Scene Framework (`com.android.compose.animation.scene.*`): 12 个
- 其他残留错误: ~58 个

> **2026-08-06 更新**：该 70 错误不是当前基线。当前 checkpoint 中的 AAR 生成改写导致 AAR transform 在编译前失败，错误数暂时无统计意义。用户已明确错误数在任何阶段都只作为诊断，不是提交/回滚/审批门槛；当前先校准源码/jar/AAR 来源与模块边界。详见 `AGENTS.md` §2.1 和 `docs/architecture/2026-08-06-reference-project-rationale.md`。

### 1.3 必须遵守的规则（优先级从高到低）

1. **用户指令 > 本文件 > 默认系统提示**
2. **规则 P**: 不要创建 stub 类（详见 AGENTS.md §1）
3. **规则 S**: SystemUI 自有代码一律源码复制；非自有纯代码走 jar、含资源走 AAR（详见 §1.5）
4. **规则 C**: SystemUI src/aidl/res 必须与 AOSP 不漏不多（详见 §1.6）
5. **规则 F**: framework 等非 SystemUI 代码严禁源码复制（详见 §1.7）
6. **规则 R**: res 缺失走 AOSP 源码 → 直接 AAR → 确认冲突后本地 Maven AAR；禁止凭空生成（详见 §1.8）
7. **规则 B**: 项目结构按 AOSP `Android.bp`（详见 §1.9 + `docs/adr/0003`）
8. **规则 I**: 以项目整体向前推进为标准；错误数不是提交/回滚/审批门槛，不要求每次修改或提交都编译
9. **规则 D**: 所有改动先写文档 (`docs/issues/YYYY-MM-DD-<topic>.md`)
10. **规则 H**: 不要替用户做产品决策；遇 2+ 候选方案用 `AskQuestion`

详细决策见 `docs/adr/`：
- **ADR 0001** `aosp-res-via-local-maven.md` — res 处理优先级：AAR 先直接引入，确认冲突后才用 local Maven
- **ADR 0002** `tools-scripts-only-python.md` — 脚本一律 Python
- **ADR 0003** `app-module-aligns-aosp-bp.md` — 项目结构对齐 bp

---

## 2. 项目结构速查

```
SystemUI-Gradle/
├── AGENTS.md                  # ⭐ 项目规则（必读）
├── docs/
│   ├── HANDOFF.md             # ⭐ 本文件（新 AI 入口）
│   ├── CURRENT_STATE.md       # ⭐ 当前状态快照
│   ├── PLAN.md                # 阶段计划
│   ├── PITFALLS.md            # ⚠️ 踩坑记录
│   ├── GRADLE_MIGRATION_LOG.md # 历史错误数演变
│   ├── issues/               # 每日问题记录
│   └── architecture/         # 架构/调研文档
├── libs/                     # 自包含依赖（不入 gitignore）
│   ├── framework.jar         # AOSP 框架（含 @hide API）
│   ├── framework-statsd.jar
│   ├── android.car.jar
│   ├── WindowManager-Shell.jar
│   ├── android_module_lib_stubs_current.jar
│   ├── SystemUI-{proto,tags,statsd}.jar
│   ├── monet.jar            # ColorScheme/Shades/Style
│   ├── systemui-flags.jar   # com.android.systemui.Flags
│   ├── maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar
│   ├── prebuilts/
│   │   ├── SystemUISharedLib.jar
│   │   ├── SystemUIPluginLib.jar
│   │   ├── SystemUICustomizationLib.jar
│   │   ├── PlatformAnimationLib.jar
│   │   └── tracinglib-platform.jar
│   └── maven/com/android/systemui/{settingslib,iconloader,WindowManager-Shell,WifiTrackerLib,SystemUISharedLib}/1.0.0/
├── SystemUI-core/            # 主模块 ~95% 代码
│   ├── src/                  # = AOSP frameworks/base/packages/SystemUI/src/
│   ├── res/                  # = AOSP SystemUI/res/
│   ├── res-keyguard/         # = AOSP SystemUI/res-keyguard/
│   ├── res-product/          # = AOSP SystemUI/res-product/
│   ├── build.gradle.kts
│   └── AndroidManifest.xml
├── SystemUI-{shared,animation,customization,plugin,plugin-core}/
├── app/                      # 主入口
├── build.gradle.kts          # 根项目（allprojects 注入 framework.jar）
├── settings.gradle.kts
└── gradle/libs.versions.toml
```

---

## 3. 调试模式与工具链

| 工具 | 版本 | 备注 |
|------|------|------|
| Gradle | 9.5.0 | wrapper |
| AGP | 9.2.0 | alias `libs.plugins.android.library` |
| Kotlin Plugin | 2.1.0（项目）/ 2.2.10（AGP 内部嵌入） | 关键：**AGP 嵌入的 kotlin-compiler-embeddable 比插件新** |
| KAPT | 1.9+ 临时禁用 | 1.9+ 与 Gradle 9.5 报 "IR 内部错误" |
| 目标 JVM | 21 | Java/Kotlin 编译都用 21 |
| 目标 SDK | `SysUISdk`（自定义 preview） | 路径 `/home/conv/Android/Sdk/platforms/android-SysUISdk/` |

---

## 4. 我（当前 AI）留下未完成的事

### 4.1 Stage 2 (server-notification-flags.jar)
- **状态**: ✅ **已解决 (2026-07-28)**。根因是源码 stub `com/android/server/notification/Flags.kt`
  遮蔽了 jar，`git rm` 后 2000 → 1979。**不是** classpath/Kotlin 2.2.10/FeatureFlags 的问题。
- **详情**: `docs/issues/2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`、`docs/PITFALLS.md §2.4`

### 4.2 app 模块按 bp 重构（ADR 0003，结构已更正）
- **状态**: ✅ 结构决策已更正并实施（详见 `docs/adr/0003-app-module-aligns-aosp-bp.md`）
- **7/31 关键更正**：最初将 bp 误读为入口类属于 app。实际 `SystemUI-core` 的 `srcs: ["src/**/*.java"]` 包含 `SystemUIApplication.java` / `SystemUIService.java`；`android_app "SystemUI"` 无独立 srcs。
- **正确结构**：入口类保留在 `:SystemUI-core/src/com/android/systemui/`；`:app` 无源码，只依赖 `:SystemUI-core`，并持有完整 AOSP manifest/proguard 配置。
- **禁止**再次把入口类迁到 `:app/src/main/java/`。

### 4.3 animationlib 源码化（进行中，未提交）
- **状态**: 🚧 源码已复制、模块骨架已创建、settings.gradle.kts 已加，但 animation/customization 的
  `build.gradle.kts` 还没改（还在用 `compileOnly(animationlib.jar)`），`libs/animationlib.jar` 也还没删
- **详情**: `docs/issues/2026-07-29-aidl-animationlib-app.md §三`
- **下一步**:
  1. `:SystemUI-animation` / `:SystemUI-customization` 的 `compileOnly(animationlib.jar)` → `api(project(":SystemUI-animationlib"))`
  2. 删除 `libs/animationlib.jar`
  3. 检查 WMShell.jar 的 6 个重叠类是否冲突

### 4.4 Stage 3 (Compose Scene Framework)
- **状态**: 12 个错误，全部在 `com.android.compose.animation.scene.*`
- **错误种类**: `thenIf`, `drawInContainer`, Modifier 内部 API, `ContainerState`
- **下次 Agent 行动**: 详查 `docs/CURRENT_STATE.md` §3

### 4.5 AIDL 编译知识（已解答）
- **问题**: 为什么 framework.jar 不能满足 AIDL 编译需要？
- **答案**: aidl 工具只认 `.aidl` 声明文件，不读 jar 字节码。framework.aidl 和 framework.jar
  服务于两个不同编译阶段，互补不可替代。详见 `docs/issues/2026-07-29-aidl-animationlib-app.md §一`
- **ISystemUiProxy.aidl** 属于 `:SystemUI-shared` 模块，由 `OverviewProxyService.java` 使用

---

## 5. 我的工作偏好

- 用户用中文交流
- 用户喜欢看代码改动总结
- 用户要求及时记录问题 (2026-07-23 提醒)
- 用户要求先做 plan 再开发 (2026-07-23 提醒)
- 用户希望增量提交，每个 commit 都有意义
- 用户希望参考 `CarSystemUIGradle` 项目的做法
- **用户要求给下一个 AI 留完整交接文档** (2026-07-28 提醒)

---

## 6. 紧急联系信息（重要）

如遇到下面情况，**停止**并询问用户：

1. 必须创建 stub 类（违反规则 P）
2. 必须修改 res/ 下的资源文件
3. 需要产品决策（多个等价方案）
4. 需要修改 AGENTS.md 的核心规则

---

**下一步**: 阅读 `AGENTS.md` 完整规则。
