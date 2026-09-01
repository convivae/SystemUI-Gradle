# C5：定位四个错误平台类引用的来源

**日期**：2026-09-01  
**状态**：计划待用户确认后派发

## 背景

Debug 与 Release APK 均已能编译。当前唯一已知阻塞是 Release APK 在 Android 17 模拟器上仍引用四个旧平台类名，设备只提供 `com.android.internal.hidden_from_bootclasspath.*` 新名字，因此发生 `NoClassDefFoundError`。

用户已确认正确方向：不修改 AOSP SystemUI 源码、不复制平台类，而是在源码编译为 class 后、D8/R8 生成 DEX 前，补齐 AOSP Soong 原本执行的类引用转换。

## 本步骤只回答一个问题

在实施转换前，先准确找到当前构建产物中是谁引用了以下四个旧名字：

- `android.app.Flags`
- `android.os.Flags`
- `android.view.accessibility.Flags`
- `com.android.window.flags.Flags`

本步骤只读现有构建产物，不修改代码、不运行 Gradle、不执行 JarJar、不生成 APK、不操作模拟器。

## 完成条件

对四个旧名字逐一给出：

1. 包含引用的具体 class/JAR/AAR 路径；
2. 它属于哪个 Gradle 模块或外部依赖；
3. 它是项目自己编译的代码还是依赖中的代码；
4. 后续应在哪一类输入上执行转换；
5. `UNKNOWN=0`；若无法证明，必须报告 `BLOCKED`，不能猜测。

## 后续

本步骤完成并由 Chief 独立复核后，再单独制定一个很小的实现任务：只给确认过的 class 输入增加 Android 17 类引用转换。实现任务不会与本定位任务合并。
