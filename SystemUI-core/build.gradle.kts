plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.androidx.room)
    id("com.google.devtools.ksp")
}

// Dagger 2.59.2：useBindingGraphFix 自 2.58 起默认启用（修复 subcomponent 绑定解析）
// https://dagger.dev/dev-guide/compiler-options#useBindingGraphFix
// ksp.incremental=false（gradle.properties）避免 KSP2 FIR 解析非确定性崩溃
//   参考：https://github.com/google/ksp/issues/2542

// Configure compile tasks to use framework.jar before Android SDK
val frameworkJars = files(
    "${rootProject.projectDir}/libs/framework.jar",
    "${rootProject.projectDir}/libs/framework-statsd.jar"
)

// No manipulation - use whatever default


android {
    // Task 072（C4 接线）：由 com.android.systemui 改为 com.android.systemui.core。
    // 原因：:SystemUI-application（承接 AOSP 17 完整 manifest，组件名为相对名）的
    // namespace 必须等于 AOSP manifest package = com.android.systemui（merger 按模块
    // namespace 展开相对名）；而 AGP merger 的 unique-namespace 检查
    // （ENFORCE_UNIQUE_PACKAGE_NAMES，默认开启）禁止闭包内两个模块同 namespace
    // （16 时代 Task 050 已实证该报错）。core 的 namespace 是 Gradle-only 标签：
    // core 无 res（R 归 :SystemUI-res）、全仓零处 import com.android.systemui.R、
    // 无 BuildConfig 引用、manifest（396 行权限表）无相对组件名，17 bp 的
    // SystemUI-core 本就无 manifest/package 声明，故改名不承载任何 AOSP 语义。
    // 详见 docs/issues/2026-08-28-c4-gradle-wiring.md §3.1。
    namespace = "com.android.systemui.core"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // AOSP SystemUI-core (android_library) 层零 ProGuard 配置（Task 028 复核确认）；
    // 此前悬挂的 consumer/release proguard 文件引用已删除（Task 029 G1）。

    // AGP 9.0+ 新 DSL 源码目录配置
    // 暂时排除复杂 UI 子包（保留源代码，未来逐步启用）
    // 它们依赖大量 Compose Scene 框架和 AOSP 内部依赖。
    // 排除它们能让 SystemUI-core 主流程（flags/log/settings/dagger/lifecycle）编译通过
    // 而保留所有源代码在目录中，便于将来改进。
    sourceSets {
        getByName("main") {
            // AOSP SystemUI-core 源码根：src + compose/features + compose/facade/enabled + pods
            // 17 bp：pods 生产源按 per-module defaults 并入（ADR 0003 全 pods →
            // :SystemUI-core）。Soong pods/build/Android.bp 的 sysui_api/sysui_main/
            // sysui_dagger defaults 只收 src/{api,main,dagger}/**；src/test
            //（sysui_testlib）、src/testFixtures（sysui_fixtureFiles）、src/preview
            //（sysui_preview）与 multivalentTests/testFixtures 顶层目录均不进
            // 任何生产模块。显式列举生产 src 根 = Soong 语义 1:1。
            java.srcDirs(
                "src",
                "compose/features/src",
                "compose/facade/enabled/src",
                "pods/brightness/src/api",
                "pods/brightness/src/dagger",
                "pods/brightness/src/main",
                "pods/bundle/phone/src/dagger",
                "pods/common/shared/colors/src/api",
                "pods/common/shared/model/src/api",
                "pods/common/ui/compose/src/api",
                "pods/common/ui/compose/windowinsets/src/api",
                "pods/common/ui/icons/src/api",
                "pods/dump/src/api",
                "pods/dump/src/dagger",
                "pods/dump/src/main",
                "pods/flags/src/api",
                "pods/graphics/src/api",
                "pods/graphics/src/dagger",
                "pods/graphics/src/main",
                "pods/headline/ui/src/api",
                "pods/headline/ui/src/dagger",
                "pods/headline/ui/src/main",
                "pods/lifecycle/src/api",
                "pods/log/src/api",
                "pods/log/table/src/api",
                "pods/notifications/content/icon/src/api",
                "pods/notifications/content/src/api",
                "pods/notifications/content/ui/src/api",
                "pods/notifications/content/ui/src/dagger",
                "pods/notifications/content/ui/src/main",
                "pods/notifications/intelligence/rules/src/api",
                "pods/notifications/intelligence/rules/src/dagger",
                "pods/notifications/intelligence/rules/src/main",
                "pods/notifications/intelligence/rules/ui/src/api",
                "pods/notifications/intelligence/rules/ui/src/dagger",
                "pods/notifications/intelligence/rules/ui/src/main",
                "pods/qs/panels/ui/src/api",
                "pods/qs/panels/ui/src/dagger",
                "pods/qs/panels/ui/src/main",
                "pods/retail/data/src/api",
                "pods/retail/data/src/main",
                "pods/retail/domain/src/api",
                "pods/retail/domain/src/main",
                "pods/retail/src/main",
                "pods/scene/src/api",
                "pods/scene/ui/src/api",
                "pods/shade/src/api",
                "pods/src/api",
                "pods/statusbar/chips/ui/src/api",
                "pods/statusbar/pipeline/airplane/data/src/api",
                "pods/statusbar/pipeline/airplane/data/src/main",
                "pods/statusbar/pipeline/airplane/shared/src/api",
                "pods/statusbar/pipeline/airplane/shared/src/main",
                "pods/user/data/src/api",
                "pods/util/kotlin/src/api",
                "pods/util/policy/src/api",
                "pods/util/policy/src/main",
                "pods/util/settings/src/api",
                "pods/util/settings/src/dagger",
                "pods/util/settings/src/main",
                "pods/util/time/src/api",
                "pods/util/time/src/dagger",
                "pods/util/time/src/main",
            )
            kotlin.srcDirs(
                "src",
                "compose/features/src",
                "compose/facade/enabled/src",
                "pods/brightness/src/api",
                "pods/brightness/src/dagger",
                "pods/brightness/src/main",
                "pods/bundle/phone/src/dagger",
                "pods/common/shared/colors/src/api",
                "pods/common/shared/model/src/api",
                "pods/common/ui/compose/src/api",
                "pods/common/ui/compose/windowinsets/src/api",
                "pods/common/ui/icons/src/api",
                "pods/dump/src/api",
                "pods/dump/src/dagger",
                "pods/dump/src/main",
                "pods/flags/src/api",
                "pods/graphics/src/api",
                "pods/graphics/src/dagger",
                "pods/graphics/src/main",
                "pods/headline/ui/src/api",
                "pods/headline/ui/src/dagger",
                "pods/headline/ui/src/main",
                "pods/lifecycle/src/api",
                "pods/log/src/api",
                "pods/log/table/src/api",
                "pods/notifications/content/icon/src/api",
                "pods/notifications/content/src/api",
                "pods/notifications/content/ui/src/api",
                "pods/notifications/content/ui/src/dagger",
                "pods/notifications/content/ui/src/main",
                "pods/notifications/intelligence/rules/src/api",
                "pods/notifications/intelligence/rules/src/dagger",
                "pods/notifications/intelligence/rules/src/main",
                "pods/notifications/intelligence/rules/ui/src/api",
                "pods/notifications/intelligence/rules/ui/src/dagger",
                "pods/notifications/intelligence/rules/ui/src/main",
                "pods/qs/panels/ui/src/api",
                "pods/qs/panels/ui/src/dagger",
                "pods/qs/panels/ui/src/main",
                "pods/retail/data/src/api",
                "pods/retail/data/src/main",
                "pods/retail/domain/src/api",
                "pods/retail/domain/src/main",
                "pods/retail/src/main",
                "pods/scene/src/api",
                "pods/scene/ui/src/api",
                "pods/shade/src/api",
                "pods/src/api",
                "pods/statusbar/chips/ui/src/api",
                "pods/statusbar/pipeline/airplane/data/src/api",
                "pods/statusbar/pipeline/airplane/data/src/main",
                "pods/statusbar/pipeline/airplane/shared/src/api",
                "pods/statusbar/pipeline/airplane/shared/src/main",
                "pods/user/data/src/api",
                "pods/util/kotlin/src/api",
                "pods/util/policy/src/api",
                "pods/util/policy/src/main",
                "pods/util/settings/src/api",
                "pods/util/settings/src/dagger",
                "pods/util/settings/src/main",
                "pods/util/time/src/api",
                "pods/util/time/src/dagger",
                "pods/util/time/src/main",
            )
            // AOSP 源码里的 .aidl 参与源码编译（规则 S：AIDL 是 SystemUI 自有代码，不用 jar）
            // framework 隐藏接口（android.os.IRemoteCallback）由 SysUISdk 的 framework.aidl 补齐，
            // 见 tools/build_sysuisdk.py（规则 F：非 SystemUI 代码不源码复制）
            aidl.srcDirs("src")
            // 资源已独立为 :SystemUI-res（com.android.systemui.res.R namespace）
            manifest.srcFile("AndroidManifest.xml")
        }
        getByName("debug") {
            java.srcDirs("src-debug")
            kotlin.srcDirs("src-debug")
            // AIDL 生成的 Java 源码加入 kotlin sourceSet，使 KSP 能解析 AIDL 接口
            kotlin.srcDir("build/generated/aidl_source_output_dir/debug/out")
        }
        getByName("release") {
            java.srcDirs("src-release")
            kotlin.srcDirs("src-release")
            kotlin.srcDir("build/generated/aidl_source_output_dir/release/out")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    buildFeatures {
        aidl = true
    }

    kotlin {
        jvmToolchain(21)
    }

    // SystemUI-core 的 compose/features 源码使用 Compose experimental API（combinedClickable、
    // pointerInteropFilter、AnimatedContent 等），需全局 opt-in。与 :SystemUI-compose 保持一致。
    // AGP builtInKotlin：已迁移到顶层 kotlin { compilerOptions { } }

    lint {
        abortOnError = false
        checkReleaseBuilds = false
    }
}

// AGP builtInKotlin：用顶层 kotlin { compilerOptions { } } 替代废弃的 android.kotlinOptions { }
// SystemUI-core 的 compose/features 源码使用 Compose experimental API（combinedClickable、
// pointerInteropFilter、AnimatedContent 等），需全局 opt-in。与 :SystemUI-compose 保持一致。
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll(
            "-Xjvm-default=all",
            "-opt-in=androidx.compose.foundation.ExperimentalFoundationApi",
            "-opt-in=androidx.compose.animation.ExperimentalAnimationApi",
            "-opt-in=androidx.compose.animation.core.ExperimentalAnimationSpecApi",
            "-opt-in=androidx.compose.animation.graphics.ExperimentalAnimationGraphicsApi",
            "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api",
            "-opt-in=androidx.compose.material3.windowsizeclass.ExperimentalMaterial3WindowSizeClassApi",
            "-opt-in=androidx.compose.ui.ExperimentalComposeUiApi",
        )
    }
}

// KSP 配置 Dagger 与 Room annotation processor（对齐 AOSP plugins: ["dagger2-compiler",
//   "androidx.room_room-compiler-plugin"]）。KAPT 已移除（IR 内部错误），KSP 2.2.10-2.0.2
//   对齐 AGP builtInKotlin 的 Kotlin 2.2.10。Dagger 2.59.2：useBindingGraphFix 自 2.58 起默认启用。
//   ksp.incremental=false（gradle.properties）避免 KSP2 FIR 非确定性崩溃。

dependencies {
    // 项目模块（对齐 AOSP SystemUI-core static_libs）
    api(project(":SystemUI-res"))
    api(project(":SystemUI-animation"))
    api(project(":SystemUI-common"))
    api(project(":SystemUI-customization"))
    // 17 bp：SystemUI-core static_libs SystemUICustomizationLib 静态链传递
    // SystemUIClocks-CommonLib（clocks res R + ClockLogger.getVisText 等；
    // core 源码 import com.android.systemui.customization.clocks.R as clocksR）
    api(project(":SystemUI-clocks-common"))
    api(project(":SystemUI-plugin"))
    // api（Task 073）：AOSP static_libs 扁平传递——SystemUI-application 的 Dagger
    // 根组件直接引用 shared 的 SysUISingleton / dagger.qualifiers.*；Gradle
    // implementation 不传递 → 改 api 对齐 Soong 语义
    api(project(":SystemUI-shared"))
    api(project(":SystemUI-compose"))
    // kairos（packages/SystemUI/utils/kairos，tier① 规则 S；17 bp SystemUI-core static_libs）
    // api（Task 073）：Dagger 模块签名引用 KairosNetwork，application KSP 需传递可见
    api(project(":SystemUI-utils-kairos"))

    // compilelib 变体（非 SystemUI 代码，tier② jar；debug/release 仅 IS_DEBUG 常量不同）
    debugImplementation(files("${rootProject.projectDir}/libs/compilelib-debug.jar"))
    releaseImplementation(files("${rootProject.projectDir}/libs/compilelib-release.jar"))

    // msdl（frameworks/libs/systemui/msdllib，tier② prebuilt jar；AOSP static_libs runtime/program
    // 输入——SystemUISharedLib static_libs ":msdl"，dex 进 APK，故 implementation）
    // api（Task 073）：Dagger 模块签名引用 MSDLPlayer，application KSP 需传递可见
    api(files("${rootProject.projectDir}/libs/msdl.jar"))
    // view_capture（frameworks/libs/systemui/viewcapturelib，tier② 干净 jar：
    // tools/package_viewcapture_motiontool_jars.py 合并 3 个 owning Soong
    // implementation 输出 javac 9 + kotlin 23 + view_capture_proto 24 = 56 类，
    // 仅 com/android/app/viewcapture/**，去除旧 FAT jar 的 androidx/kotlin/kotlinx/
    // protobuf-lite 污染。AOSP static_libs runtime/program 输入，dex 进 APK，故 implementation。
    // 顺序约束：须先于 protobuf-javalite 就位（其闭包依赖 viewcapture）
    // 17 注（Task 072）：AOSP-17 bp 已无 motiontoollib 依赖（C2 退役），
    // motion_tool_lib.jar 不再产出，仅 viewcapture 闭包保留
    implementation(files("${rootProject.projectDir}/libs/view_capture.jar"))
    // protobuf-javalite（com.google.protobuf.GeneratedMessageLite 等 lite runtime，
    // tier③ 官方 Maven 坐标；AOSP libprotobuf-java-lite 的公网等价物，task 035 R8 Batch 3）
    implementation(libs.protobuf.javalite)

    // tracinglib-platform（提供 launchTraced 等 Trace 协程扩展）
    implementation(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))

    // Framework APIs
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/framework-statsd.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/android.car.jar"))
    // 添加 android_module_lib_stubs_current.jar 提供缺失的 framework stub
    compileOnly(files("${rootProject.projectDir}/libs/android_module_lib_stubs_current.jar"))

    // AOSP bp：java_library "SystemUI-proto" (srcs: ["src/**/*.proto"], proto.type: "nano")
    // AOSP 一等产物 SystemUI-proto.jar（含 15 个 .proto 生成类如 CommunalHubState / QsTileState）。
    // protobuf.nano 运行时由 compileOnly framework.jar 提供。
    implementation(files("${rootProject.projectDir}/libs/SystemUI-proto.jar"))
    // SystemUIUnfoldLib 通过 :SystemUI-shared / :SystemUI-customization 透传
    // androidx.window：FoldingFeature / WindowLayoutInfo 等
    implementation(libs.androidx.window)
    // androidx.window.window-core（compose/features 源码引
    // androidx.window.core.layout.WindowSizeClass；bp 经 androidx prebuilts 链）
    implementation(libs.androidx.window.core)
    // bp static_libs androidx.autofill_autofill（AutofillRendererService 引
    // androidx.autofill.inline.UiVersions / InlineSuggestionUi）
    implementation(libs.androidx.autofill)
    // Lottie 动画（com.airbnb.lottie.* / lottie.compose.*）→ tier③ 标准第三方，用 maven 版本依赖
    // （lottie 见下方 implementation(libs.lottie)；lottie-compose 补 maven）
    implementation(libs.lottie.compose)
    implementation(files("${rootProject.projectDir}/libs/SystemUI-tags.jar"))
    implementation(files("${rootProject.projectDir}/libs/SystemUI-statsd.jar"))
    // Monet（56 类确定性产物，tools/package_monet_jar.py 合并两个 Soong javac 输出：
    // monet 9 + libmonet 47；errorprone 由官方 Maven error_prone_annotations 供给。
    // monet+libmonet 为 AOSP static_libs runtime/program 输入，dex 进 APK，故 implementation）
    implementation(files("${rootProject.projectDir}/libs/monet.jar"))
    implementation(files("${rootProject.projectDir}/libs/systemui-flags.jar"))
    // com.android.tools.r8.keepanno.annotations.KeepTarget/UsesReflection
    // (SystemUIAppComponentFactoryBase; Maven 上无此 artifact，AOSP 用 prebuilts/r8/keepanno-annotations.jar)
    compileOnly(files("${rootProject.projectDir}/libs/keepanno-annotations.jar"))
    // com.android.settingslib.flags.Flags (aconfig, enableLeAudioSharing 等)
    // Android.bp lists aconfig_settingslib_flags_java_lib under libs and states that
    // its implementation is already in framework.jar; use the header only for compilation.
    compileOnly(files("${rootProject.projectDir}/libs/settingslib-flags.jar"))
    // com.android.settingslib.media.flags.Flags (aconfig, removeUnnecessaryRouteScanning 等)
    implementation(files("${rootProject.projectDir}/libs/settingslib-media-flags.jar"))
    // contextualeducationlib (com.android.systemui.contextualeducation.GestureType 等，
    // 来自 frameworks/libs/systemui/contextualeducationlib，tier② jar)
    implementation(files("${rootProject.projectDir}/libs/contextualeducationlib.jar"))
    // PlatformMotionTestingComposeValues (platform.test.motion.compose.values.*，
    // 来自 platform_testing/libraries/motion/compose/values，tier② jar；BouncerContent 等用 motionTestValues)
    implementation(files("${rootProject.projectDir}/libs/PlatformMotionTestingComposeValues.jar"))
    // Traceur 双 AAR（recordissue 用 PresetTraceConfigs/TraceConfig + com.android.traceur.res.R；
    // manifest 合并 CONTROL_UI_TRACING 等 5 权限，故 AAR 而非 jar；ADR 0001 直接 AAR）
    // TraceurCommon = 15 类 ∪ perfetto_config_java_protos 625 类 = 640 类（bp static_libs 并入，先例 WM-Shell）
    implementation(files("${rootProject.projectDir}/libs/aars/TraceurCommon.aar"))
    // Traceur-res = res-only（105 文件，namespace com.android.traceur.res；R 类由 AGP 从 R.txt 重新生成）
    implementation(files("${rootProject.projectDir}/libs/aars/Traceur-res.aar"))

    // server-notification Flags (AOSP @aconfig Flags) - 显式声明，避免 Kotlin 编译器遗漏
    // 配合 root build.gradle.kts 中的 allprojects 注入以保证顺序
    // （AOSP notification_flags_lib javac 全量产物，5 类 runtime 集；tier② jar，2026-08-20 Batch 2）
    implementation(files("${rootProject.projectDir}/libs/notification-flags.jar"))
    // launcher3 aconfig flags（com.android.launcher3.Flags；iconloader_base static_libs
    // 进入 APK 打包闭包——AOSP static_libs runtime/program 输入，故 implementation）
    implementation(files("${rootProject.projectDir}/libs/launcher3-flags.jar"))
    // SettingsLib IllustrationPreference aconfig flags（com.android.settingslib.widget.flags.Flags；
    // SettingsLib 子模块 static_libs runtime/program 输入，故 implementation）
    implementation(files("${rootProject.projectDir}/libs/settingslib-widget-flags.jar"))
    // SettingsLib SelectorWithWidgetPreference aconfig flags：17 上游已删除该 flags lib
    //（其 Android.bp 无 flags static_lib、SystemUI-17 零 import；Task 071 退役产物），
    // 依赖行随 C4 一并移除（Task 072）

    // surfaceeffects 三库（Task 072，C4 接线；17 SystemUI-core bp static_libs
    // SurfaceEffectsComposeLib；SystemUI-17 源码 import 全部三个 namespace
    // com.android.systemui.surfaceeffects.{core,compose,view}.* —— AuthRippleView /
    // AuthRippleScrim / WiredChargingRippleController / KeyboardDockingIndication 等）。
    // frameworks/libs/systemui/surfaceeffects（规则 F tier② jar：bp 无 resource_dirs、
    // 源树无 res）；tools/package_misc_jars.py 冻结指纹产出，dex 进 APK，故 implementation
    implementation(files("${rootProject.projectDir}/libs/SurfaceEffectsCoreLib.jar"))
    implementation(files("${rootProject.projectDir}/libs/SurfaceEffectsComposeLib.jar"))
    implementation(files("${rootProject.projectDir}/libs/SurfaceEffectsViewLib.jar"))
    // uilatencystats flags（Task 072；17 SystemUI-core bp static_libs
    // uilatencystats_flags_core_java_lib；运行时包 com.android.server.ui_latency_stats；
    // tools/package_aconfig_jars.py 产出）
    implementation(files("${rootProject.projectDir}/libs/uilatencystats-flags.jar"))
    // mechanics 双库（Task 073，C4b；17 SystemUI-core bp static_libs L559
    // "//frameworks/libs/systemui/mechanics/compose:mechanics-compose"；源码 import
    // com.android.mechanics.{behavior,compose.modifier}.*）。规则 F tier② jar
    //（bp 无 resource_dirs）；tools/package_misc_jars.py 冻结指纹产出，dex 进 APK
    implementation(files("${rootProject.projectDir}/libs/mechanics.jar"))
    implementation(files("${rootProject.projectDir}/libs/mechanics-compose.jar"))
    // displaylib（Task 073，C4b；17 SystemUI bp static_libs L570/781/823。
    // frameworks/libs/systemui/displaylib——纯 Kotlin + dagger 生成类，
    // tier② jar；59 个 17 源文件 import com.android.app.displaylib.*）
    // api（Task 073）：GlobalRootComponent 签名引用 PerDisplayRepository，
    // application KSP 需传递可见（Soong static_libs 扁平语义）
    api(files("${rootProject.projectDir}/libs/displaylib.jar"))
    // displaylib kapt 半边（Task 074 / C4c，R2 G5 + R4 实证）：bp plugins:
    // dagger2-compiler 的 kapt 生成类；其中 5 个 *_Factory 已由我方
    // :SystemUI-application KSP Dagger 重新生成（R8 duplicate-class 实证），
    // 仅剩 3 个 DaggerDisplayLibComponent 类需真实字节（KSP 无法从 jar 内
    // 已编译接口生成组件实现；DisplayLibComponentKt.createDisplayLibComponent
    // invokestatic DaggerDisplayLibComponent.factory()）。
    implementation(files("${rootProject.projectDir}/libs/displaylib-kapt.jar"))
    // usertypelib（Task 073，C4b；Soong 经 WindowManager-Shell-shared 静态链
    // L59 进 SystemUI；AAR 不含静态依赖类 → 独立 jar）
    implementation(files("${rootProject.projectDir}/libs/usertypelib.jar"))
    // bubbles-user-model（Task 074 / C4c，R2 G4）：17 bp WindowManager-Shell-defaults
    // static_libs L114；wmshell AAR bytecode 引 BubbleUserInfo
    // （BubbleViewInfoTask.populateCommonInfo）。纯 Kotlin 无 res → tier② jar（1 类）。
    implementation(files("${rootProject.projectDir}/libs/bubbles-user-model.jar"))
    // aconfig_settings_flags_lib（Task 073，C4b；17 core bp static_libs L571；
    // com.android.settings.flags.Flags.biometricsOnboardingEducation 等）
    implementation(files("${rootProject.projectDir}/libs/settings-flags.jar"))
    // am-flags（Task 074 / C4c，R2 G2）：17 bp WindowManager-Shell-defaults
    // static_libs L127 am_flags_lib；wmshell AAR bytecode 引
    // com.android.server.am.Flags（DesktopTaskChangeListener.addTask 等）。
    implementation(files("${rootProject.projectDir}/libs/am-flags.jar"))
    // settingstheme-flags（Task 074 / C4c，R2 G3）：SettingsLibSettingsTheme bp
    // static_libs aconfig_settingstheme_exported_flags_java_lib；Theme AAR 的
    // SettingsThemeHelper.isExpressiveDesignEnabled 引
    // com.android.settingslib.widget.theme.flags.Flags。
    implementation(files("${rootProject.projectDir}/libs/settingstheme-flags.jar"))
    // wm_shell_protolog-groups（Task 073，C4b；Soong 经 WindowManager-Shell
    // 静态链进 SystemUI；BubblesManager static-import ShellProtoLogGroup）
    implementation(files("${rootProject.projectDir}/libs/wmshell-protolog.jar"))
    // personalcontext_ace_visualizer + _client（Task 073，C4b；17 SystemUI-core bp
    // static_libs；源码 import visualizer.{compat,connector}.* / common.wrappers.wrap）。
    // 规则 F tier② AAR（frameworks/libs/systemui/ace，含 res）；两个 R namespace 拆双 AAR；
    // visualizer AAR 合并 ace_common 类闭包（bp static_libs，TraceurCommon 先例）；
    // 单 consumer 族 → 直接 AAR（Task 059 例外）；tools/package_aosp_aar.py 产出
    // api（Task 073）：SystemUIModule 签名引用 visualizer 类，application KSP 需传递可见
    api(files("${rootProject.projectDir}/libs/aars/personalcontext_ace_visualizer.aar"))
    implementation(files("${rootProject.projectDir}/libs/aars/personalcontext_ace_client.aar"))
    // kotlin-parcelize-runtime（Task 074 / C4c，R2 G6）：ace client bp static_libs L34
    // 引 kotlin-parcelize-runtime（@Parcelize CLASS-retention 注解）；AAR bytecode 引用 →
    // R8 闭包需要运行时 provider。官方坐标（tier③）2.2.10，对齐项目 Kotlin 版本。
    implementation(libs.kotlin.parcelize.runtime)
    // SerialPortAccessDialog（Task 073，C4b；17 SystemUI-core bp static_libs；
    // frameworks/base/libs/serial/accessdialog，tier② AAR 含 res；manifest 携带
    // AccessDialogActivity 声明 + MANAGE_SERIAL_PORTS 权限，必须 AAR 交付；
    // android:theme=@style/Theme.SystemUI.Dialog.Alert 由 app 合并资源解析（bp static_libs SystemUI-res）
    implementation(files("${rootProject.projectDir}/libs/aars/SerialPortAccessDialog.aar"))

    // 直接 AAR（Soong javac + 原始 res + R.txt，无 R.class）
    // api（Task 073）：Dagger 模块签名引用 LocalBluetoothManager 等，
    // application KSP 需传递可见（Soong static_libs 扁平语义）
    api(libs.systemui.settingslib)
    // setupcompat：AOSP SettingsLib 经 setupdesign→setupcompat 传递获得 compile classpath
    // （com.google.android.setupcompat.util.WizardManagerHelper.SETTINGS_SECURE_USER_SETUP_COMPLETE 等）；
    // external/setupcompat android_library（含 res），tier② 直接 AAR（libs/aars/，单 consumer 族，task 059）。
    implementation(files("${rootProject.projectDir}/libs/aars/setupcompat.aar"))
    // iconloader：直接 AAR（libs/aars/，单 consumer 族，task 059）
    // api（Task 073）：Dagger 模块签名引用 IconProvider，application KSP 需传递可见
    api(files("${rootProject.projectDir}/libs/aars/iconloader.aar"))
    implementation(libs.systemui.wmshell)
    // WindowManager-Shell-aidls（Task 074 / C4c，R2 G1）：17 bp WindowManager-Shell-defaults
    // static_libs L127 将 WindowManager-Shell-aidls（src/**/*.aidl，80 类 Stub/Proxy/Listener）
    // 静态链 dex 进 APK；wmshell AAR 不含静态依赖类 → 独立冻结 jar（task073 已冻结）
    // 补 R8 runtime 闭包。与 wmshell AAR / shared AAR 类集交集实测 0（无重复类）。
    // :SystemUI-shared 侧 compileOnly 保留（编译期可见，不进 runtime classpath）。
    implementation(files("${rootProject.projectDir}/libs/wmshell-aidls.jar"))
    // WindowManager-Shell-shared：WM-Shell 的 static_libs 子模块（ShellTransitions/TransitionUtil 等），
    // Soong javac JAR 不含 static_libs 代码，需单独引入。纯代码无 R 类。
    // WM-Shell-shared 合并 javac+kotlin JAR（含 PhysicsAnimator），改为直接 AAR
    implementation(libs.systemui.wmshell.shared)
    // LowLightDreamLib: com.android.dream.lowlight.util.TruncatedInterpolator 等
    // (frameworks/base/libs/dream/lowlight，AOSP core static_libs)；直接 AAR（libs/aars/，单 consumer 族，task 059）
    // api（Task 073）：Dagger 模块签名引用 LowLightDreamComponent.Factory，
    // application KSP 需传递可见
    api(files("${rootProject.projectDir}/libs/aars/LowLightDreamLib.aar"))
    // com.android.systemui.shared.Flags（KeyboardTouchpadTutorialCoreStartable 等使用）
    implementation(files("${rootProject.projectDir}/libs/systemui-shared-flags.jar"))
    // zxing-core: SettingsLib 的 Soong static_libs（com.google.zxing.WriterException 等），
    // AOSP 把它的 classes dex 进 APK，故用 implementation（tier③ 官方坐标，task 027；本地 jar 已退役）
    implementation(libs.zxing.core)
    // Wi-Fi aconfig flags（com.android.wifi.flags.Flags；WifiTrackerLib static_libs
    // 经 core 进入 APK 打包闭包——AOSP static_libs runtime/program 输入，故 implementation）
    implementation(files("${rootProject.projectDir}/libs/wifi-flags.jar"))
    // WM-Shell aconfig flags（com.android.wm.shell.Flags；WindowManager-Shell static_libs
    // 进入 APK 打包闭包——AOSP static_libs runtime/program 输入，故 implementation）
    implementation(files("${rootProject.projectDir}/libs/wm-shell-flags.jar"))
    // Framework exportable-aconfig hidden-twin 族（task 057，用户方案 M）：
    // 14 个 owning java_aconfig_library（window / device-state-feature / android-os /
    // smartspace / content-pm / biometrics / usb / net-platform / permission / provider /
    // security / service-controls / service-notification / quickaccesswallet）在 Soong 中被
    // JarJarProvider 重写至 com.android.internal.hidden_from_bootclasspath.*，AGP 不继承该
    // 重写；现统一打包为单个确定性合并 JAR（自 AOSP javac 源合并，字典序 + 固定时间戳
    // + 固定压缩，连跑两次 sha256 相同；每源过五类 validator，类/.uau 逐字节等于源）。
    // 生成：`uv run python tools/package_aconfig_jars.py --merge-framework`
    implementation(files("${rootProject.projectDir}/libs/systemui-aconfig-flags.jar"))
    // com.google.protobuf.nano.MessageNano（SystemUI-proto 依赖；tier③ 官方坐标，task 027。
    // AOSP 私有 com.google.protobuf.nano.android.* 3 类全仓零引用，由 framework.jar/platform 兑底）
    implementation(libs.protobuf.javanano)
    // com.android.server.policy.feature.flags.Flags（ConnectingDisplayViewModel 等使用）
    implementation(files("${rootProject.projectDir}/libs/device-state-flags.jar"))
    // WifiTrackerLib：直接 AAR（libs/aars/，单 consumer 族，task 059）
    implementation(files("${rootProject.projectDir}/libs/aars/WifiTrackerLib.aar"))
    // SettingsLibColor：com.android.settingslib.color.R（settingslib_color_blue400 等）
    // 独立 android_library（res-only，无 srcs），被 SettingsLibIllustrationPreference 依赖。
    // SystemUI 源码 SideFpsOverlayViewModel.kt 直接引用 com.android.settingslib.color.R。
    implementation(libs.systemui.settingslib.color)

    // 注：prebuilt JAR 不再需要，所有子模块都包含完整源码

    // AndroidX
    implementation(libs.androidx.annotation)
    // AOSP SystemUI-core static_libs: "jsr305"; provides javax.annotation.concurrent.GuardedBy.
    implementation(libs.jsr305)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.cardview)
    // api（Task 073）：application 根组件 GlobalRootComponent 签名引用
    // AsyncLayoutInflater，KSP 需传递可见
    api(libs.androidx.asynclayoutinflater)
    implementation(libs.androidx.concurrent.futures)
    // androidx.core.animation.Animator/ValueAnimator/AnimatorSet/ObjectAnimator/Interpolator
    // AOSP PlatformAnimationLib bp 有 androidx.core_core-animation；core 通过 static_libs 传递获得。
    // Gradle implementation 不传递,需显式声明(同 Phase A Task 4 给 compose 的处理)。
    implementation(libs.androidx.core.animation)
    // api（Task 073）：Dagger 模块签名引用 MotionLayout，application KSP 需传递可见
    api(libs.androidx.constraintlayout)
    implementation(libs.androidx.constraintlayout.core)
    implementation(libs.androidx.core.ktx)
    // api（Task 073）：application 生成的 Dagger 代码经 wmshell-shared
    // PhysicsAnimator 引 FrameCallbackScheduler，需传递可见
    api(libs.androidx.dynamicanimation)
    implementation(libs.androidx.exifinterface)
    implementation(libs.androidx.fragment.ktx)
    implementation(libs.androidx.leanback)
    implementation(libs.androidx.leanback.preference)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.service)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.androidx.mediarouter)
    // explicit pin: mediarouter 1.9.0-alpha01 transitively resolves media 1.4.1 which lacks DESCRIPTION_EXTRAS_KEY_COMPLETION_PERCENTAGE
    implementation(libs.androidx.media)
    implementation(libs.androidx.palette)
    implementation(libs.androidx.preference)
    implementation(libs.androidx.recyclerview)
    implementation(libs.androidx.slice.builders)
    implementation(libs.androidx.slice.core)
    implementation(libs.androidx.slice.view)
    implementation(libs.androidx.viewpager2)

    // Kotlin
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.coroutines.core)

    // Dagger：KSP 生成 DaggerReferenceGlobalRootComponent 等（对齐 AOSP plugins: ["dagger2-compiler"]）
    // Dagger 2.59.2：useBindingGraphFix 自 2.58 起默认启用，无需手动配置 ksp{} arg
    implementation(libs.dagger)
    ksp(libs.dagger.compiler)

    // 第三方库
    implementation(libs.guava)
    implementation(libs.lottie)

    // Media3 (for media controls)
    implementation(libs.androidx.media3.common)
    implementation(libs.androidx.media3.session)
    // Compose 1.11.4（公网最高保留 ExperimentalAnimatableApi 的版本）
    api(libs.androidx.activity.compose)  // api（Task 073）：Dagger 签名引 ComponentActivity
    // api（Task 073）：core 内 Dagger 组件（ScreenCaptureUiComponent 等签名引
    // compose 类型），application KSP 需传递可见
    api(libs.compose.runtime)
    api(libs.compose.animation)
    // animation-graphics: AnimatedImageVector / animatedVectorResource（CommonTile 等）
    implementation(libs.compose.animation.graphics)
    implementation(libs.compose.material3)
    // material3-window-size-class: WindowSizeClass（compose windowsizeclass 目录）
    implementation(libs.compose.material3.window.size)
    // Material Components for Android（com.google.android.material.slider.Slider 等，非 compose）
    // 1.13.0-alpha08：trackIconActiveColor/trackIconActiveEnd 需此版本（AOSP material-design-x
    //   prebuilt 与 Maven 版字节完全一致 1985863 bytes；规则③优先官方 Maven 坐标）
    implementation(libs.google.material)
    api(libs.compose.foundation)  // api（Task 073）：Dagger 签名引 InteractionSource
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.material.icons.core)
    implementation(libs.compose.material.icons.extended)
    implementation(libs.androidx.tracing)
    // concurrent-futures-ktx: ListenableFuture.await()（media/zen 等）
    implementation(libs.androidx.concurrent.futures.ktx)
    // Room 2.8.4：fallbackToDestructiveMigration(dropAllTables=) 需 2.7+（AOSP 内部版本不在公网）
    // room-compiler 通过 KSP 运行（对齐 AOSP plugins: ["androidx.room_room-compiler-plugin"]）
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)
    // DataStore (对齐 AOSP SystemUI 的 androidx.datastore_datastore-preferences)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.datastore.core)
    // SystemUI AIDL：源码里的 .aidl 现由 AGP 源码编译（buildFeatures.aidl=true + aidl.srcDirs("src")）。
    // framework 隐藏接口 android.os.IRemoteCallback 由 SysUISdk 的 framework.aidl 补齐（tools/build_sysuisdk.py），
    // 不源码复制 framework 代码（规则 F）。已删 libs/systemui-aidl.jar：AIDL 是 SystemUI 自有代码，规则 S 要求源码编译。

    // 注：compose/scene（com.android.compose.animation.scene，45 文件）与 compose/core
    //     （com.android.compose）是 SystemUI 自有代码（soong 模块 PlatformComposeSceneTransitionLayout /
    //     PlatformComposeCore），已随 src/ 源码编译，依赖上方 androidx.compose.* maven（tier③）。
    //     全量重编 0 报错，无需再排除或拆独立模块。
}

// builtInKotlin 下 KSP 任务默认不依赖 AIDL 编译任务，导致 AIDL 生成的接口
// （如 IHomeControlsRemoteProxy）在 KSP 处理 Dagger 时不可见。按 variant 精确接线。
tasks.matching { it.name == "kspDebugKotlin" }.configureEach { dependsOn("compileDebugAidl") }
tasks.matching { it.name == "kspReleaseKotlin" }.configureEach { dependsOn("compileReleaseAidl") }

// Room schema 导出（对齐 AOSP Android.bp 的 -Aroom.schemaLocation=.../schemas）：
// 历史版本 JSON（CommunalDatabase v1–v5）自 AOSP byte-exact 复制于仓库根 schemas/，
// Room 编译期据此校验迁移链（DB v6+ AutoMigration 依赖）。
// 官方 Room Gradle Plugin 负责设置 schema 输入/输出参数并接线校验任务；
// 早期手写 KSP 内部参数的迁移记录见 docs/issues/2026-08-19-room-schema-export.md。
room {
    schemaDirectory(rootProject.file("schemas").absolutePath)
}

