# Task 059 — 4 个单 consumer AAR 族：本地 Maven → 直接 AAR

- 日期：2026-08-25
- 任务简报：`docs/orchestration/tasks/059-aar-direct-consumption-migration.md`
- 决策来源：Task 043 audit（`docs/architecture/2026-08-21-gradle-native-current-state-audit.md` §10）8 个
  NOT APPROVED packet 中，用户 2026-08-25 对其中 6 个作出裁定：
  WifiTrackerLib / iconloader / setupcompat / LowLightDreamLib **迁移为直接 AAR**；
  animationlib **保留本地 Maven**（多模块共享，catalog alias 是标准 Gradle 机制，按设计关闭）；
  SettingsLib 伞形 AAR 实验**永久关闭**（17 个 per-target AAR 保持不动）。
  其余 2 个：AssumeTrueForR8 维持 NOT APPROVED（Release 阶段），tracinglib-platform.jar 推迟到 Release 阶段。

## 背景

四个迁移族均为：单 artifact、单 consumer（仅 `:SystemUI-core`）、骨架 POM（0 依赖边）、
`libs/maven/...` 副本与 `libs/aars/` 源逐字节相同。迁移只改变 Gradle 元数据解析路径，不改变任何字节。

迁移前字节同一性复核（本任务实测，与 audit §3 一致）：

| 族 | `libs/aars/` SHA-256 | `libs/maven/` SHA-256 | 一致 |
|---|---|---|---|
| WifiTrackerLib 1.0.0 | d45bbca9…ee99fb | d45bbca9…ee99fb | ✔ |
| iconloader 1.0.1 | d6e4f27e…3da6d8b | d6e4f27e…3da6d8b | ✔ |
| setupcompat 1.0.0 | 0a4222bf…a13c95a | 0a4222bf…a13c95a | ✔ |
| LowLightDreamLib 1.0.0 | 2a7b0939…717f7c0f | 2a7b0939…717f7c0f | ✔ |

## 改动内容

1. **AGENTS.md §3.2 规则 2 修订**（用户经简报批准）：为"单 artifact、单 consumer、骨架 POM、字节相同"族
   开出直接消费 `libs/aars/*.aar` 的例外，列明当前直接消费集四族；本地 Maven 保留给多 consumer 族与
   已证实冲突族。
2. **`SystemUI-core/build.gradle.kts` 接线迁移**（4 行）：
   `libs.systemui.setupcompat` / `libs.systemui.iconloader` / `libs.systemui.wifitrackerlib` /
   `libs.systemui.lowlight.dream.lib` → `files("${rootProject.projectDir}/libs/aars/<name>.aar")`，
   邻近中文注释改为"直接 AAR（libs/aars/，单 consumer 族，task 059）"。
   animationlib / SettingsLib / wmshell 等其他 catalog alias 未动。
3. **catalog + 本地 Maven 退役**：`gradle/libs.versions.toml` 删除 4 条 alias
   （`systemui-wifitrackerlib` / `systemui-iconloader` / `systemui-lowlight-dream-lib` /
   `systemui-setupcompat`）；`git rm -r` 四棵本地 Maven 树（共 4 AAR + 4 POM）。
   `libs/aars/*.aar` 源字节未动；`tools/install_aar_to_maven.py` 及其测试未动。
4. **audit §10 packet 关闭标注**：6 个已决 packet 各加 `> RESOLVED 2026-08-25 (task 059, user decision)` 行；
   tracinglib-platform packet 加 `> DEFERRED to Release phase`；AssumeTrueForR8 packet 未动。

## 验证证据（实际命令输出摘要）

1. `grep -rn "libs.systemui.wifitrackerlib\|libs.systemui.iconloader\|libs.systemui.setupcompat\|libs.systemui.lowlight" --include="*.kts" --include="*.toml"` →
   **0 命中**（exit 1）。
2. `uv run pytest tools/tests/ -q` → **243 passed, 52 subtests passed**（69.89s；未改任何测试）。
3. `./gradlew :app:checkDebugDuplicateClasses --rerun-tasks --console=plain` → **BUILD SUCCESSFUL**，
   task 实际执行（非 UP-TO-DATE）。最终干净串行构建中再次包含并通过。
4. `./gradlew clean :app:assembleDebug --max-workers=4` → **BUILD SUCCESSFUL，229/229 tasks executed**。
   新 APK SHA-256 = `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427`
   （163,896,493 B，5,298 entries，24 dex）。

### 与基线 `b827df78…` 的差异分析（非逐字节相同，但已证明与迁移无关）

基线对比未达逐字节相同，差异链已完整取证，**迁移本身是字节中性的**：

- **决定性对照**：把本任务全部改动 `git stash` 后，用**旧接线**（本地 Maven）串行干净重建
  （同样 229/229 executed）→ APK SHA-256 仍是 **`e8aad131…`，与新接线逐字节相同**。
  即"Maven 坐标 vs `files()` 直接 AAR"两条解析路径产出完全相同的 APK，迁移零 delta。
- **基线（18:12 构建，204,921,594 B）与当前干净构建（163,896,493 B）的差异属于构建环境产物**：
  - APK entry **名字集合完全相同**（5,298 = 5,298，`comm` 0 差异）；
  - 仅 8 个 dex（classes2/4/8/10/12/13/14/15/16）各相差 8–336 B（合计 −796 B 未压缩），
    属 D8 dex 打包布局差异；其余全部 entry（resources.arsc、manifest、res、assets、16 个 dex）
    大小+日期逐行一致；
  - **定义类集合完全相等**：旧 77,832 类 = 新 77,832 类，`only_in_old=0 / only_in_new=0`
    （用 `tools/check_manifest_dex_closure.py` 的 `dex_defined_classes` 对两个 APK 全量比对）；
  - 41 MB 文件体积差来自 zip 压缩/对齐（STORED/DEFLATED + zipalign padding），非内容差异
    （未压缩总量 168,463,131 vs 168,462,335，仅差 796 B）；
  - `check_manifest_dex_closure.py` 对两个 APK 均 **PASS**（95 entry：present=93 / alias=2 / missing=0）。
- 基线 APK 来源：emulator-5554 上现行部署副本（chief 复制到
  `/tmp/task059-apk-reference/app-debug-b827df78.apk`，sha256 复核一致）。

### 构建事故记录（如实）

- 首次 `clean :app:assembleDebug`（未限并行）与 task058 的并发 Gradle 构建叠加，触发内核 OOM
  （Gradle daemon 被杀，"daemon disappeared unexpectedly"），与 Task 044/045 记录的宿主机内存压力
  模式一致。处置：终止孤儿 Kotlin/Gradle daemon（8.9 GiB + 6 GiB RSS），待 chief 确认 task058  halted、
  本任务独占工作树后，以 `--max-workers=4` 串行重建成功。期间出现的 APK 短暂缺失系并发方 `clean`
  清目录所致，非真实回归。
- 中途曾产出 APK `d1b43c6c…`（并发干扰窗口内的部分增量构建），未采信；最终证据全部来自
  task058 halt 之后的串行干净构建。

### 设备状态

未触碰。现行部署于 emulator-5554 的 `b827df78` APK 与新 APK 内容集合逐条证明相等
（类集合 77,832 全等、资源/manifest 逐 entry 一致），按简报"APK 一致则无需重新部署"及 chief 指引
（类集合匹配、无类丢失则记录并继续），不重新部署；无 NCDFE 风险引入。

## 影响面

- `libs/maven/` AAR 数 27 → 23；`libs/aars/` 29 不变。
- 规则变化仅限 AGENTS.md §3.2 一条例外；其余 catalog alias、本地 Maven 仓机制、打包/安装工具链全部不变。
- Task 043 八个 packet 现状：6/8 已决（4 迁移 + animationlib 按设计保留 + SettingsLib 永久关闭），
  AssumeTrueForR8 维持原标签（Release 姿态已由 Task 044 关闭），tracinglib-platform.jar 推迟到 Release。

## 提交

1. `refactor(deps): migrate 4 single-consumer AAR families to direct consumption (task 059)`
   （AGENTS.md 修订 + 接线 + catalog + Maven 退役 + audit 标注）
2. `docs: task 059 orchestration state`（本文档 + CURRENT_STATE.md + STATE.md + log.md + 简报归档）

均本地提交，未 push（worker contract）。
