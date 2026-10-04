# Task 029 — G1 + R3：core 零 ProGuard、恢复 export flags、未混淆 release 基线

## Authority

`self-commit`。用户已于 2026-08-20 批准本任务全部配置变更；worker 不 push。

## Goal

按 AOSP 语义修复当前 release 阻塞：SystemUI-core library 零 ProGuard；恢复
SystemUI-plugin/plugin-core flags 汇入最终 app 的通道；在 R8 尚未开启时首次产出
未混淆 release APK，作为 Task 030 对照基线。

## Steps

1. **G1 core 清理**：
   - 删除 `SystemUI-core` 的 `consumerProguardFiles("consumer-rules.pro")`；
   - 删除 core 的整个 `buildTypes.release` 块（只含 `isMinifyEnabled=false` 和悬挂
     `proguard-rules.pro`；AOSP core 无对应配置）；
   - 不创建空 `.pro` 文件。
2. **R3 SystemUI-plugin（Android library）**：
   - byte-exact 复制 AOSP `plugin/proguard_plugins.flags` 到
     `SystemUI-plugin/proguard_plugins.flags`；
   - `defaultConfig` 添加 `consumerProguardFiles("proguard_plugins.flags")`。
3. **R3 SystemUI-plugin-core（JVM library）**：
   - byte-exact 复制 AOSP `plugin_core/proguard.flags` 到
     `SystemUI-plugin-core/proguard.flags`；
   - JVM module 无 AGP consumer DSL，保持 JVM 边界，不改 module plugin；
   - 在 `app/build.gradle.kts` 现有 debug/release `proguardFiles(...)` 中直接加入
     `rootProject.file("SystemUI-plugin-core/proguard.flags")`，使最终 app R8 获得同一规则。
4. **本任务禁止开启 R8/resource shrink**：app release 仍维持默认
   `isMinifyEnabled=false` / `shrinkResources=false`，用于隔离验证 G1/R3。
5. 更新 `docs/issues/2026-08-20-release-r8-alignment-decisions.md` 实施记录。

## Allowed Paths

- `SystemUI-core/build.gradle.kts`
- `SystemUI-plugin/build.gradle.kts`
- `SystemUI-plugin/proguard_plugins.flags`（AOSP byte-exact 新文件）
- `SystemUI-plugin-core/proguard.flags`（AOSP byte-exact 新文件）
- `app/build.gradle.kts`
- `docs/issues/2026-08-20-release-r8-alignment-decisions.md`
- `docs/orchestration/tasks/029-release-g1-r3-baseline.md`

## Forbidden Paths

- `src/**`、`res/**`、任何 AOSP 镜像源码
- `gradle.properties`、版本 catalog、module 类型/边界
- app 的 `isMinifyEnabled`/`shrinkResources`（Task 030 才改）
- 自创/修改 AOSP flags 内容

## Acceptance

```bash
# 两个规则文件 byte-exact
diff -q SystemUI-plugin/proguard_plugins.flags \
  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/plugin/proguard_plugins.flags
diff -q SystemUI-plugin-core/proguard.flags \
  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/plugin_core/proguard.flags

# core 无悬挂配置
git grep -n 'consumer-rules.pro\|proguard-rules.pro' -- SystemUI-core && exit 1 || true

# Android library consumer rules 可打包；最终 release 基线
./gradlew :SystemUI-plugin:bundleReleaseAar :app:assembleRelease
# expected: BUILD SUCCESSFUL，release APK 非零

python3 -m unittest discover -s tools/tests -p 'test_*.py'
# expected: Ran 147 tests / OK

git diff --check
```

额外记录：release APK 路径、大小、SHA-256；确认本次未生成 mapping（R8 未开）。

## Reports To

架构师。报告 commit、真实命令输出、APK 信息、HANDOFF；never push。
