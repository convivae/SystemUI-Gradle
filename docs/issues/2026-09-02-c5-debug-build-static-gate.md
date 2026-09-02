# C5 Task 096：fresh Debug APK build/static gate

**日期**：2026-09-02
**状态**：PASS
**前置**：Task 095 production immutable-input seam已在commit `2994fa8f`落地并push；corrected bounded direct gate、Standards/Spec双轴review及focused re-review均PASS。
**执行基线**：`69d332f4104ada726ed16f3d5e46a8bb9d551fc1`（执行时`HEAD == origin/main`，且包含production ancestor `2994fa8f`）

## 背景

Task 095只证明production visitor在真实dependency transform中至少完成一个allowlisted instruction-level rewrite，且managed 4/166 input seam可通过AGP worker isolation。它没有构建或验收新的Debug APK，也没有证明四条runtime-critical mappings在完整program closure中全部生效。

本任务作为独立、no-fix、单Gradle调用的build/static gate执行。Debug无shrinking，APK可合法保留old source definitions及其current-class self-reference；因此release-oriented checker的exit 1不能单独判定本任务失败，必须结合四条critical hidden target和SDK 37 `dexdump` old-owner context验收。

## 执行与结果

合规replacement worker `task096-debug-r2`使用`joycode/GLM-5.3`、`thinking=high`。首个worker因在规定序列前先读brief而在preflight前退役；未创建scratch、删除产物或运行构建。replacement worker在Chief接受CONTRACT后执行以下唯一Gradle wrapper调用：

```bash
./gradlew :app:assembleDebug --console=plain --rerun-tasks --max-workers=4
```

结果：exit 0，`BUILD SUCCESSFUL in 3m 55s`，278/278 actionable tasks executed。Task 082的factory isolation failure未复现；`:app:transformDebugClassesWithAsm`、`:app:dexBuilderDebug`和`:app:packageDebug`均实际执行。

fresh APK证据：

- 路径：`app/build/outputs/apk/debug/app-debug.apk`
- 大小：`190547804` bytes
- mtime：`2026-09-02 20:01:15.912668240 +0800`
- SHA-256：`f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`
- `unzip -t`：exit 0
- DEX：13个，`classes.dex`至`classes13.dex`

725-rule checker exit 1、`RESULT=FAIL`，但这正是brief允许进一步判定的Debug形态。权威输出为：

- 四条critical hidden target均`referenced=yes, defined=no`：`4/4`
- 全725条target descriptors：`referenced=4, defined=0`
- 两个critical old source仍存在：`android.os.Flags`、`com.android.window.flags.Flags`，均为defined class
- `android.app.Flags`与`android.view.accessibility.Flags` old descriptor在所有DEX中为0 occurrence

SDK 37 `dexdump -d`对13 DEX × 4 old descriptors的current-class context验证PASS：

- `Landroid/os/Flags;`仅出现在`classes.dex`自己的`Landroid/os/Flags;` class context；
- `Lcom/android/window/flags/Flags;`仅出现在`classes7.dex`自己的`Lcom/android/window/flags/Flags;` class context；
- 其余两个old descriptor无任何DEX occurrence；
- 没有old descriptor出现在其他current class context，也没有对应`const-string` descriptor literal。

因此checker exit 1只由合法Debug definition/current-class self-reference造成，不代表program caller仍指向old owner。

## 验收

Task 096正式`PASS`：

1. 唯一Gradle调用exit 0且日志含`BUILD SUCCESSFUL`；
2. fresh APK非空、ZIP完整且身份已冻结；
3. critical hidden references `4/4`；
4. 725条规则的hidden target definitions为0；
5. old-owner residual gate无跨class残留；
6. worktree终态clean；cleanup exits `0/0/1`；Chief复核时Gradle/Kotlin/Soong/Ninja/Java census为空；
7. 未运行Release/R8、ADB/emulator/device、Soong/Ninja、Task 079，也未进行修复或tracked编辑。

证据根：`/tmp/task096-c5-debug-build-static/`，核心文件为`assemble-debug.{log,exit}`、`apk-identity.txt`、`unzip-t.{txt,exit}`、`dex-entries.txt`、`checker.{log,exit}`、`residual/`和`cleanup-exits.txt`。

## 过程偏差

worker preflight额外运行了一次`git fetch --all --quiet`。这不是冻结步骤所需命令，并更新了`.git/FETCH_HEAD`时间戳；它没有改变tracked worktree、`HEAD`或`origin/main`，也不影响APK或静态证据。Chief将其作为已披露的低风险流程偏差记录，不改变技术PASS；后续worker禁止自行补充此类非必要命令。worker两次发现process-census命令自匹配后，以不自匹配的`ps` census确认终态为空；cleanup命令本身各执行一次，exit codes完整保存，未重跑。

## 成功边界与下一步

PASS仅表示fresh Debug APK编译成功且四映射静态闭合。它不证明Release/R8、部署、runtime或整机重启稳定，也不完成Task 079。下一独立阶段是fresh Release build/R8/static gate；Release通过后再分别执行Debug与Release runtime reboot gates。
