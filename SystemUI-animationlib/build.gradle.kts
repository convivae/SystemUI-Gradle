plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.android.app.animation"
    compileSdk = rootProject.extra["compileSdkPreview"] as Int
    buildToolsVersion = "35.0.0"

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
}