# Task 080 — 找到四个错误类引用来自哪些构建产物

**Authority**: `self-commit`（worker 只提交报告，绝不 push）  
**Reports To**: Chief architect  
**执行方式**: shared checkout 串行；只能使用显式 `joycode/Kimi-K3` 或 `joycode/Kimi-K3-jcloud`

## Goal

只读检查当前已有的 Release 构建产物，准确找到四个旧 Android 平台类名引用来自哪些项目模块或依赖。不要修复，不要设计通用框架。

四个名字：

```text
android.app.Flags
android.os.Flags
android.view.accessibility.Flags
com.android.window.flags.Flags
```

## Allowed Paths

只能修改：

- `docs/issues/2026-09-01-c5-focused-reference-origins.md`
- `docs/orchestration/tasks/080-c5-find-reference-origins.md`（只勾选完成项或补实际命令）

临时文件只能写入：

- `/tmp/task080-c5-reference-origins/`

## Forbidden Paths / Actions

- 不得修改任何源码、Gradle 文件、工具脚本、资源、manifest、ProGuard、SDK、`libs/**`、AOSP 或 `out/**`。
- 不得运行 Gradle、Soong/Ninja、模拟器或 ADB。
- 不得运行 JarJar，不得尝试修复。
- 不得重新研究 464 个 stock 输入；本任务只追踪四个实际崩溃类名。
- Python 一律使用 `uv run`。
- 不得 `git add -A` 或 `git add .`。

## Steps

- [ ] 先确认当前 Release APK 的四个旧名字确实仍被引用，并记录 APK SHA-256。
- [ ] 只读扫描当前已有的 module `build/**` class/JAR 输出和当前依赖 JAR/AAR，定位每个旧名字的引用来源。
- [ ] 对每个命中记录：文件路径、SHA-256、所属 Gradle module/依赖、project-local 或 external、命中的 class 名。
- [ ] 证明四个 APK 级引用都有来源；无法证明则写 `BLOCKED`，不得填默认值或猜测。
- [ ] 给出最小结论：后续转换需要覆盖哪些已证明的输入类别。不要写实现代码。
- [ ] 显式 stage 两个 Allowed Paths，英文 commit；不得 push。

## Acceptance

报告必须含一个简短结果块：

```text
APK_CRITICAL_REFERENCES=4/4
ORIGINS_PROVEN=4/4
UNKNOWN=0
RESULT=PASS
```

如果现有只读产物不足，则必须诚实写：

```text
RESULT=BLOCKED
```

并列出缺失证据；不得运行构建补证据。

Chief 将独立执行：

```bash
git diff --check
git status --short
uv run python tools/check_aconfig_jarjar_references.py \
  --rules /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt \
  --apk app/build/outputs/apk/release/app-release.apk
```

预期：格式检查通过；worker 只触及两个 Allowed Paths；现有 Release 静态 gate 仍如实为 `RESULT=FAIL`，因为本任务不修改行为。

## Mandatory halt

发现需要运行构建、修改代码或无法证明来源时，立即停止并报告，不得扩大任务。
