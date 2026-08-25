# 2026-08-25 — aconfig flags 批量运行时闭包（Task 055）

> Worker: task055-worker（herdr tab `w2:t1R` pane `w2:p1X`）
> Brief: `docs/orchestration/tasks/055-aconfig-flags-batch-closure.md`
> 前置：Task 054（`docs/issues/2026-08-25-android-os-flags-runtime-closure.md`）修复
> `android/os/Flags` 并预扫描出 11 个同族残留 hazard；chief 2026-08-25 批准**一次性批量修复**。

## 背景

每个 hazard 都是同一模式：APK 引用公开名 `L<pkg>/Flags;`，设备 bootclasspath 只有
JarJar 重写后的 `com.android.internal.hidden_from_bootclasspath.<pkg>.Flags`，APK 又未打包。
修复配方（window-flags / task054 先例）：打包 owning `java_aconfig_library` 的
`android_common/javac/<module>.jar`（**base 变体**，其 backing API
`android.os.flagging.PlatformAconfigPackageInternal` 已在设备 framework.jar 验证存在；
export 变体的 `AconfigPackage` 不在设备 BCP，不可用），byte-identical 复制进 `libs/`，
`implementation(files(...))` 接线。

## 11 个 hazard 的 owning module 定位（✅ 已核实）

来源：`frameworks/base/AconfigFlags.bp`（11 个 `aconfig_declarations` 均在此文件，
`exportable: true`，`container: "system"`；java_aconfig_library 全部带
`framework-minus-apex-aconfig-java-defaults` —— 即 JarJar 迁移的成因）。

| # | 公开包 | owning java_aconfig_library（已核实） | javac 产物现状 |
|---|---|---|---|
| 1 | android/app/smartspace/flags | `android.app.smartspace.flags-aconfig-java` | ❌ 未构建 |
| 2 | android/content/pm | `android.content.pm.flags-aconfig-java` | ✅ 已构建（19,798B） |
| 3 | android/hardware/biometrics | `android.hardware.biometrics.flags-aconfig-java` | ✅ 已构建（9,350B） |
| 4 | android/hardware/usb/flags | `android.hardware.usb.flags-aconfig-java` | ❌ 未构建 |
| 5 | android/net/platform/flags | `android.net.platform.flags-aconfig-java` | ❌ 未构建 |
| 6 | android/permission/flags | `android.permission.flags-aconfig-java`（有 export/host 变体，取 base） | ❌ 未构建（仅 apex35 turbine） |
| 7 | android/provider | `android.provider.flags-aconfig-java` | ✅ 已构建（9,467B） |
| 8 | android/security | `android.security.flags-aconfig-java`（有 export/host 变体，取 base） | ❌ 未构建 |
| 9 | android/service/controls/flags | `android.service.controls.flags-aconfig-java` | ❌ 未构建 |
| 10 | android/service/notification | `android.service.notification.flags-aconfig-java`（有 export 变体，取 base） | ❌ 未构建（boot 关键首因） |
| 11 | android/service/quickaccesswallet | `android.service.quickaccesswallet.flags-aconfig-java` | ❌ 未构建 |

产物路径模板：`out/soong/.intermediates/frameworks/base/<module>/android_common/javac/<module>.jar`

**已构建 3 个**：content.pm、biometrics、provider。
**待构建 8 个**：smartspace、usb、net.platform、permission、security、controls、
notification、quickaccesswallet。

## 构建约束核对

- `df`：`out/` 所在文件系统可用 **147G**（≥ 10 GiB 门槛）。
- 目标 product 按 brief：`sdk_phone64_x86_64-trunk_staging-userdebug`（本树尚无该产品目录；
  `out/target/product/` 现有 emu64a/emu64x/generic_arm64；lunch 新 combo 只重写 `out/` 内的
  ninja/soong 配置，不触碰 emu64x 设备产物目录；flags javac JAR 为 android_common
  变体，product 无关；base 变体运行时取值来自设备 aconfig storage，不受构建侧默认影响）。
- 单次 `m -j4` 批量构建全部 8 个缺失模块；只写 `out/`。

## 实施步骤记录

### 1-2. 定位与构建（✅ 完成）

- lunch 修正：brief 命令里的 `export TOP=$(pwd)` 会破坏非交互 shell 下 envsetup 函数注册
  （`lunch: command not found` → TARGET_RELEASE 空 → release_config.mk:262 报错）。
  改为 `cd $AOSP_ROOT && . build/envsetup.sh && lunch sdk_phone64_x86_64-trunk_staging-userdebug`
  （TARGET_RELEASE=trunk_staging 正确解析）。
- 单次 `m -j4 <8 个模块>`：**11 秒完成，m-exit=0**（日志 `/tmp/task054-audit/task055-m-build.log`）。
- 8/8 javac 产物核验存在；3 个已有产物复用。

### 3. 类集与变体验证（✅ 完成）

11/11 javac JAR 均为标准 5 类集合（Flags/FeatureFlags/FeatureFlagsImpl/CustomFeatureFlags/
FakeFeatureFlagsImpl），brief 预警的 content.pm/provider 额外类**未出现**，五类 validator
原样适用。抽查 FeatureFlagsImpl 字节码：service.notification 与 permission.flags 均引用
`android/os/flagging/PlatformAconfigPackageInternal`（base 变体，设备 BCP 已有该 backing API）。

### 4-5. 打包与测试（✅ 完成）

- `tools/package_aconfig_jars.py`：CONFIGS 新增 11 条（含 bp 出处注释）；新增 `--all` 批量
  模式（与单 artifact 互斥，向后兼容）。
- 测试：新增 BATCH3_CONFIGS 矩阵（11 subtests）+ TestBatchAllFlag（4 用例）。
  `uv run pytest tools/tests/ -q` → **233 passed, 38 subtests passed**。
- 打包 11/11，sha256 与 AOSP 源逐一 MATCH（表见 §6）。

### 6. 接线与重构建（✅ 完成）

`SystemUI-core/build.gradle.kts` 在 android-os-flags 后插入组注释 + 11 行
`implementation(files(...))`。`./gradlew :app:assembleDebug` → BUILD SUCCESSFUL in 47s。
APK：`app-debug.apk` 204,921,594B，sha256 `b827df78a9f1e62061a7ea337e57e75861c168e8d665b0823e99af08ef088779`。

### 7. Dex 全扫（✅ 完成）

脚本 `/tmp/task054-audit/task055_dex_sweep.py`（dexdump -l plain 逐 dex 精确扫，
坑：dexdump 输出行首有 2 空格缩进 + 含非 UTF-8 字节）。24 个 dex：
11 个新 Flags 类 + `Landroid/os/Flags;`（回归项）**全部 defs=1（恰好唯一定义）**；
APK 内 hidden_from_bootclasspath 定义 = 0（无重复打包双生类）。

### 8. 部署（✅ 完成，emulator-5554 唯一设备）

设备门：`adb devices` 仅 emulator-5554。
流程：root → disable-verity → reboot → wait-for-device → root → remount /system_ext rw。
- /system_ext overlay：261M 总量，替换前仅剩 6.4M → 沿用 /data 中转：push 至
  `/data/local/tmp/SystemUI.apk`（staging sha256 MATCH）→ rm 旧候选 → cp。
- **坑（新）**：首次 `cp` 产物被静默截断为 6,561,792B（sha256 不匹配被三段校验拦下）。
  根因：rm 解除链接后空间未立即可用（crash 循环中的 SystemUI 仍持有旧 APK 句柄，
  df 事前 6,420KB free），toybox cp 写至 ENOSPC 静默截断；旧句柄释放后（df 恢复
  200MB free）重跑 cp 成功。**教训：rm+cp 模式必须以目标 sha256 校验为准，
  不匹配则等句柄释放后重试。**
- 最终目标 sha256 = `b827df78a9f1e62061a7ea337e57e75861c168e8d665b0823e99af08ef088779`
  = 本地 APK = staging，三段一致。恢复 root:root 0644 `u:object_r:system_file:s0`
  （ls -lZ 验证）；删 `oat/` + dalvik-cache + staging 副本；reboot。

### 9. 运行时验收（✅ 全绿）

- `sys.boot_completed=1`（15s）。
- **PID 稳定性：pidof 采样 11 次 × 30s（18:16:59 → 18:21:59，恰好 5 分钟）全为 835**；
  `/proc/835/cmdline` = `com.android.systemui`。
- logcat（`logcat -c` 清缓后采样窗全覆盖：18:16:59.647 → 18:22:06.407，1,641 行，
  `/tmp/task054-audit/logcat-task055.txt`）：
  - `NoClassDefFoundError`（任意包）= **0**；11 个目标包 + android.os 逐项 = **0**
  - `FATAL EXCEPTION` = **0**；DumpManager `alreadyRegistered` = **0**
- 渲染证据：`dumpsys window displays` 存在 `mStatusBar=Window{581e1c4 u0 StatusBar}`，
  InsetsSource statusBars frame=[0,0][320,24] visible=true；`dumpsys statusbar` 服务存活
  （2 条 com.android.systemui disable 记录）；截图 `task055-screen.png`（320x480）。

## sha256 对照表（11/11 与 AOSP 源一致）

| 配置 | libs/ jar | sha256(前 32) | 大小 |
|---|---|---|---|
| smartspace-flags | libs/smartspace-flags.jar | ccf4025eb2dd9f78c471650650e1d03a | 7,651 |
| content-pm-flags | libs/content-pm-flags.jar | 9909047a258d22dfdf5e1cae2d3d9cab | 19,798 |
| biometrics-flags | libs/biometrics-flags.jar | 56939235de5bedd31aa87733f7bbde89 | 9,350 |
| usb-flags | libs/usb-flags.jar | ad4e569f04ede41ef3c8261da88c0afb | 10,660 |
| net-platform-flags | libs/net-platform-flags.jar | a65b9ef41a2a5340c79840d42b0af2f2 | 9,328 |
| permission-flags | libs/permission-flags.jar | 0c1d34273ecbaa6b309f23b51ffe466d | 23,622 |
| provider-flags | libs/provider-flags.jar | 6a2ac2fc07b78126e4e2611686a3b4aa | 9,467 |
| security-flags | libs/security-flags.jar | fe4c6350e74010fddc3c230c3954ba0c | 17,736 |
| service-controls-flags | libs/service-controls-flags.jar | b3e9171df2672df2194dceb92024bb7d | 7,484 |
| service-notification-flags | libs/service-notification-flags.jar | d19b87d5aac8c1cb0aa8f11c7a09eab1 | 9,816 |
| quickaccesswallet-flags | libs/quickaccesswallet-flags.jar | 5da697f9b77eea536f0a49b42f3d3e75 | 8,006 |

## 结论

- 11 个同族 hazard 全部关闭：byte-identical 打包（11/11 sha256 MATCH）+ 接线 + APK 内
  每类恰好 1 处定义（24 dex 全扫，含 android/os/Flags 回归项）+ 设备 PID 稳定 ≥5min +
  零 NCDF + 状态栏渲染。验收 5 项全部达成。
- 复用配方（后续再遇同族时）：定位 AconfigFlags.bp 的 base 变体 `*-aconfig-java` →
  m -j4 构建 → `package_aconfig_jars.py` 注册 → 接线 → 部署。

### 遗留 / 跟进

- `pdvc_impl.txt`（repo 根，task053 scratch）未提交，provenance 不明，留给 chief 处置。
- 截图人工复核可选（本文以 dumpsys 结构证据为准）。
- `/tmp/task054-audit/`：`task055_dex_sweep.py`、`task055-m-build.log`、`logcat-task055.txt`、
  `task055-screen.png`（会话易失证据）。
