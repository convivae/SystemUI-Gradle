# 2026-08-24 Window Flags Runtime Closure

## 背景

同树 x86_64 模拟器运行时发现 `com.android.window.flags.Flags` 缺失导致 SystemUI crash loop。

## 根因与修复

- 根因：Soong aconfig 的 `java_aconfig_library` 模块被 AOSP 构建系统通过 `aconfig_values` 标记为 `exportable: true`，但生成的 runtime class 未打包进 debug APK。
- 修复：提取 `window-flags.jar`（byte-identical Soong javac 产物）到 `libs/`，在 `SystemUI-core/build.gradle.kts` 显式依赖。
- 验证：DEX 解析确认 `Lcom/android/window/flags/Flags;` 恰有一个定义。

## 扩展审计

用 `/tmp/dex_types.py` 扫描全 flags closure，发现 16 个缺失包（含 `com.android.window.flags`）。
对照 stock APK：stock 经 R8 常量折叠后大部分 flag 引用已消除，但我们的 debug build 无 R8，所有引用保留，因此 16 个全部需要定义。

## 当前进展

1. ✅ `window-flags.jar` 已加入，crash 首因从 `NoClassDefFoundError` 推进。
2. ✅ `device-state-feature-flags.jar` 已加入，当前首因变为 Dagger 图重复注册 `NotificationLockscreenUserManagerImpl`。
3. 🔴 当前运行时首因：`java.lang.IllegalArgumentException: 'com.android.systemui.statusbar.NotificationLockscreenUserManagerImpl' is already registered`（DumpManager 重复注册）。

## 待解决

- 其余 14 个缺失 flag 包待逐一按同样方式修复（一次一个根因）。
- 当前阻塞：Dagger 图生成逻辑导致 `NotificationLockscreenUserManagerImpl` 被构造两次。

## 证据

- 构建日志：`/home/conv/task053-device-flags-soong.log`
- 审计脚本：`/tmp/dex_types.py`, `/tmp/stock_audit.py`
- 候选 APK：`/home/conv/myspace/task053-same-tree-x86_64-runtime/deploy/devicestate-flags-candidate/app-debug-devicestate.apk`
- Crash 日志：`/tmp/task053-devicestate-crash.log`
