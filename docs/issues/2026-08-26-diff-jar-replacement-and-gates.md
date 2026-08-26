# 2026-08-26 — Task 065：DIFF jar 替换 + 全流程双门验证

**任务**: `docs/orchestration/tasks/065-diff-jar-replacement-and-gates.md`
**决策来源**: 用户 2026-08-26 拍板 — 无法从 AOSP 再生的 jar 一律不用（脚本产出 > 历史手工拷贝）。
**前置**: Task 064 冻结了 15 个产物的再生映射（13 MATCH + 2 DIFF，见
`docs/architecture/2026-08-26-regeneration-gap-closure.md`）。

## 目标

1. 用 `package_misc_jars.py` 冻结源产出替换 `libs/framework-statsd.jar`、`libs/android.car.jar`
2. 更新脚本两条目的 baseline sha256 → `--verify-only` 全部 MATCH
3. 双构建门：`assembleDebug` + `assembleRelease` 均 BUILD SUCCESSFUL（串行）
4. 双运行门：Debug / Release APK 分别 staged 部署 emulator-5554 →
   boot_completed=1 → 设备端 sha 门禁 → PID 稳定 2×30s → crash buffer 零 FATAL →
   dumpsys 窗口三件套（Release 额外 `cmd statusbar expand-settings/collapse`）
5. 对齐门 + pytest：`check_source_alignment.py` 0-0-0；`uv run pytest tools/tests/ -q` 全绿

两个 jar 均为 `:SystemUI-core` compileOnly 接线（`SystemUI-core/build.gradle.kts:152-153`），
不进 APK 打包边界。

**Chief 中途澄清（用户指令）**：即使 APK sha 与旧基线逐字节一致，也必须对 Debug 与 Release
两个变体各跑完整设备门（staged 部署 + reboot + boot_completed + 设备端 sha + PID 2×30s +
零 FATAL + dumpsys）——用户要看替换 jar 的真实设备效果，构建门不构成充分验收。

## 执行记录

### Step 1 — 替换

- `uv run python tools/package_misc_jars.py framework-statsd/android.car --output-root /tmp/task065-gen`
  → 均无源指纹漂移 warning（冻结源完好），产出 DIFF（对旧手工基准）符合预期
- 新旧 sha256：

| jar | 旧基准（手工拷贝） | 新（脚本产出 = 冻结源） | entry 变化 |
|-----|---|---|---|
| framework-statsd.jar | `d54489ee…` | `058f30a1…` | 39 → 70 files（impl javac 真实类，类名超集） |
| android.car.jar | `bd5faa75…` | `89f04e0a…` | 678 → 1219 files（turbine-combined 含 dep closure） |

- 风险面预检：新 android.car.jar 全部类都在 `android/car`、`com/android/car` 命名空间
  （0 个非 car 类 → 无 framework 遮蔽风险）；源码树 `import android.car` 零引用；
  新 framework-statsd.jar 类名为旧 39 类超集（真实 impl 类）
- 覆盖 `libs/` 两文件；`package_misc_jars.py` 两条目 baseline 重新冻结为源指纹
  → `--verify-only` **12/12 MATCH**
- 测试契约同步：`test_package_misc_jars.py` 的 "two known DIFF" 钉住改为
  "零 DIFF 基线 + 替换 sha 钉住"（防回退到手工拷贝）

### Step 2 — 构建门（串行，每次先杀闲置 Kotlin/Gradle daemon）

- `./gradlew clean :app:assembleDebug --console=plain --max-workers=4`
  → **BUILD SUCCESSFUL in 2m39s**，229/229 executed
- `./gradlew :app:assembleRelease --console=plain --max-workers=4`
  → **BUILD SUCCESSFUL in 5m43s**，380 tasks（318 executed + 62 up-to-date）
- APK 新基线：
  - Debug `app-debug.apk` = `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427`
    （163,896,493 B，**与替换前基线逐字节一致** —— compileOnly jar 不改变输出字节）
  - Release `app-release.apk` = `d3968fb21c2f7198d1b706b418861a31f3ba13fb0019987d420a66e7ab5b20b0`
    （34,688,965 B，与旧基线 `14768581…` 同尺寸不同字节，R8 输出漂移；**此为新 Release 基线**）
- 静态检查：`unzip -t` clean；apksigner v2 验签通过（Debug/Release 均通过）

### Step 3 — Debug 运行门（emulator-5554）

- Preflight：设备在列，boot_completed=1，verity orange（disabled），机上 Release 基线
  `14768581…` 确认
- Staged 部署 `e8aad131…`：push → staging sha MATCH → remount,rw → 同目录 `.new` cp → sync →
  原子 mv → root:root 0644 `u:object_r:system_file:s0` → oat/dalvik-cache 清理 →
  **机上 sha 门禁 MATCH**（PITFALLS §14.2）→ reboot
- 门结果：boot_completed=1；PID **821** 稳定（boot+10s / +30s / +60s 三采样）；
  crash buffer **0 行**；全量 logcat `FATAL EXCEPTION|NoClassDefFoundError` = **0**；
  dumpsys windows：StatusBar(5) + NotificationShade(2) + Taskbar(5) + ImageWallpaper(3) 全在
- **PASS**

### Step 4 — Release 运行门

- Staged 部署 `d3968fb2…`：同规程，staging sha MATCH，机上 sha 门禁 MATCH，reboot
- 门结果：boot_completed=1；PID **840** 稳定（2×30s）；crash buffer **0 行**；FATAL/NCDFE **0**；
  窗口三件套全在；bonus：`cmd statusbar expand-settings`（NotificationShade 窗口出现）→
  `collapse` → 无崩溃、PID 840 不变
- **PASS**

### Step 5 — 对齐门 + pytest

- `uv run python tools/check_source_alignment.py --strict` →
  **MISSING=0 / MISPLACED=0 / EXTRA=0**（MODIFIED 1 + RES-MODIFIED 86 为 ADR 0004 已知基线）
- `uv run pytest tools/tests/ -q` → **276 passed, 102 subtests**（含更新后的
  package_misc_jars 契约测试；无跳过无失败）

## 结论

**全部门通过**。用户决策 option A 落地完成：`libs/` 28 个根 jar 全部可由脚本从 AOSP 冻结源
再生（`--verify-only` 12/12 MATCH + aconfig 侧 3 个 gap 条目 task 064 已验证 MATCH）。
设备终态：Release `d3968fb2…` 在机上（新基线）。commit `fee014cd`（替换+测试契约）+ docs commit。

## 遗留

- 无本任务遗留。Phase C runbook 可引用 §4.4 作为替换先例。
