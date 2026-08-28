# D12 — SysUISdk 生成器桥接碰撞(UnsupportedAppUsage, turbine vs javac 字节差异)——当前挂起(task073)

status: done(决策本身待定，本文提供方案分析与推荐)

## 背景

task073 编译闭环剩 1 类阻塞：SysUISdk 未重建——它解锁 **5 个 Kotlin `e:` + 20 条 link 颜色资源
错误**(两组同根因,见 task073 issue §4)。解除路径 = 跑 
`python3 tools/build_sysuisdk.py --aosp-root /home/conv/myspace/aosp`(chief 已批准重建, 2026-08-29)。
而生成器运行时抛:

```
bridge collision: target entry android/compat/annotation/UnsupportedAppUsage$Container.class
differs from the approved source bytes
```

root cause(本审计独立复核):

- 17 树 framework.jar(`out/soong/.intermediates/frameworks/base/framework/android_common/
  turbine-combined/framework.jar`)新增内嵌
  `android/compat/annotation/UnsupportedAppUsage{,$Container}.class`(turbine 字节)。
- 桥接源 `unsupportedappusage.jar` 是同一模块的 linux_glibc_common **javac** 产物(生成器
  `AOSP_INPUT_RELPATHS["unsupportedappusage_jar"]`,build_sysuisdk.py L73-76)。
- 同源同 API、不同编译器字节——javap surface 完全一致,sha1 不一致(实测,
  固化的证据见 task073 issue §4「生成器自身防护拦截」表及本审计同步 javap 复核)。

为什么生成器拦截本身是 by-design:

- 生成器 docstring L19 已有 "The aggregate framework turbine JAR is master over duplicate
  stock SDK class entries"——这是 base-jar / framework 层的覆盖 invariant。
- 但桥接注入处(build_sysuisdk.py L353-359)的 fatal collision check 是 ADR 0006
  明确要的防护:"collision 即重审、不得静默吸收新类"(ADR 0006「后果」第 3 条)。

独立复核数据(本审计直接 python3 调 build_sysuisdk):

- 39 条 BRIDGE_ENTRIES 与 framework.jar 的实际重叠**恰好 = 这 2 条**
  (`UnsupportedAppUsage{,$Container}.class`)--与 task073 issue §4 记录一致。
- framework.jar 与 unsupportedappusage.jar 的 `UnsupportedAppUsage` 类经 javap -v 表面
 比对(public / AnnotationDefault)一致,只字节不同。`/tmp/audit01/{fw-ua.txt,jv-ua.txt}`。
- framework.jar 与 unsupportedappusage.jar 的 `UnsupportedAppUsage` 类经 javap -v 表面
 
## 三个选案

| 选项 | 内涵 | 与 ADR 0006 invariants 的一致性 | 评价 |
|---|---|---|---|
| ① 桥接去重:从 `_UNSUPPORTED_APP_USAGE_ENTRIES` slice 删除这 2 条(→37 条断言更新);framework 聚合的同名类本就被 step 2 合入 | 维持"framework aggregate is master"invariant(docstring L19 已有同意思)的延伸;collision check 对其他 37 条继续致命 | **推荐**——最少侵入、语义最干净,所缺条目由真实 AOSP 制品提供 |
| ② 桥接优先覆盖(改 collision 语义允许同名不同字节) | 破坏"collision 即重审"invariant;以后上游制品变动会被静默吞掉 | 不推荐 |
| ③ 「重新采准 bytes」:保留 39 条但把期望字节改成 turbine 字节 | 把 inbound javac jar 与 turbine 字节强绑,不利追溯;产物语义变化需全套 regression 重测 | 不推荐 |

## 审计推荐(给 chief / user 的裁决素材)

**推荐选项 ①**——在生成器:

- 删除 `("unsupportedappusage_jar", _UNSUPPORTED_APP_USAGE_ENTRIES)` 切片与对应常量;
- `BRIDGE_ENTRIES` 断言由 39 → 37;
- `AOSP_INPUT_RELPATHS` 也把 `unsupportedappusage_jar` 移除(冻结映射由 8 输入 → 7 输入;
 与 ADR 0006 的可追溯 invariant 一起记录)。或「保留 8 输入、slice = 0」的等价 form
 由 chief/user 决定;
- regression test:终态 `android.jar` 中含这 2 条 UnsupportedAppUsage class(字节 = framework
 聚合的 turbine 副本)、API 与 javap 表面预期一致;collision 防护仍保持非空测试。

## 待 chief/user 裁决点

是否:**把 ADR 0006 的冻结映射改为 7 输入(删 `unsupportedappusage_jar`)**(推荐);
或者**保留 8 输入但消耗 slice = 0**(等价 form)。由 owner 决策哪一种记录方式。

## 关联

解除后,task073 剩余 **5 个 Kotlin `e:` + 20 条 link 颜色资源错误**(issue §4)由后续 phase
(或把 073 收官)继续验收。
