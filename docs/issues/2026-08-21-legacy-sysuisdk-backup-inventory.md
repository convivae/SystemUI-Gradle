# 2026-08-21 — Legacy live SysUISdk backup inventory

## Status

Executed 2026-08-22 by Worker (Task 047, worktree `SystemUI-Gradle-wt-047`).
Read-only audit completed; nothing deleted (`DELETED=0`). Full report:
`docs/architecture/2026-08-21-legacy-sysuisdk-backup-inventory.md`.

## Background

The legacy live platform contains nine historical backup files created by superseded
patch/install workflows:

- four `android.jar` backups;
- four `core-for-system-modules.jar` backups;
- one `framework.aidl` backup.

They are outside the repository and were deliberately excluded from Task 045. Before
any irreversible deletion, the project needs a byte-level inventory and a per-file
retention recommendation.

## Steps

1. Snapshot exact path, size, mtime, SHA-256, and type for all nine files.
   ✅ `/tmp/task047-before.json`（fixed-name Python manifest；BACKUPS=9 HASHED=9 MISSING=0；
   8 个 JAR 全部通过 ZIP CRC 校验、0 重复条目名）。脚本 `/tmp/task047-inspect.py`。
2. Validate every JAR as ZIP, detect duplicate names, and inspect entry counts.
   ✅ 全部 zip_test=OK、dups=0、entry counts 已记录（见报告 §3 表）。
3. Generate one canonical current SysUISdk under `/tmp/task047-*` from the read-only
   official base and frozen AOSP inputs; never replace the live platform.
   ✅ `python3 tools/build_sysuisdk.py --aosp-root ... --output
   /tmp/task047-generated/android-SysUISdk` → exit 0（11,381 files，marker 存在）；
   三个 canonical target hash 与 Task 045 main-fresh 记录完全一致（确定性复现）。
4. Compare backups with stock base files, live primary files, canonical generated
   files, and each other.
   ✅ 逐条目（entry-name set + 每条目字节）比较完成，证据
   `/tmp/task047-comparison.json`；关键结论：两个 `.orig` 与 `framework.aidl.bak-preaidl`
   与 stock 逐字节相同；`android.jar.bak-20260821-013303` 内容与 live primary 完全相同
   （37,397/37,397 条目、逐字节相等，仅 ZIP 元数据不同）；`android.jar.bak-20260821-011116`
   内容是 live primary 的严格子集（live = backup + 35 个 Task 041 bridge 条目）；两个
   core `.bak-210813/011116` 内容 = stock + 4 个 dalvik bridge 注解（逐字节等于 live/
   canonical 对应条目）；`core-for-system-modules.jar.bak-20260821-013303` 内容与 live 和
   canonical 均完全相同；`android.jar.bak-20260813-210816` 含 230 个 live 没有的旧
   `res/**` 条目 + 1,039 个字节不同的条目（真正唯一的历史快照）。
5. Classify each backup as byte-identical/redundant, unique historical snapshot, or
   malformed/unknown; report recoverability and potential reclaimed bytes.
   ✅ 9/9 行分类完成：8 行 byte-identical/redundant（候选删除 163,149,374 字节），
   1 行 unique historical snapshot（`android.jar.bak-20260813-210816`，建议保留）；
   0 行 malformed/unknown。逐行 recoverability 与 caveat 见报告 §6。
6. Re-hash the live platform backup set after inspection to prove no mutation.
   ✅ `/tmp/task047-after.json` 与 before 规范化后逐字节相同：
   `BACKUP_SET_UNCHANGED=true`（9 个文件的 size/mtime_ns/SHA-256 全部不变）。

### 关键裁定（详见报告 §6/§7）

- Live `android-SysUISdk` 无 generator marker → legacy/unmarked；其 `android.jar`
  内容是 canonical 输出的严格超集（多 1,266 个 legacy 条目），不可由当前冻结生成器
  map 复现；`framework.aidl` 与 canonical 逐字节相同、`core-for-system-modules.jar`
  内容与 canonical 相同。
- 候选删除 8 个文件共 163,149,374 字节（~155.5 MiB）；其中 `android.jar.bak-20260821-
  011116/013303` 的冗余性依赖 live primary 继续存在（caveat A 已在报告中披露）。
- 保留建议：仅 `android.jar.bak-20260813-210816`（唯一内容）。

## Prohibition

遵守：未删除、未重命名、未 chmod/touch/replace/写入任何 SDK/AOSP 文件；临时产物
仅在 `/tmp/task047-*`；未运行任何 Gradle 任务。

## Error-count evolution

Not applicable. No build or source change was allowed, and no Gradle task was run
(实际未运行任何 Gradle 任务).

## Open questions

Deletion remains unapproved. Candidate list for the separate irreversible decision
(8 files, 163,149,374 bytes): `android.jar.orig`, `android.jar.bak-20260821-011116`,
`android.jar.bak-20260821-013303`, `core-for-system-modules.jar.orig`,
`core-for-system-modules.jar.bak-20260813-210816`,
`core-for-system-modules.jar.bak-20260821-011116`,
`core-for-system-modules.jar.bak-20260821-013303`, `framework.aidl.bak-preaidl`.
Retain recommendation: `android.jar.bak-20260813-210816` (unique historical snapshot,
44,848,587 bytes). Caveat A (rows 3–4 redundancy depends on the live primary remaining
in place) must be presented to the user together with the candidate list.
