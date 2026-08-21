# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. SysUISdk 单入口 composition（当前唯一优先级）

- **目标入口**: `python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp`。
- **范围**: 官方 SDK 只读；直接消费传入 AOSP 已编译的 `out/`；用 Python 标准库事务性生成独立 `android-SysUISdk`，不调用 Soong、不原地 patch、不生成永久备份。
- **先决条件**: 冻结 framework/APEX/module/libcore artifact family 到 `android.jar`、`core-for-system-modules.jar`、framework resources、AIDL 与 39 个 bridge classes 的确定性映射；缺失或多候选必须失败，禁止猜测。
- **流程**: 先向用户展示并取得 exact Worker brief 批准，再在隔离 worktree 以 TDD 实施；当前四脚本在替代方案通过完整验证前不得删除。
- **完成条件**: Python、fresh Debug、fresh Release R8、完整 Release、optimized resource shrinking、APK 内容和 V2 签名全部通过；bridge classes 不进入 APK。

### 2. 删除已证明被替代的文件

- 新 SysUISdk 验证等价后，退役并删除被单入口替代的仓库脚本与其他已证明无引用文件。
- 外部 live SysUISdk 的 9 个历史备份另行列出路径、大小和 hash；未经用户单独批准，不做不可逆删除。

### 3. 兼容模拟器/设备安装与运行验证

- **范围**: AVD 签名/root/framework 兼容性预审后替换预装 SystemUI 并运行验证。
- **计划**: `docs/issues/2026-08-20-device-emulator-validation-plan.md`。
- **完成条件**: APK 在目标设备/模拟器安装并运行，SystemUI 无 crash loop，核心流程可用。

### 4. 逐项讨论其余 Gradle-native 简化候选

- Task 043 剩余 7 个 `NOT APPROVED` packet 逐项说明存在原因、维护成本、替代损失和验证方法。
- 只有用户明确批准的项目才进入独立实施任务。

---

## 纪律约束（全程有效）

- 每批必须保持 `:app:assembleDebug` 成功（硬门禁）；全系统同一时刻只允许一个 Gradle build。
- 错误数/R8 refs 数只作诊断，不作为 artifact seam、提交门槛或 Soong/Gradle 等价要求（规则 I）。
- 不以 Soong target、单个 missing ref 或字节一致性自动决定 AAR/SysUISdk/R8 设计。
- 任何回退、合并或不可逆删除都必须先逐项向用户解释并获得批准。
- 每批按规则 D 先写 `docs/issues/` 记录，merge 后更新 `docs/CURRENT_STATE.md`。

## 已完成工作

从 5296 个编译错误到 Debug APK、239/239 测试、Release R8 140→0，以及完整 optimized-resource Release APK + V2 签名的历程与证据，见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)。
