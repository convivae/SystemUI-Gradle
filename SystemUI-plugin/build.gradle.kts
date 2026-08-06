plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.plugin"
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
    // Internal project modules
    implementation(project(":SystemUI-plugin-core"))
    implementation(project(":SystemUI-animation"))

    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // clocks 插件用 com.android.systemui.log.core.MessageBuffer → 依赖合并后的 :SystemUI-common
    api(project(":SystemUI-common"))

    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    // clocks 插件 ClockFaceLayout 用 androidx.constraintlayout.widget.ConstraintSet（对齐 AOSP plugin/Android.bp）
    implementation(libs.androidx.constraintlayout)
    // plugins/qs/TileDetailsViewModel 用 androidx.compose.runtime.Composable
    implementation("androidx.compose.runtime:runtime:1.7.5")

    // Kotlin
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
}