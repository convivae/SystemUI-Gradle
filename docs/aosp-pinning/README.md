# 历史 AOSP 树快照

[`aosp-manifest-2026-08-26-validated.xml`](aosp-manifest-2026-08-26-validated.xml)
是 2026-08-26 的 AOSP `main` 树快照：`repo manifest -r` 机械导出，
1042 个 project 均带精确 revision。它用于追溯当时 SDK/依赖再生及双变体运行验证，
**不是当前 Android 17 基线，也不随当前构建更新**。

当前基线 `android-17.0.0_r1` 的准备方法见 [项目 README](../../README.md)。
历史验证背景见 [再生性分析](../architecture/2026-08-26-regeneration-gap-closure.md)。
如需复现旧 main 树，应在单独 checkout 中使用这份固定 manifest，不覆盖当前 AOSP 工作树。
