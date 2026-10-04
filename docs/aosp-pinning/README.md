# AOSP Pinning（AOSP 版本快照）

本目录存放本项目验证基线对应的 **AOSP 版本快照文件**，用于把"当前验证基于哪棵 AOSP 树"
变成可追溯、可 checkout 的事实。

## 当前快照

| 文件 | 内容 |
|---|---|
| [`aosp-manifest-2026-08-26-validated.xml`](./aosp-manifest-2026-08-26-validated.xml) | AOSP `main` 分支 2026-08-26 已验证树的 `repo manifest -r` 导出：**1042 个 project**，每个 project 都带精确 `revision`（commit hash） |

该快照从完成以下验证的同一棵 AOSP 树导出：

- SysUISdk 单入口生成（`tools/build_sysuisdk.py`，Task 045 确定性验证）
- `libs/` 全部产物再生（Task 064/065：冻结 sha256 台账，15 个 gap 产物闭环）
- Debug runtime（Task 058，2026-08-25 DEBUG_RUNTIME_PASS）
- Release runtime（Task 061/065，2026-08-26 RELEASE_RUNTIME_PASS）

## 用途

- **复现**：新机器上 `repo init -u https://android.googlesource.com/platform/manifest -b main`
  后，用本快照作为 manifest（`repo init -m <snapshot>` 后 `repo sync`），即可 checkout
  到与本项目产物完全同源的 AOSP 树。
- **漂移检测**：AOSP 上游漂移后重跑 `tools/package_misc_jars.py` / `package_aconfig_jars.py`
  等脚本时，脚本内冻结的 `source_sha256` 指纹与快照树对账，漂移会以 warning 显式暴露。

## 状态声明

**正式版本固定（pinning 到某个 AOSP 正式版本号）尚未执行。** 当前基线是 `main` 分支的
时间点快照，不是正式 release。升级/固定 AOSP 版本（升级 → 重编译 → 全管线重跑 → 重新
适配验证）是已规划的后续工程（Phase C，全管线从零复现；见
[../PLAN.md](../PLAN.md) 与
[../architecture/2026-08-26-regeneration-gap-closure.md](../architecture/2026-08-26-regeneration-gap-closure.md)）。

快照由 `repo manifest -r` 机械生成（1075 行），无手工编辑。
