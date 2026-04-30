plugins {
    id("com.android.library")
}

android {
    namespace = "com.android.systemui.customization"
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
        sourceSets["main"].res.srcDirs("res")
        sourceSets["main"].aidl.srcDirs("src")
    }
}

dependencies {
    implementation(project(":plugin"))
    implementation(project(":unfold"))
    implementation(project(":animation"))

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("com.google.dagger:dagger:2.51.1")
    annotationProcessor("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
    implementation(files("$rootDir/libs/SystemUIPluginLib.jar"))
    implementation(files("$rootDir/libs/SystemUIUnfoldLib.jar"))
    implementation(files("$rootDir/libs/monet.jar"))
}
