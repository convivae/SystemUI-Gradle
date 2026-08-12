// :SystemUI-compose — Platform Compose Core + Scene 合并模块
// 对齐 AOSP compose/core + compose/scene（同工具链、无资源、单向依赖）
plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.android.compose"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("core/src", "scene/src")
            kotlin.srcDirs("core/src", "scene/src")
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
