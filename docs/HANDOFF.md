# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 本文件只做 5 分钟接手导航；**完整实时技术状态唯一见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)**（当前一句摘要：**Phase C 的 C1–C5 全部完成**。Task 099 完成 aconfig reference rewrite 生产修复（完整 725 条规则 + instrument-everything seam + 指令级门禁），fresh Debug `33e07319…` 与 fresh Release `17358f4d…` 双 APK 均通过静态门 + 部署 + 冷启动 + **整机重启门**（PID 稳定、0 FATAL）；commits `ed40e4b4`/`ea9b2f52`/`c79044b4` 已 push。Task 079 broad replay 保持暂停。下一步 C6 收口。）

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
5. **当前唯一工程优先级**：C6 收口（manifest 快照 + release tag + 版本声明，ADR 0007）。C5 已由 Task 099 闭合：双 variant fresh APK 的静态门禁、部署、冷启动与整机重启门全部 PASS。

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
| C5 task081 | app-only `ALL` reference-only build logic、四规则/166 allowlist、9 focused tests与双轴review ✅ | `docs/issues/2026-09-02-c5-pre-dex-reference-rewrite.md` |
| C5 task082–084 | 真实Debug pipeline FAIL；最深literal path固定为`InstrumentationContext_Decorated.__apiVersion__` → production factory `__instrumentationContext__` | `docs/issues/2026-09-02-c5-serialization-field-path.md` |
| C5 task085–089 | no-op controls + first-party research：Task086 PASS、Task087 INCONCLUSIVE；无升级targeted-fix证据，当前ASM seam pre-D8/pre-R8已证 | `docs/architecture/2026-09-02-agp-instrumentation-isolation-research.md` |
| C5 task090 | production custom file-parameter shape + field-free no-op control以factory sentinel实际执行，正式`PASS`；不证明production implementation/APK | `docs/issues/2026-09-02-c5-observable-file-params-control.md` |
| C5 task091 | sentinel-scoped managed file access + `FrozenAconfigInputs.load(...)` 可观察`PASS`；entered/loaded各1；cleanup重复/exit-code缺失偏差已记录 | `docs/issues/2026-09-02-c5-frozen-input-load-control.md` |
| C5 task092 | positive allowlist admission与class-byte no-op visitor可观察`PASS`；entered/accepted/visitor各1；cleanup self-match/exit-code及scratch偏差已记录 | `docs/issues/2026-09-02-c5-positive-allowlist-control.md` |
| C5 task093 | exact production-shaped transient cache layer在callback前重现Task 084 path；`CACHE_ACTIVATED_ISOLATION_FAILURE`，当前最小已知activation boundary固定为完整cache layer | `docs/issues/2026-09-02-c5-transient-cache-control.md` |
| C5 task094 | immutable managed-value + field-free no-op control正式`PASS`：三个sentinel各1、45 ASM records、known serialization markers 0；只证明isolation seam | `docs/issues/2026-09-02-c5-immutable-input-snapshot-control.md` |
| C5 task095 | production managed-value seam + `referenceOnlyVisitor(...)` focused/direct proof；corrected bounded gate与双轴review均PASS | `docs/issues/2026-09-02-c5-production-immutable-input-seam.md` |
| C5 task096 | fresh Debug build/static ✅：190,547,804 B / SHA `f3af35d9…` / 13 DEX；hidden refs `4/4`、hidden defs `0`、old-owner residual PASS | `docs/issues/2026-09-02-c5-debug-build-static-gate.md` |
| C5 task097 | fresh Release build/R8/static ✅：45,030,130 B / SHA `641c6533…` / 2 DEX；checker exit 0 / `RESULT=PASS` | `docs/issues/2026-09-02-c5-release-build-static-gate.md` |
| C5 task098 | fresh Debug runtime 门 ❌ `DEBUG_RUNTIME_REBOOT_FAIL`（622 次 `dreams.Flags` NCDFE）→ 触发 Task 099 | `docs/issues/2026-09-02-c5-debug-runtime-reboot-gate.md` |
| C5 task099 | **aconfig 生产修复 + C5 闭环 ✅**：725 规则 + instrument-everything seam + 指令级门禁；Debug `33e07319…` / Release `17358f4d…` 双 APK 静态 + 部署 + 冷启动 + 整机重启门全 PASS；commits `ed40e4b4`/`ea9b2f52`/`c79044b4` 已 push | `docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md` |
| C6 | manifest 快照 + release tag + 版本声明（README 双语已于 2026-09-03 重写为对外文档） | 进行中 |

## 1.1 16 时代 Debug/Release 双 runtime 闭环回顾（2026-08-24→26，历史基线）

| Task | 内容 | 报告 |
|------|------|------|
| 053 | dex 字节码 forensics：设备 framework hidden twin vs SysUISdk 公开名的结构性根因 | `docs/issues/2026-08-25-dex-bytecode-forensics.md` |
| 054/055 | 12 个 aconfig flags 同族缺类批量修复（权威 Soong JAR byte-identical 拷贝） | `docs/issues/2026-08-25-aconfig-flags-batch-closure.md` |
| 057 | 方案 M：14 源 JAR 确定性合并为单一 `libs/systemui-aconfig-flags.jar`，APK 逐字节不变 | `docs/issues/2026-08-25-aconfig-flags-single-jar-merge.md` |
| 059 | 4 个单 consumer AAR 族改为 `files("libs/aars/…")` 直接消费（用户逐族授权，字节中性已证） | `docs/issues/2026-08-25-aar-direct-consumption-migration.md` |
| 058 | DEBUG_RUNTIME_PASS gate suite 六门全绿（在 GLM-5.3 worker 上运行） | `docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md` |

关键新纪律（均来自 08-25 起的实战，仍有效）：同工树=串行（两 Gradle 构建并发曾致 kernel OOM）；部署后必须设备端 sha256 二次校验（toybox cp 静默截断）；verity 保持 disabled（enable-verity 拆 overlay，见 PITFALLS §14）；重启后 overlay 重挂为只读，写分区前重新 `adb remount`（PITFALLS §15.4）。（2026-09-02 起用户已取消 worker 模型/CONTRACT 等人为编排限制，见 CHARTER。）

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

`libs/` 已全部提交入 git（Phase C 后产物均由 tools 脚本从 AOSP-17 再生）。`:app:assembleDebug`
与 `:app:assembleRelease` 均已 fresh 构建成功并通过 Task 099 的指令级静态门禁与模拟器 runtime
（含整机重启）验证；最终 APK：Debug `33e07319…`、Release `17358f4d…`。aconfig 引用改写 seam
的完整记录（根因、D8 lambda 教训、instrument-everything 裁定）见
`docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md`。

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

**下一步**: 阅读 [`AGENTS.md`](../AGENTS.md) 完整规则，然后按 §1 顺序继续。当前方向：C6 收口（manifest 快照 + release tag + 版本声明）→ 尾账清理。
