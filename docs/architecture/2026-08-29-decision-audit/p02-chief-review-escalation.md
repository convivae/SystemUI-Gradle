# P2 — chief 评审接受 worker 自判项（D9/D11/B4）而未先报用户：评审与规则 H 升级的边界

status: done
判读: **可接受但需补记录**

## 背景与决策原文

task072 评审收口（orchestration log L304，2026-08-28）：

> worker 自主判断 4 项均 review 接受：core namespace→`com.android.systemui.core`
> （unique-namespace 硬约束 + merger 相对名展开，issue §3.1 有 merger 源码依据）；
> dynamiccolors 直接 AAR（Task 059 例外形状：单 consumer、记录在案）；
> plugin 补 `:SystemUI-compose`（17 bp 漂移）；core 16 遗留 manifest 未动（移交 task073）。

这 4 项中至少 D9（dynamiccolors 直接 AAR）与 D11（core namespace 改名）属于"多方案等价、
此前未在用户处裁决"的判断；chief 在评审环节直接接受，未见先报用户的记录。

## 决策链

| 环节 | 证据 |
|---|---|
| brief 授权口径 | task072 brief 五字段 Authority 只写 "self-commit；never push；遇规则 H 情形停下来问 chief"；未列出 namespace/直 AAR 扩清单的自判权限 |
| worker 自判 | task072 issue §3.1（namespace 方案论证）+ §2（dynamiccolors 直接 AAR 判据说明） |
| chief 评审接受 | orchestration log L304/L305（review-PASS，已 push）；未见这 4 项去用户的往返记录 |
| 用户侧回应 | 用户在派 audit01 时点名这几项须审计（本 brief D9/D11/P2 词表） |

## 证据链

1. **规则 H 的文本边界**：AGENTS.md §2.5 七项中与本案相关的是 "(5) 需要产品决策（多个等价方案）"
   与 "(6) 需要修改 AGENTS.md 的核心规则"。
   - D11：namespace 方案存在多个等价解（core 改名 / app 改名 / 改回 FQCN 改写——E1 先例），按
     (5) 字面应升级。
   - D9：把第 5 个族纳入 AGENTS.md §3.2 用户批准的例外集（该段原文"当前直接消费集为…四族"），
     触及 (6) 附近（规则文本的适用范围扩大）。
2. **反向证据（不自裁也要站得住）**：
   - D11 的论证有可复核依据：merger ENFORCE_UNIQUE_PACKAGE_NAMES（AGP 9 默认）+
     XmlAttribute 相对名展开源码（issue §3.1 引 manifest-merger 32.3.1 L87–113）+ core 无
     res/BuildConfig/R 引用的全仓 grep=0。
   - D9 的"Task 059 例外形状"判据在 worker/chief 层面可机械核查（单 artifact、单 consumer、
     骨架 POM、字节同一），与规则三形态表的 tier② "AAR 先直接引入"不矛盾。
3. **规则文本的现实漂移**：AGENTS.md §3.2 例外集至今仍是"四族"措辞（未写入 dynamiccolors/ace 等
   新族）；实际 build 文件已新增第 5、6、7 个直接 AAR（`SystemUI-res/build.gradle.kts:50`、
   `SystemUI-core/build.gradle.kts:249-250,254`）→ 规则文本与实践已不同步（这本身需要
   AGENTS.md 更新，而 AGENTS.md 编辑又属 CHARTER Part 5.3 红区）。
4. **先例对照**：E2 判定 Task 059 例外集是"判据制"而非"废止制"——按判据扩族与按清单扩族的
   法律效果不同（见 e02 开放问题）。chief 采用"判据制"解读接受了扩族。

## 备选路径

1. **评审前预升级**：chief 在接受前把 D9/D11 单项或打包一次问用户（成本：一次往返）——符合
   规则 H.(5)。(6) 字面。
2. **评审接受 + 事后批量上报 + 规则修订**：chief 先接受（防流程阻滞），随后把自判项打包成
   规则修订（如 AGENTS.md §3.2 改判据制）请用户批准——当前事实形态（L304 接受，规则文本未改）。
3. **worker 自行 REDLINE**：自判项属红区语义时 worker 直接 REDLINE——会显著拖慢编译闭环
   （namespace 一项就会卡整个 C4a）。

## 优劣分析

优点（fact 形态 = 路径 2）：C4a 不被阻塞；自判项全部进 issue §3 并可溯；chief 复验项有实质
标准（grep=0、bp 行号、merger 错误原文）。
缺点：规则 H 的升级义务在事实上被"评审吸收"代偿；规则文本未同步 → 下一个 worker 依旧读到
"四族"清单，同类问题会重复发生（D9/D6/SerialPort 都再次援引 Task 059 例外）。

## 判读与建议

判读：**可接受但需补记录**——自判项技术依据充分、全部被显式记录、没有绕行规则文本（AGENTS.md
未被私改）；缺的是"接受 → 用户知悉/规则固化"的收尾环节。

建议：
1. chief 把 task072/073 的自判项（D9、D11、B4、D6 双 AAR、D7 2.0.1、D8）打包一次上报用户，
   本审计的对应文档可直接作为材料。
2. 若用户认可判据制：修订 AGENTS.md §3.2 例外段为"判据 + 扩清单只须 issue 记录 + chief 复核"
   （红区修订需用户批准，CHARTER Part 5.3）。

## 开放问题

- 规则 H.(5) 的"产品决策"是否包含"可机械核查判据满足时的资产形态选择"？
- （与 e02 相同）AGENTS.md §3.2 例外段是否改判据制？
