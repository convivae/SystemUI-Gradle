# Task 062 — libs/ 全量产物审计（只读研究，为大扫除供证据）

## Goal

产出 `libs/` 目录每一个产物的**引用图审计表**，为大扫除（删除孤儿文件）提供逐项证据。
只读研究：**禁止 Gradle 构建、禁止修改任何文件**（唯一可写：报告文件本身）。

## Background

- 项目演进多轮（task 001–061），libs/ 下产物几经更替：task 057 把 14 个 flags jar
  合并为单一 `libs/systemui-aconfig-flags.jar`；task 059 把 4 族 AAR 从本地 Maven 改为
  `libs/aars/` 直接消费；疑似有旧文件残留未被引用。
- 依赖引入规则见 AGENTS.md §1.5（三层策略）与 §3.2（libs/ 交付规则）。
- tracinglib-platform.jar 溯源已关闭（chief，2026-08-26）：AOSP Soong 模块
  `frameworks/libs/systemui/tracinglib/core`（module name `tracinglib-platform`），
  纯代码无 res（demo/ 的 res 不属于它），jar 形态正确，保留。

## Inventory scope（全量，一个不漏）

- `libs/*.jar`（根目录，约 28 个）
- `libs/prebuilts/**`
- `libs/aars/*.aar`
- `libs/maven/**`（本地 Maven 仓：每个 group/artifact/version 下的 aar/pom）

## 对每个产物回答（表格列）

1. **路径 + 大小 + sha256 前 8 位**
2. **WIRED?** — 被哪些 `*.kts`/`*.toml`/`*.flags` 引用（grep 证据：文件:行）。
   注意间接引用：catalog alias（`libs.versions.toml` 的 alias → 各 module 的
   `libs.xxx` 引用）；`fileTree`/`files("libs/...")` glob。
3. **若 WIRED**：消费者模块列表（哪个 module 的哪个 configuration）。
4. **若 ORPHAN**：git 引入 commit（`git log --follow -- <path>` 最早一条）+
   疑似被取代事件（如 task 057 合并、task 059 迁移）。
5. **判定**：`KEEP` / `DELETE-CANDIDATE` / `UNCERTAIN`（UNCERTAIN 必须写明缺什么证据）。
6. **官方 Maven 等价物**（规则 §1.5 要求回查）：该产物是否已有
   Google Maven/MavenCentral 官方坐标可替代（写坐标或"无"）。网络可用
   阿里云镜像 `https://maven.aliyun.com/repository/google/...` 查询。

## 特别核查点（chief 预扫的疑点，需证实/证伪）

- `libs/` 根下 11 个分散 flags jar（device-state / launcher3 / notification /
  settingslib×4 / systemui-flags / systemui-shared-flags / wifi / wm-shell 等）：
  task 057 合并后是否已全部孤儿？合并 jar 的 wiring 在 `SystemUI-core/build.gradle.kts`
  L250 附近，逐个核对旧 jar 是否还有任何引用。
- `libs/aars/` 实际清单 vs task 059 的 4 族直接消费集（WifiTrackerLib、iconloader、
  setupcompat、LowLightDreamLib）——有没有第 5 个文件残留。
- `libs/maven/` 现存哪些 artifact 树，各自是否仍被 catalog/wiring 引用
  （预期保留：animationlib、SettingsLib 族、WindowManager-Shell；4 族已被 task 059 删除）。
- `libs/prebuilts/` 下除 tracinglib-platform.jar 外还有什么。
- `android_module_lib_stubs_current.jar`、`SystemUI-tags.jar` 等早期产物的引用状态。
- `compilelib-debug.jar` / `compilelib-release.jar` 的 wiring（AGENTS.md §3.1 说
  compilelib → debug/release JAR，核对实际引用）。

## Output

报告 `docs/architecture/2026-08-26-libs-artifact-inventory-audit.md`：
完整审计表 + DELETE-CANDIDATE 清单汇总（按风险排序）+ 官方等价物替换机会清单。
一行 `docs/orchestration/log.md`。本地 commit 报告（英文 message，不 push）。
最终消息按 worker-contract 四段式。

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
