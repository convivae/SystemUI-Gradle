# SysUISdk r1 GitHub Release 发布记录

**日期**：2026-09-03
**状态**：已完成并由用户验收
**发布方案**：方案 A——发布现有生成器产出的 SysUISdk；既有 r1 Release 与 tag 保持不变

> 2026-09-03 文档修订：原标题“SysUISdk 底座切换为 AOSP 自构建 SDK 并发布 Release zip”
> 与最终执行的方案 A 不符，现改为发布记录。该修订只澄清文档，不改代码、资产或既有 tag。

## 背景与决策

当前 SysUISdk 由只读官方 `android-37.0` SDK 平台底座与 AOSP `android-17.0.0_r1`
构建产物合成，补齐 framework 类、framework 私有资源、隐藏 AIDL 声明和 R8 library bridge。
`libs/` 已全部提交到 git；发布 SysUISdk 后，外部开发者只需 clone 仓库并安装 Release zip
即可编译，无需先下载或构建 AOSP。运行和替换系统 SystemUI 仍需要 same-tree 模拟器镜像。

最初考虑的方案 B 是先构建 AOSP SDK 底座，再改造生成器。实际执行 `m sdk` 时，
soong_build 分析阶段在约 33.7 GiB 可用内存下连续两次 OOM（exit 137）；sdk 变体的分析峰值
高于 C1 普通全量构建的 26 GiB，且当时磁盘仅余约 20 GiB。用户随后决定采用方案 A：
直接打包和发布已经通过项目构建验证的现有 SysUISdk，并在发布物中披露组成与适用条款。
方案 B 作为未来可选研究保留，不是 r1 的组成或使用前提。

## 发布内容

1. `tools/package_sysuisdk_release.py` 校验 generator marker，生成排序条目、固定时间戳和属性的 zip，
   并生成 GNU `sha256sum --check` 可直接消费的 `.sha256` sidecar。
2. zip 包含 `android-SysUISdk/` 平台目录和顶层 `LICENSE`、`NOTICE`、`README.txt`。
3. GitHub Release tag 为 `sysuisdk-android-17.0.0_r1-r1`，包含 zip 与 sidecar 两个资产。
4. 双语 README 以下载 r1 为主路径，同时保留从 AOSP 构建产物自行再生的可选路径。
5. 发布工具新增 8 个 focused tests；原 361 个 Python tests 加上本批 8 个后为 369。

## 最终资产

- Release：<https://github.com/convivae/SystemUI-Gradle/releases/tag/sysuisdk-android-17.0.0_r1-r1>
- zip：`SysUISdk-android-17.0.0_r1-r1.zip`
- 大小：79,982,462 B
- 条目：11,389（平台 11,386，另有 LICENSE / NOTICE / README.txt）
- SHA-256：`ee5bd82d664c0387473765feeea0df1c90b2fab57493765edf9bbae21c3ba1dd`
- sidecar：`SysUISdk-android-17.0.0_r1-r1.zip.sha256`
- 确定性检查：同一输入和工具链下连续两次打包字节一致
- 用户验收：从该 Release 安装 SysUISdk 后，项目可以正常编译

## 安装与校验文档

README 的主路径现提供简洁、可复制的安装与校验步骤：

1. 在固定 Release 页面下载 zip 与 `.sha256`；
2. 在解压前执行 `sha256sum --check`，必须得到 `OK`；
3. 只解压归档中的 `android-SysUISdk/*`，避免将顶层发布文档散落到 SDK 的
   `platforms/` 根目录；
4. 若目标目录已经存在则停止，不静默覆盖或混合旧文件；
5. 校验 `android.jar` 存在后再运行 Gradle。

仓库内 canonical Release body 见 [`release/sysuisdk/GITHUB_RELEASE.md`](../../release/sysuisdk/GITHUB_RELEASE.md)。
当前执行环境没有 `gh` CLI、GitHub CLI auth 配置或 HTTPS credential，因此本次无法直接修改已经发布的
GitHub Release 网页正文；r1 Release、资产和 tag 均保持不变。

## Tag 与提交记录

- 既有 lightweight tag `sysuisdk-android-17.0.0_r1-r1` 指向 `e5ca8dda`。
- 发布工具、发布物文本和第一版下载型 README 随后提交于 `928353a0`。
- 用户决定保留 r1，不撤销、不移动该 tag；以上顺序作为 r1 的历史事实记录。
- 后续 release 应先完成实现、文档和验收提交，再创建带说明的 tag 和 GitHub Release。

## 许可证与来源说明

- AOSP 来源部分按 Apache License 2.0 提供，归档中附带 `LICENSE`。
- 官方 SDK 底座文件仍受 Android SDK License Agreement 约束；归档中的 `NOTICE` 说明组成、来源和条款链接。
- r1 沿用当前发布方案。当前生成器仍以官方 `android-37.0` 为只读底座；文档不再声称现有命令可以生成
  “100% AOSP-sourced”底座。

## 方案 B 调研备忘（未实施）

- `m sdk` 入口位于 `build/make/core/main.mk`（`sdk: $(ALL_SDK_TARGETS)`）；`is_sdk_build`
  会额外纳入 samples 标签模块，分析内存峰值高于普通 `m`。
- 两次失败日志为 `/tmp/aosp-sdk-build.log`、`/tmp/aosp-sdk-build2.log`，均 exit 137 / Killed。
- soong_build 以 `env -i` 运行，GOMEMLIMIT 等 Go runtime 环境变量无法直接传入；当时未找到
  可用的 Soong 内存限制开关。
- 生成器底座消费点：`_copy_base_platform` 复制除 `android.jar`、
  `core-for-system-modules.jar`、`framework.aidl` 外的文件；`compose_android_jar` 以底座
  `android.jar` 非资源条目为底、framework 聚合类覆盖、`framework-res.apk` 提供资源；
  `package.xml` 重写身份字段，`source.properties` 原样复制。
- 重新评估方案 B 的前提是增加 swap 和可用磁盘，并先取得 `m sdk` 成功证据。

## 本次文档修订验证

- 不修改代码或发布资产，因此 Gradle/Kotlin 编译错误数不变。
- 仅运行 Markdown、链接、shell 语法与 git diff 检查；不重复运行用户已经完成的 Release 编译验收。
