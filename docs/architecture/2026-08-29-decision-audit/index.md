# task072/073 决策审计 — 索引（audit01）

> 任务 brief: `docs/orchestration/tasks/audit01-decision-audit.md`
> 只读调研；不改任何代码。本目录是唯一输出。
> 判读三档：符合 / 可接受但需补记录 / 与规则冲突建议重做。

## Resume 速查（冷启动 5 分钟恢复）

1. **先读本文件**（本页）→ 看状态表找到下一个 `not-started`/`doing` 行 → 直接做那一项。
2. 关键背景源（只读引用源，全部已确认存在）：
   - 两篇 issue：`docs/issues/2026-08-28-c4-gradle-wiring.md`（task072）、`docs/issues/2026-08-28-c4b-debug-compile-closure.md`（task073）
   - 两份 brief：`docs/orchestration/tasks/072-c4-gradle-wiring.md`、`docs/orchestration/tasks/073-c4b-debug-compile-closure.md`
   - commit 范围：`git log --oneline 452c9f6c..HEAD`；task070 相关：`git log --grep task070 --oneline`
   - ADR：`docs/adr/`；规则：`AGENTS.md`；AOSP 树：`/home/conv/myspace/aosp`（只读）
   - 参考项目：`/home/conv/myspace/CarSystemUIGradle`（重点 `docs/GRADLE_MIGRATION.md`、`docs/DEPENDENCIES.md`）
3. **每完成一个决策文档**：
   - 更新本页对应行 status → done + 一句话预结论；
   - `git add docs/architecture/2026-08-29-decision-audit/<doc>.md docs/architecture/2026-08-29-decision-audit/index.md`（**显式路径**，禁止 `git add -A`/`git add .`）；
   - 小步英文 commit（如 `audit01: audit doc for D2 (manifest package attr strip)`）。
4. 进度跟踪：已完成 = `1/19` 中的数字见状态表 done 计数。
5. 临时 scratch 目录：`/tmp/audit01/`（命令输出留存，可删）。
6. 若遇新可疑决策 → 写入下方"发现的额外问题"节，不展开。

## 状态表

| # | 决策 | 文档 | status | 一句话预结论 | 关键证据指针 |
|---|------|------|--------|--------------|--------------|
| D1 | res-product config.xml 三变体 CONV_DEL（用户授权 commit 02e60a60） | d01-config-xml-conv-del.md | done | 符合（挂账→错误实证→用户授权→执行→对齐门，ADR 0004 正面案例） | commit 02e60a60；task070 L89；issue §6 |
| D2 | application manifest 剥 package 属性（task072 80be3e58） | d02-manifest-package-strip.md | done | 符合（点名授权+语义恒等+可逆；仅警告场景下剥除属可逆清理） | manifest CONV_DEL 块 L22-28；brief 事实#3；issue §3.3 |
| D3 | application manifest 剥 featureFlag 属性（泛授权，未单独报 user） | d03-manifest-featureflag-strip.md | done | 可接受但需补记录（改动建证充分可逆；但弃用 16-era additionalParameters 先例未记理由+授权链停在泛授权） | manifest:431-443；task009 8ab860e9；aapt2.go:107,305 |
| D4 | clocks-common/floatingmenu manifest 保留 package 属性 | d04-manifest-package-keep.md | done | 符合（不扩授权、零字节差；仅警告代价；与 D2/D3 口径差异待全局裁定） | git log=bdf2dba5 only；两 build.kts 注释 |
| D5 | kairos → tier① 源码模块 :SystemUI-utils-kairos | d05-kairos-source-module.md | done | 符合（17 bp:569 实证生产依赖；且 git 复核证16 vintage bp 已依赖—16-era 判 test-only 为事实性误判但当时无损；AGENTS §3.1 注释滞后） | 17 bp L476/569；16 bp b110a8e0:540；dec85d64 对比；4ac49993 |
| D6 | ace 拆双 AAR（common jar 并入 visualizer） | d06-ace-dual-aar.md | done | 符合（单 AAR 单 namespace + 简洁 settle 判据全部具 bp/字节证据；KSP/EmbeddedScrollEvent 未验证记开放） | e6c59677；SPEC L386-423；AAR manifest/res 实测 |
| D7 | wmshell-shared AAR 并入 AIDL 闭包 19 类，2.0.0→2.0.1 | d07-wmshell-shared-aidls.md | done | 符合（bp static_libs 闭包语义原位保持；§3.2.4 升版义务履行；TraceurCommon 先例） | bp L33-51；AAR 双副本字节同一；SPEC L141-160 |
| D8 | aapt2 编译期转发 --feature-flags + systemui-aconfig-flags.txt | d08-aapt2-feature-flags.md | not-started | | task073 issue §4 批次2；commit 6e66a0ea |
| D9 | dynamiccolors 走 Task 059 直接 AAR 例外（清单 +1） | d09-dynamiccolors-direct-aar.md | done | 符合（E2 判据满足；例外清单未扩字面） | 452c9f6c；SPEC:373-385；build:50 |
| D10 | mechanics×2 jar + SerialPortAccessDialog AAR | d10-mechanics-serialport.md | done | 符合（res 有无决定 jar/AAR；SerialPort manifest 合并必须 AAR） | e6c59677；jon bp L555/559；unzip 190/23 类 |
| D11 | core namespace com.android.systemui → com.android.systemui.core | d11-core-namespace-rename.md | done | 符合（唯一保持 manifest 字节原值的解；merger 唯一机制证据源码级复核） | merger 32.3.1 XmlAttribute/ManifestMerger2；grep=0；d1352d5d |
| D12 | 生成器碰撞裁决（UnsupportedAppUsage turbine vs javac 字节）——当前挂起 | d12-sysuisdk-bridge-collision.md | not-started | | task073 issue §4 剩余阻塞 1 |
| P1 | task072/073 brief 把 CONV 权限泛授权给 worker | p01-conv-blanket-authorization.md | done | 与规则冲突建议重做（授权结构纠正：D3 补用户追认；今后点名授权） | ADR 0004 决策7；AGENTS §1.8；CHARTER P5.1；task073 issue §6 |
| P2 | chief 评审接受 worker 自判项未先报用户 | p02-chief-review-escalation.md | done | 可接受但需补记录（自判项依据充分但缺用户知悉收尾；建议批量上报+AGENTS 判据制修订） | log L304；AGENTS §2.5/§3.2；build.kts:50/249-254 |
| P3 | worker brief 外扩范围（ace 双 AAR、wmshell 2.0.1） | p03-worker-scope-drift.md | done | 可接受但需补记录（D6/D7 合理漂移；D8/D3 边界薄分别专审） | brief 073 P2 误差循环；e6c59677/74b88acb；AGENTS §3.2.4 |
| E1 | Task 050：79 处 manifest FQCN 手工改写先例 | e01-task050-fqcn-rewrites.md | done | 可接受但需补记录（授权链完整；缺 CONV 标记+merge commit 标题失真） | commits baf5c25d/2cb578be；brief 050 §A.5；orchestration log L236 |
| E2 | Task 059：直接 AAR 例外清单原始授权范围 | e02-task059-direct-aar-exception.md | done | 符合（用户明示裁定+字节中性 A/B 证明；判据与清单双写造成扩清单模糊） | AGENTS.md §3.2；issue 2026-08-25；log L256/259 |
| E3 | Task 070：5806 处 strings.xml CONV 标记授权链 | e03-task070-strings-conv.md | done | 符合（三级授权链：ADR 0004 grilling→brief 已裁决#7→68df52a1 执行；device 变体遗漏已披露） | task070 issue；commit 68df52a1；log L286 |
| E4 | 13-module → 16-module 拓扑演变 | e04-module-topology-evolution.md | done | 符合（每步预研+用户裁决+ADR 0003 seam 判据一致；§3.1 文档滞后于 settings 17 includes） | module-audit §一；panorama §5；task070 裁决#1/2/5；commits 828923fb/bdf2dba5/d1352d5d |

## 发现的额外问题（台账外）

（空 — 主清单调研中如发现再填）

## 总评

见 `summary.md`（最后写）。

## 完成验收笔记

- [ ] 19 决策文档 + index + summary 齐全，status 全 done
- [ ] 抽查结论可回溯证据（文件:行号 / 命令输出 / commit hash）
- [ ] 本目录外零代码改动；小步 commit 串
</content>
