plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.shared"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 对齐 AOSP SystemUISharedLib：src 下同时含 java/kotlin/aidl；keyguard child 合入
    sourceSets {
        getByName("main") {
            java.srcDirs("src", "keyguard/src")
            kotlin.srcDirs("src", "keyguard/src")
            aidl.srcDirs("src", "keyguard/src")
            res.srcDirs("res")
            manifest.srcFile("AndroidManifest.xml")
        }
    }

    buildFeatures {
        aidl = true
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

// AGP builtInKotlin：用顶层 kotlin { compilerOptions { } } 替代废弃的 android.kotlinOptions { }
// 对齐 AOSP SystemUISharedLib 的 kotlincflags: ["-Xjvm-default=all"]
kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xjvm-default=all")
    }
}

dependencies {
    // Framework APIs - provided by system at runtime（allprojects 已注入，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // tier① SystemUI 自有源码模块（对齐 shared/Android.bp 的 static_libs）
    api(project(":SystemUI-shared-biometrics"))
    api(project(":SystemUI-animation"))
    api(project(":SystemUI-plugin-core"))
    api(project(":SystemUI-plugin"))
    api(project(":SystemUI-unfold"))

    // tier② AOSP 特有产物 jar（含资源/内部类，非源码模块）
    compileOnly(libs.systemui.wmshell)
    compileOnly(libs.systemui.wmshell.shared)
    // com_android_systemui_shared_flags_lib（aconfig 生成，含 com.android.systemui.shared.Flags）
    compileOnly(files("${rootProject.projectDir}/libs/systemui-shared-flags.jar"))
    // tracinglib（frameworks/libs/systemui，tier② prebuilt jar）
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))
    // view_capture（frameworks/libs/systemui/viewcapturelib，tier② prebuilt jar）
    compileOnly(files("${rootProject.projectDir}/libs/view_capture.jar"))

    // tier③ 标准第三方（maven 版本依赖）
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.concurrent.futures)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    implementation(libs.dagger)
    implementation(libs.guava)
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}
