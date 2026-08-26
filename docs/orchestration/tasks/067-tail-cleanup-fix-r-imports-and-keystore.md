# Task 067 — 尾账清理：fix_r_imports 复判删除 + install_keystore.sh 转 .py

## Goal（用户 2026-08-26 批准执行）

两个独立小尾账，一个任务内完成：
1. `tools/fix_r_imports_to_res.py`：先独立验证其前提已被证伪，然后删除
2. `tools/install_keystore.sh` → `tools/install_keystore.py`：ADR 0002 欠账转换

## 工作项 1：fix_r_imports_to_res.py

**验证步骤（删除前必须做，证据入报告）**：
- 独立确认源码 R import 与 AOSP 一致：统计项目源码与 AOSP
  `frameworks/base/packages/SystemUI/src/` 中 R import 语句的分布并 diff
  （例如 `grep -rh "^import com.android.systemui.R\|^import com.android.systemui.res.R\|R$" 类模式`，
  方法自定，但结论要能独立支撑"零源码改动解决 R 类"——`check_source_alignment.py`
  的 0-0-0 已隐含证明，你要做的是交叉印证而非重复）
- 确认脚本无其他消费者（grep docs/ + tools/ + kts）

**然后**：删除 `tools/fix_r_imports_to_res.py`；其唯一 doc 引用
（`docs/superpowers/plans/2026-08-06-soong-gradle-apk-policy-checkpoint.md` 附近，
grep 确认实际位置）加"已删除"注记（不改写历史内容）。

## 工作项 2：install_keystore.sh → install_keystore.py

**现状**：读 `tools/install_keystore.sh`，理解其 openssl/keytool 命令序列
（AOSP `build/target/product/security/platform.pk8` + `platform.x509.pem` →
`keystore/platform.keystore`，tracked 产物，app release/debug 签名消费）。

**转换**：
- 新建 `tools/install_keystore.py`，逻辑等价（subprocess 调同一条 openssl/keytool 命令链），
  `--aosp-root` 参数默认走 `tools/aosp_paths.py`（用户单源规则）
- 删除 `install_keystore.sh`
- **验证**（注意 keystore 内含时间戳，逐字节一致**不一定成立**，按此纪律验证）：
  1. 用新脚本生成到临时目录
  2. `keytool -list -keystore` 对比新旧：条目数、alias、证书 SHA-256 指纹必须一致
  3. 证书指纹一致即为通过；若碰巧逐字节一致，如实记录
  4. **不得覆盖** `keystore/platform.keystore`（tracked 基准，保持不动）
- 更新 `docs/adr/0002-tools-scripts-only-python.md` 中的欠账记录
  （install_keystore.sh 引用处改为"已转换，task 067"）
- 若有必要：`tools/tests/` 加一个小测试（如参数解析 + aosp_paths 集成，仿既有模式；
  不强求覆盖 openssl 链本身）

## Acceptance

- `git status --short`：删 2 个旧脚本 + 新增 1 个 .py + ADR/plan 注记 + 测试（可选）+ 报告
- `uv run pytest tools/tests/ -q` 全绿
- 不跑 Gradle（本任务不触碰构建输入）
- 报告 `docs/issues/2026-08-26-tail-cleanup.md`（两个尾账的证据 + 验证结果）；一行 log.md
- commit 英文、本地、不 push

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
