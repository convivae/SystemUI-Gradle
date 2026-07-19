plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.customization"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    
    kotlin {
        jvmToolchain(21)
    }
}

dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
}
