// :SystemUI-compose — Platform Compose Core + Scene 合并模块
// 对齐 AOSP compose/core + compose/scene（同工具链、无资源、单向依赖）
plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.compose)
}

android {
    // scene 的 AOSP R namespace（compose/scene/AndroidManifest.xml package，且唯一
    // res 目录 = scene/res；core 无 res 无 R）。scene 源码的无限定 R 因此解析到
    // com.android.compose.animation.scene.R，与 Soong 一致，零源码改动。
    namespace = "com.android.compose.animation.scene"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("core/src", "scene/src")
            kotlin.srcDirs("core/src", "scene/src")
            // AOSP compose/scene bp resource_dirs: ["res"]（scene 唯一 res 源）
            res.srcDirs("scene/res")
            manifest.srcFile("AndroidManifest.xml")
        }
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
// Platform Compose 含 Experimental API（OverscrollEffect / AnimatedContent 等）
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll(
            "-Xjvm-default=all",
            "-opt-in=androidx.compose.foundation.ExperimentalFoundationApi",
            "-opt-in=androidx.compose.animation.ExperimentalAnimationApi",
            "-opt-in=androidx.compose.animation.core.ExperimentalAnimationSpecApi",
            "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api",
            "-opt-in=androidx.compose.material3.windowsizeclass.ExperimentalMaterial3WindowSizeClassApi",
        )
    }
}

dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // aconfig flags（compose/core 与 scene 源码引用 com.android.systemui.Flags.*；
    // AOSP scene bp static_libs com_android_systemui_flags_lib，core 经依赖图获得）
    compileOnly(files("${rootProject.projectDir}/libs/systemui-flags.jar"))
    // mechanics 双库（bp：core "//frameworks/libs/systemui:mechanics"、scene
    // "//frameworks/libs/systemui/mechanics:mechanics" + mechanics-compose；
    // 运行时由 :SystemUI-core 的 implementation(files(...)) 统一入 APK，
    // 此处 compileOnly 避免重复 dex）
    compileOnly(files("${rootProject.projectDir}/libs/mechanics.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/mechanics-compose.jar"))
    // compilelib 变体（bp：scene static_libs compilelib；StlDebugConfig 引
    // com.android.systemui.util.Compile.IS_DEBUG，debug/release 常量不同）
    debugImplementation(files("${rootProject.projectDir}/libs/compilelib-debug.jar"))
    releaseImplementation(files("${rootProject.projectDir}/libs/compilelib-release.jar"))

    // tier① SystemUI 自有源码模块
    api(project(":SystemUI-animation"))
    // animationlib 直接 AAR（含 res）
    implementation(libs.systemui.animationlib)
    implementation(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))

    // tier③ 标准第三方（合并 core + scene 的 Maven 坐标，去重）
    implementation(libs.androidx.annotation)
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.core.animation)
    implementation(libs.androidx.window)
    // bp：compose/core static_libs androidx.window_window-core
    // （windowsizeclass/WindowSizeClass.kt 引 androidx.window.core.layout.WindowSizeClass）
    implementation(libs.androidx.window.core)
    implementation(libs.androidx.savedstate.ktx)
    implementation(libs.androidx.tracing)
    // Compose 1.11.4 — 公网最高保留 ExperimentalAnimatableApi 的版本
    implementation(libs.compose.runtime)
    implementation(libs.compose.foundation)
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.animation)
    implementation(libs.compose.animation.graphics)
    implementation(libs.compose.material3)
    implementation(libs.compose.material3.window.size)
    implementation(libs.compose.material.icons.core)
    implementation(libs.compose.material.icons.extended)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
}
