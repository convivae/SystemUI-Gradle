# Task 065 — 替换 2 个 DIFF jar 为脚本产出 + 全流程双门验证

## Goal

用户拍板（2026-08-26）：**无法从 AOSP 再生的 jar 一律不用**。将 `framework-statsd.jar`
与 `android.car.jar` 替换为 `package_misc_jars.py` 冻结源产出，然后跑全流程验证：
Debug 和 Release APK 都要能编译，且部署设备后无运行时异常。
**不要求** APK 与旧版逐字节一致（jar 换了 APK 可能变）。

## Authority

- 可修改：`libs/framework-statsd.jar`、`libs/android.car.jar`（替换为脚本产出）、
  `tools/package_misc_jars.py`（更新冻结 baseline sha256 使 `--verify-only` 此后报 MATCH）、
  `docs/architecture/2026-08-26-regeneration-gap-closure.md`（§4 记录用户决策与执行结果）
- Forbidden：其他一切文件；不得并行两个 Gradle 构建
- 设备操作走既有 staged 部署规程（PITFALLS §14：sha 门禁、原子 mv、权限、清缓存、reboot）

## Steps

1. **替换**：
   ```bash
   uv run python tools/package_misc_jars.py framework-statsd --output-root <临时>   # 确认产出
   # 用产出覆盖 libs/framework-statsd.jar；android.car 同理
   # 更新 package_misc_jars.py 中两条目的 baseline sha256 → --verify-only 全部 15 条 MATCH
   ```
   记录新旧 sha256（报告用）。
2. **构建门（串行，先停闲置 Kotlin/AS daemon）**：
   - `./gradlew :app:assembleDebug --console=plain --max-workers=4` → BUILD SUCCESSFUL
   - `./gradlew :app:assembleRelease --console=plain --max-workers=4` → BUILD SUCCESSFUL
   - 记录两个 APK 的新 sha256（此后它们是新基线，报告里写明）
3. **Debug 运行门**：staged 部署 Debug APK → reboot → boot_completed=1 →
   设备端 sha 校验 → `pidof com.android.systemui` 稳定 2×30s →
   `logcat -b crash -d` 零 FATAL → dumpsys 确认 StatusBar/NotificationShade/Taskbar 在屏
4. **Release 运行门**：同上部署 Release APK → 同门（PID 稳定 2×30s + 零 FATAL + dumpsys +
   `cmd statusbar expand-settings/collapse` bonus）
5. **对齐门 + pytest**：`check_source_alignment.py` 0-0-0；`uv run pytest tools/tests/ -q` 全绿
6. **失败协议**：任一门失败 → 取证（完整栈 + 分类 + file:line 证据）→ 恢复设备已知好基线 →
   停 → 报告。不做推测性修复。
7. **报告**：更新 `docs/architecture/2026-08-26-regeneration-gap-closure.md` §4
   （用户决策 option A + 执行 + 新 sha256 台账 + 双门结果）；一行 log.md。
   commit 分两个：(a) `chore: replace framework-statsd/android.car with script-regenerated jars (user-approved)`；
   (b) docs。英文，本地，不 push。

## Model constraint

joycode GLM-5.3 或 GLM-5.2。
