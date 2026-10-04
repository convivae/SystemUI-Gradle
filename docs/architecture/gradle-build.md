# Gradle 构建设计

本工程追求与目标 AOSP 平台的**功能一致性**，而不是重建 Soong 的内部任务图、
完整优化配置或最终 APK 字节。源码/AIDL/资源对齐、真实产物来源、平台运行行为仍是约束。
本说明提取了原 Gradle-native 设计中仍适用的原则；任务派发和迁移进度不属于设计。

## 模块与依赖边界

- SystemUI 自有代码用源码；标准第三方用官方 Maven；外部 AOSP 库用可再生 JAR/AAR。
- `Android.bp` 定义来源和依赖语义，Gradle module 由资源 namespace、处理器/AIDL、
  外部消费者和依赖环决定，不机械地一对一复制 Soong target。
- 外部库按上游库族组织再生入口。一个库族可以含多个 Soong target，也可保留暂时未用的
  类/资源；只按当前 missing symbol 裁切会让下一次升级不断追加碎片。
- 拆分应有具体理由：不同 R namespace、重复类、manifest 冲突、独立 runtime/API
  所有权、工具链或依赖环。已有 target、单条 R8 warning 或“更小”本身不是拆分依据。
- 多消费者或真实传递依赖需要 Maven 元数据时保留本地 Maven；不为了统一写法增加一层
  仓库。现有产物的合并/删除仍需逐族验证及用户批准，原则本身不是批量重构授权。

实际拓扑和版本以 `settings.gradle.kts`、模块 build 文件和
`gradle/libs.versions.toml` 为准。[ADR 0003](../adr/0003-app-module-aligns-aosp-bp.md)
解释模块边界，[ADR 0005](../adr/0005-local-maven-transitive-poms.md)解释 SettingsLib
为何保留 per-target POM 依赖。

## 构建、平台与运行时三种依赖

| 引用类别 | 处理方式 |
|---|---|
| APK 运行时自带代码 | 完整的 program JAR/AAR 或 SystemUI 源码模块 |
| 设备平台提供的代码/API | SDK/platform library classes，只参与编译/分析，不打包进 APK |
| 仅构建/优化器需要的注解或签名 | 先分类，再选窄域且可维护的构建期处理，不自动转为 runtime 依赖 |

SysUISdk 提供隐藏 API、私有资源 ID 和 framework AIDL。它不是所有 R8 missing reference
的默认收容处；新增平台切片要证明来源和目标平台可用性。optional bridge 将真实平台类
提供给 AGP，同时使 mockable 转换及本地 JVM 测试可用，不替换 AOSP 方法体。
见 [ADR 0006](../adr/0006-sysuisdk-r8-library-class-bridge.md)。

## AGP 原生优化

Gradle 调度，AGP 组织 Android 管线；javac/Kotlin 编译代码，AAPT2 处理资源，Debug 用
D8，启用 minify 的 Release 用 R8，并开启资源压缩。`proguard*.flags` 使用 ProGuard
语法但由 R8 消费；实际输入规则以 `app/build.gradle.kts` 为准。Release 保持不混淆。

附加规则来自真实需求：反射/JNI、序列化、插件入口、生成代码契约、依赖 consumer rules
或可复现的 Release 故障。不因 Soong 配置里有某行就照搬。missing reference 先按上表
分类；不可达可选路径的窄域 warning 处置，需要证明不会被实例化、反射、JNI 或支持的
运行路径使用，并经用户批准、构建与运行验证。宽泛 `-dontwarn **` 不是解决方案。

Soong 与 AGP 即使使用同一优化器，program/library inputs、规则、资源图、DEX 布局和
签名元数据仍可能不同。因此“与 Soong APK 字节相等”不是验收要求；同一输入的打包
脚本仍应确定性输出，类和资源来源必须可追溯。

## 两个必要的 AGP 适配

### 合并资源的 androidprv namespace

AGP 合并 values XML 时可能丢掉只出现在属性值中的 `xmlns:androidprv`。
`buildSrc` 的 `PatchAndroidPrvMergedResourcesTask` 在 merge 后、link 前处理：
复制到临时目录，补声明，调用 **AGP 选定的 AAPT2**，传入
`libs/systemui-aconfig-flags.txt`，成功后原子替换已有 `.arsc.flat`。
不改 AOSP 资源或 merger XML，不声明拥有 AGP 输出目录；每次执行重新检查。
普通 APK 构建不需要 Python/uv。

### 平台 aconfig 引用改名

AOSP framework 的平台 Flags 经过 repackaging；仅通过编译不能证明 APK 引用可在设备
解析。`gradle/aosp17-aconfig-repackaging-rules.txt` 为冻结规则输入，插件在 pre-D8/R8
改写所有类的外向引用，保留定义身份和 self-reference；也必须覆盖 BootstrapMethods，
否则 D8 后续合成 lambda 会重新引出旧名。见
[ADR 0008](../adr/0008-pre-dex-aconfig-reference-rewrite.md)。

## 验证与上游升级

验证分开回答问题：工具测试证明打包/转换逻辑；APK 检查证明 manifest、签名、DEX、
资源及依赖边界；同基线设备上的启动、关键 UI、进程重启和整机重启证明运行行为。
构建成功不能代替后者，也不要求为每次文档或小改动执行全部门禁。

换 AOSP 基线时依次重对齐源码、按库族再生产物、重建 SDK、验证 Debug/Release、
检查 APK 并在同基线设备验证。刷新成本由真实模块/资源边界决定，不以减少文件数量为
唯一指标，也不以保存旧任务图为目标。
