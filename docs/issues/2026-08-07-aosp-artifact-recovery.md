# AOSP Artifact Recovery 执行记录

**日期**：2026-08-07
**计划**：`docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md`
**前序**：Phase A.5 已解决 B1/B2/B3，core Kotlin 编译已启动

## 背景

core 编译链推进到 AAR transform 阶段，三个本地 Maven AAR 的 `classes.jar` 含 R.class，AGP 报 "already contains entry"：

```text
Failed to transform SettingsLib-1.0.0.aar
  Zip '...SettingsLib-1.0.0-api.jar' already contains entry 'com/android/settingslib/R.class'
Failed to transform iconloader-1.0.0.aar
  ... 'com/android/launcher3/icons/R.class'
Failed to transform WindowManager-Shell-1.0.0.aar
  ... 'com/android/wm/shell/R.class'
```

根因：`gen_aar_maven.py` 把 `busybox/R.jar` 错误合入 `classes.jar`（已确认失败实验）。

## 当前 artifact 交付位置与审计（Task 1 Step 3）

| Artifact | 当前交付 | .class | R 类数 | sysui 类数 |
|----------|---------|--------|--------|------------|
| SettingsLib | `libs/maven/.../SettingsLib-1.0.0.aar` | 616 | 15 | 0 |
| iconloader | `libs/maven/.../iconloader-1.0.0.aar` | 66 | 7 | 0 |
| WindowManager-Shell | `libs/maven/.../WindowManager-Shell-1.0.0.aar` | 14265 | 16 | 179 |
| WifiTrackerLib | `libs/maven/.../WifiTrackerLib-1.0.0.aar` | 63 | 0 | 0 |

WifiTrackerLib 已干净（无 R 类），但为统一管理仍切换为直接 AAR。

## 当前依赖消费者（Task 1 Step 2）

```text
SystemUI-shared/build.gradle.kts:60   compileOnly(files("libs/WindowManager-Shell.jar"))
SystemUI-animation/build.gradle.kts:48 compileOnly(files("libs/WindowManager-Shell.jar"))
app/build.gradle.kts:78               compileOnly(files("libs/WindowManager-Shell.jar"))
SystemUI-core/build.gradle.kts:118    compileOnly(files("libs/WindowManager-Shell.jar"))
SystemUI-core/build.gradle.kts:157    implementation(libs.systemui.settingslib)
SystemUI-core/build.gradle.kts:162    implementation(libs.systemui.iconloader)
SystemUI-core/build.gradle.kts:163    implementation(libs.systemui.wmshell)
SystemUI-core/build.gradle.kts:164    implementation(libs.systemui.wifitrackerlib)
SystemUI-res/build.gradle.kts:37     api(libs.systemui.settingslib)
```

## 执行步骤与错误数演变

| 步骤 | 操作 | 结果 |
|------|------|------|
| Task 1 | 记录 baseline | 本 issue |
| Task 2 | 扩展 packager 生成 4 个直接 AAR | 待执行 |
| Task 3 | WifiTrackerLib 切直接 AAR | 待执行 |
| Task 4 | iconloader 切直接 AAR | 待执行 |
| Task 5 | SettingsLib 切直接 AAR | 待执行 |
| Task 6 | WM-Shell 切直接 AAR + 删 fat JAR | ✅ 完成 |

## Task 6 额外恢复

WM-Shell 直接 AAR 的 javac JAR 不含 static_libs 代码，需额外恢复：
- `libs/WindowManager-Shell-shared.jar`（64 classes，无 R/sysui）：含 `ShellTransitions`/`TransitionUtil` 等，加到 core(implementation)/animation(compileOnly)/shared(compileOnly)
- `libs/systemui-shared-flags.jar`（已存在，5 classes）：含 `com.android.systemui.shared.Flags`，加到 shared(compileOnly)

## 里程碑：core Kotlin 编译启动

AAR transform 阻塞全部消除后，core Kotlin 编译跑了 24 秒，产生 **708 个真实 Kotlin 错误**——这是真正的编译期诊断信息（Compose experimental API、Unresolved reference 等），不是 build 配置 blocker。这是项目首次取得可信的 core Kotlin 错误基线。
| Task 7 | 删废弃 Maven 坐标 | 待执行 |
| Task 8 | manifest merge 验证 | 待执行 |
| Task 9 | core + APK 证据 | 待执行 |

## 待解决问题

- 四个直接 AAR 的 `classes.jar` 必须无任何 R.class
- WM-Shell 直接 AAR 必须无 `com/android/systemui/**` 类
- 每次只切一个 artifact，切完单独验证
- 不运行 `gen_aar_maven.py`，不用 `turbine-combined` fat JAR
