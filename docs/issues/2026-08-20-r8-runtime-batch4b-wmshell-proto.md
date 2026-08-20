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

以下为 Task 037 worker 于 2026-08-20 在 worktree `SystemUI-Gradle-wt-037`（base `2bd9ea4f`）
填写的真实证据（全部命令真实运行，退出码未伪造）。

### 1. Fresh 106 基线（改动前）

- 命令：`./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4`
  （`set -o pipefail` + `tee /tmp/task037-r8-before.log`，真实退出码存
  `/tmp/task037-r8-before.status`）
- 结果：`GRADLE_EXIT=1`，`BUILD FAILED in 1m 53s`；
  `missing_rules.txt` unique `-dontwarn` refs = **106**；18 个 wm.shell 目标与
  `AssumeTrueForR8` 均在集合内（差分脚本断言 PASS）。

### 2. TDD 红/绿

- RED：新增 7 个聚焦测试（`TestWMShellProtoProvenance` 5 个 +
  `ArtifactRegistryTest` 2 个）后，焦点运行 `FAILED (failures=4)`——config
  code 列表缺两个 proto JAR、并集测试 1848≠1888、18 目标缺失、坐标
  1.0.0≠1.0.1，均符合预期失败原因；res 溯源/确定性/shared 不动 3 个回归
  守卫测试本来就绿（验证未变行为）。
- GREEN：实施最小修复（config 追加两 JAR + 版本 1.0.1）后，
  焦点 7 测试 `Ran 7 tests / OK`（exit 0）。

### 3. 确定性重建与产物溯源

- `python3 tools/package_aosp_aar.py WindowManager-Shell` 运行两次，
  SHA-256 均为 `37e3e78625d8ae61f7cd3259b17346df36d997156e161f477d06f61ba1fec763`
  （4396336 bytes），`cmp` byte-identical。
- `classes.jar` class 数 = **1888**（主 javac 1183 + 主 kotlin 677 − exclude 12 =
  1848 基线，∪ nano proto 4 + lite proto 36；四源两两不相交，并集精确相等，
  逐字节一致）。
- 命名空间说明：40 个 proto 类全部在 `com/android/wm/shell/**` 下；
  AAR 内另有 2 个 `com/android/internal/protolog/ProtoLogImpl_992223594{,$Cache}`
  类，系 1.0.0 基线既有（主 javac JAR 的 wm_shell protolog cache，owning
  Soong 产物），本批未新增任何越界类（单测断言固定该 2 类集合）。
- `res/**`、`AndroidManifest.xml`、`R.txt` 与配置的 AOSP/Soong 源逐字节一致
  （单测断言）；18 个 R8 目标类全部在 AAR（单测断言）。

### 4. 本地 Maven 替换

- `rm -rf libs/maven/com/android/systemui/WindowManager-Shell/1.0.0` 后
  `python3 tools/install_aar_to_maven.py WindowManager-Shell`。
- 仅剩 `1.0.1/WindowManager-Shell-1.0.1.aar` + `.pom`；AAR 与
  `libs/aars/WindowManager-Shell.aar` `cmp` 字节相同；POM 版本 `1.0.1`、
  `packaging aar`、无 `<dependencies>`。
- `gradle/libs.versions.toml` 仅 `systemui-wmshell` 一行 `1.0.0`→`1.0.1`
  （`systemui-wmshell-shared` 不动）。

### 5. 测试 / Debug / APK

- 全量：`python3 -m unittest discover -s tools/tests -p 'test_*.py'` →
  `Ran 171 tests in 41.594s / OK`（exit 0；164 基线 + 7 新增）。
- Debug：`./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug
  -Dorg.gradle.workers.max=4` → `GRADLE_EXIT=0`，
  `BUILD SUCCESSFUL in 2m 33s`，APK `app/build/outputs/apk/debug/app-debug.apk`
  生成（160613321 bytes；log 中 9 处 duplicate 均为已知 manifest 重复权限
  warning，非 duplicate-class 失败）。
- APK 定义：`apkanalyzer dex packages --defined-only` 中 18 个目标类全部有
  `C d` 行（脚本断言 `TOTAL=18 DEFINED=18 MISSING=0`，exit 0）。

### 6. Fresh R8 差分（改动后）

- 命令同基线，真实退出码 `/tmp/task037-r8-after.status`：`GRADLE_EXIT=1`
  （剩余 88 个 missing refs 阻塞，符合预期）。
- 机械差分（脚本断言，exit 0）：before = 106，after = **88**；
  removed = 恰好 18 个 wm.shell proto 目标；added = 空；
  `AssumeTrueForR8` 保留。**PASS**。

### 7. 卫生检查

- `git diff --check` 干净；改动文件仅为 Allowed Paths：
  `tools/package_aosp_aar.py`、`tools/tests/test_package_aosp_aar.py`、
  `tools/install_aar_to_maven.py`、`tools/tests/test_install_aar_to_maven.py`、
  `libs/aars/WindowManager-Shell.aar`、
  `libs/maven/.../WindowManager-Shell/1.0.0/*`（删）、
  `libs/maven/.../WindowManager-Shell/1.0.1/*`（新）、
  `gradle/libs.versions.toml`（仅 systemui-wmshell 一行）、本 issue 文档。
- 单个英文 commit，未 push。
- 正式优化 Release 在剩余 88 个 missing refs 清零前仍不声明成功。

| 阶段 | R8 unique missing refs | 说明 |
|---|---:|---|
| Task 036 后 | 106 | fresh 基线（本批实测复现） |
| 本批完成后 | 88 | 精确移除 WM-Shell proto 18 项，新增 0（实测） |

## 待解决问题

- AGENTS.md §3.2 libs 树中 `WindowManager-Shell/1.0.0/` 目录行将滞后（红线文件，
  由架构师合并时作事实性修正，与 036 同处理）。
