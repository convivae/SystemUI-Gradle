// :SystemUI-plugin-core — PluginCoreLib runtime API（JVM 源码库，无 Android 资源/manifest）
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
    }
}

dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(libs.androidx.annotation)
    implementation(libs.kotlin.stdlib)
}
