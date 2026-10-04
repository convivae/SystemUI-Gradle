# Task 066 — README.md / README.en.md 重写（Phase D 主体）

## Goal

重写 `README.md`（中文）与 `README.en.md`（英文），使其反映项目真实现状：AOSP SystemUI
已成功移植到独立 Gradle 构建体系，Debug + Release 双 runtime 在模拟器上验证通过。
README 是仓库门面：新人/外人读完应能知道这是什么、做到了什么、如何从零复现。

## Authority

- 可修改：`README.md`、`README.en.md`；可新增 `docs/aosp-pinning/README.md`（解释快照文件）。
- Forbidden：任何代码/wiring/脚本文件；不改 docs/ 下其他文档（内容引用它们即可）。
- 不跑 Gradle。

## 必读素材（动笔前全部读）

1. `README.md` + `README.en.md` 现状（过时版本，看其结构与风格）
2. `AGENTS.md`（规则、模块结构、libs 交付规则）
3. `docs/CURRENT_STATE.md`（实时状态、构建矩阵）
4. `docs/HANDOFF.md`、`docs/PLAN.md`
5. `docs/orchestration/log.md` 尾部（task 058 runtime PASS → task 061 RELEASE_RUNTIME_PASS →
   task 062-065 清理与再生管线闭环）
6. `docs/issues/2026-08-26-emulator-relaunch-runbook.md`（模拟器 runbook）
7. `docs/architecture/2026-08-26-regeneration-gap-closure.md`（15 产物再生表）
8. `docs/architecture/2026-08-21-sysuisdk-single-entry-composition.md`（SysUISdk 生成器）

## 必须包含的内容（结构你定，以下要素不可缺）

1. **项目简介**：把 AOSP `frameworks/base/packages/SystemUI` 从 Soong 搬进独立 Gradle/AGP
   体系的目标与动机；AGP-native functional parity 的成功标准（见 CURRENT_STATE）。
2. **当前状态徽章式摘要**：DEBUG_RUNTIME_PASS（2026-08-25）+ RELEASE_RUNTIME_PASS
   （2026-08-26）；关键版本矩阵（AGP 9.3.1 / Gradle 9.5.0 / builtInKotlin 2.2.10 /
   compileSdkPreview SysUISdk）；pytest 276；对齐门 0-0-0。
3. **架构**：13 模块 + app 拓扑表（照 AGENTS.md §3.1）；SysUISdk 角色一句话；
   libs/ 三形态交付（源码/jar/aar）+ 本地 Maven 规则一句话。
4. **AOSP 版本声明**：当前验证基线 = AOSP `main` @ 快照
   `docs/aosp-pinning/aosp-manifest-2026-08-26-validated.xml`（1042 项目，repo manifest -r 生成）。
   明确写：**正式版本固定（升级 AOSP → 重编译 → 全管线重跑 → 重新适配验证）是已规划的
   后续工程（见 docs/PLAN.md Phase C），尚未执行**。
5. **从零复现 Quickstart**（章节化，步骤可引用现成脚本/runbook，不要复制大段命令细节，
   指到文档；但要给出端到端步骤骨架与每步入口脚本名）：
   下载 AOSP（repo init main + manifest 快照 checkout）→ 编译
   （`lunch sdk_phone64_x86_64-trunk_staging-userdebug` + `m -j4`，产物含 emu64x 镜像）
   → 生成 SysUISdk（`tools/build_sysuisdk.py --aosp-root`）→ 生成 libs
   （`package_aosp_aar.py --all` → `install_aar_to_maven.py` → `package_aconfig_jars.py`
   → `package_misc_jars.py` → `package_compilelib_jars.py` → `package_monet_jar.py` →
   `package_viewcapture_motiontool_jars.py`）→ Gradle 构建（assembleDebug/Release）→
   启动模拟器（指向 emulator-relaunch-runbook）→ 部署验证（指向 PITFALLS §14 规程）。
   每步注明"已验证"或"待 Phase C 全流程重验"。
6. **软硬件要求**（实测数据）：Ubuntu Linux；磁盘 **≥400 GiB**（AOSP 418G 实测，含 out/ 187G；
   说明含历史实验产物，干净单产品构建预计 ~300G）；内存 **≥32 GiB**（本机 30Gi + swap 8G
   紧张可行，AOSP `-j4`）；KVM（模拟器）；JDK 17+；Python 3 + **uv**（禁 pip）；adb；
   可选 scrcpy 看画面。Gradle wrapper 自带 9.5.0，腾讯/阿里云镜像已内置 settings.gradle.kts。
7. **文档地图**：HANDOFF / CURRENT_STATE / PLAN / PITFALLS / ADR / issues / orchestration 各干什么。
8. **中英文一致**：README.en.md 与 README.md 内容等价（英文可自然改写，但信息与结构一致）。

## Acceptance

- 两文件内容准确（每个版本号/数字/路径都以仓库现状为准，写完自查一遍引用路径全部存在）
- 无虚构内容；拿不准的标注 TODO(Phase C) 而非编造
- 一行 log.md；commit（英文，本地不 push）；四段式报告

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
