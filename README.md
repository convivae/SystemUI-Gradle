# SystemUI-Gradle

**[English](README.en.md)** | 中文

把 AOSP `frameworks/base/packages/SystemUI` 从 Soong/Blueprint 构建体系中完整剥离出来，
移植为一个**独立、自包含的 Gradle 工程**——不依赖 AOSP 源码树即可编译**真实 SystemUI 源码**
（非删减、非 stub），并保持与 AOSP 源码、资源 1:1 对齐，随时可以回流。

> **16 时代里程碑（历史基线）**：Debug 与优化 Release 两个 runtime 均曾在 same-tree x86_64 模拟器上
> 验证通过（2026-08-25/26）。当前项目处于 **Phase C**（AOSP 基线固定到 `android-17.0.0_r1` 后
> 全管线清空重生）：C1/C3/C2/C4a 已完成，**C4b（恢复 `assembleDebug` 编译闭环）进行中**。
> 实时完整状态见 [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)。

---

## 当前状态速览（2026-08-28）

| 维度 | 状态 |
|---|---|
| **Debug 构建** | ⏳ **C4b 进行中**：AOSP-17 重对齐后 `:app:assembleDebug` 尚未恢复绿（16 时代历史基线：DEBUG_RUNTIME_PASS 2026-08-25，APK `e8aad131…`） |
| **Release 构建** | 未跑（归 task074；16 时代历史基线：RELEASE_RUNTIME_PASS 2026-08-26，APK `d3968fb2…`） |
| 构建链 | Gradle 9.5.0 · AGP 9.3.1 · Kotlin 2.2.10（AGP `builtInKotlin`）· KSP 2.2.10-2.0.2 · Dagger 2.59.2 · Compose 1.11.4 · material3 1.5.0-alpha18 · JDK 21 · `compileSdkPreview = "SysUISdk"` |
| 配置解析 | `./gradlew help` / `projects` **BUILD SUCCESSFUL**（16 模块全部识别；C4a 验收） |
| 工具链测试 | `uv run pytest tools/tests/ -q` → **293 passed**（+111 subtests） |
| 源码/资源对齐 | 自动对齐校验 `--strict` exit 0（MISSING / MISPLACED / EXTRA = 0 / 0 / 0；MODIFIED 1 src + 86 res 为白名单 CONV 标记） |
| 产物再生 | `libs/` 全部 107 个产物（jar/AAR/POM）提交入 git 且均可由 `tools/` 脚本从 AOSP-17 确定性再生（见 Quickstart 第 4 步） |

> 成功标准是 **AGP-native functional parity**：SysUISdk 生成的自定义 SDK 必须直接支撑既有
> Debug 与优化 Release 构建并在设备上真实运行，而不是"看起来能编过"。

## 为什么做这个项目

AOSP 的 SystemUI 正常只能在 AOSP 源码树内用 Soong 编译。这带来几个痛点：

- 无法用 Android Studio / Gradle 快速迭代；
- 无法脱离整个 AOSP checkout 独立版本化、评审、分支管理；
- 想基于 SystemUI 做二次开发的团队，被迫维护一整套 AOSP 构建环境。

本项目把 SystemUI 完整搬进纯 Gradle 构建，所需的一切依赖（隐藏 API、aconfig flags、
AOSP 库、资源）都以**真实产物的形式**收进仓库，`git clone` 之后直接构建，
**不再回头碰 AOSP 树**。

同方法论的姊妹项目：[CarSystemUIGradle](../CarSystemUIGradle)（Car SystemUI 的同款移植）。

## 架构

### 模块拓扑（16 个 Gradle 模块，语义对齐 AOSP 17 `Android.bp`）

| 模块 | 职责（对应 Soong target） |
|---|---|
| `:app` | `android_app "SystemUI"`：APK 入口（无独立源码；最小 manifest 合并壳、签名、打包） |
| `:SystemUI-core` | `android_library "SystemUI-core"`：主模块，含 `SystemUIApplication` 等入口类、src + compose + pods |
| `:SystemUI-application` | `android_library "SystemUI-application"`：Dagger 根组件 + 完整 1338 行 AOSP manifest（17 新增） |
| `:SystemUI-res` | 独立资源 namespace（res / res-keyguard / res-product），生成 `com.android.systemui.res.R` |
| `:SystemUI-common` | Common + Log + shared-utils 合并 |
| `:SystemUI-animation` | PlatformAnimationLib（含 res；17 起 surfaceeffects 改 jar 交付） |
| `:SystemUI-plugin-core` | PluginCoreLib runtime API（JVM） |
| `:SystemUI-plugin-processor` | PluginAnnotationProcessor（构建期，不进 APK） |
| `:SystemUI-plugin` | SystemUIPluginLib runtime（含 bcsmartspace） |
| `:SystemUI-unfold` | SystemUIUnfoldLib（KSP 跑 Dagger） |
| `:SystemUI-customization` | SystemUICustomizationLib（含 res） |
| `:SystemUI-clocks-common` | SystemUIClocks-CommonLib（含 res；17 新增，被 customization 消费） |
| `:SystemUI-shared` | SystemUISharedLib + keyguard 合并（含 aidl + res） |
| `:SystemUI-shared-biometrics` | biometrics（独立 R namespace，被 Settings 消费） |
| `:SystemUI-compose` | Compose Core + Scene 合并 |
| `:SystemUI-accessibility-floatingmenu-res` | AccessibilityFloatingMenu-res（res-only；17 新增，被 SystemUI-res 消费） |

（C4b 进行中正按 17 bp 追加 `:SystemUI-utils-kairos` tier① 源码模块；完整拓扑 owner 见
[AGENTS.md](AGENTS.md) §3.1。）

`SystemUI-core/src/` 与 AOSP `frameworks/base/packages/SystemUI/src/` 逐路径对应；
`SystemUI-res/res*` 与 AOSP 对应资源目录 1:1（详见 [AGENTS.md](AGENTS.md) §3.3）。

### 依赖解决（无 stub 原则）

AGP 官方 SDK 会剥离 `@hide` API 和 aconfig 生成的类，SystemUI 大量使用这两者。
本项目**不用任何手写 stub**，只用三类真实产物：

1. **官方 Maven 坐标**（优先）：androidx / Compose / Dagger / protobuf 等第三方库直接用公网最新兼容版
2. **本地 JAR**：无资源的 AOSP 纯代码产物（framework.jar、aconfig flags jar 等）
3. **AAR**：含资源的 AOSP 库（先直接引入 `libs/aars/`，确认冲突后才入本地 Maven 仓 `libs/maven/`）

**SysUISdk** 是本项目自定义的 `compileSdkPreview` 平台：由单入口生成器
`tools/build_sysuisdk.py` 从只读官方 SDK 平台 + 已构建的 AOSP `out/` 产物**事务性生成**，
一次性补齐隐藏 API 字节、framework 私有资源（`@*android:` ID）与 @hide AIDL 声明。
所有 AAR/JAR 均由 `tools/` 下脚本从 AOSP Soong 产物**确定性**打包，可复现、可审计。

## AOSP 版本基线

当前基线为 AOSP release tag **`android-17.0.0_r1`**（Phase C / C1，2026-08-27 原地切换并全量构建；
frameworks/base `94b4c163b`，manifest `5bc9a7ce`，1084 projects）：

- 源码/资源已按 17 树全量重对齐（C3，对齐门 `--strict` exit 0）；`libs/` 产物已全部从 17 树脚本再生（C2）。
- 16 时代验证所用的 `main` 分支快照仍归档于
  [`docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml`](docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml)
  （1042 projects，说明见 [`docs/aosp-pinning/README.md`](docs/aosp-pinning/README.md)）。
- **17 基线的编译/双 runtime 重验与 tag 收口仍在进行**（C4b/C5/C6，见 [docs/PLAN.md](docs/PLAN.md)
  与 [docs/adr/0007-phase-c-clean-regen-release-tag.md](docs/adr/0007-phase-c-clean-regen-release-tag.md)）；
  README 的正式版本声明将在 C6 统一更新。

## 从零复现（Quickstart）

端到端共 7 步。`libs/` 已全部提交入 git，**fresh clone 无需第 1–4 步即可直接进入第 5 步构建**；
第 1–4 步仅当需要从 AOSP 重新生成全部产物时执行。每步标注当前验证状态。

### 环境要求（实测数据）

| 项 | 要求 |
|---|---|
| 操作系统 | Ubuntu Linux（x86_64） |
| 磁盘 | **≥400 GiB**：AOSP 树实测 418G（含 `out/` 187G；含历史实验产物，干净单产品构建预计 ~300G） |
| 内存 | **≥32 GiB**：本机 30Gi RAM + 8G swap 紧张可行（AOSP 构建须 `-j4`）；模拟器另需 ~4.5 GiB 常驻 |
| KVM | 必须（same-tree x86_64 模拟器；用户需在 `kvm` 组） |
| JDK | 17+（项目工具链实测 JDK 21） |
| Python | Python 3 + [uv](https://docs.astral.sh/uv/)（脚本一律 `uv run`，禁 pip） |
| Android 工具 | adb；可选 scrcpy（headless 模拟器看画面） |

Gradle wrapper 自带 9.5.0（腾讯镜像分发），`settings.gradle.kts` 已内置腾讯云/阿里云
Maven 镜像，国内网络环境开箱即用。

### 步骤

**1. 下载 AOSP（repo init + tag checkout）** — *已按 `android-17.0.0_r1` 执行（C1）*

```bash
repo init -u https://android.googlesource.com/platform/manifest -b android-17.0.0_r1
repo sync -d -c -j4
# 16 时代验证快照归档：docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml
```

**2. 编译 AOSP** — *已验证（C1：17 树全量 `m` 构建成功，2h35m；产物脚本与模拟器镜像均消费此 `out/`）*

```bash
cd <aosp-root> && . build/envsetup.sh
lunch sdk_phone64_x86_64-trunk_staging-userdebug
m -j4        # 产物含 out/target/product/emu64x/ 模拟器镜像
```

**3. 生成 SysUISdk** — *已验证（Task 045，16 时代基线；17 树重建排在 C5 前，八输入已验存）*

```bash
uv run python tools/build_sysuisdk.py --aosp-root <aosp-root>
# 输出 <sdk-root>/platforms/android-SysUISdk；详见 docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md
```

**4. 生成 libs/ 产物**（仅重新生成时需要）— *已验证（C2：104 删 → 7 脚本从 AOSP-17 再生 102 文件；C4a 新增 5 个产物，当前共 107 文件，全部脚本产出）*

```bash
uv run python tools/package_aosp_aar.py --all          # 30 个 AAR → libs/aars/
uv run python tools/install_aar_to_maven.py            # 安装为本地 Maven AAR（23 族，全部 2.0.0）→ libs/maven/
uv run python tools/package_aconfig_jars.py --all      # aconfig flags jar（含 12 族合并）
uv run python tools/package_misc_jars.py --all         # misc jar（framework.jar、surfaceeffects×3 等）
uv run python tools/package_compilelib_jars.py         # compilelib debug/release jar
uv run python tools/package_monet_jar.py               # monet jar
uv run python tools/package_viewcapture_motiontool_jars.py
```

**5. Gradle 构建** — *16 时代已验证；17 重对齐后 `:app:assembleDebug` 编译闭环（C4b）进行中，尚未恢复绿*

```bash
./gradlew :app:assembleDebug      # Debug APK（C4b 目标门）
./gradlew :app:assembleRelease    # 优化 Release APK（归 task074）
uv run pytest tools/tests/ -q     # 工具链测试（293 passed）
```

**6. 启动模拟器** — *16 时代已验证；17 镜像重拉归 C5*；完整命令与环境变量（`ANDROID_PRODUCT_OUT` / `ANDROID_BUILD_TOP`
/ `ANDROID_TMP`、日志文件预创建等坑）见 runbook：
[docs/issues/2026-08-26-emulator-relaunch-runbook.md](docs/issues/2026-08-26-emulator-relaunch-runbook.md)

**7. 部署验证** — *16 时代已验证（Debug `e8aad131…` / Release `d3968fb2…` 双门通过）；17 基线重验归 C5*；staged 部署
规程（root → disable-verity → 分阶段 push + 设备端 sha256 门禁 → 原子替换 → 清缓存 →
reboot，及已知坑）见 [docs/PITFALLS.md](docs/PITFALLS.md) §14。

## 文档地图

| 想了解 | 看这里 |
|---|---|
| 实时状态快照（构建矩阵、版本、依赖产物、证据） | [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) |
| 5 分钟接手导航 | [docs/HANDOFF.md](docs/HANDOFF.md) |
| 项目规则（无 stub / 对齐纪律 / 求助规则） | [AGENTS.md](AGENTS.md) |
| 未完成路线与完成条件 | [docs/PLAN.md](docs/PLAN.md) |
| 踩坑记录（含设备/模拟器部署规程 §14） | [docs/PITFALLS.md](docs/PITFALLS.md) |
| 架构决策记录（ADR） | [docs/adr/](docs/adr/) |
| 深度调研 | [docs/architecture/](docs/architecture/) |
| 每日问题记录 | [docs/issues/](docs/issues/) |
| 文档索引与生命周期 | [docs/README.md](docs/README.md) |
| 多 worker 编排（herdr） | [docs/orchestration/](docs/orchestration/) |

## License

Apache License 2.0，与 AOSP 一致（源码主体来自 AOSP SystemUI）。
