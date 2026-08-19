# 2026-08-20 — Release R8 / resource shrink AOSP 对齐决策

## 背景

Task 025 证明 `:app:assembleRelease` 被 `SystemUI-core/consumer-rules.pro` 悬挂引用阻塞。
Task 028 深度核对 AOSP Android.bp / Soong：AOSP 默认
`SYSTEMUI_OPTIMIZE_JAVA=true`，最终 app 开启 R8 optimize+shrink，非 eng 构建同时收缩资源；
SystemUI-core library 层零 ProGuard，plugin/plugin_core 通过 export flags 汇入 app。

## 用户批准（2026-08-20）

1. **G1**：完整删除 SystemUI-core 的 `consumerProguardFiles("consumer-rules.pro")` 和
   release `proguardFiles(..., "proguard-rules.pro")` 配置；core 与 AOSP 一样零 ProGuard。
2. **R3**：恢复 AOSP export flags 语义：
   - Android library `:SystemUI-plugin` 使用 `consumerProguardFiles`；
   - JVM library `:SystemUI-plugin-core` 无 AGP consumer DSL，AOSP 原始 flags 由 app
     `proguardFiles` 直接接入（规则文件仍归 module 所有；不为通道强改模块类型）。
3. **R1**：app release 开启 R8：`isMinifyEnabled=true`。
4. 保留官方 `proguard-android-optimize.txt`，叠加 byte-exact AOSP `proguard.flags` 链。
5. 不显式设置 `android.enableR8.fullMode`，采用 AGP 9.3.1 默认行为；如发现实证差异再单独决策。
6. **R2**：不推迟，R8 落地时同时设置 `shrinkResources=true`。
7. 不补 AOSP 自己未 export 的 SystemUIFlagsLib ParcelableFlag keep 规则。
8. 验收：release APK、platform 签名、关键类/dex、plugin rules 汇入、mapping/usage/seeds、147 tests。
9. 诊断边界：只可接入 AOSP 原始规则；禁止发明宽泛 keep、关闭 R8/检查或排除源码。
10. 批次：Task 029（G1+R3+未混淆 release 基线）→ Task 030（R1+R2 优化 release）。

## 依据

完整证据与 gap 表：`docs/architecture/2026-08-20-aosp-release-config-analysis.md`。

## 实施记录（Task 029：G1 + R3 + 未混淆 release 基线，2026-08-20）

### 改动

1. **G1**（`SystemUI-core/build.gradle.kts`）：删除 `consumerProguardFiles("consumer-rules.pro")`
   与整个 `buildTypes.release` 块（含悬挂 `proguard-rules.pro` 引用）；core 现与 AOSP
   android_library 层一致——零 ProGuard 配置。未创建空 .pro 文件。
2. **R3 :SystemUI-plugin**（Android library）：byte-exact 复制 AOSP
   `plugin/proguard_plugins.flags`（19 行）到模块根，`defaultConfig` 添加
   `consumerProguardFiles("proguard_plugins.flags")`（对应 bp
   `export_proguard_flags_files: true` + `proguard_flags_files`）。
3. **R3 :SystemUI-plugin-core**（JVM library）：byte-exact 复制 AOSP
   `plugin_core/proguard.flags` 到模块根；JVM 模块保持边界，不改 module plugin，由
   `app/build.gradle.kts` debug/release 两处 `proguardFiles(...)` 直接追加
   `rootProject.file("SystemUI-plugin-core/proguard.flags")` 接入最终 app。
4. app 的 `isMinifyEnabled`/`shrinkResources` 未动（默认 false），本基线用于隔离验证
   G1/R3；R1+R2 属 Task 030。

### 验收结果（真实命令输出）

- `diff -q` 两个 flags 文件 vs AOSP 原文件 → identical（BYTE_EXACT_OK）
- `git grep 'consumer-rules.pro\|proguard-rules.pro' -- SystemUI-core` → 无匹配（NO_DANGLING_REFS）
- `./gradlew :SystemUI-plugin:bundleReleaseAar :app:assembleRelease` →
  **BUILD SUCCESSFUL in 3m 47s**（383 actionable tasks: 11 executed, 372 up-to-date）
  - 首次运行时 Gradle daemon 被 OOM kill（-Xmx16g + Kotlin daemon 8.7GB RSS 超出内存）；
    以 `-Dorg.gradle.workers.max=4` 重跑成功（仅命令行参数，未改 gradle.properties）
- `python3 -m unittest discover -s tools/tests` → **Ran 147 tests / OK**
- `git diff --check` → 干净（DIFF_CHECK_OK）

### Release APK 基线信息（R8 未开启）

| 项 | 值 |
|---|---|
| 路径 | `app/build/outputs/apk/release/app-release.apk` |
| 大小 | 126,642,058 bytes（约 120.8 MiB） |
| SHA-256 | `0b16d484f0aa91162d7ba3641402f09412bbafa0f16578419137699216a6aca1` |
| dex | 8 个 classes*.dex（未混淆） |
| mapping | **未生成**（`outputs/mapping/release/` 不存在，R8 关闭，符合预期） |
| 签名 | V2，platform 测试证书（CN=Android，SHA-256 `c8a2e9bc…92ab8`） |

### 额外验证

- 解包 `SystemUI-plugin-release.aar`，其中 `proguard.txt` 与 AOSP
  `proguard_plugins.flags` diff → identical（consumer 规则成功打包进 AAR）。

### 待解决

- Task 030：R1（app release `isMinifyEnabled=true`）+ R2（`shrinkResources=true`），
    对照本基线验证 mapping/usage/seeds 与 keep 名单。
