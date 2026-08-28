# E3 — Task 070：5806 处 strings.xml CONV 标记的授权链与机制（D1 的直接先例）

status: done
判读: **符合**

## 背景与决策原文

AOSP-17 重对齐（C3）期间，86 个 `SystemUI-res/res-product/values*/strings.xml` 被覆为 17 字节后，
需要对所有非 default product 变体条目（`product="tv"/"tablet"/"device"/"desktop"`）重放 CONV_DEL
标记——因为 **AAPT2 不支持 `product` 属性**（Soong 才懂），多变体在 Gradle 下被当作 default 重复，
编译报 `Found item String/<name> more than one time`。

终态（commit `68df52a1`，task070 P5）：**5806 处 CONV_DEL 标记**
（desktop 3230、tablet 1717、device 773、tv 86），86 个文件，格式
`<!-- CONV_DEL BEGIN [task070] reason: product-variant unsupported by AGP --> … <!-- CONV_DEL END -->`，
被注释原行字节保留在注释内，可整体撤回；90 个 xml 全部通过 ElementTree 解析。

## 决策链

| 环节 | 证据 |
|---|---|
| 机制与标记规范的用户批准 | `docs/adr/0004-conv-markup-and-alignment-discipline.md` 抬头："已接受；2026-08-07 与用户经 grilling 对齐后确定"（含"不直接删除、原内容以注释保留、打标记"三要求） |
| 首次应用（16 时代，2237 处） | `docs/issues/2026-08-07-product-variant-conv-del.md`（19 个 string name，default 全保留，逐 name 有 default 备份的验证）；commit `4c99c1ce` "fix: apply CONV_DEL to product variants" |
| 17 重对齐的用户裁决 | `docs/orchestration/tasks/070-c3-source-realignment-execution.md` "已裁决事项（用户 2026-08-27 批准）" 第 7 条：res-product 新变体随 CONV 整批重标 |
| 执行 | commit `68df52a1`（P5）；issue `docs/issues/2026-08-27-c3-source-realignment-execution.md` §"86 个 res-product strings.xml CONV 重标" L69–75 |
| 评审 | orchestration log L286：chief 独立复验 5806 全标、0 leak、3424 个 default 条目未动、90 xml parse OK、禁改动面零 diff |

## 证据链

1. 计数分解来自 issue L72 与 commit `68df52a1` message，两处一致（3230/1717/773/86 = 5806）。
2. `--strict` 终态（issue L43/L96）：MISSING/MISPLACED/EXTRA/APP/RES-MISS/RES-EXTRA 全 0；
   MODIFIED 1（CONV_MOD 白名单 kt）+ RES-MODIFIED 86（白名单）。即对齐门视为合规。
3. 原 16 时代标记计数 2237：`git show aa77057a^` 实测（issue L73 引述：values/strings.xml
   device 8 + tablet 18 + tv 1，全树 2237）。
4. 机制正确性（为什么必须标）：首次编译失败实证（`docs/issues/2026-08-07-product-variant-conv-del.md` §背景，
   `:SystemUI-res:packageDebugResources` 报重复资源）。
5. **变体清单差异的披露**：brief 清单是 tv/tablet/desktop（漏 `device`），worker 展开为
   tv/tablet/device/desktop 并在 issue L73 显式记录理由 + 声明"已向 architect 报告，如需缩窄可机械撤销"。
6. 参考项目对照：CarSystemUIGradle 对同一问题用 **Python regex 直接删除**非 default 变体
   （`docs/GRADLE_MIGRATION.md` 引于 ADR 0004 上下文节，L395–413）；ADR 0004 明确拒绝"直接删"，
   采用可撤回的注释打标——本项目机制严于参考项目。

## 备选路径

1. **Python regex 直接删除**（参考项目做法）——违反规则 R"不丢字节"与用户对可追溯的要求，被 ADR 0004 否决。
2. **目录级排除 res-product 变体**（Gradle sourceSet exclude）——属"source exclusion 隐藏问题"，
   CHARTER Part 5.6 明令禁止；且会连 default 一起排除，不可行。
3. **AAPT2/AGP 上游支持 product 属性**——不存在（agp 9.3.1 实测包重复），N/A。
4. **所选：CONV_DEL 注释打标**——字节保全、机器可撤、人工可对账。

## 优劣分析

优点：授权链三级齐（规范 ADR 0004 用户批准 → task 级用户裁决 #7 → 执行+chief 复验）；机制可验证
（计数两源一致 + 90 xml 合法 + 对齐门 strict exit 0）；偏差（device 变体）被显式记录上报而非隐藏。
缺点：brief 变体清单与执行集有差（device），虽被披露，但执行动作先于用户逐条确认——这是 L73
"如需缩窄可机械撤销"的兜底，风险小（device 变体不标即编译必崩，依据是 16 时代既有授权方案）。

## 判读与建议

判读：**符合**。这是项目 CONV 纪律执行的模范样本，直接成为 task073 D1（config.xml 三变体）的
授权先例：同一根因（AAPT2 不支持 product 变体）、同一机制（CONV_DEL 块）、同一对账路径（issue §CONV 对账表）。

建议：维持。唯一改进建议：brief 的逐条变体清单应写"所有非 default 变体"而非枚举，避免 device 类
小偏差；本项目的实际处理（披露 + 可撤销）已足够。

## 开放问题

- 无。（device 变体是否需要用户追认——一般认为已被 brief 第 7 条"整批重标"覆盖，留用户裁决。）
</content>
