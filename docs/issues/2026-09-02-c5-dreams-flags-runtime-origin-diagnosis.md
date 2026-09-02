# C5 Task 099：`android.service.dreams.Flags` runtime origin diagnosis

**日期**：2026-09-02
**状态**：ACTIVE REPAIR — 用户已取消所有超出 `AGENTS.md` 的人为编排限制；Task 099 第六个 Worker 的 Phase 1 证据已接受，现可直接诊断、修改、测试、构建、操作 Herdr/设备并 commit（push 仍由 Chief 负责）
**前置**：Task 098 已以 `DEBUG_RUNTIME_REBOOT_FAIL` 关闭；Task 096/097 的 fresh Debug/Release build/static 结论仍分别为 PASS，但不构成 runtime PASS。

## 2026-09-02 用户纠偏与当前授权

用户明确指出，固定 startup 顺序、逐字 `CONTRACT:`、只读诊断、禁止 `/tmp` 临时脚本、禁止 Worker commit/Herdr/build/device，以及因无害流程偏差自动退休 Worker，均不是项目要求，现已全部取消。当前唯一工程约束来自 `AGENTS.md` 和最终运行目标；协调层仅保留全机同一时间最多一个重型构建，以及最终 push 由 Chief 负责。

Task 099 第六个 Worker 在 `/tmp/task099-c5-dreams-flags-diagnosis/` 完成的 Phase 1 正式接受：冻结 Debug APK 中有 41 条真实 old-owner `invoke-static`，分布于 40 个方法、39 个类和 5 个 DEX；APK 不定义 old/hidden owner；39 个 caller 均不在现有 166-class allowlist；四条 frozen mappings 不含 dreams rule，而 AOSP 725-rule authority 包含。其 `/tmp` Python 脚本属于允许的诊断工具，不构成证据失效原因。

该 Worker 已重新获得完整工程权限，可继续做全 725-rule residual 扫描、健康/失败产物对比、生产修复、测试、串行 Debug/Release 构建、APK 静态验证和设备 runtime 验证，并可创建英文 commit。下文原有 “Allowed / forbidden”、startup attempts 和只读验收文字是历史任务设计，凡与本节冲突均已废止，不再具有当前约束力。

## 背景

Task 098 在冻结 Debug APK（size `190547804`，SHA-256 `f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`）部署后的 fresh Checkpoint A 中观察到持续 crash-loop。首个 fresh fatal 在 `com.android.wm.shell.keyguard.KeyguardTransitionHandler.onInit(KeyguardTransitionHandler.java:155)` 到达 `Landroid/service/dreams/Flags;`，而 authoritative AOSP rule 为：

```text
rule android.service.dreams.Flags com.android.internal.hidden_from_bootclasspath.android.service.dreams.Flags
```

Task 098 只证明一个未重写 old-owner reference 到达 runtime；它没有确定 APK 中全部 caller identities、该 caller 的 canonical program-input artifact/source provenance，或该规则为何没有进入现有四 mapping / 166 caller rewrite coverage。本任务只做该 bounded diagnosis，不修改 production pipeline。

## 诊断问题

1. 冻结 Debug APK 中 `Landroid/service/dreams/Flags;` 是否仍存在，位于哪些 DEX、由哪些 class/method instruction 实际引用？必须区分 instruction-level caller、type-table presence、definition、self-reference 与普通字符串。
2. 每个 caller 的 canonical Gradle program/runtime input 是哪个 JAR/AAR/module output？文件与内嵌 `classes.jar` 的 SHA-256 是什么？重复 intermediate 只按 class identity 计一次。
3. caller 对应的 AOSP source 与 `Android.bp` / Soong artifact provenance 是什么？不得把 framework source 复制到工程。
4. caller 是否已在 `gradle/aosp17-critical-aconfig-reference-classes.txt` 的 166-class allowlist 中？`android.service.dreams.Flags` mapping 是否存在于四条 frozen rules、full 725-rule AOSP mapping 和当前 focused tests？
5. 为什么 Tasks 080–097 的 bounded static gates 能 PASS 而 Task 098 仍失败？结论必须区分“既有四 mapping contract 内正确”与“contract coverage 不完整”，不得否定已有 PASS 的原始范围。

## Phase 1 feedback loop

诊断 worker 必须先建立并实际运行一个无需 build/device 的 deterministic static loop，输入只能是冻结 Debug APK。该 loop 必须在数秒级或合理的只读静态扫描时间内：

- 对 old descriptor `Landroid/service/dreams/Flags;` 返回 RED；
- 报告 old/hidden descriptor 的 referenced/defined 状态；
- 输出至少一个 instruction-level caller class/method，且能在后续修复后因 old instruction reference 消失而变 GREEN；
- 保存精确命令、exit code、输出和输入 APK identity 到 `/tmp/task099-c5-dreams-flags-diagnosis/`。

如果现有 `dexdump`/仓库工具不能可靠归属 instruction caller，必须停止并报告反馈 loop seam 不足；不得临时修改 production code、不得把普通字符串或孤儿 constant-pool/type-table entry冒充 instruction reference。

## 假设纪律

反馈 loop 首次 RED 后才允许列出 3–5 个有预测、可证伪的 ranked hypotheses。至少要检验以下候选，但不得预先把任何一项写成结论：

- H1：caller 已在 166 allowlist，唯一直接缺口是 frozen mapping 仅含四条、未含 dreams rule；预测是 caller allowlist membership 为 true、四-rule membership 为 false、725-rule membership 为 true。
- H2：mapping 已存在但 caller 不在 allowlist；预测与 H1 相反。
- H3：caller 或 reference 在 AGP `InstrumentationScope.ALL` 不覆盖的 input 形态中；预测是 canonical artifact 不会产生可观察的 transform output或 caller bytecode保持旧 owner，即使规则与 allowlist都存在。
- H4：DEX type-table 命中并非实际 instruction caller；预测是反汇编找不到相应 field/method/type instruction，Task 098 stack只能由另一个 identity解释。

每个假设必须以独立证据接受或排除；不得通过修改 mapping/allowlist或重建 APK来试验。

## Allowed / forbidden

允许：只读检查冻结 APK、现有 Gradle intermediates、现有 JAR/AAR、build logic、frozen rules/allowlist、AOSP source/`Android.bp`/Soong outputs及 Task 080–098 durable/scratch evidence；在唯一 scratch root 写诊断证据；只更新本文档的诊断结果。

禁止：修改 production source/build logic/rules/allowlist/tests/SDK/`libs/**`/AOSP；运行 Gradle、Soong、Ninja、JarJar、R8/D8、emulator、ADB 或 Herdr control；重建或替换 APK；修复；Task 079 broad replay；新增脚本；commit/push。

所有 Python 调用必须使用 `uv run python`。不得直接使用 `python`/`python3`、`pip`、`uv pip`。

## 验收

最终报告必须同时给出：

- feedback-loop 精确命令、exit、RED output 和 APK size/SHA；
- 所有 instruction-level caller identities 与 method/offset（若工具能给出）、DEX entry；
- canonical artifact/class SHA 及 AOSP source/Soong provenance；
- old/hidden referenced/defined counts；
- caller 对 166 allowlist 的 membership、dreams rule 对四-rule/full-rule 的 membership；
- 3–5 个 hypotheses 的逐项证据和 verdict；
- 单一最小根因陈述，以及下一 production-fix task 的最小建议范围与必须新增的 regression/static gates；
- 明确声明未 build、未修复、未操作设备，Debug/Release runtime 均未因此变为 PASS。

## Startup attempts（均无技术 authority）

在开始任何 preflight 或诊断前，Chief 已 fail-closed 退休四个 attempt；它们只形成流程记录，任何读取内容、推测或 malformed CONTRACT 均不得作为 Task 099 技术证据：

- `task099-dreams`（`w2:t4C` / `w2:p4H`）：CONTRACT 未逐字复现冻结 six-field authority，擅自扩大 `tools/**` writable scope并预判 coverage 结论。
- `task099-dreams-r2`（`w2:t4D` / `w2:p4J`）：在唯一冻结 log-tail read 后额外探测 line 715，并在 mandatory source 13 后因 compaction 重读 brief。
- `task099-dreams-r3`（`w2:t4E` / `w2:p4K`）：完成 source continuation，但未输出冻结的 exact six-field CONTRACT。
- `task099-dreams-r4`（`w2:t4F` / `w2:p4M`）：`docs/orchestration/STATE.md` 在 line 176/514 截断后未以 offset 177 续读即继续后续 sources；Chief 在其唯一响应前退休。

四次 session 均独立记录 `joycode/GLM-5.3`、`thinking=high`。它们没有运行 preflight、static RED loop、Gradle/Soong/Ninja/D8/R8/JarJar、emulator/ADB、build、production fix、commit 或 push，也没有 tracked change；Task 099 诊断仍未开始。

## 构建与错误数记录

规划阶段未运行 Gradle、Soong、Ninja、测试或设备命令。当前 runtime blocker 仍是 Task 098 的 622 个 fresh fatal/NCDFE；本任务不以编译错误数为门槛。

## 待解决

- 独立 worker 完成只读诊断并由 Chief 验收。
- 诊断闭包 commit/push 后，另建 production-fix task；不得在本任务内直接扩 mapping/allowlist。
