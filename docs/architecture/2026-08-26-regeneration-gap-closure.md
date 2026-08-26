# 2026-08-26 — Task 064：libs/ 再生性 GAP 关闭报告（15 个产物）

**任务**: `docs/orchestration/tasks/064-regeneration-gap-closure.md`
**性质**: 再生管线补全。**未修改 libs/ 下任何现存文件**（基准只读）；未运行 Gradle（任务不适用构建门）；
验证 = `uv run pytest tools/tests/ -q`（275 passed）+ 生成到 /tmp 与基准 sha256 比对。
**姊妹文档**: `docs/issues/2026-08-26-regeneration-gap-closure.md`（当日记录）、
`docs/architecture/2026-08-26-tools-scripts-inventory-audit.md` §7（GAP 清单来源）。

## 1. 结论速览

15 个无再生脚本的 libs/ 产物全部纳入脚本管线：

- **13 个 MATCH**：脚本产出与现存 libs/ 基准**逐字节一致**（sha256 相同）
- **2 个 DIFF**：`framework-statsd.jar`、`android.car.jar` —— 现存基准在当前 AOSP 树中**没有任何
  逐字节来源**（2026-07 手工版来自旧树状态/手工类挑选）；已冻结最接近的规范 Soong 源，
  Phase C 决策"以脚本产出为准还是以现存为准"（两者均为 compileOnly 接线，替换低风险）

| # | 产物 | 再生脚本 | Soong 模块 | 冻结 intermediates 路径（`out/soong/.intermediates/` 下） | 结果 |
|---|------|---------|-----------|--------------------------------------------------------|------|
| 1 | `libs/settingslib-flags.jar` | `package_aconfig_jars.py settingslib-flags` | `aconfig_settingslib_flags_java_lib` | `frameworks/base/aconfig_settingslib_flags_java_lib/android_common/turbine-combined/aconfig_settingslib_flags_java_lib.jar` | **MATCH**（特殊重打包，见 §3） |
| 2 | `libs/settingslib-media-flags.jar` | `package_aconfig_jars.py settingslib-media-flags` | `settingslib_media_flags_lib` | `frameworks/base/packages/SettingsLib/settingslib_media_flags_lib/android_common/javac/settingslib_media_flags_lib.jar` | **MATCH** |
| 3 | `libs/device-state-flags.jar` | `package_aconfig_jars.py device-state-flags` | `device_state_flags_lib` | `frameworks/base/services/foldables/devicestateprovider/src/com/android/server/policy/feature/device_state_flags_lib/android_common/javac/device_state_flags_lib.jar` | **MATCH** |
| 4 | `libs/framework.jar` | `package_misc_jars.py framework` | `framework` | `frameworks/base/framework/android_common/turbine-combined/framework.jar`（与 build_sysuisdk 冻结映射 `framework_jar` 同源） | **MATCH** |
| 5 | `libs/framework-statsd.jar` | `package_misc_jars.py framework-statsd` | `framework-statsd.impl` | `packages/modules/StatsD/framework/framework-statsd.impl/android_common_apex30/javac/framework-statsd.jar` | **DIFF**（§4.1） |
| 6 | `libs/android.car.jar` | `package_misc_jars.py android.car` | `android.car` | `packages/services/Car/car-lib/android.car/android_common/turbine-combined/android.car.jar` | **DIFF**（§4.2） |
| 7 | `libs/android_module_lib_stubs_current.jar` | `package_misc_jars.py android_module_lib_stubs_current` | `android_module_lib_stubs_current` | `frameworks/base/api/android_module_lib_stubs_current/android_common/turbine-combined/android_module_lib_stubs_current.jar` | **MATCH** |
| 8 | `libs/SystemUI-proto.jar` | `package_misc_jars.py SystemUI-proto` | `SystemUI-proto` | `frameworks/base/packages/SystemUI/SystemUI-proto/android_common/javac/SystemUI-proto.jar` | **MATCH** |
| 9 | `libs/SystemUI-statsd.jar` | `package_misc_jars.py SystemUI-statsd` | `SystemUI-statsd` | `frameworks/base/packages/SystemUI/shared/SystemUI-statsd/android_common/javac/SystemUI-statsd.jar` | **MATCH** |
| 10 | `libs/SystemUI-tags.jar` | `package_misc_jars.py SystemUI-tags` | `SystemUI-tags` | `frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar` | **MATCH** |
| 11 | `libs/contextualeducationlib.jar` | `package_misc_jars.py contextualeducationlib` | `contextualeducationlib` | `frameworks/libs/systemui/contextualeducationlib/contextualeducationlib/android_common/kotlin/contextualeducationlib.jar` | **MATCH** |
| 12 | `libs/msdl.jar` | `package_misc_jars.py msdl` | `msdl` | `frameworks/libs/systemui/msdllib/msdl/android_common/kotlin/msdl.jar` | **MATCH** |
| 13 | `libs/PlatformMotionTestingComposeValues.jar` | `package_misc_jars.py PlatformMotionTestingComposeValues` | `PlatformMotionTestingComposeValues` | `platform_testing/libraries/motion/compose/values/PlatformMotionTestingComposeValues/android_common/kotlin/PlatformMotionTestingComposeValues.jar` | **MATCH** |
| 14 | `libs/keepanno-annotations.jar` | `package_misc_jars.py keepanno-annotations` | `keepanno-annotations` | `prebuilts/r8/keepanno-annotations/android_common/combined/keepanno-annotations.jar`（与 build_sysuisdk 冻结映射 `keepanno_jar` 同源） | **MATCH** |
| 15 | `libs/prebuilts/tracinglib-platform.jar` | `package_misc_jars.py tracinglib-platform` | `tracinglib-platform` | `frameworks/libs/systemui/tracinglib/core/tracinglib-platform/android_common/kotlin/tracinglib-platform.jar` | **MATCH** |

冻结 sha256（源与基准同值，除 2 个 DIFF 外）逐条内嵌于 `tools/package_misc_jars.py` CONFIGS。

## 2. 新脚本使用说明（Phase C runbook 引用）

### 2.1 `tools/package_misc_jars.py`（新建）

```bash
# 全量再生 12 个 misc jar（默认写入仓库根，即真实 libs/ 路径）
python3 tools/package_misc_jars.py --all

# 单个再生
python3 tools/package_misc_jars.py framework

# 只校验现存 libs/ 与冻结基准指纹是否一致（不读 AOSP、不写盘）
python3 tools/package_misc_jars.py --verify-only

# Phase C 门禁辅助：任一产物与基准 DIFF 即退出 1
python3 tools/package_misc_jars.py --all --require-match

# 重指 AOSP 树（或 AOSP_ROOT 环境变量；默认走 tools/aosp_paths.py）
python3 tools/package_misc_jars.py --all --aosp-root /path/to/aosp
```

行为要点：

- **冻结映射纪律**（仿 build_sysuisdk 八输入）：精确相对路径，无 glob、无 newest-file 回退；
  缺文件即报错
- 每条目冻结 `source_sha256`（映射冻结日的 AOSP 产物指纹）：源漂移时打印 warning 但照常生成
  （AOSP sync 后属预期）
- 每条目冻结 `baseline_sha256`（当日 libs/ 基准指纹）：生成后输出 `MATCH`/`DIFF`
- 生成走临时文件 + 原子 rename；`--output-root` 可把产物导到 /tmp 验证（本任务即如此，libs/ 零改动）

### 2.2 `tools/package_aconfig_jars.py`（扩展）

新增三条 CONFIGS/特殊条目：

- `settingslib-media-flags`、`device-state-flags`：常规 javac 直拷（五类校验照旧）
- `settingslib-flags`：`TURBINE_BASELINE_CONFIGS` + `repack_baseline_stub_jar()`（见 §3）

```bash
python3 tools/package_aconfig_jars.py settingslib-flags
python3 tools/package_aconfig_jars.py settingslib-media-flags
python3 tools/package_aconfig_jars.py device-state-flags
# --all 现在也会处理这三条（settingslib-flags 走重打包路径）
```

## 3. settingslib-flags 的特殊性（唯一 turbine 来源 + 基准字节重打包）

- 模块 `aconfig_settingslib_flags_java_lib`（framework-minus-apex-aconfig-java-defaults 家族，
  `frameworks/base/AconfigFlags.bp:1816`）在当前构建**只有 turbine 产物、没有 javac 产物**
  （intermediates 下仅 gen/turbine/turbine-combined；同为家族的 window-flags 等有 javac）
- 现存 `libs/settingslib-flags.jar` 的 5 个 class 与 turbine-combined **逐字节相同**（javap 证实
  为无方法体 stub）；外层是 2026-07-29 手工 jar 工具包装（`Created-By: 25.0.2 (Oracle Corporation)`）
- 该 jar 为 core **compileOnly** 接线，stub 无方法体不影响编译
- `repack_baseline_stub_jar()` 按 JDK jar 工具字节格式确定性重建（UTF-8+DD flag、DOS
  create_system、首 entry 0xCAFE extra、zlib level 6、带签名的 data descriptor），
  **输出与基准逐字节一致**（sha256 `829fa4e5…` 验证 MATCH）
- 既有 `copy_jar` 的"禁止 turbine"守卫在此被显式越过并文档化：基准本身就是 turbine stub；
  五类运行时类校验仍然生效

## 4. DIFF 分析（2 个，Phase C 决策输入）→ 已由 Task 065 关闭（见 §4.4）

### 4.1 `framework-statsd.jar`

- **基准形态**：39 个 class（`android.app` StatsManager 系、`android.os` IStats* AIDL stub、
  `android.util` StatsLog/StatsEvent、`com.android.internal.statsd.StatsdStatsLog），
  API-stub 形态（StatsLog 无 private 常量/`writeImpl` native）
- **当前树无逐字节来源**：遍历 `framework-statsd*` 全部 18 个 soong 产物 +
  `prebuilts/sdk/current/{system,module-lib,public}` 三变体（14/15/2 entries），无一与基准类名集相同；
  最接近的是 `framework-statsd.impl` javac（61 entries，**类名超集**——基准 39 个类名全部在内，
  但字节全不同：当前源码新增了 ANNOTATION_ID_* 常量、`loadNativeLibrary` 等漂移）
- **冻结源**：`framework-statsd.impl/android_common_apex30/javac/framework-statsd.jar`（真实实现类，
  类名超集，compileOnly 场景语义更完整）
- **Phase C 选项**：(a) 以冻结源替换基准（推荐——更完整且可再生）；(b) 保留基准（不可再生，
  违背复现目标）

### 4.2 `android.car.jar`

- **基准形态**：678 个 STORED entry、无 manifest、无方法体 stub（javap 证实 Car.class 0 个 Code）
- **当前树只有 turbine 产物**：`android.car`（java_library，`packages/services/Car/car-lib/Android.bp:96`）
  的 intermediates 下仅 turbine/turbine-combined，无 javac（本产品构建图中无人触发其字节码编译）
- **基准是旧树状态产物**：与当前 turbine-combined（1219 class，含 static dep `com.android.car.internal.dep`
  closure）共享 664 个类名但 **0 个逐字节相同**；基准含 14 个当前 car-lib 已消失的类
  （`ICarBluetooth*`、`IPerUserCarService*`、`ExperimentalCarUserManager`、`CarRatedFloatListeners` 等）
- **冻结源**：`android.car/android_common/turbine-combined/android.car.jar`（stub 类；core compileOnly
  接线可用）
- **Phase C 选项**：同 4.1；(a) 替换为冻结源（1219 类超集，含 AIDL stub，可满足编译引用）为推荐项

### 4.3 framework.jar 敏感性说明（brief 特别要求）

`framework.jar` 被 12 个 module compileOnly + 根 build.gradle.kts JavaCompile classpath 引用。
本次验证为 **MATCH**（turbine-combined 与基准逐字节一致，sha256 `0fe39d80…`），不存在版本漂移；
AOSP 后续 sync 若致漂移，`package_misc_jars.py` 的源指纹 warning 即早期信号。

### 4.4 Phase C 决议与执行（Task 065，2026-08-26）

**用户拍板（2026-08-26）**：无法从 AOSP 再生的 jar 一律不用 —— 选 **option (a)：以脚本冻结源产出替换基准**。
执行（`docs/issues/2026-08-26-diff-jar-replacement-and-gates.md`，commit `fee014cd`）：

**新 sha256 台账**：

| jar | 旧基准（手工拷贝） | 新基准（脚本产出 = 冻结源） | 形态变化 |
|-----|--------------------|------------------------------|----------|
| `libs/framework-statsd.jar` | `d54489ee…`（39 entries，API stub） | `058f30a1…`（70 entries，impl javac 真实类，类名超集） | compileOnly，语义更完整 |
| `libs/android.car.jar` | `bd5faa75…`（678 stored stub，含 14 个上游已删类） | `89f04e0a…`（1219 turbine-combined stub 含 dep closure） | compileOnly，超集 |

`package_misc_jars.py` 两条目 baseline 重新冻结为源指纹，`--verify-only` 12/12 MATCH；
测试同步改为钉住“零 DIFF 基线 + 替换后 sha”。

**双门验证结果（全部通过）**：

1. **构建门（串行，clean）**：`:app:assembleDebug` 229/229 executed → BUILD SUCCESSFUL，
   APK sha256 `e8aad131…`（163,896,493 B，与替换前基线**逐字节一致** —— compileOnly
   jar 只影响编译签名，符号引用未变）；`:app:assembleRelease` 318 executed →
   BUILD SUCCESSFUL，APK sha256 `d3968fb2…`（34,688,965 B，与旧 Release 基线
   `14768581…` 同尺寸不同字节，R8 输出漂移；**此为新 Release 基线**）。
   apksigner v2 验签通过。
2. **Debug 运行门**（emulator-5554，staged 部署 `e8aad131…`）：boot_completed=1；
   部署后设备端 sha MATCH；PID 821 稳定 2×30s；crash buffer 0 行、全量 logcat
   FATAL/NCDFE=0；dumpsys windows：StatusBar/NotificationShade/Taskbar/ImageWallpaper
   全在。
3. **Release 运行门**（staged 部署 `d3968fb2…`）：boot_completed=1；设备端 sha MATCH；
   PID 840 稳定 2×30s；crash buffer 0 行、FATAL/NCDFE=0；窗口三件套全在；
   bonus `cmd statusbar expand-settings/collapse` 无崩溃、PID 不变。
4. **对齐门 + pytest**：`check_source_alignment.py --strict` MISSING/MISPLACED/EXTRA
   = 0-0-0（MODIFIED 1 + RES-MODIFIED 86 为 ADR 0004 已知基线）；
   `uv run pytest tools/tests/ -q` → **276 passed, 102 subtests**。

设备终态：Release `d3968fb2…` 在机上（新基线）。

## 5. W3：硬编码 AOSP 路径治理（aosp_paths 单一来源，用户规则 2026-08-25）

| 脚本 | 改造 | 行为变化 |
|------|------|---------|
| `package_aosp_aar.py` | `AOSP_ROOT = aosp_paths.aosp_root()`；新增 `--aosp-root` + `configure_aosp_root()`（CONFIGS 抽为 `_build_configs()` 按调用时全局重建） | 默认路径不变；新增 CLI 能力 |
| `package_compilelib_jars.py` | 同上（`configure_aosp_root` 重指 DEBUG/RELEASE_SRC） | 默认路径不变 |
| `check_source_alignment.py` | `AOSP_ROOT = aosp_root() / "frameworks/base/packages/SystemUI"`；新增 `--aosp-root`（树根） | 默认路径不变（实测 `--summary` 输出与改造前一致：MISSING/MISPLACED/EXTRA 全 0，MODIFIED 1+86 为 ADR 0004 已知基线） |
| `package_monet_jar.py` | default 改 `aosp_paths.aosp_root()`（保留既有 `--aosp-root` CLI） | 默认路径不变；新增 AOSP_ROOT env 覆盖能力 |
| `package_viewcapture_motiontool_jars.py` | 同上 | 同上 |

配套：5 个相关测试文件补 `sys.path` 插入（脚本 import aosp_paths 所需，沿用
test_package_aconfig_jars.py 既有模式）；`test_package_aosp_aar.py` 新增
`TestAospRootSingleSource`（含 `configure_aosp_root` 重建断言）。

## 6. 测试（W4）

- 新增 `tools/tests/test_package_misc_jars.py`：冻结映射完整性（12 条、模块名、目标路径、
  relpath 纪律、sha 格式、已知 DIFF 集合恰为 {framework-statsd, android.car}、
  与 build_sysuisdk 同源双条目钉住）、generate MATCH/DIFF/漂移 warning/缺源报错、
  verify_only 三态、CLI 互斥与 `--require-match` 退出码、aosp_paths 集成
- `test_package_aconfig_jars.py` 新增 `TestTask064Configs`（三条目形状）+
  `TestRepackBaselineStubJar`（确定性、Oracle manifest、类字节保全、缺类/带 manifest 拒绝）+
  `--all` 对 TURBINE_BASELINE 的 dispatch 测试；既有 `--all` 测试补 mock
  `TURBINE_BASELINE_CONFIGS`（防止误触真实 AOSP 树）
- 全套：`uv run pytest tools/tests/ -q` → **275 passed, 102 subtests**（改造前 245 passed）

## 7. 验证证据汇总

- `uv run pytest tools/tests/ -q` → 275 passed
- 15 产物逐一再生到 /tmp（`package_aconfig_jars.py` ×3 + `package_misc_jars.py --all --output-root /tmp/gapcheck/final`），
  与 libs/ 基准 sha256 比对：13 MATCH / 2 DIFF（§1 表）
- `python3 tools/package_misc_jars.py --verify-only` → 12/12 基准指纹完好（libs/ 未被触碰的旁证）
- `git status` → libs/ 与 *.kts/*.toml 零改动
- `python3 tools/check_source_alignment.py --summary` → 与改造前一致
- Gradle 构建：**未运行**（本任务无构建需求；验证以 pytest + sha 比对为准）

## 8. 遗留（Phase C 输入）

1. ~~`framework-statsd.jar` / `android.car.jar` 的“脚本产出 vs 现存基准”取舍~~ **已解决**：
   Task 065 用户拍板 option (a) 替换为冻结源，双门验证全过（§4.4）
2. AOSP sync 后重跑 `package_misc_jars.py --all` 会触发源指纹 warning：属预期流程
   （重新生成 → 比对 → 必要时更新冻结指纹），runbook 应写明
3. `tools/install_keystore.sh` 的 .py 转换欠账（ADR 0002，不在本任务范围）
