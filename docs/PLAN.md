# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. Task 043 当前状态只读架构审查（当前唯一优先级）

- **已批准设计**: `docs/superpowers/specs/2026-08-21-gradle-native-systemui-build-design.md`
- **计划**: `docs/superpowers/plans/2026-08-21-gradle-native-current-state-audit.md`
- **Worker brief**: `docs/orchestration/tasks/043-gradle-native-current-state-audit.md`（等待用户单独批准后派发）
- **范围**: 只看当前仓库、AOSP owner、AGP 行为与参考项目；禁止 Git 历史、Gradle、实施和回退。
- **完成条件**: 双轴审查通过的 keep / simplify / consolidate / candidate rollback / needs experiment / needs history-context ledger。

### 2. 逐项讨论并实施经用户批准的简化

- **完成条件**: 每个候选先说明存在原因、解决的问题、维护成本、替代方案和验证；仅批准项进入独立实施任务。

### 3. Gradle-native Release APK 验收

- **范围**: 在批准的新架构下处理当前 `AssumeTrueForR8` optimizer/build-time 问题；不要求复刻 Soong R8 配置或输出。
- **完成条件**: `:app:minifyReleaseWithR8` 与 `:app:assembleRelease` 成功，资源收缩及 V2 签名校验通过。

### 4. 兼容模拟器/设备安装与运行验证

- **范围**: AVD 签名/root/framework 兼容性预审后替换预装 SystemUI 并运行验证。
- **计划**: `docs/issues/2026-08-20-device-emulator-validation-plan.md`。
- **完成条件**: APK 在目标设备/模拟器安装并运行，核心 SystemUI 功能可用。

---

## 纪律约束（全程有效）

- 每批必须保持 `:app:assembleDebug` 成功（硬门禁）；全系统同一时刻只允许一个 Gradle build。
- 错误数/R8 refs 数只作诊断，不作为 artifact seam、提交门槛或 Soong/Gradle 等价要求（规则 I）。
- 不以 Soong target、单个 missing ref 或字节一致性自动决定 AAR/SysUISdk/R8 设计。
- 任何回退或合并都必须先逐项向用户解释并获得批准。
- 每批按规则 D 先写 `docs/issues/` 记录，merge 后更新 CURRENT_STATE。

## 已完成工作

从 5296 个编译错误到 debug APK 成功、233/233 测试、release R8 140→1 的完整历程与证据，
见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) 的 Verified milestones 与
[`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md)。
