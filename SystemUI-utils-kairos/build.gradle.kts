// :SystemUI-utils-kairos — kairos（AOSP packages/SystemUI/utils/kairos，java_library "kairos"）
// 纯 Kotlin JVM 源码库（tier① 规则 S），无 Android 资源/manifest，形态仿 :SystemUI-plugin-core。
plugins {
    `java-library`
    id("org.jetbrains.kotlin.jvm")
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

kotlin {
    jvmToolchain(21)
}

sourceSets {
    getByName("main") {
        java.setSrcDirs(listOf("src"))
        kotlin.setSrcDirs(listOf("src"))
    }
}

dependencies {
    // android.os.Build / SystemProperties（bp libs 隐含 platform）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // bp static_libs: tracinglib-platform（com.android.app.tracing.coroutines）
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))
    // bp static_libs: kotlinx_coroutines
    implementation(libs.kotlinx.coroutines.core)
    // bp static_libs: androidx.collection_collection（ScatterMap / ObjectIntMap）
    implementation(libs.androidx.collection)
    implementation(libs.kotlin.stdlib)
}
