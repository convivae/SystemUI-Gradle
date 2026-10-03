# PR #1 与保留 Android JVM 测试的 SDK 方案评估

日期：2026-10-03

## 背景与目标

用户提供 PR https://github.com/convivae/SystemUI-Gradle/pull/1，希望尽量保留 Android
本地 JVM 测试，评估修改 SDK 是否可行及其代价。本步骤只读调研，不合并 PR、不修改 SDK、
不放宽规则 P / ADR 0006；若方案需要例外授权，先说明再询问。

## 计划

1. 固定 PR head/base，阅读完整 diff、讨论与测试，区分作者声称和本机验证。
2. 按规范（真实 class 字节、无 stub、事务生成）与用户目标（Sync + 实际 JVM 测试）双轴检查。
3. 核对 JVM classfile、AGP 官方实现及 AOSP 产物形态，评估 SDK 方案风险、替代方案与验证成本。
4. 研究结论写入 docs/architecture；本轮不执行 PR 中的方法体改写或安装其发布物。

## 初始状态

- PR head：`4ee80743bd77f9be87e36a00670fc9310eb6a705`。
- GitHub API base：`35def1f4f110824a9fe4f8c3f3d6a38b5c29ba17`。
- 当前 repo 已有上一轮诊断文档改动与用户原有 gradle.properties 改动；均保留。
- 当前工具没有后台子 agent 接口，本轮由主 agent 直接调研，不声称已做独立双 reviewer 审查。
- 构建/测试：本步骤尚未运行；错误数无新测量。

## 有界只读输入实验计划

官方 AGP 源码发现 SDK `optional/optional.json` + DSL `useLibrary()` 通道：
optional library 进入编译 bootclasspath、R8 fullBootClasspath 与本地测试 runtime，
而 MockableJarTransform 只读取 android.jar。进一步只在 `/tmp` 创建诊断 JAR：
将当前真实 libcore/DDMS 10-class slice 从 android.jar 的临时副本中分离，检查
剩余 android.jar 能否通过当前 AGP 转换。原 SDK/AOSP 保持只读，不安装候选 SDK、
不改方法体；这仅验证 artifact 边界，不声称完整 SDK/编译/R8/测试已通过。

## 实际结果

- 完整 diff 与固定 head 生成器已读；讨论/reviews 均为空。主 agent 单人双轴审阅。
- PR 关键阻塞：真实 bridge stubbing 与原始字节 validator 冲突；MethodHandle tag 15
  payload 长度错误；enum `<clinit>/values/valueOf` 被抹除而 AGP 不恢复。
- 发现官方 SDK optional library / useLibrary 的公开接缝，编译/R8/测试路径都有源码依据。
- 临时 split probe：移动既有 libcore/DDMS 10-class slice，39,258 entries 在两个 JAR 中
  逐项内容相同；AGP mockable false/true 均 PASS（16s）。没有改 class 方法体、live SDK、生产配置。
- 未运行 PR tests / 全量 SDK 生成 / IDE 完整模型 / 实际 JVM 测试 / APK/R8/设备验收。
- 推荐先获批隔离 SDK 的端到端验证，不关闭 UnitTest，不直接合 PR，也不申请放宽无 stub 原则。
- 完整证据、风险与成本：
  [`../architecture/2026-10-03-sdk-mockable-preserve-jvm-tests.md`](../architecture/2026-10-03-sdk-mockable-preserve-jvm-tests.md)。

## 待解决问题

- PR 的全量 SDK 方法体改写是否真的能经单入口生成器完整生成、并通过实际 JVM 验证？
- 哪些方法体信息对 Kotlin inline、enum、构造器以及测试执行不可直接抹除？
- 保持现行无 stub 规则与保留 JVM 测试能力是否必须通过 AGP 端修复而不是 SDK 改写？
