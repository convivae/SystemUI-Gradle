# C5 Task 099：`android.service.dreams.Flags` runtime origin diagnosis

**日期**：2026-09-02 → 2026-09-03（修复完成）
**状态**：REPAIR COMPLETE — Debug 与 Release 均已通过 instruction-level 静态门与设备 runtime/reboot 门，等待 Chief 验收与 push（commits `ed40e4b4`、`ea9b2f52`，未 push）
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

## 修复完成记录（2026-09-03）

### 根因（经全量扫描与 A/B 实验确证）

冻结 Debug APK 的 crash 并非单一 dreams 规则缺失，而是**覆盖率双重缺口**叠加：现有生产缝只有 4 条手写 mapping + 166-class caller allowlist，面对 AOSP authoritative 725-rule repackaging 集与任意第三方/生成 caller，任何不重叠的（rule, caller）组合都漏改写。Phase B 全量扫描：Debug 460 条未解析 old-owner ref（26 个 old 类）、Release 446 条（25 个类）；Task 098 runtime crash 的 `KeyguardTransitionHandler`（WindowManager-Shell jar）只是第一个到达 runtime 的 caller。「旧构建健康」的前提已经 A/B 实验证伪（old-healthy premise falsified），当前 crash 就是覆盖不完整。

### 生产修复设计（两轮，第二轮由 Chief 裁决）

1. **第一轮**：完整 725-rule frozen inputs（`gradle/aosp17-aconfig-repackaging-rules.txt`，与 AOSP `repackaging.txt` SHA 钉死，漂移 fail-closed）+ 废弃 166 allowlist + 仪器除 mapping source/target 外的所有类。Debug 重建后静态门：unresolved 460→0（crash 类 ref 全部改写），但 gate 仍 RED——**946 条残存 old-owner ref 全部来自 D8 在 dex 阶段（ASM transform 之后）从被跳过的 source 类（如 `CustomFeatureFlags`）未被改写的 `invokedynamic` BootstrapMethods method handle 合成的 `$$ExternalSyntheticLambda*` 类**（56 个 in `android.content.pm` + 4 个 in `android.app.smartspace.flags`，经 `javap -v` on `libs/systemui-aconfig-flags.jar` 证实）。跳过任何 source 类都会在 D8 lambda 合成路径漏出 old name，说明「跳过 mapping source」与「门要求所有 caller 改写完整」在设计上不可调和。
2. **第二轮（生效，经 Chief 确认）**：**仪器所有类**。reference-only visitor 保持 this_class 与自身引用不变，把所有向外引用（含 BootstrapMethods method handle）全部改写为 hidden twin；每个 old-name 类在 APK 中成为自洽 dead shell，D8 从改写后 handle 合成的 lambda 类天然 hidden-referencing。hidden platform definition 仍是唯一非法输入，visitor 在 AGP factory 路径与 byte-level 路径都 fail-closed。门简化为：FAIL 于任何 caller != referenced old class 的 executable old-owner ref（self-reference 是唯一允许残留，解析到 APK 自身 dead-shell）；FAIL 于任何 hidden-target definition。

### 验证结果

- **buildSrc 测试**：11/11 绿（新增 D8-lambda BootstrapMethods 改写回归、hidden-input fail-closed、mappings-only seam 结构断言）。
- **tools 测试**：362 passed + 151 subtests（33 个 gate 测试，全合成 DexBuilder 覆盖 code item/catch handler/static values/多 dex）。
- **静态门（新 APK，instrument-everything）**：
  - Debug SHA-256 `33e073195e6c5cfff61274e779927e1026571c805ef4b17ef2a8b50477c7ed65`（200,506,573 B）：13 dex，94,888 类，10,329,466 instruction refs；old-owner ref 3,571 条全部 = 自身引用残留（52 个 dead-shell 唯一对，如 `CustomFeatureFlags → CustomFeatureFlags`，解析到 APK 自身死定义）；**VIOLATIONS=0**；hidden-target ref 965（预期改写产物）；hidden definition 0；**RESULT=PASS**。
  - Release SHA-256 `17358f4d73cee462eba515ae68519c14e28a61637acc63c84cfe7ada76e6fd7e`（45,030,130 B）：2 dex；old-owner ref 0（R8 将 dead shell 全部删除）；hidden ref 449；hidden definition 0；**RESULT=PASS**。
- **设备 runtime（emulator-5554，Task 098 r4 保留基线）**：
  - 部署前基线(`f3af35d9…`)：`android.service.dreams.Flags` NCDFE crash-loop 确活，crash buffer 113,911 行。
  - **Debug**：staged SHA + atomic mv 部署 → 冷启动后仅剩已知 `BLUETOOTH_CONNECT` SecurityException（Task 098 r4 预授予未延续到本次部署，re-grant 后立即恢复；随后 Release 替换中同一授予反而存活，重置诱因未隔离，Chief 指示不再深挖；观察点：授予可跨 reboot 存活，但在某些 APK 文件替换 + 冷启动组合下被重置）；grant 后 PID 5664 稳定、crash 全停；**全机 reboot gate PASS**：boot `8cbb9aa0-daad-41dc-b8db-ba5178d8cd4b`，设备 SHA = host SHA，PID 848 稳定 90s×6 采样 0 crash，grant 存活，StatusBar/NotificationShade/Wallpaper 窗口全在，launcher 获焦，截图存证。
  - **Release**：同程序部署 → 冷启动直接 PASS（PID 850 0 crash，grant 原生存活）；reboot gate PASS（boot `a33ae14c-f96a-4882-8d6f-1d7fe063f625`，PID 852 稳定 90s×6 采样 0 crash，同一组 UI 证据）。
- 截图证据（visual API 读图遇 provider 端 500，改以 dumpsys 为准，截图文件保留）：`runtime-debug-33e07319-boot1.png`、`runtime-debug-33e07319-reboot-gate.png`、`runtime-release-17358f4d-coldboot.png`、`runtime-release-17358f4d-reboot-gate.png`。

### Commits（未 push，等 Chief）

- `ed40e4b4` — `aconfig rewrite: instrument every class from the frozen 725-rule inputs`
- `ea9b2f52` — `aconfig gate: instruction-level checker enforces self-reference-only residuals`

### 证据根

`/tmp/task099-c5-dreams-flags-diagnosis/`：`gate-debug-instrument-all.txt`、`gate-release-instrument-all.txt`（RED 对照 `gate-debug-red.txt`、`gate-release-red.txt`）、`nfjar/`、`dump/`、runtime 截图、PHASE1_RECORD.md 等既往证据全部保留。

### 收尾

原「待解决」两项已被 2026-09-02 用户授权变更替代并超额完成。剩余：Chief 验收 + push + 关闭；`docs/CURRENT_STATE.md` 的实时状态同步与 Task 099 闭包由 Chief 执行。
