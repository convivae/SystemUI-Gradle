# SystemUI-Gradle

**[English](README.en.md)** | 中文

把 AOSP `frameworks/base/packages/SystemUI`——Android 的**状态栏、通知栏 / 快捷设置、锁屏（Keyguard）、
最近任务概览**等系统界面的完整真实源码——从 Soong 构建体系中剥离出来，移植为一个**独立、自包含的
Gradle 工程**：脱离 AOSP 源码树即可用 Android Studio / Gradle 构建出真实 SystemUI APK（非删减、
非 stub），并与 AOSP 源码、资源保持 1:1 对齐，改动随时可以回流上游。

- **AOSP 基线**：`android-17.0.0_r1`（Android 17 首个 release tag）
- **构建链**：Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10（AGP builtInKotlin）· KSP · Dagger · Compose · JDK 21
- **已达成**：Debug APK（约 200 MB）与 R8 优化 Release APK（约 45 MB）均编译通过，
  并已部署到 Android 17 x86_64 模拟器**真实运行**——冷启动与整机重启后均稳定（零崩溃、
  状态栏 / 通知栏 / 壁纸正常上屏）

## 这个项目能为你带来什么

AOSP 的 SystemUI 正常只能在完整的 AOSP 源码树内用 Soong 编译。本项目把它变成一个普通的
Android Gradle 工程，意味着你可以：

- **用 Android Studio 开发 SystemUI**：完整的代码索引、跳转、重构、断点调试，
  迭代速度从"整树编译"变成"按一下 Run 前的普通构建"；
- **独立版本化**：SystemUI 代码在自己的 git 仓库里分支、评审、回滚，不再绑定整套 AOSP checkout；
- **做二次开发**：定制状态栏 / 通知栏 / 锁屏、做 ROM 或行业系统（车机、平板、IoT）的系统 UI，
  直接在真实 AOSP 源码上改，而不是维护一堆 patch；
- **研究与教学**：SystemUI 是 Android 里最复杂的应用之一（Dagger + Compose + 插件化 +
  大量 `@hide` API），本工程让它可以像普通 app 一样被阅读和实验；
- **可复现**：仓库内所有二进制依赖（jar / AAR）都提交入 git，且每个都能用 `tools/` 下的
  脚本从 AOSP 构建产物**确定性再生**——没有手工上传的"魔法文件"。

## 它是怎么做到的（概览）

SystemUI 难以脱离 AOSP 构建的根本原因是：它大量使用标准 Android SDK 中不存在的
`@hide` API、aconfig 生成的 flags 类和 framework 私有资源。本项目的解决方式：

1. **SysUISdk**：一个自定义的编译平台（`compileSdkPreview = "SysUISdk"`），由单入口生成器
   `tools/build_sysuisdk.py` 从官方 SDK + 已构建的 AOSP 产物合成，补齐隐藏 API、
   framework 私有资源与 `@hide` AIDL 声明。它是"编译时平台"，不进 APK。
2. **三层依赖策略**：第三方库（androidx / Compose / Dagger 等）一律用官方 Maven 坐标；
   无资源的 AOSP 纯代码产物用本地 jar；含资源的 AOSP 库用 AAR。**全仓库没有任何手写 stub**。
3. **17 个 Gradle 模块**：模块边界按 AOSP `Android.bp` 的语义划分（见下表），
   SystemUI 自有代码全部以源码形式参与编译，资源和 manifest 与 AOSP 逐文件对齐。
4. **构建期引用改写**：Android 17 的 Soong 构建会把一批 framework aconfig 类改名到隐藏包
   （`com.android.internal.hidden_from_bootclasspath.*`）。本工程在 AGP 的字节码插桩阶段
   按同一份 AOSP 规则表（725 条 exact rename）做**仅引用级**改写，并附带指令级静态校验器
   `tools/check_aconfig_jarjar_references.py` 对 APK 做完整校验，保证运行时引用的类名与设备
   framework 一致。

### 模块地图

| 模块 | 职责（对应 AOSP Soong target） |
|---|---|
| `:app` | APK 入口：签名、打包、manifest 合并壳（`android_app "SystemUI"`） |
| `:SystemUI-core` | 主模块：`SystemUIApplication` 等入口类、src + compose + pods |
| `:SystemUI-application` | Dagger 根组件 + 完整 AOSP manifest |
| `:SystemUI-res` | 资源模块（res / res-keyguard / res-product），生成 `com.android.systemui.res.R` |
| `:SystemUI-common` | Common + Log + shared-utils |
| `:SystemUI-animation` | 平台动画库（PlatformAnimationLib） |
| `:SystemUI-compose` | Compose Core + Scene |
| `:SystemUI-customization` | 定制库（壁纸、主题选择器等） |
| `:SystemUI-clocks-common` | 时钟公共库 |
| `:SystemUI-shared` | shared + keyguard（含 AIDL 与资源） |
| `:SystemUI-shared-biometrics` | 生物识别（独立资源命名空间） |
| `:SystemUI-plugin` / `:SystemUI-plugin-core` | 插件 runtime 与 API |
| `:SystemUI-plugin-processor` | 插件注解处理器（仅构建期） |
| `:SystemUI-unfold` | 折叠屏 unfold 库 |
| `:SystemUI-accessibility-floatingmenu-res` | 无障碍悬浮菜单资源 |
| `:SystemUI-utils-kairos` | kairos（SystemUI 的响应式状态库） |

## 快速开始

> 说明：仓库内的 jar / AAR 依赖已全部提交，**clone 后即可构建**；唯一不在仓库内的前提是
> SysUISdk 编译平台与部署目标（模拟器镜像），它们各需要一次 AOSP 构建来生成。

### 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Ubuntu Linux（x86_64），用户在 `kvm` 组 |
| 磁盘 | 完整复现（含 AOSP）≥ 400 GiB；仅构建本工程 ≈ 20 GiB |
| 内存 | ≥ 32 GiB 推荐（AOSP 全量构建用；仅构建本工程 16 GiB 可行） |
| JDK | 17+（实测 21） |
| Python | 3.x + [uv](https://docs.astral.sh/uv/)（脚本一律 `uv run`） |
| 工具 | adb；可选 scrcpy（查看无头模拟器画面） |

### 步骤

**1.（一次性）获取并构建 AOSP `android-17.0.0_r1`** — 产物用于生成 SysUISdk 与模拟器镜像：

```bash
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -d -c -j4
cd <aosp-root> && . build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j$(nproc)
```

**2.（一次性）生成 SysUISdk**：

```bash
uv run python tools/build_sysuisdk.py --aosp-root <aosp-root>
# 输出 <sdk-root>/platforms/android-SysUISdk
```

**3. 构建本工程**：

```bash
git clone <this-repo> && cd SystemUI-Gradle
./gradlew :app:assembleDebug       # Debug APK → app/build/outputs/apk/debug/
./gradlew :app:assembleRelease     # R8 优化 Release APK → app/build/outputs/apk/release/
uv run pytest tools/tests/ -q      # 工具链测试
```

**4. 启动模拟器并部署**：用第 1 步产出的 `sdk_phone64_x86_64` 镜像启动模拟器
（`ANDROID_PRODUCT_OUT=<aosp-root>/out/target/product/emu64x emulator ...`，完整参数见
[docs/issues/2026-08-26-emulator-relaunch-runbook.md](docs/issues/2026-08-26-emulator-relaunch-runbook.md)），
然后替换系统 SystemUI：

```bash
adb root && adb disable-verity && adb reboot   # 等开机后：
adb root && adb remount
adb push app/build/outputs/apk/debug/app-debug.apk /system_ext/priv-app/SystemUI/SystemUI.apk
adb shell pm grant com.android.systemui android.permission.BLUETOOTH_CONNECT
adb shell pm grant com.android.systemui android.permission.READ_CONTACTS
adb reboot
```

部署细节与已知坑（校验、overlay 只读、grant 重置等）见
[docs/PITFALLS.md](docs/PITFALLS.md) 设备/模拟器章节。

## 二次开发指南

**改代码**：SystemUI 源码在 `SystemUI-core/src/`（与 AOSP `packages/SystemUI/src/` 逐路径对应），
各子库在对应 `SystemUI-*` 模块。直接改、直接构建即可——没有代码生成、没有中间层。

**改资源**：资源集中在 `SystemUI-res/res*`（与 AOSP `res/`、`res-keyguard/`、`res-product/` 1:1）。
资源引用使用 `com.android.systemui.res.R`。

**保持与上游同步**：本工程刻意不做"fork 式"改写——源码和资源与 AOSP 保持逐文件对齐，
由 `tools/check_source_alignment.py --strict` 自动校验（缺失 / 错位 / 多余文件均为 0）。
当你自己的修改积累到一定量后，可以按普通 git 流程 rebase / cherry-pick 回 AOSP 风格的提交。

**升级 AOSP 基线**：换 AOSP tag 后按顺序执行——重对齐源码（`check_source_alignment.py`）、
重跑 `tools/package_*.py` 再生全部 jar / AAR、重建 SysUISdk、重建 APK 并跑部署验证。
整条链路全部脚本化，无需手工产物。

**验证清单**（每次改动后）：

```bash
./gradlew :app:assembleDebug                                 # 编译门
uv run python tools/check_source_alignment.py --strict       # 对齐门（需 AOSP 树）
uv run python tools/check_aconfig_jarjar_references.py \
    --apk app/build/outputs/apk/debug/app-debug.apk          # APK 引用完整性门
uv run pytest tools/tests/ -q                                # 工具链回归
```

## 已知限制

- **依赖版本上限**：Compose 不得升到 1.12（移除了 AOSP 在用的 `ExperimentalAnimatableApi`）；
  kotlinx-coroutines 上限 1.10.2（1.11 的新 overload 破坏 AOSP 源码）。升级依赖请先查阅
  [docs/PITFALLS.md](docs/PITFALLS.md)。
- **部署目标必须是 same-tree 构建**：SystemUI 是平台签名应用且调用隐藏 API，
  必须部署到与基线一致的 AOSP 构建（本工程用同树模拟器镜像验证）；不能直接装到
  普通商用手机或官方模拟器镜像上。
- **Release 不混淆**：对齐 AOSP 行为，Release 仅做 R8 优化与资源压缩，不做标识符混淆。

## 文档地图

| 想了解 | 看这里 |
|---|---|
| 详细构建 / 部署踩坑记录 | [docs/PITFALLS.md](docs/PITFALLS.md) |
| 架构决策记录（ADR） | [docs/adr/](docs/adr/) |
| 深度调研（SysUISdk 生成、R8 闭包、aconfig 改名机制等） | [docs/architecture/](docs/architecture/) |
| 实时开发状态（内部） | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| 项目内部开发规则 | [AGENTS.md](AGENTS.md) |
| 文档索引与维护规则 | [docs/README.md](docs/README.md) |

## License

Apache License 2.0，与 AOSP 一致（源码主体来自 AOSP SystemUI）。
