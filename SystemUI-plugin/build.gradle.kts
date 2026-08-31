// :SystemUI-plugin — SystemUIPluginLib runtime（含 bcsmartspace）
// javac 原生注解处理（不用 KAPT/KSP）：在 JavaCompile 上配 annotationProcessorPath
// ⚠️ 待办：全部 @ProtectedInterface 标注在 .kt 文件上，javac 原生处理器看不到 Kotlin 源码，
//    PluginProtector 暂不生成，下游 Unresolved reference 作为保留错误（见 Task 9 记录）
plugins {
    alias(libs.plugins.android.library)
    // plugin 源码含 @Composable/inline composable 调用（LockscreenScope.kt
    // rememberCoroutineScope、TileDetailsViewModel @Composable）；bp static_libs
    // androidx.compose.runtime/ui → 与 :SystemUI-core 同样需 Compose compiler 插件，
    // 否则 backend 报 Couldn't inline method call
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.android.systemui.plugins"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
        // AOSP plugin/Android.bp SystemUIPluginLib: export_proguard_flags_files: true
        // + proguard_flags_files: ["proguard_plugins.flags"] → Gradle consumerProguardFiles
        // （Task 029 R3：byte-exact 复制自 AOSP plugin/proguard_plugins.flags）
        consumerProguardFiles("proguard_plugins.flags")
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src", "bcsmartspace/src")
            kotlin.srcDirs("src", "bcsmartspace/src")
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
    }
}

// javac 原生注解处理：用 annotationProcessor dependency 声明（见 dependencies 块），
// Gradle 会自动解析 processor 及其传递依赖（含 kotlin-stdlib）。
// 不再手动设 annotationProcessorPath——手动设会丢传递依赖且在 Gradle 9 触发 unsafe lock 错误。
// ⚠️ 待办：javac 看不到 .kt 源码，PluginProtector 暂不生成。
tasks.withType<JavaCompile>().configureEach {
    dependsOn(":SystemUI-plugin-processor:jar")
}

dependencies {
    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // build-time 注解处理器（javac 原生）：Gradle 自动解析其传递依赖（kotlin-stdlib 等）
    annotationProcessor(project(":SystemUI-plugin-processor"))

    // tier① SystemUI 自有源码模块
    api(project(":SystemUI-plugin-core"))
    api(project(":SystemUI-animation"))
    api(project(":SystemUI-common"))
    // 17 bp 漂移修正（Task 072）：SystemUIPluginLib bp static_libs 含
    // PlatformComposeSceneTransitionLayout；17 plugin 新增
    // keyguard/ui/composable/elements/*（import com.android.compose.animation.scene.*），
    // 16 遗留缺失，补 :SystemUI-compose（clocks-common 的 scene import 亦经此链传递）
    api(project(":SystemUI-compose"))

    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.kotlin.stdlib)
    // Compose runtime：TileDetailsViewModel.kt 用 @Composable（对齐 AOSP plugin/Android.bp）
    implementation(libs.compose.runtime)
    // AOSP plugin bp static_libs androidx.compose.ui_ui
    // （keyguard/ui/composable/elements/* 引 Modifier/BoxScope，VRect 引 geometry.Rect）
    implementation(libs.compose.ui)
    // LockscreenScope.kt 引 androidx.compose.foundation.layout.BoxScope
    // （Soong 经 androidx prebuilts 传递解析；Gradle 显式声明）
    implementation(libs.compose.foundation)
    // AOSP plugin bp static_libs monet（ClockFaceEvents.kt 引
    // com.android.systemui.monet.ColorScheme；tier② jar，运行时由 core 的
    // implementation 统一 dex）
    compileOnly(files("${rootProject.projectDir}/libs/monet.jar"))
}
