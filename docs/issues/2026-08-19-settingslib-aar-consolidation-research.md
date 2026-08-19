# 2026-08-19 — SettingsLib AAR 数量整合调研（Task 016）

## 背景

- Task 014 调研确认：完整闭包 33 个 res-owning target，推荐方案 C（30 个 per-target AAR）。
- 用户决策：采用方案 B（POM 传递依赖，ADR 0005），但**认为 30 个新 AAR 过多**，
  要求先调研合规的降数量方案，再定实施粒度。

## 调研问题

1. **最小无冲突分组**：33 个 res target 最少可分成几组、组内 0 重复相对路径？
   给出确切组数与分组清单（算法 + 验证）。
2. **R namespace 塌缩的运行期实证**：SystemUI 源码实际使用哪些
   `com.android.settingslib.*` 类？这些类引用哪些子包 R？namespace 塌缩后哪些类会真炸？
   参考项目塌缩运行的证据强度如何？
3. **可达性最小集**：从 SystemUI res/manifest/src 出发静态解析资源引用闭包，
   链接 + 运行实际需要多少个子 target？
4. **AGP 官方机制**：AAR 是否单 namespace？library R 类生成机制？
   R.txt-only AAR 能否为无 res 的 namespace 生成正确 R？
5. **综合方案**：给出若干 <30 的具体方案（数量/分组/合规性/风险/回滚）+ 一个推荐。

## 约束

只读调研；允许路径仅调研输出文档与本 issue；不修改任何代码/构建/资源文件。

## 结果

待填。
