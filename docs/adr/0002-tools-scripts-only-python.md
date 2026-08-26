# ADR 0002: tools/ 下脚本一律 Python，禁止 .sh

> **注记（2026-08-26，Task 063）**：本文提及的 `extract_prebuilts.sh` 已于 2026-08-26 经用户批准删除
> （其 4 个产物均已由源码模块取代，见 `docs/architecture/2026-08-26-tools-scripts-inventory-audit.md`）。
> 本 ADR 的决策内容不变；`install_keystore.sh` 已于 2026-08-26 经用户批准转换为
> `tools/install_keystore.py`（Task 067，逻辑等价：openssl/keytool 链经 subprocess 调用，
> 证书 SHA-256 指纹与 tracked `keystore/platform.keystore` 一致），原 .sh 已删除。

## 上下文

本项目 `tools/` 下当前有 2 个 .sh：

- `extract_prebuilts.sh`：从 AOSP out/ 找 jar 复制到 `libs/prebuilts/`
- `install_keystore.sh`：pkcs8 + x509.pem → JKS keystore

用户规则（2026-07-29 明确）：**"tools/ 下脚本一律写 Python，不写 shell"**。
原因：Python 处理复杂逻辑（条件、依赖图、跨平台路径）不易出错；shell 调 subprocess 笨重。

## 决策

1. **禁止**在 `tools/` 下新建 `.sh` 脚本
2. **现有** 2 个 .sh 在下次使用它们的时机迁为 `.py`：
   - `extract_prebuilts.sh` → `extract_prebuilts.py`
   - `install_keystore.sh` → `install_keystore.py`
3. 迁写原则：
   - `openssl` / `keytool` 等 CLI 用 `subprocess.run([...], check=True)`
   - 路径用 `pathlib.Path` 不用字符串拼接
   - 错误用异常，不用 `set -e`
4. ADR 编号继续递增（之前 `0001` 是 res/maven）

## 哪些场景例外

**仅当**满足以下全部才可保留 .sh：

- 调用的命令是系统 CLI（openssl/keytool/find/cp），无可写 Python 逻辑
- 不需要 Python 字符串处理 / 路径处理
- 不需要错误处理

**当前评估**：2 个 .sh 都不满足例外条件，应当迁。

## 迁写时机

"现在"迁写 = 下次需要跑这两个脚本时优先迁，而不是作为独立 commit。

实际触发点（注：`extract_prebuilts.sh` 已于 2026-08-26 删除，首条触发点作废）：
- 用户运行 `./tools/extract_prebuilts.sh` 拉新 jar 时
- 用户新装 AOSP 或换机器，需要 `install_keystore.sh` 时

## 副作用 / 约束

- 迁写后保留 .sh 作为 deprecated wrapper（打印 warning 指向 .py），给老调用方一个过渡期
- 或者直接 `git rm .sh` + 在 commit message 提示"调用方改 `python3 tools/x.py`"

## 参考

- AGENTS.md §八、用户偏好（`tools/` 下脚本一律写 Python，不写 shell，2026-07-29 明确）
- `CarSystemUIGradle/tools/gen_aar_maven.py` 参考实现