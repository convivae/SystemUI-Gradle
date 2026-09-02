# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. Phase C：AOSP 固定 `android-17.0.0_r1` + 清空重生（ADR 0007）

- [x] ~~C1：AOSP 升级 + 全量构建~~ ✅ 2026-08-27（原树切换 `android-17.0.0_r1`，manifest `5bc9a7ce`，frameworks/base `94b4c163b`；`m -j16` 2h35m；soong_build OOM 根因已修）
- [x] ~~C3：源码 17 重对齐（task070）~~ ✅ 2026-08-27（`--strict` exit 0；删 847/移 34/拷 2566/覆 3067；CONV 重标 5806 处；MODIFIED 终态 1 src + 86 res 均白名单）
- [x] ~~C2：libs/ 全删 + 脚本再生（task071）~~ ✅ 2026-08-28（104 删 → 7 脚本再生 102 文件，无手工产物；maven 全族 2.0.0；`motion_tool_lib.jar`/`settingslib-selector-flags.jar`/security-flags/quickaccesswallet-flags 族退役）
- [x] ~~C4a：Gradle 接线（task072）~~ ✅ 2026-08-28（16-module 拓扑、catalog 23 族 2.0.0 + jsr330、`:app` 最小 manifest 壳、core namespace→`com.android.systemui.core`、surfaceeffects×3 + uilatencystats-flags + dynamiccolors 新产物；`gradle help`/`projects` 绿、`--strict` exit 0、pytest 293）
- [x] ~~C4b：编译闭环（task073）~~ ✅ 2026-08-31（17-module 拓扑，`:app:assembleDebug` BUILD SUCCESSFUL；AOSP-17 SysUISdk 重建；对齐、pytest、冻结指纹全绿）
- [x] ~~C4c：Release/R8 闭环（task074）~~ ✅ 2026-08-31（missing refs 31→0；`:app:assembleRelease` BUILD SUCCESSFUL；内容级复现成立）
- [x] ~~**C5：17 镜像双 runtime 门**~~ ✅ 2026-09-03（Task 099 闭环）：aconfig reference rewrite 生产修复落地——完整 725 条 AOSP repackaging 规则 + instrument-everything reference-only seam + 指令级静态门禁。fresh Debug `33e07319…`（200,506,573 B）与 fresh Release `17358f4d…`（45,030,130 B）双 APK：构建 ✅、静态门 0 违规 ✅、部署 + 冷启动 ✅、**整机重启门 ✅**（PID 稳定、0 FATAL、UI 三件套在屏）。commits `ed40e4b4`/`ea9b2f52`/`c79044b4` 已 push。Task 079 broad replay 保持暂停。
- [ ] **C6**：manifest 快照 + release tag + version 声明（ADR 0007 收口；`git diff` 即产物漂移审计报告）。README 双语已于 2026-09-03 重写为对外文档，HANDOFF/CURRENT_STATE 已同步。

### 2. 尾账（Release 阶段处理）

- **tracinglib-platform.jar 溯源**：查清 AOSP 出处，决定保留 jar 还是换官方坐标。
- AssumeTrueForR8 blocker 已随 16 时代 round-1 修复关闭（精确 dontwarn 落地，`app/proguard_gradle.flags`）；17 基线 Release 重放归 task074。

### 3. 维护性观察（定期，无 deadline）

- Kotlin 2.3 / AGP 9.5 解锁后升级检查（当前 AGP 9.3.1 绑 Kotlin 2.2.10）。
- AOSP 树漂移时重跑 `package_aconfig_jars.py --merge-framework`（源字节已漂过两次）。
- 存量本地 jar 定期回查官方 Maven 等价物（规则 §1.5，Task 026 首开）。
- ~~可选诊断：AOSP prebuilts R8 与 AGP 9.3.1 内嵌 R8 的版本差~~ **已关闭（2026-08-26，用户批准跳过）**：纯好奇心诊断，不影响构建/运行，修复已用 3 行精确 `-keep` 对症落地；查出版本差也不改变方案。
- 观察项：pytest 全套偶发一次 `test_build_sysuisdk` 事务测试间歇失败（2026-08-26 观测，重跑即绿，疑文件系统时序）；不修，再次出现时先稳定复现再查。
- CoreStartable 伞形 `-keep`（`implements CoreStartable`）作为未来再出合并碰撞时的备选（目前不需要）。

---

## 纪律约束（全程有效）

- 每批必须保持 `:app:assembleDebug` 成功（硬门禁）；全系统同一时刻只允许一个 Gradle build。
- 错误数/R8 refs 数只作诊断，不作为 artifact seam、提交门槛或 Soong/Gradle 等价要求（规则 I）。
- 不以 Soong target、单个 missing ref 或字节一致性自动决定 AAR/SysUISdk/R8 设计。
- 任何回退、合并或不可逆删除都必须先逐项向用户解释并获得批准。
- 每批按规则 D 先写 `docs/issues/` 记录，merge 后更新 `docs/CURRENT_STATE.md`。

## 已完成工作

从 5296 个编译错误到 16 时代（AOSP main 快照）的 Debug APK、双 runtime 门
（**DEBUG_RUNTIME_PASS** 2026-08-25 + **RELEASE_RUNTIME_PASS** 2026-08-26，emulator-5554）
的历程与证据，见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) 与 `docs/issues/` 归档。
Phase C（AOSP 固定 17.0.0_r1 + 全管线清空重生）的 C1–C5 已全部完成：C5 最终由 Task 099
闭环（aconfig 725 规则 instrument-everything seam；Debug `33e07319…` / Release `17358f4d…`
双 APK 静态 + runtime + 整机重启门全 PASS）。Task 079 broad replay 暂停。最新证据见
`docs/issues/2026-09-02-c5-dreams-flags-runtime-origin-diagnosis.md`。
