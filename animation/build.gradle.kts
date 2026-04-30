plugins {
    id("com.android.library")
}

android {
    namespace = "com.android.systemui.animation"
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
}

afterEvaluate {
    extensions.configure<com.android.build.api.dsl.LibraryExtension> {
        sourceSets["main"].java.srcDirs("src")
        sourceSets["main"].res.srcDirs("res")
    }
}

dependencies {
    implementation("androidx.core:core-animation:1.0.0")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.annotation:annotation:1.8.2")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/WindowManager-Shell-shared.jar"))
    implementation(files("$rootDir/libs/animationlib.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_shared_flags_lib.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_flags_lib.jar"))
}
