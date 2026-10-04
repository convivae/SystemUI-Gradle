plugins {
    `java-library`
    id("org.jetbrains.kotlin.jvm")
}

// SystemUI-common: Common + Log + LogCore + shared-utils 合并为单一 JVM 源码模块
// （对齐 AOSP SystemUICommon + SystemUILogLib + SystemUILogCoreLib + SystemUI-shared-utils
// 的 static_libs 语义；17 新增 log/core/src source root）
java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

kotlin {
    jvmToolchain(21)
}

sourceSets {
    getByName("main") {
        java.setSrcDirs(listOf("common/src", "log/src", "log/core/src", "utils/src"))
        kotlin.setSrcDirs(listOf("common/src", "log/src", "log/core/src", "utils/src"))
    }
}

// JVM 模块的 SysUISdk android.jar 由根构建通过 AGP sdkComponents 接入，
// 与 Android 模块共用 SDK 解析（local.properties / 环境变量），不猜测用户路径。

dependencies {
    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // Tracing.kt 用 com.android.app.tracing.coroutines（tier② tracinglib）
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))
    // 17 SystemUI-shared-utils bp static_libs：view_capture（ViewCaptureAwareWindowManagerFactory）
    // 与 com_android_systemui_flags_lib（utils/src WindowManagerUtils 用 Flags.enableViewCaptureTracing）；
    // runtime closure 由 core 的 implementation 承担，此处 compileOnly
    compileOnly(files("${rootProject.projectDir}/libs/view_capture.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/systemui-flags.jar"))

    // Kotlin
    api(libs.kotlinx.coroutines.core)
    implementation(libs.kotlin.stdlib)

    // AndroidX（compileOnly：JVM 模块不打包 android 资源）
    compileOnly(libs.androidx.annotation)
    implementation(libs.errorprone.annotations)
}
