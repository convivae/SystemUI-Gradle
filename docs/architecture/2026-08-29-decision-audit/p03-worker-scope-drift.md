# P3 — worker 在 brief 外扩范围：何时算"记录在案的合理漂移"、何时算越权

status: done
判读: **可接受但需补记录**（D6/D7 属合理漂移；D8/D3 边界已薄，分别见 p01/d03 与 d08）

## 背景与决策原文

worker contract（skill 与 CHARTER Part 7）："Stay inside the brief. Anything the brief does not
cover is out of scope — report it instead of expanding scope yourself."

task073 brief 同时内建了一条"误差驱动循环"扩权：步骤 P2 "编译循环：按错误分类逐个根因处理
（一次一个根因）"，编译错误处理纪律表给出错误类别 → 处理动作的映射（缺 tier② 产物 → 扩展
tools 脚本产出；需要改 src → CONV 打标…）。因此 brief 边界在现实中是"枚举 + 类别"两层。

三个被点名的扩范围事件：

| 事件 | brief 内预计形态 | 实际落地 | commit |
|---|---|---|---|
| ace 拆双 AAR | #2 "personalcontext_ace_visualizer = tier② AAR"（单数） | visualizer（+ace_common 类闭包）与 client 两个 AAR | `e6c59677` |
| wmshell-shared 升版本 | brief 未提 | AIDL 19 类并入 AAR + catalog 2.0.0→2.0.1 | `74b88acb`（+对账测试 `38cd4c4b`）|
| aapt2 --feature-flags 通道 | brief 未提 | 改 `tools/patch_androidprv_merged_resources.py` + 新产物 `libs/systemui-aconfig-flags.txt` | `6e66a0ea`（D8 专审） |

## 决策链

| 环节 | 证据 |
|---|---|
| ace 双 AAR 理由 | issue §3 "ace 拆双 AAR" 段：client 自有 R namespace `com.android.personalcontext.ace.client`（`AceEmbeddedSurfaceViewCompat` 引用 client R）；visualizer 公有签名引用 client 的 `ClientActionInsight`；单 AAR 只能承载一个 manifest package/R namespace；三 Kotlin jar 互不相交已验证 |
| wmshell 升版本理由 | issue §4 批次 1：17 bp 里 `WindowManager-Shell-shared` static_libs `WindowManager-Shell-shared-aidls`；AGENTS.md §3.2 规则 4"内容变化必须升坐标…禁止同版本原地覆盖"——升 2.0.1 是规则义务而非自由选择 |
| D8 理由 | issue §4 批次 2：AGP 9.3.1 `AaptV2CommandBuilder` 无 feature-flags 参数（字节码级实证）；Soong 用 `--feature-flags` 传值；编译侧独立 aapt2 compile 是唯一阻塞点 |
| 评审状态 | task073 至今无 chief 评审条目（log 只到 L305 的 task072）——上述漂移全部"未评审" |

## 证据链

1. ace 双 AAR 各证据点可复核：AAR 分别在 `libs/aars/personalcontext_ace_{visualizer,client}.aar`
   （commit `e6c59677`）；build 文件注释给出同样理由（`SystemUI-core/build.gradle.kts:245-249`）。
2. wmshell 升版：catalog 现存 2.0.1 版本；升版后又有 `38cd4c4b` 修测试断言——说明漂移有
   连锁成本但仍属"有对账"的漂移。
3. D8 新产物 `libs/systemui-aconfig-flags.txt` 来源被标注为 Soong `com_android_systemui_flags`
   产物字节拷贝（sha256 031f4e80…，issue §4 批次 2），符合 tier② 产物规则。
4. worker 逐条在 issue §3/§4 记录"为什么扩"，不是静默扩。

## 备选路径

1. **逐项 REDLINE 上报**（contract 字面）：任一 brief 外判断都停工等 chief —— 编译循环停滞；
   ace client 的拆分会单独耗一轮往返。
2. **误差驱动循环内的有限扩权**（brief 实际形态）：扩限在"错误类别映射表可归属 + 全部入
   issue 对账 + 不触红区"三条件 —— D6/D7 满足；D8 触及"新构建通道"（产品决策面，规则 H.5 附近）。
3. **事后打包上报**（本审计即其载体）。

## 优劣分析

优点：漂移全程可溯（issue + commit + build 注释三层）；规则义务型漂移（升版）不需要另批，
worker 选择升版而非原地覆盖**遵守** AGENTS.md §3.2.4。
缺点：误差循环扩权是类别级授权，同样的"类别大范围"模式在 CONV 上已造成 P1 问题；扩与越权的
区分只能靠 worker 自律 + 事后评审，而 task073 评审尚未发生，窗口仍开着。

## 判读与建议

判读：**可接受但需补记录**——D6/D7 属记录在案的合理漂移（有类别归属、有理由、有对账）；
越权边缘的是 D8/D3（已各设专审：d03/d08/p01）。

建议：
1. task073 评审时，chief 按本文档清单（ace 双 AAR / wmshell 2.0.1 / D8 / D3）逐项核销而不是
   只看 build 结果。
2. 给 brief 的误差循环扩权写明三条件（类别归属 + issue 对账 + 不触红区），让"合理漂移"有
   明文化判据。

## 开放问题

- 无（归入 d06/d07/d08/d03 的各自裁决点）。
</content>
