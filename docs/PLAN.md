# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. 建立 host-native same-tree Goldfish baseline（等待 bounded-design 批准）

- **已验证阻塞**: Task 051 证明 Google API image 与项目 AOSP checkout 在 framework revision、
  platform certificate 与 Soong `platform_apis:true` / `usesNonSdkApi` runtime contract 上不一致；
  Task 052 又证明 x86_64-host Android Emulator launcher 正式拒绝 ARM64 guest。direct AArch64
  QEMU + generic `virt` 虽达 kernel/init/ADB，但未 boot-complete，不能作为 Goldfish baseline。
- **选定候选**: `sdk_phone64_x86_64 trunk_staging userdebug`（same-tree framework/platform key，
  host-native ISA）；`aosp_cf_x86_64_phone` 仅在完整 Cuttlefish prerequisites 满足后作为备选。
- **执行前条件**: 用户批准 bounded design；干净停止仍运行的 PID 1727011 ARM64 诊断 guest；
  证明零 QEMU/Emulator/ADB target；复核磁盘（当前约 29 GiB free，预计新增 15–17 GiB，
  10 GiB stop threshold，未经独立证据与决策不删既有 AOSP output）；
  构建严格 `m -j4 emu_img_zip`，不得并行 Gradle/Soong；在真实 launcher process 中证明
  effective KVM access。
- **baseline 完成条件**: same-tree target 报告 `ro.kernel.qemu=1`、x86_64 ABI、正确 fingerprint/
  userdebug；`sys.boot_completed=1`，`system_server` 和 stock SystemUI 稳定；在此之前禁止部署
  Gradle APK。

### 2. 部署 frozen Debug APK 并关闭 Debug runtime

- **现有静态成果**: Task 050 frozen Debug APK 为 163,561,195 B / SHA-256 `4d8240fd…f78997`；
  manifest component FQCN gate 为 93 present + 2 aliases + 0 missing。Task 051 已证明
  `SystemUIApplication` app→core→DEX assembly 正确；`appComponentFactory` 仍需纳入独立静态 gate。
- **部署条件**: 仅在第 1 项 stock baseline 全部通过后，使用动态 `pm path`、byte-identical hash、
  apksigner certificate、PackageManager policy 和 runtime log 作为权威证据。
- **完成条件**: SystemUI PID 稳定至少 60 秒；状态栏、Quick Settings、锁屏/唤醒/解锁与
  launcher 交互正常；无 fatal、ANR、watchdog 或 crash loop。一次只根据一个明确 runtime 根因
  修改一个假设；禁止调用点 `try/catch NoSuchMethodError`、stub、伪造资源或宽泛 R8 suppression。

### 3. 独立验证 Release runtime

- Debug runtime closure review、main fresh verification、merge/push 完成后，另开独立任务验证
  optimized Release APK；不得用 Debug 结果推断 Release 的 manifest keep/混淆/runtime 行为。

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
