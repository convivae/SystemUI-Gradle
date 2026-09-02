# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 本文件只做 5 分钟接手导航；**完整实时技术状态唯一见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)**（当前一句摘要：Phase C 的 C1–C4 已完成；C5 durable overlay、Debug 热运行与 Release protobuf 修复均已闭合。task078 的 725-rule 秒级 DEX gate 已 review-PASS；task080 又将四个 critical 旧名归属到 166 个唯一 program reference classes，`UNKNOWN=0`，并隔离 compileOnly `framework.jar`。Task 079 broad replay 已暂停；用户已批准 Task 081 最小 pre-D8/R8 reference-only AGP instrumentation exact brief 与 ADR 0008，下一步是串行 build-logic TDD。）

---

## 0. 这是什么项目

将 AOSP `frameworks/base/packages/SystemUI` 移植为独立、自包含的 Gradle 工程
（AGP 9.3.1 + Gradle 9.5 + builtInKotlin 2.2.10），与 AOSP 源码/资源 1:1 对齐，
目标是真实编译出的 SystemUI APK。参考实现：用户私有项目 `CarSystemUIGradle`。

## 1. 5 分钟接手流程（按顺序读）

1. **读 [`AGENTS.md`](../AGENTS.md)** — 全部强制规则（规则 P/S/C/F/R/B/H/D/I、依赖三层策略、诊断流程）。
2. **若参与编排**（herdr worker/architect）再读 [`docs/orchestration/CHARTER.md`](./orchestration/CHARTER.md)、[`docs/orchestration/STATE.md`](./orchestration/STATE.md) 和 [`docs/orchestration/log.md`](./orchestration/log.md) 尾部。
3. **读 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)** — 获取全部实时状态：构建矩阵、版本、依赖产物、blocker、下一步。
4. **读 [`docs/PLAN.md`](./PLAN.md)** — 未完成路线与完成条件。
5. **当前唯一工程优先级**：执行已获批准的 Task 081 exact brief。实现只在 `:app` 建一个 AGP 9.3.1 pre-D8/R8 seam，以 Task 080 冻结的 166-class allowlist 将实际 visitor 范围限制到已证明 program classes，并只改四条 critical exact references；必须保持 `this_class`、hidden target definitions=0。Task 079 不恢复。实现并 review-PASS 后，再把 Debug build、Release build/static gate 和双 runtime reboot gate 拆成串行小任务。主机重启后模拟器当前未运行，Task 081 不需要启动设备。

## 1.0 Phase C 主线（2026-08-27 起）

| 阶段 | 内容 | 报告 |
|------|------|------|
| C1 | AOSP 树原地切换 `android-17.0.0_r1` + 全量 `m -j16` 构建（2h35m） | `docs/orchestration/log.md` 2026-08-27；ADR 0007 |
| C3（task070） | 源码 17 重对齐：删 847/移 34/拷 2566/覆 3067 + CONV 重标 5806 处；`--strict` exit 0 | `docs/issues/2026-08-27-c3-source-realignment-execution.md` |
| C2（task071） | libs/ 104 文件全删 → 仅凭 7 个 tools 脚本从 AOSP-17 再生 102 文件；maven 全族 2.0.0 | `docs/issues/2026-08-27-c2-libs-regen-17.md` |
| C4a（task072） | 16-module 拓扑接线、catalog 2.0.0、`:app` 最小 manifest 壳、4 个新产物；`gradle help`/`projects` 绿、pytest 293 | `docs/issues/2026-08-28-c4-gradle-wiring.md` |
| C4b（task073） | 17-module Debug 编译闭环（含 kairos 与 AOSP-17 SysUISdk 重建）✅ | `docs/issues/2026-08-28-c4b-debug-compile-closure.md` |
| C4c（task074） | Release/R8 missing refs 31→0，`:app:assembleRelease` ✅ | `docs/issues/2026-09-01-c4c-release-r8-closure.md` |
| C5 task075–077 | Debug 热运行 ✅；Release proto keep ✅；goldfish 2880MiB super / 582MiB scratch / 64MiB probe 跨重启 ✅；Release jarjar runtime blocker 待修 | `docs/issues/2026-09-01-c5-emulator-super-slack.md` |
| C5 task078 | DEX 静态 gate + 725-rule Soong/JarJar 机制研究 review-PASS；Release FAIL / stock PASS | `docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md` |
| C5 task080 | 四个 critical old references 的 166-class program-input 来源闭环；50/7/5/104、`UNKNOWN=0`，compileOnly 隔离 | `docs/issues/2026-09-01-c5-focused-reference-origins.md` |
| C5 task081 | 最小 pre-D8/R8 reference-only build logic exact brief 与 ADR 0008 已获用户批准；等待串行实现，尚未构建 APK | `docs/issues/2026-09-02-c5-pre-dex-reference-rewrite.md` |
| C6 | manifest 快照 + release tag + README/version 声明 | 待 C5 完成 |

## 1.1 16 时代 Debug/Release 双 runtime 闭环回顾（2026-08-24→26，历史基线）

| Task | 内容 | 报告 |
|------|------|------|
| 053 | dex 字节码 forensics：设备 framework hidden twin vs SysUISdk 公开名的结构性根因 | `docs/issues/2026-08-25-dex-bytecode-forensics.md` |
| 054/055 | 12 个 aconfig flags 同族缺类批量修复（权威 Soong JAR byte-identical 拷贝） | `docs/issues/2026-08-25-aconfig-flags-batch-closure.md` |
| 057 | 方案 M：14 源 JAR 确定性合并为单一 `libs/systemui-aconfig-flags.jar`，APK 逐字节不变 | `docs/issues/2026-08-25-aconfig-flags-single-jar-merge.md` |
| 059 | 4 个单 consumer AAR 族改为 `files("libs/aars/…")` 直接消费（用户逐族授权，字节中性已证） | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` |
| 058 | DEBUG_RUNTIME_PASS gate suite 六门全绿（在 GLM-5.3 worker 上运行） | `docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md` |

关键新纪律（均来自 08-25 起的实战，仍有效）：同工树=串行（两 Gradle 构建并发曾致 kernel OOM）；worker/reviewer 只允许显式 `joycode/Kimi-K3` 或 `joycode/Kimi-K3-jcloud`；部署后必须设备端 sha256 二次校验（toybox cp 静默截断）；verity 保持 disabled（enable-verity 拆 overlay，见 PITFALLS §14）。

16 时代 Release 闭环（2026-08-26，task 060→061）：AssumeFalseForR8 精确 dontwarn →
`-dontobfuscate`（对齐 Soong dex.go:545）→ 3 行 `-keep`（抗 R8 水平合并），
`docs/issues/2026-08-26-release-runtime-closure.md`。16 时代 APK 台账：Debug `e8aad131…` /
Release `d3968fb2…`。

## 2. 环境确认

```bash
ls /home/conv/myspace/aosp/                     # AOSP 源码必须存在
ls /home/conv/Android/Sdk/platforms/            # 必须有 android-SysUISdk
./gradlew --version                             # Gradle 9.5
```

`libs/` 已全部提交入 git（Phase C 后产物均由 tools 脚本从 AOSP-17 再生）；
`:app:assembleDebug` 与 `:app:assembleRelease` 均可构建。当前失败面不是编译，而是 Release
DEX 对 AOSP 17 platform aconfig Flags 的原名引用与设备 jarjar 后类名不一致；具体证据和
设备终态见 `docs/issues/2026-09-01-c5-emulator-super-slack.md`。

## 3. 红线速查（违反即停，详见 AGENTS/CHARTER）

- **禁止 stub**：不手写 `*.java`/`*.kt` stub，不伪造 res 文件（规则 P/R）。
- **禁止擅改 res/src**：AOSP 镜像源码与资源改动需 ADR 0004 CONV 标记 + 用户授权（规则 R/F）。
- **禁止宽泛 `-dontwarn`/keep 掩盖真实问题**；精确 warning 处置必须先按新架构分类、记录证据并经用户逐项批准；禁止 `@Suppress("DEPRECATION")` 绕过。
- **全系统同一时刻只允许一个 Gradle build**；每批必须保持 `:app:assembleDebug` 成功（硬门禁）。
- `tools/` 脚本一律 Python（ADR 0002）。
- 版本矩阵与模块边界是红线区域：升级依赖、增删模块、移动入口类须先与用户沟通。

## 4. 工作偏好

中文交流；先 plan 再开发；增量提交（commit message 用英文）；依赖尽量最新但先沟通；
及时记录 `docs/issues/`；给下一个 AI 留完整交接文档。

---

**下一步**: 阅读 [`AGENTS.md`](../AGENTS.md) 完整规则，然后按 §1 顺序继续。当前方向：Task 081 build logic TDD 与双轴复核 → 串行 Debug/Release build + 静态 gate → 启动专用模拟器并分别执行双 runtime reboot gate → C6 收口。
