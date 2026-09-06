# SystemUI-Gradle

**[English](README.en.md)** | 中文

[![AOSP baseline](https://img.shields.io/badge/AOSP-android--17.0.0__r1-3ddc84?logo=android&logoColor=white)](https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1)
[![Build verified](https://img.shields.io/badge/Debug%20%2B%20Release-verified-brightgreen)](docs/CURRENT_STATE.md)
[![Gradle 9.5.0](https://img.shields.io/badge/Gradle-9.5.0-02303a?logo=gradle&logoColor=white)](gradle/wrapper/gradle-wrapper.properties)
[![AGP 9.3.1](https://img.shields.io/badge/AGP-9.3.1-3ddc84?logo=android&logoColor=white)](gradle/libs.versions.toml)
[![Kotlin 2.2.10](https://img.shields.io/badge/Kotlin-2.2.10-7f52ff?logo=kotlin&logoColor=white)](gradle/libs.versions.toml)

本项目把 AOSP `frameworks/base/packages/SystemUI`——Android 的**状态栏、通知栏 / 快捷设置、
锁屏（Keyguard）、最近任务概览**等系统界面的完整真实源码——从 Soong 构建体系中移植出来，
做成一个**独立、自包含的 Android Gradle 工程**。它可以像普通 app 一样用 Android Studio /
Gradle 构建，产出可安装的 Debug 与 Release APK，并已在同版本 AOSP 17 模拟器上真实验证运行。

## 亮点

- **真实源码，非删减、非 stub**：SystemUI 自有代码全部以源码形式编译，资源与 manifest
  与 AOSP 逐文件对齐，改动可随时回流上游；
- **17 个 Gradle 模块**：模块边界按 AOSP `Android.bp` 的语义划分，代码路径与 AOSP
  一一对应，阅读与导航零成本；
- **SysUISdk**：自定义编译平台，补齐标准 Android SDK 缺失的 `@hide` API、framework
  私有资源与隐藏 AIDL 声明（已发布到 [GitHub Releases](https://github.com/convivae/SystemUI-Gradle/releases)，
  也可从 AOSP 产物确定性再生）；
- **依赖干净**：androidx / Compose / Dagger 等第三方库一律使用官方 Maven 坐标；
  AOSP 产物以 jar / AAR 形式提交入库，且每个都能用 `tools/` 下的脚本确定性再生——
  没有手工上传的"魔法文件"，也没有任何手写 stub；
- **Release 支持**：R8 优化 + 资源压缩，产物与 AOSP 同为不混淆的平台签名 APK。

## 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | Ubuntu Linux（x86_64）；跑模拟器时用户需在 `kvm` 组 |
| JDK | 21+（Gradle daemon 实测 25，编译 toolchain 为 21） |
| 内存 | 仅构建本工程约 16 GiB 可行（Gradle `-Xmx16g`）；同时构建 AOSP 建议 ≥ 30 GiB |
| 磁盘 | 仅构建本工程 ≈ 20 GiB；完整复现（含 AOSP 树）≥ 400 GiB |
| Android SDK | 常规即可；自行再生 SysUISdk 时才需要官方 `platforms/android-37.0` 作为只读基础平台 |
| Python | 3.x + [uv](https://docs.astral.sh/uv/)（脚本一律 `uv run`） |
| 工具 | unzip、sha256sum；adb；可选 repo（仅 AOSP 路径）、scrcpy（查看无头模拟器画面） |

> 构建 APK **不需要** AOSP 源码树——仓库内的 jar / AAR 依赖已全部提交，SysUISdk 以
> zip 形式发布。只有需要自行再生 SysUISdk / libs 产物，或构建部署用模拟器镜像时，
> 才需要 AOSP 17 树（见第 3 步）。

## 快速开始

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

**方式 A（推荐）：安装已发布的 r1**

从 [SysUISdk r1 Release](https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1)
下载 zip 和同名 `.sha256`，在下载目录中校验后安装到 Android SDK：

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
`ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`。若已有
`android-SysUISdk` 目录，请先明确删除或重命名，不要新旧混装。

**方式 B：从 AOSP 自行生成**——先完成第 3 步，再执行：

```bash
uv run python tools/build_sysuisdk.py \
  --aosp-root "$AOSP_ROOT" \
  --sdk-root "$ANDROID_SDK_ROOT"

# 从新的 AOSP 产物重新生成已有 SysUISdk 时加 --replace
```

如果 Gradle 报 `Failed to find Platform SDK with path: platforms;android-SysUISdk`，
说明第 2 步尚未完成，或 SysUISdk 解压位置与 Gradle 使用的不是同一个 Android SDK 目录。

### 3.（可选）准备 AOSP 17 构建产物

仅以下情况需要：用方式 B 自行生成 SysUISdk、再生 `libs/` 产物、或构建部署用模拟器
镜像。如果走方式 A 且不需要跑模拟器，直接跳到第 4 步。

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

两个变体都使用仓库内提交的平台签名 keystore（`keystore/platform.keystore`，源自 AOSP
开发测试密钥），无需额外配置即可产出可部署的签名 APK。

## 在模拟器上运行

SystemUI 是平台签名应用并调用隐藏 API，因此部署目标必须是**同一 AOSP 基线**的构建
（本工程在自建的 `sdk_phone64_x86_64` 模拟器镜像上验证；不能装到普通商用手机或官方
模拟器镜像）。

用第 3 步产出的镜像启动模拟器（`ANDROID_PRODUCT_OUT="$AOSP_ROOT/out/target/product/emu64x"
emulator ...`，完整参数见
[模拟器启动 runbook](docs/issues/2026-08-26-emulator-relaunch-runbook.md)），然后替换系统
SystemUI：

```bash
adb root && adb disable-verity && adb reboot   # 等开机后：
adb root && adb remount
adb push app/build/outputs/apk/debug/app-debug.apk /system_ext/priv-app/SystemUI/SystemUI.apk
adb reboot
```

部署细节与已知问题（校验、overlay 只读、缓存清理等）见
[docs/PITFALLS.md](docs/PITFALLS.md)。

## 二次开发指南

**改代码**：SystemUI 源码在 `SystemUI-core/src/`（与 AOSP `packages/SystemUI/src/`
逐路径对应），各子库在对应 `SystemUI-*` 模块。直接改、直接构建即可——没有代码生成、
没有中间层。关键入口：

- `:SystemUI-core` — `SystemUIApplication` 等入口类与主体逻辑；
- `:SystemUI-application` — Dagger 根组件与完整 manifest。

**改资源**：资源集中在 `SystemUI-res/res*`（与 AOSP `res/`、`res-keyguard/`、
`res-product/` 1:1），代码中通过 `com.android.systemui.res.R` 引用。

**模块结构**：模块划分与合并严格按 AOSP `Android.bp` 的语义（详见
[ADR 0003](docs/adr/0003-app-module-aligns-aosp-bp.md)）。模块地图：

| 模块 | 职责（对应 AOSP Soong target） |
|---|---|
| `:app` | APK 入口：签名、打包、manifest 合并壳（`android_app "SystemUI"`） |
| `:SystemUI-core` | 主模块：入口类、src + compose + pods |
| `:SystemUI-application` | Dagger 根组件 + 完整 AOSP manifest |
| `:SystemUI-res` | 资源模块（res / res-keyguard / res-product） |
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

**保持与上游同步**：本工程刻意不做"fork 式"改写——源码和资源与 AOSP 保持逐文件对齐，
由 `tools/check_source_alignment.py --strict` 自动校验（缺失 / 错位 / 多余文件均为 0）。
你自己的修改就是普通 git 历史，可以随时 rebase / cherry-pick 回 AOSP。

**升级 AOSP 基线**：换 tag 后按顺序执行——重对齐源码（`check_source_alignment.py`）、
用 `tools/package_*.py` 再生全部 jar / AAR、重建 SysUISdk、重建 APK 并跑部署验证。
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
  kotlinx-coroutines 上限 1.10.2（1.11 的新 overload 破坏 AOSP 源码）。升级依赖前请先查阅
  [docs/PITFALLS.md](docs/PITFALLS.md)。
- **Release 不混淆**：对齐 AOSP 行为，Release 仅做 R8 优化与资源压缩，不做标识符混淆。

## 项目结构

```
SystemUI-Gradle/
├── app/                      # APK 打包入口（签名、manifest 合并壳）
├── SystemUI-*/               # 17 个源码/资源模块（见上方模块地图）
├── libs/                     # AOSP 产物依赖（jar / AAR / 本地 Maven，均由脚本再生）
├── tools/                    # Python 构建/校验工具（SysUISdk 生成、产物打包、对齐校验等）
├── keystore/                 # 平台签名 keystore（AOSP 开发测试密钥）
├── release/                  # SysUISdk 发布物（LICENSE / NOTICE / 打包脚本）
├── docs/                     # 项目文档（见下节）
└── gradle/                   # wrapper 与版本 catalog
```

## 文档

| 想了解 | 看这里 |
|---|---|
| 详细构建 / 部署踩坑记录 | [docs/PITFALLS.md](docs/PITFALLS.md) |
| 文档索引与导航 | [docs/README.md](docs/README.md) |
| 实时开发状态 | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| 架构决策记录（ADR） | [docs/adr/](docs/adr/) |
| 深度调研报告 | [docs/architecture/](docs/architecture/) |

## License

SystemUI 的 AOSP 来源代码（Apache License 2.0，Copyright The Android Open Source
Project）与本项目自有代码按 Apache License 2.0 提供。单独发布的 SysUISdk zip 还包含
受 Android SDK License Agreement 约束的官方 SDK 底座文件；下载或使用前请阅读
[`release/sysuisdk/NOTICE`](release/sysuisdk/NOTICE) 与
[Android SDK Terms](https://developer.android.com/studio/terms)。
