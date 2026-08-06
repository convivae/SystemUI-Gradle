// :SystemUI-plugin-processor — PluginAnnotationProcessor（build-time，JVM）
// 生成 PluginProtector 等 protected 源码；不作为 runtime implementation 打进 APK
plugins {
    `java-library`
    alias(libs.plugins.kotlin.jvm)
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
        // 服务描述符打包进 processor JAR（等价 Soong auto_service_plugin）
        resources.setSrcDirs(listOf("resources"))
    }
}

dependencies {
    implementation(project(":SystemUI-plugin-core"))
    compileOnly("com.google.auto.service:auto-service-annotations:1.1.1")
    implementation(libs.kotlin.stdlib)
}
