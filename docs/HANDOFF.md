# SystemUI-Gradle 交接文档 (HANDOFF)

> **下一个 AI Agent 请先读本文件。**
> 本文件只做 5 分钟接手导航；**完整实时技术状态唯一见 [`docs/CURRENT_STATE.md`](./CURRENT_STATE.md)**（当前一句摘要：Gradle-native 架构 spec 已获用户批准；Task 043 只读现状审查 plan/brief 已起草，等待 exact brief 单独批准后派发；release R8 事实仍为 1 个 missing ref）。

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
5. **当前唯一工程优先级**：用户复核 `docs/orchestration/tasks/043-gradle-native-current-state-audit.md`；批准后才派隔离只读 Worker，禁止直接实施、回退或重启原 Task 042。

## 2. 环境确认

```bash
ls /home/conv/myspace/aosp/                     # AOSP 源码必须存在
ls /home/conv/Android/Sdk/platforms/            # 必须有 android-SysUISdk
./gradlew --version                             # Gradle 9.5
```

`libs/` 已全部提交入 git，新 clone **无需**重新生成 AOSP 产物即可构建。
新 Agent **不要求**默认先跑重型全量构建；按 CURRENT_STATE 的验证命令与任务需要选择。

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

**下一步**: 阅读 [`AGENTS.md`](../AGENTS.md) 完整规则，然后按 §1 顺序继续。
