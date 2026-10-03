# SysUISdk optional bridge：隔离验证与实现

日期：2026-10-03

> 本文记录第一轮 SDK 修复及交付时的状态。用户后续授权 live SDK 替换和 SettingsTheme
> 测试修复，现均已完成；最新状态见 CURRENT_STATE.md 及
> `2026-10-03-live-sdk-offline-handoff.md` / `2026-10-03-settingstheme-resource-inventory.md`。

## 用户授权与边界

用户批准按 optional bridge 路线继续；保持原有禁止 stub、真实字节、来源可追溯规则。
先在隔离 SDK/项目上验证，不替换 live SDK，不修改 AOSP、SystemUI 源码或资源，
不合 PR #1，不关闭 UnitTest。用户已有 gradle.properties 修改保留。

## 计划与验收

1. 构建只在临时目录内的项目和 SDK 副本；SDK 10-class slice 逐字节分离。
2. 用 Gradle Tooling API 获取真实 AndroidProject 模型：原 SDK 精确失败，候选 SDK
   全 Android 模块通过，UnitTest artifact 保留（不是 help 或 NO-SOURCE 冒充）。
3. 在隔离测试工程运行真实 Android 本地 JVM 测试，检查 javac/Kotlin/R8 的 optional bridge
   classpath；无 stub，测试源码为验证逻辑而不是平台类替身。
4. 前述门通过后，生成器以测试先行实现 deterministic optional bridge，修订 ADR 0006
   布局/验证合同及 Gradle useLibrary 接线，运行 Python 测试和完整真实 AOSP 再生。
5. 隔离构建 Debug/Release 与 APK 静态门；按实际可执行范围记录结果，遇阻塞先诊断/询问。
6. 记录交接与 SDK 安装/发布下一步；未获 live SDK 替换授权前不替换。

## 环境

- 本机 AOSP：用户给定 `/home/leijiabin/myspace/aosp`，所有路径通过 CLI 输入。
- live SDK：`/home/leijiabin/Android/Sdk`，只读。
- 当前 PATH 未提供 uv：为遵守 Python 一律 uv run，计划下载官方 uv 独立二进制到临时目录，
  不用 pip/uv pip、不改 shell 配置；Python 依赖使用项目现有 uv.lock。
- Gradle 构建串行。取完整 NPE 栈时的 JVM fast-throw 开关仅诊断，不写生产配置。

## 发布步骤（用户后续授权）

用户已授权 commit/push 和发布新版 SDK。发布物必须来自正式单入口生成器与冻结 AOSP
输入，禁止使用手工临时 SDK。补充发布门：打包前核对 marker 的完整文件清单与每文件
SHA；两份独立再生产物分别打包、zip/sidecar 相同；记录源码 commit 与复现命令。
当前 `gh auth status` 未登录，已请用户执行浏览器登录，不接收聊天明文 token。
GitHub SSH 22 连接超时，登录后可使用仓库现有 HTTPS remote。

## 最终验收（2026-10-03，仅本地交付）

### 改动

- 生成器 045.3：冻结 37-entry allowlist 不变；android.jar 留 27 类，既有 libcore/DDMS
  10 类进 `optional/sysui-platform-bridge.jar`，system modules JAR 仍保留 37 类。
- metadata 保留 stock optional entries、追加 manifest=false 的唯一 bridge；冲突/非法
  metadata 拒绝、原始字节校验、禁止 android.jar 重复定义、两次确定性与事务发布保留。
- 根 Gradle 只增加公开 `useLibrary` 接线，不关闭 UnitTest，不修改 SystemUI 源码/资源。
- 新增 opaque-byte 组合/破坏性门禁测试与真实 AGP Java/Kotlin/JUnit fixture；没有创建
  平台 stub。IDL、旧 android.jar 的 39,258 条目 payload 并集、system-module JAR 全部原样。
- packager 默认 r2，输出前按 marker 清单核对所有文件 SHA，拒绝手工补丁/漏文件/多文件。
- ADR 0006 只修订交付位置，P/F/R、无 stub 与真实字节约束不变。README 双语标明旧 r1
  只适用于历史 tag，当前 main 需新布局 SDK。发布说明为本地草稿。

### 已执行证据

证据目录：`/tmp/sysuisdk-optional-validation/`。最后阶段统一使用用户安装的全局 uv 0.12.22。
AOSP_ROOT 均显式设为用户给定目录，未修改 tools/aosp_paths.py 的历史默认路径。

| 门禁 | 结果 / 日志 |
|---|---|
| 原 SDK Tooling API AndroidProject | FAIL：原样 androidApis/MockableJarTransform/handlerRangeBlock，`model-red.log` |
| prototype SDK + useLibrary | 13 模块模型通过，`model-green.log`；不是 help，也不是空 test |
| 正式生成器 SDK + 正式根 Gradle 接线 + fresh model daemon | PASS，`model-final.log`；13 模块、26 variant records，每个 Debug 保留 UnitTest；Release 默认无 host artifact |
| SDK 组合原测试基线 | 72 passed，`python-baseline.log` |
| 新 optional 测试 red→green | 14 failed/1 passed → 全 15 passed，`optional-tests-red.log` / `optional-tests-green.log` |
| 发布清单门 red→green | 修改/遗漏/额外文件原先可被打包 → 三种均拒绝；r2 默认名测试通过，`package-red.log` |
| SDK + optional + packaging tests | **97 passed + 3 subtests**，`sdk-tests-final.log` |
| 全 Python 测试（正确 AOSP_ROOT） | **366 passed + 154 subtests、1 failed**，`python-all-final.log`；不是全绿，见下 |
| 两次正式 AOSP SDK 再生 | 各 11,386 输出文件；marker（含全部输出 SHA）相同，`generator-real.log` / `generator-real-again.log` |
| 真实 JVM fixture（生成器 SDK，fresh daemon） | **4 tests、0 errors/failures/skips**，`jvm-generated-fresh.log`；运行时精确 bridge 绝对路径检查通过 |
| 初次 Debug / Release build | 成功，5m17s / 6m56s；早期 daemon 缓存路径问题见下，不能单独作为新根目录证明 |
| fresh-daemon 双 build + 路径断言 + 强制 R8 重跑 | **PASS 2m44s，759 tasks（23 executed、736 up-to-date）**，`fresh-sdk-build.log`；R8 实际执行，完整 library 路径均为 generated-sdk，无 prototype 路径 |
| SDK 输入/输出不变性 | 原 android.jar 的 39,258 entry payload 在新 android.jar+optional 的不相交并集中完全相等；system modules JAR 和 framework.aidl 字节相同，`*-boundaries-final.log` |
| R8/编译接线 | generated bridge 在 core javac 和 R8 bootclasspath，不在 R8 program classes；`CORE_JAVAC_OPTIONAL_INPUT_PASS` / `R8_LIBRARY_INPUT_PASS` / `R8_NOT_PROGRAM_INPUT_PASS` |
| Debug + Release aconfig gate | 两者 RESULT=PASS；13/2 DEX，0 违规、0 hidden 定义，`*-aconfig-final.log` |
| APK bridge/manifest gate | 两 APK 全 37 bridge 定义为 0；aapt2 XML 中不存在 com.android.systemui.platform.bridge uses-library，`*-boundaries-final.log` / `*-manifest.txt` |
| APK 签名 | 两者 v2=true，`*-signature.log` |
| 两份独立 SDK 发布打包 | ZIP 逐字节相同（cmp），79,983,909 B；`package-one.log` / `package-two.log` |
| ZIP 交付清单 | 实际 ZIP 恰含 marker + 11,386 项生成文件 + LICENSE/NOTICE/README.txt；全部文件 SHA 匹配 marker，CRC/整包 SHA 通过 |

APK：
- Debug：190,547,872 B，`e7277867695b85098bee5d3bba06732371ff708471d332e807e5ff08b3a45abd`，
  **与 docs/release-manifest/README.md 发布 Debug 完整 SHA 相同**。
- Release：45,030,198 B，`395959de6cc2b1741244df29ff00b3a1033ff3e5053b108298721268d16281c3`。
  本次未比较旧 Release APK 内部条目，不把 SHA 差异擅自归因于签名随机性，也不声称逐字节相同。

### 执行中的诊断修正（如实保留）

1. Tooling probe 最初假设 host key 为 `unitTest`，实际是 `_unit_test_`；且 Release 默认无
   host artifact。修正的是 probe 预期，没改 AGP test enable 设置。
2. classpath probe 起初跨 project 解析配置、随后在未执行 producer 时查询 R8 provider，
   分别触发 Gradle exclusive-lock 和 producer-completion 保护；最终任务在所属 project
   解析、依赖 r8.classes producer，实际门已通过。
3. offline core probe 起初缺第三方缓存；正常解析后缺本地 producer JAR（诊断任务没有编译
   upstream）。后续完整构建及最终输入 gate 已通过，不是 unresolved API。
4. **AGP static cache 教训**：同一 daemon 在切换 SDK root 后，BootClasspathBuilder
   仍返回 prototype SDK 路径；CacheKey 只有 AndroidVersion/optional requests，缺 SDK root。
   虽然 prototype 与正式 SDK 的所有 class bytes 相同，仍撤销“仅凭初次 build 即证明正式
   SDK 路径”的推断。最终 `--no-daemon` + 精确全路径断言 + R8 强制重跑通过。
   JVM fixture 强化为精确路径断言，Tooling probe 使用唯一 JVM identity 避免复用。
5. 首次全 Python suite 未设 AOSP_ROOT，35 个旧默认路径失败；显式路径后只剩 1 个
   `TestSettingsLibSettingsThemeProvenance.test_res_entries_match_aosp_tree_exactly`。
   已在 **未改动 HEAD 35def1f4** 的隔离工具副本复现相同失败
   (`python-head-existing-failure.log`)；与本次 SDK/打包改动无关，未擅改资源解决。

### 关键复现命令

```bash
uv run python tools/build_sysuisdk.py \
  --aosp-root /home/leijiabin/myspace/aosp \
  --sdk-root /home/leijiabin/Android/Sdk \
  --output /tmp/sysuisdk-optional-validation/generated-sdk/platforms/android-SysUISdk

# 第二次使用 generated-again；比较两个 marker 和独立打包 ZIP。
ANDROID_HOME=/tmp/sysuisdk-optional-validation/generated-sdk ./gradlew \
  -p tools/tests/fixtures/sysuisdk_optional_bridge testDebugUnitTest \
  --no-daemon --rerun-tasks --console=plain

AOSP_ROOT=/home/leijiabin/myspace/aosp uv run pytest tools/tests -q
uv run python tools/package_sysuisdk_release.py \
  --platform /tmp/sysuisdk-optional-validation/generated-sdk/platforms/android-SysUISdk \
  --output dist/sysuisdk-optional-bridge/SysUISdk-android-17.0.0_r1-r2.zip
```

完整模型客户端与运行方法已入库 `tools/tests/fixtures/sysuisdk_optional_bridge/`。
完整 APK gate 使用仓库 `tools/check_aconfig_jarjar_references.py`；只读 bridge-definition
检查复用了其 Dex.defined 与生成器的 BRIDGE_ENTRIES，没有另造 DEX/字节码改写器。

## 发布与安装状态

用户随后明确要求 **不要在公司机器上传 GitHub，改为本地 patch，另一台机器发布**。
遵照最新指令：没有 push、没有创建远端 tag/Release、没有上传资产；停止进一步远端操作。
本轮仅在用户授权窗口内读取过远端元数据、检查过账号权限。

交付目录：`dist/sysuisdk-optional-bridge/`（gitignore 已覆盖 dist）。
ZIP：`SysUISdk-android-17.0.0_r1-r2.zip`，SHA-256：
`329fd0e12a19b8004180fb74f0a9a3817b2e7b3c1fc36617a8af7d535b5543ae`。
含同名 `.sha256`；本地 patch 和应用/发布步骤一并放该目录。
发布包使用 **AOSP 七输入 + 官方 android-37.0 Pkg.Revision=2 / ExtensionLevel=22 底座**；
不是 pure-AOSP SDK，输入/底座每文件 SHA 全在 marker 中。压缩环境 Python3.12.7/zlib1.2.11。

## 尚未执行 / 下一步

- **live `/home/leijiabin/Android/Sdk/platforms/android-SysUISdk` 未替换**。要让本机 Studio 使用
  新布局，停止 Gradle daemon 后，用当前生成器 `--replace` 或干净安装本地 ZIP；不得覆盖混装。
- 本轮没有手动点击 Studio Sync、没有设备部署/整机重启；有真实 Tooling model 和 JVM/构建门。
- 在另一台机器应用 patch、复核 artifacts SHA，再人工决定 tag/Release 发布时间。
- 全 Python suite 的那个既有 SettingsTheme 资源清单失败留待独立维护，不在此次 SDK 修复范围。
