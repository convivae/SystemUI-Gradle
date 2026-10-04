# 文档与现状对齐（2026-10-04）

## 背景

`git fetch` 后确认：`origin/main` 仍为 `69937f24`；本地 `main` 领先 6 个未 push
commit（host 可移植性、Kotlin androidprv 修复、parallel tooling sync、文档 ledger 调整）。
GitHub 已于 2026-10-04 发布 SysUISdk `android-17.0.0_r1-r2`，但 `CURRENT_STATE` /
`PLAN` / 双语 README 仍写「待异机发布 / 请用方式 B」，与事实不符；`docs/HANDOFF.md`
已删除。

## 操作

更新 owner 文档与对外 Quickstart，使状态、未完成项、SDK 下载路径与仓库/Release 一致。
不 push。

## 待解决问题

- 本地领先远端的 6 个 commit 是否 push：由用户决定（本机本次不 push）。
- Studio UI Sync、设备部署仍未在本机手工验收。
