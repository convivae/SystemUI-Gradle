plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.shared"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/shared/src"
            )
            res.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/shared/res"
            )
            aidl.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/shared/src"
            )
        }
    }

    buildFeatures {
        aidl = true
    }
}

dependencies {
    implementation(project(":plugin"))
    implementation(project(":unfold"))
    implementation(project(":animation"))
    implementation(project(":common"))

    // AndroidX
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("androidx.concurrent:concurrent-futures:1.2.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")

    // Kotlin coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")

    // Dagger
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/BiometricsSharedLib.jar"))
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
    implementation(files("$rootDir/libs/SystemUIPluginLib.jar"))
    implementation(files("$rootDir/libs/SystemUIUnfoldLib.jar"))
    implementation(files("$rootDir/libs/WindowManager-Shell-shared.jar"))
    implementation(files("$rootDir/libs/tracinglib-platform.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_shared_flags_lib.jar"))
    implementation(files("$rootDir/libs/msdl.jar"))
    implementation(files("$rootDir/libs/view_capture.jar"))
}
