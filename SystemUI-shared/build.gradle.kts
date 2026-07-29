plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.shared"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 对齐 AOSP SystemUISharedLib：src 下同时含 java/kotlin/aidl
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            aidl.srcDirs("src")
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

    // 对齐 AOSP SystemUISharedLib 的 kotlincflags: ["-Xjvm-default=all"]
    kotlinOptions {
        freeCompilerArgs = freeCompilerArgs + "-Xjvm-default=all"
    }

    lint {
        abortOnError = false
    }
}

dependencies {
    // Framework APIs - provided by system at runtime（allprojects 已注入，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // UncaughtExceptionPreHandlerManager 依赖 libcore 隐藏 API Thread.setUncaughtExceptionPreHandler，
    // Kotlin/JDK21 工具链的 java.lang.Thread 无此隐藏方法（AOSP 走 core-for-system-modules bootclasspath），
    // 无法从源码编译。故其 .kt 源码已排除，改由 AOSP 编译产物提取的 class 提供（§1.3 允许）。
    // 详见 docs/issues/2026-07-29-shared-source-migration.md
    compileOnly(files("${rootProject.projectDir}/libs/shared-uncaught-handler.jar"))

    // tier① SystemUI 自有源码模块（对齐 shared/Android.bp 的 SystemUIPluginLib / PluginCoreLib）
    implementation(project(":SystemUI-plugin"))
    implementation(project(":SystemUI-plugin-core"))

    // tier② AOSP 特有产物 jar（含资源/内部类，非源码模块）
    compileOnly(files("${rootProject.projectDir}/libs/WindowManager-Shell.jar"))
    // SystemUIUnfoldLib 暂以 jar 引入（后续 Phase C 再源码化）
    compileOnly(project(":SystemUI-unfold"))
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
