# C5：定位四个错误平台类引用的来源

**日期**：2026-09-01  
**状态**：Task 080 调查完成，待 Chief 独立复核

## 背景与范围

Debug 与 Release APK 均已能编译。当前 Release runtime blocker 是 APK 仍引用四个旧平台 aconfig 类名，而 Android 17 设备提供 `com.android.internal.hidden_from_bootclasspath.*` 名称。本任务只读检查已有 Release APK、module `build/**` 产物和当前 JAR/AAR 依赖；不修改构建行为，不运行 Gradle、Soong、JarJar、模拟器或 ADB，也不设计转换实现。

四个目标为：

- `android.app.Flags`
- `android.os.Flags`
- `android.view.accessibility.Flags`
- `com.android.window.flags.Flags`

## 方法与去重口径

`/tmp/task080-c5-reference-origins/scan_flags_refs.py` 解析 JVM class 常量池，以 `this_class` 判定定义，以真实 `CONSTANT_Class` 条目判定引用；它不把任意 UTF-8 子串当成引用。扫描结果保存在 `hits.jsonl`（550 行），归组明细保存在 `report-details.md`。

计数按 **target + referencing-class identity** 去重。同一编译类在 `built_in_kotlinc`/`javac` loose class、`compile_library_classes_jar`、`full_jar`、`runtime_library_classes_jar` 和 `aar_main_jar` 中的副本只算一个来源类；模块 `aar_libs_directory` 中复制的依赖 JAR，以及 `libs/aars/` 与字节相同的本地 Maven AAR，也只算证据副本，不增加来源计数。

## Release APK 基线

- APK：`app/build/outputs/apk/release/app-release.apk`
- SHA-256：`f389bd459df24b1cead6e440da2b60fa6885e16d67a8abfbd5d6bb64ea2975ef`
- 四个旧名在 `classes*.dex` 中均存在，因此 `APK_CRITICAL_REFERENCES=4/4`。
- 规则文件：`/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`
- 规则 SHA-256：`f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`（725 条 exact rules，726 个物理行）。
- 现有 checker 仍应得到 `RESULT=FAIL`；本任务不改变 APK。

## 来源汇总

| 旧类名 | 去重引用类 | 已证明来源 |
|---|---:|---|
| `android.app.Flags` | 50 | `:SystemUI-core` 47；SettingsLib 1；WindowManager-Shell 2 |
| `android.os.Flags` | 7 | `:SystemUI-core` 4；`:SystemUI-shared` 1；tracinglib 1；aconfig JAR 1 |
| `android.view.accessibility.Flags` | 5 | `:SystemUI-core` 4；WindowManager-Shell 1 |
| `com.android.window.flags.Flags` | 104 | `:SystemUI-core` 13；`:SystemUI-shared` 1；WindowManager-Shell 83；WindowManager-Shell-shared 5；personalcontext AAR 1；aconfig JAR 1 |

合计 166 个 target/reference-class 对，四个目标全部可归属，`UNKNOWN=0`。

## Canonical artifact 身份与 SHA-256

### Project-local module 输出

下列 release runtime class JAR 作为模块类集的稳定代表；其 loose class 和其他 JAR intermediate 是同批编译类的副本：

| 模块 | 代表产物 | SHA-256 |
|---|---|---|
| `:SystemUI-core` | `SystemUI-core/build/intermediates/runtime_library_classes_jar/release/bundleLibRuntimeToJarRelease/classes.jar` | `a5574653d15ad28276198de13882e2c701be46d5623e2241dafe9afbfa7e93c3` |
| `:SystemUI-shared` | `SystemUI-shared/build/intermediates/runtime_library_classes_jar/release/bundleLibRuntimeToJarRelease/classes.jar` | `568e03483ba9ed6726fba711bc5166de6b98d0670ce52b33a4068fb448244f07` |

### Runtime/program JAR 输入

| 依赖 | 路径 | SHA-256 |
|---|---|---|
| systemui aconfig | `libs/systemui-aconfig-flags.jar` | `992021b783b3bebbaf50ebf176a0cbf578d7db8a3fb46ec9c7244f0fbb4c5cf7` |
| tracinglib platform | `libs/prebuilts/tracinglib-platform.jar` | `aa5077c38e9991970ca2230df7709e8d36fa8c36c79abc9b015668e8f72f6dcd` |

`libs/systemui-aconfig-flags.jar` 是 runtime/program 输入中 `android.os.Flags` 与 `com.android.window.flags.Flags` 两个旧名定义的唯一来源，同时其两个 `CustomFeatureFlags` 类也引用相应旧名。

### Runtime/program AAR 输入

AAR 外层文件与内嵌 `classes.jar` 的 SHA-256 分开记录：

| 依赖 | AAR 路径 | AAR SHA-256 | `classes.jar` SHA-256 |
|---|---|---|---|
| SettingsLib 2.0.1 | `libs/maven/com/android/systemui/SettingsLib/2.0.1/SettingsLib-2.0.1.aar` | `718dae39519323f0c004c6d961aba4ed0f3be5a165828db4653cf0fcd36730da` | `fc5767c9dbb9a33000c48b96f52422bf80edc01a3e547ddd5e8cb256a9fc868b` |
| WindowManager-Shell 2.0.0 | `libs/maven/com/android/systemui/WindowManager-Shell/2.0.0/WindowManager-Shell-2.0.0.aar` | `af096dda2124b969ec9c66998444826f3d9e69d8ef8d7e95c1f0b8a8c23acf87` | `e9b41a7ec705b01236ebe7a2830ad395d0c1993dd243f7d4bcb3b4e90ea6f974` |
| WindowManager-Shell-shared 2.0.1 | `libs/maven/com/android/systemui/WindowManager-Shell-shared/2.0.1/WindowManager-Shell-shared-2.0.1.aar` | `545cac20314566464cc08ac8880d433d5334942dcaad006502a8e493cbca14aa` | `6b09bd46527ce51d0a28575b59138763368ac56c105fec3862867240ef9de0f2` |
| personalcontext ace visualizer | `libs/aars/personalcontext_ace_visualizer.aar` | `1540a3e3ec857ccaccb1c17c56e8e1c70299362b0b1550ece6c9889cd5492df3` | `4581836463f15e518ad6a9a7a43132da71739affb09b2caa84615da240fbdd70` |

对应 `libs/aars/SettingsLib.aar`、`libs/aars/WindowManager-Shell.aar`、`libs/aars/WindowManager-Shell-shared.aar` 的外层 SHA 分别与上表本地 Maven AAR 完全相同，因此不另计来源。

### compileOnly 隔离

`libs/framework.jar`（SHA-256 `a2ff898903296097fa12951e786f8620cb213113a0325add81b9e0bb7ff9009d`）定义全部四个旧名，但它是 compileOnly/library classpath，不是 APK program/runtime 输入，不能把这些定义归入后续 program-input 转换范围。

## 逐目标引用类明细

以下列表按引用类身份去重；完整机器记录（含每个 intermediate 路径、artifact SHA 和 class SHA）在 `/tmp/task080-c5-reference-origins/hits.jsonl`。

#### `android.app.Flags`

- **project-local `:SystemUI-core`** — release 编译产物（`built_in_kotlinc`/`javac` loose 类与 `compile_library_classes_jar`/`full_jar`/`runtime_library_classes_jar`/`aar_main_jar` 为同一批类的重复中间产物，去重后 47 类）

  `com/android/systemui/notifications/intelligence/rules/data/repository/ConversationPartnersRepositoryImpl`、`com/android/systemui/notifications/intelligence/rules/data/repository/NotificationRulesRepositoryImpl`、`com/android/systemui/notifications/intelligence/rules/shared/NmContextualDisplayLaunch`、`com/android/systemui/notifications/intelligence/rules/ui/composable/NotificationRulesActivity`、`com/android/systemui/notifications/intelligence/rules/ui/viewmodel/NotificationRuleEditViewModelImpl`、`com/android/systemui/notifications/ui/composable/NotificationsKt`、`com/android/systemui/notifications/ui/composable/NotificationsShadeOverlay`、`com/android/systemui/qs/tiles/ModesDndTile`、`com/android/systemui/qs/tiles/impl/modes/domain/interactor/ModesDndTileDataInteractor`、`com/android/systemui/qs/ui/composable/QuickSettingsScene`、`com/android/systemui/shade/ui/composable/ShadeScene`、`com/android/systemui/statusbar/CommandQueue`、`com/android/systemui/statusbar/NotificationGroupingUtil`、`com/android/systemui/statusbar/chips/notification/ui/viewmodel/NotifChipsViewModel`、`com/android/systemui/statusbar/chips/ui/compose/ChipContentKt`、`com/android/systemui/statusbar/chips/ui/viewmodel/OngoingActivityChipsViewModel$unrefinedChips$2`、`com/android/systemui/statusbar/notification/ConversationNotificationProcessor`、`com/android/systemui/statusbar/notification/NmSummarizationAllFlag`、`com/android/systemui/statusbar/notification/collection/BundleEntry`、`com/android/systemui/statusbar/notification/collection/coordinator/BundleCoordinator$bundler$1`、`com/android/systemui/statusbar/notification/collection/coordinator/NotifCoordinatorsImpl`、`com/android/systemui/statusbar/notification/collection/coordinator/SummarizationCoordinator`、`com/android/systemui/statusbar/notification/collection/coordinator/SummarizationCoordinator$attach$2`、`com/android/systemui/statusbar/notification/icon/IconManager`、`com/android/systemui/statusbar/notification/promoted/AODPromotedNotificationViewUpdater`、`com/android/systemui/statusbar/notification/promoted/PromotedNotificationContentExtractorImpl`、`com/android/systemui/statusbar/notification/row/ExpandableNotificationRow`、`com/android/systemui/statusbar/notification/row/HeadsUpStyleProviderImpl`、`com/android/systemui/statusbar/notification/row/NotificationContentView`、`com/android/systemui/statusbar/notification/row/NotificationConversationInfo`、`com/android/systemui/statusbar/notification/row/NotificationInfo`、`com/android/systemui/statusbar/notification/row/NotificationMenuRow`、`com/android/systemui/statusbar/notification/row/NotificationRowContentBinderImpl$Companion`、`com/android/systemui/statusbar/notification/row/PartialConversationInfo`、`com/android/systemui/statusbar/notification/row/dagger/EligibilityStaticModule$providesAFlagEligibility$1`、`com/android/systemui/statusbar/notification/row/icon/AppIconProviderImpl`、`com/android/systemui/statusbar/notification/row/icon/NotificationRowIconViewInflaterFactory$createIconProvider$2`、`com/android/systemui/statusbar/notification/row/ui/viewbinder/SingleLineViewBinder`、`com/android/systemui/statusbar/notification/shared/NmContextualDisplay`、`com/android/systemui/statusbar/notification/shared/NotificationChipFromCompactContent`、`com/android/systemui/statusbar/notification/shared/StatusBarHeadline`、`com/android/systemui/statusbar/notification/stack/NotificationChildrenContainer`、`com/android/systemui/statusbar/notification/stack/NotificationSectionsManager`、`com/android/systemui/statusbar/notification/stack/ui/viewbinder/SummarizationOnboardingViewBinder$bind$2$3`、`com/android/systemui/statusbar/pipeline/shared/ui/composable/StatusBarRootKt`、`com/android/systemui/statusbar/pipeline/shared/ui/viewmodel/HeadlineItemsAdapterImpl`、`com/android/systemui/statusbar/pipeline/shared/ui/viewmodel/HomeStatusBarViewModelImpl`


- **external** `libs/maven/com/android/systemui/SettingsLib/2.0.1/SettingsLib-2.0.1.aar` — SettingsLib-2.0.1 (本地 Maven AAR; libs/aars 原件字节等同)，1 类：

  `com/android/settingslib/fuelgauge/PowerAllowlistBackend`


- **external** `libs/maven/com/android/systemui/WindowManager-Shell/2.0.0/WindowManager-Shell-2.0.0.aar` — WindowManager-Shell-2.0.0 (本地 Maven AAR)，2 类：

  `com/android/wm/shell/pip/PipTransitionController`、`com/android/wm/shell/pip2/phone/PipUiStateChangeController`

#### `android.os.Flags`

- **project-local `:SystemUI-core`** — release 编译产物（`built_in_kotlinc`/`javac` loose 类与 `compile_library_classes_jar`/`full_jar`/`runtime_library_classes_jar`/`aar_main_jar` 为同一批类的重复中间产物，去重后 4 类）

  `com/android/systemui/bouncer/ui/composable/PasswordBouncerKt`、`com/android/systemui/compose/PerfettoSdkTracer`、`com/android/systemui/dreams/dagger/DreamModule`、`com/android/systemui/lowlight/LowLightBehaviorCoreStartable`


- **project-local `:SystemUI-shared`** — release 编译产物（`built_in_kotlinc`/`javac` loose 类与 `compile_library_classes_jar`/`full_jar`/`runtime_library_classes_jar`/`aar_main_jar` 为同一批类的重复中间产物，去重后 1 类）

  `com/android/keyguard/BasePasswordTextView`


- **external** `libs/systemui-aconfig-flags.jar` — systemui-aconfig-flags.jar (直接 jar)，1 类：

  `android/os/CustomFeatureFlags`


- **external** `libs/prebuilts/tracinglib-platform.jar` — tracinglib-platform.jar (直接 jar)，1 类：

  `com/android/app/tracing/coroutines/TraceContextElement`

#### `android.view.accessibility.Flags`

- **project-local `:SystemUI-core`** — release 编译产物（`built_in_kotlinc`/`javac` loose 类与 `compile_library_classes_jar`/`full_jar`/`runtime_library_classes_jar`/`aar_main_jar` 为同一批类的重复中间产物，去重后 4 类）

  `com/android/systemui/accessibility/SystemActions`、`com/android/systemui/accessibility/shortcutchooser/domain/interactor/ShortcutChooserDialogInteractor`、`com/android/systemui/accessibility/shortcutchooser/ui/startable/ShortcutChooserDialogStartable`、`com/android/systemui/accessibility/shortcutchooser/ui/viewmodel/ShortcutChooserDialogViewModel`


- **external** `libs/maven/com/android/systemui/WindowManager-Shell/2.0.0/WindowManager-Shell-2.0.0.aar` — WindowManager-Shell-2.0.0 (本地 Maven AAR)，1 类：

  `com/android/wm/shell/startingsurface/SplashscreenContentDrawer`

#### `com.android.window.flags.Flags`

- **project-local `:SystemUI-core`** — release 编译产物（`built_in_kotlinc`/`javac` loose 类与 `compile_library_classes_jar`/`full_jar`/`runtime_library_classes_jar`/`aar_main_jar` 为同一批类的重复中间产物，去重后 13 类）

  `com/android/keyguard/mediator/ScreenOnCoordinator`、`com/android/systemui/LauncherProxyService$1`、`com/android/systemui/accessibility/FullscreenMagnificationController`、`com/android/systemui/actioncorner/data/repository/ActionCornerSettingRepository`、`com/android/systemui/display/flags/DisplayComponentRepositoryFlag`、`com/android/systemui/display/flags/WmCallbackForSysDecorFlag`、`com/android/systemui/keyguard/KeyguardViewMediator`、`com/android/systemui/keyguard/WindowManagerLockscreenVisibilityManager`、`com/android/systemui/navigationbar/TaskbarDelegate`、`com/android/systemui/shade/display/EnsureWallpaperDrawnOnDisplaySwitch`、`com/android/systemui/shade/display/PendingDisplayChangeController`、`com/android/systemui/statusbar/gesture/GesturePointerEventListener`、`com/android/systemui/wallpapers/dagger/WallpaperModule$Companion`


- **project-local `:SystemUI-shared`** — release 编译产物（`built_in_kotlinc`/`javac` loose 类与 `compile_library_classes_jar`/`full_jar`/`runtime_library_classes_jar`/`aar_main_jar` 为同一批类的重复中间产物，去重后 1 类）

  `com/android/systemui/shared/system/ActivityManagerWrapper`


- **external** `libs/maven/com/android/systemui/WindowManager-Shell/2.0.0/WindowManager-Shell-2.0.0.aar` — WindowManager-Shell-2.0.0 (本地 Maven AAR)，83 类：

  `com/android/wm/shell/ShellTaskOrganizer`、`com/android/wm/shell/apptoweb/AppToWebRepositoryImpl`、`com/android/wm/shell/apptoweb/AppToWebShellCommandHandler`、`com/android/wm/shell/apptoweb/AppToWebUtils`、`com/android/wm/shell/apptoweb/BaseOpenByDefaultDialog`、`com/android/wm/shell/apptoweb/OpenByDefaultDialog`、`com/android/wm/shell/apptoweb/OpenByDefaultDialogView`、`com/android/wm/shell/apptoweb/OpenByDefaultFirstRunPrompt`、`com/android/wm/shell/apptoweb/OpenByDefaultFirstRunPromptView`、`com/android/wm/shell/back/BackAnimationController$BackTransitionHandler`、`com/android/wm/shell/back/CrossActivityBackAnimation`、`com/android/wm/shell/back/DefaultCrossActivityBackAnimation`、`com/android/wm/shell/bubbles/BubbleController`、`com/android/wm/shell/bubbles/BubbleController$1`、`com/android/wm/shell/bubbles/BubbleHelperImpl`、`com/android/wm/shell/common/pip/PipDesktopState`、`com/android/wm/shell/common/split/SplitLayout`、`com/android/wm/shell/compatui/letterbox/LetterboxCommandHandler`、`com/android/wm/shell/compatui/letterbox/lifecycle/TaskInfoLetterboxLifecycleEventFactory`、`com/android/wm/shell/compatui/letterbox/roundedcorners/RoundedCornersLetterboxController`、`com/android/wm/shell/dagger/WMShellBaseModule`、`com/android/wm/shell/dagger/WMShellModule`、`com/android/wm/shell/desktopai/core/TriggerManager$1`、`com/android/wm/shell/desktopai/dagger/DesktopAIModule`、`com/android/wm/shell/desktopmode/DesktopMixedTransitionHandler`、`com/android/wm/shell/desktopmode/DesktopModeShellCommandHandler`、`com/android/wm/shell/desktopmode/DesktopModeUtils`、`com/android/wm/shell/desktopmode/DesktopScrimController`、`com/android/wm/shell/desktopmode/DesktopTaskPositionKt`、`com/android/wm/shell/desktopmode/DesktopTasksController`、`com/android/wm/shell/desktopmode/DesktopTasksController$DeskDeactivationFromOverviewScheduler`、`com/android/wm/shell/desktopmode/DesktopTasksTransitionObserver`、`com/android/wm/shell/desktopmode/DesktopWallpaperActivity`、`com/android/wm/shell/desktopmode/DisplayDisconnectTransitionHandler`、`com/android/wm/shell/desktopmode/PipDisplayReconnectHandler`、`com/android/wm/shell/desktopmode/ShellDesktopStateImpl`、`com/android/wm/shell/desktopmode/clientfullscreenrequest/DesktopFullscreenRequestHandler`、`com/android/wm/shell/desktopmode/common/DefaultHomePackageSupplier`、`com/android/wm/shell/desktopmode/data/DesktopRepository`、`com/android/wm/shell/desktopmode/data/DesktopRepositoryInitializerImpl$initialize$1`、`com/android/wm/shell/desktopmode/data/persistence/DesktopPersistentRepository$addOrUpdateRepository$2`、`com/android/wm/shell/desktopmode/desktopfirst/DesktopDisplayModeController`、`com/android/wm/shell/desktopmode/desktopwallpaperactivity/DesktopWallpaperActivityUtils`、`com/android/wm/shell/desktopmode/education/AppHandleEducationController`、`com/android/wm/shell/desktopmode/education/AppToWebEducationFilter`、`com/android/wm/shell/desktopmode/homescreenpeeking/DesktopHomeScreenPeekController`、`com/android/wm/shell/desktopmode/multidesks/RootTaskDesksOrganizer`、`com/android/wm/shell/freeform/FreeformTaskTransitionObserver`、`com/android/wm/shell/fullscreen/FullscreenReconnectHandler`、`com/android/wm/shell/hierarchy/updates/HierarchyUpdater`、`com/android/wm/shell/keyguard/KeyguardTransitionHandler`、`com/android/wm/shell/pinnedlayer/phone/PinnedLayerFlags`、`com/android/wm/shell/pip2/phone/PipTransitionState`、`com/android/wm/shell/splitscreen/SplitScreenTransitions`、`com/android/wm/shell/splitscreen/SplitStatusBarHider`、`com/android/wm/shell/splitscreen/StageCoordinator`、`com/android/wm/shell/startingsurface/SnapshotWindowCreator`、`com/android/wm/shell/startingsurface/TaskSnapshotWindow`、`com/android/wm/shell/taskview/TaskViewTaskController`、`com/android/wm/shell/taskview/TaskViewTransitions`、`com/android/wm/shell/transition/ActivityPlanner`、`com/android/wm/shell/transition/DefaultMixedTransition`、`com/android/wm/shell/transition/DefaultTransitionHandler`、`com/android/wm/shell/transition/FocusTransitionObserver`、`com/android/wm/shell/transition/RemoteTransitionHandler`、`com/android/wm/shell/transition/Transitions`、`com/android/wm/shell/windowdecor/DefaultWindowDecoration`、`com/android/wm/shell/windowdecor/DesktopModeWindowDecorViewModel`、`com/android/wm/shell/windowdecor/DesktopModeWindowDecorViewModel$TaskPositionerFactory`、`com/android/wm/shell/windowdecor/DragDetector`、`com/android/wm/shell/windowdecor/DragPositioningCallbackUtility`、`com/android/wm/shell/windowdecor/HandleMenu`、`com/android/wm/shell/windowdecor/LayoutMenu$LayoutMenuView`、`com/android/wm/shell/windowdecor/MultiDisplayVeiledResizeTaskPositioner`、`com/android/wm/shell/windowdecor/WindowDecoration`、`com/android/wm/shell/windowdecor/WindowDecorationInsets`、`com/android/wm/shell/windowdecor/WindowingPillView`、`com/android/wm/shell/windowdecor/caption/AppHeaderController`、`com/android/wm/shell/windowdecor/caption/CaptionController`、`com/android/wm/shell/windowdecor/caption/FullscreenHeaderController`、`com/android/wm/shell/windowdecor/viewholder/AppHandleViewHolder`、`com/android/wm/shell/windowdecor/viewholder/AppHeaderViewHolder`、`com/android/wm/shell/windowdecor/viewholder/FullscreenHeaderViewHolder`


- **external** `libs/maven/com/android/systemui/WindowManager-Shell-shared/2.0.1/WindowManager-Shell-shared-2.0.1.aar` — WindowManager-Shell-shared-2.0.1 (本地 Maven AAR)，5 类：

  `com/android/wm/shell/shared/FocusTransitionListener`、`com/android/wm/shell/shared/TransitionUtil`、`com/android/wm/shell/shared/bubbles/BubbleFlagHelper`、`com/android/wm/shell/shared/desktopmode/DesktopModeStatus`、`com/android/wm/shell/shared/desktopmode/DesktopStateImpl`


- **external** `libs/aars/personalcontext_ace_visualizer.aar` — personalcontext_ace_visualizer (直接 AAR)，1 类：

  `com/android/personalcontext/ace/visualizer/templates/utils/RemoteActionUtils`


- **external** `libs/systemui-aconfig-flags.jar` — systemui-aconfig-flags.jar (直接 jar)，1 类：

  `com/android/window/flags/CustomFeatureFlags`


## 最小结论：后续转换必须覆盖的已证明输入类别

只依据本任务证据，后续转换需要覆盖：

1. project-local Android library 的 release 编译类输出：`:SystemUI-core`、`:SystemUI-shared`；
2. 直接 runtime JAR：`libs/systemui-aconfig-flags.jar`、`libs/prebuilts/tracinglib-platform.jar`；
3. 本地 Maven AAR 的 `classes.jar`：SettingsLib、WindowManager-Shell、WindowManager-Shell-shared；
4. 直接 AAR 的 `classes.jar`：personalcontext ace visualizer。

此清单只描述已证明的输入类别，不选择或设计实现机制。`libs/framework.jar` 明确排除，因为它是 compileOnly/library input。

## 结果

```text
APK_CRITICAL_REFERENCES=4/4
ORIGINS_PROVEN=4/4
UNKNOWN=0
RESULT=PASS
```

## 验证与构建声明

- 已运行 class-file 常量池只读扫描，并通过 artifact/class identity 去重。
- 已核对 APK、规则文件、canonical JAR/AAR、AAR 内嵌 `classes.jar` 的 SHA-256。
- 未运行 Gradle、Soong/Ninja、JarJar、模拟器或 ADB。
- 未修改源码、Gradle、工具、SDK、`libs/**`、AOSP 或 `out/**`。
- Release 静态 gate 仍为预期的 `RESULT=FAIL`，因为 Task 080 仅定位来源、没有修复行为。

## 后续

由 Chief 独立复核本报告后，另行制定一个小型实现任务，在 class compilation 与 D8/R8 之间只处理本报告证明的 program inputs；实现、重编与双 APK runtime gate 不属于 Task 080。
