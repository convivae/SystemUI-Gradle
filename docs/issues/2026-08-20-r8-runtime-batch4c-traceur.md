# R8 Runtime Closure — Batch 4C（Traceur）调研与设计

> 日期：2026-08-20。前置：`docs/architecture/2026-08-20-r8-runtime-closure-audit.md`（A7 候选 + Batch 4 建议）
> 与 `docs/issues/2026-08-20-release-r8-alignment-decisions.md`。本批为 Batch 4 的**第三个批次（4C）**，
> 也是**第一个含真实 res 的 AAR 批次**（为后续 SettingsLib 热身）。

## 1. 范围与基线

A7：7 个 missing refs 全部位于 `SystemUI-core/src/com/android/systemui/recordissue/**`
（SystemUI 的 Issue Recording / Traceur 桥接代码）：

| # | Missing class | 来源 Soong target |
|---|---|---|
| 1-2 | `com.android.traceur.FileSender` / `PresetTraceConfigs`（+内部类 `TraceOptions`） | `packages/apps/Traceur:TraceurCommon` |
| 3 | `com.android.traceur.TraceConfig`（+Builder） | 同上 |
| 4 | `com.android.traceur.res.R$array` / `R$string` | `packages/apps/Traceur:Traceur-res` |

基线（main `34cac970` fresh 复验）：**88** = SettingsLib 74 + Traceur 7 + B 类 6 + AssumeTrueForR8 1。
本批目标：**88 → 81**（removed 恰为 7 个 traceur 目标、added=0）。

## 2. AOSP 结构事实（Soong 为准）

`packages/apps/Traceur/Android.bp`：

- `android_app "Traceur"`（独立 app，与我们无关）
- `android_library "TraceurCommon"`：srcs `src_common/**/*.java`；
  static_libs = appcompat、legacy-support-v4、**perfetto_config_java_protos**；
  manifest `AndroidManifest-common.xml`（package `com.android.traceur.common`，声明 5 权限）
- `android_library "Traceur-res"`：res-only（无 srcs），`use_resource_processor: true`，
  resource_dirs `res`（**105 个文件**）；manifest `AndroidManifest-res.xml`（package `com.android.traceur.res`）；
  static_libs = androidx.leanback、leanback-preference、legacy-preference-v14

SystemUI 消费方：`frameworks/base/packages/SystemUI/Android.bp` L502-503 与 L695-696
（`SystemUI-core` 的 static_libs 两处均含 `TraceurCommon` + `Traceur-res`）。
SystemUI 源码使用点：`src/com/android/systemui/recordissue/*`（CustomTraceState、TraceurConnection、
IssueRecordingService*、CustomTraceSettingsDialogDelegate 等）。

## 3. Soong 产物盘点（均存在于 out/soong/.intermediates）

| 产物 | 路径 | 内容 |
|---|---|---|
| TraceurCommon javac | `packages/apps/Traceur/TraceurCommon/android_common/javac/TraceurCommon.jar` | **15 类**，全部 `com/android/traceur/` |
| perfetto config protos javac | `external/perfetto/perfetto_config_java_protos/android_common/javac/perfetto_config_java_protos.jar` | **625 类**，全部 `perfetto/protos/` |
| Traceur-res R.txt | `packages/apps/Traceur/Traceur-res/android_common/R.txt` | res 符号表（array/color/drawable/id/layout/mipmap/string/style 8 个 R 子类） |
| Traceur-res package-res.apk | `packages/apps/Traceur/Traceur-res/android_common/package-res.apk` | 链接验证参考 |

当前项目占位物（**本批退役**）：
- `libs/TraceurCommon.jar` —— 已验证与 Soong javac jar **类集合完全一致**（15 类），当前 compileOnly
- `libs/traceur-res-R.jar` —— 仅 8 个 `com/android/traceur/res/R$*` 类，无 res（compile-time-only）

## 4. 关键设计判定（已逐一实证）

1. **perfetto protos 是 lite runtime**：生成类 `registerAllExtensions(com.google.protobuf.ExtensionRegistryLite)`
   → 现有 `com.google.protobuf:protobuf-javalite:4.35.1`（implementation，Batch 3 落地）即覆盖，
   **无需新增 protobuf full runtime**。
2. **TraceurCommon 外部引用闭合**（src_common 全部 import 审计）：
   - `androidx.core.content.FileProvider` → androidx.core 已 implementation ✓
   - `com.android.internal.inputmethod.ImeTracing` → SysUISdk android.jar 与 framework.jar 均含 ✓
   - `perfetto.protos.{DataSourceDescriptor,FtraceDescriptor,TraceConfig,TracingServiceState}*` → 随 625 类并入 AAR ✓
   - src_common **不 import** appcompat/legacy-support-v4（bp 声明属 Soong 惯例/传递安全），无需新增官方坐标
3. **Traceur-res 资源引用闭合**：styles.xml 引用 `@layout/preference_list_fragment`（androidx.preference ✓）、
   `@style/PreferenceThemeOverlay.v14.Leanback`（leanback-preference ✓，均已在 core implementation）；
   xml/main.xml 仅用 androidx.preference 控件。**无需新增 androidx.legacy:\*:1.0.0**；
   若 `processDebugResources` 链接报缺资源，属意外 → HALT 上报用户（新增官方依赖需用户批准）。
4. **Manifest 权限合并必须保留**：`CONTROL_UI_TRACING`、`START_FOREGROUND_SERVICES_FROM_BACKGROUND`
   不在 AOSP SystemUI 自身 manifest 中，AOSP 靠 TraceurCommon manifest 合并进 APK
   → TraceurCommon 必须以 **AAR（含 AndroidManifest-common.xml）**交付，不能用纯 jar（jar 无 manifest 合并）。
5. **打包形态（对齐 WM-Shell proto 先例）**：
   - `libs/aars/TraceurCommon.aar`：classes.jar = 15 + 625 = **640 类不相交并集**
     （bp `TraceurCommon.static_libs` 含 perfetto_config_java_protos，与 WindowManager-Shell 并入其 proto static_libs 同构）；
     manifest = `AndroidManifest-common.xml`；无 res。
   - `libs/aars/Traceur-res.aar`：code=[]；res = Traceur/res 105 文件；
     manifest = `AndroidManifest-res.xml`；R.txt = Soong R.txt（namespace `com.android.traceur.res`）。
     （res-only 先例：SettingsLibColor / SettingsLibSettingsTheme。）
6. **直接 AAR 优先（ADR 0001）**：两 AAR 直接 `implementation(files("libs/aars/…"))` 引入；
   `com.android.traceur.*`、`perfetto.protos.*`、res namespace 均与现有产物零重叠，预期无冲突；
   仅当确认冲突才转本地 Maven（届时另行上报）。
7. **退役纪律**：删除 `libs/TraceurCommon.jar` + `libs/traceur-res-R.jar`，
   SystemUI-core 两条 compileOnly 改为两条 implementation；全仓 grep 确认无残留引用。

## 5. 对构建/产物的预期影响

- **R8 program 输入**：+640 类（TraceurCommon+perfetto）、+8 R 类、+105 res、+1 manifest 合并。
  所有外部引用已实证闭合（§4.1-4.3），预期 added=0。
- **fresh R8 差分**：88→81，removed 恰为：FileSender、PresetTraceConfigs、TraceConfig、
  PresetTraceConfigs$TraceOptions、TraceConfig$Builder、traceur.res.R$array、traceur.res.R$string（7）。
  `AssumeTrueForR8` 保留。
- **debug 硬门禁**：`:app:assembleDebug` 必须 exit 0（含 res 链接与 manifest 合并）。
- **APK 行为对齐 AOSP**：合并 manifest 应新增 `CONTROL_UI_TRACING` 等权限（AOSP 同样合并）。

## 6. 风险与红线

- 640 个 perfetto proto 类首次进入 program scope：若有未预见外部引用（除 lite runtime/framework 外）→ added≠0 → REDLINE。
- res 链接若缺 leanback/v14 资源 → HALT 上报（新增官方依赖需用户批准），worker 不得自行加坐标。
- 不加任何 keep/-dontwarn；不改任何 res；不动 SettingsLib（下一批）；不碰 SysUISdk。
- 构建串行纪律：本批仅 worker 一个构建者；reviewer 静态验证；架构师主分支 fresh 复验排在最后。

## 7. 验收

以下为 Task 038 worker 于 2026-08-20 在 worktree `SystemUI-Gradle-wt-038`（branch `task-038-r8-runtime-batch4c-traceur`，base `57da6777`）填写的真实证据（全部命令真实运行，退出码未伪造）。

### 1. TDD 红/绿

- RED：新增 `TestTraceurProvenance`（8 用例）+ `TestAllFlag` CONFIGS 集合更新后，焦点运行 `Ran 10 tests / FAILED (failures=1, errors=7)`——仅直接读 Soong R.txt 的回归守卫用例绿，其余均因 CONFIGS 缺 Traceur 两项而失败，符合预期。
- GREEN：CONFIGS 实现后焦点 `Ran 10 tests / OK`；全量 `python3 -m unittest discover -s tools/tests` → **`Ran 179 tests in 46.149s / OK`**（171 基线 + 8 新增）。

### 2. 产物审计

- `libs/aars/TraceurCommon.aar`：1053643 bytes；`classes.jar` = **640 类**（`com/android/traceur/` 15 ∪ `perfetto/protos/` 625，两两不相交，字节与 Soong 输入一致）；无 res 条目；manifest=`AndroidManifest-common.xml`（package `com.android.traceur.common`，含 `CONTROL_UI_TRACING` 等 5 权限）；R.txt = Soong 空表；双跑 SHA-256 稳定：`e358570e907ee8c33f12e4c9a36fa741d923454d0ab872e125c0436bd02be2dd`。
- `libs/aars/Traceur-res.aar`：409115 bytes；`classes.jar` **0 类**；res 恰好 **105 文件**与 AOSP `packages/apps/Traceur/res` 字节一致；manifest=`AndroidManifest-res.xml`（package `com.android.traceur.res`）；R.txt 与 Soong 逐字节一致（139 符号，含 array 8/string 114）；双跑 SHA-256：`868237f6757f73719a6718b7551c966ae4e2e7b2caa53133b24e0e01554e40dd`。
- 重叠审计：两 AAR 互斥；与 `libs/*.jar`、`libs/aars/*.aar`、`libs/maven/**` 全量比对，唯一交集 = 待退役的 `libs/TraceurCommon.jar` 自身（15 类子集）；`libs/TraceurCommon.jar`、`libs/traceur-res-R.jar` 已 `git rm`，`git grep` 仅余历史文档记载与 AOSP 源路径引用，无功能性引用。

### 3. Debug 硬门禁

- `set -o pipefail; ./gradlew :app:assembleDebug 2>&1 | tee /tmp/task038-debug.log` → **exit=0，`BUILD SUCCESSFUL in 2m 53s`**（216 tasks）；`/tmp/task038-debug.status` = `exit=0`；无 leanback/v14 缺资源错误。
- APK（162931039 bytes）类定义（apkanalyzer `dex packages --defined-only`，架构师修正口径：source-set ⊆ defined-set）：**AAR 输入 640 类全部 defined，MISSING=0**（traceur 15/15；perfetto 625/625）。另 perfetto namespace 实测 defined 总数 679 = 625 源类 + 54 个 D8 interface-desugaring 合成类 `*-IA`（dexdump 证实 `D8$$SyntheticClass`，验收不计入）。
- traceur R 类由 AGP 从 R.txt 重新生成：`com.android.traceur.res.R{,$array,$color,$drawable,$id,$layout,$mipmap,$string,$style,$xml}` 全部 defined。
- merged manifest（`app/build/intermediates/merged_manifests/debug/processDebugManifest/AndroidManifest.xml`）：`CONTROL_UI_TRACING`、`START_FOREGROUND_SERVICES_FROM_BACKGROUND`、`QUERY_ALL_PACKAGES`、`FOREGROUND_SERVICE`、`WRITE_SECURE_SETTINGS` 5 权限全部在场。
- traceur res 链接验证：aapt2 dump resources 显示 `layout/custom_trace_settings_dialog`、`string/custom_trace_settings_dialog_title` 等进入 resources.arsc。

### 4. Fresh R8 差分

- Baseline（detached HEAD `57da6777`）：`./gradlew :app:minifyReleaseWithR8 -Dorg.gradle.workers.max=4` → exit=1（剩余 missing refs 阻塞，符合预期）；`missing_rules.txt` unique `-dontwarn` refs = **88**，7 个 traceur 目标与 `AssumeTrueForR8` 均在场。
- Changed（branch HEAD `0a0ba884`）：同命令 → exit=1（81 剩余）；unique refs = **81**。
- 机械差分：**removed = 恰好 7 个 traceur 目标**（FileSender、PresetTraceConfigs、PresetTraceConfigs$TraceOptions、TraceConfig、TraceConfig$Builder、traceur.res.R$array、traceur.res.R$string）；**added = 0**；`AssumeTrueForR8` 保留。PASS。

### 5. 卫生检查

- 改动文件仅 Allowed Paths（见下方 commit）；`git diff --check` 干净；英文 commit，未 push。

| 阶段 | R8 unique missing refs | 说明 |
|---|---:|---|
| Task 037 后 | 88 | fresh 基线（本批 detached-HEAD 实测复现） |
| 本批完成后 | 81 | 精确移除 traceur 7 项，新增 0（实测） |

### 原始验收清单（全部满足）

- [x] `python3 -m unittest discover -s tools/tests` 全绿（179）
- [x] 两 AAR 确定性（双跑同 SHA-256）；类集合 = 640 / 0（res-only）；命名空间零重叠验证
- [x] `libs/TraceurCommon.jar`、`libs/traceur-res-R.jar` 已删且无引用残留
- [x] `./gradlew :app:assembleDebug` exit 0（完整日志 + pipefail + status 文件）
- [x] APK：`com/android/traceur/` 与 `perfetto/protos/` 源集类全部 defined；merged manifest 含 `CONTROL_UI_TRACING`
- [x] fresh `minifyReleaseWithR8`：88→81 精确差分（added=0、`AssumeTrueForR8` 保留）
- [x] 审计文档 A7 行更新（实际落在 §3.2 映射表 A7 行，brief 所指“§4.2”即该行）

## 8. 待解决问题

- AGENTS.md §3.2 libs 树将滞后（`TraceurCommon.jar`/`traceur-res-R.jar` 行、`libs/aars/` 双 AAR 未列）——红线文件，由架构师合并时作事实性修正（与 036/037 同处理）。
- perfetto namespace 内 54 个 D8 `-IA` 合成类（interface desugaring，`D8$$SyntheticClass`）为 debug dex 正常现象，非来源问题，无需处理（架构师 2026-08-20 裁定）。
- 剩余 81 missing refs：SettingsLib 74（下一批 4D）+ B 类 6 + AssumeTrueForR8 1，不属本批。
