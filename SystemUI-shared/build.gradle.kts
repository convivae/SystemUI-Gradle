plugins {
    alias(libs.plugins.android.library)
    id("com.google.devtools.ksp")
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
    // view_capture（frameworks/libs/systemui/viewcapturelib，tier② 干净 jar：
    // tools/package_viewcapture_motiontool_jars.py 合并 3 个 owning Soong
    // implementation 输出 javac 9 + kotlin 23 + view_capture_proto 24 = 56 类，
    // 仅 com/android/app/viewcapture/**，无 androidx/kotlin/kotlinx/protobuf-lite 污染。
    // AOSP SystemUISharedLib static_libs runtime/program 输入，dex 进 APK，故 implementation
    implementation(files("${rootProject.projectDir}/libs/view_capture.jar"))
    // protobuf-javalite（lite proto runtime，tier③ 官方 Maven 坐标，task 035 R8 Batch 3）；
    // view_capture_proto 生成类依赖它，补齐本库自身 runtime closure
    implementation(libs.protobuf.javalite)

    // Dagger 组件（SystemUnfoldSharedModule 的 factory）由 KSP 在本项目内生成。
    // 对齐 AOSP shared/Android.bp SystemUISharedLib plugins: ["dagger2-compiler"]；Dagger 2.59.2 + useBindingGraphFix 默认启用（2.58+）。
    ksp(libs.dagger.compiler)

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
