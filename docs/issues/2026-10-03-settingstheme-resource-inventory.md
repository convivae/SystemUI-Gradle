# SettingsTheme AAR 资源清单测试失败诊断

日期：2026-10-03

## 背景

SDK 修复期间全 Python suite 存在 1 个既有失败：
`TestSettingsLibSettingsThemeProvenance.test_res_entries_match_aosp_tree_exactly`。
已在原 HEAD 35def1f4 复现。用户本轮要求修复，不能仅将其作为已知失败保留。
AOSP 根使用用户指定的 `/home/leijiabin/myspace/aosp`，通过 AOSP_ROOT 传入统一路径机制。

## 计划

1. 重跑精确测试建立反馈循环，比较实际缺/多资源名称与内容。
2. 阅读测试、SettingsTheme 打包族配置与 AOSP Android.bp，分别判断测试预期、打包产物、
   源码版本/路径是否有误；按已证据给出最小修复。
3. 若测试预期错误，只修测试并保留完整来源核对；若打包产物错误，按 AAR 内容变化升版本规则
   处理，涉及资源源码修改/架构决策时先询问，禁止擅改 res。
4. 精确回归与全工具测试；将修复、原因和证据纳入离线 patch/bundle。

## 根因与修复

实测：测试的旧硬编码目录不存在，`Path.rglob()` 静默返回空集合；测试比较的是 AAR 的
230 个真实资源与 0 个预期资源。打包脚本则正确使用共享 AOSP_ROOT 机制指向本机目录。
AOSP `SettingsTheme/Android.bp` 的 `resource_dirs: ["res"]` 与 packager 配置一致。
临时再生的 AAR 有 230 项 res，与真实源码目录逐项/逐字节一致，且整体 AAR 与
仓库 `libs/aars/SettingsLibSettingsTheme.aar` 字节相同。**没有产物/资源缺失。**

修复仅涉及测试：
- 删除固定 `/home/conv/...` 路径，调用时从 packager 的共享 AOSP_ROOT 派生独立的
  AOSP 相对路径；不直接读 CONFIGS 的 res 路径，以免测试跟随错误打包配置一起通过。
- 显式断言资源目录存在且文件集合非空，避免路径错误时被误判为资源差异或空对空通过。
- 路径使用 as_posix，保持 ZIP entry 在不同操作系统上的表示一致。
- 增加缺失/空目录两个负例，不创建资源替身。

未改 SystemUI/AOSP 资源、AAR/JAR、Gradle 依赖坐标；AAR 内容未变，无需升 Maven version。

## 验证

- 原精确测试 FAIL，日志 `/tmp/settingstheme-failure.log`。
- 新 missing/empty guard 测试修复前两个 subtest FAIL：
  `/tmp/sysuisdk-live-handoff/settingstheme-guard-red.log`。
- 修复后 `AOSP_ROOT=/home/leijiabin/myspace/aosp uv run --offline pytest tools/tests -q`：
  **368 passed，156 subtests passed，4 个预期 duplicate ZIP fixture warnings**。
  日志 `/tmp/sysuisdk-live-handoff/pytest-all.log`。
- 本轮没有重跑 APK 构建：仅测试路径/断言改动，SDK 生产实现与已验收 APK 输入未变。
