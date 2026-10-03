# 本机 SysUISdk 安装与完整离线交付

日期：2026-10-03

## 用户授权 / 范围

用户明确授权：替换本机已安装 SDK、不保留旧 SDK；将全部修改及 SDK 打包给另一台机器
发布（另一机器可能只有 GitHub 下载的源码 ZIP、无 .git）。随后增加修复既有 SettingsTheme
资源清单测试失败。**仍禁止本机 push / Release / 附件上传**。

## 计划

1. 停止 Gradle daemon（当前无构建进程），由正式生成器 --replace 从既有七个 AOSP 输入
   再生本机平台；输出与已验收 SDK 一致，旧目录仅作事务期 rollback，成功后由生成器删除。
2. 新 daemon 下验证本机 root project 的真实 Tooling API 模型和 JVM fixture，精确路径为
   `/home/leijiabin/Android/Sdk/platforms/android-SysUISdk`。
3. 独立诊断/修复 SettingsTheme 既有失败；详情另记 issue，禁止改资源绕测试。
4. 增量本地 commit；完整离线包包含 self-contained Git bundle（仅 main 可达历史、无
   外部 prerequisite）、累计 patch、SDK ZIP/sidecar、发布说明、摘要及发布步骤。
   不打包 .git/config、SSH/gh 凭据、local.properties、构建缓存或个人未提交修改。
5. 本地从 bundle clone，验证提交/tree 完整；累计 patch 从 GitHub 基线应用验证；
   ZIP 全文件 SHA 校验。另一机器无需网络即可恢复代码+Git 历史；上线发布由用户自行操作。

## 安装及验收结果

执行：

```bash
./gradlew --stop
uv run --offline python tools/build_sysuisdk.py \
  --aosp-root /home/leijiabin/myspace/aosp \
  --sdk-root /home/leijiabin/Android/Sdk --replace
```

- 停止 2 个 idle daemon 后，正式生成器 045.3 完成 live SDK 事务替换。
- live marker 与此前已验收的 11,386-file SDK marker 完全相同。
- 生成器的临时 old/staging 目录已清空；没有为旧平台保留永久副本。官方 android-37.0 底座
  未修改，用户原有 SDK 根下其他组件未删除。
- root project 的实际 Tooling API 模型：13 Android 模块/26 variants PASS；
  `model.log` 位于 `/tmp/sysuisdk-live-handoff/`。
- `ANDROID_HOME=/home/leijiabin/Android/Sdk ./gradlew -p tools/tests/fixtures/sysuisdk_optional_bridge
  testDebugUnitTest --no-daemon --offline --rerun-tasks --console=plain`：4 tests PASS，
  精确 bridge 路径为 live SDK，见 `jvm.log`。未手动操作 Studio UI。
- 从 live SDK 再次调用发布打包器，产物与已验收 r2 ZIP 逐字节相同（`cmp`）：
  79,983,909 B / `329fd0e12a19b8004180fb74f0a9a3817b2e7b3c1fc36617a8af7d535b5543ae`。
- SettingsTheme 修复（commit c962742c）已闭环，见同日资源清单 issue；全 Python suite
  **368 passed +156 subtests**。仅测试/文档变化，无新 APK 输入，不重复完整 APK 构建。

## 完整离线包合同

输出 `dist/SystemUI-Gradle-offline-release-2026-10-03.zip`，内含一个目录：

- `SystemUI-Gradle-main.bundle`：只导出 main 及可达祖先的 self-contained Git bundle，
  带已提交的源码、libs、原 Git 历史和本轮增量 commits；无外部 prerequisite。
  不是直接压缩 .git，不含 config/hooks/reflog/SSH/gh 凭据或未提交文件。
- `SystemUI-Gradle-changes.patch`：从 GitHub 基线 35def1f4 起的累计 format-patch。
  与 bundle **二选一**恢复改动，不重复应用。
- `SysUISdk-android-17.0.0_r1-r2.zip` / `.zip.sha256`：SDK 发布资产。
- `COMMITS.txt`：精确 HEAD/tree/base 与增量 commit 记录。
- `RELEASE_NOTES.md`：更新后的发布草稿，已说明 SettingsTheme 失败修复。
- `README.md`：有 Git clone / 只有源码 ZIP 两类接收方的恢复与异机发布步骤。
- `SHA256SUMS`：包内文件摘要；外层 ZIP 另有 `.sha256`。

有 Git clone 的接收方可 fetch bundle 后 fast-forward；仅有源码 ZIP 的接收方直接从
bundle clone 到新目录，即可保留真实历史和 commit，不需要凭空 git init 制造基线。
不需要转移 AOSP/out、完整 Android SDK、构建缓存或个人环境；再生 SDK 时才需要 AOSP
和官方底座（本包已携带可直接安装/发布的 SDK）。

交付前检查：bundle verify / 从 bundle clone / git fsck 与精确 HEAD/tree 对比；
累计 patch 在原基线 git am 并比较 tree；全包清单 SHA、内层 SDK 摘要与外层 ZIP 校验。
这些是本地操作，不涉及上传/下载远端内容。
