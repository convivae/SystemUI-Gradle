plugins {
    id("com.android.library")
}

android {
    namespace = "com.android.systemui.plugin"
    // JD MOD: Use custom SDK platform with merged android.jar
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlin {
        compilerOptions {
            freeCompilerArgs.add("-Xjvm-default=all")
        }
    }

    buildFeatures {
        aidl = true
    }

    // JD MOD: Configure source directories for AGP 9.x
    // Use sourceSets directly in android block
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
        }
    }
}

dependencies {
    implementation(project(":plugin-core"))
    implementation(project(":common"))
    implementation(project(":log"))

    implementation("androidx.annotation:annotation:1.8.2")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.compose.ui:ui:1.7.0")
    implementation("androidx.compose.runtime:runtime:1.7.0")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/SystemUICommon.jar"))
    implementation(files("$rootDir/libs/SystemUILogLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
}
