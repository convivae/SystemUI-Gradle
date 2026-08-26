# SystemUI-Gradle 未完成路线 (PLAN.md)

> **Owner**: 本文件只描述**未完成**路线、顺序与完成条件。
> 已完成里程碑与完整实时状态见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)；
> 历史阶段详情见 [`docs/GRADLE_MIGRATION_LOG.md`](./GRADLE_MIGRATION_LOG.md) 与 `docs/issues/` 归档。

---

## 当前路线（有序，完成一项进入下一项）

### 1. ~~独立验证 Release runtime~~ ✅ 已完成（2026-08-26，RELEASE_RUNTIME_PASS）

三轮修复闭环：R8 missing `AssumeFalseForR8`（精确 dontwarn，Task 044 同款）→ `-dontobfuscate`（对齐 Soong dex.go:545 语义，治愈 getSimpleName 撞名）→ 3 行 `-keep`（抗 R8 水平合并，DumpManager 类名注册撞键）。Release APK `14768581…` 在 emulator-5554 上门级验证通过。证据：`docs/issues/2026-08-26-release-runtime-closure.md`（四轮完整记录）。

### 2. Release 阶段遗留尾账

- **tracinglib-platform.jar 溯源**：查清 AOSP 出处，决定保留 jar 还是换官方坐标。
- ~~AssumeTrueForR8 blocker~~ 已随 round-1 修复关闭（同族 AssumeFalseForR8 精确 dontwarn 落地，`app/proguard_gradle.flags`）。

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

从 5296 个编译错误到 Debug APK、239/239 测试、Release R8 140→0、完整 optimized-resource Release APK + V2 签名，以及 **same-tree x86_64 模拟器 DEBUG_RUNTIME_PASS（Tasks 052c→059，2026-08-25）+ RELEASE_RUNTIME_PASS（Tasks 060→061，2026-08-26）** 的历程与证据，见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md) 与 `docs/issues/` 2026-08-24/25 五篇报告。
