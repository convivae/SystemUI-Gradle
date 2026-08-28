# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 本文件只做 5 分钟接手导航；**完整实时技术状态唯一见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)**（当前一句摘要：**Phase C（AOSP 固定到 `android-17.0.0_r1` 后全管线清空重生）已过半**——C1 升级+全量构建、C3 源码重对齐、C2 libs/ 脚本再生、C4a Gradle 接线均完成；**C4b（`:app:assembleDebug` 编译闭环，task073）进行中，17 重对齐后构建尚未恢复绿**。16 时代双 runtime 闭环为历史基线。）

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
5. **当前唯一工程优先级**：Phase C 收尾——C4b 恢复 `:app:assembleDebug` 绿（task073 进行中）→ task074 Release/R8 闭环 → C5 17 镜像模拟器双 runtime 门（C5 前需先从 AOSP-17 `out/` 重跑 `build_sysuisdk.py`）→ C6 manifest 快照 + tag + README 版本声明（ADR 0007）。

## 1.0 Phase C 主线（2026-08-27 起）

| 阶段 | 内容 | 报告 |
|------|------|------|
| C1 | AOSP 树原地切换 `android-17.0.0_r1` + 全量 `m -j16` 构建（2h35m） | `docs/orchestration/log.md` 2026-08-27；ADR 0007 |
| C3（task070） | 源码 17 重对齐：删 847/移 34/拷 2566/覆 3067 + CONV 重标 5806 处；`--strict` exit 0 | `docs/issues/2026-08-27-c3-source-realignment-execution.md` |
| C2（task071） | libs/ 104 文件全删 → 仅凭 7 个 tools 脚本从 AOSP-17 再生 102 文件；maven 全族 2.0.0 | `docs/issues/2026-08-27-c2-libs-regen-17.md` |
| C4a（task072） | 16-module 拓扑接线、catalog 2.0.0、`:app` 最小 manifest 壳、4 个新产物；`gradle help`/`projects` 绿、pytest 293 | `docs/issues/2026-08-28-c4-gradle-wiring.md` |
| **C4b（task073）** | **进行中**：恢复 `:app:assembleDebug`（kairos 模块已落地，错误驱动闭环中） | `docs/orchestration/tasks/073-c4b-debug-compile-closure.md` |
| task074 / C5 / C6 | Release/R8 闭环 → 17 模拟器双 runtime 门 → tag 收口 | 未派发/规划中 |

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

`libs/` 已全部提交入 git（Phase C 后 107 文件全部由 tools 脚本从 AOSP-17 再生，无手工产物）；
**但 17 重对齐后 `:app:assembleDebug` 编译闭环（C4b）进行中，尚不能直接构建出 APK**——
新 Agent 不要求默认先跑重型全量构建；按 CURRENT_STATE 的验证命令与任务需要选择。

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

**下一步**: 阅读 [`AGENTS.md`](../AGENTS.md) 完整规则，然后按 §1 顺序继续。当前方向：Phase C 收口（C4b 编译闭环 → task074 → C5 → C6，见 CURRENT_STATE 与 PLAN.md）。
