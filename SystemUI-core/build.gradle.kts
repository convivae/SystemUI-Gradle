plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    // id("kotlin-kapt") // 临时禁用：KAPT 1.9+ 与 Gradle 9.5 不兼容（IR 内部错误）
}

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
        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

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
            // AOSP 源码里的 .aidl 参与源码编译（规则 S：AIDL 是 SystemUI 自有代码，不用 jar）
            // framework 隐藏接口（android.os.IRemoteCallback）由 SysUISdk 的 framework.aidl 补齐，
            // 见 tools/install_sdk.py（规则 F：非 SystemUI 代码不源码复制）
            aidl.srcDirs("src")
            // 资源已独立为 :SystemUI-res（com.android.systemui.res.R namespace）
            manifest.srcFile("AndroidManifest.xml")
        }
        getByName("debug") {
            java.srcDirs("src-debug")
        }
        getByName("release") {
            java.srcDirs("src-release")
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

    lint {
        abortOnError = false
        checkReleaseBuilds = false
    }
}

// Configure kapt for Dagger (built-in in AGP 9.0+)
// 临时禁用：KAPT 1.9+ 与 Gradle 9.5 + Kotlin 2.x 不兼容（IR fake override builder 内部错误）
// kapt {
//     correctErrorTypes = true
//     javacOptions {
//         option("-J--add-opens=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED")
//     }
// }

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

    // msdl / view_capture（frameworks/libs/systemui，tier② prebuilt jar）
    // 原先由 SystemUISharedLib.jar（fat turbine-combined）透传，shared 源码化后需 core 直接依赖
    compileOnly(files("${rootProject.projectDir}/libs/msdl.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/view_capture.jar"))

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
    implementation("androidx.window:window:1.3.0")
    // Lottie 动画（com.airbnb.lottie.* / lottie.compose.*）→ tier③ 标准第三方，用 maven 版本依赖
    // （lottie 见下方 implementation(libs.lottie)；lottie-compose 补 maven）
    implementation(libs.lottie.compose)
    implementation(files("${rootProject.projectDir}/libs/SystemUI-tags.jar"))
    implementation(files("${rootProject.projectDir}/libs/SystemUI-statsd.jar"))
    // Monet (从 AOSP out/.../monet.jar 提取，含 ColorScheme/Shades/Style 等)
    compileOnly(files("${rootProject.projectDir}/libs/monet.jar"))
    implementation(files("${rootProject.projectDir}/libs/systemui-flags.jar"))
    // com.android.settingslib.flags.Flags (aconfig, enableLeAudioSharing 等)
    compileOnly(files("${rootProject.projectDir}/libs/settingslib-flags.jar"))
    // motion_tool_lib (com.android.app.motiontool.*，来自 AOSP frameworks/libs/systemui/motiontoollib)
    compileOnly(files("${rootProject.projectDir}/libs/motion_tool_lib.jar"))
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
    implementation(libs.android.server.notification.flags)
    

    // 直接 AAR（Soong javac + 原始 res + R.txt，无 R.class）
    implementation(libs.systemui.settingslib)
    // SettingsLib-full.jar 含 SettingsLib 子模块类（与 AAR javac 0 重叠），保留
    compileOnly(files("${rootProject.projectDir}/libs/SettingsLib-full.jar"))
    implementation(libs.systemui.iconloader)
    implementation(libs.systemui.wmshell)
    // WindowManager-Shell-shared：WM-Shell 的 static_libs 子模块（ShellTransitions/TransitionUtil 等），
    // Soong javac JAR 不含 static_libs 代码，需单独引入。纯代码无 R 类。
    // WM-Shell-shared 合并 javac+kotlin JAR（含 PhysicsAnimator），改为直接 AAR
    implementation(libs.systemui.wmshell.shared)
    // com.android.systemui.shared.Flags（KeyboardTouchpadTutorialCoreStartable 等使用）
    implementation(files("${rootProject.projectDir}/libs/systemui-shared-flags.jar"))
    // com.google.protobuf.nano.MessageNano（SystemUI-proto 依赖）
    implementation(files("${rootProject.projectDir}/libs/libprotobuf-java-nano.jar"))
    // com.android.server.policy.feature.flags.Flags（ConnectingDisplayViewModel 等使用）
    implementation(files("${rootProject.projectDir}/libs/device-state-flags.jar"))
    implementation(libs.systemui.wifitrackerlib)

    // 注：prebuilt JAR 不再需要，所有子模块都包含完整源码

    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.cardview)
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

    // Dagger
    implementation(libs.dagger)
    // kapt(libs.dagger.compiler) - 临时禁用 KAPT（IR 内部错误，待替换为 KSP）

    // 第三方库
    implementation(libs.guava)
    implementation(libs.lottie)

    // Media3 (for media controls)
    implementation(libs.androidx.media3.common)
    implementation(libs.androidx.media3.session)
    // Compose (用于 Scene 框架与 UI 组件)
    implementation("androidx.compose.runtime:runtime:1.7.5")
    implementation("androidx.compose.animation:animation:1.7.5")
    // animation-graphics: AnimatedImageVector / animatedVectorResource（CommonTile 等）
    implementation("androidx.compose.animation:animation-graphics:1.7.5")
    implementation("androidx.compose.material3:material3:1.3.1")
    // material3-window-size-class: WindowSizeClass（compose windowsizeclass 目录）
    implementation("androidx.compose.material3:material3-window-size-class:1.3.1")
    // Material Components for Android（com.google.android.material.slider.Slider 等，非 compose）
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.compose.foundation:foundation:1.7.5")
    implementation("androidx.compose.ui:ui:1.7.5")
    implementation("androidx.compose.ui:ui-tooling-preview:1.7.5")
    implementation("androidx.compose.ui:ui-graphics:1.7.5")
    implementation("androidx.compose.material:material-icons-core:1.7.5")
    implementation("androidx.compose.material:material-icons-extended:1.7.5")
    implementation("androidx.tracing:tracing:1.2.0")
    // concurrent-futures-ktx: ListenableFuture.await()（media/zen 等）
    implementation("androidx.concurrent:concurrent-futures-ktx:1.2.0")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    // DataStore (对齐 AOSP SystemUI 的 androidx.datastore_datastore-preferences)
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.datastore:datastore-core:1.1.1")
    // SystemUI AIDL：源码里的 .aidl 现由 AGP 源码编译（buildFeatures.aidl=true + aidl.srcDirs("src")）。
    // framework 隐藏接口 android.os.IRemoteCallback 由 SysUISdk 的 framework.aidl 补齐（tools/install_sdk.py），
    // 不源码复制 framework 代码（规则 F）。已删 libs/systemui-aidl.jar：AIDL 是 SystemUI 自有代码，规则 S 要求源码编译。

    // 注：compose/scene（com.android.compose.animation.scene，45 文件）与 compose/core
    //     （com.android.compose）是 SystemUI 自有代码（soong 模块 PlatformComposeSceneTransitionLayout /
    //     PlatformComposeCore），已随 src/ 源码编译，依赖上方 androidx.compose.* maven（tier③）。
    //     全量重编 0 报错，无需再排除或拆独立模块。
}
