# product variant 首个 CONV_DEL 应用

**日期**：2026-08-07
**状态**：执行中
**关联**：[ADR 0004](../adr/0004-conv-markup-and-alignment-discipline.md)、[conv-markup-spec](./2026-08-07-conv-markup-spec.md)
**前置条件**：阶段一已完成；对齐 0/0/0/0、strict exit 0、27 tests PASS

## 背景

`./gradlew :SystemUI-core:compileDebugKotlin` 首个失败为 `:SystemUI-res:packageDebugResources`：

```
Error: Found item String/inattentive_sleep_warning_message more than one time
```

根因：AOSP `res-product/values/strings.xml`（与项目字节一致，MODIFIED=0）用 `product="tv"`/`"tablet"`/`"device"`/`"default"` 属性区分设备变体。Soong 理解该属性，AAPT2 不支持，把多变体当 default 重复。

## 调研结果

`SystemUI-res/res-product/` 共 86 个 `.xml` 文件，全部含 `product="..."` 属性。分布：

| product 值 | 出现次数 | 处理 |
|-----------|---------|------|
| `default` | 1807 | **保留** |
| `tablet` | 1463 | **CONV_DEL 注释掉** |
| `device` | 688 | **CONV_DEL 注释掉** |
| `tv` | 86 | **CONV_DEL 注释掉** |

非 default 变体共 2237 处，涉及 19 个不同 string name。已验证**全部 19 个 name 都有 `product="default"` 变体**（见下方清单），删除非 default 不丢任何定义。

## 改动清单（19 个 string name）

所有 name 在 `res-product/values/strings.xml` 及 ~40 个 locale 目录的 `strings.xml` 中出现。每个 name 的非 default 变体（tv/tablet/device）将被 CONV_DEL 注释：

| string name | tv | tablet | device | default |
|-------------|----|--------|--------|---------|
| finder_active | 0 | 1 | 0 | 1 |
| global_action_lock_message | 0 | 1 | 1 | 1 |
| high_temp_dialog_message | 0 | 1 | 1 | 1 |
| high_temp_notif_message | 0 | 1 | 1 | 1 |
| high_temp_title | 0 | 1 | 1 | 1 |
| inattentive_sleep_warning_message | 1 | 0 | 0 | 1 |
| keyguard_missing_sim_message | 0 | 1 | 0 | 1 |
| kg_failed_attempts_almost_at_erase_profile | 0 | 1 | 0 | 1 |
| kg_failed_attempts_almost_at_erase_user | 0 | 1 | 0 | 1 |
| kg_failed_attempts_almost_at_login | 0 | 1 | 0 | 1 |
| kg_failed_attempts_almost_at_wipe | 0 | 1 | 0 | 1 |
| kg_failed_attempts_now_erasing_profile | 0 | 1 | 0 | 1 |
| kg_failed_attempts_now_erasing_user | 0 | 1 | 0 | 1 |
| kg_failed_attempts_now_wiping | 0 | 1 | 0 | 1 |
| media_transfer_playing_this_device | 0 | 1 | 0 | 1 |
| security_settings_sfps_enroll_find_sensor_message | 0 | 1 | 1 | 1 |
| thermal_shutdown_dialog_message | 0 | 1 | 1 | 1 |
| thermal_shutdown_message | 0 | 1 | 1 | 1 |
| thermal_shutdown_title | 0 | 1 | 1 | 1 |

**合计**：tv 1 + tablet 19 + device 9 = 29 处/string-name/文件。考虑 86 个文件（含 locale 变体），总注释数约 2237 处。

## 处理方式（CONV_DEL）

按 ADR 0004，用 Python 脚本批量给每个非 default product 变体加 CONV_DEL 块。XML 格式（三段独立 `<!-- -->` 注释）：

**注释前**（原 AOSP 行）：
```xml
<string name="inattentive_sleep_warning_message" product="tv">The Android TV device will soon turn off; press a button to keep it on.</string>
```

**注释后**：
```xml
<!-- CONV_DEL BEGIN: 移除 tv 变体，AAPT2 不支持 product 属性（见 docs/issues/2026-08-07-product-variant-conv-del.md） -->
<!-- <string name="inattentive_sleep_warning_message" product="tv">The Android TV device will soon turn off; press a button to keep it on.</string> -->
<!-- CONV_DEL END -->
```

AAPT2 把三段 `<!-- -->` 全部当注释忽略，原 tv 标签失效；原内容以注释文本保留在文件里，可追溯可撤回。

## 验收标准

1. 脚本运行后，`res-product/` 下无非 default product 变体是**有效标签**（都被 `<!-- -->` 包裹）
2. `check_source_alignment.py`：RES-MODIFIED 清单 = 本次改动的 86 个文件，逐条与 issue 对账
3. `:SystemUI-res:packageDebugResources` 成功（重复资源错误消除）
4. 所有 19 个 string name 的 `product="default"` 变体仍为有效标签（未被注释）

## 待办

- [x] 写 Python 脚本 `tools/markup_product_variants.py`（符合 ADR 0002）
- [x] 脚本单测（8 个，含多行标签、幂等、dry-run）
- [x] 运行脚本批量加 CONV_DEL（86 文件、2237 处）
- [x] 跑对齐，对账 RES-MODIFIED 清单（86 文件一致）
- [x] 跑 `:SystemUI-res:packageDebugResources` 验证（BUILD SUCCESSFUL）
- [x] 顺便解决 B2（processor kotlin stdlib）：移除手动 annotationProcessorPath，用 Gradle 自动解析传递依赖
- [x] 新 first boundary：`:SystemUI-shared` 4 个 `Thread.getUncaughtExceptionPreHandler` framework @hide 错误
