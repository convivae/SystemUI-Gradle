plugins {
    id("com.android.application")
    id("com.google.protobuf")
}

android {
    namespace = "com.android.systemui"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.android.systemui"
        minSdk = 34
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        javaCompileOptions {
            annotationProcessorOptions {
                arguments += mapOf(
                    "dagger.fastInit" to "enabled",
                    "dagger.explicitBindingConflictsWithInject" to "ERROR",
                    "dagger.strictMultibindingValidation" to "enabled"
                )
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    buildFeatures {
        aidl = true
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                file("proguard.flags"),
                file("proguard_common.flags"),
                file("proguard_kotlin.flags")
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    lint {
        baseline = file("lint-baseline.xml")
    }
}

afterEvaluate {
    extensions.configure<com.android.build.api.dsl.ApplicationExtension> {
        sourceSets["main"].manifest.srcFile("src/main/AndroidManifest.xml")
        sourceSets["main"].java.srcDirs("src/main/java", "src/main/java/compose")
        sourceSets["main"].res.srcDirs("src/main/res")
        sourceSets["main"].aidl.srcDirs("src/main/java")
    }
}

dependencies {
    // Internal modules
    implementation(project(":shared"))
    implementation(project(":customization"))
    implementation(project(":animation"))
    implementation(project(":common"))
    implementation(project(":log"))
    implementation(project(":utils"))

    // AndroidX - Core
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.viewpager2:viewpager2:1.1.0")
    implementation("androidx.legacy:legacy-support-v4:1.0.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.preference:preference:1.2.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.concurrent:concurrent-futures:1.2.0")
    implementation("androidx.concurrent:concurrent-futures-ktx:1.2.0")
    implementation("androidx.mediarouter:mediarouter:1.7.0")
    implementation("androidx.palette:palette:1.0.0")
    implementation("androidx.legacy:legacy-preference-v14:1.0.0")
    implementation("androidx.leanback:leanback:1.2.0")
    implementation("androidx.slice:slice-core:1.1.0")
    implementation("androidx.slice:slice-view:1.1.0")
    implementation("androidx.slice:slice-builders:1.1.0")
    implementation("androidx.arch.core:core-runtime:2.2.0")
    implementation("androidx.lifecycle:lifecycle-common-java8:2.8.4")
    implementation("androidx.lifecycle:lifecycle-extensions:2.2.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.exifinterface:exifinterface:1.3.7")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    annotationProcessor("androidx.room:room-compiler:2.6.1")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.media3:media3-common:1.4.1")
    implementation("androidx.media3:media3-session:1.4.1")

    // Material
    implementation("com.google.android.material:material:1.12.0")

    // Compose
    implementation("androidx.compose.runtime:runtime:1.7.0")
    implementation("androidx.compose.material3:material3:1.3.0")
    implementation("androidx.compose.material:material-icons-extended:1.7.0")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.compose.animation:animation-graphics:1.7.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.4")

    // Kotlin
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.3.21")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")

    // Dagger
    implementation("com.google.dagger:dagger:2.51.1")
    annotationProcessor("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")
    implementation("javax.annotation:javax.annotation-api:1.3.2")

    // Lottie
    implementation("com.airbnb.android:lottie:6.4.2")
    implementation("com.airbnb.android:lottie-compose:6.4.2")

    // Protobuf
    implementation("com.google.protobuf:protobuf-javalite:3.25.3")

    // Prebuilt AOSP libs (compileOnly — framework APIs)
    compileOnly(files("$rootDir/libs/framework.jar"))

    // Prebuilt AOSP libs (implementation)
    implementation(files("$rootDir/libs/SystemUI-proto.jar"))
    implementation(files("$rootDir/libs/SystemUI-tags.jar"))
    implementation(files("$rootDir/libs/SystemUI-statsd.jar"))
    implementation(files("$rootDir/libs/SystemUI-res.jar"))
    implementation(files("$rootDir/libs/WifiTrackerLib.jar"))
    implementation(files("$rootDir/libs/SettingsLib.jar"))
    implementation(files("$rootDir/libs/WindowManager-Shell.jar"))
    implementation(files("$rootDir/libs/WindowManager-Shell-proto.jar"))
    implementation(files("$rootDir/libs/compilelib.jar"))
    implementation(files("$rootDir/libs/iconloader_base.jar"))
    implementation(files("$rootDir/libs/motion_tool_lib.jar"))
    implementation(files("$rootDir/libs/contextualeducationlib.jar"))
    implementation(files("$rootDir/libs/monet.jar"))
    implementation(files("$rootDir/libs/libmonet.jar"))
    implementation(files("$rootDir/libs/notification_flags_lib.jar"))
    implementation(files("$rootDir/libs/device_state_flags_lib.jar"))
    implementation(files("$rootDir/libs/LowLightDreamLib.jar"))
    implementation(files("$rootDir/libs/TraceurCommon.jar"))
    implementation(files("$rootDir/libs/Traceur-res.jar"))
    implementation(files("$rootDir/libs/PlatformComposeCore.jar"))
    implementation(files("$rootDir/libs/PlatformComposeSceneTransitionLayout.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_flags_lib.jar"))

    // Pods (Dagger API modules)
    implementation(files("$rootDir/libs/pods-api.jar"))
    implementation(files("$rootDir/libs/pods-impl.jar"))
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:3.25.3"
    }
}
