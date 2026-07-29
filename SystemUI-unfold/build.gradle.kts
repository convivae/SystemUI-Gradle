plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.android.systemui.unfold"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 对齐 AOSP SystemUIUnfoldLib：src 含 kotlin/aidl
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            aidl.srcDirs("src")
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

    // 对齐 AOSP kotlincflags: ["-Xjvm-default=all"]
    kotlinOptions {
        freeCompilerArgs = freeCompilerArgs + "-Xjvm-default=all"
    }

    lint {
        abortOnError = false
    }
}

dependencies {
    // Framework APIs（allprojects 已注入，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // unfold 依赖 androidx.dynamicanimation 1.1.0-alpha04（AOSP 内部 prebuilt，公网 maven 无此版本）：
    // 用到 SpringAnimation.scheduler 属性与 FrameCallbackScheduler 接口。作 compileOnly（tier② 例外），
    // 运行时由 app 提供的真实 androidx 提供；不引 maven 1.0.0 以免 API 版本冲突
    compileOnly(files("${rootProject.projectDir}/libs/dynamicanimation-1.1.0-alpha04.jar"))

    // Dagger 组件（DaggerUnfold/RemoteUnfoldSharedComponent）由 KSP 在本项目内生成。
    // 本模块单独用 dagger 2.57.2：2.51.1 + KSP2 有 "unexpected jvm signature V" bug；
    // 而 2.56+ 全局引入 Lazy<T : Any> 边界会让 core 的无界 Lazy<T> 报错，故用 implementation
    // 直接坐标把 2.57.2 限定在 unfold（implementation 不透传到 core，core 仍用 catalog 2.51.1）
    ksp("com.google.dagger:dagger-compiler:2.57.2")

    // tier③ 标准第三方（maven 版本依赖，对齐 bp static_libs）
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation("com.google.dagger:dagger:2.57.2")
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}
