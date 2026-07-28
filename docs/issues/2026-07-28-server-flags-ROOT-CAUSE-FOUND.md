# Stage 2: server-notification-flags 根因定位 + 修复 (2026-07-28)

> 前序: `2026-07-23-server-notification-flags-unresolvable.md` → `2026-07-28-server-flags-debug-session.md`
> 本文件: **根因已找到并修复**。错误数 2000 → 1979。

## TL;DR

**根因不是 classpath、不是 Kotlin 2.2.10、不是缺 FeatureFlags。**

真正原因：源码里存在一个 **stub 文件** `SystemUI-core/src/com/android/server/notification/Flags.kt`（一个 `object Flags`），
在全项目编译时 **Kotlin 优先用源码定义而非 jar**，于是 `com.android.server.notification.Flags` 解析到这个 stub，
而 stub 里没有 `screenshareNotificationHiding()` 等方法（且把 `politeNotifications` 声明成 `val` 而非方法）。

**修复**: `git rm SystemUI-core/src/com/android/server/notification/Flags.kt`。
删除后 Kotlin 改用 jar 里的真实 `Flags`（含全部方法），19 个错误清零，总错误 2000 → 1979。

---

## 1. 之前几轮排查为何全部走偏

前序文档把方向锁定在 "jar 在 classpath 但 Kotlin 看不到方法"，围绕以下假设反复尝试且全部失败：
- classpath 注入方式 (compileOnly/implementation/api/libraries.from/双重注入)
- Kotlin 2.2.10 对 `@UnsupportedAppUsage` 注解处理变化
- 缺 `FeatureFlags` 接口
- AGP 9 jar 转换

**关键盲点**: 没有人检查 **源码里是否已存在同名 `Flags` 定义**。
前序文档甚至观察到"独立 kotlin(jvm) 项目能编译同一个 jar"——这本该是决定性线索
（独立项目没有那个 stub 源码文件），但被解读成了"Kotlin 版本差异"。

## 2. 本次 systematic-debugging 过程

### Phase 1 复现 + 证伪
1. 基线重编: 2000 错误, 13× `screenshareNotificationHiding`, 6× `FlagDependencies.kt`。
2. 空 jar 核实: `libs/server-notification-flags.jar` 确为空/无内容；真实 jar 在
   `libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar`。
3. **孤立 K2JVMCompiler 实验**（用最小复现 `Test.kt`，内容就是失败的静态导入 + 调用）:
   - 仅 `android.jar + framework.jar + partial-jar`（无 FeatureFlags）→ **编译成功** ⇒ 证伪"缺 FeatureFlags"假设
   - 用**完整 128 项 AGP classpath** → **编译成功** ⇒ 证伪"classpath 有毒 / 有重复 Flags"假设
   - 同一个 Kotlin 2.2.10 编译器 ⇒ 证伪"Kotlin 版本"假设
4. 结论: classpath 与编译器都无罪，差异只可能在 **全项目源码集** 里。

### Phase 2 定位遮蔽源码
```bash
find . -path "*/com/android/server/notification/Flags.*" -not -path "*/build/*"
# → ./SystemUI-core/src/com/android/server/notification/Flags.kt  (git 已跟踪)
```
内容:
```kotlin
package com.android.server.notification
object Flags {
    @JvmField val FLAG_CROSS_APP_POLITE_NOTIFICATIONS = false
    @JvmField val FLAG_POLITE_NOTIFICATIONS = false
    @JvmField val FLAG_VIBRATE_WHILE_UNLOCKED = false
    @JvmField val crossAppPoliteNotifications = false   // ← val, 不是方法
    @JvmField val politeNotifications = false
    @JvmField val vibrateWhileUnlocked = false
    // 没有 screenshareNotificationHiding
}
```
这一次性解释两类错误:
| 错误 | 数量 | 原因 |
|------|------|------|
| `Unresolved 'screenshareNotificationHiding'` | 13 | stub 根本没有该成员 |
| `FlagDependencies.kt` Argument type mismatch + Unresolved | 6 | stub 把 flag 声明为 `val Boolean`，代码按方法 `politeNotifications()` 调用 |

### Phase 3 最小验证
把 stub 挪出源码树重编 → **2000 → 1979** (−21)，`screenshareNotificationHiding` 与 `FlagDependencies` 均归零，**无新增错误**。根因确认。

### Phase 4 固化
`git rm SystemUI-core/src/com/android/server/notification/Flags.kt`。

## 3. 同类隐患（follow-up，本次未动）

广度扫描发现其它同模式 stub 源码 `object Flags`：

| 源码 | 是否有 jar 提供 | 当前是否致错 | 处置 |
|------|----------------|-------------|------|
| `com/android/server/display/feature/flags/Flags.kt` | ✅ framework.jar/android-merged.jar | ❌ 否（stub 为空，无消费者引用缺失成员） | 暂留，latent，不致错不动 |
| `com/android/service/controls/flags/Flags.kt` | ❌ 无 jar | - | **保留**（源码是唯一来源） |
| `com/android/server/policy/feature/flags/Flags.kt` | ❌ 无 jar | - | **保留** |
| `com/android/hardware/devicestate/feature/flags/Flags.kt` | ❌ 无 jar | - | **保留** |
| `com/android/systemui/flags/Flags.kt` | (真实 AOSP 源码, 非 stub) | - | **保留** |

**规律**: 只有当 (1) 源码是 stub 且 (2) 有真实 jar 提供该类 且 (3) 消费者引用了 stub 缺失的成员，三者同时满足才致错。
server.notification 三条全中；display 只中前两条（消费者没引用缺失成员），故暂不致错。

## 4. 给下个 AI 的教训

1. **排查 "Unresolved reference 某方法" 时，先确认该类是从 jar 还是从源码解析的**——
   `find src -path "*/<包路径>/<类名>.*"`。源码同名定义会静默遮蔽 jar。
2. **孤立编译成功 / 全项目编译失败** 的组合，几乎一定指向"源码集里有东西"，而不是 classpath/编译器版本。
3. stub 文件违反 AGENTS.md §1，且会制造这种极难查的遮蔽 bug——见到 `object Flags { val xxx = false }` 立即警惕。

## 5. 错误数演变
| 时点 | 错误数 |
|------|--------|
| 进入本次 | 2000 |
| 删除 stub Flags.kt | **1979** |
