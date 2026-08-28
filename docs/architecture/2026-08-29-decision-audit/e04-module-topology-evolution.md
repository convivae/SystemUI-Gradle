# E4 — 13-module → 16-module 拓扑演变（含 SystemUI-application / clocks-common 创建决策）

status: done
判读: **符合**

## 背景与决策原文

两个阶段：

**阶段 A（AOSP-16 时代，22 → 13 modules）**：2026-08-06 重新审定模块边界
（`docs/architecture/2026-08-06-module-structure-audit.md` L25–46：当时 `settings.gradle.kts`
include 22 个 module，重审后收敛为 13 个），实施计划
`docs/superpowers/plans/2026-08-06-13-module-source-topology.md`，决策依据 ADR 0003
（`docs/adr/0003-app-module-aligns-aosp-bp.md`）决策 1："源码 owner 和依赖语义对齐 BP，
Gradle module 不与 target 1:1"——module 边界由真实 seam 决定（独立 R namespace、
多消费者、外部 API、处理器/AIDL 工具链、防依赖环）。执行 commit 链含
`828923fb`（13 modules scaffolded）等。

目标 13 module（module-audit §一清单）：
app / core / res / common / animation / plugin-core / plugin-processor / plugin / unfold /
customization / shared / shared-biometrics / compose。

旁注：早期的 `:SystemUI-monet` 在此次审定中**移除**——monet 源码位于
`frameworks/libs/systemui/monet`（非 `packages/SystemUI`），按规则 F 不得源码复制
（module-audit L106、L411：不能源码化，改 AOSP 合并 JAR）；该审定同时说明参考项目
CarSystemUIGradle 的 7 模块不可照抄（module-audit L101–108："参考项目是'不要 1:1 映射 BP'
的证据，不是当前模块清单的权威来源"）。

**阶段 B（AOSP-17 重对齐，13 → 16 → 现 17 modules）**：切到 android-17.0.0_r1 后，task069 预研
`docs/architecture/2026-08-27-sysui17-realignment-panorama.md` §5 把拓扑变化以
**规则 H 用户决策点**列出 7 项，用户 2026-08-27 全部批准（task070 brief"已裁决事项"）：

| # | 17-bp 新 target | 用户批准方案 | 落地模块 |
|---|---|---|---|
| 1 | `application/src` 4 文件 + 1338 行完整 manifest（android_library "SystemUI-application"） | (a) 新模块（不并入 core） | `:SystemUI-application` |
| 2 | `customization/clocks/common`（21 src + res + 自有 manifest/R namespace） | (a) 新模块（不并入 customization） | `:SystemUI-clocks-common` |
| 5 | `AccessibilityFloatingMenu-res`（packages/SystemUI 内 res-only target，130 res + manifest） | res-only 源码 module | `:SystemUI-accessibility-floatingmenu-res` |

执行链：task070 (C3) 拷目录（commit `bdf2dba5`：1989 src + 577 res MISSING 补入，
含 application 4 src + 1338 行 manifest、clocks-common 21 src + res + manifest、
floatingmenu-res 130 res + manifest）；task072 (C4a) 注册 settings + 写三个
build.gradle.kts（commit `d1352d5d`）。随后 task073 P0 又增 `:SystemUI-utils-kairos`
（commit `4ac49993`，另审于 D5）→ 当前 settings 共 **17 个 include**
（实测：`git show HEAD:settings.gradle.kts | grep -c include` = 17；task072 基线
`452c9f6c^` = 13）。

## 决策链

| 环节 | 证据 |
|---|---|
| 16 时代 13-module 审定 | module-audit §一；plan 2026-08-06-13-module-source-topology；ADR 0003 决策 1 |
| 17 预研 | panorama §5 七项用户决策点（含三新模块两项建议 + floatingmenu 一项） |
| 用户批准 | task070 brief「已裁决事项（用户 2026-08-27 批准）」#1/#2/#5 |
| C3 拷贝 | commit `bdf2dba5`（task070 P3） |
| C4a 接线 | task072 brief「chief 预核实事实」#2/#4/#5；commit `d1352d5d` |
| kairos 增格 | task073 P0；commit `4ac49993`（D5 见附件） |

## 证据链

1. settings 计数：`git show 452c9f6c^:settings.gradle.kts` 13 includes → HEAD 17 includes。
2. 16 时代清单双 owner 一致：module-audit §一 与 `452c9f6c^` 版 AGENTS.md §3.1。
3. seam 判据适用：clocks-common 自有 R namespace `com.android.systemui.customization.clocks`
   （`SystemUI-clocks-common/build.gradle.kts` L10 注释 + manifest package 同值）；
   application 为 bp `android_library` 带 `manifest: "AndroidManifest.xml"`
   （17 主 bp L599–620，task072 issue §2 摘录）。
4. floatingmenu-res 的 tier 归属：soong target 定义在 17 主 `Android.bp` L415–427，
   属规则 S tier①（packages/SystemUI 内）→ 源码；task069 §5-5 曾建议 AAR，用户批准项
   改为 res-only 源码 module，与规则 S 文字一致。

## 备选路径

1. **新 target 并入既有模块**（application→core；clocks-common→customization）——ADR 0003 seam
   判据下两项都被列为 (b) 备选并否决：独立 manifest / R namespace 是真实 seam。
2. **floatingmenu-res 打 AAR**（task069 §5-5 原建议）——与规则 S 字面冲突
   （bp target 在 packages/SystemUI 下），被用户批准项取代。
3. **SurfaceEffects 源码 module**——被否（在 frameworks/libs 下，规则 F → AAR/JAR；
   task072 P0 产出 `libs/SurfaceEffects*Lib.jar`）。

## 优劣分析

优点：每次拓扑变化都先预研 + 用户裁决（规则 H 正确触发）；ADR 0003 seam 判据在 16→17
一致适用；计数可复验（settings include 数、对齐工具 strict 门）。
缺点：AGENTS.md §3.1 的 era 命名（"16-module 拓扑（17 后扩为 16）"）与 settings 当前
17 includes 已不同步——文档更新滞后于 kairos 落格。

## 判读与建议

判读：**符合**——三新模块创建属"规则 H 要求的产品决策先问用户"的正面执行案例。

建议：保持拓扑；C4b 收尾时把 §3.1 模块图补上 kairos（对齐 settings 实况），作为
task074 文档任务完成。

## 开放问题

- 无。
</content>
