# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. 独立验证 Release runtime（当前主线）

- Debug runtime 已于 2026-08-25 闭环（DEBUG_RUNTIME_PASS，Task 058）；**不得用 Debug 结果推断 Release 的 manifest keep/混淆/runtime 行为**。
- Release APK 静态面已绿（Task 045：R8 missing refs 0、28,600,808 B、V2 签名、0/39 bridge），但从未上过设备。
- **执行要点**：在 emulator-5554（same-tree `sdk_phone64_x86_64`）用 task 054/058 的原子部署规程部署 Release APK；预期会暴露 Debug 没有的一类问题（aconfig 假设注解 shrink、BuildConfig 字段、反射入口 keep）；一次只根据一个明确 runtime 根因改一个假设。
- **完成条件**：与 Debug 门同级——PID 稳定 ≥5 分钟、零 FATAL/NoClassDefFoundError、StatusBar/NotificationShade 在屏、关键交互正常。

### 2. Release 阶段遗留 2 包（Task 043 尾账，用户 2026-08-25 拍板）

- **AssumeTrueForR8**：NOT APPROVED 维持；等 Release runtime 出现真 blocker 证据后逐项讨论处置。
- **tracinglib-platform.jar 溯源**：查清 AOSP 出处，决定保留 jar 还是换官方坐标。

### 3. 维护性观察（定期，无 deadline）

- Kotlin 2.3 / AGP 9.5 解锁后升级检查（当前 AGP 9.3.1 绑 Kotlin 2.2.10）。
- AOSP 树漂移时重跑 `package_aconfig_jars.py --merge-framework`（源字节已漂过两次）。
- 存量本地 jar 定期回查官方 Maven 等价物（规则 §1.5，Task 026 首开）。

---

## 纪律约束（全程有效）

- 每批必须保持 `:app:assembleDebug` 成功（硬门禁）；全系统同一时刻只允许一个 Gradle build。
- 错误数/R8 refs 数只作诊断，不作为 artifact seam、提交门槛或 Soong/Gradle 等价要求（规则 I）。
- 不以 Soong target、单个 missing ref 或字节一致性自动决定 AAR/SysUISdk/R8 设计。
- 任何回退、合并或不可逆删除都必须先逐项向用户解释并获得批准。
- 每批按规则 D 先写 `docs/issues/` 记录，merge 后更新 `docs/CURRENT_STATE.md`。

## 已完成工作

从 5296 个编译错误到 Debug APK、239/239 测试、Release R8 140→0、完整 optimized-resource Release APK + V2 签名，以及 **same-tree x86_64 模拟器 DEBUG_RUNTIME_PASS（Tasks 052c→059，2026-08-25：dex forensics → 12 族 aconfig flags 闭环 → 合并单 JAR → AAR 直接消费迁移 → 六门 gate suite 全绿）** 的历程与证据，见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) 与 `docs/issues/` 2026-08-24/25 五篇报告。
