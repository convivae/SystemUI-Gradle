# Task 054 — android.os.Flags Runtime Closure

**Date**: 2026-08-25 · **Worker**: herdr task054 · **Brief**: `docs/orchestration/tasks/054-android-os-flags-runtime-closure.md`

## 背景

Debug APK crash-loop：NLSUMI 首次构造时 `privateSpaceFlagsEnabled()`（源码行 844，
`import static android.os.Flags.allowPrivateProfile`）抛
`NoClassDefFoundError: Landroid/os/Flags;`。

根因（chief 已确认，不重新调查）：模拟器 `/system/framework/framework.jar` 只定义
`Lcom/android/internal/hidden_from_bootclasspath/android/os/Flags;`（JarJar 重写后的隐藏名），
公开名 `Landroid/os/Flags;` 在设备 bootclasspath 上不存在。AOSP stock SystemUI 经 Soong
JarJarProvider 重写引用隐藏名；AGP 不继承该重写，我们的字节码引用公开名 → 运行期类缺失。

这是同族第三例（先例：`window-flags.jar` 2026-08-24、`device-state-feature-flags.jar`），
修复方案沿用：把 owning Soong `java_aconfig_library` 的 javac JAR **byte-identical** 打包进
`libs/`，并在 `SystemUI-core/build.gradle.kts` 加 `implementation(files(...))`。

## 变体选择（证据）

两个候选 Soong javac JAR 都含 `android/os/` 下五个 runtime 类：

| 变体 | FeatureFlagsImpl backing API | 设备 bootclasspath 是否定义 |
|---|---|---|
| **base** `android.os.flags-aconfig-java/.../android.os.flags-aconfig-java.jar` | `Landroid/os/flagging/PlatformAconfigPackageInternal;`（`load(String,J)` + `getBooleanFlagValue(I)Z`） | ✅ 定义（见下） |
| export `android.os.flags-aconfig-java-export/.../android.os.flags-aconfig-java-export.jar` | `Landroid/os/flagging/AconfigPackage;`（`load(String)` + `getBooleanFlagValue(String,Z)Z`） | ❌ **未定义** |

证据命令与输出（同树设备 framework：
`/home/conv/myspace/aosp/out/target/product/emu64x/system/framework/framework.jar`，
44,980,102 bytes）：

```text
$ javap -c -p android.os.FeatureFlagsImpl   # base 变体
  invokestatic  PlatformAconfigPackageInternal.load:(Ljava/lang/String;J)Landroid/os/flagging/PlatformAconfigPackageInternal;
  invokevirtual PlatformAconfigPackageInternal.getBooleanFlagValue:(I)Z

$ javap -c -p android.os.FeatureFlagsImpl   # export 变体
  invokestatic  AconfigPackage.load:(Ljava/lang/String;)Landroid/os/flagging/AconfigPackage;
  invokevirtual AconfigPackage.getBooleanFlagValue:(Ljava/lang/String;Z)Z

$ dexdump framework.jar | grep "Class descriptor.*android/os/flagging/" | sort -u
  Class descriptor  : 'Landroid/os/flagging/PlatformAconfigPackage;'
  Class descriptor  : 'Landroid/os/flagging/PlatformAconfigPackageInternal;'
  # 没有 AconfigPackage —— export 变体的 backing API 在设备上缺失

$ dexdump framework.jar | grep -A… PlatformAconfigPackageInternal   # 成员方法
  name : 'load'
  name : 'getBooleanFlagValue'
```

SysUISdk `android.jar` 同时含 `android/os/flagging/PlatformAconfigPackageInternal.class`
（编译期 OK）；其 `android/os/Flags.class` 为公开 stub，与设备 bootclasspath 公开名缺失
正好对应本任务修复的 compile/runtime 偏差。

**结论：选 base 变体** —— ① 遵循 window-flags 先例（rule 1）；② 其 backing API
`PlatformAconfigPackageInternal` 已验证存在于设备 framework.jar（rule 2）；export 变体会把
crash 从 `android/os/Flags` 搬到 `android/os/flagging/AconfigPackage`。

## 实施步骤记录

### 1-3. 打包与测试（✅）

- `tools/package_aconfig_jars.py` CONFIGS 新增 `android-os-flags`（base 变体）。
- 同时按用户新规则完成工具链改造：`tools/aosp_paths.py` 统一 AOSP 根（DEFAULT +
  `AOSP_ROOT` env + 显式 override 三级优先），packager 与测试改从统一来源派生；
  Python 一律 `uv run`（repo root `pyproject.toml` + `uv add --dev pytest`，`uv.lock`
  入库）；`.gitignore` 增 `.venv/`、`.pytest_cache/`、`*.egg-info/`。
- `uv run python tools/package_aconfig_jars.py android-os-flags` 产出与 AOSP 源
  **byte-identical**：
  `116d5b6f4b92a7b1b7f1c26322779d947d904aaf72eb73757aaea32175164acf`（两侧相同）。
  validator 通过 → 恰好五个 runtime `.class`（`.uau` 元数据按设计忽略）。
- `uv run pytest tools/tests/test_package_aconfig_jars.py -q` → **16 passed, 16 subtests passed**；
  全量 `tools/tests/` → **228 passed**。

### 4-5. 接线与 TEMP-DEBUG 移除（✅）

- `SystemUI-core/build.gradle.kts`：在 device-state-feature-flags 块后加
  `implementation(files("${rootProject.projectDir}/libs/android-os-flags.jar"))`
  （同款中文注释，注明 JarJarProvider 与 base 变体 backing API 验证结论）。
- 三个 task053 TEMP-DEBUG 文件经 `git restore` 恢复到已入库的 AOSP 对齐版：
  - `diff` vs `/home/conv/myspace/aosp/.../SystemUI/src/...` → 三文件全部 **identical**
    （零 `TEMP-DEBUG`/`SysUIDup` 残留）。
  - `uv run python tools/check_source_alignment.py --strict`：
    **MISSING=0, MISPLACED=0, EXTRA=0**；MODIFIED=1 为既有 CONV 标记文件
    `SystemUI-shared/.../UncaughtExceptionPreHandlerManager.kt`（与本次无关，strict 不卡
    MODIFIED，ADR 0004）；RES-MODIFIED=86 同为既有存量。exit=0。

### 6. 构建与 dex 验证（✅）

- `./gradlew :app:assembleDebug` → **BUILD SUCCESSFUL in 1m 26s**（构建前确认无并发 gradle）。
- 新 APK（24 dex）中 `Landroid/os/Flags;` **定义恰好 1 处**：classes.dex（无重复定义）。

### 7. 同族 hazard 预扫描（✅ 完成，见下表）

方法：APK 每个 dex 的字符串池正则提取 `L(android|com/android/internal)/.../Flags;`
（type 引用全集）；dexdump `Class descriptor` 得 APK 定义集与设备定义集
（设备 `$BOOTCLASSPATH` 45 条目的同树 emu64x 副本 + framework.jar）。
Hazard = APK 引用但 APK 与设备都不定义。

| 引用包 | APK 定义 | 设备公开名 | 设备隐藏 twin | 结论 |
|---|---|---|---|---|
| android/os | classes.dex ×1 | ❌ | ✅ | **本任务修复（BUNDLED）** |
| android/hardware/devicestate/feature/flags | classes.dex ×1 | ❌ | ✅ | 已修（task053） |
| android/adaptiveauth, android/app, android/appwidget/flags, android/multiuser, android/net/wifi/flags, android/service/dreams, android/tracing, android/view/accessibility, android/view/flags, android/view/inputmethod, android/webkit, android/widget/flags, com/android/internal/camera/flags, com/android/internal/telephony/flags | — | ✅ | — | device-provided |
| android/app/smartspace/flags | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/content/pm | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/hardware/biometrics | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/hardware/usb/flags | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/net/platform/flags | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/permission/flags | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/provider | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/security | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/service/controls/flags | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/service/notification | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |
| android/service/quickaccesswallet | ❌ | ❌ | ✅ | ⚠️ 残留 hazard |

**11 个残留 hazard 全部确认同族**（设备上只有 `hidden_from_bootclasspath` twin，无公开名）。
它们是懒加载触发——只有对应 flag 调用路径在运行期首次执行才会抛
`NoClassDefFoundError`。修复方式与本案相同（逐一打包 owning Soong javac JAR），
按“一次一个根因”族策略留待后续任务。

审计脚本：`/tmp/task054-audit/prescan_flags.py`、`/tmp/task054-audit/augment.py`。

### 8. 部署与运行时验证（✅ 本任务目标已修复；⚠️ 下一族成员成为新首因）

部署（emulator-5554，`adb devices` 仅此一台，qemu=1/emu64x/x86_64）：

1. `adb root` → `disable-verity`（成功）→ reboot → `wait-for-device` → `adb root`
   → `su 0 mount -o remount,rw /system_ext`。
2. **空间问题与绕行**：/system_ext 为 overlay（261M 总，仅 44M 可用，上有 task053
   候选 165,142,154B）；新 debug APK 204,916,105B，同分区 tmp+mv 原子替换放不下。
   改经 /data 中转（5.2G 可用）：push 到 `/data/local/tmp/SystemUI.apk` 并核 sha256
   → 删除旧候选 → `cp` 到目标路径 → 再核 sha256。三步校验一致：
   `98e2402de5f1b4b1945a84b97013f679a4090acdc936722d2ffb2423caaed793`。
3. 恢复 `root:root` `0644` `u:object_r:system_file:s0`（`ls -lZ` 已核）；删
   `oat/` 与 dalvik-cache；reboot。

验证（boot 后采样，`logcat -d` 21,321 行全文分析）：

| 验收项 | 结果 |
|---|---|
| `sys.boot_completed=1` | ✅ |
| `NoClassDefFoundError: android/os/Flags` | ✅ **0 次**（修复目标） |
| DumpManager `alreadyRegistered` 重复注册 crash | ✅ **0 次**（仅 2 条 cameraserver HAL 噪声，与 SystemUI 无关；task053 取证 §3.3 预测获证：android/os/Flags 可加载后 NLSUMI 构造成功、注册一次） |
| `SysUIDup` 插桩日志 | ✅ 0 次（插桩已移除） |
| SystemUI PID 稳定 ≥5min | ❌ **每 ~30s 换 PID（7 次 FATAL）** —— 见下 |

**当前唯一 crash 首因**（7 次 FATAL 全部同一根因，无其他签名）：

```text
java.lang.NoClassDefFoundError: Failed resolution of: Landroid/service/notification/Flags;
  at NotificationSectionsManager.reinflateViews(NotificationSectionsManager.kt:321)
  at NotificationSectionsManager.initialize(NotificationSectionsManager.kt:117)
  at NotificationStackScrollLayout.<init>(NotificationStackScrollLayout.java:650)
  → InflateException: layout/super_notification_shade → notification_stack_scroll_layout
ClassNotFoundException: class "android.service.notification.Flags" not found on
  DexPathList[[zip file "/system_ext/priv-app/SystemUI/SystemUI.apk"]...]
```

这正是本任务预扫描报告的 11 个残留 hazard 之一（`android/service/notification`，
同族：设备仅有 hidden twin），位于通知栈布局 inflate 的启动关键路径。

**超出本 brief Authority**：brief 仅授权新建 `libs/android-os-flags.jar`；打包
`android.service.notification` 对应 JAR 属下一任务（建议 Task 055，同法处理）。
补充情报：Soong owning target `android.service.notification.flags-aconfig-java`
的 `android_common/javac/` JAR **在当前 AOSP 树尚未构建**（仅有 codegen 的
`.srcjar`），需先在 AOSP 侧 `m android.service.notification.flags-aconfig-java`。

证据文件：
- 完整 boot logcat：`/tmp/task054-audit/logcat-since-boot.txt`
- 部署 APK（本地副本）：`app/build/outputs/apk/debug/app-debug.apk`
  sha256 `98e2402d…ed793`（设备同值）
- stock 恢复点：`/home/conv/myspace/task053-same-tree-x86_64-runtime/deploy/stock-backup/SystemUI.apk`

## 结论

Task 054 目标达成：`android/os/Flags` 运行时闭包修复（jar byte-identical、单一定义、
NCDF 清零、task053 重复注册 crash 随之消失），task053 TEMP-DEBUG 全部移除且源对齐
归零，同族 11 个残留 hazard 已定位并报告。PID 稳定验收项被下一族成员
（`android/service/notification/Flags`，boot 关键路径）阻塞——**brief 内无解**，
上报 chief 决定是否立即派 Task 055。
