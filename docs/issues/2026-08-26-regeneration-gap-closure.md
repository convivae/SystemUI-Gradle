# 2026-08-26 — Task 064：关闭 15 个 libs/ 产物再生性 GAP（Phase C 前置）

## 背景

审计 `docs/architecture/2026-08-26-tools-scripts-inventory-audit.md` §7 发现 libs/ 28 个根目录 jar 中
15 个没有任何再生脚本（2026-07 时代手工 cp）。本任务让每个保留产物都能从 AOSP `out/` 产物脚本化再生。

Brief: `docs/orchestration/tasks/064-regeneration-gap-closure.md`。
约束：不改 libs/ 现存任何 jar（基准，只读比对）；不跑 Gradle；pytest 验证。

## AOSP 溯源结论（15 个产物）

| # | 产物 | Soong 模块 | intermediates 相对路径 | 基准 sha256 比对 |
|---|------|-----------|----------------------|------------------|
| 1 | settingslib-flags.jar | `aconfig_settingslib_flags_java_lib` | `frameworks/base/aconfig_settingslib_flags_java_lib/android_common/turbine-combined/aconfig_settingslib_flags_java_lib.jar` | MATCH（经 jar-tool 格式重打包，见下） |
| 2 | settingslib-media-flags.jar | `settingslib_media_flags_lib` | `frameworks/base/packages/SettingsLib/settingslib_media_flags_lib/android_common/javac/settingslib_media_flags_lib.jar` | MATCH（直接拷贝） |
| 3 | device-state-flags.jar | `device_state_flags_lib` | `frameworks/base/services/foldables/devicestateprovider/src/com/android/server/policy/feature/device_state_flags_lib/android_common/javac/device_state_flags_lib.jar` | MATCH（直接拷贝） |
| 4 | framework.jar | `framework` | `frameworks/base/framework/android_common/turbine-combined/framework.jar`（与 build_sysuisdk 冻结映射同源） | MATCH |
| 5 | framework-statsd.jar | `framework-statsd.impl` | `packages/modules/StatsD/framework/framework-statsd.impl/android_common_apex30/javac/framework-statsd.jar` | **DIFF**（见"DIFF 分析"） |
| 6 | android.car.jar | `android.car` | `packages/services/Car/car-lib/android.car/android_common/turbine-combined/android.car.jar` | **DIFF**（见"DIFF 分析"） |
| 7 | android_module_lib_stubs_current.jar | `android_module_lib_stubs_current` | `frameworks/base/api/android_module_lib_stubs_current/android_common/turbine-combined/android_module_lib_stubs_current.jar` | MATCH |
| 8 | SystemUI-proto.jar | `SystemUI-proto` | `frameworks/base/packages/SystemUI/SystemUI-proto/android_common/javac/SystemUI-proto.jar` | MATCH |
| 9 | SystemUI-statsd.jar | `SystemUI-statsd` | `frameworks/base/packages/SystemUI/shared/SystemUI-statsd/android_common/javac/SystemUI-statsd.jar` | MATCH |
| 10 | SystemUI-tags.jar | `SystemUI-tags` | `frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar` | MATCH |
| 11 | contextualeducationlib.jar | `contextualeducationlib` | `frameworks/libs/systemui/contextualeducationlib/contextualeducationlib/android_common/kotlin/contextualeducationlib.jar` | MATCH |
| 12 | msdl.jar | `msdl` | `frameworks/libs/systemui/msdllib/msdl/android_common/kotlin/msdl.jar` | MATCH |
| 13 | PlatformMotionTestingComposeValues.jar | `PlatformMotionTestingComposeValues` | `platform_testing/libraries/motion/compose/values/PlatformMotionTestingComposeValues/android_common/kotlin/PlatformMotionTestingComposeValues.jar` | MATCH |
| 14 | keepanno-annotations.jar | `keepanno-annotations` | `prebuilts/r8/keepanno-annotations/android_common/combined/keepanno-annotations.jar`（与 build_sysuisdk 冻结映射同源） | MATCH |
| 15 | prebuilts/tracinglib-platform.jar | `tracinglib-platform` | `frameworks/libs/systemui/tracinglib/core/tracinglib-platform/android_common/kotlin/tracinglib-platform.jar` | MATCH（现盘文件 = 原始 kotlin jar，未过 clean_prebuilts 清洗） |

### settingslib-flags 的特殊性（唯一非 javac 来源）

`aconfig_settingslib_flags_java_lib`（framework-minus-apex-aconfig-java-defaults 家族）在当前构建里
**只有 turbine 产物，没有 javac 产物**。现存 libs/settingslib-flags.jar 的 5 个 class 与
turbine-combined 逐字节相同（sha 验证），外层是 2026-07-29 手工 jar 工具包装（Oracle Created-By manifest）。
该 jar 为 core compileOnly 接线，turbine stub（无方法体）不影响编译。新增的重打包函数按 jar 工具
字节格式（UTF-8+DD flag、DOS create_system、0xCAFE extra 于首 entry）确定性重建，与基准逐字节一致。

### DIFF 分析（2 个）

**framework-statsd.jar**：现存 jar（39 class，API-stub 形态：StatsLog 无 private 常量/native impl）
在当前 AOSP 构建中**没有任何逐字节来源**；最接近的是 `framework-statsd.impl` javac（61 entries，
类名超集，含全部 39 个基准类名，但字节全不同——源码含新 annotation 常量等漂移）。prebuilts/sdk
三变体（system/module-lib/public，14/15/2 entries）类名集即不足。判定：当年手工版来自旧树状态的
类挑选；Phase C 需决策以 impl javac（当前冻结源）替换或保留基准。

**android.car.jar**：`android.car` 模块当前构建只有 turbine 产物（1219 class，含 static dep closure）。
现存 jar（678 个 STORED entry，同为无方法体 stub）与 turbine 无任何逐字节相同 entry，且含 14 个
已从当前 car-lib 消失的类（ICarBluetooth、IPerUserCarService、ExperimentalCarUserManager 等）——
证明它是 2026-07 旧树状态的产物。compileOnly 接线，turbine stub 可用；Phase C 决策同上。

## 工作项

- W1: `tools/package_aconfig_jars.py` CONFIGS + settingslib-media-flags/device-state-flags 两条常规条目
  + settingslib-flags 特殊重打包条目（TURBINE_BASELINE_CONFIGS + `repack_baseline_stub_jar`）
- W2: 新建 `tools/package_misc_jars.py`：12 条冻结映射（模块名/intermediates 路径/目标路径/基准 sha256/
  源 sha256），生成 + 与 libs/ 基准 sha256 比对输出 MATCH/DIFF；`--aosp-root` 走 aosp_paths
- W3: 硬编码路径治理——package_aosp_aar / package_compilelib_jars / check_source_alignment 加
  `--aosp-root` 并默认走 aosp_paths；package_monet_jar / package_viewcapture_motiontool_jars 默认值
  改走 aosp_paths
- W4: 新脚本单测 + 全套 pytest 全绿

## 验证

- `uv run pytest tools/tests/ -q` 全绿
- 生成到 /tmp/gapcheck/out，与 libs/ 逐一 sha256 比对（结果表见上）
- `git status` 确认 libs/ 零改动
- 未运行 Gradle（本任务不适用构建门）
