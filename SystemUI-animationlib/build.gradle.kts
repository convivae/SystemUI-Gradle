plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.app.animation"
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
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    // androidx.core:core-animation 提供 androidx.core.animation.* 类
    implementation("androidx.core:core-animation:1.0.0")
    implementation(libs.kotlin.stdlib)
}