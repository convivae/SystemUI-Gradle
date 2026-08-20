# SystemUI-Gradle

**[English](README.en.md)** | 中文

把 AOSP `frameworks/base/packages/SystemUI` 从 Soong/Blueprint 构建体系中完整剥离出来，
移植为一个**独立、自包含的 Gradle 工程**——不依赖 AOSP 源码树即可编译真实 SystemUI 源码，
同时保持与 AOSP 的源码、资源 1:1 对齐，随时可以回流。

> **状态**：活跃开发中。debug APK 已可构建；release（R8 全程序优化）正在逐批收口。
> 实时状态见 [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)。

---

## 为什么做这个项目

AOSP 的 SystemUI 正常只能在 AOSP 源码树内用 Soong 编译。这带来几个痛点：

- 无法用 Android Studio / Gradle 快速迭代；
- 无法脱离整个 AOSP checkout 独立版本化、评审、分支管理；
- 想基于 SystemUI 做二次开发的团队，被迫维护一整套 AOSP 构建环境。

本项目把 SystemUI 完整搬进纯 Gradle 构建（Gradle 9.5 + AGP 9.3.1 + Kotlin 2.2.10），
所需的一切依赖（隐藏 API、aconfig flags、AOSP 库、资源）都以真实产物的形式收进仓库，
`git clone` 之后直接构建，**不再回头碰 AOSP 树**。

同方法论的姊妹项目：[CarSystemUIGradle](../CarSystemUIGradle)（Car SystemUI 的同款移植）。

## 当前状态速览（2026-08-20）

| 维度 | 状态 |
|---|---|
| 构建链 | Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10（AGP `builtInKotlin`）· KSP 2.2.10-2.0.2 · Dagger 2.59.2 · Compose 1.11.4 |
| 自定义 SDK | SysUISdk 完全可复现（`tools/build_sysuisdk.py --apply` 声明式生成，含隐藏 API / 私有资源 / AIDL 声明） |
| 编译 | KSP 0 错误 · core Kotlin 0 错误 · core javac 0 错误 |
| 单元测试 | **171 个全部通过** |
| **Debug APK** | ✅ `:app:assembleDebug` 成功产出（每批改动的硬门禁） |
| Release APK | 🚧 R8 配置已对齐 AOSP（core 零混淆 / app 统一 R8+shrinkResources）；运行时闭包缺失从 140 收敛至 **88**，逐批清零中 |
| 装机验证 | ⏳ 待 release 打通后进行（模拟器/真机方案已记录在案） |

## 已经做了什么

- **13 个 Gradle 模块**，边界语义严格对齐 AOSP `Android.bp`（ADR 0003）；SystemUI 自有代码全部源码化（规则 S：不用 jar 顶替），非 SystemUI 的 AOSP 产物一律 jar/AAR 引入（规则 F：不偷拷 framework 源码）
- **源码/资源与 AOSP 逐一对齐**（规则 C：不漏不多），有自动化对齐校验工具；任何必要的源码改动以 CONV 标记追溯（ADR 0004）
- **SysUISdk 可复现流水线**：隐藏 API、framework 私有资源（`androidprv`）、@hide AIDL 全部由脚本声明式补齐，禁止手工 patch
- **全套依赖治理**：AOSP 库由 `tools/package_aosp_aar.py` 确定性打包为 AAR（17 个），经本地 Maven 仓 + version catalog 统一管理；第三方库一律官方 Maven 坐标并升级到最新兼容版；`libs/` 全部提交入 git
- **Release 对齐 AOSP**：以 Soong 实际行为为基准，core 零 ProGuard、app 统一 R8 + shrinkResources
- **R8 运行时闭包审计与收口**：140 项缺失分类为 A（program/runtime）/B（classpath）两类，按批清零：140 → 126 → 119 → 109 → 106 → **88**

## 正在做什么

- **R8 闭包清零（88 → 0）**：当前批次为 Traceur 双 AAR（Batch 4C）；之后是最大的一块 SettingsLib（74 项），再之后是 platform classpath 桥接（B 类）
- 闭包归零后：完整 `:app:assembleRelease`（R8 + 资源收缩 + 签名）
- 模拟器/真机装机验证（方案见 `docs/issues/2026-08-20-device-emulator-validation-plan.md`）

## 模块结构

```
SystemUI-Gradle/
├── app/                        # APK 入口（无独立源码；manifest、签名、打包）
├── SystemUI-core/              # 主模块：SystemUIApplication、src + compose + pods
├── SystemUI-res/               # 独立资源 namespace（res / res-keyguard / res-product）
├── SystemUI-common/            # Common + Log + shared-utils
├── SystemUI-animation/         # PlatformAnimation + Shader(surfaceeffects)
├── SystemUI-plugin-core/       # Plugin 运行时 API（JVM）
├── SystemUI-plugin-processor/  # Plugin 注解处理器（构建期）
├── SystemUI-plugin/            # PluginLib 运行时（含 bcsmartspace）
├── SystemUI-unfold/            # Unfold（KSP 跑 Dagger）
├── SystemUI-customization/     # Customization（含 res）
├── SystemUI-shared/            # Shared + keyguard（含 aidl + res）
├── SystemUI-shared-biometrics/ # Biometrics（独立 R namespace）
├── SystemUI-compose/           # Compose Core + Scene
├── libs/                       # 全部预置产物，提交入 git
│   ├── framework.jar           # AOSP framework（含 @hide API）
│   ├── *-flags.jar             # aconfig 生成的 flags 类
│   ├── aars/                   # 17 个 AOSP 产物 AAR（SettingsLib、WM-Shell、iconloader…）
│   └── maven/                  # 本地 Maven 仓（AAR + POM，经 catalog 引用）
├── tools/                      # Python 工具链（AAR 打包、SDK 生成、对齐校验…）
└── docs/                       # 状态、计划、踩坑、issue 记录、ADR
```

`SystemUI-core/src/` 与 AOSP `frameworks/base/packages/SystemUI/src/` 逐路径对应；
`SystemUI-res/res*` 与 AOSP 对应资源目录 1:1（详见 `AGENTS.md` §3.3）。

## 依赖是怎么解决的（无 stub 原则）

AGP 官方 SDK 会剥离 `@hide` API 和 aconfig 生成的类，SystemUI 大量使用这两者。
本项目**不用任何手写 stub**，而是用三类真实产物补齐：

1. **官方 Maven 坐标**（优先）：androidx / Compose / Dagger / protobuf 等第三方库直接用公网最新兼容版
2. **本地 JAR**：无资源的 AOSP 纯代码产物（framework.jar、aconfig flags jar 等）
3. **AAR**：含资源的 AOSP 库（先直接引入，确认冲突后才入本地 Maven 仓）

所有 AAR/JAR 均由 `tools/` 下脚本从 AOSP Soong 产物**确定性**打包，可复现、可审计。

## 构建

### 环境要求

- Linux x86_64 · JDK 21
- Android SDK + 安装好的 **SysUISdk** 平台（`platforms/android-SysUISdk`，由 `tools/install_sdk.py` / `build_sysuisdk.py` 生成）
- 仅当需要重新生成 AOSP 产物时，才需要本地 AOSP 树

### 常用命令

```bash
./gradlew :app:assembleDebug            # 构建 debug APK（当前硬门禁）
./gradlew :SystemUI-core:compileDebugKotlin
python3 -m unittest discover -s tools/tests   # 工具链测试（171 个）
```

`libs/` 已全部提交入 git，**fresh clone 开箱即建**。

## 文档导航

| 想了解 | 看这里 |
|---|---|
| 实时状态快照 | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| 项目规则（无 stub / 对齐纪律 / 求助规则） | [AGENTS.md](AGENTS.md) |
| 阶段计划 | [docs/PLAN.md](docs/PLAN.md) |
| 踩坑记录 | [docs/PITFALLS.md](docs/PITFALLS.md) |
| 架构决策记录 | [docs/adr/](docs/adr/) |
| 每日问题/调研记录 | [docs/issues/](docs/issues/) · [docs/architecture/](docs/architecture/) |

## License

Apache License 2.0，与 AOSP 一致。
