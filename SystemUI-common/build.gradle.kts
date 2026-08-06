plugins {
    `java-library`
    alias(libs.plugins.kotlin.jvm)
}

// SystemUI-common: Common + Log + shared-utils 合并为单一 JVM 源码模块
// （对齐 AOSP SystemUICommon + SystemUILogLib + SystemUI-shared-utils 的 static_libs 语义）
java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

kotlin {
    jvmToolchain(21)
}

sourceSets {
    getByName("main") {
        java.setSrcDirs(listOf("common/src", "log/src", "utils/src"))
        kotlin.setSrcDirs(listOf("common/src", "log/src", "utils/src"))
    }
}

dependencies {
    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // Tracing.kt 用 com.android.app.tracing.coroutines（tier② tracinglib）
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))

    // Kotlin
    api(libs.kotlinx.coroutines.core)
    implementation(libs.kotlin.stdlib)

    // AndroidX（compileOnly：JVM 模块不打包 android 资源）
    compileOnly(libs.androidx.annotation)
    implementation(libs.errorprone.annotations)
}
