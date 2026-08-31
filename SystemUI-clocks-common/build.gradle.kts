// :SystemUI-clocks-common — AOSP 17 android_library "SystemUIClocks-CommonLib"
// (frameworks/base/packages/SystemUI/customization/clocks/common/Android.bp)：
//   srcs src/**/*.java|kt（21 文件）+ resource_dirs: ["res"] + 模块根 manifest
//   static_libs: [PlatformAnimationLib, androidx.compose.runtime_runtime,
//                 androidx.compose.ui_ui, dagger2, jsr330, kotlinx_coroutines, monet]
//   libs: ["SystemUIPluginLib"]（Soong libs = 编译期可见、运行时由宿主提供）
//   plugins: ["dagger2-compiler"]；kotlincflags: ["-Xjvm-default=all"]
// 被 SystemUICustomizationLib static_libs 消费（customization/Android.bp L36）。

plugins {
    alias(libs.plugins.android.library)
    id("com.google.devtools.ksp")
}

android {
    // 与 AOSP manifest package 一致（manifest 保留 package 属性 → AGP 仅警告，值与 namespace 相等）
    namespace = "com.android.systemui.customization.clocks"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        // bp min_sdk_version: "current"（平台当前版）；本 Gradle 树统一 minSdk 32（工程惯例，
        // 编译闭包由 compileSdk 决定，见 docs/issues/2026-08-28-c4-gradle-wiring.md）
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            res.srcDirs("res")
            manifest.srcFile("AndroidManifest.xml")
        }
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
        checkReleaseBuilds = false
    }
}

// AGP builtInKotlin：顶层 kotlin { compilerOptions { } }
// 对齐 bp kotlincflags: ["-Xjvm-default=all"]
kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xjvm-default=all")
    }
}

dependencies {
    // Framework APIs（allprojects 已注入，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // tier① SystemUI 自有源码模块
    // bp static_libs: PlatformAnimationLib（scene/log 经 :SystemUI-plugin 的 api 链传递）
    api(project(":SystemUI-animation"))
    // bp libs: ["SystemUIPluginLib"]（编译期可见；运行时由 core/customization 闭包 dex 提供）
    // scene 类（com.android.compose.animation.scene.*，clocks 源码直接 import）经
    // :SystemUI-plugin → :SystemUI-compose 的 api 链获得（对齐 SystemUIPluginLib bp
    // static_libs 含 PlatformComposeSceneTransitionLayout）
    compileOnly(project(":SystemUI-plugin"))

    // bp static_libs: monet（tier② jar；运行时由 core 的 implementation 提供）
    compileOnly(files("${rootProject.projectDir}/libs/monet.jar"))

    // bp static_libs: androidx.compose.runtime_runtime / androidx.compose.ui_ui（tier③ 官方坐标）
    implementation(libs.compose.runtime)
    implementation(libs.compose.ui)
    // ContentScopeUtils / DefaultClockFaceLayout 引
    // androidx.compose.foundation.layout.BoxScope（Soong 经 androidx prebuilts
    // 传递解析；Gradle 显式声明）
    implementation(libs.compose.foundation)
    // DefaultClockFaceLayout 引 androidx.constraintlayout.widget.ConstraintSet
    //（Soong 经 SystemUIPluginLib libs: 链的 androidx prebuilts 解析；Gradle 显式声明）
    implementation(libs.androidx.constraintlayout)
    // DigitalClockTextView 引 androidx.core.graphics.withSave/withRotate 等
    //（core-ktx 扩展；Soong 经依赖链解析，Gradle 显式声明）
    implementation(libs.androidx.core.ktx)

    // bp static_libs: kotlinx_coroutines（tier③ 官方坐标）
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)

    // bp static_libs: jsr330（tier③ 官方坐标 javax.inject:1）
    implementation(libs.jsr330)

    // bp static_libs + plugins: dagger2 / dagger2-compiler（KSP 跑，KAPT 禁用）
    implementation(libs.dagger)
    ksp(libs.dagger.compiler)
}
