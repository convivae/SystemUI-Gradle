# 2026-08-19 — :SystemUI-plugin 不挂 Compose compiler（对齐 AOSP，关闭 deferred 项）

## 结论（用户批准）

`:SystemUI-plugin`（SystemUIPluginLib）**不应用 kotlin-compose 插件**，维持现状关闭此项。

## 依据

1. AOSP `plugin/Android.bp` 的 `SystemUIPluginLib` 只声明 `plugins: ["PluginAnnotationProcessor"]`，
   无 compose compiler；SystemUI 全部 bp 均不显式声明 compose 编译器（规则 B 语义对齐）。
2. 模块内仅 1 个抽象 `@Composable`（`TileDetailsViewModel.GetContentView`），
   抽象声明无函数体，编译通过。
3. 理论 ABI 风险（基类未变换 vs core 实现类被 compose compiler 变换 → AbstractMethodError）
   在 AOSP 生产结构相同且正常运行，说明该结构在实践中成立；装机验证（待办）兜底实证。
4. 主动挂插件反而是偏离 AOSP 的 ABI 布局。

## 复查触发条件

装机/运行验证中若出现 `AbstractMethodError` 指向 composable 覆写（如
`GetContentView(Landroidx/compose/runtime/Composer;...)`），重开此项。
