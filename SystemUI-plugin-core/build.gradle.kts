// :SystemUI-plugin-core — PluginCoreLib + PluginAnnotationLib runtime API（JVM 源码库，
// 无 Android 资源；17 起 annotations/src 为独立 source root，bp PluginCoreLib
// static_libs = PluginAnnotationLib + SystemUILogCoreLib）
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
        java.setSrcDirs(listOf("src", "annotations/src"))
        kotlin.setSrcDirs(listOf("src", "annotations/src"))
    }
}

dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(libs.androidx.annotation)
    implementation(libs.kotlin.stdlib)
    // 17 bp PluginCoreLib static_libs SystemUILogCoreLib（log/core 已折入 :SystemUI-common）；
    // PluginListener 公有签名引用 MessageBuffer → api
    api(project(":SystemUI-common"))
}
