# 2026-08-25 — framework aconfig flags 单 JAR 合并（Task 057，方案 M）

> Worker: task057-worker（herdr tab `w2:t1R` pane `w2:p1X`）
> Brief: `docs/orchestration/tasks/057-aconfig-flags-single-jar-merge.md`
> 用户 2026-08-25 选定**方案 M**：把 task054/055 产出的 14 个 framework exportable-aconfig
> hidden-twin 族 runtime JAR 确定性合并为 `libs/systemui-aconfig-flags.jar`（1 文件 1 wiring）。

## 范围（14 个输入，全部显式 provenance）

| # | 配置名 | 来源 libs jar（task） | owning java_aconfig_library |
|---|---|---|---|
| 1 | window-flags | libs/window-flags.jar（053） | `com.android.window.flags.window-aconfig-java` |
| 2 | device-state-feature-flags | libs/device-state-feature-flags.jar（053） | `android.hardware.devicestate.feature.flags-aconfig-java` |
| 3 | android-os-flags | libs/android-os-flags.jar（054） | `android.os.flags-aconfig-java` |
| 4-14 | task055 11 个 | libs/{smartspace,content-pm,biometrics,usb,net-platform,permission,provider,security,service-controls,service-notification,quickaccesswallet}-flags.jar | 见 task055 报告全表 |

合并工具**直接读 AOSP javac 源**（`tools/aosp_paths.py` 单源），不经手 libs/ 副本（副本虽
byte-identical，直接从源合并使 provenance 显式）。每源先过五类 validator。

## 勘察事实（实施前）

- 每源结构：`META-INF/` + `META-INF/MANIFEST.MF`（45B）+ 目录条目 + 5 `.class` + 4 `.uau`
  （CustomFeatureFlags / FeatureFlags / FeatureFlagsImpl / Flags 的 `.uau`；
  `FakeFeatureFlagsImpl.uau` 不存在）。时间戳已是 Soong 确定性惯例 `2008-01-01 00:00`。
- **14/14 MANIFEST.MF 字节一致**（sha256 `5b85b9d6…`）→ 允许去重 1 份。
- 其他构建文件无 11 个新 jar 的引用（仅 `SystemUI-core/build.gradle.kts`）。
- `pdvc_impl.txt` = 118B 单行 python3 报错输出（task053 取证误存 scratch）→ 删除。

## 碰撞策略（对 brief "no overlapping pathnames, fail loudly" 的精确化）

| 条目类型 | 策略 | 理由 |
|---|---|---|
| `.class` / `.uau` | **任何 pathname 重叠即 fail**（即使字节相同） | 类路径重叠=归属模块错误，必须显式失败 |
| `META-INF/MANIFEST.MF` | 去重；字节不一致则 fail | 14 源结构性共享（已实测 14/14 一致） |
| 目录条目 | 并集去重 | zip 结构条目，无语义负载 |

## 确定性规则（验收项 1）

- 条目（目录+文件）**字典序排序**写出
- 固定时间戳 `(2008,1,1,0,0,0)`（沿 Soong 惯例）
- 固定压缩：`ZIP_DEFLATED, compresslevel=9`；显式 external_attr（文件 0o644<<16，目录 0o755<<16|0x10）
- 同输入连跑两次 → 同一 sha256（验收时贴出两个 hash）

## 工具设计

- `FRAMEWORK_FAMILY` frozenset：14 个配置名（单一机制，替代散标 family 字段）。
- 新 CLI 开关 `--merge-framework`：生成 `libs/systemui-aconfig-flags.jar`；
  与单 artifact / `--all` 三选一互斥（argparse 显式校验）。
- 核心函数拆分：`merge_sources(items=[(name, source, package)], destination)` 纯函数
  （便于测试）+ `merge_framework_family()` 从 CONFIGS/FRAMEWORK_FAMILY 装配。
- `--all` 语义家族化：合并族 1 次 + 逐包非族 7 个（systemui-shared/wifi/wm-shell/
  notification/launcher3/settingslib-widget/settingslib-selector），不再回写 14 个单 JAR。

## 实施记录

### 1. 工具与测试（✅）

- `tools/package_aconfig_jars.py`：新增 `FRAMEWORK_FAMILY`（14 名，单一归属机制）、
  `MERGED_FRAMEWORK_JAR=libs/systemui-aconfig-flags.jar`、`merge_sources(items, dst)`
  纯函数、`merge_framework_family()` 装配；CLI 三选一：单 artifact / `--all` /
  `--merge-framework`（互斥显式校验）。`--all` 家族化：族合并 1 次 + 非族 7 个逐包，
  不回写 14 个单 JAR（显式按名单独打包仍留作 provenance/调试口）。
- 测试：`write_runtime_jar` 补 manifest/.uau 使合成源逼近真实；新增
  `test_framework_family_membership_and_shape`（14 subtests）、`TestMergeSources`
  （确定性/并集+逐字节/同类路径即便字节相同也 fail/manifest 分歧 fail/manifest 去重
  5 用例）、`TestBatchAllFlag` 更新+新增（家族排除、`--merge-framework` 不逐拷、
  三选一互斥）。`uv run pytest tools/tests/ -q` → **243 passed, 52 subtests passed**。

### 2. 合并证据（验收项 1/2）

- 连跑两次 sha256 相同：
  `5b62958035e746eae36bde2e4ffaebb933d8b490edc6c0f65ba4bef198772174`
  `5b62958035e746eae36bde2e4ffaebb933d8b490edc6c0f65ba4bef198772174` → DETERMINISTIC ✅
- 158 条目 = 70 `.class`（14×5）+ 56 `.uau`（14×4）+ 1 manifest + 31 目录；总 783,657B。
- 逐条目对源 byte-identity：140 次读取比对 **mismatches=0，extras=[]**
  （`/tmp/task054-audit/t57-byteidentity.txt`）。
- **观察**：task053 两个源（window `eb7d63fd…`、device-state-feature `60f2e399…`）的当前
  树内字节与 task053 提交的 libs 副本（`b224bf8b…`/`3105d687…`）不同——task055 lunch
  sdk_phone64_x86_64 后 Soong 重构了这两个产物（aconfig 生成物随 release config 烘焙差异）；
  合并一律以当前 AOSP 源为准（brief 要求从源合并），功能由 §4 运行时验收兑现，且本 APK
  与 task055 已验 APK 逐字节相同（见下）提供额外回归保证。

### 3. 接线收敛 + 删除（验收项 4）

- `SystemUI-core/build.gradle.kts`：14 行旧 wiring + 3 段注释 → 1 段组注释 + 1 行：
  `implementation(files("${rootProject.projectDir}/libs/systemui-aconfig-flags.jar"))`（L250）。
  grep 14 个旧名 = 0 命中；族内 wiring 恰 1 行 ✅。
- `git rm` 14 个单 JAR（D 状态核验）；非族 flags jar 不动（systemui-flags、
  systemui-shared-flags、wifi-flags、wm-shell-flags、launcher3-flags、notification-flags、
  settingslib-{flags,media,widget,selector}、device-state-flags）。
- `pdvc_impl.txt`：内容 = 单行 `python3: can't open file '.../extract_methods.py': [Errno 2]`
  （task053 取证误存的 stderr 重定向，118B），确认为 scratch，已删除（未曾入库，无 git 变更）。

### 4. 重建 + dex 扫描（验收项 5）

- `./gradlew :app:assembleDebug` BUILD SUCCESSFUL（37s）。
- **APK 与 task055 已验 APK 逐字节相同**：sha256 `b827df78…8779`，204,921,594B。
  说明 R8/D8 只消费类字节（合并 JAR 内 126 个负载条目与 14 单 JAR 并集逐字节一致），
  容器布局不进 dex —— 合并内容保真的最强证据。
- `/tmp/task054-audit/task055_dex_sweep.py` 扩为 14 目标重扫：**14/14 defs=1，
  hidden twin defs = 0** ✅。

### 5. 部署 + 运行时验收（验收项 6）

- 设备在线 APK sha256 与新构建完全相同（`b827df78…`）→ 按字节而言无需重推（task055
  已按三段校验部署）；自 18:16 起同一进程 PID 835 持续运行。
- 正式验证窗（task057 于 18:41:28 清 logcat 后采样）：PID 835 稳定 11 采样×30s
  （18:41:28→18:46:28，恰好 5 分钟；进程总连续运行 >25min）；logcat 窗
  18:41:29→18:46:34（1,026 行，`/tmp/task054-audit/logcat-task057.txt`）：
  **NoClassDefFoundError(任意包)=0、FATAL EXCEPTION=0、alreadyRegistered=0**；
  `dumpsys window displays`：mStatusBar 窗口存在，statusBars insets 可见 ✅。
- `sys.boot_completed=1`（设备未因本任务重启——字节未变）。

## 结论

- 方案 M 落地：14 → 1（文件、wiring 行）且内容零漂移（70 类+56 .uau 逐字节对源一致、
  APK 与已验基线逐字节相同、设备验收全绿）。
- 复生入口：`uv run python tools/package_aconfig_jars.py --merge-framework`
  （`--all` 含族合并 + 非族逐包；单名打包留作 provenance 调试口，与接线无关）。
- 待办：本地 commit；056 brief 处置权在 chief。
