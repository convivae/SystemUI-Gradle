plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.common"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src/main/java")
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

    lint {
        abortOnError = false
    }
}

dependencies {
    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // Tracing.kt 用 com.android.app.tracing.coroutines.createCoroutineTracingContext（tier② tracinglib）
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))

    // AndroidX
    implementation(libs.androidx.annotation)

    // Kotlin
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}
