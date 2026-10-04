# Task audit01 — task072/073 决策审计（详细调查报告）

## 背景

用户认为 task072（C4a Gradle 接线，review-PASS）与 task073（C4b 编译闭环，进行中）期间所做的一批决策做得不对/未经其同意成立，要求一份**逐决策的详细调查报告**：每个决策的来龙去脉、优劣得失、证据链、备选路径（含参考项目做法）。本任务**只调研与建议，不改任何代码、不回退任何改动**。

## 调查范围（用户指定：(c) 全覆盖 + 授权流程 + 先例追溯）

### D1–D4：AOSP 镜像内容改动（CONV 类）

- **D1** `SystemUI-res/res-product/values/config.xml` 三变体（config_enableLargeScreenScreencapture）CONV_DEL，留 default（commit `02e60a60`，用户授权）
- **D2** application manifest 剥 `package="com.android.systemui"`（task072 commit `80be3e58`）
- **D3** application manifest 剥 `REPORT_UI_LATENCY_STATS` 权限的 `android:featureFlag` 属性（task073 R6 轮修复；chief brief 泛授权，未单独报用户）
- **D4** clocks-common / floatingmenu manifest **保留** package 属性（仅警告不剥，task072）

### D5–D11：产物/依赖决策

- **D5** kairos → tier① 源码模块 `:SystemUI-utils-kairos`（63 kt，task073 P0，commit `4ac49993`）——重点：16 时代判"test-only 不进生产图"与 17 bp 生产依赖的矛盾，哪个对？
- **D6** ace 拆双 AAR（visualizer = viz+common 两 Kotlin jar 合并 + client 独立；task073 P1）——重点：common jar 并入 visualizer AAR 该不该独立成第三产物
- **D7** wmshell-shared AAR 并入 AIDL 闭包 19 类 + 版本 2.0.0→2.0.1（task073 P2a）——重点：17 bp 里 `WindowManager-Shell-shared-aidls` 是独立 target，并入 AAR vs 独立 jar
- **D8** aapt2 编译期转发 `--feature-flags`（改 `tools/patch_androidprv_merged_resources.py`）+ 新产物 `libs/systemui-aconfig-flags.txt`（Soong 产物字节拷贝）——重点：自造构建通道 vs 其他路径（如 Soong 侧预处理、AGP 官方能力）
- **D9** dynamiccolors 走 Task 059 直接 AAR 例外（例外清单 +1，task072）——重点：例外机制本身 vs 本地 Maven
- **D10** mechanics×2 jar、SerialPortAccessDialog AAR（task073 P1）——常规核验
- **D11** core namespace `com.android.systemui` → `com.android.systemui.core`（task072）——重点：翻案了 16 时代 Task 050 的既定格局，merger 依是否充分、有没有别的解

### D12：生成器碰撞裁决（当前挂起）

SysUISdk 重建受阻：17 树 framework.jar 新内嵌 `android/compat/annotation/UnsupportedAppUsage{,$Container}` 两类（turbine 字节）与桥接 39 条的 unsupportedappusage.jar（javac 字节）碰撞，API 相同字节不同。三选项：①桥接去重（聚合 jar 为主源，桥接只填缝）②桥接优先覆盖 ③重准 bytes。给出专业判断与依据（ADR 0006 设计意图 + soong 侧这两类的实际消费面）。

### P1–P3：授权流程（建议同规格写文档）

- **P1** task072/073 brief 把 CONV 权限泛授权给 worker（File Map 写"必要时 SystemUI-*/src 的 CONV 标记改动"）→ 偏离 ADR 0004"res/src 改动须用户授权"的纪律（D3 即后果）
- **P2** chief 评审接受 worker 自判项（D9/D11/B4）而未先报用户——评审与升级规则（规则 H）的边界在哪
- **P3** worker 在 brief 外扩范围（ace 拆双 AAR、wmshell-shared 2.0.1 版本升位）——何时算"记录在案的合理漂移"、何时算越权

### E1–E4：16 时代先例追溯（只审被引用的，不全面翻旧账）

- **E1** Task 050：79 处 manifest FQCN 手工改写（D11 的"免掉"对象，先例本身健康的健康度）
- **E2** Task 059：直接 AAR 例外清单的原始授权范围（D9 的扩清单依据是否成立）
- **E3** Task 070：5806 处 strings.xml CONV 标记的授权链与机制（D1 的直接先例）
- **E4** 13-module → 16-module 拓扑演变（含 SystemUI-application/clocks-common 模块创建决策，用户曾追问过）

## 方法与纪律（硬性）

1. **每个结论必须有可复核的证据支撑**：AOSP bp 源码引用到文件+行号、javap/unzip/aapt2 dump 实测输出、git commit hash、scripts 代码行、"参考项目路径:行号"。无法独立验证的断言必须明确标注"未能验证"，禁止猜测性结论。
2. **每个决策独立成文**，结构统一：
   ```
   status / 背景与决策原文（引用 issue 文档与 commit）
   决策链（谁、何时、凭哪份授权）
   证据链（逐项，含命令与输出要点或文件:行号）
   备选路径（至少 2 个，含 CarSystemUIGradle 参考项目做法——该仓库在 /home/conv/myspace/CarSystemUIGradle，
     重点看其 docs/GRADLE_MIGRATION.md、DEPENDENCIES.md 与对应脚本/tooling 如何处理同类问题）
   优劣分析（结合项目规则：P/S/C/F/R/B/H/D/I、ADR 0001-0007、依赖三形态表、§3.2 libs 交付纪律）
   判读（三档：符合 / 可接受但需补记录 / 与规则冲突建议重做）→ 建议（保持/回退/重做+方向思路）
   开放问题（列给用户的裁决点）
   ```
3. **判读标准**以项目基本规则为准（不是你个人偏好）；规则之间冲突时如实指出冲突点而不是单边站队。
4. **增量保存（128K 上下文，防丢）**：每完成一个决策文档，立即 ①更新索引页状态行 ②`git add` **只加该决策文档与索引页的显式路径**，单独小 commit（英文 message）。**严禁 `git add -A`/`.`**。
5. 本任务全程**只读**项目代码与 AOSP 树；允许跑 grep/javap/unzip/aapt2 dump/git 查询等只读命令；**禁止**任何 gradle 构建、pytest、写代码文件。临时 scratch 放 `/tmp/audit01/`。
6. 若某决策调研中发现**台账外的新可疑决策**，先写进索引页"发现的额外问题"节，不展开（除非完成主清单后仍有预算）。
7. 完工后写总评：总体结论、最需要用户注意的前 N 项、建议的处置顺序。

## File Map

- 输出目录：`docs/architecture/2026-08-29-decision-audit/`
  - `index.md` — 索引页（每个决策一行：status(not-started/doing/done) + 文件名 + 一句话预结论 + 关键证据指针；顶部维护"resume 速查"段，供压缩后快速恢复现场）
  - `d01-…md` … `d12-…md`、`p01-…md` … `p03-…md`、`e01-…md` … `e04-…md`、`summary.md`
- 只读引用源：两篇 issue（c4-gradle-wiring / c4b-debug-compile-closure）、两份 brief（tasks/072、073）、commits `452c9f6c..HEAD` 及 task070 相关 commit、ADR 0001–0007、AGENTS.md、AOSP 树（`/home/conv/myspace/aosp`，只读）、参考项目（`/home/conv/myspace/CarSystemUIGradle`，只读）

## 验收

- 19 份决策文档 + index.md + summary.md 齐全，格式统一，status 全部 done。
- 抽查任一结论都能找到对应证据（文件:行号 / 命令输出 / commit hash）。
- 索引页 resume 速查段可让一个冷启动 AI 在 5 分钟内接续工作。
- 除本目录外零代码改动；git log 为小步 commit 串（每个决策 1 commit）。

## 五字段

- **Authority**: 只读调研 + 自己的文档目录写入 + 小步 docs-only commit；never push；任何代码改动一律不碰；证据缺口如实标注；用户是最终裁决人
- **Allowed Paths**: `docs/architecture/2026-08-29-decision-audit/**`、`/tmp/audit01/**`
- **Forbidden Paths**: 一切代码/res/build 文件/AGENTS.md/tools/**、git push、gradle/pytest 命令、`git add -A`/`.`
- **Acceptance**: 19 文档 + 索引 + 总评齐全，证据可复核，增量 commit 纪律全程未见 `git add -A`
- **Reports To**: chief（herdr agent `audit01`）

## 执行顺序建议（防压缩丢失的产出顺序）

E1–E4（先例基线）→ P1–P3（流程）→ D1–D4（CONV 类）→ D5–D11（产物类）→ D12（生成器裁决，放最后沉淀）→ summary.md。
每完成一个就立即 commit（见纪律 4）。

## 模型

joycode Kimi-K3-jcloud（128K 上下文）。
