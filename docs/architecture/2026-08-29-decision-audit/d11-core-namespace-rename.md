# D11 — `:SystemUI-core` namespace `com.android.systemui` → `com.android.systemui.core`（task072 P1，commit `d1352d5d`）

status: done
判读: **符合**（机制证据经本审计在 merger 32.3.1 源码级独立复核）

## 背景

17 起完整 manifest 归 `:SystemUI-application`（AOSP 顶层 manifest，组件名**全部相对名**，
如 `.application.impl.SystemUIApplicationImpl`）。merger 对 package-dependent 属性把相对名
展开为 `<document namespace>.X`。要让展开结果等于 `com.android.systemui.application.impl.
SystemUIApplicationImpl`（该类在 `:SystemUI-core`，实测存在：
`SystemUI-core/src/com/android/systemui/application/impl/SystemUIApplicationImpl.java`），
`:SystemUI-application` 的 namespace 必须 = `com.android.systemui`。

但 16 时代 `:SystemUI-core` 的 namespace 就是 `com.android.systemui`。merger 的
unique-namespace 检查（strict 模式 ERROR）禁止同一合并闭包内的两个模块共享 namespace。

## 决策

| 模块 | namespace | 说明 |
|---|---|---|
| `:SystemUI-application` | `com.android.systemui` | = AOSP manifest package，承担相对名展开 |
| `:SystemUI-core` | `com.android.systemui.core` | Gradle-only 标签；不承载 AOSP 语义 |
| `:app` | `com.android.systemui.app` | 维持 Task 050 结论不变 |

## 证据链

1. **merger 相对名展开（源码级复核）**：manifest-merger 32.3.1 sources jar
   `XmlAttribute.checkAndExpandPlaceHolder()`（对应 issue 引用的 L87-113 区域）：
   `isPackageDependent()` 且值以 `.` 开头 → `pkg + value`（渐同代码位置即上文 grep 输出 L87-124）。
2. **unique-namespace 检查（源码级复核）**：`ManifestMerger2.checkUniqueNamespaces()` +
   `getNonUniqueNamespaceSeverity()` —— strictMode 时 repeatedNamespaceMessage 为 ERROR
   （函数体已逐项阅读）。
3. **core 无 namespace 消费**：`grep -rn "BuildConfig" SystemUI-core/src` = 0 命中；
   `grep "com.android.systemui.R"` = 0 命中（本审计复核，与 issue 记录一致）；
   core 无 res（res 全归 `:SystemUI-res`）；core manifest 无组件相对名。
4. **17 bp**：`SystemUI-core` 的 android_library 无 manifest/package 声明（bp 中无
   `manifest:` 行，manifest 归 `SystemUI-application`），即 soong 侧 core 本无 package 语义。
5. **app 的 16 时代命名空间约束**维持Task 050（`:app` namespace = `com.android.systemui.app`，
   applicationId = `com.android.systemui`）。

## 备选路径

| 路径 | 结论 |
|------|------|
| app/application 改名 + FQCN 改写全部组件名（= 16 时代 E1 的 79 处手工改写方案） | 17 manifest 条目更多、E1 已被记为“不健康先例”；工作量+回归风险大；issue §3.1 已否决 |
| gradle property 放开 unique-namespace 检查（非 strict → 警告） | 仅把 ERROR 变 WARNING，R/BuildConfig 冲突风险仍在；AGP 未来版本愈来愈严；否决 |
| application 改名到 com.android.systemui.application | FQCN 展开错（相对名依赖 namespace），且与 bp "manifest package = com.android.systemui" 语义背离；否决 |
| **core 改名（所选）** | core 侧无 AOSP 语义负载，变更面仅限 build.gradle.kts 一行 |

## 优劣分析

优点：merger 展开按构造正确，无需任何 manifest 手工改写；core 侧消费面 0 命中，
风险面可控；17 bp 结构自然适配（SystemUI-application 本就是 manifest owner）。
缺点：翻转了 16 时代 Task 050 格局（当时是 `:app` rename + FQCN rewrite）；对后续读
16 时代文档的读者需要解释（已在 issue §3.1 详记，d02 的 manifest strip 亦在此背景下）。

## 判读与建议

判读：**符合**——是唯一保持 17 manifest 原字节不动的解；两条机制证据均已源码级复核。

建议：**保持**；E1（Task 050 FQCN rewrite）作为历史先例保持冻结，不回溯。

## 开放问题

- 无（与 D2 的 manifest package 属性剥除构成同一命名空间议题的两半，见 d02）。
</content>
