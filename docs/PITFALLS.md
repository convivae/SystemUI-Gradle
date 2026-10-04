# 构建与部署故障排查

这里保留当前工程仍适用的根因与检查方法；依赖版本看
[`gradle/libs.versions.toml`](../gradle/libs.versions.toml)，开发约束看
[`AGENTS.md`](../AGENTS.md)。旧任务的错误数、假设和验收流水不在此重复维护。

## SDK 找不到、隐藏 API 缺失或 Studio Sync 失败

- `SysUISdk` 是自定义 preview platform，需要安装到 Gradle 实际使用的
  `<SDK>/platforms/android-SysUISdk/`，不是普通官方 platform 的别名。
- 先检查 `local.properties` 与环境指向的 SDK 是否一致；JVM 模块需要平台 API 时
  复用 AGP 的 SDK provider，不另用机器路径或另一套环境变量回退。
- 当前 main 需要含 `com.android.systemui.platform.bridge` 的 optional bridge 布局。
  若报找不到 optional library，按 [README](../README.md)再生/安装匹配 SDK；
  不删除 `useLibrary()`，不通过关闭 UnitTest 或改写 AOSP 方法体绕过。
- `framework.jar` 的类签名不能修正私有资源 ID。代码 API、`framework.aidl` 和
  framework-res 都应由 SDK 生成器从匹配的 AOSP 输入提供，不手工拷贝补丁。
- 更换 SDK 后，在无其他构建时停止旧 Gradle daemon，必要时用 `--no-daemon` 验证。
  AGP 的 bootclasspath cache 未按 SDK 根目录隔离，旧 daemon 可能继续使用另一份 SDK。

机制见 [ADR 0006](adr/0006-sysuisdk-r8-library-class-bridge.md)；真实 JVM 测试和
无界面 IDE 模型检查见 [SDK fixture](../tools/tests/fixtures/sysuisdk_optional_bridge/README.md)。

## Kotlin、KSP 与 AIDL

Android 模块使用 AGP built-in Kotlin，JVM 模块仍用 Kotlin JVM 插件。升级时一起核对
AGP、内置 Kotlin、KSP 和 Compose compiler 的兼容性，不只改 Kotlin 版本字符串。
Dagger 使用 KSP，不改回 KAPT。

| 现象 | 检查 |
|---|---|
| KSP 通过 kotlin.sourceSets 添加源码被禁止 | 保留 `android.disallowKotlinSourceSets=false` |
| Kotlin/KSP `NO-SOURCE` | 非标准源码目录同时配置 java 和 kotlin roots，不能只加 `java.srcDirs` |
| KSP 看不到 AIDL 接口 | 对应 variant 的 AIDL 生成目录须加入 Kotlin sources，KSP 显式依赖该 variant 的 AIDL task |
| Compose inline / `Couldn't inline method call` | 检查是否错误向 KotlinCompile 注入 framework.jar；隐藏 API 应由 SysUISdk 提供 |

参考现有模块接线，尤其避免 Release 错用 Debug 的 AIDL 输出。

### 依赖升级限制

- Compose 1.12 移除了本基线使用的 `ExperimentalAnimatableApi`；未解决源码兼容性前
  保持现有兼容版本，material3 与之配套。
- coroutines 1.11 的新 overload 曾破坏 AOSP 源码的调用解析，不能只按版本号升级。
- AOSP prebuilts 的版本不一定已发布到公网 Maven。先查官方元数据及 API，不能用一个
  相似坐标假定等价，也不因解析失败就自行打包上游库。

## JAR 有类但仍然 unresolved

1. 在 AOSP 查完整限定名及其 `Android.bp` owner。
2. 用 `unzip -l` / `jar tf` 检查实际 SDK/JAR 内容，用 `javap -p` 检查所需成员。
3. 检查实际 compile classpath，而不仅是某条 dependencies 声明。
4. 检查同包同名源码是否遮蔽 JAR，以及 flags JAR 是否被 framework.jar 同名定义遮蔽。

曾经 notification Flags 的失败来自源码 stub 遮蔽，而不是 Kotlin 对包名或
`@UnsupportedAppUsage` 的特殊行为。若孤立编译成功、全工程失败，应优先查源码和
classpath 差异，不重复调整无关注解。模块里的 `files("libs/...")` 相对于模块目录，
引用仓库根产物要显式使用 root project 路径。

## 资源合并与链接

- SystemUI 资源使用 `com.android.systemui.res.R`；其他库有各自 namespace。
  R 歧义先对比 AOSP 原始 import 与资源归属，不添加伪造资源或批量改 R 引用。
- 非 default `product=` 变体通过获准的 CONV 标记处理，不能手工去重或合并到主资源。
  依据见 [CONV 规范](adr/0004-conv-markup-and-alignment-discipline.md)和
  [原始授权记录](issues/2026-08-07-product-variant-conv-del.md)。
- `androidprv` 仅出现在属性值时，AGP merge 可能丢失 namespace 声明。现有 Kotlin
  task 在临时副本补声明，再用 AGP AAPT2 重编译 flats；不要修改 merger XML 或
  AOSP 原始资源。失败时查 `patch<Variant>AndroidPrvMergedResources` 的输入与输出。
- 独立 AAPT2 compile 也需要 aconfig feature flags；`Resource flag value undefined`
  先查 `libs/systemui-aconfig-flags.txt` 及 task 的 `--feature-flags @file` 参数。

实现边界见 [Gradle 构建设计](architecture/gradle-build.md)。

## Release/R8 缺类与运行时反射

`Android.bp static_libs` 不会自动变成 Gradle 的 program dependencies。
先区分 APK 自带依赖、设备平台类、构建期注解，再决定补哪个产物或平台接口。
宽泛 keep / dontwarn 不能修复真实依赖缺口；本地 Maven AAR 内容变化应升坐标，
否则缓存可能继续消费旧产物。

Release 特别检查反射、JNI、序列化和插件入口：

- protobuf-lite 通过反射访问消息字段，错误裁剪会在运行时失败。
- R8 合并身份不同的 CoreStartable 类后，按类名注册的 DumpManager 可能发生冲突。
- 精确规则及理由在 `app/proguard_gradle.flags`；不要照搬整个 Soong 优化配置。

### 平台 aconfig 改名

设备 framework 的 aconfig 类经过 repackaging；编译期能找到原名，不代表设备上存在。
插件必须覆盖冻结的完整规则，对所有类的外向引用改写，包括 BootstrapMethods。
跳过定义类会让 D8 在后续生成仍引用旧名的 lambda。

构建后运行对应 APK 的门禁：

```bash
uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/debug/app-debug.apk
uv run python tools/check_aconfig_jarjar_references.py --apk app/build/outputs/apk/release/app-release.apk
```

任何非 self-reference 的旧 owner 指令引用或 hidden target 定义都应失败。
仅启动过一次、或旧 APK 曾经看似正常，不能替代覆盖检查。机制见
[ADR 0008](adr/0008-pre-dex-aconfig-reference-rewrite.md)。

## 设备与模拟器部署

SystemUI 是系统关键进程。只在匹配 AOSP 基线及平台签名的可恢复测试环境验证，
先备份原 APK/镜像；不要将下面的检查表当作商用设备通用刷写步骤。
启动参数取决于镜像布局；旧日期 runbook 的产品、路径、super/scratch 大小不能直接套用。

### overlay、空间和 APK 校验

- overlay 部署依赖 verity disabled。执行 `adb enable-verity` 并重启会拆掉 overlay，
  已部署 APK 回退到 stock；仅在明确要放弃 overlay 部署时这样恢复。
- overlay 内容可跨重启保留，但 rw 状态可能不保留。再次写分区前重新
  `adb root && adb remount`，先确认返回成功及可用空间。
- 先 push 到 staging，再复制到**目标 APK 同目录临时名**，校验大小、SHA 和文件权限，
  最后同文件系统原子 rename 替换。不要直接覆盖正在使用的 APK。
- 设备端曾在空间不足时出现复制截断而命令返回成功；替换前后都必须检查设备 SHA
  与本地产物一致。校验不符立即停止，不把损坏产物当作已部署版本。
- 重启后重新核验设备 APK SHA、进程稳定性、崩溃日志和关键 UI；确认未回退 stock。

### 权限崩溃先查 sharedUserId

若出现 `BLUETOOTH_CONNECT` / `READ_CONTACTS` SecurityException，先检查最终 APK 的
`sharedUserId`、平台签名、设备 appId 和系统默认授权，不能靠每次手动 `pm grant`
掩盖构建错误。AGP 不会自动从 library manifest 继承 `sharedUserId`，所以 app 主清单
必须显式声明 `android.uid.systemui`。

根因及修复依据见 [sharedUserId 回归](architecture/2026-09-03-systemui-shareduserid-appid-regression.md)；
[全新实例双变体验证](architecture/2026-09-06-fresh-instance-dual-variant-validation.md)
证明修复后无需手动 grant。这些是历史验证证据，不代表新 APK 已经部署通过。
