# SysUISdk 底座切换为 AOSP 自构建 SDK 并发布 Release zip

**日期**：2026-09-03
**状态**：已完成（方案 A）
**决策（2026-09-03 修订）**：最初用户拍板方案 B（底座换 AOSP 自构建 SDK）。执行中发现 `m sdk`
的 soong_build 分析阶段在约 33.7G 可用内存下连续两次 OOM（exit 137；sdk 变体分析峰值高于
普通构建的 26G，GOMEMLIMIT 因 ninja `env -i` 无法传入 soong_build，C1 当年的 32G swap 已不在），
且磁盘仅剩 20G。用户据此改拍 **方案 A**：直接打包现有 `android-SysUISdk`（官方 SDK 底座 +
AOSP 合并，生成器 marker 完备）发布到 GitHub Releases，附带 LICENSE/NOTICE 说明成分与来源。
方案 B（AOSP 底座）留作未来法律洁癖方向，需 32G+ swap 与磁盘空间。

## 背景与动机

- 当前 SysUISdk = 官方 SDK 平台底座 + AOSP `out/` 产物合并（framework 类、framework-res、
  framework.aidl 隐藏声明、R8 library bridge）。底座文件受 Android SDK License Agreement
  约束，严格条款不允许再分发。
- 项目立身之本是"无 stub、一切真实 AOSP 产物、可复现可审计"；发布物应过同样标准。
- `libs/` 已全部入 git；SysUISdk 发布后，外部开发者构建本工程将完全不碰 AOSP。
- 运行仍需要 same-tree 模拟器镜像（本任务不解决，另行决策）。

## 计划（方案 A）

1. **打包脚本** `tools/package_sysuisdk_release.py`：校验 generator marker → 确定性 zip
   （排序条目、固定时间戳/属性、deflate）→ 输出 `SysUISdk-android-17.0.0_r1-r1.zip` + SHA-256。
   zip 内含 `android-SysUISdk/` 平台目录 + 顶层 `LICENSE`（Apache 2.0）/ `NOTICE`（成分与来源）/
   `README.txt`（安装说明）。
2. **发布物文本** `release/sysuisdk/{LICENSE,NOTICE,README.txt}` 入库，打包脚本内嵌进 zip。
3. **GitHub Release**：tag `sysuisdk-android-17.0.0_r1-r1`，附 zip + `.sha256` 两个资产。
4. **README 双语** Quickstart 改为“下载 zip 解压”为主路径，AOSP 全量路径降为可选再生路径。
5. **文档同步**：CURRENT_STATE / HANDOFF / PLAN / AGENTS.md 工具表 / 本 issue。
6. **脚本测试**：marker 缺失拒绝、两次打包字节一致、条目集合与前缀正确。

## 历史：方案 B 尝试记录（已搁置）

## 待解决

- zip 实际体积与 SHA-256（打包后记录）。
- ~~Release notes 与 README 下载链接的最终 URL（发布后回填）。~~
- 未来基线升级时的再发布纪律（每次换 AOSP tag → 重新生成 SysUISdk → 发新 rev）。
- 方案 B 重启条件：32G+ swap、足够磁盘、`m sdk` 成功后按上文历史计划执行。

## 结果（2026-09-03，方案 A 完成）

- **打包**：`uv run python tools/package_sysuisdk_release.py` → `dist/SysUISdk-android-17.0.0_r1-r1.zip`，
  79,982,462 B，11,389 条目（平台 11,386 含 marker + LICENSE/NOTICE/README.txt），
  SHA-256 `ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`；
  两次打包字节一致（确定性验证通过）；`.sha256` sidecar 同步生成。
- **发布**：GitHub Release `sysuisdk-android-17.0.0_r1-r1`（zip + .sha256 两资产），
  https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1
- **脚本与测试**：新增 `tools/package_sysuisdk_release.py`（marker 门禁、symlink 拒绝、
  确定性 zip、sidecar）+ `tools/tests/test_package_sysuisdk_release.py`（8 tests）。
- **发布物文本**：`release/sysuisdk/{LICENSE,NOTICE,README.txt}` 入库；NOTICE 完整披露
  许可证栈（AOSP 部分 Apache 2.0 + 官方 SDK 底座部分仍受 Android SDK License Agreement 约束）。
- **README 双语**：Quickstart 改为“下载 zip”为主路径（方式 A），AOSP 生成降为方式 B / 可选第 3 步。
- **.gitignore**：新增 `dist/`。
- 首次 `gh release create` 因 keyring 内 token 失效返回 401，用户重新 `gh auth login` 后发布成功。

## 方案 B 调研备忘（已搁置，供未来参考）

- `m sdk` 入口存在于 build/make/core/main.mk（`sdk: $(ALL_SDK_TARGETS)`）；`is_sdk_build`
  会额外纳入 samples 标签模块，分析内存峰值高于普通 `m`。
- 两次失败日志：`/tmp/aosp-sdk-build.log`、`/tmp/aosp-sdk-build2.log`（均 exit 137 Killed）。
- soong_build 以 `env -i` 运行，GOMEMLIMIT 等 Go runtime 环境变量无法传入；soong 无内存限制开关。
- 生成器底座消费点已摸清：`_copy_base_platform` 复制除 android.jar / core-for-system-modules.jar /
  framework.aidl 外的全部文件；`compose_android_jar` 以底座 android.jar 非资源条目为底、framework
  聚合类覆盖、framework-res.apk 提供全部资源；package.xml 重写身份字段；source.properties 原样复制。
- 生成器现有测试使用合成 fixture，底座切换对测试影响小（仅 CLI 默认值断言需改）。
