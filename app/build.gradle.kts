plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    id("kotlin-kapt")
}

android {
    namespace = "com.android.systemui"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        applicationId = "com.android.systemui"
        minSdk = 35
        targetSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    signingConfigs {
        create("release") {
            storeFile = file("../keystore/platform.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }
    buildTypes {
        debug {
            // SYSOPS: platform-signed so the APK is installable as a system app.
            // See v2 spec §11.7 risk #10. To regenerate keystore, run
            // tools/install_keystore.sh.
            signingConfig = signingConfigs.getByName("release")
        }
    }
}

dependencies {
    implementation(project(":SystemUI-core"))
    implementation(project(":SystemUI-shared"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-customization"))
    implementation(project(":SystemUI-plugin"))
    implementation(project(":SystemUI-plugin-core"))
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/WindowManager-Shell.jar"))
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.dagger)
}
