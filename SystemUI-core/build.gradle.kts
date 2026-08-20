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
    namespace = "com.android.systemui"
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
            java.srcDirs(
                "src",
                "compose/features/src",
                "compose/facade/enabled/src",
                "pods",
            )
            kotlin.srcDirs(
                "src",
                "compose/features/src",
                "compose/facade/enabled/src",
                "pods",
            )
            // AOSP 源码里的 .aidl 参与源码编译（规则 S：AIDL 是 SystemUI 自有代码，不用 jar）
            // framework 隐藏接口（android.os.IRemoteCallback）由 SysUISdk 的 framework.aidl 补齐，
            // 见 tools/install_sdk.py（规则 F：非 SystemUI 代码不源码复制）
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
    implementation(project(":SystemUI-res"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-common"))
    implementation(project(":SystemUI-customization"))
    implementation(project(":SystemUI-plugin"))
    implementation(project(":SystemUI-shared"))
    implementation(project(":SystemUI-compose"))

    // compilelib 变体（非 SystemUI 代码，tier② jar；debug/release 仅 IS_DEBUG 常量不同）
    debugImplementation(files("${rootProject.projectDir}/libs/compilelib-debug.jar"))
    releaseImplementation(files("${rootProject.projectDir}/libs/compilelib-release.jar"))

    // msdl（frameworks/libs/systemui/msdllib，tier② prebuilt jar；AOSP static_libs runtime/program
    // 输入——SystemUISharedLib static_libs ":msdl"，dex 进 APK，故 implementation）
    implementation(files("${rootProject.projectDir}/libs/msdl.jar"))
    // view_capture（frameworks/libs/systemui/viewcapturelib，tier② 干净 jar：
    // tools/package_viewcapture_motiontool_jars.py 合并 3 个 owning Soong
    // implementation 输出 javac 9 + kotlin 23 + view_capture_proto 24 = 56 类，
    // 仅 com/android/app/viewcapture/**，去除旧 FAT jar 的 androidx/kotlin/kotlinx/
    // protobuf-lite 污染。AOSP static_libs runtime/program 输入，dex 进 APK，故 implementation；
    // 顺序约束：必须先于 motion_tool_lib 就位（其闭包依赖 viewcapture + protobuf）
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
    // motion_tool_lib (com.android.app.motiontool.*，来自 AOSP frameworks/libs/systemui/motiontoollib)
    // 干净 jar：tools/package_viewcapture_motiontool_jars.py 合并 2 个 owning Soong
    // implementation 输出 kotlin 8 + motion_tool_proto 57 = 65 类，仅 com/android/app/motiontool/**。
    // AOSP static_libs runtime/program 输入，dex 进 APK，故 implementation；
    // 顺序约束：必须在 view_capture + protobuf-javalite 之后（其 static 闭包依赖二者）
    implementation(files("${rootProject.projectDir}/libs/motion_tool_lib.jar"))
    // contextualeducationlib (com.android.systemui.contextualeducation.GestureType 等，
    // 来自 frameworks/libs/systemui/contextualeducationlib，tier② jar)
    implementation(files("${rootProject.projectDir}/libs/contextualeducationlib.jar"))
    // PlatformMotionTestingComposeValues (platform.test.motion.compose.values.*，
    // 来自 platform_testing/libraries/motion/compose/values，tier② jar；BouncerContent 等用 motionTestValues)
    implementation(files("${rootProject.projectDir}/libs/PlatformMotionTestingComposeValues.jar"))
    // Traceur (record issue 用 PresetTraceConfigs/TraceConfig + com.android.traceur.res.R)
    compileOnly(files("${rootProject.projectDir}/libs/TraceurCommon.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/traceur-res-R.jar"))

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
    // SettingsLib SelectorWithWidgetPreference aconfig flags
    // （com.android.settingslib.widget.selectorwithwidgetpreference.flags.Flags；同上）
    implementation(files("${rootProject.projectDir}/libs/settingslib-selector-flags.jar"))

    // 直接 AAR（Soong javac + 原始 res + R.txt，无 R.class）
    implementation(libs.systemui.settingslib)
    // SettingsLib-full.jar 含 SettingsLib 子模块类（与 AAR javac 0 重叠），保留
    compileOnly(files("${rootProject.projectDir}/libs/SettingsLib-full.jar"))
    // setupcompat：AOSP SettingsLib 经 setupdesign→setupcompat 传递获得 compile classpath
    // （com.google.android.setupcompat.util.WizardManagerHelper.SETTINGS_SECURE_USER_SETUP_COMPLETE 等）；
    // external/setupcompat android_library（含 res），tier② AAR 经本地 Maven 交付。
    implementation(libs.systemui.setupcompat)
    implementation(libs.systemui.iconloader)
    implementation(libs.systemui.wmshell)
    // WindowManager-Shell-shared：WM-Shell 的 static_libs 子模块（ShellTransitions/TransitionUtil 等），
    // Soong javac JAR 不含 static_libs 代码，需单独引入。纯代码无 R 类。
    // WM-Shell-shared 合并 javac+kotlin JAR（含 PhysicsAnimator），改为直接 AAR
    implementation(libs.systemui.wmshell.shared)
    // LowLightDreamLib: com.android.dream.lowlight.util.TruncatedInterpolator 等
    // (frameworks/base/libs/dream/lowlight，AOSP core static_libs)
    implementation(libs.systemui.lowlight.dream.lib)
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
    // com.google.protobuf.nano.MessageNano（SystemUI-proto 依赖；tier③ 官方坐标，task 027。
    // AOSP 私有 com.google.protobuf.nano.android.* 3 类全仓零引用，由 framework.jar/platform 兑底）
    implementation(libs.protobuf.javanano)
    // com.android.server.policy.feature.flags.Flags（ConnectingDisplayViewModel 等使用）
    implementation(files("${rootProject.projectDir}/libs/device-state-flags.jar"))
    implementation(libs.systemui.wifitrackerlib)
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
    implementation(libs.androidx.asynclayoutinflater)
    implementation(libs.androidx.concurrent.futures)
    // androidx.core.animation.Animator/ValueAnimator/AnimatorSet/ObjectAnimator/Interpolator
    // AOSP PlatformAnimationLib bp 有 androidx.core_core-animation；core 通过 static_libs 传递获得。
    // Gradle implementation 不传递,需显式声明(同 Phase A Task 4 给 compose 的处理)。
    implementation(libs.androidx.core.animation)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.constraintlayout.core)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
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
    implementation(libs.androidx.activity.compose)
    implementation(libs.compose.runtime)
    implementation(libs.compose.animation)
    // animation-graphics: AnimatedImageVector / animatedVectorResource（CommonTile 等）
    implementation(libs.compose.animation.graphics)
    implementation(libs.compose.material3)
    // material3-window-size-class: WindowSizeClass（compose windowsizeclass 目录）
    implementation(libs.compose.material3.window.size)
    // Material Components for Android（com.google.android.material.slider.Slider 等，非 compose）
    // 1.13.0-alpha08：trackIconActiveColor/trackIconActiveEnd 需此版本（AOSP material-design-x
    //   prebuilt 与 Maven 版字节完全一致 1985863 bytes；规则③优先官方 Maven 坐标）
    implementation(libs.google.material)
    implementation(libs.compose.foundation)
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
    // framework 隐藏接口 android.os.IRemoteCallback 由 SysUISdk 的 framework.aidl 补齐（tools/install_sdk.py），
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

