# D4 — clocks-common / floatingmenu manifest 保留 package 属性（不复用 application manifest 处理）

status: done
判读: **符合**

## 背景与决策原文

两个新增资源模块的 AOSP 源 manifest 携带 package 属性：

| 模块 | manifest | package 属性 | namespace（build 文件） |
|---|---|---|---|
| `:SystemUI-clocks-common` | `SystemUI-clocks-common/AndroidManifest.xml:19` | `com.android.systemui.customization.clocks` | 同值（build.gradle.kts:16-17） |
| `:SystemUI-accessibility-floatingmenu-res` | `SystemUI-accessibility-floatingmenu-res/AndroidManifest.xml:2` | `com.android.systemui.accessibility.floatingmenu` | 同值（build.gradle.kts:12-13） |

决策（task072 接线时）：**不做 D2 式 CONV_DEL 打标，保留属性原样**。理由（task072 issue §接线步骤
+ build 文件注释）：值 == namespace → AGP CHECK_IF_PACKAGE_IN_MAIN_MANIFEST 仅警告不硬错；
剥除需 CONV 打标，而本批授权的唯一例外是 application manifest 的 package 属性——扩到另外两个
manifest 就超出 brief 授权。

## 决策链

| 环节 | 证据 |
|---|---|
| 来源落实 | 两份 manifest 由 task070 `bdf2dba5` 以 MISSING 补齐从 AOSP 拷贝（对齐 0 前提下，无字节改动） |
| 决策记录 | `SystemUI-clocks-common/build.gradle.kts:16-17`、`SystemUI-accessibility-floatingmenu-res/build.gradle.kts:12-13` 注释（"manifest 保留 package 属性 → AGP 仅警告，值与 namespace 相等"）；task072 issue §3.3 "clocks-common / floatingmenu 两 manifest 保留 AOSP 原始 package 属性（namespace 同值 → 仅警告），未打 CONV" |
| 副作用 | 每次构建两条 CHECK_IF_PACKAGE_IN_MAIN_MANIFEST 警告（已知噪声） |

## 证据链

1. **两 manifest 与 AOSP 来源一致**（bdf2dba5 的 MISSING 补齐批，无后续改动；
   `git log -- <files>` 仅 bdf2dba5 一次）。
2. **AGP 行为分级**：值 == namespace → 仅警告（aapt2/AGP namespace 检查行为，与 D2 issue §3.3 同一
   机制）。
3. **AGP unique-namespace**（`MergeManifests` 的 ENFORCE_UNIQUE_PACKAGE_NAMES）只比较
   **Gradle namespace**，不受 manifest package 属性影响——issue §3.1 已实证；保留 属性 不影响
   merger R/rename 行为。

## 备选路径

1. **同一打标**（D2 机制，CONV_DEL 剥属性）：静默警告；需扩 brief 授权——D2/D4 不一致的根本原因。
2. **保留属性**（所选）：零打标、零字节差；代价 = 每构建两条警告。
3. **把 namespace 改成与属性不同**：制造不和，违 AGP namespace 约定，否决。

## 优劣分析

优点：最小权限（授权唯一例外没被扩用）；字节保全完全（无任何 AOSP 改动）；与 assembly 行为无关
（package 属性在 library 模块只影响警告）。
缺点：与 D2 的处理不一致（同源 AOSP manifest 两种处理并存）；每构建两条警告（可接受；
issue 已记录）。

## 判读与建议

判读：**符合**——这是对 brief 授权纪律的 *遵守* 而非规避（宁可保留警告也不扩自授权）。

建议：与 D2/D3 一起在最后向用户裁定一次"全局 manifest package 属性口径"（三处统一打标或全部保留）；
若用户选全保留：D2 的 CONV_DEL 可回撤。

## 开放问题

- （与 d02 同一开放问题）manifest package 属性的全局口径。
</content>
