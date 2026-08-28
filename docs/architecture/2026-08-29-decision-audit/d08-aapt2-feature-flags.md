# D8 — 编译期 aapt2 转发 `--feature-flags @file` + 新产物 `libs/systemui-aconfig-flags.txt`（task073，commit `6e66a0ea`）

status: done
判读: **符合**（附一项开放问题：flags 覆盖只含 systemui 包）

## 背景

17 重对齐后，AGP mergeDebugResources 输出的 values XML 里出现 `android:featureFlag` 引用
（flag 名例如 `com.android.systemui.dream_overlay_updated_ui`）。AGP 内部的 kotlin aaptcompiler
端口不校验 featureFlag；project 里**唯一** AGP 外的 aapt2 调用点是
`tools/patch_androidprv_merged_resources.py` 的独立 `aapt2 compile`，它**校验** flags 并报
 "Resource flag value undefined"，此即为 task073 编译循环 R5 的阻塞点（issue §4 批次 2）。

## 决策

1. 此独立 compile 调用显式插入 `--feature-flags @<file>`（与 Soong 完全同机制）；
2. 值文件 = Soong `com_android_systemui_flags` aconfig-flags.txt 产物**逐字节拷贝**检入
   `libs/systemui-aconfig-flags.txt`（tier② AOSP 产物，非自造）；
3. AGP 9.3.1 的 link 侧仍无 feature-flags 通道（字节码级实证已被 issue 采录，见 d03），所以
   link 侧经 D3 的对照处理，不在本决策范围。

## 证据链

- **错误实证**：task073 issue §4 批次 2 的错误日志摘录（merge-resources 不规律报 flag
  undefined 在独立 compile 侧）。
- **Soong 行为对照源代码**：`build/soong/java/aapt2.go:107-108` 在 compile 时追加
  `--feature-flags @<path>`；link 在同文件 L305-307 同样追加。
- **bp flags 包集**：17 SystemUI-res bp `flags_packages [android.app.flags-aconfig,
  android.net.platform.flags-aconfig, com_android_systemui_flags, uilatencystats_flags]`
  （Android.bp:429-434）——即 Soong 用的是 **多 flags 文件**，但本任务只转发 systemui 包一文件；
  见开放问题。
- **产物真实性**：`sha256sum` 于 `libs/systemui-aconfig-flags.txt`（282 行）与
  `out/soong/.intermediates/.../com_android_systemui_flags/aconfig-flags.txt` 均为
  `031f4e80…`，字节一致（实测）。
- **改动实体**：commit `6e66a0ea`，`tools/patch_androidprv_merged_resources.py` +61 行——默认
  路径常量 `_DEFAULT_FEATURE_FLAGS`、互斥 CLI `--feature-flags/--no-feature-flags`、文件缺失
  时快失败（exit 2）、compile 调用插参；
- **测试**：`tools/tests/test_patch_androidprv_merged_resources.py` +109 行，20 项测试过、全
  suite 303 + 121 过、`check_source_alignment --strict exit 0`。

## 备选路径

| 路径 | 否决理由 |
|---|---|
| Soong-侧预处理 flat 交付 | 构建产物不可确定性复现，违反 libs/产物"deterministic / 可重放"要求 |
| AGP 官方能力 | 17 调查实证 AGP 9.3.1 无此 DSL 与命令行参数（issue §4 批次 2 字节码检查）——不可得 |
| `additionalParameters` 追加（16 时代 task009 先例） | 只作用 final link，不解独立 `aapt2 compile`，且包区覆盖也不开门 |
| CONV 删 values XML 中的 `android:featureFlag` 引用 | 破坏 Soong 运行时过滤语义，违反规则 R/ADR 0004 |

所选（转发 + tier② 产物检入）是**侵入度最低且与 Soong 一比一**的方案。

## 优劣分析

优点：Soong parity（机制/命令形式/产物源均同）；AGP 无法提供时才自造（不是无谓重发明）；
产物真实性 hash 可验证；工具 fast fail 而非黑盒报错。
缺点：白名单目前**只有 `com_android_systemui_flags` 一包**——将来 res/product/values 若引用
其他包 flag（现 bp 里有 `uilatencystats_flags`、`android.app.flags-aconfig`、
`android.net.platform.flags-aconfig`），独立 compile 将再度报缺且需扩展工具（或给每包开
flags 文件目录）；此项未在 issue 或 spec 注释内显式记入（属误差的"例外开放项"）。

## 判读与建议

判读：**符合**——决策实体（转发规则 + 来源+测试）可以在 6e66a0ea、SPEC 注释、 bp 与产物 hash
四处交叉核对。

建议：
1. **保持**；
2. 把"flags 仅覆盖 `com_android_systemui_flags`"以及"若其他包 flag 入 res, 需扩展 flags 文件
   或多文件转发"记到 commit/工具 docstring 末尾或 issue §4 尾部（现为 open 项，未见尾随印反文记录）；
3. 不做 Soong 侧多 flags 文件的全量切换——按需求驱动。

## 开放问题

- flags 覆盖扩展何时发生、如何 form（multiple `--feature-flags` 参数? aapt2 compile 是否支持
  多文件?）——给将来 task 的发现/实验项；
- present assembly 状态：C4b 其余阻塞（余下的 5 个 Kotlin `e:` 和 20 个 link color error，
  issue §4 批注"全部可归因于 SysUISdk 重建被挂"）由 D12 依例处理，不涉及本决策。
</content>
