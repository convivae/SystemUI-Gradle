plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.customization"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 对齐 AOSP SystemUICustomizationLib：src 含 java/kotlin/aidl，res 目录
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            aidl.srcDirs("src")
            res.srcDirs("res")
            manifest.srcFile("AndroidManifest.xml")
        }
    }

    buildFeatures {
        aidl = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlin {
        jvmToolchain(21)
    }

    lint {
        abortOnError = false
    }
}

// AGP builtInKotlin：用顶层 kotlin { compilerOptions { } } 替代废弃的 android.kotlinOptions { }
// 对齐 AOSP kotlincflags: ["-Xjvm-default=all"]
kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xjvm-default=all")
    }
}

dependencies {
    // Framework APIs（allprojects 已注入，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // tier① SystemUI 自有源码模块（对齐 bp static_libs）
    api(project(":SystemUI-animation"))
    api(project(":SystemUI-plugin-core"))
    api(project(":SystemUI-plugin"))
    api(project(":SystemUI-unfold"))
    // 17 bp 新增（Task 072）：SystemUIClocks-CommonLib（customization/Android.bp L36）
    implementation(project(":SystemUI-clocks-common"))

    // tier② AOSP 特有产物 jar
    compileOnly(files("${rootProject.projectDir}/libs/monet.jar"))
    // com.android.systemui.Flags（enableAiClocks；Soong 经 SystemUIPluginLib bp
    // static_libs com_android_systemui_flags_lib 传递；运行时由 core 的
    // implementation 统一 dex）
    compileOnly(files("${rootProject.projectDir}/libs/systemui-flags.jar"))
    // com.android.systemui.shared.Flags（enableAiClocks；Soong 经 SystemUIPluginLib
    // 静态链传递；运行时由 core 的 implementation 统一 dex）
    compileOnly(files("${rootProject.projectDir}/libs/systemui-shared-flags.jar"))
    // animationlib 直接 AAR（含 res）
    api(libs.systemui.animationlib)

    // tier③ 标准第三方（maven 版本依赖）
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.concurrent.futures)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    // FlexClockFaceController.kt 引 androidx.compose.ui.Modifier /
    // layout.onGloballyPositioned（Soong 经 SystemUIPluginLib 静态链传递）
    implementation(libs.compose.ui)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.dagger)
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}
