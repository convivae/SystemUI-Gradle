# D6 — ace 拆双 AAR（visualizer = viz+common 两 jar 合并；client 独立；task073 P1，commit `e6c59677`）

status: done
判读: **符合**（兼 "可接受但需补记录"：common/wrappers 未按 bp 独立拆成纯代码 jar 属偏离 1:1 镜像，但理由已记录在案）

## 背景与决策原文

17 SystemUI-core bp static_libs L574 `personalcontext_ace_visualizer`；
源码 import `com.android.personalcontext.ace.visualizer.{compat,connector}.*` 与
`common.wrappers.*`（SPEC 注释 L386-388）。

AOSP ace 的 soong 结构（`frameworks/libs/systemui/ace/.../Android.bp`，**非** packages/SystemUI
→ 规则 F tier② 产物）：

| soong target | 形态 | res | manifest namespace |
|---|---|---|---|
| personalcontext_ace_visualizer | android_library（KSP dagger2） | res/ | com.android.personalcontext.ace.visualizer |
| personalcontext_ace_client | android_library | clientsdk/compat/res | com.android.personalcontext.ace.client |
| personalcontext_ace_common | android_library（无 res） | 无 | （manifest 无 res，R 无实义） |
| personalcontext_ace_common_embeddedscroll | android_library（单文件） | 无 | 同上 |
| personalcontext_ace_common_wrappers | android_library（无 res） | 无 | 同上 |

决策（`e6c59677`）：打 **2 个 AAR** ——
- `personalcontext_ace_visualizer.aar`：visualizer Kotlin jar + ace_common Kotlin jar 合并
  （wrappers 类在 common Kotlin jar 里已含：AAR classes 包根实测含 `ace/common`、`ace/common/wrappers`、
  `ace/visualizer`）；res + R.txt + manifest 用 visualizer 的；
- `personalcontext_ace_client.aar`：client Kotlin jar 独立 AAR，包 client namespace
  （`AceEmbeddedSurfaceViewCompat` 引用 client R，故 client 必须独立 AAR——单 AAR 只能承载一个
  manifest package/R namespace）。

两个 AAR 均按"单 artifact、单 consumer（仅 :SystemUI-core）、骨架 POM、字节同一"Task 059 例外走
直接 AAR（不进 maven/catalog，SPEC 注释 L392-393、L411-412）。

## 决策链

| 环节 | 证据 |
|---|---|
| bp 依据 | SystemUI-core bp static_libs L574（visualizer）；visualizer bp static_libs [common, client]；client bp static_libs [common, common_embeddedscroll] |
| res/R namespace 实证 | AAR 字节实测：visualizer.aar manifest `package="com.android.personalcontext.ace.visualizer"` + res/drawable；client.aar manifest `package="com.android.personalcontext.ace.client"` + res/values/attrs.xml（declare-styleable）；SPEC L409-410 记"AceEmbeddedSurfaceViewCompat 引用 client R" |
| 非-SystemUI 定位 | `frameworks/libs/systemui/ace/**`（规则 F/tier② → 产物交付，**非**源码 module） |
| 执行/记录 | commit `e6c59677`；`tools/package_aosp_aar.py:394-423` SPEC 两份 + 理由注释；`SystemUI-core/build.gradle.kts:247-250` 直接 AAR 接线注释 |

## 证据链

1. `git show e6c59677`：libs/aars 两 AAR + SPEC + core build 接线 + issue 更新。
2. AAR 结构实测（unzip）：visualizer.aar classes.jar 包根 = visualizer + common + common/wrappers；
   client.aar classes.jar 包根 = client；两 AAR manifest、res、R.txt 与 SPEC 一致。
3. SPEC 的 KSP 注明"ksp-classes.jar 为空，Kotlin jar 即完整类集"（visualizer enable_ksp 的
   dagger 输出未随包——KSP 产物为空时成立；**未独立验证** ksp-classes 为空，开放验证）。
4. common_embeddedscroll 的单文件（EmbeddedScrollEvent.kt）被记入 SPEC 注释"同名覆盖"——
   common jar 已带该类，故未单独产物；**未独立验证** 类存在（开放验证——但仅一个数据类，
   缺失只在引用时暴露）。

## 备选路径

1. **单 AAR**（viz+client+common 合并）——R namespace 冲突（AAR 单 package），否决；
2. **3+ 产物**（common/wrappers/embeddedscroll 各自纯代码 jar）——最 1:1 镜像 bp，但让一个用户
  （core）交付 5 产物族，管理成本升高；我们已有"多个 owning Soong jar 合并 AAR"的 TraceurCommon 先例；
3. **local Maven（ADR 0001 标准路）**——多 consumer 才需要；当前单 consumer；
4. **所选**：2 AAR + common 类闭包并入 visualizer。

## 优劣分析

优点：满足 tier② 资源存在性规则（viz/client 均含 res → AAR；common 无 res 以类闭包并入含 res 同族
AAR，不违反"资源归属"）；命名空间与 Soong manifest 语义 1:1（两个 AAR = 两个真实存在 R namespace 的
target）；并包理由+先例+互不相交验证全部写进 SPEC 注释。
缺点：偏离 soong target ↔ artifact 1:1（5 target → 2 AAR）；若将来 client/common 出现独立 consumer
或 common 自身加 res，需要重新切分版本（届时按 §3.2 规则 4 升坐标）；未验证 KSP 空输出与
EmbeddedScrollEvent 类始终存在——留作低优先验证项。

## 判读与建议

判读：**符合**——技术判据（单 AAR 单 namespace、含 res 用 AAR、无 res 类闭包并入同族 AAR、单 consumer
直接 AAR）每条都有 bp/字节证据；扩范围由 issue 记录在案（见 p03）。

建议:**保持**;把“5 soong target → 2 AAR”的合并理由同时记进 issue §3（当前只在 SPEC 注释，
干读 issue 时看不到全局形态）。

## 开放问题

- KSP 输出（ksp-classes.jar 为空）与 EmbeddedScrollEvent 类在 common jar 的两个"已知断言"未在
  编译链验证；C5 release 验证时若报缺类，先查此处。
</content>
