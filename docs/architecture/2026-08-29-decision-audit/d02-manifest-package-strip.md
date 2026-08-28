# D2 — SystemUI-application manifest 剥除 `package="com.android.systemui"` 属性（CONV_DEL）

status: done
判读: **符合**（授权 + 机制 + 对账齐全；brief 对 AGP 行为的表述有轻度夸大但结论方向正确）

## 背景与决策原文

AOSP-17 的完整 manifest（1338 行，`SystemUI-application/src/main/AndroidManifest.xml`）根标签
带 `package="com.android.systemui"`。AGP 对该属性的检查（CHECK_IF_PACKAGE_IN_MAIN_MANIFEST）：

- 值 ≠ namespace → RuntimeException（硬错）；
- 值 == namespace → 仅警告。

task072 brief「chief 预核实事实」第 3 条指示："**必须剥除**并按 ADR 0004 用 CONV_DEL 标记"
（brief 原文表述为 "AGP 9 拒绝源 manifest 的 package 属性"；issue §3.3 细化为"≠ 硬错、= 警告，
仍按 brief 指示剥除"）。

决策（commit `80be3e58`，Task 072 P3）：在 manifest prolog 区（根元素之前，因为 XML 注释不能出现
在标签内部）加 CONV_DEL 块，把 `package="com.android.systemui"` 一行保全为注释；
namespace 由 `SystemUI-application/build.gradle.kts` 承担（同值 `com.android.systemui`）。

## 决策链

| 环节 | 证据 |
|---|---|
| brief 授权 | task072 brief §"chief 预核实事实"#3（点名单文件单属性，Forbidden Paths 中唯一例外） |
| 执行 | commit `80be3e58`（含本文首 CONV_DEL 块；现文件 L22–28 可见） |
| 核对 | issue §CONV 对账表（唯一一项未进 alignment MODIFIED——APP_TOP_FILES 只验存在性不比字节，人工对账） |

## 证据链

1. **实际字段**：`SystemUI-application/src/main/AndroidManifest.xml` 开头 CONV_DEL 块
   （BEGIN/END 包 `<!--     package="com.android.systemui" -->`，reason 含 AGP 行为说明与撤回指引）；
   namespace 在 `SystemUI-application/build.gradle.kts`（同值 com.android.systemui）。
2. **AGP 行为分级**：issue §3.3 与 build 文件注释一致（CHECK_IF_PACKAGE_IN_MAIN_MANIFEST）。
3. **语义等价**：值 == namespace → 剥属性后 merger 展开的相对名与展开前完全相同
   （XmlAttribute 按文档 namespace 展开，见 d11 的 merger 源码依据）；无行为变化。
4. **对齐工具覆盖缺口已披露**：APP_TOP_FILES 只验存在性，不比字节（issue §CONV 对账注记）。

## 备选路径

1. **保留 package 属性**（==namespace，仅警告）：零字节差；被 brief 指示否决（16 时代 app manifest
   已剥除的先例 + 每构建持久警告噪声）。
2. **既然 ==namespace，不修**：同 1。
3. **CONV_MOD 假改 namespace 绕道**：更糟（制造行为差异）。
4. 参考项目 CarSystemUIGradle：app manifest 保留 `package="com.android.systemui.car"`（JD MOD 块），
   但该项目 manifest 归属在 `:app`（app 级）且需双编译（bp + Gradle，`--rename-manifest-package`），
   与本项目 library manifest 情形不完全可比。

## 优劣分析

优点：语义恒等（无行为差）、可逆（注释保字）、授权颗粒度精确（单文件单属性）；对齐工具的覆盖
缺口被诚实标注为人工对账而不是粉饰。
缺点：因值 == namespace，纯"风险评估"下剥除不属必要条件——剥与不剥只差构建期警告；在这个意义上
这是"清理性打标"而非"阻塞性打标"（与 D1/D3 的硬阻塞性质不同），授权成本来源是 brief 本身。

## 判读与建议

判读：**符合**——性质是"brief 点名的可逆清理"，授权—执行—对账链完整，与 task070/E3 机制一致。

建议：**保持**；若用户希望最小化 CONV 面，可选择撤销此打标（恢复 package 属性、接受每构建一条警告）
——两者代价都极小，建议留给用户裁决一次。

## 开放问题

- D2 是"brief 指示下的可逆清理"而非硬阻塞修复；用户是否希望维持剥除（静默警告持续每月构建），
  还是撤回打标恢复属性？
</content>
