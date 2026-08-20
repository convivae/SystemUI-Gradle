# 2026-08-20 R8 Runtime Batch 4B — WM-Shell proto 闭包（106→88）

## 背景

主分支 fresh R8 当前缺 **106** 个类（Batch 4A / Task 036 后）。其中 **18 个是
`com.android.wm.shell.*` proto 生成类**，全部属于 A4 组（审计
`docs/architecture/2026-08-20-r8-runtime-closure-audit.md` §3 A4、§7 Batch 4 第 4 项）：

- 15 个 **lite proto**：`desktopmode.persistence.Desktop*`（9）+
  `desktopmode.education.data.WindowingEducationProto*`（6）
- 3 个 **nano proto**：`nano.Transition`、`nano.HandlerMapping`、
  `nano.WmShellTransitionTraceProto`

### 根因

AOSP `frameworks/base/libs/WindowManager/Shell/Android.bp`：

- `java_library "WindowManager-Shell-proto"`（L138，nano，srcs `proto/*.proto`）
- `java_library "WindowManager-Shell-lite-proto"`（L148，lite，srcs desktopmode
  education data + persistence 的 `*.proto`）
- `android_library "WindowManager-Shell"` 的 `static_libs` 含两者（L188-189）

`tools/package_aosp_aar.py` 的 `WindowManager-Shell` config 当前只合并主 javac+kotlin
两个 jar，**漏掉了这两个 proto javac 产物**，导致 40 个 proto 生成类未进 AAR。
Soong 中间产物实测：

| Soong javac jar | 类数 | 命名空间 |
|---|---|---|
| `WindowManager-Shell-proto/android_common/javac/WindowManager-Shell-proto.jar` | 4 | 全部 `com/android/wm/shell/nano/` |
| `WindowManager-Shell-lite-proto/android_common/javac/WindowManager-Shell-lite-proto.jar` | 36 | 全部 `com/android/wm/shell/desktopmode/` |

**已实测验证**：40 类与当前 AAR 1848 类零重叠、与 `WindowManager-Shell-shared.aar`
零重叠、18 个 missing 目标 100% 被覆盖。

### 运行时底座（已就位，无需改动）

- nano runtime：`com.google.protobuf.nano:protobuf-javanano:3.1.0`（implementation，Task 027）
- lite runtime：`com.google.protobuf:protobuf-javalite:4.35.1`（implementation，Task 035）
- 当前 missing_rules 中 protobuf runtime 类 = 0

## 操作步骤（设计）

1. `tools/package_aosp_aar.py` `CONFIGS["WindowManager-Shell"].code` 追加上述两个 Soong
   proto javac jar（主 javac + kotlin 保持在前）。
2. 重打包 `libs/aars/WindowManager-Shell.aar`：1848 + 40 = **1888 类**（精确不相交并集，
   全部 `com/android/wm/shell/**`）；res / AndroidManifest / R.txt 逐字节保留。
3. `tools/install_aar_to_maven.py` `ARTIFACTS["WindowManager-Shell"]` 版本
   **1.0.0→1.0.1**（用户已批准；避免同坐标 Gradle 缓存复用）；删除旧
   `libs/maven/com/android/systemui/WindowManager-Shell/1.0.0/`；安装 1.0.1
   （AAR 逐字节一致 + 骨架 POM）。
4. `gradle/libs.versions.toml` `systemui-wmshell` 一行改为 1.0.1（**只此一行**）。
5. TDD：先写失败测试（40 类存在性、1888 精确并集、不相交、确定性、坐标、POM），
   再实现至全绿。

### 禁止事项（与 036 同）

- 不改任何 `SystemUI-*/src/**`、`SystemUI-*/res*/**`；不改 `SystemUI-core/build.gradle.kts`
  （`implementation(libs.systemui.wmshell)` 已是正确 scope）。
- **launcher3 flags 禁止并入 AAR**（审计 §3.2 A4：由独立 `libs/launcher3-flags.jar`
  统一供给，防双来源重复类）。
- 不加 stub / keep / dontwarn / 源码排除 / 构建绕过；不动 Traceur、SettingsLib、B1–B4。
- 不用 turbine/header/combined/FAT jar；只用 owning Soong javac 产物。
- `WindowManager-Shell-shared` 与 shared 相关坐标一律不动。

## 验收标准

1. 全套 `tools/tests` 通过（164 + 本批新增聚焦测试）。
2. `libs/aars/WindowManager-Shell.aar` 恰好 1888 类；两次重打包 byte-identical。
3. 18 个目标类全部在 AAR classes.jar 中；并集与两个 proto jar 逐字节一致。
4. 本地 Maven 仅剩 `WindowManager-Shell/1.0.1/`（AAR 与 libs/aars byte-identical，
   POM 无 dependencies）。
5. `gradle/libs.versions.toml` 相对基线恰好一行变化。
6. **`:app:assembleDebug` BUILD SUCCESSFUL（用户硬性门禁：每批必须保持 debug 可编译）**。
7. 18 个目标类在 debug APK 中 defined（`C d` 行）。
8. fresh R8：**106→88 精确**（removed 恰为 18 个 wm.shell 目标，added=0，
   `AssumeTrueForR8` 保留）；任何偏差即 REDLINE。

## 错误数演变 / 证据

（worker 实施时如实填写；架构师主分支复验后补充最终值）

## 待解决问题

- AGENTS.md §3.2 libs 树中 `WindowManager-Shell/1.0.0/` 目录行将滞后（红线文件，
  由架构师合并时作事实性修正，与 036 同处理）。
