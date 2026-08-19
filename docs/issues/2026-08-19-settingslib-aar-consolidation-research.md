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

结论文档：`docs/architecture/2026-08-19-settingslib-aar-consolidation-research.md`（详见该文档；要点如下）。

1. **最小无冲突分组：k = 12**（DSATUR 精确分支定界 + 12-clique 最优性证明，clique 经
   `values/styles.xml` 两两冲突）。放松变体（同名 values XML 条目不相交合并）**不能降到
   12 以下**：clique 成员的 styles 条目互相重叠，条目级合并需改写字节，违反规则 R。
   约束版（保 main/Color/SettingsTheme/AdaptiveIcon 四 namespace 独立）仍为 12 组。
2. **Namespace 塌缩实证**：SystemUI 直接使用 74 个 settingslib 类（69 个来自 main target）；
   塌缩后有 **39 个类带死 R 引用（dormant time bomb），但 0 个可从 SystemUI 到达**。
   `SideFpsOverlayViewModel.kt:194` 直接引用 `color.R`，故 color namespace 必须保活。
   参考项目单 AAR 运行是存在性证明，但使用面更小更不同，仅作支持性证据。
3. **可达性最小集**：代码级需 6 个 target；AAPT2 链接闭包（链接看的是 shipped AAR 的
   **完整 res 树**）迭代到不动点后为 **10 个 target = 7 个新 AAR**（760/1512 文件），
   闭包内 0 未解析引用；其余 28 个外部引用由 androidx.preference/material 官方依赖满足。
4. **AGP 机制**（gradle-9.3.1.jar 字节码实证）：AAR 单 namespace；依赖的编译期 R 类由
   `AarToClassTransform.generateRClassJarFromRTxt` 从 **R.txt + manifest package** 生成
   （解释了 SystemUI-core compile R.jar 只含自身 R 之谜）；app link 时
   `SymbolTable.withValuesFrom` 过滤 merged table 中不存在的符号 → R.txt-only AAR
   编译通过但链接期被丢弃 → 运行期 NoSuchFieldError（中等置信度，参数接线未完全追踪）。
5. **推荐：B2（可达性驱动）** — 保留现有 main/Color/SettingsTheme 三个 AAR，新增 **7 个
   per-target AAR**（SelectorWithWidget 92 / RestrictedLockUtils 87 / ActionButtons 15 /
   ProgressBar 10 / TwoTarget 7 / LayoutPreference 6 / AdaptiveIcon 3），经 ADR 0005 POM
   传递依赖接线。新 AAR 数 7（对比基线 30，降 77%）；全部失败模式编译期可见（fail-fast）；
   备选 B1′（12 合并 AAR）如需全类覆盖。灰区 k=1 与 B3（R.txt-only）均被否决。

分析脚本与 JSON 工件均在 /tmp（未入仓库），结论文档附录列出复算路径。
