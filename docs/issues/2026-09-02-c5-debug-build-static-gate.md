# C5 Task 096：fresh Debug APK build/static gate

**日期**：2026-09-02
**状态**：PLANNED
**前置**：Task 095 production immutable-input seam已在commit `2994fa8f`落地并push；corrected bounded direct gate、Standards/Spec双轴review及focused re-review均PASS。

## 背景

Task 095只证明production visitor在真实dependency transform中至少完成一个allowlisted instruction-level rewrite，且managed 4/166 input seam可通过AGP worker isolation。它没有构建或验收新的Debug APK，也没有证明四条runtime-critical mappings在完整program closure中全部生效。

本任务是独立、no-fix、单Gradle调用的build/static gate。它不得修改tracked文件，不运行Release/R8，不启动设备，不恢复Task 079 broad replay。Debug无shrinking，APK可合法保留old source definitions及其current-class self-reference；因此release-oriented checker可能exit 1，不能单凭该exit判定本任务失败。

## 计划与验收

1. 只读确认`HEAD == origin/main == 2994fa8f`、tracked worktree clean且无Gradle/Kotlin/Soong/Ninja活动进程。
2. 建立`/tmp/task096-c5-debug-build-static/`，记录preflight；删除仅生成物`app/build/outputs/apk/debug/app-debug.apk`，防止失��后误收旧APK。
3. 全程仅运行一次Gradle wrapper：
   ```bash
   ./gradlew :app:assembleDebug --console=plain --rerun-tasks --max-workers=4
   ```
   用`set -o pipefail`保存真实exit code与完整日志。失败即停止，不做修复。
4. 成功后记录APK size/SHA-256并以`unzip -t`验证完整性；用authoritative AOSP `repackaging.txt`运行现有checker并单独保存exit code。
5. Debug静态判据：四个critical hidden targets全部referenced；全725规则hidden target definitions为0。对四个critical old source descriptors，以SDK 37 `dexdump -d`按当前class context枚举全部DEX残留；只允许old source class自身definition/current-class self-reference，任何其他class中的old descriptor残留均FAIL。
6. 记录tracked status并执行一次冻结cleanup；不commit、不push。

## 成功边界

PASS仅表示fresh Debug APK编译成功且四映射静态闭合。它不证明Release/R8，不证明设备运行或整机重启稳定，也不授权修改visitor/checker。PASS后下一独立阶段才是Release build/static gate。

## 错误数演变与待解决问题

- Task 082旧Debug pipeline在factory isolation阶段FAIL，未产出候选APK。
- Task 095已消除该已知isolation触发边界，但fresh full Debug build尚未执行。
- 若本任务失败，保留首个actionable failure和全部静态证据，Chief另立修复任务；本任务自身不改代码。
