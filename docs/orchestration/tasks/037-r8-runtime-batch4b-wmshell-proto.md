# Task 037 Brief — R8 Runtime Batch 4B: WM-Shell proto 闭包（106→88）

> **执行模式**：redline-gated（触碰红线立即停止并上报，禁止即兴扩 scope）
> **必读顺序**：worker-contract → AGENTS.md → docs/orchestration/CHARTER.md → 本 brief
> → `docs/issues/2026-08-20-r8-runtime-batch4b-wmshell-proto.md`
> → `docs/superpowers/plans/2026-08-20-r8-runtime-batch4b-wmshell-proto.md`
> （plan 是唯一实施蓝图，逐步照做）
> 开始工作前先输出 `CONTRACT:` 确认块。

## 任务一句话

把 AOSP `WindowManager-Shell` 的两个 proto static_libs 的 Soong javac 产物并入
WM-Shell AAR（1848→1888 类），坐标升 1.0.0→1.0.1，fresh R8 精确 106→88，
且 debug 构建保持成功。

## Allowed Paths（只许改这些）

- `tools/package_aosp_aar.py`（仅 `CONFIGS["WindowManager-Shell"]` 的 code 列表 + 注释）
- `tools/install_aar_to_maven.py`（仅 `ARTIFACTS["WindowManager-Shell"]` 的 version 值）
- `tools/tests/test_package_aosp_aar.py`、`tools/tests/test_install_aar_to_maven.py`（新增测试）
- `gradle/libs.versions.toml`（仅 `systemui-wmshell` 一行版本）
- `libs/aars/WindowManager-Shell.aar`（重打包产物）
- `libs/maven/com/android/systemui/WindowManager-Shell/`（删 1.0.0/、装 1.0.1/）
- `docs/issues/2026-08-20-r8-runtime-batch4b-wmshell-proto.md`（补证据段）

## Forbidden Paths / 禁止事项

- 任何 `SystemUI-*/src/**`、`SystemUI-*/res*/**`、任何 build.gradle.kts、settings.gradle.kts、
  AGENTS.md、docs/adr/**、CHARTER.md
- launcher3 flags / `WindowManager-Shell-shared` / shared AAR 一律不动
- 禁止 stub、keep、dontwarn、@Suppress、源码排除、禁用检查等构建绕过
- 禁止 turbine/header/combined/FAT jar；只用 owning Soong javac 产物
- 禁止实现 Traceur、SettingsLib、B1–B4 等任何其他闭包
- 禁止 push；单个英文 commit

## 验收（十条，全部必须真实通过）

1. 新增聚焦测试先红后绿；全套 tools/tests 通过（164 + 新增）。
2. `libs/aars/WindowManager-Shell.aar` 恰 1888 类（1848+40 精确并集，零重叠）。
3. 40 个 proto 类与 Soong 源 jar 逐字节一致；18 个目标类全在 AAR 中；
   全部类位于 `com/android/wm/shell/**`。
4. res / AndroidManifest.xml / R.txt 与 AOSP/Soong 源逐字节一致；
   两次重打包 byte-identical。
5. 本地 Maven 仅剩 `WindowManager-Shell/1.0.1/`，AAR 与 libs/aars byte-identical，
   POM 骨架无 dependencies；无 1.0.0 残留目录。
6. `gradle/libs.versions.toml` 恰好一行变化（systemui-wmshell 1.0.0→1.0.1）。
7. `:app:checkDebugDuplicateClasses :app:assembleDebug` BUILD SUCCESSFUL
   （tee 日志 + 真实退出码；**硬性门禁**）。
8. 18 个目标类在 debug APK 全部 `C d` defined。
9. fresh R8：before=106、after=88、removed 恰为 18 个 wm.shell 目标、added=0、
   `AssumeTrueForR8` 保留；任何偏差 REDLINE。
10. issue 文档证据段如实补全；`git diff --check` 干净；单 commit 未 push。

## 结束协议

- 成功：输出 `HANDOFF:` 块（done / verified / remaining），附真实命令与退出码。
- 红线/失败：输出 `REDLINE:` 块（卡点、已验证事实、建议），**禁止**绕过验收。
