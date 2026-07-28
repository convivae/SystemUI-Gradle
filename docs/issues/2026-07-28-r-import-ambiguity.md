# Stage 3 (部分): 消除全项目 R import 歧义 (2026-07-28)

> 承接 `2026-07-28-server-flags-ROOT-CAUSE-FOUND.md`（Stage 2 已解决，2000→1979）。
> 本次处理 `docs/PITFALLS.md §3.2` 的 "Compose Theme R 冲突"，并顺带清掉全项目所有 R 歧义。

## TL;DR

7 个文件同时 `import` 了两个名为 `R` 的类，触发 `imported name 'R' is ambiguous`，
并**级联**导致文件内所有 `R.xxx` 引用报 unresolved。删除每个文件里**多余的那一个** R import
（对齐 AOSP 原文件），错误数 **1979 → 1879 (−100)**，全项目 R 歧义清零。

## 根因

Kotlin 不允许同一文件 import 两个同名类。这些文件被（非 AOSP 地）加了一行多余的
`import com.android.systemui.R`，与文件本应使用的另一个 R 冲突。AOSP 原文件每个都只 import 一个 R。

| 文件 | 冲突的两个 R | 应保留(对齐AOSP) | 删除 |
|------|-------------|-----------------|------|
| compose/theme/AndroidColorScheme.kt | internal.R + systemui.R | `com.android.internal.R` | systemui.R |
| compose/theme/PlatformTheme.kt | internal.R + systemui.R | `com.android.internal.R` | systemui.R |
| accessibility/floatingmenu/DragToInteractView.kt | systemui.R + wm.shell.R | `com.android.wm.shell.R` | systemui.R |
| screenshot/ScreenshotWindow.kt | android.R + systemui.R | `android.R` | systemui.R |
| user/ui/dialog/AddUserDialog.kt | settingslib.R + systemui.R | `com.android.settingslib.R` | systemui.R |
| user/ui/dialog/ExitGuestDialog.kt | settingslib.R + systemui.R | `com.android.settingslib.R` | systemui.R |
| volume/domain/interactor/DeviceIconInteractor.kt | settingslib.R + systemui.R | `com.android.settingslib.R` | systemui.R |

> `internal.R.color.system_*` 是 framework 动态色 (public)，已验证在 framework.jar / android.jar 里。

## 方法（systematic-debugging）

1. **复现**: AndroidColorScheme.kt 26 错 = 2 R 歧义 + 24 级联 color 错。
2. **对照 AOSP**: 每个文件的 AOSP 原版都只 import 一个 R；多出来的 systemui.R 是本地添加。
3. **最小验证**: 逐个删除多余 import，重编。
4. **无回归验证**: 5 个 systemui-vs-其它 R 的文件，改前/改后错误数均**严格下降**
   （如 DragToInteractView 22→3, ScreenshotWindow 6→0），没有任何文件变差。

## 残留（follow-up，归入 Stage 4 资源完整性，非本次范围）

删除歧义后，少数 `R.xxx` 引用变成诚实的 unresolved，属于**资源缺失**而非 import 问题：

| 文件 | 残留 | 归属 | 说明 |
|------|------|------|------|
| ExitGuestDialog.kt | `guest_exit_*` (7) | AOSP SettingsLib strings | 我们的 SettingsLib aar 缺这些 string |
| AddUserDialog.kt | `user_add_user_message_guest_remove` (1) | 在 SystemUI-core/res | 需 systemui.R —— 该文件其实同时用到两个 R，可后续用 alias import 修 |
| DragToInteractView.kt | `action_edit`/`action_remove_menu` (systemui res), `ic_screenshot_edit` | 混合 | 同上，需 alias import |
| DeviceIconInteractor.kt | `DeviceIconUtil` 类 + `ic_earbuds_advanced` | 缺类/缺 drawable | `DeviceIconUtil` 是**类**未解析(与 R 无关，本就存在) |

**规律**: 当一个文件真的同时需要两个 R 命名空间时，正解是 alias import
（`import com.android.settingslib.R as SettingsR` 并限定引用），而非删一个。
本次这几个文件删 systemui.R 后仍净下降，故先按对齐 AOSP 处理，alias 修复留作后续。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| 本次起点 (Stage 2 后) | 1979 |
| 修 AndroidColorScheme.kt | 1953 |
| 修 PlatformTheme.kt | 1923 |
| 修其余 5 个 R 歧义文件 | **1879** |
