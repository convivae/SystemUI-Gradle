plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.customization"
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
                "$aospDir/frameworks/base/packages/SystemUI/customization/src"
            )
            res.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/customization/res"
            )
            aidl.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/customization/src"
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

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
    implementation(files("$rootDir/libs/SystemUIPluginLib.jar"))
    implementation(files("$rootDir/libs/SystemUIUnfoldLib.jar"))
    implementation(files("$rootDir/libs/monet.jar"))
}
