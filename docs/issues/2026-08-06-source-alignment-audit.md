# SystemUI 源码与资源对齐差异诊断

**日期**：2026-08-06

## 背景

checkpoint `44316ff4` 引入并修正了 `tools/check_source_alignment.py`。当前稳定复现：

```text
[MISSING]   13
[MISPLACED] 0
[EXTRA]     7
[RES-MISS]  0
[RES-EXTRA] 7
[SHADER]    AOSP 22 / 项目 0
```

用户要求前期优先保证源码、jar/AAR 和资源归属准确；SystemUI src/AIDL/res 不漏不多，非 SystemUI 代码不得源码复制，AOSP 资源不得擅改。

## 诊断原则

1. 先核对每个差异在 AOSP `Android.bp` 中的真实 owner，不根据包名猜测。
2. 区分：脚本映射错误、真实缺失、放错 module、违规外部源码/资源复制。
3. 在确认 owner 和替代依赖前，不删除资源、不新建资源、不创建 stub。
4. 错误数和逐次编译不是本次门槛；使用文件集、BP、jar/AAR 内容作为证据。

## 初始差异

### 缺失源码

- `SystemUI-animationlib`：8 个 Java/AIDL
- retail data/domain pods：4 个 Kotlin
- `SystemUI-shared`：`UncaughtExceptionPreHandlerManager.kt`

### 多余源码

- `SystemUI-animationlib/com/android/app/animation/*`：4 个
- `SystemUI-common/.../flow/*Conflated.kt`：2 个
- `SystemUI-core/.../Compile.java`：1 个

### 多余资源

`SystemUI-animationlib/src/main/res` 下 6 个 interpolator XML 和 `values/ids.xml`。

## 待完成

- [ ] 读取相关 AOSP BP，确定每个文件 owner
- [ ] 全 AOSP 搜索 extra 文件及资源来源
- [ ] 检查项目 Gradle module 与现有 jar/AAR 是否已经提供对应 owner
- [ ] 判断脚本映射是否准确
- [ ] 形成单一、可验证的最小修正方案
- [ ] 任何涉及 res 删除/迁移的操作前再次核对来源和替代 AAR

## 验证记录

尚未修改源码或资源，尚未运行源码编译。
