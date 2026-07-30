plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.android.app.animation"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src/main/java")
            res.srcDirs("src/main/res")
            manifest.srcFile("src/main/AndroidManifest.xml")
        }
    }

    buildFeatures {
        resValues = false
    }
}

dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // androidx.core 提供 WindowInsetsControllerCompat / WindowCompat
    implementation("androidx.core:core-ktx:1.13.1")
    // androidx.core:core-animation 提供 androidx.core.animation.Interpolator / PathInterpolator
    // 用 api 让下游 compose-core 也能看到
    api("androidx.core:core-animation:1.0.0")
}