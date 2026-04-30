plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.unfold"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/unfold/src")
            aidl.srcDirs("$aospDir/frameworks/base/packages/SystemUI/unfold/src")
        }
    }

    buildFeatures {
        aidl = true
    }
}

dependencies {
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")
}
