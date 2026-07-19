plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.plugin"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    
    sourceSets {
        getByName("main") {
            java.srcDirs("src/main")
            manifest.srcFile("src/main/AndroidManifest.xml")
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
    // 项目模块
    implementation(project(":SystemUI-plugin-core"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-shared"))
    
    // Framework APIs
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    
    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    
    // Kotlin
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
}
