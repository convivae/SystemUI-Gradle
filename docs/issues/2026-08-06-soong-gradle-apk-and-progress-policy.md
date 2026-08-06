# Soong/Gradle APK 入口与项目推进规则更新

**日期**：2026-08-06

## 背景

用户确认入口类必须留在 `:SystemUI-core`，并要求解释 AOSP `android_app "SystemUI"` 在无独立源码时如何生成 APK，以及 Gradle 是否可以采用同样的模块边界。

用户同时取消以下历史限制：

- 每次提交必须降低编译错误数
- 错误数上升超过 50 必须回滚/审批
- 错误数上升超过 200 必须停止并询问
- 每次修改或每次提交必须运行编译

## 本次操作

1. 从 AOSP `Android.bp` 和 Soong `build/soong/java/{app.go,base.go}` 调研 APK 生成流程。
2. 记录 `android_app` / `static_libs` 与 Gradle application / implementation 的对应关系。
3. 修正 ADR 0003 中关于 manifest 和 `AndroidManifest-res.xml` 的历史误述。
4. 将规则 I 替换为“项目进度向前推进”原则。
5. 明确编译是按需验证工具，不是每次修改/提交的强制门槛。
6. 将当前工作区拆为实现 WIP checkpoint 与规则/调研文档两个 commit 并 push。

## 验证策略

本次不要求源码编译。使用以下证据：

- Gradle `debugRuntimeClasspath` 包含 `project :SystemUI-core`
- `:app` 存在 `assembleDebug` / `packageDebug` 等任务
- Python 脚本通过 `py_compile`
- 新增 jar 通过 ZIP 完整性检查
- 文档通过 `git diff --check`

如未运行 `:app:assembleDebug`，文档必须明确不能声称 APK 已成功构建。

## 当前已知问题

- AAR 中重复 R 类仍会在 transform 阶段阻塞构建。
- `gen_aar_maven.py` 当前改写是待回滚/重新诊断的中间态。
- `:app` 仍有若干 core 之外的直接依赖，后续需按 bp 审查。
- `AndroidManifest-res.xml` 当前位于 app 但未被 app Gradle 配置消费，后续建立独立 `SystemUI-res` module 时按 bp 归位。
- `PlatformMotionTestingComposeValues.jar` 按 bp 应属于 `:SystemUI-compose-core` 的依赖；当前临时写在 `:SystemUI-core`，后续应改为 compose-core 的可传递依赖。

## Checkpoint 验证结果

- 四个 Python 脚本通过 `python3 -m py_compile`。
- 两个新增 jar 通过 `unzip -t`：
  - `libs/contextualeducationlib.jar` 与 AOSP `.../contextualeducationlib/android_common/kotlin/contextualeducationlib.jar` SHA-256 完全一致：`21827c3c18dd1f8087eaac1bbecaa339fcb9679818a7d10dff169b6b1bc61385`
  - `libs/PlatformMotionTestingComposeValues.jar` 与 AOSP `.../PlatformMotionTestingComposeValues/android_common/kotlin/PlatformMotionTestingComposeValues.jar` SHA-256 完全一致：`beb021cfba4d335a05b77ccbaf18a7f935154f04bd1196531d78e4edaafba59e`
- `:app:dependencies --configuration debugRuntimeClasspath` 退出 0，包含 `project :SystemUI-core`。
- `:app:tasks --all` 退出 0，包含 `assembleDebug` 和 `packageDebug`。
- 未运行源码编译或 `:app:assembleDebug`，因此不声称 APK 构建成功。
- `tools/check_source_alignment.py --summary` 当前结果：源码缺 13、多 7；res 缺 0、多 7；另有未建立 module 的 SystemUIShaderLib 22 个文件。该结果用于下一步校准，不阻止 checkpoint。
