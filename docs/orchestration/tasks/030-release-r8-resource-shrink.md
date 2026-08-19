# Task 030 — R1 + R2：app release 开启 R8 与资源收缩

## Authority

`redline-gated`。用户已批准 app release 同时开启 R8 + shrinkResources，并批准下述诊断边界。
本任务必须在 Task 029 合并且未混淆 release 基线成功后派发。worker 不 push。

## Goal

对齐 AOSP `SYSTEMUI_OPTIMIZE_JAVA=true` 的核心行为：最终 app release 执行代码
optimize/shrink 与资源收缩，消费 app AOSP flags 链和 Task 029 的 plugin flags，产出
可签名、关键反射入口仍保留的优化 release APK。

## Steps

1. `app/build.gradle.kts` release：
   - `isMinifyEnabled = true`
   - `shrinkResources = true`
   - 保留 `getDefaultProguardFile("proguard-android-optimize.txt")`
   - 保留 byte-exact AOSP `proguard.flags` 链及 plugin-core flags
2. **不**显式设置 `android.enableR8.fullMode`，采用 AGP 9.3.1 默认行为。
3. **不**加入 AOSP 未 export 的 SystemUIFlagsLib ParcelableFlag keep 规则。
4. 运行 `:app:assembleRelease`，系统性诊断任何 R8/shrinker 失败。
5. 只允许：核对/接入 AOSP 原始 flags、修正已批准通道的机械接线。
   禁止自创宽泛 keep、`-dontwarn **`、关闭 R8/shrink/check、排除源码或改 res。
   若 AOSP 原规则不足，停止并报告 `REDLINE`，不得猜规则。
6. 更新 release issue，记录优化前后 APK 大小与 R8 产物。

## Allowed Paths

- `app/build.gradle.kts`
- `docs/issues/2026-08-20-release-r8-alignment-decisions.md`
- `docs/orchestration/tasks/030-release-r8-resource-shrink.md`
- 如仅为 AOSP byte-exact 规则接线修正：Task 029 的两个 flags 文件及对应 build 文件
  （必须在报告逐项说明；内容不得偏离 AOSP）

## Forbidden Paths

- `src/**`、`res/**`、SysUISdk、依赖版本/模块边界
- `gradle.properties` full-mode 开关
- 自创 keep/dontwarn/优化绕过规则
- debug build type minify/shrink

## Acceptance

```bash
./gradlew :app:assembleRelease
# expected: BUILD SUCCESSFUL，app-release.apk 非零

# 签名
$ANDROID_HOME/build-tools/*/apksigner verify --verbose app/build/outputs/apk/release/app-release.apk
# expected: Verifies

# R8 诊断产物
ls app/build/outputs/mapping/release/{mapping.txt,configuration.txt,seeds.txt,usage.txt}
# expected: all exist and non-empty

# configuration.txt 中同时有 app / plugin / plugin-core 特色规则
grep -E 'SystemUIInitializerImpl|plugins\.\*\*|RuntimeVisible.*Annotation' \
  app/build/outputs/mapping/release/configuration.txt

# APK dex 中关键入口（使用可用的 apkanalyzer/dexdump）
# 必查：SystemUIApplication、SystemUIService、SystemUIInitializerImpl、VendorServices、
# DaggerReferenceGlobalRootComponent*；并抽查 plugin API 包。

./gradlew :app:assembleDebug
python3 -m unittest discover -s tools/tests -p 'test_*.py'
# expected: debug BUILD SUCCESSFUL；Ran 147 tests / OK

git diff --check
```

报告 release APK 路径/大小/SHA-256、debug/release 大小对比、签名、关键类、
mapping/usage/seeds、resource shrink 结果与所有 warning。

## Reports To

架构师。报告 commit、真实验证、HANDOFF；never push。失败时给首个失败任务、错误原文、
根因分类和 REDLINE，不得用绕过配置伪造成功。
