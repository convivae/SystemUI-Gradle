plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.animation"
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
                "$aospDir/frameworks/base/packages/SystemUI/animation/src"
            )
            res.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/animation/res"
            )
        }
    }
}

dependencies {
    implementation("androidx.core:core-animation:1.0.0")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.annotation:annotation:1.8.2")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/WindowManager-Shell-shared.jar"))
    implementation(files("$rootDir/libs/animationlib.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_shared_flags_lib.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_flags_lib.jar"))
}
