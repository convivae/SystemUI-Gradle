plugins {
    id("com.android.library")
}

android {
    namespace = "com.android.systemui.unfold"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlin {
        compilerOptions {
            freeCompilerArgs.add("-Xjvm-default=all")
        }
    }

    buildFeatures {
        aidl = true
    }
}

afterEvaluate {
    extensions.configure<com.android.build.api.dsl.LibraryExtension> {
        sourceSets["main"].java.srcDirs("src")
        sourceSets["main"].aidl.srcDirs("src")
    }
}

dependencies {
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("com.google.dagger:dagger:2.51.1")
    annotationProcessor("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")
}
