# SystemUI-Gradle

**[English](README.en.md)** | 中文

[![AOSP baseline](https://img.shields.io/badge/AOSP-android--17.0.0__r1-3ddc84?logo=android&logoColor=white)](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1)
[![Build verified](https://img.shields.io/badge/Debug%20%2B%20Release-verified-brightgreen)](docs/CURRENT_STATE.md)
[![Gradle 9.5.0](https://img.shields.io/badge/Gradle-9.5.0-02303a?logo=gradle&logoColor=white)](gradle/wrapper/gradle-wrapper.properties)
[![AGP 9.3.1](https://img.shields.io/badge/AGP-9.3.1-3ddc84?logo=android&logoColor=white)](gradle/libs.versions.toml)
[![Kotlin 2.2.10](https://img.shields.io/badge/Kotlin-2.2.10-7f52ff?logo=kotlin&logoColor=white)](gradle/libs.versions.toml)

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

> 仓库内的 jar / AAR 依赖已经提交，自定义编译平台 `android-SysUISdk` 以 zip 形式发布在
> [GitHub Releases](https://github.com/convivae/SystemUI-Gradle/releases)——
> **clone + 下载一个 zip 即可构建，无需下载 AOSP**。仅当需要自行再生 SysUISdk / libs 产物、
> 或构建部署用模拟器镜像时，才需要 AOSP 17 源码树（见第 3 步的可选分支）。如果看到
> `Failed to find Platform SDK with path: platforms;android-SysUISdk`，说明第 2 步尚未完成，
> 或 SysUISdk 解压位置与 Gradle 使用的不是同一个 Android SDK 目录。

### 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Ubuntu Linux（x86_64）；跑模拟器时用户需在 `kvm` 组 |
| 磁盘 | 仅构建本工程 ≈ 20 GiB；完整复现（含 AOSP）≥ 400 GiB |
| 内存 | 仅构建本工程 16 GiB 可行；AOSP 全量构建 ≥ 32 GiB 推荐 |
| JDK | 17+（实测 21） |
| Android SDK | 常规即可；仅当自行再生 SysUISdk 时才需要官方 `platforms/android-37.0` 作为只读基础平台 |
| Python | 3.x + [uv](https://docs.astral.sh/uv/)（脚本一律 `uv run`） |
| 工具 | unzip、sha256sum；adb；可选 repo（仅 AOSP 路径）、scrcpy（查看无头模拟器画面） |

### 1. 克隆项目并设置路径

以下路径必须替换为本机的**绝对路径**：

```bash
git clone https://github.com/convivae/SystemUI-Gradle.git
cd SystemUI-Gradle

export PROJECT_ROOT="$PWD"
export ANDROID_SDK_ROOT=/absolute/path/to/Android/Sdk
export ANDROID_HOME="$ANDROID_SDK_ROOT"
printf 'sdk.dir=%s\n' "$ANDROID_SDK_ROOT" > local.properties
```

### 2. 获取 SysUISdk（二选一）

**方式 A（推荐）：安装已验收的 r1**

从 [SysUISdk r1 Release](https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1)
下载 zip 和同名 `.sha256`，在下载目录中校验后安装：

```bash
cd "$HOME/Downloads"  # 按实际下载目录调整
sha256sum --check SysUISdk-android-17.0.0_r1-r1.zip.sha256

(
  set -eu
  target="$ANDROID_SDK_ROOT/platforms/android-SysUISdk"
  test ! -e "$target" || {
    echo "ERROR: $target already exists; remove or rename it first." >&2
    exit 1
  }
  mkdir -p "$ANDROID_SDK_ROOT/platforms"
  unzip -q SysUISdk-android-17.0.0_r1-r1.zip 'android-SysUISdk/*' \
    -d "$ANDROID_SDK_ROOT/platforms"
  test -f "$target/android.jar"
)

cd "$PROJECT_ROOT"
```

校验命令必须输出 `SysUISdk-android-17.0.0_r1-r1.zip: OK`。固定 SHA-256 为
`ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`。已有
`android-SysUISdk` 时请先明确删除或重命名，避免新旧文件混合。

**方式 B：从 AOSP 自行生成**——先完成第 3 步，再执行：

```bash
uv run python tools/build_sysuisdk.py \
  --aosp-root "$AOSP_ROOT" \
  --sdk-root "$ANDROID_SDK_ROOT"

# 从新的 AOSP 产物重新生成已有 SysUISdk 时加 --replace
```

### 3.（可选）一次性准备 AOSP 17 构建产物

仅以下情况需要：用方式 B 自行生成 SysUISdk、再生 `libs/` 产物、或构建部署用模拟器镜像。
如果走方式 A 且不需要跑模拟器，直接跳到第 4 步。

```bash
export AOSP_ROOT=/absolute/path/to/aosp
mkdir -p "$AOSP_ROOT"
cd "$AOSP_ROOT"
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -d -c -j4
. build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j"$(nproc)"
cd "$PROJECT_ROOT"
```

### 4. 构建 APK

```bash
# Debug APK → app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:assembleDebug

# 清理 app 后构建 R8 优化 Release APK
# 输出 → app/build/outputs/apk/release/app-release.apk
./gradlew :app:clean :app:assembleRelease
```

可选的工具链验证：

```bash
uv run pytest tools/tests/ -q
uv run python tools/check_aconfig_jarjar_references.py \
  --apk app/build/outputs/apk/release/app-release.apk
```

### 5. 启动模拟器并部署

用第 3 步产出的 `sdk_phone64_x86_64` 镜像启动模拟器
（`ANDROID_PRODUCT_OUT="$AOSP_ROOT/out/target/product/emu64x" emulator ...`，完整参数见
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

SystemUI 的 AOSP 来源代码与本项目自有代码按 Apache License 2.0 提供。单独发布的
SysUISdk r1 还包含受 Android SDK License Agreement 约束的官方 SDK 底座文件；下载或使用前请阅读
[`release/sysuisdk/NOTICE`](release/sysuisdk/NOTICE) 和
[Android SDK Terms](https://developer.android.com/studio/terms)。
