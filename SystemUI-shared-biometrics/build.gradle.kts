// BiometricsSharedLib — 独立 R namespace（com.android.systemui.shared.biometrics）
plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.shared.biometrics"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            res.srcDirs("res")
            manifest.srcFile("AndroidManifest.xml")
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
    implementation(libs.kotlin.stdlib)
}
