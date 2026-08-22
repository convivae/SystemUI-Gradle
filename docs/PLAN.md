# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. 修复 Application 入口并建立 runtime-ready 静态门禁（待用户批准）

- **已验证阻塞**: Task 048 的 frozen Release APK 在专用 API 37 模拟器上真实启动失败：
  - AOSP manifest 的 `.SystemUIApplication` 被 AGP `:app` namespace 展开为不存在的
    `com.android.systemui.app.SystemUIApplication`；真实源码类是
    `com.android.systemui.SystemUIApplication`；
  - R8 另将真实类重命名为 `kvc`，说明 manifest 入口 keep 语义也未生效。
- **拟议范围**: 在不擅改 AOSP mirror 的前提下设计 Gradle manifest overlay/merge 或等效合规方案，
  保证 packaged manifest 指向真实入口，并证明 R8 保留所有 manifest-referenced classes。
- **静态完成条件**: Debug/Release packaged manifest FQN 正确；每个 manifest-referenced class 均存在于
  APK DEX；mapping/usage/seed 证据解释 keep 来源；原有 Python、Debug、fresh R8、optimized Release、
  ZIP/V2/DEX gates 全部保持通过。
- **运行完成条件**: 在签名与 framework-res 兼容的 AOSP-built/identically-keyed image 上重跑专用
  模拟器验证，SystemUI PID 稳定、无 fatal crash loop，状态栏/快捷设置/锁屏可用。
- **审批边界**: manifest/source/res、build rule 或 R8 rule 的任何修改必须先提交精确方案并取得用户批准。

### 2. 逐项讨论其余 Gradle-native 简化候选

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
