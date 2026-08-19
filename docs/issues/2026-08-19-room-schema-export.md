# 2026-08-19 — Room schema 导出（Task 020）

## 背景

Deferred Follow-up 之一。AOSP `SystemUI/Android.bp` 对 SystemUI-core 设
`-Aroom.schemaLocation=frameworks/base/packages/SystemUI/schemas`，并入库 5 个
`CommunalDatabase` v1–v5 的 schema JSON。本项目 Room 走 KSP 但未配 schemaLocation，
无 schemas 目录。

意义（已向用户说明并获理解）：schema JSON 是数据库各版本表结构快照，Room 编译期据此
校验迁移链；没有它，将来 DB v6+ 若用 AutoMigration 会直接编译失败，且结构演进无审计。

用户 2026-08-19 批准实施。

## 关键事实（architect 勘察）

- AOSP schemas 位于 `packages/SystemUI/schemas/com.android.systemui.communal.data.db.CommunalDatabase/{1..5}.json`；
- AOSP `asset_dirs: ["schemas"]` 属于 `SystemUI-tests-base`（测试模块），**不在生产 APK**，
  故本项目无需 assets 接线（未构建测试模块）；
- 导出目标定为仓库根 `schemas/`（镜像 AOSP SystemUI 包根）；
- 构建后 Room 重导出 `5.json`，Room 版本差异可能造成格式 diff，以结构对比为准。

## 结果

待填。
