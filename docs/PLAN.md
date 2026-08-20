# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. B1–B4 platform/build classpath 6 refs（当前唯一优先级）

- **范围**: 6 个 platform/build classpath 桥接类（需 SysUISdk/AGP 桥或窄域处理，禁止宽泛 `-dontwarn`）。
- **完成条件**: 该组 refs 清零且不引入掩盖性配置。

### 2. `AssumeTrueForR8` build-time annotation 1 ref

- **完成条件**: 该 ref 以真实产物/桥接消除。

### 3. Release R8 达到 0 missing refs

- **完成条件**: fresh `:app:minifyReleaseWithR8 --rerun-tasks` BUILD SUCCESSFUL。

### 4. `shrinkResources` + 签名/打包验证

- **完成条件**: release 构建含资源收缩成功产出，V2 签名校验通过。

### 5. 兼容模拟器/设备安装与运行验证

- **范围**: AVD 签名/root/framework 兼容性预审后替换预装 SystemUI 并运行验证。
- **计划**: `docs/issues/2026-08-20-device-emulator-validation-plan.md`。
- **完成条件**: APK 在目标设备/模拟器安装并运行，核心 SystemUI 功能可用。

---

## 纪律约束（全程有效）

- 每批必须保持 `:app:assembleDebug` 成功（硬门禁）；全系统同一时刻只允许一个 Gradle build。
- 错误数/R8 refs 数只作诊断，不作为提交门槛（规则 I）；但 R8 差分必须精确可解释。
- 每批按规则 D 先写 `docs/issues/` 记录，merge 后更新 CURRENT_STATE。

## 已完成工作

从 5296 个编译错误到 debug APK 成功、195/195 测试、release R8 140→7 的完整历程与证据，
见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) 的 Verified milestones 与
[`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md)。
