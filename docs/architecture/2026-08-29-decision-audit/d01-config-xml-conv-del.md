# D1 — `res-product/values/config.xml` 三变体（config_enableLargeScreenScreencapture）CONV_DEL

status: done
判读: **符合**

## 背景与决策原文

AOSP-17 新增 `config_enableLargeScreenScreencapture`，在 `SystemUI-res/res-product/values/config.xml`
以 `product="default"|"tablet"|"desktop"` 三重声明出现。Soong 按产品形态选择变体；**AAPT2 不理解
product 属性**，把三变体视为同名重复定义，`packageDebugResources` 失败（task073 编译 R2 轮的
实际阻塞：见 `docs/issues/2026-08-28-c4b-debug-compile-closure.md` §4 错误数表 R2 行）。

决策（commit `02e60a60`，2026-08-28）：保留 `product="default"` 一行，tablet/desktop 两行用
两个 CONV_DEL BEGIN/END 注释块包裹（**字节保全、可整体撤回**，机制同 task070 strings.xml）：

```
<!-- CONV_DEL BEGIN [task073] reason: product-variant unsupported by AGP; user-authorized 2026-08-28; keep default only -->
<!-- <bool name="config_enableLargeScreenScreencapture" product="tablet">false</bool> -->
<!-- CONV_DEL END -->
```

## 决策链

| 环节 | 证据 |
|---|---|
| 已知挂账 | task070 C3 handover（`docs/issues/2026-08-27-c3-source-realignment-execution.md` L89）："res-product/values/config.xml 的 3 个 bool product 变体未标 CONV（既有状态），C4 若遇重复资源错误需处理" |
| 错误实证 | task073 R2：`packageDebugResources` 报 res-product bool product-variant 重复（issue §4 表 R2 行） |
| 用户授权 | commit `02e60a60` message："user-authorized 2026-08-28 (via chief)"；issue §6 CONV 对账表同记 |
| 执行 | commit `02e60a60`（6 insertions/2 deletions，机械可复核） |

## 证据链

1. **改动内容机械核对**：`git show 02e60a60` — 仅 8 行差异；两行 tablet/desktop 被注释包裹，
   default 行保留；文件无其他区段改动。
2. **机制必要性的根因**：同 E3/E1 的 AAPT2 product 变体局限；首见于 2026-08-07 issue 的编译失败
   （`Found item String/inattentive_sleep_warning_message more than one time`）。
3. **工具状态**：commit message 记录 `check_source_alignment.py --strict` exit 0；
   RES-MODIFIED 计数 86→87（该文件计入白名单）——issue §5 对齐行同记（RES-MODIFIED 87 =
   task070 5806 + 本 1 处）。
4. **语义后果明示**：default=false 被保留，desktop=true 变体被注释——Gradle 产物在 desktop
   形态下会取 false，这是 AAPT2 单变体限制的**固有代价**，与 16 时代 strings 变体标记相同；
   因 AAPT2 本来就无法选变体，注解掉非 default 变体是唯一能过编译的分支（否则编译失败）。
5. **先例一致性**：与 task070 5806 处标记完全同构（同一 reason 文本格式、同一机制、同一对账路径）。

## 备选路径

1. **不打标直接删**（参考项目 regex 删除模式）——违反规则 R/ADR 0004（不丢字节、可回撤）。
2. **保留三变体 + 等 AGP/AAPT2 支持**——编译即失败，永远阻塞。
3. **product-aware 资源分流**（Gradle 变体/flavor 自建）——等于重发明 AOSP systemui-product
   体系，超出本工程的目标。
4. 所选：CONV_DEL 打标 + default 保留（与 E3 一致的既有授权方案延伸）。

## 优劣分析

优点：授权链完整（已知挂账 → 错误实证 → 用户授权 → 执行 → 对齐门记录）；机制可逆；
后果昭示（语义差异 = AAPT2 限制固有）。缺点：desktop 形态的功能差异（large-screen capture
开关）在 build 产物中丢失——但除承接该限制外无替代（见备选 2 的不可能性）。

## 判读与建议

判读：**符合**——授权、机制、对账、先例四项齐全；这是 ADR 0004 设计意图的正面实现。

建议：**保持**；与 E3 一起作为"product 变体打标"的制度化流程固化。

## 开放问题

- 无。
</content>
