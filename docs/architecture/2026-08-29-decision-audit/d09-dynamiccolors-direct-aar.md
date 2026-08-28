# D9 — dynamiccolors 直接 AAR 走 Task 059 例外（task072，commit `452c9f6c`）

status: done
判读： **符合**（开放项：AGENTS.md §3.2 例外清单仍为 4 族）

## 事实

| 项目 | 值 | 来源 |
|------|----|------|
| soong target | `dynamiccolors` (res-only android_library) | AOSP `frameworks/libs/systemui/dynamiccolors` |
| namespace | `com.android.systemui.dynamiccolors` | manifest |
| static_libs 被引 | 17 SystemUI-res bp L425 | AOSP |
| consumer | 仅 `:SystemUI-res` | core build 未引 |
| 交付 | 1 个 AAR，`files()` 直引，无 maven/catalog | commit `452c9f6c` |

## 证据

- `libs/aars/dynamiccolors.aar`：manifest `package="com.android.systemui.dynamiccolors"`（unzip 核）；res/ 2 条
- `tools/package_aosp_aar.py:373-385`（SPEC 注释：res-only, Task 059 例外）
- `SystemUI-res/build.gradle.kts:50`：`files("libs/aars/dynamiccolors.aar")`
- `gradle/libs.versions.toml` 无 `systemui-dynamiccolors`
- `AGENTS.md` §3.2：仅 4 族清单（dynamiccolors 未在字面）

## 备选

| 路径 | 结论 |
|------|------|
| local maven | 多 consumer 才需要，Task 059 例外成立 → 不选 |
| 并入 SystemUI-res | 违 resources owner 原则 |
| CONV 同名资源 | 违 rule R |

## 判读与建议

结论：**符合**。机制与 E2 审查的 precedent 同型；records on spec + issue + build 里可被回溯。
开放：AGENTS §3.2 例外清单扩到 5 族（user 批准、红区文档）。

## 开放问题

- 判据制 vs 清单制：AGENTS §3.2 的例外段以"单 artifact、单 consumer、骨架 POM、字节退中性"
  判据扩清单，还是保留字面 4 族？由 user 裁决。

