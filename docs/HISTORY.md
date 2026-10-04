# 项目构建历程（冻结归档）

> 本文件是**一次性写成的历史归档**（2026-10-04），记录本项目如何从 AOSP Soong 体系
> 一步步移植为独立 Gradle 工程。写后不再维护、不随新构建更新；当前事实以仓库现状
> （README、AGENTS、构建配置）为准。各阶段的完整细节见 `docs/issues/` 与
> `docs/architecture/` 对应日期文件；已删除的交接/状态/编排文档可用
> `git log --all -- <路径>` 从 Git 历史查阅（精简前最后版本见提交 `570b8c23`）。

## 起点

- 目标：把 AOSP `frameworks/base/packages/SystemUI`（状态栏、通知、锁屏、最近任务等
  系统界面的真实源码）从 Soong 构建体系移植为**独立、自包含、可二次开发**的
  Android Gradle 工程，产出可在同基线模拟器上运行的平台签名 Debug/Release APK。
- 参照：用户此前的 `CarSystemUIGradle` 项目（车辆 SystemUI 移植）提供依赖引入与
  SDK 合并的初始思路，但本项目后来在模块语义、产物来源纪律上走了更严格的自有路线。
- 最终基线：AOSP `android-17.0.0_r1`，AGP 9.3.1 / Gradle 9.5 / built-in Kotlin 2.2.10，
  17 个 Gradle 模块；tag `v1.0.0-android-17.0.0_r1`。

## 阶段 0：骨架与依赖探路（2026-07-16 → 07-22）

- v1 离线策略（手工拷贝 jar）很快暴露不可维护，废弃，改 v2 双构建骨架设计。
- 早期为了让 IDE 满意写过一批 stub 类，后被全部清除并确立**规则 P（无 stub）**：
  这是本项目最重要的一条边界，后续所有"编译不过"都被迫回到真实产物来源解决。
- 实验：framework.jar 合并进 SDK android.jar、平台密钥转换（pk8+x509 → JKS）、
  AOSP 命名与参考项目命名的差异（`SystemUISharedLib.jar` 等）。

## 阶段 1：大规模依赖补齐（2026-07-22 → 07-30）

- 从数千个编译错误起步，按"缺什么补什么来源"逐类清障：SettingsLib、lottie、
  proto、AIDL 生成 jar、unfold、compose 内部 API、biometrics……
- 关键根因教训：`server-notification-flags.jar` unresolved 的真凶是**源码树里的
  同名 stub 遮蔽了 jar 类**，与 Kotlin 版本/注解/包名全无关（孤立编译成功、全工程
  失败时应先查源码集与 classpath 遮蔽）。此教训沉淀为诊断流程。
- R import 歧义（多命名空间）：正解是对齐 AOSP 原始 import，而非发明 alias。
- 2026-07-29 确立核心规则组：S（SystemUI 自有代码源码化）、C（与 AOSP 不漏不多）、
  F（framework 代码禁止源码复制，走 SDK/JAR）、R（资源来源可追溯）、B（按
  `Android.bp` 语义对齐模块）。曾把 framework `IRemoteCallback.aidl` 源码拷进
  core，被用户否决，改为补 SysUISdk 的 `framework.aidl` 声明。

## 阶段 2：模块拓扑与规则成型（2026-08-06 → 08-07）

- 模块边界调研后定型：`Android.bp` 是语义依据，但 Soong target 不与 Gradle module
  一一对应（ADR 0003）；13-module 拓扑落地（后演化为 17）。
- AOSP 资源含 `product="tv"` 等变体、AAPT2 不支持：确立 **CONV 标记纪律**
  （ADR 0004，`CONV_ADD/DEL/MOD` + BEGIN/END，保留原字节，可追溯可撤回），
  配套 `check_source_alignment.py --strict` 对账。
- Maven 定位澄清：本地 `libs/maven/` 只是 AAR 交付仓库，不是第四种产物（ADR 0001）。

## 阶段 3：工具链升级（2026-08-11 → 08-13）

- KSP 替代 KAPT（KAPT 1.9+ 与 Gradle 9.5 冲突），Dagger 经 KSP 全量生成通过。
- 全依赖升级 + **AGP builtInKotlin** 迁移：`kotlin.srcDirs` 对齐、AIDL 生成源接入
  KSP、`disallowKotlinSourceSets=false` 三件套踩坑全部记录在案。
- 版本耦合天花板实测：Compose 1.12 移除 `ExperimentalAnimatableApi`（AOSP 在用）、
  coroutines 1.11 新 overload 破坏源码——升级前必须按 API 核对，不能只看版本号。
- core javac 归零；SysUISdk 走可复现构建；AGP 合并资源丢 `xmlns:androidprv` 的
  问题首次定位并修复（后来在维护期又 JVM 化，见阶段 7）。

## 阶段 4：首个 APK 与 Release 闭包（2026-08-19 → 08-21）

- **2026-08-19 首个 Debug APK**（158,775,460 B）。SettingsLib 资源闭包走 per-target
  res-only AAR + POM 传递依赖（ADR 0005，本地 Maven 唯一真实传递边例外）。
- 官方 Maven 全量审计：能走公网坐标的一律走公网（zxing 3.5.4 等四个本地 jar 退役）。
- R8 missing refs 从 140 逐批清零（iconloader / viewcapture / motiontool / Traceur /
  SettingsLib / WM-Shell proto / platform classpath bridge）：方法论是**逐类归属真实
  产物来源，拒绝宽泛 dontwarn**。Release 28,600,808 B 无混淆 V2 签名成功。
- SysUISdk 重写为**单入口事务性生成器**（`tools/build_sysuisdk.py`，ADR 0006）：
  冻结输入映射 + 只读官方 platform 底座，两次生成逐字节一致。

## 阶段 5：真机运行门与 16 时代闭环（2026-08-22 → 08-26）

- 首次部署一次性模拟器即 RUNTIME_FAIL：根因审计锁定编译期 SDK 与设备 framework
  的双重偏差，选定 same-tree 自建镜像路线（Family B）。
- 2026-08-25 **DEBUG_RUNTIME_PASS**、2026-08-26 **RELEASE_RUNTIME_PASS**
  （`-dontobfuscate` 对齐 Soong + 3 行 CoreStartable `-keep` 抗 R8 水平合并）。
- 部署纪律沉淀（overlay/verity 互斥、toybox cp 静默截断必须 SHA 二次校验、
  重启后重新 remount）；`libs/` 产物再生性 15/15 全部纳入脚本管线。

## 阶段 6：Phase C——AOSP 17 清空重生（2026-08-26 → 09-09，ADR 0007）

放弃 main 漂移态，固定 `android-17.0.0_r1`，全管线"删光重来"证明可复现：

- **C1** AOSP 原树切 tag 全量构建（`m -j16` 2h35m，GOMEMLIMIT+swap 解 soong OOM）。
- **C2** `libs/` 104 文件全删 → 仅凭 7 个 `tools/package_*.py` 脚本从 AOSP-17 再生
  102 文件，无一手工产物。
- **C3** 源码整树重对齐（删 847 / 移 34 / 拷 2566 / 覆 3067，CONV 重标 5806 处，
  `--strict` exit 0）。
- **C4** 17-module 拓扑接线，Debug 编译闭环、Release/R8 闭环先后恢复。
- **C5** 最硬的一段：17 镜像模拟器上 Debug 部署后 622 次
  `NoClassDefFoundError: dreams.Flags` 崩溃。根因是 **AOSP 17 对 framework aconfig
  类做了 725 条 jarjar 改名**，编译期名字在设备上不存在；且"跳过定义类只改引用"
  被 D8 后置的 lambda 合成证伪。最终方案：pre-D8/R8 对**所有类**做仅引用改写
  （保 this_class/self-ref，含 BootstrapMethods，ADR 0008）+ 指令级静态门禁
  （`check_aconfig_jarjar_references.py`）。双 APK 静态+部署+整机重启门全 PASS。
  其间还闭环了 sharedUserId 回归（AGP merger 不从 library 清单继承，app 主清单
  显式声明修复，DPGP 首靴自动授权，零手动 grant）。
- **C6** versionCode=37 / versionName="17" 落双 APK，发布清单快照，tag
  `v1.0.0-android-17.0.0_r1` + GitHub Release（含确定性打包的 SysUISdk r1 zip）。

## 阶段 7：维护期（2026-10）

- **SysUISdk optional bridge**：修复 Studio Sync 的 MockableJarTransform 故障——
  真实 library classes 经 SDK optional library 交付，保留本地 JVM 测试，不改写
  AOSP 方法体（ADR 0006 修订；拒绝 PR #1 式全量 stubbing）。
- **主机可移植性**：清除机器绝对路径，AOSP 根经 `tools/aosp_paths.py` 统一，
  构建脚本与测试跨主机可复现。
- **资源修复 JVM 化**：`androidprv` namespace 修复从 Python 脚本迁为 buildSrc 的
  Kotlin Gradle task（AGP 选定 AAPT2 + 冻结 feature-flags），普通 APK 构建不再
  依赖 Python/uv；Python 仅保留为产物再生维护工具。
- 文档精简（本文件即其产物）：撤销常驻交接/状态/编排台账，方法论并入现行文档，
  历程归档于此。

## 可迁移的经验要点

以上历程中可带到其他项目的核心判断，多数已沉淀为现行规则（AGENTS/ADR/PITFALLS）：

1. **产物来源纪律先于编译通过**：无 stub、资源不凭空生成，逼所有问题回到真实
   来源，短期慢、长期是唯一可维护路径。
2. **镜像工程的验收是"不漏不多"而非"能编译"**：对齐脚本 + 标记纪律 + 人工对账。
3. **编译期解析成功 ≠ 设备运行可用**：jarjar 改名、平台签名、sharedUserId、
   overlay/verity 都只在部署后才暴露；构建门禁之后必须有指令级引用门 + 真机门。
4. **优化器缺引用逐类归因**，宽泛 keep/dontwarn 只会把失败推迟到运行时。
5. **自定义 SDK 用生成器事务性重建**，禁止手工补丁；可复现性用"冻结输入 +
   两次生成逐字节一致"证明。
6. **错误数是诊断信息不是门槛**：允许提交诚实的中间态，保持项目向前推进。
