# Task 068 — android-17.0.0_r1 tag 核查（Phase C 前置研究）

## Goal（ADR 0007 Phase C 前置）

用户已拍板固定到 `android-17.0.0_r1`。动 sync 大动作前，核查该 tag 的关键事实，
排除执行风险。**本任务只读研究，不做任何 sync/编译/仓库改动。**

## Authority

- 可修改：报告文件 `docs/architecture/2026-08-26-android17-tag-verification.md`；
  log.md 一行；commit（英文，本地，不 push）
- Forbidden：一切其他改动；不得动 AOSP 树；不得跑 repo sync

## 核查清单

用清华镜像 `https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest`（googlesource
直连超时已证实）。当前 AOSP 树在 `/home/conv/myspace/aosp`（main @ 2026-04-27，SDK 35
preview，lunch `sdk_phone64_x86_64-trunk_staging-userdebug`）。

1. **tag 存在性与身份**：`git ls-remote --tags <镜像> | grep android-17`，确认
   `android-17.0.0_r1` 与可能的 `-gpl` 变体；拿到 manifest commit sha
2. **tag 对应的 lunch target**：checkout 该 tag 的 manifest（浅层，或从镜像拉
   `platform/build` 在该 revision 的 `target/` 目录）确认：
   - `sdk_phone64_x86_64` 产品是否仍存在？还是改名（如 `sdk_phone64_x86_64` → 新 emulator 产品名）？
   - 对应 build variant（是否仍 `-trunk_staging-userdebug`，还是 release tag 上变成 `-userdebug`/其他）
   - PLATFORM_VERSION / SDK_INT（应为 36.x？）
   - **重点**：release tag 上 trunk_staging 通常不可用——核查该 tag 下我们脚本消费的
     隐藏产物路径是否有已知差异（framework turbine-combined、framework-res.apk 路径
     在 release 构建下是否相同）
3. **SystemUI 子树漂移量粗估**：从镜像拉 `platform/frameworks/base` 在该 tag revision
   的 commit，对比本地 `git -C /home/conv/myspace/aosp/frameworks/base rev-parse HEAD`：
   - 两个 revision 之间 `packages/SystemUI/` 的 diff 统计（`git log --oneline HEAD..<new> -- packages/SystemUI/ | wc -l`，如果本地 shallow 拿不到完整历史就 fetch 该 revision 后做 diff --stat）
   - 顺带 `frameworks/libs/systemui/`、`packages/SettingsLib/` 的漂移统计
   - 目的：给 Phase C 适配工作量一个量化预期
4. **repo sync 体量**：`repo init -b android-17.0.0_r1 && repo sync -d` 的下载量粗估
   （对比本地各 project HEAD 与 tag revision 的距离，抽查 frameworks/base、art、
   prebuilts 几个大头），确认夜间执行可行
5. **风险红旗**：任何会导致"该 tag 无法用现有 7 脚本 + build_sysuisdk 消费"的结构性
   变化（如 emulator 产品消失、framework 产物路径迁移）→ 明确列出并给降级建议
   （降级到 android-16.0.0_r4 的判定条件）

## Acceptance

- 报告含上述 5 项事实与证据（命令 + 输出摘录）
- 明确 GO / NO-GO 建议
- log.md 一行；commit 英文本地不 push

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
