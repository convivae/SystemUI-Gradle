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
| Task 035 后 | 109 | fresh main baseline（本批实测复现） |
| 本批完成后 | 106 | 精确移除 iconloader Kotlin 3 项，新增 0（实测） |

## 实施记录

以下为 Task 036 worker 于 2026-08-20 填写的真实证据（全部命令真实运行，未伪造）。

### 1. Fresh 109 基线（改动前）

- 命令：`./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4`（`set -o pipefail` + `tee`，真实退出码经 `${PIPESTATUS[0]}` 保存于 `/tmp/task036-r8-before.status`）
- 结果：`GRADLE_EXIT=1`，`BUILD FAILED`；`missing_rules.txt` 去重后 unique `-dontwarn` refs = **109**；三个目标类与 `AssumeTrueForR8` 均在集合内（脚本断言 `BASELINE=109 TARGETS=3 PASS`）。

### 2. TDD 红/绿

- RED：新增/扩展 5 个测试后，焦点运行 `FAILED (failures=2, errors=1)`——config 测试因 code 列表缺 kotlin JAR 失败，并集测试因单元素列表解包失败，坐标测试因 `1.0.0 != 1.0.1` 失败，均符合预期失败原因。
- GREEN：实施最小修复后，焦点 5 测试 `Ran 5 tests in 2.053s / OK`。

### 3. 确定性重建与产物溯源

- `python3 tools/package_aosp_aar.py iconloader` 运行两次，SHA-256 均为
  `d6e4f27e4b752620b9207fd804db1f5f3dad3225998375ed36d13346d3da6d8b`（137664 bytes）。
- `classes.jar` class 数 = **75**（javac 59 + kotlin 16，两输入集不相交，并集精确相等，逐字节一致）；全部类名位于 `com/android/launcher3/**`。
- `res/**`、`AndroidManifest.xml`、`R.txt` 与配置的 AOSP/Soong 源逐字节一致（单测断言）。

### 4. 本地 Maven 替换

- `rm -rf libs/maven/com/android/systemui/iconloader/1.0.0` 后 `python3 tools/install_aar_to_maven.py iconloader`。
- 仅剩 `1.0.1/iconloader-1.0.1.aar` + `.pom`；AAR 与 `libs/aars/iconloader.aar` `cmp` 字节相同；POM 版本 `1.0.1`、`packaging aar`、无 `<dependencies>`。
- `gradle/libs.versions.toml` 仅 `systemui-iconloader` 一行 `1.0.0`→`1.0.1`。

### 5. 测试 / Debug / APK

- 全量：`python3 -m unittest discover -s tools/tests -p 'test_*.py'` → `Ran 164 tests in 37.855s / OK`（160 基线 + 4 新增）。
- Debug：`./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug -Dorg.gradle.workers.max=4` → `GRADLE_EXIT=0`，`BUILD SUCCESSFUL in 2m 21s`，APK `app/build/outputs/apk/debug/app-debug.apk` 生成（log 中 9 处 duplicate 均为已知 manifest 重复权限 warning，非 duplicate-class 失败）。
- APK 定义：`apkanalyzer dex packages --defined-only` 中三个目标类均有 `C d` 行：
  - `C d 3 3 102 com.android.launcher3.icons.IconThemeController`
  - `C d 2 2 90 com.android.launcher3.icons.ThemedBitmap`
  - `C d 10 10 1028 com.android.launcher3.icons.mono.ThemedIconDrawable`

### 6. Fresh R8 差分（改动后）

- 命令同基线，真实退出码 `/tmp/task036-r8-after.status`：`GRADLE_EXIT=1`（剩余 missing classes 阻塞，符合预期）。
- 机械差分：before = 109，after = **106**；removed = 恰好三个 iconloader 目标；added = 空；`AssumeTrueForR8` 保留。

### 7. 卫生检查

- `git diff --check` 干净；改动文件仅为 Allowed Paths：`tools/package_aosp_aar.py`、`tools/tests/test_package_aosp_aar.py`、`tools/install_aar_to_maven.py`、`tools/tests/test_install_aar_to_maven.py`、`libs/aars/iconloader.aar`、`libs/maven/.../iconloader/1.0.0/*`（删）、`libs/maven/.../iconloader/1.0.1/*`（新）、`gradle/libs.versions.toml`（仅 iconloader 行）、本 issue 文档。
- 正式优化 Release 在剩余 106 个 missing refs 清零前仍不声明成功。

## 待解决问题

- 后续 A 类 closure：Traceur 7、WM-Shell proto 18、SettingsLib 74。
- A 类完成后处理 B1–B4 library/build classpath closure。
