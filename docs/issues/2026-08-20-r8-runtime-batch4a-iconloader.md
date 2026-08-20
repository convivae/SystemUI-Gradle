# R8 Runtime Closure Batch 4A：iconloader Kotlin AAR

日期：2026-08-20

## 背景

Task 035 后，正式优化 Release 仍在 `:app:minifyReleaseWithR8` 阶段因 109 个 unique missing refs 失败。其中 3 项同属 `frameworks/libs/systemui/iconloaderlib`：

- `com.android.launcher3.icons.IconThemeController`
- `com.android.launcher3.icons.ThemedBitmap`
- `com.android.launcher3.icons.mono.ThemedIconDrawable`

当前 `libs/aars/iconloader.aar` 与本地 Maven `iconloader:1.0.0` 的 `classes.jar` 只有 Soong `javac/iconloader.jar` 的 59 个 Java class。AOSP `iconloader` target 同时声明 `src/**/*.java` 与 `src/**/*.kt`；其 `kotlin/iconloader.jar` 另有 16 个 Kotlin class，当前全部遗漏。Launcher3 aconfig runtime 已在 Task 034 通过 `libs/launcher3-flags.jar` 以 `implementation` 补齐，因此本批只修复 AAR 自身的 Kotlin implementation closure。

## 依赖判定

| 项目 | 判定 |
|---|---|
| owner | `frameworks/libs/systemui/iconloaderlib/Android.bp`，不属于 `packages/SystemUI/**` |
| tier | ② AOSP 非 SystemUI、含资源产物 |
| 交付 | 保持现有 local-Maven AAR 通道，重建 AAR 后安装新坐标 `com.android.systemui:iconloader:1.0.1` |
| scope | `SystemUI-core` 已是 `implementation(libs.systemui.iconloader)`，不新增或改变 scope |
| resources | 继续逐字节复制 AOSP `iconloaderlib/res`、manifest 与 Soong `R.txt`，禁止重写资源 |

用户已在当前对话明确批准将本地 iconloader AAR 从 `1.0.0` 升至 `1.0.1`，以避免同坐标缓存复用。旧 `1.0.0` 目录随替换删除，避免 orphan artifact。

## 设计

1. TDD 扩展 `tools/tests/test_package_aosp_aar.py`：先要求 iconloader config 精确包含 owning Soong 的 javac 与 Kotlin implementation JAR；验证输出 class 集/字节等于两输入的精确并集（59+16=75）、资源/manifest/R.txt 与来源逐字节一致、重复构建 byte-identical。
2. TDD 扩展 `tools/tests/test_install_aar_to_maven.py`：要求 iconloader registry 坐标精确为 `1.0.1`。
3. `tools/package_aosp_aar.py` 只为 iconloader config 加入 `android_common/kotlin/iconloader.jar`，沿用现有确定性 AAR 合并器。
4. `tools/install_aar_to_maven.py` 只将 iconloader 版本改为 `1.0.1`。
5. 重建 `libs/aars/iconloader.aar`，仅安装选定 artifact 到 `libs/maven/com/android/systemui/iconloader/1.0.1/`，删除旧 `1.0.0/`，并把 catalog 的 `systemui-iconloader` 指向 `1.0.1`。
6. fresh 验证 tests、debug duplicate/build、APK 定义和 R8 精确差分。

## 预期产物

- AAR `classes.jar`：75 个 class，精确等于：
  - javac input：59
  - Kotlin input：16
- class namespace：仅 `com/android/launcher3/**`。
- AAR 的 `res/**`、`AndroidManifest.xml`、`R.txt`：与 AOSP/Soong canonical inputs 逐字节一致。
- local Maven AAR 与 `libs/aars/iconloader.aar` byte-identical；POM 为无 dependencies 的 `aar` 骨架且版本为 `1.0.1`。
- 本地仓不保留旧 `iconloader/1.0.0`。

## 验收与预期 R8 差分

| 阶段 | 预期 |
|---|---|
| 改动前 fresh R8 | true exit 1；109 refs；三个目标均存在 |
| Python tests | 当前 160 基线 + 4 个新增测试 = 164，全部 `OK` |
| Debug | duplicate check + assembleDebug true exit 0 |
| APK | 三个目标类均有 `C d` defined row |
| 改动后 fresh R8 | true exit 1；**109→106**；精确移除三个目标；新增 0 |

`AssumeTrueForR8`、B1–B4、Traceur、SettingsLib、WM-Shell refs 必须保持，不在本批处理。若 R8 新增 ref、删除额外 ref，或最终不是 106，worker 必须保留 before/after 集并 REDLINE，不得添加 `dontwarn`、keep、源码排除或扩大 scope。

## 红线与禁止项

- 不修改任何 `SystemUI-*/src/**`、`SystemUI-*/res*/**` 或其他 `res/` 文件。
- 不修改 `SystemUI-core` dependency scope；它已经是正确的 `implementation`。
- 不添加 stub、keep/dontwarn、source exclusion、build bypass。
- 不使用 turbine/header/FAT JAR；只使用 owning Soong `javac` 与 `kotlin` implementation outputs。
- 不改 iconloader 之外的 AAR、Maven 坐标或依赖版本。
- 不实现 Traceur、SettingsLib、WM-Shell 或 B1–B4 bridge。

## 错误数演变

| 阶段 | R8 unique missing refs | 说明 |
|---|---:|---|
| Task 035 后 | 109 | fresh main baseline |
| 本批目标 | 106 | 精确移除 iconloader Kotlin 3 项，新增 0 |

## 实施记录

待 worker 填写真实输入/输出类数、SHA-256、测试数量、Gradle true exit、APK defined rows 和 R8 before/after 差分。正式优化 Release 在剩余 missing refs 清零前仍不得声明成功。

## 待解决问题

- 后续 A 类 closure：Traceur 7、WM-Shell proto 18、SettingsLib 74。
- A 类完成后处理 B1–B4 library/build classpath closure。
