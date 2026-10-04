# SystemUI-Gradle 开发规则

本文件是项目约定入口；用户当前指令优先于这些约定。按任务需要阅读
[使用说明](README.md)、[故障排查](docs/PITFALLS.md)和[设计索引](docs/README.md)，
不要求读取历史任务记录或固定的交接顺序。

## 工作方式与文档

- 中文交流；先说明计划，再开发。复杂任务可按需写计划，不要求每个步骤新建文档。
- **只在使用方式、现行设计或重要限制变化时，更新对应说明。** 不维护常驻进度、
  交接、编排状态或错误数台账，不要求每次提交创建 issue 或同步多份文档。
- `docs/issues/` 和按日期命名的调研是历史证据，不因新版本或新测试结果持续更新，
  其中的旧任务限制和待办不构成当前指令。CONV 授权、资源来源等独有依据仍须保留。
- 重要决策仅在同时满足“难以反转、缺乏上下文会令人困惑、有真正权衡”时写 ADR。
- **规则 I（向前推进）**：错误数是诊断信息，不是提交、回滚或审批门槛。源码补全、
  依赖纠正和模块校准可提交诚实的中间态，不要求每次提交都能完整构建。
- 按变更选择有效验证，不要求每次修改都编译。报告实际命令及结果；未运行就说未运行，
  构建成功不等于设备运行通过。验证结果可以直接在对话中报告。
- 聚焦、增量提交，commit message 用英文；及时提交及按用户授权推送。
- 参考用户的 `CarSystemUIGradle` 项目；不熟悉的 API 查官方文档。

## 源码与资源边界

### 规则 P：无 stub

不创建 Java/Kotlin stub、伪造资源或用空实现满足编译。所有代码、资源来自真实上游。
若确需临时 stub，必须先停止并请求用户明确授权；获准后标注
`// TODO: temporary stub, replace with real impl`，保留替换依据，不能自行启用此退路。

### 规则 S / F：SystemUI 用源码，外部 AOSP 用产物

| 层 | 判定 | 引入方式 |
|---|---|---|
| SystemUI 自有 | 模块定义在 `frameworks/base/packages/SystemUI/**/Android.bp` | 源码依赖，不用 prebuilt 替代 |
| 外部 AOSP 特有 | 不属于 SystemUI、无兼容官方坐标或被 AOSP fork | 无资源用 JAR，有资源用 AAR |
| 标准第三方 | Google Maven / Maven Central 有兼容、未被 fork 的产物 | 官方坐标，经 `gradle/libs.versions.toml` 管理 |

- 优先使用官方坐标，避免把标准 androidx/Compose 等重新打成本地 JAR/AAR；维护依赖时
  回查官方等价物，不能因历史原因永久保留本地形式。版本升级及重要依赖决策先与用户沟通。
- 官方版本不满足 AOSP 时，核对 `Android.bp` 并向用户说明问题，不擅自打包替代。
- 源码化时移除同类 prebuilt，避免重复类。非 SystemUI 的 framework 源码/AIDL 不复制进工程。
- 隐藏 API、私有资源或 framework AIDL 声明缺失时，修正 SysUISdk 生成器或对应 JAR，
  而非复制 framework 源码。例如 `IRemoteCallback` 应由生成器补入 `framework.aidl`。

### 规则 C / R：完整对齐及资源来源

- SystemUI 相关源码、AIDL、资源与对应 AOSP 目录**不漏不多**：缺的补齐，多的移除。
- SystemUI 原始资源优先从 AOSP 镜像消费；外部库资源通过原始 AAR 引入。
  不凭空生成同名资源，不为适配 AAPT2 擅自去重、合并、改写资源。
- 优先通过 sourceSets、模块和依赖配置解决构建差异。确需修改镜像源码/资源时，先获得
  用户授权，并按 [ADR 0004](docs/adr/0004-conv-markup-and-alignment-discipline.md)
  使用 `CONV_ADD` / `CONV_DEL` / `CONV_MOD` 与 BEGIN/END 标记，保留原内容。
- 打标前运行 `tools/check_source_alignment.py --strict`，确保 MISSING / MISPLACED / EXTRA
  全为 0。strict 不拦 MODIFIED；MODIFIED 必须与 CONV 授权/来源记录人工对账。
- 文档清理不得删除仍支撑 CONV 改动的独有依据，也不得顺带修改镜像源码或资源。

## 模块与产物

### 规则 B：按 Android.bp 的语义对齐

`Android.bp` 是生产 source roots、资源 owner、static/libs/plugins 语义的依据，
但**不要求每个 Soong target 对应一个 Gradle module**。模块边界按 R namespace、
多消费者、外部 API、处理器/AIDL 工具链及依赖环确定。

- `:app` 负责签名、最终 APK 打包及 manifest 合并壳，无独立 SystemUI 源码。
- `SystemUIApplication` / `SystemUIService` 留在 `:SystemUI-core`；完整 manifest 与
  Dagger 根组件属于 `:SystemUI-application`。
- app 清单须显式保留 `sharedUserId` 等不会从 library 自动合入的属性；“最小壳”
  不等于删除这些必要声明。
- `com.android.systemui`（application manifest 展开）与 `com.android.systemui.res`
  （资源 R 引用）是承重 namespace；其他含资源模块优先镜像 AOSP manifest package，
  无运行时作用的 namespace 才是 Gradle 占位。详见
  [namespace 设计](docs/architecture/2026-08-29-namespace-design.md)。
- 模块图以 `settings.gradle.kts` 和各模块 build 文件为准；模块职责见 README。
  设计依据见 [ADR 0003](docs/adr/0003-app-module-aligns-aosp-bp.md) 与
  [Gradle 构建设计](docs/architecture/gradle-build.md)。

### AAR / JAR 交付

- Maven 是获取/交付渠道，不是第四种产物。`libs/maven/` 只交付 AAR + POM，纯代码
  JAR 直接放 `libs/`（已有 tracinglib 位于 `libs/prebuilts/`）。
- 外部资源库先验证直接 AAR 消费；确认资源、类或依赖冲突后，再借本地 Maven 的标准
  元数据解析解决。不能仅为 catalog 统一而新增 Maven 层。已有多 consumer 族及已确认
  冲突的族保留本地 Maven 路径，如 SettingsLib、WindowManager-Shell、animationlib。
- 已获准直接消费的族：WifiTrackerLib、iconloader、setupcompat、LowLightDreamLib、
  TraceurCommon/Traceur-res、dynamiccolors、personalcontext_ace_visualizer/client、
  SerialPortAccessDialog。沿用现有交付边界；新增例外或合并产物先讨论。
- AAR 由 `tools/package_aosp_aar.py` 生成至 `libs/aars/`，需要本地 Maven 时再由
  `tools/install_aar_to_maven.py` 安装并通过 catalog 引用。POM 默认骨架；SettingsLib
  按 [ADR 0005](docs/adr/0005-local-maven-transitive-poms.md) 携带真实 per-target 依赖边。
- 本地 Maven AAR 内容变化必须升 version 并退役旧坐标，禁止同版本覆盖。
- `libs/` 的 JAR、AAR、本地 Maven 产物全部提交 Git，确保克隆后无需重新生成依赖。
- 只有需要再生时才运行打包工具；产物来源及映射以 `tools/package_*.py` 为准，
  坐标以 catalog 为准，不另维护逐文件文档清单。

### SysUISdk 与 R8

- Android 模块使用 `compileSdkPreview = "SysUISdk"`。SDK 路径由 AGP 解析；JVM 模块
  需要平台类时复用 AGP SDK provider，不自行硬编码机器路径。
- 通过单入口 `uv run python tools/build_sysuisdk.py --aosp-root "$AOSP_ROOT"`
  从只读官方 platform 和真实 AOSP 产物事务性生成 SDK；已有生成器自有输出可用
  `--replace`。输入映射以生成器为准，不手工修 SDK。
- SDK 提供隐藏 API、framework-res 私有资源 ID 和隐藏 AIDL 声明。
  `framework.jar` 只补代码签名，不能替代 SDK 的资源部分。
- SDK optional bridge 提供真实 library classes；保留本地 JVM 测试，不改写真实
  AOSP 方法体，不把 bridge 当作 APK program input。见
  [ADR 0006](docs/adr/0006-sysuisdk-r8-library-class-bridge.md)。
- 根 build 文件对 JavaCompile 注入 `framework.jar`，**不对 KotlinCompile 注入**，
  避免污染 Compose inline metadata；Kotlin 隐藏 API 由 SysUISdk/AGP classpath 提供。
  内部 flags JAR 应排在 framework.jar 前，避免同名定义遮蔽。
- 使用 AGP 原生 D8/R8 管线，不要求复制 Soong 合并后的优化配置或最终 APK 字节。
  禁止宽泛 `-dontwarn` / keep 掩盖缺依赖；窄域规则须先证明引用类别、作用范围，
  获得用户批准并验证构建/运行。不使用 `@Suppress("DEPRECATION")` 等绕过写法。
- aconfig 改写按 [ADR 0008](docs/adr/0008-pre-dex-aconfig-reference-rewrite.md)
  在 pre-D8/R8 对所有类做仅引用改写；保留 this_class/self-reference，禁止把 hidden 类
  打包进 APK，禁止 post-D8/DEX 改写。

## 工具与验证

- `tools/` 脚本一律 Python，不新增 shell 脚本；系统 CLI 的直接调用不受此限。
  普通 APK 构建使用 JVM/AGP 工具链，不引入 Python/uv 构建依赖。
- Python 一律 `uv run`，安装依赖用 `uv add`；不用 `pip` / `uv pip`。
- AOSP 根路径唯一配置来源是 `tools/aosp_paths.py`；使用显式参数或 `AOSP_ROOT`，
  默认值是仓库的同级 `aosp` 目录，脚本内不散落机器绝对路径。
- `.venv`、`__pycache__`、构建和临时验证产物通过 `.gitignore` 排除。
- 同一机器上的重型 Gradle/Soong 构建串行执行，先确认没有其他任务占用；只读核查可并行。
- 构建 APK 后运行对应变体的指令级引用门禁；设备部署需再单独验证，不能用静态门代替。

```bash
./gradlew :app:assembleDebug
./gradlew :app:assembleRelease
./gradlew :buildSrc:test
uv run pytest tools/tests -q
uv run python tools/check_source_alignment.py --strict  # 需匹配的 AOSP 树
uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/debug/app-debug.apk
uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/release/app-release.apk
```

出现 unresolved reference 时：查 AOSP 定义与 bp → 查 SDK/实际依赖 JAR 的类集 →
用 `javap` 核实成员 → 检查同名源码及 classpath 遮蔽；不要凭符号名创建替代实现。

## 规则 H：需要用户决策时停止

以下情况先说明原因并询问用户：需要 stub、修改镜像资源、伪造资源、新增 shell 脚本，
需要产品/架构选择、修改核心规则，或可行方案都失败。文档精简不等于放松这些技术边界。

使用 herdr 时：一个 worker/reviewer 一个独立 tab，不做同 tab split；模型由用户在
派发时指定，worker 独立核实 session 的 provider/modelId。协调共享文件与重型构建，
不另建编排台账。编写 skill 只描述当前有效内容，不要求说明已删除的 skill。
