plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.animation"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            manifest.srcFile("src/AndroidManifest.xml")
        }
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
    
    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
}
