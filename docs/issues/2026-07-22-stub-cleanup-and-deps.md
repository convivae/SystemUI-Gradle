# 2026-07-22 补充: 遵循参考项目 (CarSystemUIGradle) 依赖引入方式

## 用户要求

> 你在改造的过程中不允许使用 stub 技术，所有的依赖要么是源码复制过来当作子项目，
> 或者是 jar 包，aar 包，maven 的形式引入进来，也不允许私自创建资源文件，
> 所有的资源文件都必须来自 AOSP 源码，或者 aar 包，或者 maven

## 删除内容

### 删除的 stub 文件 (~60 个)

所有这些文件要么在合并后的 SDK android.jar 中，要么替换为 jar/aar 引入：

| 路径 | 原因 |
|------|------|
| `SystemUI-core/src/android/appwidget/` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/hardware/{biometrics,face,input}/` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/window/{WindowOnBackInvokedDispatcher,flags/Flags}.*` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/media/projection/{StopReason,flags/Flags}.*` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/app/{Flags,smartspace/flags/Flags}.*` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/service/notification/flags/Flags.kt` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/view/accessibility/flags/Flags.kt` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/widget/flags/Flags.kt` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/android/settingslib/flags/Flags.kt` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/com/android/internal/annotations/Keep.java` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/com/android/internal/jank/Cuj.java` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/com/android/internal/statusbar/LetterboxDetails.java` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/com/android/internal/camera/flags/Flags.kt` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/com/android/internal/telephony/flags/Flags.kt` | 已在 SDK android.jar 中 |
| `SystemUI-core/src/com/android/compose/{theme,nestedscroll,ui/util}/` | 待 Scene AAR 处理 |
| `SystemUI-core/src/com/android/wm/shell/dagger/HasWMComponent.kt` | WindowManager-Shell.jar 已提供 |

### 删除的资源修改

- `SystemUI-core/res/values/config.xml` 中我私自添加的
  `config_enableLockScreenCustomClocks` - 改为从 AOSP res-keyguard 复制

## 引入方式（参考 CarSystemUIGradle）

### 1. 复制 AOSP res-keyguard, res-product 目录

```bash
# 不在 git 中跟踪，由 build.gradle.kts 通过 sourceSets 配置自动加载
cp -r aosp/frameworks/base/packages/SystemUI/res-keyguard SystemUI-core/
cp -r aosp/frameworks/base/packages/SystemUI/res-product  SystemUI-core/
```

`SystemUI-core/build.gradle.kts`:
```kotlin
sourceSets {
    getByName("main") {
        java.srcDir("src")
        res.srcDirs("res", "res-keyguard", "res-product")
        manifest.srcFile("AndroidManifest.xml")
    }
}
```

`.gitignore`:
```
res-product/
res-keyguard/
res-gradle/
```

### 2. 处理 res-product 的 product 属性冲突

AOSP res-product 的 strings.xml 包含 `<string product="tv">...</string>` 等，
AAPT2 不支持 product 属性，必须去除并去重：

```python
# 1. 去除 product 属性
re.sub(r' product="[^"]*"', '', content)

# 2. 去重同名 string（同一文件多版本取第一个）
#    完整的 res 文件处理逻辑参考 tools/gen_aar_maven.py
```

处理脚本保存在 `tools/gen_aar_maven.py` (从 CarSystemUIGradle 复制并适配)

### 3. Monet 改用 jar 引入

```bash
cp aosp/out/soong/.intermediates/frameworks/libs/systemui/monet/monet/android_common/turbine-combined/monet.jar libs/monet.jar
```

`SystemUI-core/build.gradle.kts`:
```kotlin
compileOnly(files("${rootProject.projectDir}/libs/monet.jar"))
```

**对比参考项目**: CarSystemUIGradle 用独立 module (`:SystemUI-monet`)，我们更简洁用 jar。
参考项目的设计假设是 AOSP 的 monet.jar 与 AndroidX 冲突需要切分 module，
但我们的 SDK 已包含 androidx，所以单 jar 足够。

### 4. SystemUI Flags 用预编译 jar

AOSP 编译产物的 `SystemUI_intermediates/classes.jar` 包含
`com.android.systemui.Flags`（aconfig 生成的完整类），不能整 jar 用
（146MB），提取单 class：

```bash
unzip -j aosp/out/target/common/obj/APPS/SystemUI_intermediates/classes.jar \
  com/android/systemui/Flags.class -d /tmp/extracted/
mkdir -p /tmp/extracted/com/android/systemui/
mv /tmp/extracted/Flags.class /tmp/extracted/com/android/systemui/Flags.class
cd /tmp/extracted && jar cf libs/systemui-flags.jar com/
```

同样为 `com.android.server.notification.Flags` 创建单独 jar:
```bash
unzip -j aosp/out/target/common/obj/JAVA_LIBRARIES/services_intermediates/classes.jar \
  'com/android/server/notification/Flags*' -d /tmp/sn/
mkdir -p /tmp/sn/com/android/server/notification/
mv /tmp/sn/Flags.class /tmp/sn/com/android/server/notification/Flags.class
cd /tmp/sn && jar cf libs/server-notification-flags.jar com/
```

## 编译错误数演变

| Commit | 描述 | 错误数 |
|--------|------|--------|
| `5b17012` | 上一轮 (合并 android.jar) | 3,008 |
| **`a7176c7`** | **删除 stub + 加 res-keyguard/res-product + monet.jar** | **2,412** |
| 当前 (未 commit) | 加 systemui-flags.jar (去 SystemUI.Flags.kt stub) | 2,000 |

## 待解决问题

### 问题：server-notification-flags.jar 加入 classpath 但符号未解析

`com.android.server.notification.Flags.screenshareNotificationHiding`
依然 unresolved。验证：

```bash
unzip -p libs/server-notification-flags.jar com/android/server/notification/Flags.class | \
  javap -p | grep screenshareNotificationHiding
# 输出: public static boolean screenshareNotificationHiding();
```

但 Gradle Kotlin compile classpath 报告包含此 jar：
```
--- FlagsJars: [systemui-flags.jar, server-notification-flags.jar]
```

可能原因：
1. AGP 9 Kotlin compile 缓存未刷新
2. `compileOnly()` 在 Kotlin compile classpath 中位置不当
3. SDK android.jar 中可能也有同名类（被遮蔽）

下一步：
- 检查 SDK android.jar 中是否有 `com.android.server.notification.Flags`
- 强制 `--rerun-tasks`
- 试用 `implementation()` 而非 `compileOnly()`

## 参考项目文件对照

| CarSystemUIGradle | SystemUI-Gradle | 说明 |
|--------------------|-----------------|------|
| `libs/framework.jar` (40MB) | `libs/framework.jar` (20MB) | 我们的更精简 |
| `libs/SystemUI-proto.jar` | `libs/SystemUI-proto.jar` | 同源 |
| `libs/SystemUI-tags.jar` | `libs/SystemUI-tags.jar` | 同源 |
| `libs/SystemUI-statsd.jar` | `libs/SystemUI-statsd.jar` | 同源 |
| `libs/SystemUISharedLib.jar` (AAR) | `libs/maven/.../SystemUISharedLib-1.0.0.aar` | 本地 Maven |
| `:SystemUI-monet` module | `libs/monet.jar` (compileOnly) | 我们用 jar |
| `libs/WindowManager-Shell.jar` | `libs/WindowManager-Shell.jar` | 同源 |
| `tools/gen_aar_maven.py` | `tools/gen_aar_maven.py` (从 Car 复制) | 同源 |
| `libs/maven/com/android/systemui/*` | 同 | 本地 Maven 仓库 |

## 后续计划

1. **解决 server-notification-flags.jar 可见性** (上方问题)
2. **生成更多 SystemUI 内部 AAR** (使用 gen_aar_maven.py 模式):
   - Scene framework AAR
   - Compose theme AAR
   - Compose animation/scene AAR
3. **AAR 资源合并**: Scene 框架包含大量 drawable/layout 资源，
   改用 AAR 方式才能正确合并（不能用 jar）
4. **持续 commit/push + 更新本文档**