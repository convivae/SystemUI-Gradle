# R8 Runtime Closure Batch 3：protobuf-javalite + view_capture + motion_tool

日期：2026-08-20

## 背景

Task 034 合并后，`:app:minifyReleaseWithR8` 仍如实失败于 119 个 unique missing refs。Task 031 的闭包审计把其中 11 个归入同一有序依赖链：

```text
motion_tool_lib
├── view_capture
├── motion_tool_proto
│   ├── view_capture_proto
│   └── libprotobuf-java-lite
└── androidx.core_core

view_capture
├── view_capture_proto
│   └── libprotobuf-java-lite
└── androidx.core_core
```

当前仓库状态不满足 APK program/runtime closure：

- `libs/view_capture.jar` 是 3427-class FAT JAR，混入 AndroidX、Kotlin、kotlinx、protobuf 等上游类；不能直接改为 `implementation`，否则 D8 duplicate classes。
- `libs/motion_tool_lib.jar` 只含 main Kotlin 的 8 类，缺 `motion_tool_proto` 的 57 类。
- 两个 JAR 都是 `compileOnly`，因此真实 runtime 类没有进入 APK。
- `protobuf-javalite` 尚未声明为官方 Maven runtime dependency。

## 依赖判定

| 依赖 | tier | 交付方式 | 依据 |
|---|---|---|---|
| `protobuf-javalite` | ③ 标准上游 | Maven Central `com.google.protobuf:protobuf-javalite` | AOSP `libprotobuf-java-lite` 对应官方 protobuf lite runtime；无 AOSP fork API 需求 |
| `view_capture` / `view_capture_proto` | ② AOSP 非 SystemUI 纯代码 | 确定性 clean JAR | 定义于 `frameworks/libs/systemui/viewcapturelib/Android.bp`，无资源 |
| `motion_tool_lib` / `motion_tool_proto` | ② AOSP 非 SystemUI 纯代码 | 确定性 clean JAR | 定义于 `frameworks/libs/systemui/motiontoollib/Android.bp`，无资源 |

Maven Central metadata 于 2026-08-20 实测：`latest/release=4.36.0-RC2`，过滤 RC 后最新稳定版为 **4.35.1**。依用户“优先尝试公网最新稳定版，构建通过则采用”的既定授权，本批先使用 4.35.1；只有出现可复现的二进制/编译兼容失败时，才可 REDLINE 请求回退 AOSP pin `3.21.12`，不得静默降级。

## 干净产物输入

所有输入必须来自 owning Soong implementation 产物，禁止 turbine/header/FAT 输入：

### `libs/view_capture.jar`

1. `view_capture/android_common/javac/view_capture.jar` — 9 类
2. `view_capture/android_common/kotlin/view_capture.jar` — 23 类
3. `view_capture_proto/android_common/javac/view_capture_proto.jar` — 24 类

输出必须恰为 56 个 `com/android/app/viewcapture/**.class`。

### `libs/motion_tool_lib.jar`

1. `motion_tool_lib/android_common/kotlin/motion_tool_lib.jar` — 8 类
2. `motion_tool_proto/android_common/javac/motion_tool_proto.jar` — 57 类

输出必须恰为 65 个 `com/android/app/motiontool/**.class`。

打包器必须拒绝缺失/空输入、批准 namespace 外的 class、输入内或跨输入重复 class；输出 class 按路径排序并固定 ZIP timestamp/权限，重复运行 byte-identical。非 class entry 不进入输出。

## 操作步骤

1. 在改动前 fresh 运行 `:app:minifyReleaseWithR8`，保存真实 Gradle exit code 和 119-ref baseline。
2. TDD 新增 `tools/package_viewcapture_motiontool_jars.py` 及聚焦单测。
3. 生成并提交 clean 56-class `libs/view_capture.jar` 和 65-class `libs/motion_tool_lib.jar`。
4. `gradle/libs.versions.toml` 新增 `protobufJavalite = "4.35.1"` 与 `protobuf-javalite` alias。
5. 严格按顺序接入：
   - `protobuf-javalite` + clean view_capture；
   - 再接入 clean motion_tool。
6. `SystemUI-core`：view_capture、motion_tool 从 `compileOnly` 改为 `implementation`，并加入 `implementation(libs.protobuf.javalite)`。
7. `SystemUI-shared`：view_capture 从 `compileOnly` 改为 `implementation`，并加入 `implementation(libs.protobuf.javalite)`，使该库自身 runtime closure 完整。
8. 运行全套 Python tests、debug duplicate/build、APK class 定义检查和 fresh R8 差分。

## 预期 R8 差分

119 → 108，必须恰好移除以下 11 项，新增 0：

- `com.android.app.motiontool.DdmHandleMotionTool$Companion`
- `com.android.app.motiontool.DdmHandleMotionTool`
- `com.android.app.motiontool.MotionToolManager$Companion`
- `com.android.app.motiontool.MotionToolManager`
- `com.android.app.viewcapture.LooperExecutor`
- `com.android.app.viewcapture.ViewCapture`
- `com.android.app.viewcapture.ViewCaptureAwareWindowManager$Factory`
- `com.android.app.viewcapture.ViewCaptureAwareWindowManager`
- `com.android.app.viewcapture.ViewCaptureFactory`
- `com.google.protobuf.GeneratedMessageLite$Builder`
- `com.google.protobuf.GeneratedMessageLite`

`com.android.aconfig.annotations.AssumeTrueForR8` 必须继续保留，不在本批处理。

## 红线与禁止项

- 不修改任何 AOSP mirrored `src/` 或 `res/`。
- 不添加 stub、keep/dontwarn、source exclusion 或 build bypass。
- 不使用 turbine/header/FAT 产物。
- 不将 JAR 放进 `libs/maven/`，不调用 `install_aar_to_maven.py`。
- 不改除 protobuf-javalite 之外的任何依赖版本。
- 4.35.1 若失败，必须保留证据并 REDLINE；不得自行改用 3.21.12。

## 错误数演变

| 阶段 | R8 unique missing refs | 说明 |
|---|---:|---|
| Task 034 后 | 119 | fresh main baseline |
| 本批目标 | 108 | 精确移除 A5+A8 共 11 项，0 additions |

## 待解决问题

本批结束后仍有 108 个 missing refs，继续按已审计顺序处理 Batch 4 的 Traceur、SettingsLib、SettingsTheme、WM-Shell、iconloader 闭包；B1–B4 classpath 问题仍不得越界处理。
