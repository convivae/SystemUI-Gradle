# SettingsLib 资源闭包打包调研（Task 014）

日期：2026-08-19
性质：只读调研（未修改任何代码/资源/构建脚本/依赖；构建未运行）
任务：`docs/orchestration/tasks/014-settingslib-resource-closure-research.md`
问题记录：`docs/issues/2026-08-19-settingslib-resource-closure-research.md`

---

## 0. 结论速览（Recommendation）

**推荐方案 C：每个真实 Soong res target 一个 res-only AAR（byte-exact），consumer 显式声明依赖。**

- **不采用**方案 A（单一合并 `SettingsLib.aar` 装下完整资源闭包）：AAR 的 `res/` 根目录是单一扁平树，
  闭包内存在 **101 组同相对路径文件**，物理合并必然要求静默跳过/内容改写/正则去重——
  这正是参考项目 `CarSystemUIGradle` 的做法，也是本项目规则 R 明确禁止的"擅改 AOSP 资源"。
  且单一 namespace 会遗留子模块 R 类运行期悬空引用（见 §5）。
- **不推荐现在采用**方案 B（per-target AAR + POM 传递依赖）：技术上可行且 consumer 接口更深，
  但它要求 `tools/install_aar_to_maven.py` 从"依赖无关 POM 骨架"升级为带 `<dependencies>` 的传递 POM，
  改变本地 Maven 语义（CHARTER Part 3 明确当前 POM 是 dependency-free skeleton），
  且对 Task 013 已落地的显式接线造成迁移churn。可作为闭包验证通过后的后续演进。
- **推荐**方案 C：33 个 res target 中除已在 `SettingsLib.aar`（主 target res）、
  `SettingsLibSettingsTheme.aar`、`SettingsLibColor.aar` 中的 3 个外，新增约 30 个 res-only AAR，
  在 `:SystemUI-res` 逐个显式 `api(...)` 接入（沿用 Task 013 已验证的模式）。
  打包来源与 Soong target 边界一一对应（规则 B），res 字节不动（规则 R），
  重复相对路径天然规避（各 AAR 独立 res 树，AAPT2 在 link 阶段按符号合并——与 Soong 在 app link 的机制同构），
  并顺带修复子模块 R 类运行期悬空引用。

---

## 1. 调研方法与一手来源

全部结论来自对以下一手来源的实际读取/解包（无记忆推断）：

| 来源 | 用途 |
|---|---|
| `/home/conv/myspace/CarSystemUIGradle/tools/gen_aar_maven.py` | 参考项目 SettingsLib AAR 生成机制 |
| `/home/conv/myspace/CarSystemUIGradle/libs/maven/com/android/systemui/SettingsLib/1.0.0/{SettingsLib-1.0.0.aar,.pom}` | 参考产物实物解包 |
| `/home/conv/myspace/CarSystemUIGradle/{gradle/libs.versions.toml,SystemUI-core/build.gradle.kts,docs/GRADLE_MIGRATION.md,docs/DEPENDENCIES.md}` | 接线方式与历史问题 |
| `/home/conv/myspace/aosp/frameworks/base/packages/SettingsLib/Android.bp` 及全部子目录 `Android.bp`/`AndroidManifest.xml` | Soong target 图、resource_dirs、R namespace |
| `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SettingsLib/**` | Soong 中间产物（package-res.apk、R.txt、javac、busybox/R.jar） |
| 本项目 `tools/package_aosp_aar.py`、`SystemUI-res/build.gradle.kts`、`libs/aars/SettingsLib.aar`、Task 013 issue/brief | 现状基线 |

量化审计使用 /tmp 下一次性 Python 脚本（未在仓库创建任何脚本）。
本次**未运行任何 Gradle 构建**；所有"实测"指对文件的解包/字节码/javap 检查。

---

## 2. Finding 1 — 参考项目 CarSystemUIGradle 的真实机制

**参考项目使用单一合并 AAR（monolithic），由脚本把整个 SettingsLib 源码树下所有 res 目录
物理拼接进一个 AAR `res/` 根，并伴随内容改写与删除。**

证据：

1. **单一 AAR + 无依赖 POM 骨架**：
   `libs/maven/com/android/systemui/SettingsLib/1.0.0/SettingsLib-1.0.0.pom` 仅含
   `groupId=com.android.systemui / artifactId=SettingsLib / version=1.0.0 / packaging=aar`，无 `<dependencies>`。
2. **资源来源 = 源码树全量扫描**：`tools/gen_aar_maven.py` 的
   `AarConfig(name="SettingsLib", intermediate_path="frameworks/base/packages/SettingsLib/SettingsLib",
   source_path="frameworks/base/packages/SettingsLib", ...)`（L50-53）；
   `find_res_dirs()`（约 L105-115）对整个 `frameworks/base/packages/SettingsLib` 做 `os.walk`，
   收集**所有**名为 `res/res-private/res-keyguard/res-product` 的目录（排除 tests），
   不区分它们属于哪个 Soong target。
3. **消费方式**：`gradle/libs.versions.toml:95`
   `systemui-settingslib = { group = "com.android.systemui", name = "SettingsLib", version.ref = "systemui-local" }`；
   `SystemUI-core/build.gradle.kts:104` `implementation(libs.systemui.settingslib)`。
4. **代码来源**：Soong intermediates 的 combined/javac jar（`find_jar_source()`，约 L118-135）；
   `clean_jar()` 删除 R.class 与冲突包。
5. **实测产物内容**（解包 `SettingsLib-1.0.0.aar`，/tmp/refsl）：309 个 res 文件，
     **包含子模块资源**（`res/layout/preference_two_target_divider.xml`、
   `res/interpolator/progress_indeterminate_horizontal_rect2_translatex_copy.xml`、
   `res/layout/settingslib_action_buttons.xml` 等）——即 TwoTargetPreference/ProgressBar/ActionButtonsPreference
   的资源确实被源码树扫描带进了合并 AAR。
6. **关键差异**：参考配置 `res_to_remove=["values-v31","values-night-v31","color-v31",
   "color-night-v31","drawable-v31","layout-v31"]`（L54-56，注释"Material Components 依赖"）
   ——参考项目**刻意删除了全部 v31 资源目录**。这就是为什么参考 AAR 里没有
   `settingslib_switch_track/thumb`（它们位于 `SettingsTheme/res/drawable-v31/`）：
   Car SystemUI 场景不引用这些资源，删除后无人报错。本项目不能照抄（SystemUI res 直接引用，Task 013 已证）。
7. 参考项目 AOSP 根为另一 ROM checkout（`/home/conv/myspace/rom/jkc-A/...`，现已不存在于磁盘），
   其 SettingsLib 版本与本项目 `/home/conv/myspace/aosp` 并不同源，文件数（309 vs 本项目闭包 1512）不可直接对比。

---

## 3. Finding 2 — 参考项目如何处理同相对路径资源：不回避，而是静默改写/丢弃

`gen_aar_maven.py` 的合并策略（这是方案 A 的必经之路，也是其被否决的原因）：

| 冲突类型 | 参考项目的处理 | 代码位置 |
|---|---|---|
| 非 values 文件同相对路径 | **后到者静默跳过（first-wins）**，字节丢失无记录 | `copy_res_dir()`：`if dst_file.exists(): ... 非values已存在则跳过` |
| values XML 同相对路径 | `merge_values_xml()` 把 source 的 `<resources>` 内文**追加**到 target 文件（重写字节） | `merge_values_xml()` |
| 跨文件同名资源 | `remove_duplicate_resources()` 按文件名排序后**正则去重，首个定义胜出**，其余定义被删除并回写文件 | `remove_duplicate_resources()` |

即：参考机制**并没有避免**重复相对路径问题，而是用内容改写 + 静默丢弃 + 正则去重把问题压平。
这违反本项目规则 R（资源不得擅改；ADR 0004 要求 CONV 标记且需用户授权，而此处连可追溯的标记都没有）。
本项目 `tools/package_aosp_aar.py` 是严格打包器，遇到同路径会正确拒绝——Task 013 已确认
`SettingsLib/res` 与 `SettingsTheme/res` 有 89 个同路径文件不可合并，本调研把该结论推广到整个闭包（§4）。

**参考项目自身的教训（重要先例）**：单一 namespace 合并 AAR 曾导致运行期
`NoClassDefFoundError: Lcom/android/wifitrackerlib/R$string;`
（`docs/GRADLE_MIGRATION.md` 约 L1260-1275），根因是"SettingsLib AAR 包含 wifitrackerlib 的类，
但其资源不在 AAR 里 → APK 缺 `com.android.wifitrackerlib.R$string` 类"。
参考项目的解法是**为 WifiTrackerLib 单独出一个 AAR（独立 namespace）**——
即参考项目自己也是靠"per-target 独立 AAR"修 R 类问题的，而不是靠合并 AAR。

---

## 4. Finding 3/4 — Soong 可复用产物搜索 + 量化闭包审计

### 4.1 Soong 没有可直接复用的"完整合并 SettingsLib 资源"产物（not found）

对 `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SettingsLib/**` 的检查：

1. **主 target `SettingsLib` 的 `package-res.apk` 只含自己的 res**。实测解包
   `SettingsLib/android_common/package-res.apk`：174 个文件条目（color/drawable/layout/layout-v33/xml + resources.pb）；
   `settingslib_switch_track`、`progress_indeterminate_horizontal_rect2_translatex_copy`、
   `preference_two_target_divider` 的出现次数均为 **0**。
   即 static_libs 子模块资源**不进入**库级 package-res.apk。
2. **主 target `R.txt` 只含主包符号**（1138 行；上述三个子模块资源名均 0 命中）；
   SettingsTheme 有自己的 `R.txt`（302 行）。每个子 target 的 intermediates 目录各有独立的
   `package-res.apk`/`R.txt`/`aapt2`/`javac`（SettingsLib 树下共 84 个 package-res.apk）。
3. **整个 SettingsLib intermediates 树中不存在任何 `.aar`**（find 结果为空）。
4. 完整合并只发生在 **app link 阶段**（如 `SystemUI/SystemUI-core/android_common/package-res.apk`），
   那是 SystemUI 自己的产物，不可当 SettingsLib 交付物复用。
5. **最接近可用的中间产物**＝每个 target 的：`res/` 源目录（AOSP 源码）、
   `AndroidManifest.xml`（提供 R namespace 包名）、`android_common/R.txt`——
   恰好是本项目 `tools/package_aosp_aar.py` 已经消费的三件套。

### 4.2 量化闭包审计（brace-aware 解析全部 Android.bp）

`SettingsLib`（`frameworks/base/packages/SettingsLib/Android.bp` L12-70）的直接 `static_libs` 共 44 项，
其中 `SettingsLib*` 子 target 35 个；非 SettingsLib 资源依赖为
`WifiTrackerLibRes`、`iconloader`、`setupdesign`（见 §7 相邻发现）。

传递闭包（仅 SettingsLib* 子图）共 39 个 target，其中**拥有资源的有 33 个**：

- 主 target `SettingsLib`（`res/`，365 文件）
- 30 个直接 static_libs 子 target（各带 `resource_dirs`）
- 2 个仅传递出现：`SettingsLibSettingsTheme`（被 24 个子 target 依赖；174 文件）、
  `SettingsLibColor`（被 IllustrationPreference 依赖；1 文件 = `values/colors.xml` 内 47 个 color 条目；
  其 Android.bp 无显式 `resource_dirs`，依赖 Soong 默认值 `["res"]`——审计工具必须按此默认值识别）

| 指标 | 数值 |
|---|---|
| 闭包内 res-owning target | **33**（主 + 30 直接 + 2 传递） |
| res 文件总数 | **1512** |
| 去重后唯一相对路径 | 599 |
| **同相对路径冲突组** | **101**（其中 85 组是 9 个 target 共享的 `values-*/strings.xml` 等 locale 文件） |
| 跨 target 同名资源（type+name） | **仅 5 个**，全部是 `style/EntityHeader*` 5 兄弟：LayoutPreference `values/styles.xml` vs SettingsTheme `values-v35/styles_expressive.xml` |

那 5 个 style"冲突"在单一 namespace 合并下是**合法的 config 变体**（values vs values-v35，
即 expressive 覆盖语义），AAPT2 link 不会报错；在 Soong 按包分 namespace 时它们本是不同包的不同资源。
除此之外整个闭包的资源名无冲突——**说明 AAPT2 符号级合并（link 阶段）天然消化这 101 组路径冲突，
冲突只在"物理拼接单一 res/ 根"时才致命**。这正是 Soong app link 与 AGP 多 AAR link 的共同机制，
Task 013 已在本项目实证（加 SettingsTheme AAR 后 unqualified `@drawable/settingslib_switch_track` 解析成功）。

### 4.3 R namespace 事实（决定运行期正确性）

- 每个子 target 的 `AndroidManifest.xml` 声明**独立包名**（如
  `TwoTargetPreference → com.android.settingslib.widget.preference.twotarget`，
  `SettingsTheme → com.android.settingslib.widget.theme`），即各自独立的 R namespace。
- Soong 库级 R 类字段是**非 final**（实测 `javap` busybox/R.jar：`public static int`，非 `static final`），
  因此子模块字节码以 `getstatic` 引用 R 字段（实测 `TwoTargetPreference.class`：
  `getstatic com/android/settingslib/widget/preference/twotarget/R$id.two_target_divider`），
  **不内联常量**。
- 子 target javac jar 不含 R 类；当前本项目 `SettingsLib.aar` classes.jar（781 类，合并全部子模块 javac）
  同样不含任何 R 类；res 仅主 target 365 文件。
- **推论（当前架构的潜在运行期缺陷）**：合并 classes.jar 里的子模块类在运行期需要
  `com.android.settingslib.widget.preference.twotarget.R$id.two_target_divider` 这类字段，
  但当前没有任何 AAR 的 namespace 提供该包的 R 类 → 实例化时将 `NoSuchFieldError`。
  参考项目的 `NoClassDefFoundError: Lcom/android/wifitrackerlib/R$string;`（§3）是同一失败模式的实证。
  **per-target res-only AAR（保留原始 manifest 包名）会让 AGP 在各子包名下生成带最终 ID 的 R 类，
  恰好修复该缺陷**；单一合并 AAR 则修不了（只生成 `com.android.settingslib.R`）。

---

## 5. 三方案对比

判定维度：规则 R/B、溯源、重复路径、可复现性、本地 Maven 语义、consumer 接口深度、Task 013 迁移/回滚。

| 维度 | A：单一合并 SettingsLib.aar | B：per-target AAR + POM 传递依赖 | C：per-target AAR + 显式 consumer 依赖 |
|---|---|---|---|
| 规则 R | **违反**：101 组同路径必须 first-wins 跳过 / values 内容拼接 / 正则去重（参考项目做法），资源字节被改写且不可溯源 | 合规：每 AAR res 树 byte-exact | 同 B |
| 规则 B / Soong 边界 | 丢失：33 个 target 边界被压扁成 1 个 namespace | 保持：AAR = Soong target 一一对应 | 同 B |
| 重复相对路径 | 物理冲突，无法合规解决 | 规避：各 AAR 独立 res 树；AAPT2 link 按符号合并（Soong app link 同构，Task 013 已实证） | 同 B |
| 子模块 R 类运行期 | **不修复**（只生成主包 R） | **修复**（AGP 按各 AAR manifest 包名生成 R） | 同 B |
| 可复现性 | 打包器需引入改写逻辑，确定性遭内容级破坏 | 现有确定性打包器直接适用 | 同 B |
| 本地 Maven 语义 | 不变 | **改变**：install_aar_to_maven.py 需产出带 `<dependencies>` 的 POM；当前全仓 POM 均为骨架（CHARTER Part 3 警告），语义升级波及所有 artifact 的测试与心智模型 | 不变：依赖无关骨架照旧 |
| consumer 接口深度 | 最浅（1 个依赖） | 深（consumer 只见 settingslib） | 浅层显式：`:SystemUI-res` 需列 ~30 行 `api(...)`；但该模块本就显式列资源依赖（settingslib/theme/leanback/slice），符合既有惯例 |
| Task 013 迁移/回滚 | 推倒重来（SettingsTheme AAR 作废或被合并逻辑吞并） | 迁移：SettingsTheme 从显式 `api(...)` 改挂 POM 边，回滚需同时回滚 POM 语义 | **零迁移**：纯增量，新增 alias + api 行；回滚 = 删行删 AAR |
| 审计/漂移风险 | 打包逻辑黑箱化 | POM 边与 bp 图需保持同步 | consumer 清单与 bp 图需保持同步；但 target 清单的唯一事实源已在 `tools/package_aosp_aar.py` CONFIGS（可加对齐测试兜底） |

**推荐：方案 C。** 理由：A 在规则 R 上不可行（除非走 ADR 0004 CONV + 用户授权的内容级改写，
代价与收益完全不成比例，且参考项目的先例正是我们引以为戒的静默改写）；B 的唯一优势
（consumer 接口更深）不足以抵偿本地 Maven POM 语义升级的风险与迁移churn，
且 CHARTER Part 3 已把"POM 是骨架"列为已知事实。C 是 Task 013 已验证模式的最小外推，
合规性、可回滚性、可审计性最好。B 可作为闭包链接通过、运行验证稳定后的可选收敛步骤
（届时 POM 边可由打包脚本从 Android.bp 图机械生成，风险可控）。

### 实施轮廓（供架构师拆任务，本调研不改任何文件）

- 新增 res-only AAR：33 − 3（主 target res 已在 `SettingsLib.aar`；SettingsTheme、Color 已存在）= **30 个**
  （30 个直接 static_libs 子 target，见 §4.2 清单）。
- 每个 AAR：原始 `res/**` byte-exact + 原始 `AndroidManifest.xml`（保 R namespace 包名）+ Soong `R.txt`，
  版本一律 `1.0.0`，坐标 `com.android.systemui:<SoongTargetName>:1.0.0`，走
  `package_aosp_aar.py` CONFIGS + `install_aar_to_maven.py` + catalog alias + `:SystemUI-res` 显式 `api(...)`
  ——与 Task 013 完全同构的流水线。
- 依赖版本矩阵、模块边界、`:SystemUI-res/build.gradle.kts` 均属 CHARTER Part 5 红线，实施前需用户批准。

---

## 6. 残余风险与相邻发现（不属于本调研范围，仅记录）

1. **闭包外还有非 SettingsLib 的资源型 static_libs**：`WifiTrackerLibRes`（已由 WifiTrackerLib.aar 覆盖）、
   `iconloader`（已覆盖）、**`setupdesign`（external/setupdesign，有 intermediates，当前未打包）**。
   SettingsLib 的 src/res 未发现对 setupdesign 资源的引用（grep 为空），此前 Task 已按需引入 setupcompat；
   若后续链接报 setupdesign 资源缺失，按同一 per-target 模式补即可。
2. **跨依赖资源名冲突**：5 个 EntityHeader* style 只是闭包内部情形；与 SystemUI-res、framework-res、
   iconloader、WifiTrackerLib 等合并后的全局名冲突只能由 AAPT2 link 实测暴露（链接器会精确报错，不会静默）。
3. **POM 骨架语义**（若未来选 B）：需同步更新 `tools/tests/` 与 CHARTER Part 3 的事实描述。
4. 本调研的 Android.bp 解析为自写 brace-aware 解析器（/tmp 一次性脚本），
   实施任务的 CONFIGS 注册应以逐 target 复核为准（尤其依赖 Soong 默认 `resource_dirs=["res"]` 的 target）。

---

## 7. 验证命令（本次调研实际执行的代表性命令）

```bash
# 参考产物解包与内容验证
unzip -l CarSystemUIGradle/libs/maven/com/android/systemui/SettingsLib/1.0.0/SettingsLib-1.0.0.aar
# → 309 res files；含 preference_two_target_divider.xml / progress_*interpolator / settingslib_action_buttons.xml

# Soong 主 target package-res.apk 只含自有 res
unzip -l aosp/out/soong/.intermediates/frameworks/base/packages/SettingsLib/SettingsLib/android_common/package-res.apk | grep -c settingslib_switch_track   # → 0

# Soong R 类非 final、字节码 getstatic 引用子包 R
javap -p  SettingsLib/android_common/busybox/R.jar!com/android/settingslib/R\$layout.class   # → public static int（非 final）
javap -c  TwoTargetPreference.class | grep twotarget   # → getstatic com/android/settingslib/widget/preference/twotarget/R$id.two_target_divider

# 闭包审计（/tmp 一次性脚本，未入仓库）
python3 /tmp/sl_final2.py   # → 33 res targets / 1512 files / 101 duplicate-path groups
python3 /tmp/sl_names3.py   # → 仅 5 个 EntityHeader* style 名跨 target 重名
```
