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

## 结果（2026-08-19 实施）

### 1. 前置发现：Room 2.8.4 + KSP2 下 `room.schemaLocation` 单独不生效

仅传 `arg("room.schemaLocation", ...)` 时 KSP 构建成功但**不导出 schema 也无警告**。
反编译 `room-compiler-2.8.4.jar`（`Context$ProcessorOptions` / `DatabaseProcessingStep`）确认：

- 处理器选项有三个：`room.schemaLocation`（OPTION_SCHEMA_FOLDER）、
  `room.internal.schemaInput`（INTERNAL_SCHEMA_INPUT_FOLDER）、
  `room.internal.schemaOutput`（INTERNAL_SCHEMA_OUTPUT_FOLDER）；
- 导出条件是 `schemaInFolderPath != null && schemaOutFolderPath != null`
  （`DatabaseProcessingStep` bytecode 1038–1045），而 schemaIn **只来自**
  `room.internal.schemaInput`——正常由 Room Gradle Plugin（id `androidx.room`）设置；
- `Database.exportSchema(in, out)` 先读 in 下现有 `<db>/<version>.json`，
  `isSchemaEqual` 则**跳过写入**（结构不变不动文件）。

未引入 Room Gradle Plugin（需动 `libs.versions.toml`/`settings.gradle.kts`，
属 CHARTER Part 5.4 红线且超出本 brief 允许路径），改为在 `ksp {}` 同时传
`room.schemaLocation` 与 `room.internal.schemaInput`，均指向仓库根 `schemas/`。
代价：`room.internal.*` 是 Room 内部参数，升级 Room 时需复核（已在 build 文件注释）。

### 2. schemas/ 复制（byte-exact）

来源 `aosp/frameworks/base/packages/SystemUI/schemas/com.android.systemui.communal.data.db.CommunalDatabase/`：

| 文件 | SHA-256（项目 = AOSP） |
|------|------------------------|
| 1.json | `12343af8edbef5b7de48b3da29a1f9361c47d0126640170b322720c7e2780161` |
| 2.json | `e282295ac5e23f39e33704ff305a3ea42b94c2f09c26f5f81488afac6f8c74ed` |
| 3.json | `5733222974b82a7720e973e97a8284ecfb6a16df94c0a4bbf769752b552dfb51` |
| 4.json | `6921f00836b7daece81c0ce8cfdbe641ba2be98d2ef89e75a0c64d37d0f9a9cc` |
| 5.json | `c82f260a287c1707fec1f944c255b719b155d269d887ac38c201043aba34d466` |

### 3. 构建后 5.json 对比结论

- 正向证据（导出机制确实运行）：临时把两个参数指向 /tmp 目录（只留 1–4.json），
  `kspDebugKotlin` 后 Room 在该目录生成 5.json，**与 AOSP 5.json byte-identical**
  （SHA-256 同为 `c82f260a...`，2901 bytes）——无需 jq 结构对比，字节级一致；
  jq 对 entities/indices 抽取对比亦 STRUCTURE-IDENTICAL。
- 仓库内正式配置（指向根 `schemas/`）：Room 读取现有 AOSP 5.json，`isSchemaEqual`
  判定结构一致 → 按设计跳过重写，文件保持 AOSP byte-exact（mtime/SHA 不变）。
  即“构建重导出的 5.json 与 AOSP 版有 diff 需保留 Room 版”的情形**未发生**。

### 4. 构建与测试

- `./gradlew :SystemUI-core:kspDebugKotlin --rerun-tasks` → BUILD SUCCESSFUL（88 tasks executed）
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` → Ran 148 tests, OK（148 基线维持）
- 未接 asset_dirs（Non-goal）：AOSP 中 schemas 只进 SystemUI-tests-base 测试模块 assets，
  本项目未构建测试模块，无需接线

### 5. 遗留

- 若将来升级 Room 或引入官方 Room Gradle Plugin，应移除 `room.internal.schemaInput`
  内部参数改为 `room { schemaDirectory(...) }`（需用户批准动版本矩阵）。
- DB v6+ 需要 AutoMigration 时，schema 历史链已就绪（1–5.json 在仓）。

## 后续：官方插件迁移（Task 022）

Task 020 用手写 `room.internal.schemaInput` 解决导出（Room 2.8.4 + KSP2 下
`room.schemaLocation` 单独不生效的机制发现）。用户 2026-08-19 批准迁移到官方
Room Gradle Plugin（`alias(libs.plugins.androidx.room)` +
`room { schemaDirectory(...) }`），删除内部参数；catalog 管理版本，不动 settings。
