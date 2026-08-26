# android-17.0.0_r1 tag 核查（Task 068，Phase C 前置研究）

> 日期：2026-08-26 · 只读研究（未 sync、未编译、未改 AOSP 树、未跑 Gradle）。
> 数据源：清华 TUNA 镜像（googlesource 直连超时已证实）；本地 AOSP 树
> `/home/conv/myspace/aosp`。所有 tag 侧证据取自 /tmp 下的临时克隆（task 结束可清理）。

## 结论先行：GO（有条件）

**无结构性阻断**：lunch 产品、trunk_staging release config、全部 8 个
SysUISdk 冻结输入模块、7 脚本消费的 Soong 模块、`turbine-combined` 路径逻辑
在 tag 上全部验证存在且未迁移。`android-17.0.0_r1` 可以按现有管线消费。

**但有一个改写 Phase C 预期的重大事实**（§3）：本地 AOSP 树实际停在
**2025-03-26**（不是此前认知的 2026-04-27），距 tag（约 2026-05/06 切出）
**漂移约 14 个月、跨两个 SDK 级别（35 preview → 37 release）**。
SystemUI 子树 +77 万行/−41 万行、文件数 10695→13708。Phase C 的主成本
是全量 tier-① 源码重对齐（规则 C 的 MISSING 会是四位数），不是依赖矩阵。

---

## 1. tag 存在性与身份

```
$ git ls-remote --tags https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest | grep android-17
7a9e46ba6ed424f922a3457f4964e67e0b966201  refs/tags/android-17.0.0_r1
5bc9a7ce1cd78dd53613bbfd0ebf506e1e4adb0f  refs/tags/android-17.0.0_r1^{}
```

- tag 存在，peeled manifest commit = `5bc9a7ce`（"Manifest for Android 17.0.0 Release 1"）。
- **无 `-gpl` 变体**，也无 r2+（`android-17*` 只有 r1 一条）。
- manifest default revision = `refs/tags/android-17.0.0_r1`（所有 project 直接钉 tag，
  非 per-project sha）。
- 抽查各 project 在 TUNA 均带该 tag：art `fc31298b`、prebuilts/sdk `a0d8210a`、
  prebuilts/runtime `25b7bb06`、system/core `f1f2be8c`。
- 关键 revision：frameworks/base@tag = `94b4c163b`（2026-05-21，"Merge cherrypicks
  … into 26Q2-release"）；frameworks/libs/systemui@tag = `11e04f60`（2026-04-24）。
- BUILD_ID（build/make@tag `core/build_id.mk`）：`CP2A.260605.016`。

## 2. lunch target 与隐藏产物路径

### 2.1 产品与变体

- `sdk_phone64_x86_64` **仍存在**：`device/generic/goldfish/64bitonly/product/
  sdk_phone64_x86_64.mk` 在 tag 上保留，且在 `AndroidProducts.mk` 的
  PRODUCT_MAKEFILES 中（sdk_phone64/16k/arm64/riscv64/tablet/slim 全家族俱在）。
- envsetup lunch 解析逻辑未变：新格式缺省 `release=trunk_staging`；legacy
  `product-release-variant` 连字符格式仍被解析（envsetup.sh L555-575）。
- **release tag 上 trunk_staging 仍可用**（否定了"release tag 上 trunk_staging
  通常不可用"的担忧）：build/release@tag 的 `flag_values/trunk_staging/`
  存在（273 个 flag 文件）；`release_config.mk` 在 TARGET_RELEASE 未设时也
  fallback 到 trunk_staging。
- 版本事实（build/release@tag）：
  - `cp2a`（tag 的冻结 release config，`aosp_current → cp2a`）：
    `RELEASE_PLATFORM_SDK_VERSION = 37`，codename `REL`，base SDK ext 22。
  - `trunk_staging`：SDK 37，codename `Baklava`（⚠️ 非 REL → 产出按 preview
    语义处理；见 §5 R3）。
- 建议：沿用现有 `lunch sdk_phone64_x86_64-trunk_staging-userdebug`（语义与
  当前本地构建路径一致）；如需冻结语义可用 cp2a release config。

### 2.2 build_sysuisdk.py 八个冻结输入（重点核查项）

tag 侧逐一验证（方法：TUNA tag 浅克隆/blobless `git show`）：

| 输入 | 消费路径关键 | tag 验证 |
|---|---|---|
| framework_jar | 模块 `framework` + soong `turbine-combined` | frameworks/base/Android.bp L614 ✓；build/soong@tag `java/base.go:2527` 仍 `PathForModuleOut(ctx, "turbine-combined", jarName)` ✓ |
| framework_res_apk | 模块 `framework-res` | core/res/Android.bp L106 ✓ |
| core_libart_jar | 模块 `core-libart` | libcore/JavaLibrary.bp L426 ✓（该文件漂移 366 diff 行，模块未动） |
| unsupportedappusage_jar | 模块 `unsupportedappusage` | tools/platform-compat `java/android/compat/annotation/Android.bp` L61 ✓ |
| aconfig_annotations_jar | 模块 `aconfig-annotations-lib` | frameworks/libs/modules-utils/java/Android.bp L74 ✓ |
| keepanno_jar | 模块 `keepanno-annotations` | prebuilts/r8/Android.bp L139 ✓ |
| iremote_callback_aidl | 源文件 | 存在且与本地**逐字节一致** ✓ |
| screenshot_request_aidl | 源文件 | 存在且与本地**逐字节一致** ✓ |

**残余风险（无法静态验证）**：soong 变体后缀（core-libart 的
`android_common_apex31`、host 端 `linux_glibc_common`）由 soong 运行时推导，
无证据表明变化，但首次 tag 构建后必须重验 8 条冻结路径逐一存在。

### 2.3 其余脚本消费的模块（抽查）

- package_aosp_aar.py 全部 config 的 owning 模块/源码目录在 tag 上存在：
  `animationlib`（fls Android.bp L21）、`iconloader`（L45）、`SettingsLib`
  （Android.bp L12）、`WindowManager-Shell`（L92）、`LowLightDreamLib`（L34）、
  `WifiTrackerLib`（frameworks/opt/net/wifi libs/…/Android.bp L22），
  及 SettingsLib 子 target / WM-Shell-shared / proto 等目录均在。
- package_compilelib_jars.py：`compilelib`（frameworks/libs/systemui/compilelib
  Android.bp L39）✓。
- package_aconfig_jars.py：frameworks/base/AconfigFlags.bp@tag 有 573 个 aconfig
  target；抽查 `aconfig_settingslib_flags_java_lib`（L2521）、
  `android.app.smartspace.flags-aconfig-java`（L1967）均存在 ✓。
- SystemUI 关键 Soong 模块名（SystemUI-core / SystemUI-res / SystemUISharedLib /
  SystemUIUnfoldLib）本地与 tag 一致存在；13-module Gradle 拓扑的 bp 语义基础未塌。

## 3. SystemUI 子树漂移量（⚠️ 重大事实修正）

**本地树真实年龄**：各 project HEAD 提交日期均为 **2025-03-2x**：

```
frameworks/base  main 1cdfff55  2025-03-26  (temp-branch 40eb05de "init" 为其同 tree 的 squash，2026-04-27 只是 squash 的创建时间)
art                       2025-03-26   system/core   2025-03-26
build/make                2025-03-26   prebuilts/sdk 2025-03-14
device/generic/goldfish   2025-03-13   frameworks/libs/systemui 89da99e2 2025-03-08
```

out/ 产物佐证：`ro.build.version.sdk=35`、`codename=Baklava`（Android 16 开发期
preview）。即此前"main @ 2026-04-27"是 squash 时间戳造成的误读，实际漂移窗口
**≈ 14 个月**（2025-03-26 → tag 切出 2026-05/06），**SDK 35 preview → 37 release
跨两个 SDK 级别**。

diff 统计（方法：/tmp 克隆 fetch 双端 revision 后 `git diff --stat`，14 个月
历史无法廉价取全故不报 commit 数）：

| 范围 | files changed | insertions | deletions | 文件数变化 |
|---|---|---|---|---|
| frameworks/base（全仓） | 28,387 | +2,477,706 | −1,001,355 | — |
| **packages/SystemUI/** | **10,318** | **+773,353** | **−414,879** | 10,695 → 13,708（+28%） |
| packages/SettingsLib/ | 1,888 | +88,240 | −22,068 | 3,055 → 3,545 |
| frameworks/libs/systemui（独立仓） | 651 | +76,915 | −10,795 | — |

SystemUI 结构性变化：`Android.bp` 985 → 1129 行；新增 `application/`、`metrics/`、
`ravenwood.sysprop`、`AndroidManifest-robo.xml`；移除 `flag_check.py`、`tools/`。

**对 Phase C 的含义**：这不是"小版本 bump"，而是一次接近两个 release 的
tier-① 全量源码刷新。`check_source_alignment.py` 的 MISSING 将是四位数文件；
工作量主体是 SystemUI-res/SystemUI-* 各模块的源码与 res 重对齐 + 随之而来的
Compose/Kotlin API 适配，远超依赖矩阵更新。建议 Phase C 排期按此量级设定。

## 4. repo sync 体量

- 1045 个 project；`.repo` = 109G（project-objects 106G）；磁盘 916G 已用 737G，
  **剩 134G（85%）**。
- 漂移窗口 ~14 个月。frameworks/base 内容级 churn ≈ 35%（全仓 2.8 万文件变更），
  tag 侧 depth-1 快照 pack 1.2G；prebuilts/clang 工作树单仓 14G（工具链 bump 是
  下载大头）。
- **粗估**：`repo init -b android-17.0.0_r1 && repo sync -d`（建议加 `-c`）下载量
  **约 15–40GB**，其中源码仓 5–15GB、prebuilts 工具链 bump 占其余。夜间执行可行。
- TUNA 排队实测：manifest 克隆排队 53 位、小仓 blobless 克隆也要数分钟——
  建议夜间 + 重试循环 + `-j4~8`（若写成脚本必须 Python，ADR 0002）。
- **磁盘策略**：out/（187G，SDK 35 preview 时代）对 tag 完全失效，重建前建议
  `rm -rf out`，一次性释放 187G，磁盘余量即充足（134G + 187G）。
- 附注：本地 frameworks/base 仓配有一个指向 `github:convivae/SystemUI-Gradle`
  的多余 remote——无害，但 sync 时注意勿 push。

## 5. 风险红旗与降级判定

未发现"现有 7 脚本 + build_sysuisdk 无法消费该 tag"的结构性变化。风险清单：

- **R1（高，预期内）**：14 个月 / 两 SDK 级漂移 → Phase C 源码重对齐工作量
  巨大（§3 量化）。这不是阻断，而是必须让用户在 Phase C 排期前知情的成本事实。
- **R2（中）**：soong 变体后缀（`android_common_apex31` 等）静态不可验——
  首次 tag 构建后必须逐一重验 8 条冻结输入路径。
- **R3（低）**：trunk_staging 在 tag 上 codename=`Baklava`（非 REL）→ 平台按
  preview 语义产出。我们只消费 soong 编译产物，理论上无感；如遇 SDK 语义相关
  问题，切 `TARGET_RELEASE=cp2a`（冻结 config，SDK 37 + REL）。
- **R4（低）**：磁盘 85%；按 §4 清 out/ 后消除。
- **R5（信息）**：tag 无 `-gpl` 变体、无 r2；`android-17.0.0_r1` 即唯一选择。

**降级到 android-16.0.0_r4 的判定条件**（均未触发）：
1. 首次 tag 构建后 8 条冻结输入路径有 ≥1 条缺失且排查后确认是 tag 结构迁移；
2. TUNA 对必需 project 缺 tag（抽查 6 仓全有）；
3. 用户判定 14 个月漂移的适配成本不可接受（此时 16.0.0_r4 漂移窗口更短，
   但仍需重新核定——本地是 SDK 35 preview，16 r1/r4 同样跨一个级别）。

## 附：本次核查使用的命令与克隆

- `git ls-remote --tags`（manifest/art/prebuilts/sdk/prebuilts/runtime/system/core）
- tag 浅克隆（/tmp/task068 与 /tmp/aosp-*）：manifest、build、build/release、
  build/soong、device/generic/goldfish、frameworks/base（2.8G 全量 diff 用）、
  frameworks/libs/systemui；blobless：libcore、platform-compat、modules-utils、
  prebuilts/r8、opt/net/wifi、Traceur。
- 漂移对比：`git fetch --depth 1 origin <local-sha>` 后 `git diff --stat
  <local-sha> <tag-sha> -- <path>`。
- 本地侧：`repo manifest`、各仓 `rev-parse/log`、`out/target/product/emu64a/
  system/build.prop`、`tools/build_sysuisdk.py` 冻结映射（只读）。

构建：**未运行**（只读研究任务，无任何 Gradle/Soong 调用）。
