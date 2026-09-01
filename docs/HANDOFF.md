# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 本文件只做 5 分钟接手导航；**完整实时技术状态唯一见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)**（当前一句摘要：Phase C 的 C1–C4 已完成；C5 durable overlay、Debug 热运行与 Release protobuf 修复均已闭合。task078 的秒级 DEX gate 与 Soong/JarJar 研究已 review-PASS：规则为 725 条 exact / 726 物理行，当前 Release 稳定 FAIL、stock 稳定 PASS；首选 pre-R8 方案族仍须先经用户批准完成 E1–E4 有界实验，之后才能裁决/实施 rewrite、重跑双冷启动门并进入 C6。）

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
5. **当前唯一工程优先级**：task078 研究/gate 已完成；先向用户申请 E1–E4 实验批准（仅清单、scratch JarJar/AAR 干跑及 standalone R8 resolution probe，零行为变更），实验通过并再次裁决后才实施 C5 JarJar 引用改写。不得打包 platform Flags、不得 stub/dontwarn/源码 import 批量改写；随后在 task077 durable overlay 上重跑 Debug/Release 整机重启门，最后做 C6。

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
| C5 task078 | DEX 静态 gate + 725-rule Soong/JarJar 机制研究 review-PASS；Release FAIL / stock PASS；E1–E4 与 rewrite 均未执行 | `docs/architecture/2026-09-01-aosp17-systemui-jarjar-design.md` |
| C6 | manifest 快照 + release tag + README/version 声明 | 待 C5 完成 |

## 1.1 16 时代 Debug/Release 双 runtime 闭环回顾（2026-08-24→26，历史基线）

| Task | 内容 | 报告 |
|------|------|------|
| 053 | dex 字节码 forensics：设备 framework hidden twin vs SysUISdk 公开名的结构性根因 | `docs/issues/2026-08-25-dex-bytecode-forensics.md` |
| 054/055 | 12 个 aconfig flags 同族缺类批量修复（权威 Soong JAR byte-identical 拷贝） | `docs/issues/2026-08-25-aconfig-flags-batch-closure.md` |
| 057 | 方案 M：14 源 JAR 确定性合并为单一 `libs/systemui-aconfig-flags.jar`，APK 逐字节不变 | `docs/issues/2026-08-25-aconfig-flags-single-jar-merge.md` |
| 059 | 4 个单 consumer AAR 族改为 `files("libs/aars/…")` 直接消费（用户逐族授权，字节中性已证） | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` |
| 058 | DEBUG_RUNTIME_PASS gate suite 六门全绿（在 GLM-5.3 worker 上运行） | `docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md` |

关键新纪律（均来自 08-25 实战，仍有效）：同工树=串行（两 Gradle 构建并发曾致 kernel OOM）；worker 只用 joycode GLM-5.3/5.2 模型；部署后必须设备端 sha256 二次校验（toybox cp 静默截断）；verity 保持 disabled（enable-verity 拆 overlay，见 PITFALLS §14）。

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

**下一步**: 阅读 [`AGENTS.md`](../AGENTS.md) 完整规则，然后按 §1 顺序继续。当前方向：请求用户裁决并执行 E1–E4 有界实验 → 基于实验结果另立并裁决 JarJar rewrite 实现 brief → C5 双冷启动门 → C6 收口。
