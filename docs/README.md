# 文档索引

## 使用与维护

- [项目说明与构建步骤](../README.md) / [English](../README.en.md)
- [开发规则](../AGENTS.md)：源码、资源、依赖和验证边界
- [故障排查](PITFALLS.md)：SDK、编译、资源、R8 和设备部署
- [Gradle 构建设计](architecture/gradle-build.md)：模块/产物边界、平台依赖与 AGP 适配
- [SDK JVM/IDE 验证](../tools/tests/fixtures/sysuisdk_optional_bridge/README.md)

## 设计依据（按需阅读）

| 主题 | 文档 |
|---|---|
| 资源及依赖来源 | [ADR 0001](adr/0001-aosp-res-via-local-maven.md) |
| Python 维护工具 | [ADR 0002](adr/0002-tools-scripts-only-python.md) |
| Android.bp 与 Gradle 模块语义 | [ADR 0003](adr/0003-app-module-aligns-aosp-bp.md) |
| CONV 标记、授权与对齐 | [ADR 0004](adr/0004-conv-markup-and-alignment-discipline.md) |
| SettingsLib 资源依赖 | [ADR 0005](adr/0005-local-maven-transitive-poms.md) |
| SysUISdk 与 optional bridge | [ADR 0006](adr/0006-sysuisdk-r8-library-class-bridge.md) |
| pre-D8/R8 aconfig 引用改写 | [ADR 0008](adr/0008-pre-dex-aconfig-reference-rewrite.md) |
| namespace 归属 | [namespace 设计](architecture/2026-08-29-namespace-design.md) |
| 共享 UID 与平台权限 | [sharedUserId 根因](architecture/2026-09-03-systemui-shareduserid-appid-regression.md) |

版本、模块列表、产物映射以构建配置和生成器为准，不另维护实时状态清单。
文档只在使用方法、设计或重要限制变化时更新；日常计划和验证结果可在对话/提交中说明。

## 历史资料

- [项目构建历程（冻结归档）](HISTORY.md)：从 Soong 移植到独立 Gradle 工程的完整时间线，
  含各阶段问题、解法与可迁移经验；写成后不维护。

`issues/` 和按日期命名的 `architecture/` 报告保留独有根因、来源或授权证据，
不作为当前规则、待办或构建状态，也不因新测试结果持续更新。按相关问题查阅即可。
[ADR 0007](adr/0007-phase-c-clean-regen-release-tag.md)是已完成的 AOSP 17 迁移决策，
[aosp-pinning](aosp-pinning/README.md)是旧 main 树快照，
[release-manifest](release-manifest/README.md)只对应其指定的发布版本。

已删除的交接、编排和计划记录可从 Git 历史查阅，无需恢复到工作树：

```bash
git log --all -- <历史路径>
git show <提交>:<历史路径>
```

历史报告中 `git show 570b8c23:<路径>` 指向文档精简前的版本；这些引用只用于追溯。
