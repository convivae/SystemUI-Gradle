# SysUISdk r1 发布文档与 README 修订

**日期**：2026-09-03
**状态**：已完成
**范围**：仅文档；不修改代码、构建逻辑、发布资产或既有 r1 tag

## 背景

SysUISdk r1 已发布并由用户验收，可用于正常编译。后续 review 发现仓库 README 与归档内安装说明存在不可直接复制执行的问题：尖括号占位符会被 shell 解释为重定向，`sha256sum` 仅打印摘要而未使用 sidecar 校验，且下载路径、已有安装目录和解压顺序不够明确。README 顶部也缺少类似成熟开源项目的状态 badges。

当前环境没有 `gh` CLI、`~/.config/gh/hosts.yml` 或可用的 GitHub HTTPS credential，因此不能直接编辑已发布 Release 的网页正文；本次同步维护仓库中的发布说明，并提供可直接粘贴到 Release body 的 canonical 文本。

## 操作计划

1. 为中英文 README 添加真实、可追溯的 badges；仓库目前没有 GitHub Actions workflow，因此不伪造 CI badges。
2. 将克隆、sidecar 校验和安装命令改成可直接复制执行的 Bash 命令；下载动作保持为成熟开发者熟悉的 Release 页面操作，不在 README 堆叠 `curl` 细节。
3. 修订 `release/sysuisdk/README.txt`，确保先校验、后安装，并明确已有目标目录时 fail closed。
4. 修订原发布 issue 的标题、方案表述、验收结果、tag 历史和许可证措辞。
5. 同步 `docs/CURRENT_STATE.md` 的测试数与用户完成的发布资产编译验收。
6. 新增 canonical GitHub Release notes，供当前 Release 手工粘贴或后续 release 复用。

## 结果

- 中英文 README 顶部新增 AOSP 基线、双 variant 验证、Gradle、AGP 与 Kotlin badges；由于仓库没有 GitHub Actions workflow，没有添加虚假的 CI badge，也不展示下载量。
- README 改为“在 Release 页面下载两个资产 → `sha256sum --check` → 只解压 `android-SysUISdk/*` → 验证 `android.jar`”的简洁流程。
- `release/sysuisdk/README.txt` 与 `GITHUB_RELEASE.md` 使用同一安装语义。
- r1 Release、资产和 tag 未修改；用户完成的正常编译验收已同步到实时状态文档。

## 错误数演变

本次不修改代码，不预期改变 Gradle/Kotlin 编译错误数。发布工具新增前的 Python 工具测试基线为 361；新增 8 个 SysUISdk release focused tests 后总数为 369。用户已确认 r1 Release 可正常编译。

## 待解决

- 当前 GitHub Release body 需要在有 GitHub 写权限的环境中手工替换为仓库内 canonical release notes；本机缺少认证，无法直接 PATCH。
- r1 保持现状，不撤销、不移动既有 tag；tag 与实现提交的历史关系在发布记录中如实说明。
