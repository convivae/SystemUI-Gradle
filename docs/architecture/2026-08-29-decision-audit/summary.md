# 2026-08-29 决策审计总结（task072 / task073）

判读汇总 + 整改优先级清单。详细出处见 [index.md](index.md)。

## 判读汇总（19 项）

| 编号 | 决策 | 判读 |
|---|---|---|
| E1 | Task 050 FQCN 手工改写 79 处先例 | 可接受但需补记录 |
| E2 | Task 059 直接 AAR 例外 | 符合 |
| E3 | task070 strings.xml 5806 处批量标记 | 符合（授权链 3 级、最终用户 2026-08-16 全库授权） |
| E4 | 13→16→17 模块拓扑演进 | 符合 |
| P1 | task073 整仓类别级 CONV 记账（blanket 授权） | **与规则冲突建议重做**（过程级） |
| P2 | chief 接受 worker 自judgement 决策未上报 user | 可接受但需补记录 |
| P3 | worker 越界优化（ace 双 AAR / wmshell 2.0.1 / D8 / D3） | 可接受但需补记录 |
| D1 | config.xml 变体 CONV_DEL ×2 | 符合 |
| D2 | application manifest 剥 package 属性 | 符合 |
| D3 | manifest featureFlag 属性剥除 | 可接受但需补记录（与 P1 同源） |
| D4 | clocks / floatingmenu manifest 保留 package 属性 | 符合 |
| D5 | kairos 恢复 tier① 源码模块 | 符合（16-era 模块审计“core BP 不依赖 kairos”的事实判断当时已不成立——16 时代 b p 就已在 L540 列出，但 16 时代 workspace 无 kairos 消费者，所以无实际后果） |
| D6 | personalcontext_ace visualizer+client 双 AAR | 符合（附两条开放项） |
| D7 | wmshell-shared AIDL 并入 maven 2.0.1 | 符合 |
| D8 | aapt2 编译期转发 --feature-flags | 符合（附开放项：flags 仅含 systemui 包） |
| D9 | dynamiccolors 走 Task 059 例外（清单 +1） | 符合（例外清单字面未扩） |
| D10 | mechanics×2 jar + SerialPortAccessDialog AAR | 符合 |
| D11 | core namespace 改 com.android.systemui.core | 符合 |
| D12 | SysUISdk 生成器碰撞裁决 | **决策待定**（审计推荐选项 ①） |

汇总：符合 12、可接受但需补记录 4、与规则冲突建议重做 1（过程级，不推翻代码）、决策待定 1、推荐重构 0。

## 跨主题模式

1. **blanket 授权式 CONV**（P1, D3）：File Map 的"授权区"给整类标记开了口，违 CHARTER P5.1。
2. **chief 自决未上报**（P2）：AGENTS §3.2 例外清单 +1（dynamiccolors）、命名空间原则翻转、
   皆属 chief review-PASS 内的 self-judgement，未触发规则 H。
3. **bp static_libs 闭包 vs 1:1 soong mirror**（D6, D7）："TraceurCommon 先例"已转为惯例，
   建议以 ADR 收编。
4. **文档滞后**（E4, D5, P2）：AGENTS.md §3.1 的模块清单和 §3.2 的例外清单字面都未追
   上 practice；需一次 user 批准的红区文档同步。
5. **D2/D3/D4 manifest 命名空间处理三分法**：同类问题三种做法，建议 user 一次性裁定为统一 convention。

## 整改优先级清单（给 user / chief）

1. **P1 过程整改**：把 MODULE_FILE_MAP.md 的"授权区"语言改回点名授权；不需要代码改动。
2. **D3 追认**：由 user 明确裁定 manifest featureFlag 属性处理路径（CONV_DEL 剥除 vs
   additionalParameters 解套——16-era task009 已有先例）。
3. **D12 裁决**：批准选项 ①（生成器 slice 删除 2 条 + BRIDGE 断言 39→37 + 冻结映射
   8→7 输入 + regression test）——解锁 task073 剩余 5 个 Kotlin `e:` + 20 条 link 颜色错误。
4. **AGENTS.md §3.1/§3.2 文档同步**（user 批准后执行）：模块拓扑改判据制；§3.2 例外清单
   改写为"判据制"。
5. **一次 batch user review**：把 D2/D3/D4、P2、P3 和 D5/D9 的文档滞后项打包一次报批
   （report ≤20 行）。
6. **追踪 D8 flags 白名单覆盖**：若未来 res-product/values 引用其他 aconfig 包 flag
   （bp L429-434 还有 uilatencystats_flags / app.flags / net.platform.flags 3 个），工具需
   扩展多文件转发——当下登记为备忘。
7. **补齐 task073 formal review 记录**（orchestration log 至今无 task073 行的 review 条目），
   本项目已提交了审计产出，并请 chief 把 review judgment 记入 log.md。

## 结论

所有结构性决策都符合规则。唯一过程级要整改的是 P1 的 blanket 授权语言；P2/P3 是
典型的 chief/worker 边界开放项，一次 user batch review 即可解决。task073 下的关键下一步
是 D12 的生成器碰撞裁决（选项 ①）。

